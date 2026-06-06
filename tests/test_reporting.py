import csv
import re
from datetime import date, datetime
from pathlib import Path

from reporter.models import (
    DataSource,
    DriftItem,
    ExpirationRow,
    MonthlySignal,
    ReportBundle,
    Signal,
    Snapshot,
    SymbolAnalysis,
    SymbolReport,
    TopMetrics,
)
from reporter.reporting import render_reports


def _snapshot_for_layout(
    symbol: str,
    captured_at: datetime,
    monthly_signal: Signal,
    commentary: str,
    data_source: DataSource | None = None,
) -> tuple[Snapshot, SymbolAnalysis]:
    if symbol == "NOW":
        metrics = TopMetrics("07/22/26", 30.86, 37.28, 29.62, 39.0)
        rows = [
            ExpirationRow("06/18/26 (m)", date(2026, 6, 18), 16, 11737, 26979, 38716, 0.44, 202821, 226097, 428918, 0.90, 31.92, True),
            ExpirationRow("06/26/26 (w)", date(2026, 6, 26), 24, 9104, 19646, 28750, 0.46, 84120, 156882, 241002, 0.54, 32.10, False),
        ]
        monthly_signals = [
            MonthlySignal("2026-06", "06/18/26 (m)", 0.44, 0.90, 438716, 528918, monthly_signal),
            MonthlySignal("2026-07", "07/17/26 (m)", 0.61, 1.34, 1234567, 7654321, Signal.MIXED),
        ]
    else:
        metrics = TopMetrics("08/01/26", 22.45, 28.75, 18.25, 64.0)
        rows = [
            ExpirationRow("07/17/26 (m)", date(2026, 7, 17), 45, 3444444, 4555555, 7999999, 1.72, 611111, 722222, 1333333, 1.88, 44.44, True),
            ExpirationRow("07/24/26 (w)", date(2026, 7, 24), 52, 55555, 66666, 122221, 0.83, 77777, 88888, 166665, 0.88, 45.55, False),
        ]
        monthly_signals = [
            MonthlySignal("2026-07", "07/17/26 (m)", 1.72, 1.88, 8111111, 1444444, monthly_signal),
            MonthlySignal("2026-08", "08/21/26 (m)", 0.77, 1.11, 654321, 987654, Signal.MIXED_CAUTION),
        ]
    snapshot = Snapshot(
        symbol=symbol,
        url=f"https://www.barchart.com/stocks/quotes/{symbol.lower()}/put-call-ratios",
        captured_at=captured_at,
        metrics=metrics,
        rows=rows,
        **({"data_source": data_source} if data_source is not None else {}),
    )
    analysis = SymbolAnalysis(
        symbol=symbol,
        captured_at=captured_at,
        metrics=snapshot.metrics,
        monthly_signals=monthly_signals,
        commentary=commentary,
    )
    return snapshot, analysis


def _successful_symbol_report_with_source(
    symbol: str,
    monthly_signal: Signal,
    commentary: str,
    data_source: DataSource | None = None,
) -> SymbolReport:
    captured_at = datetime(2026, 6, 2, 21, 30)
    snapshot, analysis = _snapshot_for_layout(
        symbol,
        captured_at,
        monthly_signal,
        commentary,
        data_source,
    )
    return SymbolReport(symbol=symbol, snapshot=snapshot, analysis=analysis, drift=[])


def _successful_symbol_report(symbol: str, monthly_signal: Signal, commentary: str) -> SymbolReport:
    captured_at = datetime(2026, 6, 2, 21, 30)
    snapshot, analysis = _snapshot_for_layout(symbol, captured_at, monthly_signal, commentary)
    if symbol == "NOW":
        drift = DriftItem(
            "previous_day",
            "NOW drift summary: front-month call demand cooled while July open interest stayed elevated.",
            signal_flips=["2026-07: Bullish -> Mixed / caution"],
        )
    else:
        drift = DriftItem(
            "previous_day",
            "META drift summary: bearish monthly hedging accelerated as total volume spiked.",
            signal_flips=["2026-07: Neutral -> Bearish / hedging-heavy"],
        )
    return SymbolReport(
        symbol=symbol,
        snapshot=snapshot,
        analysis=analysis,
        drift=[drift],
    )


