import csv
import re
from datetime import date, datetime
from pathlib import Path

from reporter.models import (
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


def _snapshot_for_layout(symbol: str, captured_at: datetime, monthly_signal: Signal, commentary: str) -> tuple[Snapshot, SymbolAnalysis]:
    if symbol == "NOW":
        metrics = TopMetrics("07/22/26", 30.86, 37.28, 29.62, 39.0)
        rows = [
            ExpirationRow("06/18/26 (m)", date(2026, 6, 18), 16, 11737, 26979, 38716, 0.44, 202821, 226097, 428918, 0.90, 31.92, True),
            ExpirationRow("06/26/26 (w)", date(2026, 6, 26), 24, 9104, 19646, 28750, 0.46, 84120, 156882, 241002, 0.54, 32.10, False),
        ]
        monthly_signals = [
            MonthlySignal("2026-06", "06/18/26 (m)", 0.44, 0.90, 38716, 428918, monthly_signal),
            MonthlySignal("2026-07", "07/17/26 (m)", 0.61, 1.34, 1234567, 7654321, Signal.MIXED),
        ]
    else:
        metrics = TopMetrics("08/01/26", 22.45, 28.75, 18.25, 64.0)
        rows = [
            ExpirationRow("07/17/26 (m)", date(2026, 7, 17), 45, 3333333, 4320988, 7654321, 1.72, 111111, 222222, 333333, 1.88, 44.44, True),
            ExpirationRow("07/24/26 (w)", date(2026, 7, 24), 52, 55555, 66666, 122221, 0.83, 77777, 88888, 166665, 0.88, 45.55, False),
        ]
        monthly_signals = [
            MonthlySignal("2026-07", "07/17/26 (m)", 1.72, 1.88, 7654321, 333333, monthly_signal),
            MonthlySignal("2026-08", "08/21/26 (m)", 0.77, 1.11, 654321, 987654, Signal.MIXED_CAUTION),
        ]
    snapshot = Snapshot(
        symbol=symbol,
        url=f"https://www.barchart.com/stocks/quotes/{symbol.lower()}/put-call-ratios",
        captured_at=captured_at,
        metrics=metrics,
        rows=rows,
    )
    analysis = SymbolAnalysis(
        symbol=symbol,
        captured_at=captured_at,
        metrics=snapshot.metrics,
        monthly_signals=monthly_signals,
        commentary=commentary,
    )
    return snapshot, analysis


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
    assert len(matches) == 1, f"expected exactly one summary row containing {value!r}, found {len(matches)}"
    return matches[0]


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
    _assert_html_link(html, "NOW-expirations.csv", "NOW-expirations.csv")
    _assert_html_link(html, "META-expirations.csv", "META-expirations.csv")
    assert str(tmp_path) in html

    now_detail = _extract_symbol_detail_block(html, "NOW")
    meta_detail = _extract_symbol_detail_block(html, "META")
    _assert_contains_all(
        now_detail,
        [
            "NOW: bullish call demand remains constructive.",
            "07/22/26",
            "30.86",
            "29.62",
            "39.0",
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
            "32.1",
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
            "64.0",
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
    assert "38,716" in now_detail
    assert "7,654,321" in meta_detail
    assert "META drift summary" not in now_detail
    assert "NOW drift summary" not in meta_detail

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
            "39.0",
            "08/01/26",
            "22.45",
            "28.75",
            "18.25",
            "64.0",
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
            "2026-06 | 06/18/26 (m) | 0.44 | 0.90 | 38,716 | 428,918 | Bullish |",
            "2026-07 | 07/17/26 (m) | 0.61 | 1.34 | 1,234,567 | 7,654,321 | Mixed |",
            "2026-07 | 07/17/26 (m) | 1.72 | 1.88 | 7,654,321 | 333,333 | Bearish / hedging-heavy |",
            "2026-08 | 08/21/26 (m) | 0.77 | 1.11 | 654,321 | 987,654 | Mixed / caution |",
            "07/22/26",
            "30.86",
            "37.28",
            "29.62",
            "39.0",
            "08/01/26",
            "22.45",
            "28.75",
            "18.25",
            "64.0",
            "16 | 11,737 | 26,979 | 38,716 | 0.44",
            "24 | 9,104 | 19,646 | 28,750 | 0.46",
            "45 | 3,333,333 | 4,320,988 | 7,654,321 | 1.72",
            "52 | 55,555 | 66,666 | 122,221 | 0.83",
            "31.92 | True",
            "32.1 | False",
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
    formatted_values = [
        "11,737",
        "26,979",
        "202,821",
        "226,097",
        "9,104",
        "19,646",
        "28,750",
        "84,120",
        "156,882",
        "241,002",
        "38,716",
        "428,918",
        "1,234,567",
        "7,654,321",
        "3,333,333",
        "4,320,988",
        "111,111",
        "222,222",
        "333,333",
        "55,555",
        "66,666",
        "122,221",
        "77,777",
        "88,888",
        "166,665",
        "654,321",
        "987,654",
    ]
    unformatted_values = [value.replace(",", "") for value in formatted_values]
    for output in (html, markdown):
        for value in formatted_values:
            assert value in output
        for value in unformatted_values:
            assert value not in output


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
