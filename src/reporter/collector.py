from __future__ import annotations

import asyncio
import json
from contextlib import suppress
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
TOP_METRICS_READY_SCRIPT = r"""() => {
    const toolbar = document.querySelector(".bc-options-toolbar");
    if (!toolbar) {
        return false;
    }
    const text = toolbar.innerText.replace(/\u00a0/g, " ").replace(/\s+/g, " ");
    return /Latest Earnings:\s+\S+/.test(text)
        && /Implied Volatility:\s+[-0-9.]+%/.test(text)
        && /Historic Volatility:\s+[-0-9.]+%/.test(text)
        && /IV Rank:\s+[-0-9.]+%/.test(text)
        && /IV Percentile:\s+[-0-9.]+%/.test(text);
}"""


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
            expiration_response_task = _watch_for_options_expirations_response(page, timeout_ms=60000)
            response = await page.goto(symbol_config.url, wait_until="domcontentloaded", timeout=60000)
            status = getattr(response, "status", None)
            if status is not None and status >= 400:
                expiration_response_task.cancel()
                with suppress(asyncio.CancelledError):
                    await expiration_response_task
                raise CollectionError(f"{symbol_config.symbol} collection returned HTTP {status}")
            expiration_response = await expiration_response_task
            await _wait_for_top_metrics(page)
            html = await page.content()
            rows = await _extract_rows_from_api_response(expiration_response, symbol_config.symbol)
            snapshot = await _snapshot_from_page(page, symbol_config.symbol, symbol_config.url, captured_at, rows=rows)
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


async def _snapshot_from_page(
    page,
    symbol: str,
    url: str,
    captured_at: datetime,
    rows: list[ExpirationRow] | None = None,
) -> Snapshot:
    normalized_symbol = symbol.upper()
    metrics = await _extract_metrics(page, normalized_symbol)
    expiration_rows = rows if rows is not None else await _extract_rows(page)
    if not expiration_rows:
        raise CollectionError(f"{normalized_symbol} extraction produced zero expiration rows")
    return Snapshot(symbol=normalized_symbol, url=url, captured_at=captured_at, metrics=metrics, rows=expiration_rows)


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


def _is_options_expirations_response(response) -> bool:
    return "/options-expirations/get" in getattr(response, "url", "")


def _watch_for_options_expirations_response(page, timeout_ms: int):
    return _OptionsExpirationsResponseWaiter(page, timeout_ms)


class _OptionsExpirationsResponseWaiter:
    def __init__(self, page, timeout_ms: int) -> None:
        self._page = page
        self._future = asyncio.get_running_loop().create_future()
        self._timeout_handle = asyncio.get_running_loop().call_later(timeout_ms / 1000, self._timeout)
        self._closed = False
        page.on("response", self._handle_response)

    def _handle_response(self, response) -> None:
        if self._future.done():
            return
        try:
            if _is_options_expirations_response(response):
                self._future.set_result(response)
        except Exception as exc:
            self._future.set_exception(exc)

    def _timeout(self) -> None:
        if not self._future.done():
            self._future.set_exception(TimeoutError("Timed out waiting for Barchart options-expirations response"))

    def cancel(self) -> None:
        if not self._future.done():
            self._future.cancel()
        self._cleanup()

    async def _wait(self):
        try:
            return await self._future
        finally:
            self._cleanup()

    def _cleanup(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._timeout_handle.cancel()
        self._page.remove_listener("response", self._handle_response)

    def __await__(self):
        return self._wait().__await__()


async def _wait_for_top_metrics(page) -> None:
    await page.wait_for_function(TOP_METRICS_READY_SCRIPT, timeout=30000)


async def _extract_metrics(page, symbol: str) -> TopMetrics:
    try:
        text = await page.locator(".bc-options-toolbar").inner_text(timeout=1000)
    except Exception:
        text = await page.locator("body").inner_text()
    text = text.replace("\xa0", " ")

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


async def _extract_rows_from_api_response(response, symbol: str) -> list[ExpirationRow]:
    status = getattr(response, "status", None)
    if status is not None and status >= 400:
        raise CollectionError(f"{symbol} options expiration API returned HTTP {status}")
    data = await response.json()
    rows = data.get("data") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise CollectionError(f"{symbol} options expiration API returned no data rows")
    return [_api_row_to_expiration_row(row, symbol) for row in rows if isinstance(row, dict)]


def _api_row_to_expiration_row(row: dict, symbol: str) -> ExpirationRow:
    label = _api_expiration_label(row, symbol)
    parsed = parse_expiration_label(label)
    return ExpirationRow(
        expiration_label=label,
        expiration_date=parsed.expiration_date,
        dte=parse_int(_required_api_value(row, "daysToExpiration", symbol)),
        put_volume=parse_int(_required_api_value(row, "putVolume", symbol)),
        call_volume=parse_int(_required_api_value(row, "callVolume", symbol)),
        total_volume=parse_int(_required_api_value(row, "totalVolume", symbol)),
        put_call_volume_ratio=parse_float(_required_api_value(row, "putCallVolumeRatio", symbol)),
        put_open_interest=parse_int(_required_api_value(row, "putOpenInterest", symbol)),
        call_open_interest=parse_int(_required_api_value(row, "callOpenInterest", symbol)),
        total_open_interest=parse_int(_required_api_value(row, "totalOpenInterest", symbol)),
        put_call_open_interest_ratio=parse_float(_required_api_value(row, "putCallOpenInterestRatio", symbol)),
        implied_volatility=parse_percent(_required_api_value(row, "averageVolatility", symbol)),
        is_monthly=parsed.is_monthly,
    )


def _api_expiration_label(row: dict, symbol: str) -> str:
    expiration_date = _required_api_value(row, "expirationDate", symbol)
    expiration_type = _required_api_value(row, "expirationType", symbol).lower()
    suffix_by_type = {"monthly": "m", "weekly": "w"}
    suffix = suffix_by_type.get(expiration_type)
    if suffix is None:
        raise CollectionError(f"{symbol} unsupported expiration type '{expiration_type}'")
    return f"{expiration_date} ({suffix})"


def _required_api_value(row: dict, field: str, symbol: str) -> str:
    value = row.get(field)
    if value is None:
        raise CollectionError(f"{symbol} options expiration API row missing {field}")
    return str(value)


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
