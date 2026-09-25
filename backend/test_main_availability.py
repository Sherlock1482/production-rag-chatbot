import asyncio

from main import call_availability_mcp


async def main():
    result = await call_availability_mcp(
        "2026-10-02T20:30:00+05:30",
        "2026-10-02T21:30:00+05:30"
    )

    print("\nAvailability result:")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())