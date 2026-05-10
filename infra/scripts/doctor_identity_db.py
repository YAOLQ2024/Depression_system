#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from urllib import error, request

ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = ROOT / "infra" / "compose" / "docker-compose.dev.yml"
DEFAULT_DATABASE = "mcs"
REQUIRED_TABLES = ("users", "sessions", "alembic_version")
SEED_USERS = (
    "admin@mcs.local",
    "researcher@mcs.local",
    "participant@mcs.local",
)


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


def print_ok(message: str) -> None:
    print(f"[OK]   {message}")


def print_fail(message: str) -> None:
    print(f"[FAIL] {message}")


def format_command(args: list[str]) -> str:
    return " ".join(args)


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
        raise RuntimeError(f"{format_command(args)} -> {stderr}")
    return result.stdout.strip()


def check_http_ready(name: str, url: str) -> None:
    try:
        with request.urlopen(url, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
            status = payload.get("status")
            if response.status != 200 or status not in {"ready", "ok"}:
                raise RuntimeError(f"unexpected response: {payload}")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    except error.URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Check identity-service database initialization.")
    parser.add_argument("--database", default=DEFAULT_DATABASE, help="PostgreSQL database name inside compose postgres.")
    args = parser.parse_args()

    print(f"Checking identity database against compose file: {COMPOSE_FILE}")
    print(f"Target database: {args.database}")

    failures: list[str] = []

    try:
        output = query_postgres(args.database, "SELECT 1;")
        if output != "1":
            raise RuntimeError(f"unexpected query result: {output!r}")
        print_ok("postgres is reachable")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"postgres connectivity check failed: {exc}")
        print_fail(f"postgres connectivity check failed: {exc}")

    missing_tables: list[str] = []
    if not failures:
        try:
            relation_sql = (
                "SELECT "
                "to_regclass('public.users'),"
                "to_regclass('public.sessions'),"
                "to_regclass('public.alembic_version');"
            )
            output = query_postgres(args.database, relation_sql)
            relations = output.split("|") if output else []
            for table_name, relation_name in zip(REQUIRED_TABLES, relations, strict=False):
                if relation_name != table_name:
                    missing_tables.append(table_name)
            if len(relations) != len(REQUIRED_TABLES):
                missing_tables.extend(REQUIRED_TABLES[len(relations) :])

            if missing_tables:
                raise RuntimeError(f"missing tables: {', '.join(missing_tables)}")
            print_ok("required identity tables exist")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"table check failed: {exc}")
            print_fail(f"table check failed: {exc}")

    if not failures:
        try:
            seed_sql = (
                "SELECT email FROM users "
                "WHERE email IN ("
                + ",".join(f"'{email}'" for email in SEED_USERS)
                + ") ORDER BY email;"
            )
            output = query_postgres(args.database, seed_sql)
            found_users = tuple(line.strip() for line in output.splitlines() if line.strip())
            missing_users = [email for email in SEED_USERS if email not in found_users]
            if missing_users:
                raise RuntimeError(f"missing seed users: {', '.join(missing_users)}")
            print_ok("default seed users exist")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"seed user check failed: {exc}")
            print_fail(f"seed user check failed: {exc}")

    for service_name, url in (
        ("identity-service", "http://127.0.0.1:8011/health/ready"),
        ("gateway-service", "http://127.0.0.1:8080/health/ready"),
    ):
        try:
            check_http_ready(service_name, url)
            print_ok(f"{service_name} ready endpoint is healthy")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{service_name} readiness check failed: {exc}")
            print_fail(f"{service_name} readiness check failed: {exc}")

    if not failures:
        print("\nIdentity database doctor passed.")
        return 0

    print("\nIdentity database doctor found problems.")
    print("Suggested recovery:")
    print("  1. docker compose -f infra/compose/docker-compose.dev.yml up -d --build identity-service gateway-service consultation")
    print("  2. If the local volume is corrupted, run:")
    print("     docker compose -f infra/compose/docker-compose.dev.yml down -v")
    print("     docker compose -f infra/compose/docker-compose.dev.yml up -d --build")
    return 1


if __name__ == "__main__":
    sys.exit(main())
