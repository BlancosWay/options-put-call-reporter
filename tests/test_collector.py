import html
import json
import math
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pytest

from reporter import collector
from reporter.collector import CollectionError, collect_from_html, collect_symbol
from reporter.models import SymbolConfig


FIXTURE_HTML = Path(__file__).parent / "fixtures" / "barchart_put_call_sample.html"


class _FakeWaitHandle:
    def __init__(self, page: "_FakePage", text: str) -> None:
        self._page = page
        self._text = text

    @property
    def first(self) -> "_FakeWaitHandle":
        return self

    async def wait_for(self, timeout: int) -> None:
        self._page.waited_for_texts.append((self._text, timeout))


class _FakeLocator:
    def __init__(self, page: "_FakePage", selector: str, has_text: str | None = None) -> None:
        self._page = page
        self._selector = selector
        self._has_text = has_text

    @property
    def first(self) -> "_FakeLocator":
        return self

    async def wait_for(self, timeout: int) -> None:
        self._page.waited_for_locators.append((self._selector, self._has_text, timeout))

    async def inner_text(self, **kwargs) -> str:
        if self._selector == ".bc-options-toolbar" and "bc-options-toolbar" in self._page.html:
            return _body_text(self._page.html)
        if self._selector != "body":
            raise AssertionError(f"Unexpected inner_text selector {self._selector}")
        return _body_text(self._page.html)

    async def all(self) -> list["_FakeRow"]:
        if self._selector != "table tr":
            raise AssertionError(f"Unexpected all selector {self._selector}")
        return [_FakeRow(row_html) for row_html in _row_html(self._page.html)]


class _FakeRow:
    def __init__(self, html: str) -> None:
        self._html = html

    def locator(self, selector: str) -> "_FakeCells":
        assert selector == "th,td"
        return _FakeCells(self._html)


class _FakeCells:
    def __init__(self, html: str) -> None:
        self._html = html

    async def all_inner_texts(self) -> list[str]:
        return _cell_texts(self._html)


class _FakePage:
    def __init__(
        self,
        html: str = "",
        *,
        goto_error: Exception | None = None,
        response_status: int | None = None,
        expiration_response_data: dict[str, Any] | None = None,
        expiration_response_text: str | None = None,
        content_error: Exception | None = None,
    ) -> None:
        self.html = html
        self.goto_error = goto_error
        self.response_status = response_status
        self.expiration_response_data = expiration_response_data
        self.expiration_response_text = expiration_response_text
        self.content_error = content_error
        self.goto_calls: list[dict[str, object]] = []
        self.waited_for_texts: list[tuple[str, int]] = []
        self.waited_for_locators: list[tuple[str, str | None, int]] = []
        self.response_listener_events: list[str] = []
        self.response_handlers: list = []
        self.waited_for_functions: list[int] = []
        self.screenshot_paths: list[Path] = []

    async def goto(self, url: str, *, wait_until: str, timeout: int) -> None:
        self.goto_calls.append({"url": url, "wait_until": wait_until, "timeout": timeout})
        if self.goto_error is not None:
            raise self.goto_error
        if self.response_status is not None:
            return _FakeResponse(self.response_status)
        response = _FakeResponse(200, self.expiration_response_data, self.expiration_response_text)
        for handler in list(self.response_handlers):
            handler(response)
        return None

    async def wait_for_function(self, expression: str, *, timeout: int) -> None:
        assert "bc-options-toolbar" in expression
        self.waited_for_functions.append(timeout)

    def get_by_text(self, text: str) -> _FakeWaitHandle:
        return _FakeWaitHandle(self, text)

    def on(self, event: str, handler) -> None:
        assert event == "response"
        self.response_listener_events.append("on")
        self.response_handlers.append(handler)

    def remove_listener(self, event: str, handler) -> None:
        assert event == "response"
        self.response_listener_events.append("remove")
        if handler in self.response_handlers:
            self.response_handlers.remove(handler)

    async def content(self) -> str:
        if self.content_error is not None:
            raise self.content_error
        return self.html

    async def set_content(self, html: str) -> None:
        self.html = html

    def locator(self, selector: str, *, has_text: str | None = None) -> _FakeLocator:
        return _FakeLocator(self, selector, has_text)

    async def screenshot(self, *, path: Path, full_page: bool) -> None:
        assert full_page is True
        self.screenshot_paths.append(path)
        path.write_bytes(b"fake screenshot")


class _FakeBrowser:
    def __init__(self, playwright: "_FakePlaywright") -> None:
        self._playwright = playwright
        self.closed = False
        self.close_attempted = False

    async def new_context(self, *, user_agent: str) -> "_FakeContext":
        self._playwright.context_user_agents.append(user_agent)
        context = _FakeContext(self._playwright)
        self._playwright.contexts.append(context)
        return context

    async def new_page(self) -> _FakePage:
        page = self._playwright.new_page()
        self._playwright.pages.append(page)
        return page

    async def close(self) -> None:
        self.close_attempted = True
        if self._playwright.browser_close_error is not None:
            raise self._playwright.browser_close_error
        self.closed = True


