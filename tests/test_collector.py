import json
import re
from datetime import datetime
from pathlib import Path

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

    async def inner_text(self) -> str:
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
        content_error: Exception | None = None,
    ) -> None:
        self.html = html
        self.goto_error = goto_error
        self.content_error = content_error
        self.goto_calls: list[dict[str, object]] = []
        self.waited_for_texts: list[tuple[str, int]] = []
        self.waited_for_locators: list[tuple[str, str | None, int]] = []
        self.screenshot_paths: list[Path] = []

    async def goto(self, url: str, *, wait_until: str, timeout: int) -> None:
        self.goto_calls.append({"url": url, "wait_until": wait_until, "timeout": timeout})
        if self.goto_error is not None:
            raise self.goto_error

    def get_by_text(self, text: str) -> _FakeWaitHandle:
        return _FakeWaitHandle(self, text)

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

    async def new_page(self) -> _FakePage:
        page = self._playwright.new_page()
        self._playwright.pages.append(page)
        return page

    async def close(self) -> None:
        self.closed = True


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
    return "\n".join(lines)


def _row_html(html: str) -> list[str]:
    return re.findall(r"<tr>\s*(.*?)\s*</tr>", html, flags=re.DOTALL)


def _cell_texts(html: str) -> list[str]:
    cells = re.findall(r"<t[dh][^>]*>\s*(.*?)\s*</t[dh]>", html, flags=re.DOTALL)
    return [re.sub(r"<[^>]+>", "", cell).strip() for cell in cells]


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
async def test_collect_symbol_writes_raw_artifacts_without_second_browser_launch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    html = FIXTURE_HTML.read_text(encoding="utf-8")
    fake_playwright = _FakePlaywright(lambda: _FakePage(html))
    _install_fake_playwright(monkeypatch, fake_playwright)

    snapshot = await collect_symbol(
        SymbolConfig("msft", "https://example.test/msft"),
        captured_at=datetime(2026, 6, 2, 21, 30),
        archive_dir=tmp_path,
    )

    assert snapshot.symbol == "MSFT"
    assert len(snapshot.rows) == 3
    assert (tmp_path / "msft-raw.html").read_text(encoding="utf-8") == html
    raw_json = json.loads((tmp_path / "msft-raw.json").read_text(encoding="utf-8"))
    assert raw_json["symbol"] == "MSFT"
    assert raw_json["rows"][1]["expiration_label"] == "06/26/26 (w)"
    assert fake_playwright.launch_count == 1


@pytest.mark.asyncio
async def test_collect_symbol_uses_domcontentloaded_then_waits_for_expiration_header(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    html = FIXTURE_HTML.read_text(encoding="utf-8")
    fake_playwright = _FakePlaywright(lambda: _FakePage(html))
    _install_fake_playwright(monkeypatch, fake_playwright)

    await collect_symbol(
        SymbolConfig("msft", "https://example.test/msft"),
        captured_at=datetime(2026, 6, 2, 21, 30),
        archive_dir=tmp_path,
    )

    assert fake_playwright.pages[0].goto_calls[0]["wait_until"] == "domcontentloaded"
    assert fake_playwright.pages[0].waited_for_texts == []
    assert fake_playwright.pages[0].waited_for_locators == [("table th", "Expiration Date", 30000)]


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
