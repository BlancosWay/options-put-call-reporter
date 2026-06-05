from __future__ import annotations

import argparse
import asyncio
import getpass
import json
from datetime import datetime
from pathlib import Path

from reporter.analyzer import analyze_snapshot
from reporter.collector import collect_symbol
from reporter.config import load_config
from reporter.drift import build_drift
from reporter.emailer import send_email_report
from reporter.history import HistoryStore
from reporter.keychain import get_password, set_password
from reporter.models import EmailConfig, SymbolAnalysis, SymbolReport
from reporter.reporting import render_reports


def _load_email_config(path: Path) -> EmailConfig:
    data = json.loads(path.read_text(encoding="utf-8"))
    return EmailConfig(from_email=data["from_email"], to_email=data["to_email"])


def _write_email_config(path: Path, email_config: EmailConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"from_email": email_config.from_email, "to_email": email_config.to_email},
            indent=2,
        ),
        encoding="utf-8",
    )


async def _run_async(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    captured_at = datetime.fromisoformat(args.run_date) if args.run_date else datetime.now()
    run_archive = config.archive_dir / captured_at.strftime("%Y-%m-%d")
    store = HistoryStore(config.database_path)
    symbol_reports: list[SymbolReport] = []

    for symbol_config in config.symbols:
        try:
            snapshot = await collect_symbol(symbol_config, captured_at, run_archive)
            store.save_snapshot(snapshot)
            analysis = analyze_snapshot(snapshot, config.thresholds)
            prior_snapshots = store.prior_snapshots(snapshot.symbol, captured_at)
            prior_analyses: dict[str, SymbolAnalysis | None] = {
                period: analyze_snapshot(prior, config.thresholds) if prior else None
                for period, prior in prior_snapshots.items()
            }
            drift = build_drift(analysis, prior_analyses, config.thresholds)
            symbol_reports.append(SymbolReport(symbol=snapshot.symbol, snapshot=snapshot, analysis=analysis, drift=drift))
        except Exception as exc:
            symbol_reports.append(
                SymbolReport(
                    symbol=symbol_config.symbol,
                    snapshot=None,
                    analysis=None,
                    drift=[],
                    error=str(exc),
                )
            )

    bundle = render_reports(captured_at, symbol_reports, run_archive)
    failures = [report for report in symbol_reports if report.error]
    successes = [report for report in symbol_reports if not report.error]

    if args.send_email:
        email_config = _load_email_config(args.email_config)
        app_password = get_password(config.keychain_service, email_config.from_email)
        subject_status = "FAILED" if not successes else "Partial" if failures else "Complete"
        send_email_report(
            email_config=email_config,
            smtp_host=config.gmail_smtp_host,
            smtp_port=config.gmail_smtp_port,
            app_password=app_password,
            subject=f"{subject_status} Options Put/Call Report - {captured_at:%Y-%m-%d}",
            html_path=bundle.html_path,
        )

    print(f"Report written to {bundle.html_path}")
    return 1 if not successes else 0


def _setup_email(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    from_email = input("Gmail sender address: ").strip()
    to_email = input("Report recipient address: ").strip()
    password = getpass.getpass("Gmail App Password: ").strip()
    if not from_email or not to_email:
        raise ValueError("Sender and recipient email addresses are required")
    set_password(config.keychain_service, from_email, password)
    _write_email_config(args.email_config, EmailConfig(from_email=from_email, to_email=to_email))
    print(f"Email config written to {args.email_config}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="options-put-call-report")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run")
    run.add_argument("--config", type=Path, default=Path("config/symbols.json"))
    run.add_argument("--email-config", type=Path, default=Path("config/email.local.json"))
    run.add_argument("--run-date", default=None)
    email_group = run.add_mutually_exclusive_group()
    email_group.add_argument("--send-email", action="store_true")
    email_group.add_argument("--no-email", action="store_true")

    setup = subparsers.add_parser("setup-email")
    setup.add_argument("--config", type=Path, default=Path("config/symbols.json"))
    setup.add_argument("--email-config", type=Path, default=Path("config/email.local.json"))
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "setup-email":
        return _setup_email(args)
    if args.command == "run":
        if not args.send_email and not args.no_email:
            args.no_email = True
        return asyncio.run(_run_async(args))
    parser.error(f"Unsupported command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
