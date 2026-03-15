import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# Load .env from the same directory as this file
load_dotenv(Path(__file__).with_name(".env"))

RUST_API_BASE = os.getenv("RUST_API_BASE", "http://127.0.0.1:8080")
PUBLIC_IP = os.getenv("MCP_PUBLIC_IP", "136.114.37.41")

mcp = FastMCP(
    "stock-tools",
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            "127.0.0.1:*",
            "localhost:*",
            f"{PUBLIC_IP}:*",
        ],
        allowed_origins=[
            "http://127.0.0.1:6274",
            "http://localhost:6274",
            f"http://{PUBLIC_IP}:6274",
        ],
    ),
)


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


# Mount MCP under /mcp
starlette_app = Starlette(
    routes=[
        Mount("/", app=mcp.streamable_http_app()),
    ]
)

# Browser-based MCP clients need CORS + exposed Mcp-Session-Id header
app = CORSMiddleware(
    starlette_app,
    allow_origins=[
        "http://127.0.0.1:6274",
        "http://localhost:6274",
        f"http://{PUBLIC_IP}:6274",
    ],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "mcp-protocol-version",
        "mcp-session-id",
    ],
    expose_headers=["Mcp-Session-Id", "mcp-session-id"],
    allow_credentials=False,
)