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


def test_render_reports_writes_markdown_html_and_csv(tmp_path: Path) -> None:
    snapshot = Snapshot(
        symbol="NOW",
        url="https://www.barchart.com/stocks/quotes/now/put-call-ratios",
        captured_at=datetime(2026, 6, 2, 21, 30),
        metrics=TopMetrics("07/22/26", 30.86, 37.28, 29.62, 39.0),
        rows=[
            ExpirationRow("06/18/26 (m)", date(2026, 6, 18), 16, 11737, 26979, 38716, 0.44, 202821, 226097, 428918, 0.90, 31.92, True)
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
    markdown = bundle.markdown_path.read_text(encoding="utf-8")
    assert "# Daily Options Put/Call Report - 2026-06-02" in markdown
    assert "NOW: mixed overall." in markdown
    csv_text = csv_path.read_text(encoding="utf-8")
    assert csv_text.startswith("expiration_label,")
    assert "06/18/26 (m)" in csv_text


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
    assert "Failed: fetch timed out" in markdown
    assert not (tmp_path / "ERR-expirations.csv").exists()