def _assert_has_class(html: str, class_name: str) -> None:
    assert re.search(rf'class="[^"]*\b{re.escape(class_name)}\b[^"]*"', html), f"missing class {class_name}"


def _extract_element_by_class(html: str, tag: str, class_name: str) -> str:
    pattern = (
        rf'<{tag}\b[^>]*class="[^"]*\b{re.escape(class_name)}\b[^"]*"[^>]*>'
        rf'.*?</{tag}>'
    )
    match = re.search(pattern, html, flags=re.DOTALL)
    assert match, f"missing {tag}.{class_name}"
    return match.group(0)


def _extract_summary_rows(summary_table: str) -> list[str]:
    rows = re.findall(r"<tr\b[^>]*>.*?</tr>", summary_table, flags=re.DOTALL)
    assert rows, "summary table has no rows"
    return rows


def _row_containing(rows: list[str], value: str) -> str:
    matches = [row for row in rows if value in row]
    assert len(matches) == 1, f"expected exactly one row containing {value!r}, found {len(matches)}"
    return matches[0]


def _html_row_containing(block: str, value: str) -> str:
    rows = re.findall(r"<tr\b[^>]*>.*?</tr>", block, flags=re.DOTALL)
    return _row_containing(rows, value)


def _assert_html_row_contains(block: str, row_marker: str, expected_values: list[str]) -> None:
    _assert_contains_all(_html_row_containing(block, row_marker), expected_values)


def _html_first_row_containing(block: str, value: str) -> str:
    rows = re.findall(r"<tr\b[^>]*>.*?</tr>", block, flags=re.DOTALL)
    matches = [row for row in rows if value in row]
    assert matches, f"expected at least one row containing {value!r}"
    return matches[0]


def _assert_first_html_row_contains(block: str, row_marker: str, expected_values: list[str]) -> None:
    _assert_contains_all(_html_first_row_containing(block, row_marker), expected_values)


def _extract_symbol_detail_block(html: str, symbol: str) -> str:
    card_pattern = (
        r'<section\b[^>]*class="[^"]*\bsymbol-card\b[^"]*"[^>]*>'
        rf"(?:(?!</section>).)*\b{re.escape(symbol)}\b.*?</section>"
    )
    card_match = re.search(card_pattern, html, flags=re.DOTALL)
    if card_match:
        return card_match.group(0)
    heading_match = re.search(rf"<h2>{re.escape(symbol)}</h2>(.*?)(?=<h2>|</body>)", html, flags=re.DOTALL)
    assert heading_match, f"missing detail block for {symbol}"
    return heading_match.group(0)


def _assert_html_link(html: str, href: str, text: str) -> None:
    assert re.search(
        rf'<a\b[^>]*href="{re.escape(href)}"[^>]*>\s*{re.escape(text)}\s*</a>',
        html,
    ), f"missing link {text} -> {href}"


def _extract_markdown_symbol_section(markdown: str, symbol: str) -> str:
    match = re.search(rf"^## {re.escape(symbol)}\n(.*?)(?=^## |\Z)", markdown, flags=re.DOTALL | re.MULTILINE)
    assert match, f"missing markdown section for {symbol}"
    return match.group(0)


def _extract_markdown_failures_section(markdown: str) -> str:
    match = re.search(r"^## Failures\n(.*?)(?=^## |\Z)", markdown, flags=re.DOTALL | re.MULTILINE)
    assert match, "missing markdown failures section"
    return match.group(0)


def _extract_markdown_failure_detail_section(markdown: str, symbol: str) -> str:
    symbol_heading = re.search(rf"^## {re.escape(symbol)}\n", markdown, flags=re.MULTILINE)
    if symbol_heading:
        return _extract_markdown_symbol_section(markdown, symbol)
    return _extract_markdown_failures_section(markdown)


def _markdown_line_containing(section: str, value: str) -> str:
    matches = [line for line in section.splitlines() if value in line]
    assert len(matches) == 1, f"expected exactly one markdown line containing {value!r}, found {len(matches)}"
    return matches[0]


