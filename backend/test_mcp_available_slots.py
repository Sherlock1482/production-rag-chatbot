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
                "find_available_interview_slots",
                arguments={
                    "start_time": "2026-10-02T15:00:00+00:00",
                    "duration_minutes": 30,
                    "number_of_slots": 3,
                },
            )

            print("\nAvailable slots:")
            print(result)


if __name__ == "__main__":
    asyncio.run(main())