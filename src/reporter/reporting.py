from __future__ import annotations

import csv
from datetime import datetime
from html import escape
from pathlib import Path

from reporter.models import ReportBundle, Signal, SymbolReport


_REPORT_STYLE = """
<style>
  body { margin: 0; background: #f5f7fb; color: #1f2937; font-family: Arial, Helvetica, sans-serif; line-height: 1.45; }
  .report-shell { max-width: 1180px; margin: 0 auto; padding: 28px 18px 40px; }
  .report-header { background: #111827; color: #ffffff; border-radius: 18px; padding: 24px; margin-bottom: 22px; }
  .report-header h1 { margin: 0 0 6px; font-size: 28px; }
  .report-header p { margin: 0; color: #d1d5db; }
  .panel { background: #ffffff; border: 1px solid #d9e2ef; border-radius: 16px; padding: 18px; margin: 18px 0; }
  table { border-collapse: collapse; width: 100%; margin: 12px 0; background: #ffffff; }
  th, td { border: 1px solid #d8e1ee; padding: 9px 10px; text-align: left; vertical-align: top; }
  th { background: #eef4ff; color: #1e3a5f; font-size: 12px; letter-spacing: 0.03em; text-transform: uppercase; }
  .summary-table { overflow: hidden; border-radius: 12px; }
  .symbol-card { background: #ffffff; border: 1px solid #cbd5e1; border-radius: 18px; padding: 20px; margin: 22px 0; }
  .symbol-card__header { display: table; width: 100%; border-bottom: 1px solid #e5e7eb; padding-bottom: 12px; margin-bottom: 14px; }
  .symbol-card__title { display: table-cell; vertical-align: top; }
  .symbol-card__signal { display: table-cell; text-align: right; vertical-align: top; width: 180px; }
  .symbol-card h2 { margin: 0; font-size: 24px; }
  .symbol-card h3 { margin: 22px 0 8px; color: #243b53; }
  .kpi-grid { margin: 14px 0; }
  .kpi-card { display: inline-block; vertical-align: top; width: 160px; min-height: 54px; border: 1px solid #d8e1ee; border-radius: 14px; padding: 12px; margin: 0 8px 8px 0; background: #f8fbff; }
  .kpi-card__label { color: #64748b; font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; }
  .kpi-card__value { margin-top: 4px; font-size: 18px; font-weight: 700; color: #0f172a; }
  .signal-badge { display: inline-block; border-radius: 999px; padding: 4px 10px; font-size: 12px; font-weight: 700; white-space: nowrap; }
  .signal-badge--bullish { background: #dcfce7; color: #166534; }
  .signal-badge--mixed { background: #fef3c7; color: #92400e; }
  .signal-badge--bearish { background: #fee2e2; color: #991b1b; }
  .signal-badge--failed { background: #e5e7eb; color: #374151; }
  .drift-table td:last-child { color: #334155; }
  .raw-data-panel { border: 1px solid #cbd5e1; border-radius: 14px; background: #fbfdff; padding: 14px; margin-top: 12px; overflow-x: auto; }
  .raw-options-table { min-width: 980px; font-size: 13px; }
  .csv-link { font-weight: 700; }
  .muted { color: #64748b; }
</style>
""".strip()


def _format_number(value: int) -> str:
    return f"{value:,}"


def _format_value(value: object | None) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return _format_number(value)
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _html_value(value: object | None) -> str:
    return escape(_format_value(value))


def _signal_class(signal: Signal | None) -> str:
    if signal in {Signal.STRONG_BULLISH, Signal.BULLISH}:
        return "bullish"
    if signal is Signal.BEARISH_HEDGING:
        return "bearish"
    if signal in {Signal.NEUTRAL, Signal.MIXED, Signal.MIXED_CAUTION}:
        return "mixed"
    return "failed"


def _signal_badge(label: str, signal: Signal | None = None) -> str:
    return f'<span class="signal-badge signal-badge--{_signal_class(signal)}">{escape(label)}</span>'


