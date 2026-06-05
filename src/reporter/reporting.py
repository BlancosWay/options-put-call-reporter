from __future__ import annotations

import csv
from datetime import datetime
from html import escape
from pathlib import Path

from reporter.models import ReportBundle, SymbolReport


def _metric_cell(value: object | None) -> str:
    if value is None:
        return "—"
    return escape(str(value))


def _metrics_html(report: SymbolReport) -> str:
    if report.snapshot is None:
        return "<p>No metrics available.</p>"
    metrics = report.snapshot.metrics
    return (
        "<table><tr><th>Latest Earnings</th><th>IV</th><th>Historic Vol</th><th>IV Rank</th><th>IV Percentile</th></tr>"
        f"<tr><td>{_metric_cell(metrics.latest_earnings)}</td>"
        f"<td>{_metric_cell(metrics.implied_volatility)}</td><td>{_metric_cell(metrics.historic_volatility)}</td>"
        f"<td>{_metric_cell(metrics.iv_rank)}</td><td>{_metric_cell(metrics.iv_percentile)}</td></tr></table>"
    )


def _monthly_html(report: SymbolReport) -> str:
    if report.analysis is None:
        return "<p>No monthly signals available.</p>"
    rows = [
        "<table><tr><th>Month</th><th>Expiration</th><th>Put/Call Vol</th><th>Put/Call OI</th><th>Total Vol</th><th>Total OI</th><th>Signal</th></tr>"
    ]
    for item in report.analysis.monthly_signals:
        rows.append(
            "<tr>"
            f"<td>{escape(item.month)}</td><td>{escape(item.expiration_label)}</td>"
            f"<td>{item.put_call_volume_ratio:.2f}</td><td>{item.put_call_open_interest_ratio:.2f}</td>"
            f"<td>{item.total_volume}</td><td>{item.total_open_interest}</td><td>{escape(item.signal.value)}</td>"
            "</tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)


def _drift_html(report: SymbolReport) -> str:
    if not report.drift:
        return "<p>No drift comparisons available.</p>"
    parts = ["<ul>"]
    for item in report.drift:
        flips = "; ".join(item.signal_flips)
        suffix = f" Signal flips: {escape(flips)}" if flips else ""
        parts.append(f"<li><strong>{escape(item.period)}</strong>: {escape(item.summary)}{suffix}</li>")
    parts.append("</ul>")
    return "\n".join(parts)


def _metric_text(value: object | None) -> str:
    if value is None:
        return "—"
    return str(value)


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
            f"{item.total_volume} | {item.total_open_interest} | {item.signal.value} |"
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
        return "<p>No raw expiration rows available.</p>"
    rows = [
        "<table><tr><th>Expiration</th><th>DTE</th><th>Put Vol</th><th>Call Vol</th><th>Total Vol</th>"
        "<th>Put/Call Vol</th><th>Put OI</th><th>Call OI</th><th>Total OI</th><th>Put/Call OI</th>"
        "<th>Implied Volatility</th><th>Monthly</th></tr>"
    ]
    for row in report.snapshot.rows:
        rows.append(
            "<tr>"
            f"<td>{escape(row.expiration_label)}</td><td>{row.dte}</td><td>{row.put_volume}</td>"
            f"<td>{row.call_volume}</td><td>{row.total_volume}</td><td>{row.put_call_volume_ratio:.2f}</td>"
            f"<td>{row.put_open_interest}</td><td>{row.call_open_interest}</td><td>{row.total_open_interest}</td>"
            f"<td>{row.put_call_open_interest_ratio:.2f}</td><td>{_metric_cell(row.implied_volatility)}</td>"
            f"<td>{row.is_monthly}</td>"
            "</tr>"
        )
    rows.append("</table>")
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
            f"{row.expiration_label} | {row.dte} | {row.put_volume} | {row.call_volume} | {row.total_volume} | "
            f"{row.put_call_volume_ratio:.2f} | {row.put_open_interest} | {row.call_open_interest} | "
            f"{row.total_open_interest} | {row.put_call_open_interest_ratio:.2f} | "
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
        ])
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
            ])
    return path


def render_reports(generated_at: datetime, symbol_reports: list[SymbolReport], archive_dir: Path) -> ReportBundle:
    archive_dir.mkdir(parents=True, exist_ok=True)
    title = f"Daily Options Put/Call Report - {generated_at:%Y-%m-%d}"
    html_sections = [
        "<!DOCTYPE html>",
        f'<html lang="en"><head><meta charset="utf-8"><title>{title}</title></head><body>',
        f"<h1>{title}</h1>",
    ]
    markdown_sections = [f"# {title}", ""]
    failures = [report for report in symbol_reports if report.error]
    successes = [report for report in symbol_reports if not report.error]
    if symbol_reports and not successes:
        all_failed_message = "No usable symbol data was collected for this run. All configured symbols failed."
        html_sections.append(f"<p><strong>{all_failed_message}</strong></p>")
        markdown_sections.extend([f"**{all_failed_message}**", ""])
    if failures:
        html_sections.append("<h2>Failures</h2><ul>")
        markdown_sections.extend(["## Failures", ""])
        for failure in failures:
            html_sections.append(f"<li>{escape(failure.symbol)}: {escape(failure.error or '')}</li>")
            markdown_sections.append(f"- {failure.symbol}: {failure.error or ''}")
        html_sections.append("</ul>")
        markdown_sections.append("")

    for report in symbol_reports:
        html_sections.append(f"<h2>{escape(report.symbol)}</h2>")
        if report.error:
            html_sections.append(f"<p><strong>Failed:</strong> {escape(report.error)}</p>")
            markdown_sections.extend([f"## {report.symbol}", f"Failed: {report.error}", ""])
            continue
        html_sections.append(_metrics_html(report))
        html_sections.append(f"<p>{escape(report.analysis.commentary if report.analysis else '')}</p>")
        html_sections.append("<h3>Monthly Signals</h3>")
        html_sections.append(_monthly_html(report))
        html_sections.append("<h3>Drift</h3>")
        html_sections.append(_drift_html(report))
        html_sections.append("<h3>Raw Options Table</h3>")
        html_sections.append(_raw_rows_html(report))
        csv_path = _raw_csv(report, archive_dir)
        if csv_path is not None:
            csv_ref = escape(csv_path.name)
            html_sections.append(f'<p>Raw CSV: <a href="{csv_ref}">{csv_ref}</a></p>')
        markdown_sections.extend([f"## {report.symbol}", "", "### Metrics"])
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

    html_sections.append(f"<p>Archive: {escape(str(archive_dir))}</p>")
    html_sections.append("</body></html>")
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