class _FakeContext:
    def __init__(self, playwright: "_FakePlaywright") -> None:
        self._playwright = playwright
        self.closed = False
        self.close_attempted = False

    async def new_page(self) -> _FakePage:
        page = self._playwright.new_page()
        self._playwright.pages.append(page)
        return page

    async def close(self) -> None:
        self.close_attempted = True
        if self._playwright.context_close_error is not None:
            raise self._playwright.context_close_error
        self.closed = True


class _FakeResponse:
    def __init__(self, status: int, data: dict[str, Any] | None = None, text: str | None = None) -> None:
        self.status = status
        self.url = "https://www.barchart.com/proxies/core-api/v1/options-expirations/get"
        self._data = data if data is not None else _options_expirations_response()
        self._text = text

    async def json(self) -> dict[str, Any]:
        return self._data

    async def text(self) -> str:
        return self._text if self._text is not None else json.dumps(self._data)


class _FakeChromium:
    def __init__(self, playwright: "_FakePlaywright") -> None:
        self._playwright = playwright

    async def launch(self, *, headless: bool) -> _FakeBrowser:
        assert headless is True
        if self._playwright.launch_error is not None:
            raise self._playwright.launch_error
        self._playwright.launch_count += 1
        browser = _FakeBrowser(self._playwright)
        self._playwright.browsers.append(browser)
        return browser


class _FakePlaywright:
    def __init__(
        self,
        page_factory,
        *,
        launch_error: Exception | None = None,
        enter_error: Exception | None = None,
        exit_error: Exception | None = None,
        context_close_error: Exception | None = None,
        browser_close_error: Exception | None = None,
    ) -> None:
        self._page_factory = page_factory
        self.launch_error = launch_error
        self.enter_error = enter_error
        self.exit_error = exit_error
        self.context_close_error = context_close_error
        self.browser_close_error = browser_close_error
        self.chromium = _FakeChromium(self)
        self.launch_count = 0
        self.pages: list[_FakePage] = []
        self.browsers: list[_FakeBrowser] = []
        self.contexts: list[_FakeContext] = []
        self.context_user_agents: list[str] = []

    def new_page(self) -> _FakePage:
        return self._page_factory()

    async def __aenter__(self) -> "_FakePlaywright":
        if self.enter_error is not None:
            raise self.enter_error
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.exit_error is not None:
            raise self.exit_error
        return None


def _install_fake_playwright(monkeypatch: pytest.MonkeyPatch, fake_playwright: _FakePlaywright) -> None:
    monkeypatch.setattr(collector, "async_playwright", lambda: fake_playwright)


def _body_text(html: str) -> str:
    without_tags = re.sub(r"<[^>]+>", "\n", html)
    lines = [line.strip() for line in without_tags.splitlines() if line.strip()]
    return html_lib_unescape("\n".join(lines))


def _row_html(html: str) -> list[str]:
    return re.findall(r"<tr>\s*(.*?)\s*</tr>", html, flags=re.DOTALL)


def _cell_texts(html: str) -> list[str]:
    cells = re.findall(r"<t[dh][^>]*>\s*(.*?)\s*</t[dh]>", html, flags=re.DOTALL)
    return [html_lib_unescape(re.sub(r"<[^>]+>", "", cell).strip()) for cell in cells]


def html_lib_unescape(value: str) -> str:
    return html.unescape(value)


def _toolbar_html() -> str:
    return """
    <div class="bc-options-toolbar">
      <div>Latest&nbsp;Earnings: <strong>07/29/26</strong></div>
      <div>Implied&nbsp;Volatility: <strong>31.62%</strong></div>
      <div>Historic&nbsp;Volatility: <strong>33.28%</strong></div>
      <div>IV&nbsp;Rank: <strong>61.17%</strong></div>
      <div>IV&nbsp;Percentile: <strong>85%</strong></div>
    </div>
    """


def _options_expirations_response() -> dict[str, Any]:
    return {
        "count": 2,
        "total": 2,
        "data": [
            {
                "expirationDate": "06/18/26",
                "expirationType": "monthly",
                "daysToExpiration": "16",
                "putVolume": "26,096",
                "callVolume": "84,918",
                "totalVolume": "111,014",
                "putCallVolumeRatio": "0.31",
                "putOpenInterest": "244,398",
                "callOpenInterest": "454,545",
                "totalOpenInterest": "698,943",
                "putCallOpenInterestRatio": "0.54",
                "averageVolatility": "32.94%",
            },
            {
                "expirationDate": "06/26/26",
                "expirationType": "weekly",
                "daysToExpiration": "24",
                "putVolume": "9,104",
                "callVolume": "19,646",
                "totalVolume": "28,750",
                "putCallVolumeRatio": "0.46",
                "putOpenInterest": "84,120",
                "callOpenInterest": "156,882",
                "totalOpenInterest": "241,002",
                "putCallOpenInterestRatio": "0.54",
                "averageVolatility": "32.10%",
            },
        ],
    }