def _assert_markdown_line_contains(section: str, line_marker: str, expected_values: list[str]) -> None:
    _assert_contains_all(_markdown_line_containing(section, line_marker), expected_values)


def _assert_contains_all(output: str, expected_values: list[str]) -> None:
    for expected in expected_values:
        assert expected in output


def _layout_bundle(tmp_path: Path) -> ReportBundle:
    return render_reports(
        generated_at=datetime(2026, 6, 2, 21, 35),
        symbol_reports=[
            _successful_symbol_report("NOW", Signal.BULLISH, "NOW: bullish call demand remains constructive."),
            _successful_symbol_report("META", Signal.BEARISH_HEDGING, "META: bearish hedging remains elevated."),
            SymbolReport(
                symbol="ERR",
                snapshot=None,
                analysis=None,
                drift=[],
                error="fetch timed out",
            ),
        ],
        archive_dir=tmp_path,
    )


def test_render_reports_adds_dashboard_layout_without_losing_details(tmp_path: Path) -> None:
    bundle = _layout_bundle(tmp_path)

    html = bundle.html_path.read_text(encoding="utf-8")
    markdown = bundle.markdown_path.read_text(encoding="utf-8")
    assert "<style" in html
    assert "display: flex" not in html
    assert "display: grid" not in html
    assert "box-shadow" not in html
    _assert_has_class(html, "report-shell")
    _assert_has_class(html, "summary-table")
    _assert_has_class(html, "symbol-card")
    _assert_has_class(html, "kpi-grid")
    _assert_has_class(html, "kpi-card")
    _assert_has_class(html, "signal-badge")
    _assert_has_class(html, "signal-badge--bullish")
    _assert_has_class(html, "signal-badge--mixed")
    _assert_has_class(html, "signal-badge--bearish")
    _assert_has_class(html, "signal-badge--failed")
    _assert_has_class(html, "drift-table")
    _assert_has_class(html, "raw-data-panel")
    _assert_has_class(html, "raw-options-table")
    assert len(re.findall(r'class="[^"]*\bsymbol-card\b[^"]*"', html)) >= 2

    summary_table = _extract_element_by_class(html, "table", "summary-table")
    summary_rows = _extract_summary_rows(summary_table)
    now_summary_row = _row_containing(summary_rows, "NOW")
    meta_summary_row = _row_containing(summary_rows, "META")
    err_summary_row = _row_containing(summary_rows, "ERR")
    _assert_contains_all(now_summary_row, ["NOW", "Success", "Bullish", "NOW-expirations.csv"])
    _assert_contains_all(meta_summary_row, ["META", "Success", "Bearish / hedging-heavy", "META-expirations.csv"])
    _assert_contains_all(err_summary_row, ["ERR", "Failed", "fetch timed out"])
    _assert_html_link(now_summary_row, "NOW-expirations.csv", "NOW-expirations.csv")
    _assert_html_link(meta_summary_row, "META-expirations.csv", "META-expirations.csv")
    assert "META" not in now_summary_row
    assert "NOW" not in meta_summary_row
    assert "expirations.csv" not in err_summary_row
    _assert_contains_all(
        summary_table,
        [
            "NOW",
            "META",
            "ERR",
            "Bullish",
            "Bearish / hedging-heavy",
            "Failed",
            "fetch timed out",
            "NOW-expirations.csv",
            "META-expirations.csv",
        ],
    )
    assert "ERR-expirations.csv" not in summary_table
    assert str(tmp_path) in html

    now_detail = _extract_symbol_detail_block(html, "NOW")
    meta_detail = _extract_symbol_detail_block(html, "META")
    _assert_html_link(now_detail, "NOW-expirations.csv", "NOW-expirations.csv")
    _assert_html_link(meta_detail, "META-expirations.csv", "META-expirations.csv")
    _assert_contains_all(
        now_detail,
        [
            "NOW: bullish call demand remains constructive.",
            "07/22/26",
            "30.86",
            "37.28",
            "29.62",
            "39.00",
            "2026-06",
            "2026-07",
            "Bullish",
            "Mixed",
            "06/18/26 (m)",
            "06/26/26 (w)",
            "16",
            "24",
            "0.44",
            "0.90",
            "0.46",
            "0.54",
            "31.92",
            "32.10",
            "True",
            "False",
            "previous_day",
            "NOW drift summary: front-month call demand cooled while July open interest stayed elevated.",
            "2026-07: Bullish -&gt; Mixed / caution",
            "NOW-expirations.csv",
        ],
    )
    _assert_contains_all(
        meta_detail,
        [
            "META: bearish hedging remains elevated.",
            "08/01/26",
            "22.45",
            "28.75",
            "18.25",
            "64.00",
            "2026-07",
            "2026-08",
            "Bearish / hedging-heavy",
            "Mixed / caution",
            "07/17/26 (m)",
            "07/24/26 (w)",
            "45",
            "52",
            "1.72",
            "1.88",
            "0.83",
            "0.88",
            "44.44",
            "45.55",
            "True",
            "False",
            "previous_day",
            "META drift summary: bearish monthly hedging accelerated as total volume spiked.",
            "2026-07: Neutral -&gt; Bearish / hedging-heavy",
            "META-expirations.csv",
        ],
    )
    assert "438,716" in _html_first_row_containing(now_detail, "2026-06")
    assert "7,654,321" in _html_first_row_containing(now_detail, "2026-07")
    assert "8,111,111" in _html_first_row_containing(meta_detail, "2026-07")
    assert "1,333,333" in _html_row_containing(meta_detail, "44.44")
    assert "META drift summary" not in now_detail
    assert "NOW drift summary" not in meta_detail
    now_drift_table = _extract_element_by_class(now_detail, "table", "drift-table")
    _assert_contains_all(now_drift_table, ["2026-07: Bullish -&gt; Mixed / caution"])
    assert "&#8209;" not in now_drift_table
    assert now_detail.count("2026-07: Bullish -&gt; Mixed / caution") == 1
    meta_drift_table = _extract_element_by_class(meta_detail, "table", "drift-table")
    _assert_contains_all(meta_drift_table, ["2026-07: Neutral -&gt; Bearish / hedging-heavy"])
    assert "&#8209;" not in meta_drift_table
    assert meta_detail.count("2026-07: Neutral -&gt; Bearish / hedging-heavy") == 1

    _assert_contains_all(
        html,
        [
            "NOW",
            "META",
            "ERR",
            "NOW: bullish call demand remains constructive.",
            "META: bearish hedging remains elevated.",
            "07/22/26",
            "30.86",
            "37.28",
            "29.62",
            "39.00",
            "08/01/26",
            "22.45",
            "28.75",
            "18.25",
            "64.00",
            "2026-06",
            "2026-07",
            "2026-08",
            "Bullish",
            "Mixed",
            "Mixed / caution",
            "Bearish / hedging-heavy",
            "06/18/26 (m)",
            "06/26/26 (w)",
            "07/17/26 (m)",
            "07/24/26 (w)",
            "previous_day",
            "NOW drift summary: front-month call demand cooled while July open interest stayed elevated.",
            "META drift summary: bearish monthly hedging accelerated as total volume spiked.",
            "2026-07: Bullish -&gt; Mixed / caution",
            "2026-07: Neutral -&gt; Bearish / hedging-heavy",
            "fetch timed out",
        ],
    )

    now_markdown = _extract_markdown_symbol_section(markdown, "NOW")
    meta_markdown = _extract_markdown_symbol_section(markdown, "META")
    err_markdown = _extract_markdown_failure_detail_section(markdown, "ERR")
    _assert_contains_all(
        now_markdown,
        [
            "## NOW",
            "NOW: bullish call demand remains constructive.",
            "07/22/26",
            "30.86",
            "37.28",
            "29.62",
            "39.00",
            "2026-06 | 06/18/26 (m) | 0.44 | 0.90 | 438,716 | 528,918 | Bullish |",
            "2026-07 | 07/17/26 (m) | 0.61 | 1.34 | 1,234,567 | 7,654,321 | Mixed |",
            "- **previous_day**: NOW drift summary: front-month call demand cooled while July open interest stayed elevated. Signal flips: 2026-07: Bullish -> Mixed / caution",
            "2026-07: Bullish -> Mixed / caution",
            "06/18/26 (m)",
            "06/26/26 (w)",
            "16 | 11,737 | 26,979 | 38,716 | 0.44",
            "24 | 9,104 | 19,646 | 28,750 | 0.46",
            "31.92 | True",
            "32.10 | False",
            "NOW-expirations.csv",
        ],
    )
    _assert_contains_all(
        meta_markdown,
        [
            "## META",
            "META: bearish hedging remains elevated.",
            "08/01/26",
            "22.45",
            "28.75",
            "18.25",
            "64.00",
            "2026-07 | 07/17/26 (m) | 1.72 | 1.88 | 8,111,111 | 1,444,444 | Bearish / hedging-heavy |",
            "2026-08 | 08/21/26 (m) | 0.77 | 1.11 | 654,321 | 987,654 | Mixed / caution |",
            "Bearish / hedging-heavy",
            "- **previous_day**: META drift summary: bearish monthly hedging accelerated as total volume spiked. Signal flips: 2026-07: Neutral -> Bearish / hedging-heavy",
            "2026-07: Neutral -> Bearish / hedging-heavy",
            "07/17/26 (m)",
            "07/24/26 (w)",
            "45 | 3,444,444 | 4,555,555 | 7,999,999 | 1.72",
            "52 | 55,555 | 66,666 | 122,221 | 0.83",
            "44.44 | True",
            "45.55 | False",
            "META-expirations.csv",
        ],
    )
    _assert_contains_all(err_markdown, ["ERR", "fetch timed out"])
    assert "META drift summary" not in now_markdown
    assert "META-expirations.csv" not in now_markdown
    assert "NOW drift summary" not in meta_markdown
    assert "NOW-expirations.csv" not in meta_markdown

    _assert_contains_all(
        markdown,
        [
            "## NOW",
            "## META",
            "## ERR",
            "NOW: bullish call demand remains constructive.",
            "META: bearish hedging remains elevated.",
            "ERR: fetch timed out",
            "Failed: fetch timed out",
            "- **previous_day**: NOW drift summary: front-month call demand cooled while July open interest stayed elevated. Signal flips: 2026-07: Bullish -> Mixed / caution",
            "- **previous_day**: META drift summary: bearish monthly hedging accelerated as total volume spiked. Signal flips: 2026-07: Neutral -> Bearish / hedging-heavy",
            "2026-07: Bullish -> Mixed / caution",
            "2026-07: Neutral -> Bearish / hedging-heavy",
            "06/18/26 (m)",
            "06/26/26 (w)",
            "07/17/26 (m)",
            "07/24/26 (w)",
            "2026-06 | 06/18/26 (m) | 0.44 | 0.90 | 438,716 | 528,918 | Bullish |",
            "2026-07 | 07/17/26 (m) | 0.61 | 1.34 | 1,234,567 | 7,654,321 | Mixed |",
            "2026-07 | 07/17/26 (m) | 1.72 | 1.88 | 8,111,111 | 1,444,444 | Bearish / hedging-heavy |",
            "2026-08 | 08/21/26 (m) | 0.77 | 1.11 | 654,321 | 987,654 | Mixed / caution |",
            "07/22/26",
            "30.86",
            "37.28",
            "29.62",
            "39.00",
            "08/01/26",
            "22.45",
            "28.75",
            "18.25",
            "64.00",
            "16 | 11,737 | 26,979 | 38,716 | 0.44",
            "24 | 9,104 | 19,646 | 28,750 | 0.46",
            "45 | 3,444,444 | 4,555,555 | 7,999,999 | 1.72",
            "52 | 55,555 | 66,666 | 122,221 | 0.83",
            "31.92 | True",
            "32.10 | False",
            "44.44 | True",
            "45.55 | False",
            "NOW-expirations.csv",
            "META-expirations.csv",
        ],
    )
    assert str(tmp_path) in markdown


