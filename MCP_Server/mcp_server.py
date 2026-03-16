import os
import re
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware

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
            "http://127.0.0.1:*",
            "http://localhost:*",
            f"http://{PUBLIC_IP}:*",
            "https://127.0.0.1:*",
            "https://localhost:*",
            f"https://{PUBLIC_IP}:*",
        ],
    ),
)


@mcp.tool()
async def get_stock_quotes(symbols: list[str]) -> dict[str, Any]:
    """Fetch latest stock quotes from the Rust API."""
    joined = ",".join(symbols)

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            response = await client.get(
                f"{RUST_API_BASE}/quotes",
                params={"symbols": joined},
            )
        except httpx.RequestError as exc:
            raise RuntimeError(
                f"Failed to reach Rust API at {RUST_API_BASE}/quotes: {exc}. "
                "Ensure the Rust API process is running and RUST_API_BASE is correct."
            ) from exc

        if response.status_code >= 400:
            detail = _extract_error_detail(response)
            raise RuntimeError(
                f"Rust API returned HTTP {response.status_code} for /quotes: {detail}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise RuntimeError(
                "Rust API returned a non-JSON response for /quotes."
            ) from exc


def _extract_error_detail(response: httpx.Response) -> str:
    """Return a short error detail string from a Rust API response."""
    try:
        payload = response.json()
    except ValueError:
        text = response.text.strip()
        return text if text else "empty response body"

    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, str) and error.strip():
            return error.strip()
        return str(payload)

    return str(payload)


# Build MCP ASGI app (includes /mcp route and required lifespan handlers)
starlette_app = mcp.streamable_http_app()

# Browser-based MCP clients need CORS + exposed Mcp-Session-Id header
app = CORSMiddleware(
    starlette_app,
    allow_origin_regex=rf"^https?://(127\.0\.0\.1|localhost|{re.escape(PUBLIC_IP)})(:\d+)?$",
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


def main() -> None:
    """Run the server for local development and MCP Inspector."""
    parser = ArgumentParser(description="Run the stock MCP server")
    parser.add_argument(
        "--transport",
        choices=["streamable-http", "stdio"],
        default=os.getenv("MCP_TRANSPORT", "streamable-http"),
        help="Use streamable-http for browser Inspector URL mode or stdio for command mode",
    )
    parser.add_argument("--host", default=os.getenv("MCP_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MCP_PORT", "8000")))
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
        return

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
