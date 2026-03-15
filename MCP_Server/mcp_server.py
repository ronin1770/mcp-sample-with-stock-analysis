import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv(Path(__file__).with_name(".env"))

mcp = FastMCP("stock-tools")
RUST_API_BASE = os.getenv("RUST_API_BASE", "http://127.0.0.1:8080")


@mcp.tool()
async def get_stock_quotes(symbols: list[str]) -> dict[str, Any]:
    """Fetch latest stock quotes from the Rust API."""
    joined = ",".join(symbols)

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            f"{RUST_API_BASE}/quotes",
            params={"symbols": joined},
        )
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    mcp.run(transport="streamable-http")