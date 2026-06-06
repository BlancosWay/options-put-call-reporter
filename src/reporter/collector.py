from __future__ import annotations

import asyncio
import json
import urllib.parse
import urllib.request
from contextlib import suppress
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

from reporter.models import DataSource, ExpirationRow, Snapshot, SymbolConfig, TopMetrics
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


YFIN_OPTIONS_URL = "https://api.yfin.dev/v1/options"


async def collect_symbol(symbol_config: SymbolConfig, captured_at: datetime, archive_dir: Path) -> Snapshot:
    try:
        return await _collect_symbol_from_barchart(symbol_config, captured_at, archive_dir)
    except CollectionError as primary_exc:
        try:
            return await _collect_symbol_from_yfin(symbol_config, captured_at, archive_dir, primary_exc)
        except Exception as fallback_exc:
            raise CollectionError(
                f"{symbol_config.symbol} collection failed. "
                f"Barchart failed: {_short_error(primary_exc)}; "
                f"yfin.dev fallback failed: {_short_error(fallback_exc)}"
            ) from fallback_exc


async def _collect_symbol_from_barchart(
    symbol_config: SymbolConfig,
    captured_at: datetime,
    archive_dir: Path,
) -> Snapshot:
    archive_dir.mkdir(parents=True, exist_ok=True)
    playwright_manager = async_playwright()
    try:
        playwright = await playwright_manager.__aenter__()
    except Exception as exc:
        raise CollectionError(f"{symbol_config.symbol} extraction failed: {exc}") from exc

    snapshot = None
    try:
        browser = None
        context = None
        page = None
        expiration_response_task = None
        collection_error = None
        try:
            browser = await playwright.chromium.launch(headless=True)
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
            raw_api_json, api_payload = await _api_body_and_payload_from_response(
                expiration_response,
                symbol_config.symbol,
            )
            rows = _extract_rows_from_api_payload(api_payload, symbol_config.symbol)
            snapshot = await _snapshot_from_page(page, symbol_config.symbol, symbol_config.url, captured_at, rows=rows)
            (archive_dir / f"{symbol_config.symbol}-raw.html").write_text(html, encoding="utf-8")
            (archive_dir / f"{symbol_config.symbol}-raw.json").write_text(
                raw_api_json,
                encoding="utf-8",
            )
            (archive_dir / f"{symbol_config.symbol}-snapshot.json").write_text(
                _snapshot_json(snapshot),
                encoding="utf-8",
            )
        except Exception as exc:
            if expiration_response_task is not None:
                expiration_response_task.cancel()
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
            collection_error = CollectionError(message)
            raise collection_error from exc
        finally:
            cleanup_error = None
            for resource in (context, browser):
                if resource is None:
                    continue
                try:
                    await resource.close()
                except Exception as exc:
                    if collection_error is not None:
                        continue
                    if cleanup_error is None:
                        cleanup_error = exc
            if cleanup_error is not None:
                raise cleanup_error
    except BaseException as exc:
        suppress_exception = await playwright_manager.__aexit__(type(exc), exc, exc.__traceback__)
        if not suppress_exception:
            raise
    else:
        await playwright_manager.__aexit__(None, None, None)
        if snapshot is None:
            raise CollectionError(f"{symbol_config.symbol} extraction failed: no snapshot was created")
        return snapshot


async def _collect_symbol_from_yfin(
    symbol_config: SymbolConfig,
    captured_at: datetime,
    archive_dir: Path,
    primary_error: CollectionError,
) -> Snapshot:
    archive_dir.mkdir(parents=True, exist_ok=True)
    symbol = symbol_config.symbol.upper()
    initial_payload = await _fetch_yfin_json(symbol)
    raw_responses: list[dict[str, Any]] = [{"expiration": None, "payload": initial_payload}]
    expiration_dates = _extract_yfin_expiration_dates(initial_payload, symbol)
    seen_expirations = _extract_yfin_option_expirations(initial_payload, symbol)
    for expiration in expiration_dates:
        if expiration in seen_expirations:
            continue
        payload = await _fetch_yfin_json(symbol, expiration)
        raw_responses.append({"expiration": expiration, "payload": payload})
        seen_expirations.update(_extract_yfin_option_expirations(payload, symbol))

    rows = _extract_yfin_rows([response["payload"] for response in raw_responses], symbol, captured_at)
    source_url = _yfin_url(symbol)
    snapshot = Snapshot(
        symbol=symbol,
        url=symbol_config.url,
        captured_at=captured_at,
        metrics=TopMetrics(None, None, None, None, None),
        rows=rows,
        data_source=DataSource(
            name="yfin.dev",
            url=source_url,
            is_fallback=True,
            note=f"Fallback after Barchart failed: {_short_error(primary_error)}",
        ),
    )
    (archive_dir / f"{symbol_config.symbol}-yfin-raw.json").write_text(
        json.dumps({"symbol": symbol, "responses": raw_responses}, indent=2),
        encoding="utf-8",
    )
    (archive_dir / f"{symbol_config.symbol}-snapshot.json").write_text(
        _snapshot_json(snapshot),
        encoding="utf-8",
    )
    return snapshot