def _source_label(report: SymbolReport) -> str:
    if report.snapshot is None:
        return "—"
    source = report.snapshot.data_source
    suffix = " (fallback)" if source.is_fallback else ""
    return f"{source.name}{suffix}"


def _source_html(report: SymbolReport) -> str:
    if report.snapshot is None:
        return "—"
    source = report.snapshot.data_source
    label = _source_label(report)
    linked_label = (
        f'<a href="{escape(source.url, quote=True)}">{escape(label)}</a>'
        if source.url
        else escape(label)
    )
    note = f" — {escape(source.note)}" if source.note else ""
    return f"Data source: {linked_label}{note}"


def _source_markdown(report: SymbolReport) -> list[str]:
    if report.snapshot is None:
        return ["No data source available."]
    source = report.snapshot.data_source
    rows = [
        f"- Name: {source.name}",
        f"- URL: {source.url}",
        f"- Fallback: {'Yes' if source.is_fallback else 'No'}",
    ]
    if source.note:
        rows.append(f"- Note: {source.note}")
    return rows


def _primary_signal(report: SymbolReport) -> Signal | None:
    if report.analysis and report.analysis.monthly_signals:
        return report.analysis.monthly_signals[0].signal
    return None


def _metrics_html(report: SymbolReport) -> str:
    if report.snapshot is None:
        return '<p class="muted">No metrics available.</p>'
    metrics = report.snapshot.metrics
    cards = [
        ("Latest Earnings", metrics.latest_earnings),
        ("IV", metrics.implied_volatility),
        ("Historic Vol", metrics.historic_volatility),
        ("IV Rank", metrics.iv_rank),
        ("IV Percentile", metrics.iv_percentile),
    ]
    parts = ['<div class="kpi-grid">']
    for label, value in cards:
        parts.append(
            '<div class="kpi-card">'
            f'<div class="kpi-card__label">{escape(label)}</div>'
            f'<div class="kpi-card__value">{_html_value(value)}</div>'
            '</div>'
        )
    parts.append("</div>")
    return "\n".join(parts)


