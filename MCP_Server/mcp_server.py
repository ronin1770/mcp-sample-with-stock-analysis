import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

load_dotenv(Path(__file__).with_name(".env"))

mcp = FastMCP(
    "stock-tools",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            "127.0.0.1:*",
            "localhost:*",
            "136.114.37.41:*",
        ],
        allowed_origins=[
            "http://127.0.0.1:6274",
            "http://localhost:6274",
            "http://136.114.37.41:6274",
        ],
    ),
)

RUST_API_BASE = os.getenv("RUST_API_BASE", "http://127.0.0.1:8080")


@mcp.tool()
async def get_stock_quotes(symbols: list[str]) -> dict[str, Any]:
    joined = ",".join(symbols)

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            f"{RUST_API_BASE}/quotes",
            params={"symbols": joined},
        )
        response.raise_for_status()
        return response.json()


app = mcp.streamable_http_app()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:6274",
        "http://localhost:6274",
        "http://136.114.37.41:6274",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)