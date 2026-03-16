import asyncio
import json
import os
from typing import Any

from dotenv import load_dotenv
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.exceptions import ToolError

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
        try:
            result = await client.call_tool("get_stock_quotes", {"symbols": symbols})
        except ToolError as exc:
            raise RuntimeError(
                "MCP tool get_stock_quotes failed. "
                "If the message includes 502 for /quotes, ensure the Rust API is running "
                "at RUST_API_BASE (default http://127.0.0.1:8080), and that "
                "ALPHAVANTAGE_API_KEY is valid and not rate-limited."
            ) from exc

        # FastMCP examples show structured tool results exposed via .data
        if hasattr(result, "data"):
            return result.data

        # Fallback for environments returning plain dict-like results
        if isinstance(result, dict):
            return result

        return {"raw_result": str(result)}


async def main() -> None:
    symbols = ["MSFT"]
    data = await fetch_stock_quotes(symbols)
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
