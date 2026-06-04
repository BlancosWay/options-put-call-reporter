from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

from reporter.models import ExpirationRow, Snapshot, SymbolConfig, TopMetrics
from reporter.parsing import ParseError, parse_expiration_label, parse_float, parse_int, parse_percent


BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/137.0.0.0 Safari/537.36"
)


class CollectionError(RuntimeError):
    pass


async def collect_symbol(symbol_config: SymbolConfig, captured_at: datetime, archive_dir: Path) -> Snapshot:
    archive_dir.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = None
        page = None
        try:
            context = await browser.new_context(user_agent=BROWSER_USER_AGENT)
            page = await context.new_page()
            response = await page.goto(symbol_config.url, wait_until="domcontentloaded", timeout=60000)
            status = getattr(response, "status", None)
            if status is not None and status >= 400:
                raise CollectionError(f"{symbol_config.symbol} collection returned HTTP {status}")
            await page.locator("table th", has_text="Expiration Date").first.wait_for(timeout=30000)
            html = await page.content()
            snapshot = await _snapshot_from_page(page, symbol_config.symbol, symbol_config.url, captured_at)
            (archive_dir / f"{symbol_config.symbol}-raw.html").write_text(html, encoding="utf-8")
            (archive_dir / f"{symbol_config.symbol}-raw.json").write_text(_snapshot_json(snapshot), encoding="utf-8")
            return snapshot
        except Exception as exc:
            if page is None:
                diagnostic_paths, diagnostic_errors = [], ["page was not created"]
            else:
                diagnostic_paths, diagnostic_errors = await _capture_failure_diagnostics(
                    page,
                    symbol_config.symbol,
                    archive_dir,
                )
            message = f"{symbol_config.symbol} extraction failed: {exc}"
            if diagnostic_paths:
                message += f"; diagnostics saved to {' and '.join(str(path) for path in diagnostic_paths)}"
            if diagnostic_errors:
                message += f"; diagnostic capture failed: {'; '.join(diagnostic_errors)}"
            raise CollectionError(message) from exc
        finally:
            if context is not None:
                await context.close()
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
    normalized_symbol = symbol.upper()
    metrics = await _extract_metrics(page, normalized_symbol)
    rows = await _extract_rows(page)
    if not rows:
        raise CollectionError(f"{normalized_symbol} extraction produced zero expiration rows")
    return Snapshot(symbol=normalized_symbol, url=url, captured_at=captured_at, metrics=metrics, rows=rows)


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


async def _extract_metrics(page, symbol: str) -> TopMetrics:
    text = (await page.locator("body").inner_text()).replace("\xa0", " ")

    def after(label: str) -> str | None:
        index = text.find(label)
        if index == -1:
            return None
        value = text[index + len(label):].strip().splitlines()[0].strip()
        return value.split()[0] if value else None

    def required_percent(label: str) -> float | None:
        raw_value = after(f"{label}:")
        try:
            return parse_percent(raw_value)
        except ParseError as exc:
            raise CollectionError(f"{symbol} top metric parse failed for {label}: {exc}") from exc

    metrics = TopMetrics(
        latest_earnings=after("Latest Earnings:"),
        implied_volatility=required_percent("Implied Volatility"),
        historic_volatility=required_percent("Historic Volatility"),
        iv_rank=required_percent("IV Rank"),
        iv_percentile=required_percent("IV Percentile"),
    )
    missing = _missing_top_metric_labels(metrics)
    if missing:
        raise CollectionError(f"{symbol} missing top metrics: {', '.join(missing)}")
    return metrics


def _missing_top_metric_labels(metrics: TopMetrics) -> list[str]:
    missing: list[str] = []
    if metrics.latest_earnings is None:
        missing.append("Latest Earnings")
    if metrics.implied_volatility is None:
        missing.append("Implied Volatility")
    if metrics.historic_volatility is None:
        missing.append("Historic Volatility")
    if metrics.iv_rank is None:
        missing.append("IV Rank")
    if metrics.iv_percentile is None:
        missing.append("IV Percentile")
    return missing


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
