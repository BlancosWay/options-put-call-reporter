from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

from reporter.models import ExpirationRow, Snapshot, SymbolConfig, TopMetrics
from reporter.parsing import parse_expiration_label, parse_float, parse_int, parse_percent


class CollectionError(RuntimeError):
    pass


async def collect_symbol(symbol_config: SymbolConfig, captured_at: datetime, archive_dir: Path) -> Snapshot:
    archive_dir.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(symbol_config.url, wait_until="domcontentloaded", timeout=60000)
            await page.locator("table th", has_text="Expiration Date").first.wait_for(timeout=30000)
            html = await page.content()
            snapshot = await _snapshot_from_page(page, symbol_config.symbol, symbol_config.url, captured_at)
            (archive_dir / f"{symbol_config.symbol}-raw.html").write_text(html, encoding="utf-8")
            (archive_dir / f"{symbol_config.symbol}-raw.json").write_text(_snapshot_json(snapshot), encoding="utf-8")
            return snapshot
        except Exception as exc:
            diagnostic_paths, diagnostic_errors = await _capture_failure_diagnostics(page, symbol_config.symbol, archive_dir)
            message = f"{symbol_config.symbol} extraction failed: {exc}"
            if diagnostic_paths:
                message += f"; diagnostics saved to {' and '.join(str(path) for path in diagnostic_paths)}"
            if diagnostic_errors:
                message += f"; diagnostic capture failed: {'; '.join(diagnostic_errors)}"
            raise CollectionError(message) from exc
        finally:
            await browser.close()


async def collect_from_html(symbol: str, url: str, html: str, captured_at: datetime) -> Snapshot:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.set_content(html)
            return await _snapshot_from_page(page, symbol, url, captured_at)
        finally:
            await browser.close()


async def _snapshot_from_page(page, symbol: str, url: str, captured_at: datetime) -> Snapshot:
    metrics = await _extract_metrics(page)
    rows = await _extract_rows(page)
    if not rows:
        raise CollectionError(f"{symbol} extraction produced zero expiration rows")
    return Snapshot(symbol=symbol.upper(), url=url, captured_at=captured_at, metrics=metrics, rows=rows)


async def _capture_failure_diagnostics(page, symbol: str, archive_dir: Path) -> tuple[list[Path], list[str]]:
    paths: list[Path] = []
    errors: list[str] = []
    html_path = archive_dir / f"{symbol}-failure.html"
    png_path = archive_dir / f"{symbol}-failure.png"
    try:
        html_path.write_text(await page.content(), encoding="utf-8")
        paths.append(html_path)
    except Exception as exc:
        errors.append(f"HTML: {exc}")
    try:
        await page.screenshot(path=png_path, full_page=True)
        paths.append(png_path)
    except Exception as exc:
        errors.append(f"PNG: {exc}")
    return paths, errors


async def _extract_metrics(page) -> TopMetrics:
    text = await page.locator("body").inner_text()

    def after(label: str) -> str | None:
        index = text.find(label)
        if index == -1:
            return None
        value = text[index + len(label):].strip().splitlines()[0].strip()
        return value.split()[0] if value else None

    return TopMetrics(
        latest_earnings=after("Latest Earnings:"),
        implied_volatility=parse_percent(after("Implied Volatility:")),
        historic_volatility=parse_percent(after("Historic Volatility:")),
        iv_rank=parse_percent(after("IV Rank:")),
        iv_percentile=parse_percent(after("IV Percentile:")),
    )


async def _extract_rows(page) -> list[ExpirationRow]:
    rows: list[ExpirationRow] = []
    table_rows = await page.locator("table tr").all()
    for table_row in table_rows[1:]:
        cells = [cell.strip() for cell in await table_row.locator("th,td").all_inner_texts()]
        if len(cells) < 11 or "/" not in cells[0]:
            continue
        parsed = parse_expiration_label(cells[0])
        rows.append(
            ExpirationRow(
                expiration_label=cells[0],
                expiration_date=parsed.expiration_date,
                dte=parse_int(cells[1]),
                put_volume=parse_int(cells[2]),
                call_volume=parse_int(cells[3]),
                total_volume=parse_int(cells[4]),
                put_call_volume_ratio=parse_float(cells[5]),
                put_open_interest=parse_int(cells[6]),
                call_open_interest=parse_int(cells[7]),
                total_open_interest=parse_int(cells[8]),
                put_call_open_interest_ratio=parse_float(cells[9]),
                implied_volatility=parse_percent(cells[10]),
                is_monthly=parsed.is_monthly,
            )
        )
    return rows


def _snapshot_json(snapshot: Snapshot) -> str:
    data = asdict(snapshot)
    data["captured_at"] = snapshot.captured_at.isoformat()
    data["metrics"] = asdict(snapshot.metrics)
    data["rows"] = [
        {
            **asdict(row),
            "expiration_date": row.expiration_date.isoformat(),
        }
        for row in snapshot.rows
    ]
    return json.dumps(data, indent=2)
