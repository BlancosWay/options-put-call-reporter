import json
from datetime import date, datetime
from pathlib import Path

from reporter.cli import main
from reporter.history import HistoryStore
from reporter.models import EmailConfig, ExpirationRow, Snapshot, SymbolConfig, TopMetrics


def _config(path: Path, symbols: list[str] | None = None) -> None:
    symbols = symbols or ["NOW"]
    path.write_text(
        json.dumps(
            {
                "archive_dir": str(path.parent / "archive"),
                "database_path": str(path.parent / "history.sqlite3"),
                "report_time_local": "14:30",
                "keychain_service": "options-put-call-reporter:gmail-app-password",
                "gmail_smtp_host": "smtp.gmail.com",
                "gmail_smtp_port": 587,
                "thresholds": {
                    "strong_bullish_volume_max": 0.35,
                    "strong_bullish_oi_max": 0.7,
                    "bullish_volume_max": 0.7,
                    "bullish_oi_max": 0.9,
                    "bearish_volume_min": 1.1,
                    "bearish_oi_min": 1.25,
                    "mixed_oi_min": 1.0,
                    "mixed_oi_max": 1.25,
                    "neutral_volume_min": 0.7,
                    "neutral_volume_max": 1.1,
                    "neutral_oi_max": 1.1,
                    "min_total_volume_for_commentary": 1000,
                },
                "symbols": [
                    {
                        "symbol": symbol,
                        "url": f"https://www.barchart.com/stocks/quotes/{symbol.lower()}/put-call-ratios",
                    }
                    for symbol in symbols
                ],
            }
        ),
        encoding="utf-8",
    )


def _sample_snapshot(symbol_config: SymbolConfig, captured_at: datetime, archive_dir: Path) -> Snapshot:
    return Snapshot(
        symbol=symbol_config.symbol.upper(),
        url=symbol_config.url,
        captured_at=captured_at,
        metrics=TopMetrics("07/22/26", 30.86, 37.28, 29.62, 39.0),
        rows=[
            ExpirationRow(
                "06/18/26 (m)",
                date(2026, 6, 18),
                16,
                11737,
                26979,
                38716,
                0.44,
                202821,
                226097,
                428918,
                0.90,
                31.92,
                True,
            )
        ],
    )