def test_render_reports_comma_formats_large_human_facing_numbers(tmp_path: Path) -> None:
    bundle = _layout_bundle(tmp_path)

    html = bundle.html_path.read_text(encoding="utf-8")
    markdown = bundle.markdown_path.read_text(encoding="utf-8")
    now_detail = _extract_symbol_detail_block(html, "NOW")
    meta_detail = _extract_symbol_detail_block(html, "META")

    _assert_first_html_row_contains(now_detail, "2026-06", ["438,716", "528,918"])
    _assert_first_html_row_contains(now_detail, "2026-07", ["1,234,567", "7,654,321"])
    _assert_html_row_contains(
        now_detail,
        "31.92",
        ["11,737", "26,979", "38,716", "202,821", "226,097", "428,918"],
    )
    _assert_html_row_contains(
        now_detail,
        "32.10",
        ["9,104", "19,646", "28,750", "84,120", "156,882", "241,002"],
    )
    _assert_first_html_row_contains(meta_detail, "2026-07", ["8,111,111", "1,444,444"])
    _assert_first_html_row_contains(meta_detail, "2026-08", ["654,321", "987,654"])
    _assert_html_row_contains(
        meta_detail,
        "44.44",
        ["3,444,444", "4,555,555", "7,999,999", "611,111", "722,222", "1,333,333"],
    )
    _assert_html_row_contains(
        meta_detail,
        "45.55",
        ["55,555", "66,666", "122,221", "77,777", "88,888", "166,665"],
    )

    now_markdown = _extract_markdown_symbol_section(markdown, "NOW")
    meta_markdown = _extract_markdown_symbol_section(markdown, "META")
    _assert_markdown_line_contains(now_markdown, "2026-06 |", ["438,716", "528,918"])
    _assert_markdown_line_contains(now_markdown, "2026-07 |", ["1,234,567", "7,654,321"])
    _assert_markdown_line_contains(
        now_markdown,
        "31.92 | True",
        ["11,737", "26,979", "38,716", "202,821", "226,097", "428,918"],
    )
    _assert_markdown_line_contains(
        now_markdown,
        "32.10 | False",
        ["9,104", "19,646", "28,750", "84,120", "156,882", "241,002"],
    )
    _assert_markdown_line_contains(meta_markdown, "2026-07 |", ["8,111,111", "1,444,444"])
    _assert_markdown_line_contains(meta_markdown, "2026-08 |", ["654,321", "987,654"])
    _assert_markdown_line_contains(
        meta_markdown,
        "44.44 | True",
        ["3,444,444", "4,555,555", "7,999,999", "611,111", "722,222", "1,333,333"],
    )
    _assert_markdown_line_contains(
        meta_markdown,
        "45.55 | False",
        ["55,555", "66,666", "122,221", "77,777", "88,888", "166,665"],
    )


