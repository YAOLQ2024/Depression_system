from app.services.user_store import ensure_seed_users


def main() -> None:
    ensure_seed_users()
    print("seeded default identity users")


if __name__ == "__main__":
    main()
