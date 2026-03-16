import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

load_dotenv()

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp")
REPORT_DIR = Path(os.getenv("REPORT_DIR", "./reports"))
REPORT_DIR.mkdir(parents=True, exist_ok=True)


async def fetch_quotes_via_mcp(symbols: list[str]) -> dict[str, Any]:
    """
    Fetch normalized quotes by calling the MCP tool instead of the Rust API directly.
    """
    transport = StreamableHttpTransport(url=MCP_SERVER_URL)
    client = Client(transport)

    async with client:
        result = await client.call_tool("get_stock_quotes", {"symbols": symbols})

        if hasattr(result, "data"):
            data = result.data
        elif isinstance(result, dict):
            data = result
        else:
            raise RuntimeError(f"Unexpected MCP tool result: {result}")

        if not isinstance(data, dict):
            raise RuntimeError("MCP tool returned non-dict data")

        return data


def enrich_analysis(report_data: dict[str, Any]) -> dict[str, Any]:
    """
    Add ranking and summary fields for PDF generation.
    """
    quotes = report_data.get("quotes", [])
    if not quotes:
        raise ValueError("No quotes found in report data")

    sorted_quotes = sorted(quotes, key=lambda q: float(q.get("change", 0)), reverse=True)
    best = sorted_quotes[0]
    worst = sorted_quotes[-1]

    return {
        "requested_symbols": report_data.get("requested_symbols", []),
        "quotes": sorted_quotes,
        "summary": {
            "highest_performer": best["symbol"],
            "highest_change": best["change"],
            "highest_change_percent": best["change_percent"],
            "lowest_performer": worst["symbol"],
            "lowest_change": worst["change"],
            "lowest_change_percent": worst["change_percent"],
        },
    }


def _draw_line(c: canvas.Canvas, text: str, x: int, y: int, max_chars: int = 100) -> int:
    c.drawString(x, y, text[:max_chars])
    return y - 16


def generate_pdf(report_data: dict[str, Any], filename: Path) -> None:
    """
    Render the analysis result into a simple PDF report.
    """
    c = canvas.Canvas(str(filename), pagesize=A4)
    width, height = A4

    y = height - 50

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Stock Analysis Report")

    y -= 25
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Generated at: {datetime.now(timezone.utc).isoformat()}")

    y -= 30
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Requested Symbols")

    y -= 20
    c.setFont("Helvetica", 10)
    symbols_text = ", ".join(report_data.get("requested_symbols", []))
    y = _draw_line(c, symbols_text, 50, y, max_chars=110)

    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Ranked Quote Summary")

    y -= 20
    c.setFont("Helvetica", 10)

    for idx, quote in enumerate(report_data["quotes"], start=1):
        line = (
            f"{idx}. {quote['symbol']} | price={quote['price']} | prev_close={quote['previous_close']} | "
            f"change={quote['change']} ({quote['change_percent']}) | day={quote['latest_trading_day']}"
        )
        y = _draw_line(c, line, 50, y, max_chars=115)

        if y < 80:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 10)

    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Highlights")

    y -= 20
    c.setFont("Helvetica", 10)

    summary = report_data["summary"]
    y = _draw_line(
        c,
        f"Top performer: {summary['highest_performer']} with change "
        f"{summary['highest_change']} ({summary['highest_change_percent']})",
        50,
        y,
        max_chars=110,
    )
    y = _draw_line(
        c,
        f"Weakest performer: {summary['lowest_performer']} with change "
        f"{summary['lowest_change']} ({summary['lowest_change_percent']})",
        50,
        y,
        max_chars=110,
    )

    c.save()


async def main() -> None:
    symbols = ["MSFT", "AAPL", "NVDA"]

    raw_data = await fetch_quotes_via_mcp(symbols)
    analyzed = enrich_analysis(raw_data)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = REPORT_DIR / f"stock-report-{ts}.pdf"

    generate_pdf(analyzed, output)
    print(f"Report written to {output}")


if __name__ == "__main__":
    asyncio.run(main())