def test_render_reports_writes_markdown_html_and_csv(tmp_path: Path) -> None:
    snapshot = Snapshot(
        symbol="NOW",
        url="https://www.barchart.com/stocks/quotes/now/put-call-ratios",
        captured_at=datetime(2026, 6, 2, 21, 30),
        metrics=TopMetrics("07/22/26", 30.86, 37.28, 29.62, 39.0),
        rows=[
            ExpirationRow("06/18/26 (m)", date(2026, 6, 18), 16, 11737, 26979, 38716, 0.44, 202821, 226097, 428918, 0.90, 31.92, True),
            ExpirationRow("06/26/26 (w)", date(2026, 6, 26), 24, 9104, 19646, 28750, 0.46, 84120, 156882, 241002, 0.54, 32.10, False),
        ],
    )
    analysis = SymbolAnalysis(
        symbol="NOW",
        captured_at=snapshot.captured_at,
        metrics=snapshot.metrics,
        monthly_signals=[
            MonthlySignal("2026-06", "06/18/26 (m)", 0.44, 0.90, 38716, 428918, Signal.MIXED)
        ],
        commentary="NOW: mixed overall.",
    )
    bundle = render_reports(
        generated_at=datetime(2026, 6, 2, 21, 35),
        symbol_reports=[
            SymbolReport(
                symbol="NOW",
                snapshot=snapshot,
                analysis=analysis,
                drift=[DriftItem("previous_day", "No previous_day snapshot is available yet.")],
            )
        ],
        archive_dir=tmp_path,
    )

    assert isinstance(bundle, ReportBundle)
    assert bundle.markdown_path.exists()
    assert bundle.html_path.exists()
    csv_path = tmp_path / "NOW-expirations.csv"
    assert csv_path.exists()
    html = bundle.html_path.read_text(encoding="utf-8")
    assert '<meta charset="utf-8">' in html
    assert "NOW" in html
    assert "06/18/26 (m)" in html
    assert "Mixed" in html
    assert "NOW-expirations.csv" in html
    assert "Raw Options Table" in html
    assert "06/26/26 (w)" in html
    markdown = bundle.markdown_path.read_text(encoding="utf-8")
    assert "# Daily Options Put/Call Report - 2026-06-02" in markdown
    assert "NOW: mixed overall." in markdown
    assert "07/22/26" in markdown
    assert "30.86" in markdown
    assert "06/18/26 (m)" in markdown
    assert "Mixed" in markdown
    assert "No previous_day snapshot is available yet." in markdown
    assert "### Raw Options Table" in markdown
    assert "06/26/26 (w)" in markdown
    assert f"Raw CSV: {csv_path}" in markdown
    assert str(tmp_path) in markdown

    with csv_path.open(encoding="utf-8", newline="") as file:
        csv_rows = list(csv.reader(file))
    assert len(csv_rows) == 3
    header = csv_rows[0]
    values = csv_rows[1]
    assert len(header) == len(values)
    csv_values = dict(zip(header, values))
    assert csv_values["expiration_label"] == "06/18/26 (m)"
    assert csv_values["put_call_volume_ratio"] == "0.44"
    assert csv_values["put_call_open_interest_ratio"] == "0.9"
    assert csv_values["is_monthly"] == "True"


