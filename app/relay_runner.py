import asyncio

from app.services.outbox_relay import run_outbox_relay


def main() -> None:
    asyncio.run(run_outbox_relay())


if __name__ == "__main__":
    main()
