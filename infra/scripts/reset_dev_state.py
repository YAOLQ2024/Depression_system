#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = ROOT / "infra" / "compose" / "docker-compose.dev.yml"
DEFAULT_DATABASE = "mcs"
AUTH_TABLES = {"users", "sessions"}


def print_info(message: str) -> None:
    print(f"[INFO] {message}")


def print_ok(message: str) -> None:
    print(f"[OK]   {message}")


def print_fail(message: str) -> None:
    print(f"[FAIL] {message}")


def run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def compose_args(*args: str) -> list[str]:
    return ["docker", "compose", "-f", str(COMPOSE_FILE), *args]


def query_postgres(database: str, sql: str) -> str:
    args = compose_args(
        "exec",
        "-T",
        "postgres",
        "psql",
        "-U",
        "mcs",
        "-d",
        database,
        "-Atc",
        sql,
    )
    result = run_command(args)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise RuntimeError(f"{' '.join(args)} -> {stderr}")
    return result.stdout.strip()


def list_public_tables(database: str) -> list[str]:
    sql = (
        "SELECT tablename FROM pg_tables "
        "WHERE schemaname = 'public' "
        "ORDER BY tablename;"
    )
    output = query_postgres(database, sql)
    return [line.strip() for line in output.splitlines() if line.strip()]


def is_version_table(table_name: str) -> bool:
    return table_name == "alembic_version" or table_name.endswith(
        "_alembic_version"
    )


def resolve_reset_tables(
    database: str,
    *,
    include_auth: bool,
) -> list[str]:
    tables = list_public_tables(database)
    filtered: list[str] = []
    for table_name in tables:
        if is_version_table(table_name):
            continue
        if not include_auth and table_name in AUTH_TABLES:
            continue
        filtered.append(table_name)
    return filtered


def truncate_tables(database: str, tables: list[str]) -> None:
    quoted_tables = ", ".join(f'public."{table}"' for table in tables)
    sql = f"TRUNCATE TABLE {quoted_tables} RESTART IDENTITY CASCADE;"
    query_postgres(database, sql)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Reset development runtime data in the compose postgres database "
            "without dropping Docker volumes."
        )
    )
    parser.add_argument(
        "--database",
        default=DEFAULT_DATABASE,
        help="PostgreSQL database name inside compose postgres.",
    )
    parser.add_argument(
        "--include-auth",
        action="store_true",
        help=(
            "Also clear identity tables (users and sessions). "
            "Use only when you intend to rebuild auth seed data."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        tables = resolve_reset_tables(
            args.database,
            include_auth=args.include_auth,
        )
        if not tables:
            print_info("No resettable tables found.")
            return 0

        print_info(
            f"Resetting {len(tables)} tables in compose postgres database {args.database}."
        )
        for table_name in tables:
            print(f"  - {table_name}")

        truncate_tables(args.database, tables)
    except Exception as exc:  # noqa: BLE001
        print_fail(str(exc))
        return 1

    print_ok("Development runtime data cleared.")
    if args.include_auth:
        print_info(
            "Auth tables were cleared too. Restart identity-service if you need seed users recreated."
        )
    else:
        print_info("Auth tables were preserved.")
    print_info(
        "If the browser still shows old login or session references, clear site storage and reload."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