def _monthly_html(report: SymbolReport) -> str:
    if report.analysis is None or not report.analysis.monthly_signals:
        return '<p class="muted">No monthly signals available.</p>'
    rows = [
        "<table><tr><th>Month</th><th>Expiration</th><th>Put/Call Vol</th><th>Put/Call OI</th><th>Total Vol</th><th>Total OI</th><th>Signal</th></tr>"
    ]
    for item in report.analysis.monthly_signals:
        rows.append(
            "<tr>"
            f"<td>{escape(item.month)}</td><td>{escape(item.expiration_label)}</td>"
            f"<td>{item.put_call_volume_ratio:.2f}</td><td>{item.put_call_open_interest_ratio:.2f}</td>"
            f"<td>{_format_number(item.total_volume)}</td><td>{_format_number(item.total_open_interest)}</td>"
            f"<td>{_signal_badge(item.signal.value, item.signal)}</td>"
            "</tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)


def _drift_html(report: SymbolReport) -> str:
    if not report.drift:
        return '<p class="muted">No drift comparisons available.</p>'
    parts = ["<table class=\"drift-table\"><tr><th>Period</th><th>Summary</th><th>Signal Flips</th></tr>"]
    for item in report.drift:
        flips = "; ".join(item.signal_flips) if item.signal_flips else "—"
        parts.append(
            "<tr>"
            f"<td><strong>{escape(item.period)}</strong></td>"
            f"<td>{escape(item.summary)}</td>"
            f"<td>{escape(flips)}</td>"
            "</tr>"
        )
    parts.append("</table>")
    return "\n".join(parts)


def _metric_text(value: object | None) -> str:
    return _format_value(value)


def _metrics_markdown(report: SymbolReport) -> list[str]:
    if report.snapshot is None:
        return ["No metrics available."]
    metrics = report.snapshot.metrics
    return [
        "| Latest Earnings | IV | Historic Vol | IV Rank | IV Percentile |",
        "| --- | ---: | ---: | ---: | ---: |",
        "| "
        f"{_metric_text(metrics.latest_earnings)} | "
        f"{_metric_text(metrics.implied_volatility)} | "
        f"{_metric_text(metrics.historic_volatility)} | "
        f"{_metric_text(metrics.iv_rank)} | "
        f"{_metric_text(metrics.iv_percentile)} |",
    ]


def _monthly_markdown(report: SymbolReport) -> list[str]:
    if report.analysis is None or not report.analysis.monthly_signals:
        return ["No monthly signals available."]
    rows = [
        "| Month | Expiration | Put/Call Vol | Put/Call OI | Total Vol | Total OI | Signal |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in report.analysis.monthly_signals:
        rows.append(
            "| "
            f"{item.month} | {item.expiration_label} | "
            f"{item.put_call_volume_ratio:.2f} | {item.put_call_open_interest_ratio:.2f} | "
            f"{_format_number(item.total_volume)} | {_format_number(item.total_open_interest)} | {item.signal.value} |"
        )
    return rows


def _drift_markdown(report: SymbolReport) -> list[str]:
    if not report.drift:
        return ["No drift comparisons available."]
    rows = []
    for item in report.drift:
        flips = "; ".join(item.signal_flips)
        suffix = f" Signal flips: {flips}" if flips else ""
        rows.append(f"- **{item.period}**: {item.summary}{suffix}")
    return rows


def _raw_rows_html(report: SymbolReport) -> str:
    if report.snapshot is None or not report.snapshot.rows:
        return '<p class="muted">No raw expiration rows available.</p>'
    rows = [
        '<div class="raw-data-panel">'
        '<table class="raw-options-table"><tr><th>Expiration</th><th>DTE</th><th>Put Vol</th><th>Call Vol</th><th>Total Vol</th>'
        '<th>Put/Call Vol</th><th>Put OI</th><th>Call OI</th><th>Total OI</th><th>Put/Call OI</th>'
        '<th>Implied Volatility</th><th>Monthly</th></tr>'
    ]
    for row in report.snapshot.rows:
        rows.append(
            "<tr>"
            f"<td>{escape(row.expiration_label)}</td><td>{row.dte}</td><td>{_format_number(row.put_volume)}</td>"
            f"<td>{_format_number(row.call_volume)}</td><td>{_format_number(row.total_volume)}</td><td>{row.put_call_volume_ratio:.2f}</td>"
            f"<td>{_format_number(row.put_open_interest)}</td><td>{_format_number(row.call_open_interest)}</td><td>{_format_number(row.total_open_interest)}</td>"
            f"<td>{row.put_call_open_interest_ratio:.2f}</td><td>{_html_value(row.implied_volatility)}</td>"
            f"<td>{_html_value(row.is_monthly)}</td>"
            "</tr>"
        )
    rows.append("</table></div>")
    return "\n".join(rows)


def _raw_rows_markdown(report: SymbolReport) -> list[str]:
    if report.snapshot is None or not report.snapshot.rows:
        return ["No raw expiration rows available."]
    rows = [
        "| Expiration | DTE | Put Vol | Call Vol | Total Vol | Put/Call Vol | Put OI | Call OI | Total OI | Put/Call OI | Implied Volatility | Monthly |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in report.snapshot.rows:
        rows.append(
            "| "
            f"{row.expiration_label} | {row.dte} | {_format_number(row.put_volume)} | {_format_number(row.call_volume)} | {_format_number(row.total_volume)} | "
            f"{row.put_call_volume_ratio:.2f} | {_format_number(row.put_open_interest)} | {_format_number(row.call_open_interest)} | "
            f"{_format_number(row.total_open_interest)} | {row.put_call_open_interest_ratio:.2f} | "
            f"{_metric_text(row.implied_volatility)} | {row.is_monthly} |"
        )
    return rows


def _raw_csv(report: SymbolReport, archive_dir: Path) -> Path | None:
    if report.snapshot is None:
        return None
    path = archive_dir / f"{report.symbol}-expirations.csv"
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            "expiration_label",
            "expiration_date",
            "dte",
            "put_volume",
            "call_volume",
            "total_volume",
            "put_call_volume_ratio",
            "put_open_interest",
            "call_open_interest",
            "total_open_interest",
            "put_call_open_interest_ratio",
            "implied_volatility",
            "is_monthly",
            "data_source_name",
            "data_source_url",
            "data_source_is_fallback",
            "data_source_note",
        ])
        source = report.snapshot.data_source
        for row in report.snapshot.rows:
            writer.writerow([
                row.expiration_label,
                row.expiration_date.isoformat(),
                row.dte,
                row.put_volume,
                row.call_volume,
                row.total_volume,
                row.put_call_volume_ratio,
                row.put_open_interest,
                row.call_open_interest,
                row.total_open_interest,
                row.put_call_open_interest_ratio,
                row.implied_volatility,
                row.is_monthly,
                source.name,
                source.url,
                source.is_fallback,
                source.note or "",
            ])
    return path


def _summary_table_html(symbol_reports: list[SymbolReport], csv_paths: dict[str, Path]) -> str:
    rows = [
        '<table class="summary-table"><tr><th>Symbol</th><th>Status</th><th>Signal</th><th>Source</th><th>Details</th><th>Raw CSV</th></tr>'
    ]
    for report in symbol_reports:
        symbol = escape(report.symbol)
        if report.error:
            rows.append(
                "<tr>"
                f"<td><strong>{symbol}</strong></td><td>{_signal_badge('Failed', Signal.FAILED)}</td>"
                f"<td>{_signal_badge('Unavailable')}</td><td>—</td><td>{escape(report.error)}</td><td>—</td>"
                "</tr>"
            )
            continue
        signal = _primary_signal(report)
        signal_label = signal.value if signal is not None else "Unavailable"
        csv_name = csv_paths[report.symbol].name if report.symbol in csv_paths else ""
        csv_link = f'<a class="csv-link" href="{escape(csv_name)}">{escape(csv_name)}</a>' if csv_name else "—"
        commentary = report.analysis.commentary if report.analysis else "No commentary available."
        rows.append(
            "<tr>"
            f"<td><strong>{symbol}</strong></td><td>{_signal_badge('Success', Signal.BULLISH)}</td>"
            f"<td>{_signal_badge(signal_label, signal)}</td><td>{escape(_source_label(report))}</td>"
            f"<td>{escape(commentary)}</td><td>{csv_link}</td>"
            "</tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)


def _failure_html(failures: list[SymbolReport]) -> str:
    if not failures:
        return ""
    parts = ['<div class="panel"><h2>Failures</h2><ul>']
    for failure in failures:
        parts.append(f"<li>{escape(failure.symbol)}: {escape(failure.error or '')}</li>")
    parts.append("</ul></div>")
    return "\n".join(parts)


def _symbol_card_html(report: SymbolReport, csv_path: Path | None) -> str:
    symbol = escape(report.symbol)
    if report.error:
        return (
            '<section class="symbol-card">'
            '<div class="symbol-card__header">'
            f'<div class="symbol-card__title"><h2>{symbol}</h2><p><strong>Failed:</strong> {escape(report.error)}</p></div>'
            f'<div class="symbol-card__signal">{_signal_badge("Failed", Signal.FAILED)}</div>'
            "</div></section>"
        )
    signal = _primary_signal(report)
    signal_label = signal.value if signal is not None else "Unavailable"
    csv_link = ""
    if csv_path is not None:
        csv_ref = escape(csv_path.name)
        csv_link = f'<p>Raw CSV: <a class="csv-link" href="{csv_ref}">{csv_ref}</a></p>'
    commentary = report.analysis.commentary if report.analysis else ""
    return "\n".join([
        '<section class="symbol-card">',
        '<div class="symbol-card__header">',
        f'<div class="symbol-card__title"><h2>{symbol}</h2><p>{escape(commentary)}</p><p>{_source_html(report)}</p>{csv_link}</div>',
        f'<div class="symbol-card__signal">{_signal_badge(signal_label, signal)}</div>',
        "</div>",
        "<h3>Metrics</h3>",
        _metrics_html(report),
        "<h3>Monthly Signals</h3>",
        _monthly_html(report),
        "<h3>Drift</h3>",
        _drift_html(report),
        "<h3>Raw Options Table</h3>",
        _raw_rows_html(report),
        "</section>",
    ])


def render_reports(generated_at: datetime, symbol_reports: list[SymbolReport], archive_dir: Path) -> ReportBundle:
    archive_dir.mkdir(parents=True, exist_ok=True)
    title = f"Daily Options Put/Call Report - {generated_at:%Y-%m-%d}"
    failures = [report for report in symbol_reports if report.error]
    successes = [report for report in symbol_reports if not report.error]
    csv_paths = {report.symbol: path for report in successes if (path := _raw_csv(report, archive_dir)) is not None}

    html_sections = [
        "<!DOCTYPE html>",
        f'<html lang="en"><head><meta charset="utf-8"><title>{escape(title)}</title>{_REPORT_STYLE}</head><body>',
        '<main class="report-shell">',
        '<div class="report-header">',
        f"<h1>{escape(title)}</h1>",
        f'<p>Generated {escape(generated_at.strftime("%Y-%m-%d %H:%M"))}</p>',
        "</div>",
        '<div class="panel"><h2>All-symbol summary</h2>',
        _summary_table_html(symbol_reports, csv_paths),
        "</div>",
    ]
    markdown_sections = [f"# {title}", ""]

    if symbol_reports and not successes:
        all_failed_message = "No usable symbol data was collected for this run. All configured symbols failed."
        html_sections.append(f'<div class="panel"><p><strong>{all_failed_message}</strong></p></div>')
        markdown_sections.extend([f"**{all_failed_message}**", ""])

    failure_block = _failure_html(failures)
    if failure_block:
        html_sections.append(failure_block)
        markdown_sections.extend(["## Failures", ""])
        for failure in failures:
            markdown_sections.append(f"- {failure.symbol}: {failure.error or ''}")
        markdown_sections.append("")

    for report in symbol_reports:
        csv_path = csv_paths.get(report.symbol)
        html_sections.append(_symbol_card_html(report, csv_path))
        if report.error:
            markdown_sections.extend([f"## {report.symbol}", f"Failed: {report.error}", ""])
            continue
        markdown_sections.extend([f"## {report.symbol}", "", "### Data Source"])
        markdown_sections.extend(_source_markdown(report))
        markdown_sections.extend(["", "### Metrics"])
        markdown_sections.extend(_metrics_markdown(report))
        markdown_sections.extend(["", "### Commentary", report.analysis.commentary if report.analysis else ""])
        markdown_sections.extend(["", "### Monthly Signals"])
        markdown_sections.extend(_monthly_markdown(report))
        markdown_sections.extend(["", "### Drift"])
        markdown_sections.extend(_drift_markdown(report))
        markdown_sections.extend(["", "### Raw Options Table"])
        markdown_sections.extend(_raw_rows_markdown(report))
        if csv_path is not None:
            markdown_sections.extend(["", f"Raw CSV: {csv_path}"])
        markdown_sections.append("")

    html_sections.append(f'<div class="panel"><h2>Archive</h2><p>Archive: {escape(str(archive_dir))}</p></div>')
    html_sections.append("</main></body></html>")
    markdown_sections.extend(["## Archive", "", f"Archive: {archive_dir}", ""])

    markdown_path = archive_dir / "report.md"
    html_path = archive_dir / "report.html"
    markdown_path.write_text("\n".join(markdown_sections), encoding="utf-8")
    html_path.write_text("\n".join(html_sections), encoding="utf-8")
    return ReportBundle(
        generated_at=generated_at,
        symbol_reports=symbol_reports,
        archive_dir=archive_dir,
        markdown_path=markdown_path,
        html_path=html_path,
    )
