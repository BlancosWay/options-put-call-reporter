from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from reporter.analyzer import analyze_snapshot
from reporter.collector import collect_symbol
from reporter.config import ConfigError, load_config, load_symbol_file, symbols_from_names
from reporter.drift import build_drift
from reporter.emailer import send_email_report
from reporter.history import HistoryStore
from reporter.keychain import KeychainError, get_password, set_password
from reporter.models import EmailConfig, SymbolAnalysis, SymbolConfig, SymbolReport
from reporter.reporting import render_reports

_URL_PATTERN = re.compile(r"https?://\S+")


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


def _progress(message: str) -> None:
    print(message, flush=True)


def _short_symbol_error(exc: Exception, symbol_config: SymbolConfig) -> str:
    raw_message = str(exc).strip()
    message = raw_message.splitlines()[0] if raw_message else exc.__class__.__name__
    message = _URL_PATTERN.sub("<url omitted>", message)
    message = message.replace(symbol_config.url, "<url omitted>")
    if len(message) > 160:
        return f"{message[:157]}..."
    return message


def _run_symbols(args: argparse.Namespace, default_symbols):
    if args.symbols_file:
        return symbols_from_names(load_symbol_file(args.symbols_file))
    if args.symbols:
        return symbols_from_names(args.symbols)
    return default_symbols


async def _run_async(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    run_symbols = _run_symbols(args, config.symbols)
    captured_at = datetime.fromisoformat(args.run_date) if args.run_date else datetime.now()
    run_archive = config.archive_dir / captured_at.strftime("%Y-%m-%d")
    store = HistoryStore(config.database_path)
    symbol_reports: list[SymbolReport] = []
    total_symbols = len(run_symbols)
    symbol_names = ", ".join(symbol.symbol for symbol in run_symbols)

    _progress(f"Starting options report for {total_symbols} symbols: {symbol_names}")
    for index, symbol_config in enumerate(run_symbols, start=1):
        progress_prefix = f"[{index}/{total_symbols}]"
        _progress(f"{progress_prefix} Collecting {symbol_config.symbol}...")
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
            _progress(
                f"{progress_prefix} {snapshot.symbol} complete: "
                f"{len(analysis.monthly_signals)} monthly signals, {len(snapshot.rows)} raw rows"
            )
        except Exception as exc:
            _progress(f"{progress_prefix} {symbol_config.symbol} failed: {_short_symbol_error(exc, symbol_config)}")
            symbol_reports.append(
                SymbolReport(
                    symbol=symbol_config.symbol,
                    snapshot=None,
                    analysis=None,
                    drift=[],
                    error=str(exc),
                )
            )

    _progress("Rendering report...")
    bundle = render_reports(captured_at, symbol_reports, run_archive)
    failures = [report for report in symbol_reports if report.error]
    successes = [report for report in symbol_reports if not report.error]
    exit_code = 1 if not successes else 0

    if args.send_email:
        try:
            _progress("Sending email...")
            email_config = _load_email_config(args.email_config)
            api_key = get_password(config.keychain_service, email_config.from_email)
            subject_status = "FAILED" if not successes else "Partial" if failures else "Complete"
            send_email_report(
                email_config=email_config,
                resend_api_url=config.resend_api_url,
                api_key=api_key,
                subject=f"{subject_status} Options Put/Call Report - {captured_at:%Y-%m-%d}",
                html_path=bundle.html_path,
            )
            _progress("Email sent.")
        except Exception as exc:
            print(f"Email was not sent: {exc}. Report remains at {bundle.html_path}", file=sys.stderr)
            exit_code = 1

    _progress(f"Report written to {bundle.html_path}")
    return exit_code


def _setup_email(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    from_email = input("Resend sender address: ").strip()
    to_email = input("Report recipient address: ").strip()
    api_key = getpass.getpass("Resend API key: ").strip()
    if not from_email or not to_email:
        raise ValueError("Sender and recipient email addresses are required")
    set_password(config.keychain_service, from_email, api_key)
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
    run.add_argument("--symbols-file", type=Path, default=None)
    email_group = run.add_mutually_exclusive_group()
    email_group.add_argument("--send-email", action="store_true")
    email_group.add_argument("--no-email", action="store_true")
    run.add_argument("symbols", nargs="*")

    setup = subparsers.add_parser("setup-email")
    setup.add_argument("--config", type=Path, default=Path("config/symbols.json"))
    setup.add_argument("--email-config", type=Path, default=Path("config/email.local.json"))
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "setup-email":
        try:
            return _setup_email(args)
        except (ConfigError, KeychainError, OSError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
    if args.command == "run":
        if args.symbols_file and args.symbols:
            print("Use either positional symbols or --symbols-file, not both", file=sys.stderr)
            return 2
        if not args.send_email and not args.no_email:
            args.no_email = True
        try:
            return asyncio.run(_run_async(args))
        except ConfigError as exc:
            print(str(exc), file=sys.stderr)
            return 2
    parser.error(f"Unsupported command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
