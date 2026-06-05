import html
import json
import re
from datetime import datetime
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
        content_error: Exception | None = None,
    ) -> None:
        self.html = html
        self.goto_error = goto_error
        self.response_status = response_status
        self.expiration_response_data = expiration_response_data
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
        response = _FakeResponse(200, self.expiration_response_data)
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
        self.closed = True


class _FakeContext:
    def __init__(self, playwright: "_FakePlaywright") -> None:
        self._playwright = playwright
        self.closed = False

    async def new_page(self) -> _FakePage:
        page = self._playwright.new_page()
        self._playwright.pages.append(page)
        return page

    async def close(self) -> None:
        self.closed = True


class _FakeResponse:
    def __init__(self, status: int, data: dict[str, Any] | None = None) -> None:
        self.status = status
        self.url = "https://www.barchart.com/proxies/core-api/v1/options-expirations/get"
        self._data = data if data is not None else _options_expirations_response()

    async def json(self) -> dict[str, Any]:
        return self._data


class _FakeChromium:
    def __init__(self, playwright: "_FakePlaywright") -> None:
        self._playwright = playwright

    async def launch(self, *, headless: bool) -> _FakeBrowser:
        assert headless is True
        self._playwright.launch_count += 1
        browser = _FakeBrowser(self._playwright)
        self._playwright.browsers.append(browser)
        return browser


class _FakePlaywright:
    def __init__(self, page_factory) -> None:
        self._page_factory = page_factory
        self.chromium = _FakeChromium(self)
        self.launch_count = 0
        self.pages: list[_FakePage] = []
        self.browsers: list[_FakeBrowser] = []
        self.contexts: list[_FakeContext] = []
        self.context_user_agents: list[str] = []

    def new_page(self) -> _FakePage:
        return self._page_factory()

    async def __aenter__(self) -> "_FakePlaywright":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
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
    fake_playwright = _FakePlaywright(lambda: _FakePage(html))
    _install_fake_playwright(monkeypatch, fake_playwright)

    snapshot = await collect_symbol(
        SymbolConfig("msft", "https://example.test/msft"),
        captured_at=datetime(2026, 6, 2, 21, 30),
        archive_dir=tmp_path,
    )

    assert snapshot.symbol == "MSFT"
    assert len(snapshot.rows) == 2
    assert (tmp_path / "msft-raw.html").read_text(encoding="utf-8") == html
    raw_json = json.loads((tmp_path / "msft-raw.json").read_text(encoding="utf-8"))
    assert raw_json["symbol"] == "MSFT"
    assert raw_json["rows"][1]["expiration_label"] == "06/26/26 (w)"
    assert fake_playwright.launch_count == 1


@pytest.mark.asyncio
async def test_collect_symbol_uses_realistic_browser_user_agent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    html = _toolbar_html()
    fake_playwright = _FakePlaywright(lambda: _FakePage(html))
    _install_fake_playwright(monkeypatch, fake_playwright)

    await collect_symbol(
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
        await collect_symbol(
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
        await collect_symbol(
            SymbolConfig("MSFT", "https://example.test/msft"),
            captured_at=datetime(2026, 6, 2, 21, 30),
            archive_dir=tmp_path,
        )

    assert "navigation failed" in str(exc_info.value)
    assert page.response_listener_events == ["on", "remove"]


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

    await collect_symbol(
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

    await collect_symbol(
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
        await collect_symbol(
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
        await collect_symbol(
            SymbolConfig("MSFT", "https://example.test/msft"),
            captured_at=datetime(2026, 6, 2, 21, 30),
            archive_dir=tmp_path,
        )

    message = str(exc_info.value)
    assert "missing expiration table" in message
    assert "content capture broke" in message