def test_render_reports_discloses_data_sources_in_html_markdown_and_csv(tmp_path: Path) -> None:
    fallback_source = DataSource(
        name="yfin.dev",
        url="https://api.yfin.dev/v1/options?symbol=META",
        is_fallback=True,
        note="Fallback after Barchart failed: primary <failed> & timed out",
    )
    bundle = render_reports(
        generated_at=datetime(2026, 6, 2, 21, 35),
        symbol_reports=[
            _successful_symbol_report_with_source(
                "NOW",
                Signal.BULLISH,
                "NOW: bullish call demand remains constructive.",
            ),
            _successful_symbol_report_with_source(
                "META",
                Signal.BEARISH_HEDGING,
                "META: bearish hedging remains elevated.",
                fallback_source,
            ),
            SymbolReport(
                symbol="ERR",
                snapshot=None,
                analysis=None,
                drift=[],
                error="fetch timed out",
            ),
        ],
        archive_dir=tmp_path,
    )

    html = bundle.html_path.read_text(encoding="utf-8")
    summary_table = _extract_element_by_class(html, "table", "summary-table")
    _assert_contains_all(summary_table, ["<th>Source</th>", "Barchart", "yfin.dev (fallback)"])
    err_summary_row = _row_containing(_extract_summary_rows(summary_table), "ERR")
    assert "<td>—</td>" in err_summary_row
    now_detail = _extract_symbol_detail_block(html, "NOW")
    meta_detail = _extract_symbol_detail_block(html, "META")
    _assert_contains_all(now_detail, ["Data source:", "Barchart", "https://www.barchart.com"])
    _assert_contains_all(
        meta_detail,
        [
            "Data source:",
            "yfin.dev (fallback)",
            "https://api.yfin.dev/v1/options?symbol=META",
            "Fallback after Barchart failed: primary &lt;failed&gt; &amp; timed out",
        ],
    )
    assert "primary <failed>" not in html

    markdown = bundle.markdown_path.read_text(encoding="utf-8")
    now_markdown = _extract_markdown_symbol_section(markdown, "NOW")
    meta_markdown = _extract_markdown_symbol_section(markdown, "META")
    _assert_contains_all(
        now_markdown,
        ["### Data Source", "- Name: Barchart", "- URL: https://www.barchart.com", "- Fallback: No"],
    )
    _assert_contains_all(
        meta_markdown,
        [
            "### Data Source",
            "- Name: yfin.dev",
            "- URL: https://api.yfin.dev/v1/options?symbol=META",
            "- Fallback: Yes",
            "- Note: Fallback after Barchart failed: primary <failed> & timed out",
        ],
    )

    with (tmp_path / "META-expirations.csv").open(encoding="utf-8", newline="") as file:
        meta_csv_rows = list(csv.DictReader(file))
    assert meta_csv_rows
    assert meta_csv_rows[0]["data_source_name"] == "yfin.dev"
    assert meta_csv_rows[0]["data_source_url"] == "https://api.yfin.dev/v1/options?symbol=META"
    assert meta_csv_rows[0]["data_source_is_fallback"] == "True"
    assert meta_csv_rows[0]["data_source_note"] == "Fallback after Barchart failed: primary <failed> & timed out"

    with (tmp_path / "NOW-expirations.csv").open(encoding="utf-8", newline="") as file:
        now_csv_rows = list(csv.DictReader(file))
    assert now_csv_rows[0]["data_source_name"] == "Barchart"
    assert now_csv_rows[0]["data_source_url"] == "https://www.barchart.com"
    assert now_csv_rows[0]["data_source_is_fallback"] == "False"
    assert now_csv_rows[0]["data_source_note"] == ""