def test_run_no_email_creates_report_and_saves_history(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "symbols.json"
    _config(config_path)

    async def fake_collect(symbol_config, captured_at, archive_dir):
        return _sample_snapshot(symbol_config, captured_at, archive_dir)

    monkeypatch.setattr("reporter.cli.collect_symbol", fake_collect)

    exit_code = main(["run", "--config", str(config_path), "--no-email", "--run-date", "2026-06-02T21:30:00"])

    assert exit_code == 0
    assert (tmp_path / "archive" / "2026-06-02" / "report.html").exists()
    assert HistoryStore(tmp_path / "history.sqlite3").latest_snapshot("NOW") is not None


def test_run_reports_partial_failures_without_stopping(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "symbols.json"
    _config(config_path, symbols=["NOW", "MSFT"])

    async def fake_collect(symbol_config, captured_at, archive_dir):
        if symbol_config.symbol == "MSFT":
            raise RuntimeError("Barchart blocked MSFT")
        return _sample_snapshot(symbol_config, captured_at, archive_dir)

    monkeypatch.setattr("reporter.cli.collect_symbol", fake_collect)

    exit_code = main(["run", "--config", str(config_path), "--no-email", "--run-date", "2026-06-02T21:30:00"])

    report_html = (tmp_path / "archive" / "2026-06-02" / "report.html").read_text(encoding="utf-8")
    assert exit_code == 0
    assert "Barchart blocked MSFT" in report_html
    assert HistoryStore(tmp_path / "history.sqlite3").latest_snapshot("NOW") is not None
    assert HistoryStore(tmp_path / "history.sqlite3").latest_snapshot("MSFT") is None


def test_run_returns_nonzero_when_all_symbols_fail(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "symbols.json"
    _config(config_path)

    async def fake_collect(symbol_config, captured_at, archive_dir):
        raise RuntimeError("Barchart blocked NOW")

    monkeypatch.setattr("reporter.cli.collect_symbol", fake_collect)

    exit_code = main(["run", "--config", str(config_path), "--no-email", "--run-date", "2026-06-02T21:30:00"])

    report_html = (tmp_path / "archive" / "2026-06-02" / "report.html").read_text(encoding="utf-8")
    assert exit_code == 1
    assert (tmp_path / "archive" / "2026-06-02" / "report.html").exists()
    assert "No usable symbol data was collected for this run. All configured symbols failed." in report_html


def test_run_send_email_loads_keychain_and_sends_report(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "symbols.json"
    email_config_path = tmp_path / "email.local.json"
    _config(config_path)
    email_config_path.write_text(
        json.dumps({"from_email": "sender@gmail.com", "to_email": "recipient@gmail.com"}),
        encoding="utf-8",
    )
    sent: dict[str, object] = {}

    async def fake_collect(symbol_config, captured_at, archive_dir):
        return _sample_snapshot(symbol_config, captured_at, archive_dir)

    monkeypatch.setattr("reporter.cli.collect_symbol", fake_collect)
    monkeypatch.setattr("reporter.cli.get_password", lambda service, account: "app-password")
    monkeypatch.setattr(
        "reporter.cli.send_email_report",
        lambda **kwargs: sent.update(kwargs),
    )

    exit_code = main([
        "run",
        "--config",
        str(config_path),
        "--email-config",
        str(email_config_path),
        "--send-email",
        "--run-date",
        "2026-06-02T21:30:00",
    ])

    assert exit_code == 0
    assert sent["email_config"] == EmailConfig("sender@gmail.com", "recipient@gmail.com")
    assert sent["app_password"] == "app-password"
    assert sent["smtp_host"] == "smtp.gmail.com"
    assert sent["smtp_port"] == 587
    assert sent["subject"] == "Complete Options Put/Call Report - 2026-06-02"
    assert Path(sent["html_path"]).name == "report.html"


def test_run_send_email_failure_prints_clear_error_and_keeps_report(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    config_path = tmp_path / "symbols.json"
    email_config_path = tmp_path / "email.local.json"
    _config(config_path)
    email_config_path.write_text(
        json.dumps({"from_email": "sender@gmail.com", "to_email": "recipient@gmail.com"}),
        encoding="utf-8",
    )

    async def fake_collect(symbol_config, captured_at, archive_dir):
        return _sample_snapshot(symbol_config, captured_at, archive_dir)

    monkeypatch.setattr("reporter.cli.collect_symbol", fake_collect)
    monkeypatch.setattr("reporter.cli.get_password", lambda service, account: "app-password")
    monkeypatch.setattr(
        "reporter.cli.send_email_report",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("SMTP unavailable")),
    )

    exit_code = main([
        "run",
        "--config",
        str(config_path),
        "--email-config",
        str(email_config_path),
        "--send-email",
        "--run-date",
        "2026-06-02T21:30:00",
    ])

    assert exit_code == 1
    report_path = tmp_path / "archive" / "2026-06-02" / "report.html"
    assert report_path.exists()
    captured = capsys.readouterr()
    assert "Email was not sent: SMTP unavailable" in captured.err
    assert str(report_path) in captured.err
    assert "Report written to" in captured.out


def test_run_send_email_missing_keychain_prints_clear_error_and_keeps_report(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    config_path = tmp_path / "symbols.json"
    email_config_path = tmp_path / "email.local.json"
    _config(config_path)
    email_config_path.write_text(
        json.dumps({"from_email": "sender@gmail.com", "to_email": "recipient@gmail.com"}),
        encoding="utf-8",
    )

    async def fake_collect(symbol_config, captured_at, archive_dir):
        return _sample_snapshot(symbol_config, captured_at, archive_dir)

    monkeypatch.setattr("reporter.cli.collect_symbol", fake_collect)
    monkeypatch.setattr("reporter.cli.get_password", lambda service, account: (_ for _ in ()).throw(RuntimeError("missing keychain secret")))

    exit_code = main([
        "run",
        "--config",
        str(config_path),
        "--email-config",
        str(email_config_path),
        "--send-email",
        "--run-date",
        "2026-06-02T21:30:00",
    ])

    assert exit_code == 1
    report_path = tmp_path / "archive" / "2026-06-02" / "report.html"
    assert report_path.exists()
    captured = capsys.readouterr()
    assert "Email was not sent: missing keychain secret" in captured.err
    assert str(report_path) in captured.err


def test_setup_email_writes_local_email_config_and_keychain(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "symbols.json"
    _config(config_path)
    stored: dict[str, str] = {}
    answers = iter(["sender@gmail.com", "recipient@gmail.com", "app-password"])

    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    monkeypatch.setattr("getpass.getpass", lambda prompt: next(answers))
    monkeypatch.setattr(
        "reporter.cli.set_password",
        lambda service, account, password: stored.update({"service": service, "account": account, "password": password}),
    )

    exit_code = main(["setup-email", "--config", str(config_path), "--email-config", str(tmp_path / "email.local.json")])

    assert exit_code == 0
    assert stored == {
        "service": "options-put-call-reporter:gmail-app-password",
        "account": "sender@gmail.com",
        "password": "app-password",
    }
    email_config = json.loads((tmp_path / "email.local.json").read_text(encoding="utf-8"))
    assert email_config == {"from_email": "sender@gmail.com", "to_email": "recipient@gmail.com"}
