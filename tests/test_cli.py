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
                "keychain_service": "options-put-call-reporter:resend-api-key",
                "resend_api_url": "https://api.resend.com/emails",
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


def test_run_positional_symbols_override_config_symbols(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "symbols.json"
    _config(config_path, symbols=["NOW"])
    collected: list[SymbolConfig] = []

    async def fake_collect(symbol_config, captured_at, archive_dir):
        collected.append(symbol_config)
        return _sample_snapshot(symbol_config, captured_at, archive_dir)

    monkeypatch.setattr("reporter.cli.collect_symbol", fake_collect)

    exit_code = main([
        "run",
        "--config",
        str(config_path),
        "--no-email",
        "--run-date",
        "2026-06-02T21:30:00",
        "meta",
        "META",
        "MSFT",
        "brk.b",
        "msft",
    ])

    assert exit_code == 0
    assert [symbol.symbol for symbol in collected] == ["META", "MSFT", "BRK.B"]
    assert [symbol.url for symbol in collected] == [
        "https://www.barchart.com/stocks/quotes/meta/put-call-ratios",
        "https://www.barchart.com/stocks/quotes/msft/put-call-ratios",
        "https://www.barchart.com/stocks/quotes/brk.b/put-call-ratios",
    ]
    assert HistoryStore(tmp_path / "history.sqlite3").latest_snapshot("NOW") is None
    assert HistoryStore(tmp_path / "history.sqlite3").latest_snapshot("META") is not None


def test_run_symbols_file_overrides_config_symbols(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "symbols.json"
    symbols_file = tmp_path / "watchlist.txt"
    _config(config_path, symbols=["NOW"])
    symbols_file.write_text("meta, msft\n# comment\nlite aaoi\n", encoding="utf-8")
    collected: list[str] = []

    async def fake_collect(symbol_config, captured_at, archive_dir):
        collected.append(symbol_config.symbol)
        return _sample_snapshot(symbol_config, captured_at, archive_dir)

    monkeypatch.setattr("reporter.cli.collect_symbol", fake_collect)

    exit_code = main([
        "run",
        "--config",
        str(config_path),
        "--symbols-file",
        str(symbols_file),
        "--no-email",
        "--run-date",
        "2026-06-02T21:30:00",
    ])

    assert exit_code == 0
    assert collected == ["META", "MSFT", "LITE", "AAOI"]
    assert HistoryStore(tmp_path / "history.sqlite3").latest_snapshot("NOW") is None
    assert HistoryStore(tmp_path / "history.sqlite3").latest_snapshot("LITE") is not None


def test_run_without_symbol_override_uses_config_symbols(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "symbols.json"
    _config(config_path, symbols=["NOW", "MSFT"])
    collected: list[str] = []

    async def fake_collect(symbol_config, captured_at, archive_dir):
        collected.append(symbol_config.symbol)
        return _sample_snapshot(symbol_config, captured_at, archive_dir)

    monkeypatch.setattr("reporter.cli.collect_symbol", fake_collect)

    exit_code = main(["run", "--config", str(config_path), "--no-email", "--run-date", "2026-06-02T21:30:00"])

    assert exit_code == 0
    assert collected == ["NOW", "MSFT"]


def test_run_no_email_prints_concise_progress(monkeypatch, tmp_path: Path, capsys) -> None:
    config_path = tmp_path / "symbols.json"
    _config(config_path, symbols=["NOW", "MSFT"])

    async def fake_collect(symbol_config, captured_at, archive_dir):
        return _sample_snapshot(symbol_config, captured_at, archive_dir)

    monkeypatch.setattr("reporter.cli.collect_symbol", fake_collect)

    exit_code = main(["run", "--config", str(config_path), "--no-email", "--run-date", "2026-06-02T21:30:00"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Starting options report for 2 symbols: NOW, MSFT" in captured.out
    assert "[1/2] Collecting NOW..." in captured.out
    assert "[1/2] NOW complete: 1 monthly signals, 1 raw rows" in captured.out
    assert "[2/2] Collecting MSFT..." in captured.out
    assert "[2/2] MSFT complete: 1 monthly signals, 1 raw rows" in captured.out
    assert "Rendering report..." in captured.out
    assert "Report written to" in captured.out
    assert captured.err == ""


def test_run_rejects_symbols_file_combined_with_positional_symbols(tmp_path: Path, capsys) -> None:
    config_path = tmp_path / "symbols.json"
    symbols_file = tmp_path / "watchlist.txt"
    _config(config_path)
    symbols_file.write_text("META\n", encoding="utf-8")

    exit_code = main([
        "run",
        "--config",
        str(config_path),
        "--symbols-file",
        str(symbols_file),
        "--no-email",
        "MSFT",
    ])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "Use either positional symbols or --symbols-file, not both" in captured.err


def test_run_missing_symbols_file_prints_clear_error(tmp_path: Path, capsys) -> None:
    config_path = tmp_path / "symbols.json"
    missing_symbols_file = tmp_path / "missing-watchlist.txt"
    _config(config_path)

    exit_code = main([
        "run",
        "--config",
        str(config_path),
        "--symbols-file",
        str(missing_symbols_file),
        "--no-email",
    ])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert f"Could not read symbols file {missing_symbols_file}" in captured.err
    assert "Traceback" not in captured.err


def test_run_invalid_utf8_symbols_file_prints_clear_error(tmp_path: Path, capsys) -> None:
    config_path = tmp_path / "symbols.json"
    symbols_file = tmp_path / "watchlist.txt"
    _config(config_path)
    symbols_file.write_bytes(b"META\n\xff\xfe\n")

    exit_code = main([
        "run",
        "--config",
        str(config_path),
        "--symbols-file",
        str(symbols_file),
        "--no-email",
    ])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert f"Could not read symbols file {symbols_file}" in captured.err
    assert "UTF-8 text" in captured.err
    assert "Traceback" not in captured.err


def test_run_reports_partial_failures_without_stopping(monkeypatch, tmp_path: Path, capsys) -> None:
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
    captured = capsys.readouterr()
    assert "[1/2] Collecting NOW..." in captured.out
    assert "[1/2] NOW complete: 1 monthly signals, 1 raw rows" in captured.out
    assert "[2/2] Collecting MSFT..." in captured.out
    assert "[2/2] MSFT failed: Barchart blocked MSFT" in captured.out
    assert "Rendering report..." in captured.out


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


def test_run_progress_omits_raw_symbol_url_from_failure(monkeypatch, tmp_path: Path, capsys) -> None:
    config_path = tmp_path / "symbols.json"
    _config(config_path)

    async def fake_collect(symbol_config, captured_at, archive_dir):
        raise RuntimeError(f"Fetch failed for {symbol_config.url}?bc_debug=true\nsecond diagnostic line")

    monkeypatch.setattr("reporter.cli.collect_symbol", fake_collect)

    exit_code = main(["run", "--config", str(config_path), "--no-email", "--run-date", "2026-06-02T21:30:00"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "[1/1] NOW failed: Fetch failed for <url omitted>" in captured.out
    terminal_output = captured.out + captured.err
    assert "https://www.barchart.com/stocks/quotes/now/put-call-ratios" not in terminal_output
    assert "https://www.barchart.com/stocks/quotes/now/put-call-ratios?bc_debug=true" not in terminal_output
    assert "bc_debug=true" not in terminal_output
    assert "second diagnostic line" not in terminal_output


def test_run_send_email_loads_keychain_and_sends_report(monkeypatch, tmp_path: Path, capsys) -> None:
    config_path = tmp_path / "symbols.json"
    email_config_path = tmp_path / "email.local.json"
    _config(config_path)
    email_config_path.write_text(
        json.dumps({"from_email": "reports@example.com", "to_email": "recipient@example.com"}),
        encoding="utf-8",
    )
    sent: dict[str, object] = {}
    keychain_lookups: list[tuple[str, str]] = []

    async def fake_collect(symbol_config, captured_at, archive_dir):
        return _sample_snapshot(symbol_config, captured_at, archive_dir)

    def fake_get_password(service, account):
        keychain_lookups.append((service, account))
        return "re_secret"

    monkeypatch.setattr("reporter.cli.collect_symbol", fake_collect)
    monkeypatch.setattr("reporter.cli.get_password", fake_get_password)
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
    assert keychain_lookups == [("options-put-call-reporter:resend-api-key", "reports@example.com")]
    assert sent["email_config"] == EmailConfig("reports@example.com", "recipient@example.com")
    assert sent["resend_api_url"] == "https://api.resend.com/emails"
    assert sent["api_key"] == "re_secret"
    assert sent["subject"] == "Complete Options Put/Call Report - 2026-06-02"
    assert Path(sent["html_path"]).name == "report.html"
    captured = capsys.readouterr()
    assert "Sending email..." in captured.out
    assert "Email sent." in captured.out
    assert "re_secret" not in captured.out
    assert "re_secret" not in captured.err


def test_run_send_email_failure_prints_clear_error_and_keeps_report(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    config_path = tmp_path / "symbols.json"
    email_config_path = tmp_path / "email.local.json"
    _config(config_path)
    email_config_path.write_text(
        json.dumps({"from_email": "reports@example.com", "to_email": "recipient@example.com"}),
        encoding="utf-8",
    )

    async def fake_collect(symbol_config, captured_at, archive_dir):
        return _sample_snapshot(symbol_config, captured_at, archive_dir)

    monkeypatch.setattr("reporter.cli.collect_symbol", fake_collect)
    monkeypatch.setattr("reporter.cli.get_password", lambda service, account: "re_secret")
    monkeypatch.setattr(
        "reporter.cli.send_email_report",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("Resend unavailable")),
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
    assert "Email was not sent: Resend unavailable" in captured.err
    assert str(report_path) in captured.err
    assert "Report written to" in captured.out
    assert "re_secret" not in captured.out
    assert "re_secret" not in captured.err


def test_run_send_email_missing_keychain_prints_clear_error_and_keeps_report(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    config_path = tmp_path / "symbols.json"
    email_config_path = tmp_path / "email.local.json"
    _config(config_path)
    email_config_path.write_text(
        json.dumps({"from_email": "reports@example.com", "to_email": "recipient@example.com"}),
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
    answers = iter(["reports@example.com", "recipient@example.com", "re_secret"])
    input_prompts: list[str] = []
    getpass_prompts: list[str] = []

    def fake_input(prompt):
        input_prompts.append(prompt)
        return next(answers)

    def fake_getpass(prompt):
        getpass_prompts.append(prompt)
        return next(answers)

    monkeypatch.setattr("builtins.input", fake_input)
    monkeypatch.setattr("getpass.getpass", fake_getpass)
    monkeypatch.setattr(
        "reporter.cli.set_password",
        lambda service, account, password: stored.update({"service": service, "account": account, "password": password}),
    )

    exit_code = main(["setup-email", "--config", str(config_path), "--email-config", str(tmp_path / "email.local.json")])

    assert exit_code == 0
    assert input_prompts == ["Resend sender address: ", "Report recipient address: "]
    assert getpass_prompts == ["Resend API key: "]
    assert stored == {
        "service": "options-put-call-reporter:resend-api-key",
        "account": "reports@example.com",
        "password": "re_secret",
    }
    email_config = json.loads((tmp_path / "email.local.json").read_text(encoding="utf-8"))
    assert email_config == {"from_email": "reports@example.com", "to_email": "recipient@example.com"}
