import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():

    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"]
    )

    async with stdio_client(server_params) as (read, write):

        async with ClientSession(read, write) as session:

            await session.initialize()

            result = await session.call_tool(
                "get_interview_schedule",
                {
                    "candidate_name": "Priya Patel"
                }
            )

            print("\nMCP RESULT:")
            print(result)


if __name__ == "__main__":
    asyncio.run(main())