def _yfin_payload(expiration_dates: list[int], options: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "data": {
            "optionChain": {
                "result": [
                    {
                        "expirationDates": expiration_dates,
                        "options": options,
                    }
                ]
            }
        }
    }


@pytest.mark.asyncio
async def test_collect_from_html_extracts_metrics_and_rows(tmp_path: Path) -> None:
    html = FIXTURE_HTML.read_text(encoding="utf-8")

    snapshot = await collect_from_html(
        symbol="MSFT",
        url="https://www.barchart.com/stocks/quotes/msft/put-call-ratios",
        html=html,
        captured_at=datetime(2026, 6, 2, 21, 30),
    )

    assert snapshot.symbol == "MSFT"
    assert snapshot.metrics.latest_earnings == "07/29/26"
    assert snapshot.metrics.implied_volatility == 31.62
    assert len(snapshot.rows) == 3
    assert snapshot.rows[0].expiration_label == "06/18/26 (m)"
    assert snapshot.rows[0].put_call_volume_ratio == 0.31
    assert snapshot.rows[0].is_monthly is True
    assert snapshot.rows[1].expiration_label == "06/26/26 (w)"
    assert snapshot.rows[1].is_monthly is False


@pytest.mark.asyncio
async def test_collect_from_html_extracts_metrics_with_nonbreaking_space_labels(tmp_path: Path) -> None:
    html = (
        FIXTURE_HTML.read_text(encoding="utf-8")
        .replace("Latest Earnings:", "Latest&nbsp;Earnings:")
        .replace("Implied Volatility:", "Implied&nbsp;Volatility:")
        .replace("Historic Volatility:", "Historic&nbsp;Volatility:")
        .replace("IV Rank:", "IV&nbsp;Rank:")
        .replace("IV Percentile:", "IV&nbsp;Percentile:")
    )

    snapshot = await collect_from_html(
        symbol="MSFT",
        url="https://www.barchart.com/stocks/quotes/msft/put-call-ratios",
        html=html,
        captured_at=datetime(2026, 6, 2, 21, 30),
    )

    assert snapshot.metrics.latest_earnings == "07/29/26"
    assert snapshot.metrics.implied_volatility == 31.62
    assert snapshot.metrics.historic_volatility == 33.28
    assert snapshot.metrics.iv_rank == 61.17
    assert snapshot.metrics.iv_percentile == 85.0


@pytest.mark.asyncio
async def test_collect_from_html_allows_missing_latest_earnings(tmp_path: Path) -> None:
    html = FIXTURE_HTML.read_text(encoding="utf-8").replace(
        "      <span>Latest Earnings:</span><strong>07/29/26</strong>\n",
        "",
    )

    snapshot = await collect_from_html(
        symbol="SPY",
        url="https://www.barchart.com/stocks/quotes/spy/put-call-ratios",
        html=html,
        captured_at=datetime(2026, 6, 2, 21, 30),
    )

    assert snapshot.metrics.latest_earnings is None
    assert snapshot.metrics.implied_volatility == 31.62
    assert snapshot.metrics.historic_volatility == 33.28
    assert snapshot.metrics.iv_rank == 61.17
    assert snapshot.metrics.iv_percentile == 85.0
    assert len(snapshot.rows) == 3


@pytest.mark.asyncio
async def test_collect_from_html_rejects_snapshots_missing_required_top_metrics(tmp_path: Path) -> None:
    html = FIXTURE_HTML.read_text(encoding="utf-8").replace(
        "      <span>IV Rank:</span><strong>61.17%</strong>\n",
        "",
    )

    with pytest.raises(CollectionError) as exc_info:
        await collect_from_html(
            symbol="MSFT",
            url="https://www.barchart.com/stocks/quotes/msft/put-call-ratios",
            html=html,
            captured_at=datetime(2026, 6, 2, 21, 30),
        )

    assert "MSFT missing top metrics: IV Rank" in str(exc_info.value)


@pytest.mark.asyncio
async def test_collect_from_html_rejects_unparsable_required_top_metric(tmp_path: Path) -> None:
    html = FIXTURE_HTML.read_text(encoding="utf-8").replace("61.17%", "not-a-percent")

    with pytest.raises(CollectionError) as exc_info:
        await collect_from_html(
            symbol="MSFT",
            url="https://www.barchart.com/stocks/quotes/msft/put-call-ratios",
            html=html,
            captured_at=datetime(2026, 6, 2, 21, 30),
        )

    message = str(exc_info.value)
    assert "MSFT top metric parse failed" in message
    assert "IV Rank" in message