def test_render_reports_renders_non_http_source_urls_as_plain_escaped_text(tmp_path: Path) -> None:
    evil_source = DataSource(
        name="evil",
        url="javascript:alert(1)",
        is_fallback=True,
        note="bad <note>",
    )
    bundle = render_reports(
        generated_at=datetime(2026, 6, 2, 21, 35),
        symbol_reports=[
            _successful_symbol_report_with_source(
                "META",
                Signal.BEARISH_HEDGING,
                "META: bearish hedging remains elevated.",
                evil_source,
            )
        ],
        archive_dir=tmp_path,
    )

    html = bundle.html_path.read_text(encoding="utf-8")
    meta_detail = _extract_symbol_detail_block(html, "META")
    assert 'href="javascript:alert(1)"' not in meta_detail
    assert "<note>" not in meta_detail
    _assert_contains_all(
        meta_detail,
        [
            "Data source:",
            "evil (fallback)",
            "javascript:alert(1)",
            "bad &lt;note&gt;",
        ],
    )


def test_render_reports_uses_dash_for_missing_metrics(tmp_path: Path) -> None:
    snapshot = Snapshot(
        symbol="EMPTY",
        url="https://www.barchart.com/stocks/quotes/empty/put-call-ratios",
        captured_at=datetime(2026, 6, 2, 21, 30),
        metrics=TopMetrics(None, None, None, None, None),
        rows=[],
    )

    bundle = render_reports(
        generated_at=datetime(2026, 6, 2, 21, 35),
        symbol_reports=[SymbolReport(symbol="EMPTY", snapshot=snapshot, analysis=None, drift=[])],
        archive_dir=tmp_path,
    )

    html = bundle.html_path.read_text(encoding="utf-8")
    assert "None" not in html
    assert "—" in html