async def _fetch_yfin_json(symbol: str, expiration: int | None = None) -> dict[str, Any]:
    return await asyncio.to_thread(_fetch_json_from_url, _yfin_url(symbol, expiration))


def _fetch_json_from_url(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": BROWSER_USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = getattr(response, "status", None)
            if status is not None and status >= 400:
                raise CollectionError(f"yfin.dev returned HTTP {status}")
            body = response.read().decode("utf-8")
    except CollectionError:
        raise
    except Exception as exc:
        raise CollectionError(str(exc)) from exc
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise CollectionError("yfin.dev returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise CollectionError("yfin.dev returned an invalid payload")
    return payload


def _yfin_url(symbol: str, expiration: int | None = None) -> str:
    params: dict[str, str] = {"symbol": symbol.upper()}
    if expiration is not None:
        params["date"] = str(expiration)
    return f"{YFIN_OPTIONS_URL}?{urllib.parse.urlencode(params)}"


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


async def _api_body_and_payload_from_response(response, symbol: str) -> tuple[str, dict]:
    status = getattr(response, "status", None)
    if status is not None and status >= 400:
        raise CollectionError(f"{symbol} options expiration API returned HTTP {status}")
    body = await response.text()
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise CollectionError(f"{symbol} options expiration API returned invalid JSON") from exc
    if not isinstance(data, dict):
        raise CollectionError(f"{symbol} options expiration API returned an invalid payload")
    return body, data


def _extract_rows_from_api_payload(data: dict, symbol: str) -> list[ExpirationRow]:
    rows = data.get("data")
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


def _extract_yfin_expiration_dates(payload: dict[str, Any], symbol: str) -> list[int]:
    raw_dates = _yfin_result(payload, symbol).get("expirationDates")
    if not isinstance(raw_dates, list) or not raw_dates:
        raise CollectionError(f"{symbol} yfin.dev payload returned no expiration dates")
    dates: list[int] = []
    for raw_date in raw_dates:
        try:
            dates.append(int(raw_date))
        except (TypeError, ValueError) as exc:
            raise CollectionError(f"{symbol} yfin.dev payload contained invalid expiration date") from exc
    return dates


def _extract_yfin_option_expirations(payload: dict[str, Any], symbol: str) -> set[int]:
    expirations: set[int] = set()
    for option_chain in _yfin_options(payload, symbol):
        expiration = option_chain.get("expirationDate")
        if expiration is None:
            continue
        try:
            expirations.add(int(expiration))
        except (TypeError, ValueError) as exc:
            raise CollectionError(f"{symbol} yfin.dev option chain contained invalid expirationDate") from exc
    return expirations


def _extract_yfin_rows(payloads: list[dict[str, Any]], symbol: str, captured_at: datetime) -> list[ExpirationRow]:
    contracts_by_expiration: dict[int, dict[str, list[dict[str, Any]]]] = {}
    seen_contracts: dict[int, dict[str, set[tuple[str, str]]]] = {}
    for payload in payloads:
        for option_chain in _yfin_options(payload, symbol):
            expiration = option_chain.get("expirationDate")
            if expiration is None:
                raise CollectionError(f"{symbol} yfin.dev option chain missing expirationDate")
            try:
                expiration_timestamp = int(expiration)
            except (TypeError, ValueError) as exc:
                raise CollectionError(f"{symbol} yfin.dev option chain contained invalid expirationDate") from exc
            calls = option_chain.get("calls", [])
            puts = option_chain.get("puts", [])
            valid_calls = [contract for contract in calls if isinstance(contract, dict)] if isinstance(calls, list) else []
            valid_puts = [contract for contract in puts if isinstance(contract, dict)] if isinstance(puts, list) else []
            if not valid_calls and not valid_puts:
                continue
            grouped_contracts = contracts_by_expiration.setdefault(expiration_timestamp, {"calls": [], "puts": []})
            seen_for_expiration = seen_contracts.setdefault(expiration_timestamp, {"calls": set(), "puts": set()})
            grouped_contracts["calls"].extend(
                _deduplicate_yfin_contracts(
                    valid_calls,
                    "calls",
                    expiration_timestamp,
                    seen_for_expiration["calls"],
                )
            )
            grouped_contracts["puts"].extend(
                _deduplicate_yfin_contracts(
                    valid_puts,
                    "puts",
                    expiration_timestamp,
                    seen_for_expiration["puts"],
                )
            )

    if not contracts_by_expiration:
        raise CollectionError(f"{symbol} yfin.dev payload returned no data rows")

    rows = [
        _yfin_expiration_to_row(expiration, contracts["calls"], contracts["puts"], captured_at)
        for expiration, contracts in contracts_by_expiration.items()
    ]
    rows.sort(key=lambda row: row.expiration_date)
    return rows


def _deduplicate_yfin_contracts(
    contracts: list[dict[str, Any]],
    side: str,
    expiration_timestamp: int,
    seen: set[tuple[str, str]],
) -> list[dict[str, Any]]:
    unique_contracts: list[dict[str, Any]] = []
    for contract_index, contract in enumerate(contracts):
        identity = _yfin_contract_identity(
            contract,
            side,
            expiration_timestamp,
            contract_index,
        )
        if identity in seen:
            continue
        seen.add(identity)
        unique_contracts.append(contract)
    return unique_contracts


def _yfin_contract_identity(
    contract: dict[str, Any],
    side: str,
    expiration_timestamp: int,
    contract_index: int,
) -> tuple[str, str]:
    contract_symbol = contract.get("contractSymbol")
    if isinstance(contract_symbol, str) and contract_symbol.strip():
        return ("contractSymbol", contract_symbol.strip())
    strike = contract.get("strike")
    fallback_key = f"{side}:{expiration_timestamp}:{strike!r}:{contract_index}"
    return ("position", fallback_key)


def _yfin_result(payload: dict[str, Any], symbol: str) -> dict[str, Any]:
    data = payload.get("data")
    if not isinstance(data, dict):
        raise CollectionError(f"{symbol} yfin.dev payload returned no data")
    option_chain = data.get("optionChain")
    if not isinstance(option_chain, dict):
        raise CollectionError(f"{symbol} yfin.dev payload returned no optionChain")
    result = option_chain.get("result")
    if not isinstance(result, list) or not result or not isinstance(result[0], dict):
        raise CollectionError(f"{symbol} yfin.dev payload returned no result")
    return result[0]


def _yfin_options(payload: dict[str, Any], symbol: str) -> list[dict[str, Any]]:
    options = _yfin_result(payload, symbol).get("options")
    if not isinstance(options, list):
        raise CollectionError(f"{symbol} yfin.dev payload returned no options")
    return [option for option in options if isinstance(option, dict)]


def _yfin_expiration_to_row(
    expiration_timestamp: int,
    calls: list[dict[str, Any]],
    puts: list[dict[str, Any]],
    captured_at: datetime,
) -> ExpirationRow:
    expiration_date = datetime.fromtimestamp(expiration_timestamp, tz=timezone.utc).date()
    put_volume = _sum_yfin_contract_field(puts, "volume")
    call_volume = _sum_yfin_contract_field(calls, "volume")
    put_open_interest = _sum_yfin_contract_field(puts, "openInterest")
    call_open_interest = _sum_yfin_contract_field(calls, "openInterest")
    implied_volatility = _average_yfin_implied_volatility([*calls, *puts])
    is_monthly = _is_standard_monthly_expiration(expiration_date)
    return ExpirationRow(
        expiration_label=f"{expiration_date:%m/%d/%y} ({'m' if is_monthly else 'w'})",
        expiration_date=expiration_date,
        dte=(expiration_date - captured_at.date()).days,
        put_volume=put_volume,
        call_volume=call_volume,
        total_volume=put_volume + call_volume,
        put_call_volume_ratio=_safe_ratio(put_volume, call_volume),
        put_open_interest=put_open_interest,
        call_open_interest=call_open_interest,
        total_open_interest=put_open_interest + call_open_interest,
        put_call_open_interest_ratio=_safe_ratio(put_open_interest, call_open_interest),
        implied_volatility=implied_volatility,
        is_monthly=is_monthly,
    )


def _sum_yfin_contract_field(contracts: list[dict[str, Any]], field: str) -> int:
    total = 0
    for contract in contracts:
        value = contract.get(field)
        if value is None:
            continue
        try:
            total += int(value)
        except (TypeError, ValueError):
            total += int(float(value))
    return total


def _average_yfin_implied_volatility(contracts: list[dict[str, Any]]) -> float | None:
    values: list[float] = []
    for contract in contracts:
        value = contract.get("impliedVolatility")
        if value is None:
            continue
        values.append(float(value) * 100)
    if not values:
        return None
    return sum(values) / len(values)


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator:
        return numerator / denominator
    if numerator:
        return float("inf")
    return 0.0


def _is_standard_monthly_expiration(expiration_date: date) -> bool:
    first_day = expiration_date.replace(day=1)
    third_friday = first_day + timedelta(days=(4 - first_day.weekday()) % 7 + 14)
    juneteenth_displaces_third_friday = third_friday.month == 6 and third_friday.day in {18, 19}
    if juneteenth_displaces_third_friday:
        return expiration_date == third_friday - timedelta(days=1)
    return expiration_date == third_friday


def _short_error(error: BaseException) -> str:
    message = str(error).split(";")[0]
    extraction_prefix = " extraction failed: "
    if extraction_prefix in message:
        return message.split(extraction_prefix, 1)[1]
    return message


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