@pytest.mark.asyncio
async def test_collect_symbol_writes_raw_artifacts_without_second_browser_launch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    html = _toolbar_html()
    api_body = json.dumps(_options_expirations_response(), separators=(",", ":"))
    fake_playwright = _FakePlaywright(lambda: _FakePage(html, expiration_response_text=api_body))
    _install_fake_playwright(monkeypatch, fake_playwright)

    snapshot = await collect_symbol(
        SymbolConfig("msft", "https://example.test/msft"),
        captured_at=datetime(2026, 6, 2, 21, 30),
        archive_dir=tmp_path,
    )

    assert snapshot.symbol == "MSFT"
    assert len(snapshot.rows) == 2
    assert (tmp_path / "msft-raw.html").read_text(encoding="utf-8") == html
    raw_api_text = (tmp_path / "msft-raw.json").read_text(encoding="utf-8")
    assert raw_api_text == api_body
    raw_api_json = json.loads(raw_api_text)
    assert raw_api_json["data"][1]["expirationType"] == "weekly"
    snapshot_json = json.loads((tmp_path / "msft-snapshot.json").read_text(encoding="utf-8"))
    assert snapshot_json["symbol"] == "MSFT"
    assert snapshot_json["rows"][1]["expiration_label"] == "06/26/26 (w)"
    assert fake_playwright.launch_count == 1


@pytest.mark.asyncio
async def test_collect_symbol_uses_realistic_browser_user_agent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    html = _toolbar_html()
    fake_playwright = _FakePlaywright(lambda: _FakePage(html))
    _install_fake_playwright(monkeypatch, fake_playwright)

    await collector._collect_symbol_from_barchart(
        SymbolConfig("msft", "https://example.test/msft"),
        captured_at=datetime(2026, 6, 2, 21, 30),
        archive_dir=tmp_path,
    )

    assert len(fake_playwright.context_user_agents) == 1
    user_agent = fake_playwright.context_user_agents[0]
    assert "Mozilla/5.0" in user_agent
    assert "Chrome/" in user_agent