def test_render_reports_records_failures_without_csv(tmp_path: Path) -> None:
    bundle = render_reports(
        generated_at=datetime(2026, 6, 2, 21, 35),
        symbol_reports=[
            SymbolReport(
                symbol="ERR",
                snapshot=None,
                analysis=None,
                drift=[],
                error="fetch timed out",
            )
        ],
        archive_dir=tmp_path,
    )

    html = bundle.html_path.read_text(encoding="utf-8")
    markdown = bundle.markdown_path.read_text(encoding="utf-8")
    assert "Failures" in html
    assert "ERR: fetch timed out" in html
    assert "## Failures" in markdown
    assert "ERR: fetch timed out" in markdown
    assert "Failed: fetch timed out" in markdown
    assert not (tmp_path / "ERR-expirations.csv").exists()


def test_render_reports_escapes_dynamic_html_content(tmp_path: Path) -> None:
    bundle = render_reports(
        generated_at=datetime(2026, 6, 2, 21, 35),
        symbol_reports=[
            SymbolReport(
                symbol="XSS",
                snapshot=None,
                analysis=None,
                drift=[],
                error='fetch failed <script>alert("x")</script>',
            )
        ],
        archive_dir=tmp_path,
    )

    html = bundle.html_path.read_text(encoding="utf-8")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
