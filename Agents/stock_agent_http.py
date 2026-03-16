import asyncio
import json
import os
from typing import Any

from dotenv import load_dotenv
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

load_dotenv()

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp")


async def fetch_stock_quotes(symbols: list[str]) -> dict[str, Any]:
    """
    Connect to the remote MCP server over Streamable HTTP
    and call the get_stock_quotes tool.
    """
    transport = StreamableHttpTransport(url=MCP_SERVER_URL)
    client = Client(transport)

    async with client:
        result = await client.call_tool("get_stock_quotes", {"symbols": symbols})

        # FastMCP examples show structured tool results exposed via .data
        if hasattr(result, "data"):
            return result.data

        # Fallback for environments returning plain dict-like results
        if isinstance(result, dict):
            return result

        return {"raw_result": str(result)}


async def main() -> None:
    symbols = ["MSFT", "AAPL", "NVDA"]
    data = await fetch_stock_quotes(symbols)
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    asyncio.run(main())