@pytest.mark.asyncio
async def test_collect_symbol_fails_fast_on_blocked_http_status(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    html = FIXTURE_HTML.read_text(encoding="utf-8")
    page = _FakePage(html, response_status=403)
    fake_playwright = _FakePlaywright(lambda: page)
    _install_fake_playwright(monkeypatch, fake_playwright)

    with pytest.raises(CollectionError) as exc_info:
        await collector._collect_symbol_from_barchart(
            SymbolConfig("MSFT", "https://example.test/msft"),
            captured_at=datetime(2026, 6, 2, 21, 30),
            archive_dir=tmp_path,
        )

    assert "HTTP 403" in str(exc_info.value)
    assert page.waited_for_locators == []
    assert page.response_listener_events == ["on", "remove"]


@pytest.mark.asyncio
async def test_collect_symbol_cleans_response_listener_when_navigation_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    page = _FakePage(_toolbar_html(), goto_error=RuntimeError("navigation failed"))
    fake_playwright = _FakePlaywright(lambda: page)
    _install_fake_playwright(monkeypatch, fake_playwright)

    with pytest.raises(CollectionError) as exc_info:
        await collector._collect_symbol_from_barchart(
            SymbolConfig("MSFT", "https://example.test/msft"),
            captured_at=datetime(2026, 6, 2, 21, 30),
            archive_dir=tmp_path,
        )

    assert "navigation failed" in str(exc_info.value)
    assert page.response_listener_events == ["on", "remove"]


@pytest.mark.asyncio
async def test_collect_symbol_falls_back_to_yfin_when_barchart_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    page = _FakePage("<html>blocked</html>", goto_error=RuntimeError("Barchart blocked"))
    fake_playwright = _FakePlaywright(lambda: page)
    _install_fake_playwright(monkeypatch, fake_playwright)
    fetch_calls: list[tuple[str, int | None]] = []

    async def fake_fetch_yfin_json(symbol: str, expiration: int | None = None) -> dict[str, Any]:
        fetch_calls.append((symbol, expiration))
        if expiration is None:
            return _yfin_payload(
                [1781740800, 1782432000],
                [
                    {
                        "expirationDate": 1781740800,
                        "calls": [
                            {"volume": 100, "openInterest": 5, "impliedVolatility": 0.2},
                            {"volume": None, "openInterest": 15, "impliedVolatility": None},
                        ],
                        "puts": [
                            {"volume": 50, "openInterest": 10, "impliedVolatility": 0.4},
                            {"volume": 30, "openInterest": None},
                        ],
                    }
                ],
            )
        if expiration == 1782432000:
            return _yfin_payload(
                [1781740800, 1782432000],
                [
                    {
                        "expirationDate": 1782432000,
                        "calls": [{"volume": 0, "openInterest": 0}],
                        "puts": [{"volume": 7, "openInterest": 9}],
                    }
                ],
            )
        raise AssertionError(f"unexpected yfin expiration {expiration}")

    monkeypatch.setattr(collector, "_fetch_yfin_json", fake_fetch_yfin_json, raising=False)

    snapshot = await collect_symbol(
        SymbolConfig("msft", "https://example.test/msft"),
        captured_at=datetime(2026, 6, 2, 21, 30),
        archive_dir=tmp_path,
    )

    assert snapshot.symbol == "MSFT"
    assert snapshot.metrics.latest_earnings is None
    assert snapshot.metrics.iv_rank is None
    assert snapshot.data_source.name == "yfin.dev"
    assert snapshot.data_source.url == "https://api.yfin.dev/v1/options?symbol=MSFT"
    assert snapshot.data_source.is_fallback is True
    assert snapshot.data_source.note is not None
    assert snapshot.data_source.note.startswith("Fallback after Barchart failed: Barchart blocked")
    assert fetch_calls == [("MSFT", None), ("MSFT", 1782432000)]
    assert [row.expiration_label for row in snapshot.rows] == ["06/18/26 (m)", "06/26/26 (w)"]
    assert snapshot.rows[0].dte == 16
    assert snapshot.rows[0].put_volume == 80
    assert snapshot.rows[0].call_volume == 100
    assert snapshot.rows[0].total_volume == 180
    assert snapshot.rows[0].put_open_interest == 10
    assert snapshot.rows[0].call_open_interest == 20
    assert snapshot.rows[0].total_open_interest == 30
    assert snapshot.rows[0].put_call_volume_ratio == 0.8
    assert snapshot.rows[0].put_call_open_interest_ratio == 0.5
    assert snapshot.rows[0].implied_volatility == 30.0
    assert snapshot.rows[0].is_monthly is True
    assert snapshot.rows[1].expiration_label == "06/26/26 (w)"
    assert math.isinf(snapshot.rows[1].put_call_volume_ratio)
    assert math.isinf(snapshot.rows[1].put_call_open_interest_ratio)
    assert snapshot.rows[1].implied_volatility is None
    raw_json = json.loads((tmp_path / "msft-yfin-raw.json").read_text(encoding="utf-8"))
    assert raw_json["symbol"] == "MSFT"
    assert len(raw_json["responses"]) == 2
    snapshot_json = json.loads((tmp_path / "msft-snapshot.json").read_text(encoding="utf-8"))
    assert snapshot_json["data_source"]["name"] == "yfin.dev"


@pytest.mark.asyncio
async def test_collect_symbol_falls_back_to_yfin_when_browser_launch_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_playwright = _FakePlaywright(lambda: _FakePage(), launch_error=RuntimeError("chromium missing"))
    _install_fake_playwright(monkeypatch, fake_playwright)

    async def fake_fetch_yfin_json(symbol: str, expiration: int | None = None) -> dict[str, Any]:
        assert symbol == "MSFT"
        assert expiration is None
        return _yfin_payload(
            [1781740800],
            [
                {
                    "expirationDate": 1781740800,
                    "calls": [{"volume": 1, "openInterest": 2, "impliedVolatility": 0.25}],
                    "puts": [{"volume": 3, "openInterest": 4, "impliedVolatility": 0.35}],
                }
            ],
        )

    monkeypatch.setattr(collector, "_fetch_yfin_json", fake_fetch_yfin_json)

    snapshot = await collect_symbol(
        SymbolConfig("MSFT", "https://example.test/msft"),
        captured_at=datetime(2026, 6, 2, 21, 30),
        archive_dir=tmp_path,
    )

    assert snapshot.data_source.is_fallback is True
    assert snapshot.data_source.note == "Fallback after Barchart failed: chromium missing"
    assert snapshot.rows[0].put_volume == 3


@pytest.mark.asyncio
async def test_collect_symbol_falls_back_to_yfin_when_playwright_startup_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_playwright = _FakePlaywright(
        lambda: _FakePage(),
        enter_error=RuntimeError("playwright startup failed"),
    )
    _install_fake_playwright(monkeypatch, fake_playwright)

    async def fake_fetch_yfin_json(symbol: str, expiration: int | None = None) -> dict[str, Any]:
        assert symbol == "MSFT"
        assert expiration is None
        return _yfin_payload(
            [1781740800],
            [
                {
                    "expirationDate": 1781740800,
                    "calls": [{"volume": 1, "openInterest": 2, "impliedVolatility": 0.25}],
                    "puts": [{"volume": 3, "openInterest": 4, "impliedVolatility": 0.35}],
                }
            ],
        )

    monkeypatch.setattr(collector, "_fetch_yfin_json", fake_fetch_yfin_json)

    snapshot = await collect_symbol(
        SymbolConfig("MSFT", "https://example.test/msft"),
        captured_at=datetime(2026, 6, 2, 21, 30),
        archive_dir=tmp_path,
    )

    assert snapshot.data_source.is_fallback is True
    assert snapshot.data_source.note == "Fallback after Barchart failed: playwright startup failed"
    assert snapshot.rows[0].put_volume == 3


@pytest.mark.asyncio
async def test_collect_symbol_falls_back_to_yfin_when_barchart_and_cleanup_fail(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    page = _FakePage("<html>blocked</html>", goto_error=RuntimeError("primary blocked"))
    fake_playwright = _FakePlaywright(
        lambda: page,
        context_close_error=RuntimeError("context close failed"),
        browser_close_error=RuntimeError("browser close failed"),
    )
    _install_fake_playwright(monkeypatch, fake_playwright)

    async def fake_fetch_yfin_json(symbol: str, expiration: int | None = None) -> dict[str, Any]:
        assert symbol == "MSFT"
        assert expiration is None
        return _yfin_payload(
            [1781740800],
            [
                {
                    "expirationDate": 1781740800,
                    "calls": [{"volume": 1, "openInterest": 2, "impliedVolatility": 0.25}],
                    "puts": [{"volume": 3, "openInterest": 4, "impliedVolatility": 0.35}],
                }
            ],
        )

    monkeypatch.setattr(collector, "_fetch_yfin_json", fake_fetch_yfin_json)

    snapshot = await collect_symbol(
        SymbolConfig("MSFT", "https://example.test/msft"),
        captured_at=datetime(2026, 6, 2, 21, 30),
        archive_dir=tmp_path,
    )

    assert snapshot.data_source.is_fallback is True
    assert snapshot.data_source.note == "Fallback after Barchart failed: primary blocked"
    assert snapshot.rows[0].put_volume == 3
    assert fake_playwright.contexts[0].close_attempted is True
    assert fake_playwright.browsers[0].close_attempted is True


@pytest.mark.asyncio
async def test_collect_symbol_falls_back_to_yfin_when_barchart_and_playwright_manager_exit_fail(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    page = _FakePage("<html>blocked</html>", goto_error=RuntimeError("primary blocked"))
    fake_playwright = _FakePlaywright(
        lambda: page,
        exit_error=RuntimeError("playwright manager exit failed"),
    )
    _install_fake_playwright(monkeypatch, fake_playwright)

    async def fake_fetch_yfin_json(symbol: str, expiration: int | None = None) -> dict[str, Any]:
        assert symbol == "MSFT"
        assert expiration is None
        return _yfin_payload(
            [1781740800],
            [
                {
                    "expirationDate": 1781740800,
                    "calls": [{"volume": 1, "openInterest": 2, "impliedVolatility": 0.25}],
                    "puts": [{"volume": 3, "openInterest": 4, "impliedVolatility": 0.35}],
                }
            ],
        )

    monkeypatch.setattr(collector, "_fetch_yfin_json", fake_fetch_yfin_json)

    snapshot = await collect_symbol(
        SymbolConfig("MSFT", "https://example.test/msft"),
        captured_at=datetime(2026, 6, 2, 21, 30),
        archive_dir=tmp_path,
    )

    assert snapshot.data_source.is_fallback is True
    assert snapshot.data_source.note == "Fallback after Barchart failed: primary blocked"
    assert snapshot.rows[0].put_volume == 3


@pytest.mark.asyncio
async def test_collect_symbol_falls_back_to_yfin_when_cleanup_fails_after_barchart_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    html = _toolbar_html()
    fake_playwright = _FakePlaywright(
        lambda: _FakePage(html),
        context_close_error=RuntimeError("context close failed"),
    )
    _install_fake_playwright(monkeypatch, fake_playwright)
    yfin_calls: list[str] = []

    async def fake_fetch_yfin_json(symbol: str, expiration: int | None = None) -> dict[str, Any]:
        yfin_calls.append(symbol)
        assert expiration is None
        return _yfin_payload(
            [1781740800],
            [
                {
                    "expirationDate": 1781740800,
                    "calls": [{"volume": 1, "openInterest": 2, "impliedVolatility": 0.25}],
                    "puts": [{"volume": 3, "openInterest": 4, "impliedVolatility": 0.35}],
                }
            ],
        )

    monkeypatch.setattr(collector, "_fetch_yfin_json", fake_fetch_yfin_json)

    snapshot = await collect_symbol(
        SymbolConfig("MSFT", "https://example.test/msft"),
        captured_at=datetime(2026, 6, 2, 21, 30),
        archive_dir=tmp_path,
    )

    assert yfin_calls == ["MSFT"]
    assert snapshot.data_source.is_fallback is True
    assert snapshot.data_source.note == "Fallback after Barchart failed: context close failed"
    assert snapshot.rows[0].put_volume == 3


@pytest.mark.asyncio
async def test_collect_symbol_error_includes_barchart_and_yfin_causes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    page = _FakePage("<html>blocked</html>", goto_error=RuntimeError("primary blocked"))
    fake_playwright = _FakePlaywright(lambda: page)
    _install_fake_playwright(monkeypatch, fake_playwright)

    async def fake_fetch_yfin_json(symbol: str, expiration: int | None = None) -> dict[str, Any]:
        raise CollectionError("fallback unavailable")

    monkeypatch.setattr(collector, "_fetch_yfin_json", fake_fetch_yfin_json, raising=False)

    with pytest.raises(CollectionError) as exc_info:
        await collect_symbol(
            SymbolConfig("MSFT", "https://example.test/msft"),
            captured_at=datetime(2026, 6, 2, 21, 30),
            archive_dir=tmp_path,
        )

    message = str(exc_info.value)
    assert "Barchart failed:" in message
    assert "primary blocked" in message
    assert "yfin.dev fallback failed:" in message
    assert "fallback unavailable" in message


@pytest.mark.asyncio
async def test_fetch_yfin_json_uses_to_thread_with_expected_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[object, str]] = []

    async def fake_to_thread(func, url: str) -> dict[str, Any]:
        calls.append((func, url))
        return {"ok": True}

    monkeypatch.setattr(collector.asyncio, "to_thread", fake_to_thread)

    assert await collector._fetch_yfin_json("msft") == {"ok": True}
    assert await collector._fetch_yfin_json("msft", 1781740800) == {"ok": True}
    assert calls == [
        (collector._fetch_json_from_url, "https://api.yfin.dev/v1/options?symbol=MSFT"),
        (collector._fetch_json_from_url, "https://api.yfin.dev/v1/options?symbol=MSFT&date=1781740800"),
    ]


def test_extract_yfin_rows_rejects_payloads_without_data_rows() -> None:
    with pytest.raises(CollectionError) as exc_info:
        collector._extract_yfin_rows([_yfin_payload([1781740800], [])], "MSFT", datetime(2026, 6, 2, 21, 30))

    assert "MSFT yfin.dev payload returned no data rows" in str(exc_info.value)


def test_extract_yfin_rows_rejects_expirations_without_contracts() -> None:
    payload = _yfin_payload([1781740800], [{"expirationDate": 1781740800, "calls": [], "puts": []}])

    with pytest.raises(CollectionError) as exc_info:
        collector._extract_yfin_rows([payload], "MSFT", datetime(2026, 6, 2, 21, 30))

    assert "MSFT yfin.dev payload returned no data rows" in str(exc_info.value)


def test_extract_yfin_rows_skips_expirations_without_contracts() -> None:
    payload = _yfin_payload(
        [1781740800, 1782432000],
        [
            {"expirationDate": 1781740800, "calls": [], "puts": []},
            {"expirationDate": 1782432000, "calls": [{"volume": 5, "openInterest": 2}], "puts": []},
        ],
    )

    rows = collector._extract_yfin_rows([payload], "MSFT", datetime(2026, 6, 2, 21, 30))

    assert len(rows) == 1
    assert rows[0].expiration_date == date(2026, 6, 26)
    assert rows[0].call_volume == 5


def test_extract_yfin_rows_deduplicates_contract_symbols_by_side_and_expiration() -> None:
    expiration = 1781740800
    duplicate_chain = {
        "expirationDate": expiration,
        "calls": [{"contractSymbol": "MSFT260618C00100000", "volume": 10, "openInterest": 100}],
        "puts": [{"contractSymbol": "MSFT260618P00100000", "volume": 4, "openInterest": 40}],
    }
    distinct_chain = {
        "expirationDate": expiration,
        "calls": [{"contractSymbol": "MSFT260618C00105000", "volume": 5, "openInterest": 50}],
        "puts": [{"contractSymbol": "MSFT260618P00105000", "volume": 8, "openInterest": 80}],
    }
    payloads = [
        _yfin_payload([expiration], [duplicate_chain]),
        _yfin_payload([expiration], [duplicate_chain, distinct_chain]),
    ]

    rows = collector._extract_yfin_rows(payloads, "MSFT", datetime(2026, 6, 2, 21, 30))

    assert len(rows) == 1
    row = rows[0]
    assert row.put_volume == 12
    assert row.call_volume == 15
    assert row.total_volume == 27
    assert row.put_call_volume_ratio == 0.8
    assert row.put_open_interest == 120
    assert row.call_open_interest == 150
    assert row.total_open_interest == 270
    assert row.put_call_open_interest_ratio == 0.8


def test_extract_yfin_rows_deduplicates_no_symbol_contracts_across_duplicate_payloads() -> None:
    expiration = 1781740800
    chain_without_contract_symbols = {
        "expirationDate": expiration,
        "calls": [
            {"strike": 100, "volume": 10, "openInterest": 100},
            {"strike": 100, "volume": 20, "openInterest": 200},
        ],
        "puts": [
            {"strike": 100, "volume": 4, "openInterest": 40},
            {"strike": 100, "volume": 8, "openInterest": 80},
        ],
    }
    payloads = [
        _yfin_payload([expiration], [chain_without_contract_symbols]),
        _yfin_payload([expiration], [chain_without_contract_symbols]),
    ]

    rows = collector._extract_yfin_rows(payloads, "MSFT", datetime(2026, 6, 2, 21, 30))

    assert len(rows) == 1
    row = rows[0]
    assert row.call_volume == 30
    assert row.put_volume == 12
    assert row.call_open_interest == 300
    assert row.put_open_interest == 120
    assert row.put_call_volume_ratio == 0.4
    assert row.put_call_open_interest_ratio == 0.4


def test_safe_ratio_returns_infinity_for_positive_numerator_over_zero_denominator() -> None:
    assert math.isinf(collector._safe_ratio(5, 0))
    assert collector._safe_ratio(0, 0) == 0.0
    assert collector._safe_ratio(5, 2) == 2.5


def test_yfin_monthly_detection_only_marks_holiday_thursday_adjustment() -> None:
    assert collector._is_standard_monthly_expiration(date(2026, 6, 18)) is True
    assert collector._is_standard_monthly_expiration(date(2027, 6, 17)) is True
    assert collector._is_standard_monthly_expiration(date(2027, 6, 18)) is False
    assert collector._is_standard_monthly_expiration(date(2026, 7, 16)) is False
    assert collector._is_standard_monthly_expiration(date(2026, 7, 17)) is True


@pytest.mark.asyncio
async def test_collect_symbol_reads_expiration_rows_from_barchart_api_response(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    page = _FakePage(_toolbar_html())
    fake_playwright = _FakePlaywright(lambda: page)
    _install_fake_playwright(monkeypatch, fake_playwright)

    snapshot = await collect_symbol(
        SymbolConfig("msft", "https://example.test/msft"),
        captured_at=datetime(2026, 6, 2, 21, 30),
        archive_dir=tmp_path,
    )

    assert [row.expiration_label for row in snapshot.rows] == ["06/18/26 (m)", "06/26/26 (w)"]
    assert snapshot.rows[0].put_call_volume_ratio == 0.31
    assert snapshot.rows[1].is_monthly is False
    assert page.response_listener_events == ["on", "remove"]


@pytest.mark.asyncio
async def test_collect_symbol_uses_playwright_response_listener_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class PageWithoutWaitForConvenienceApis(_FakePage):
        wait_for_response = None
        expect_response = None

    page = PageWithoutWaitForConvenienceApis(_toolbar_html())
    fake_playwright = _FakePlaywright(lambda: page)
    _install_fake_playwright(monkeypatch, fake_playwright)

    snapshot = await collect_symbol(
        SymbolConfig("msft", "https://example.test/msft"),
        captured_at=datetime(2026, 6, 2, 21, 30),
        archive_dir=tmp_path,
    )

    assert len(snapshot.rows) == 2
    assert page.response_listener_events == ["on", "remove"]


@pytest.mark.asyncio
async def test_collect_symbol_waits_for_top_metrics_toolbar(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    page = _FakePage(_toolbar_html())
    fake_playwright = _FakePlaywright(lambda: page)
    _install_fake_playwright(monkeypatch, fake_playwright)

    await collector._collect_symbol_from_barchart(
        SymbolConfig("msft", "https://example.test/msft"),
        captured_at=datetime(2026, 6, 2, 21, 30),
        archive_dir=tmp_path,
    )

    assert page.waited_for_functions == [30000]


@pytest.mark.asyncio
async def test_collect_symbol_uses_domcontentloaded_then_waits_for_expiration_header(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    html = _toolbar_html()
    fake_playwright = _FakePlaywright(lambda: _FakePage(html))
    _install_fake_playwright(monkeypatch, fake_playwright)

    await collector._collect_symbol_from_barchart(
        SymbolConfig("msft", "https://example.test/msft"),
        captured_at=datetime(2026, 6, 2, 21, 30),
        archive_dir=tmp_path,
    )

    assert fake_playwright.pages[0].goto_calls[0]["wait_until"] == "domcontentloaded"
    assert fake_playwright.pages[0].waited_for_texts == []
    assert fake_playwright.pages[0].waited_for_locators == []


@pytest.mark.asyncio
async def test_collect_symbol_failure_includes_original_cause_and_diagnostic_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    page = _FakePage("<html>partial page</html>", goto_error=RuntimeError("navigation boom"))
    fake_playwright = _FakePlaywright(lambda: page)
    _install_fake_playwright(monkeypatch, fake_playwright)

    with pytest.raises(CollectionError) as exc_info:
        await collector._collect_symbol_from_barchart(
            SymbolConfig("MSFT", "https://example.test/msft"),
            captured_at=datetime(2026, 6, 2, 21, 30),
            archive_dir=tmp_path,
        )

    message = str(exc_info.value)
    assert "navigation boom" in message
    assert str(tmp_path / "MSFT-failure.html") in message
    assert str(tmp_path / "MSFT-failure.png") in message
    assert (tmp_path / "MSFT-failure.html").read_text(encoding="utf-8") == "<html>partial page</html>"
    assert (tmp_path / "MSFT-failure.png").read_bytes() == b"fake screenshot"


@pytest.mark.asyncio
async def test_collect_symbol_diagnostic_capture_failure_does_not_mask_original_cause(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    page = _FakePage(
        "<html>partial page</html>",
        goto_error=RuntimeError("missing expiration table"),
        content_error=RuntimeError("content capture broke"),
    )
    fake_playwright = _FakePlaywright(lambda: page)
    _install_fake_playwright(monkeypatch, fake_playwright)

    with pytest.raises(CollectionError) as exc_info:
        await collector._collect_symbol_from_barchart(
            SymbolConfig("MSFT", "https://example.test/msft"),
            captured_at=datetime(2026, 6, 2, 21, 30),
            archive_dir=tmp_path,
        )

    message = str(exc_info.value)
    assert "missing expiration table" in message
    assert "content capture broke" in message
