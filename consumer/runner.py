import asyncio

from consumer.main import app


def main() -> None:
    asyncio.run(app.run())


if __name__ == "__main__":
    main()
