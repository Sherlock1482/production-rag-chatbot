import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


MCP_SERVER_PATH = "mcp_server.py"


async def main():

    server_params = StdioServerParameters(
        command="python",
        args=[MCP_SERVER_PATH],
    )

    async with stdio_client(server_params) as (read, write):

        async with ClientSession(read, write) as session:

            await session.initialize()

            result = await session.call_tool(
                "check_calendar_availability_tool",
                arguments={
                    "start_time": "2026-10-02T20:30:00+05:30",
                    "end_time": "2026-10-02T21:30:00+05:30",
                },
            )

            print("\nAvailability result:")
            print(result)


if __name__ == "__main__":
    asyncio.run(main())