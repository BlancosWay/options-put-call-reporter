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
    snapshot = Snapshot(
        symbol=symbol,
        url=f"https://www.barchart.com/stocks/quotes/{symbol.lower()}/put-call-ratios",
        captured_at=captured_at,
        metrics=TopMetrics("07/22/26", 30.86, 37.28, 29.62, 39.0),
        rows=[
            ExpirationRow("06/18/26 (m)", date(2026, 6, 18), 16, 11737, 26979, 38716, 0.44, 202821, 226097, 428918, 0.90, 31.92, True),
            ExpirationRow("06/26/26 (w)", date(2026, 6, 26), 24, 9104, 19646, 28750, 0.46, 84120, 156882, 241002, 0.54, 32.10, False),
        ],
    )
    analysis = SymbolAnalysis(
        symbol=symbol,
        captured_at=captured_at,
        metrics=snapshot.metrics,
        monthly_signals=[
            MonthlySignal("2026-06", "06/18/26 (m)", 0.44, 0.90, 38716, 428918, monthly_signal),
            MonthlySignal("2026-07", "07/17/26 (m)", 0.61, 1.34, 1234567, 7654321, Signal.MIXED),
        ],
        commentary=commentary,
    )
    return snapshot, analysis


def _successful_symbol_report(symbol: str, monthly_signal: Signal, commentary: str) -> SymbolReport:
    captured_at = datetime(2026, 6, 2, 21, 30)
    snapshot, analysis = _snapshot_for_layout(symbol, captured_at, monthly_signal, commentary)
    return SymbolReport(
        symbol=symbol,
        snapshot=snapshot,
        analysis=analysis,
        drift=[
            DriftItem(
                "previous_day",
                f"{symbol} drift summary: volume cooled while open interest stayed elevated.",
                signal_flips=["2026-07: Bullish -> Mixed / caution"],
            )
        ],
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
            "2026-06",
            "2026-07",
            "Bullish",
            "Mixed",
            "Bearish / hedging-heavy",
            "06/18/26 (m)",
            "06/26/26 (w)",
            "previous_day",
            "NOW drift summary: volume cooled while open interest stayed elevated.",
            "META drift summary: volume cooled while open interest stayed elevated.",
            "2026-07: Bullish -&gt; Mixed / caution",
            "fetch timed out",
        ],
    )
    _assert_contains_all(
        markdown,
        [
            "## META",
            "## ERR",
            "META: bearish hedging remains elevated.",
            "ERR: fetch timed out",
            "Failed: fetch timed out",
            "2026-07: Bullish -> Mixed / caution",
            "06/18/26 (m)",
            "06/26/26 (w)",
            "2026-06 | 06/18/26 (m) | 0.44 | 0.90",
            "2026-07 | 07/17/26 (m) | 0.61 | 1.34",
            "07/22/26",
            "30.86",
            "37.28",
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
