# Concise Run Progress Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `options-put-call-report run` print concise default progress during collection, rendering, and optional email delivery.

**Architecture:** Keep progress output inside `src/reporter/cli.py` because `_run_async` already orchestrates the run lifecycle. Add tiny CLI-only helpers for flushed output and short terminal error formatting; do not change collector, analyzer, report renderer, history, or emailer responsibilities.

**Tech Stack:** Python 3.11, argparse, asyncio, pytest, existing reporter dataclasses and CLI tests.

---

## File Structure

- Modify `src/reporter/cli.py`: add flushed progress output in `_run_async`, plus a short error formatter for per-symbol terminal failures.
- Modify `tests/test_cli.py`: add CLI-level progress assertions using `capsys` and existing fake collectors.
- Modify `README.md`: document that manual and scheduled runs now print concise progress by default.

No new modules are needed. The output is terminal behavior, so the CLI remains the only implementation boundary.

---

### Task 1: Add failing CLI progress tests

**Files:**
- Modify: `tests/test_cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Add a successful-run progress test**

Add this test after `test_run_without_symbol_override_uses_config_symbols` in `tests/test_cli.py`:

```python
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
```

- [ ] **Step 2: Extend the partial-failure test**

In `tests/test_cli.py`, change the existing function definition:

```python
def test_run_reports_partial_failures_without_stopping(monkeypatch, tmp_path: Path) -> None:
```

to:

```python
def test_run_reports_partial_failures_without_stopping(monkeypatch, tmp_path: Path, capsys) -> None:
```

Then add these assertions after the existing history assertions in that test:

```python
    captured = capsys.readouterr()
    assert "[1/2] Collecting NOW..." in captured.out
    assert "[1/2] NOW complete: 1 monthly signals, 1 raw rows" in captured.out
    assert "[2/2] Collecting MSFT..." in captured.out
    assert "[2/2] MSFT failed: Barchart blocked MSFT" in captured.out
    assert "Rendering report..." in captured.out
```

- [ ] **Step 3: Extend the email success test**

In `tests/test_cli.py`, change the existing function definition:

```python
def test_run_send_email_loads_keychain_and_sends_report(monkeypatch, tmp_path: Path) -> None:
```

to:

```python
def test_run_send_email_loads_keychain_and_sends_report(monkeypatch, tmp_path: Path, capsys) -> None:
```

Then add these assertions after the existing `sent` assertions in that test:

```python
    captured = capsys.readouterr()
    assert "Sending email..." in captured.out
    assert "Email sent." in captured.out
    assert "app-password" not in captured.out
    assert "app-password" not in captured.err
```

- [ ] **Step 4: Add an error-sanitization progress test**

Add this test after `test_run_returns_nonzero_when_all_symbols_fail` in `tests/test_cli.py`:

```python
def test_run_progress_omits_raw_symbol_url_from_failure(monkeypatch, tmp_path: Path, capsys) -> None:
    config_path = tmp_path / "symbols.json"
    _config(config_path)

    async def fake_collect(symbol_config, captured_at, archive_dir):
        raise RuntimeError(f"Fetch failed for {symbol_config.url}\nsecond diagnostic line")

    monkeypatch.setattr("reporter.cli.collect_symbol", fake_collect)

    exit_code = main(["run", "--config", str(config_path), "--no-email", "--run-date", "2026-06-02T21:30:00"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "[1/1] NOW failed: Fetch failed for <url omitted>" in captured.out
    assert "https://www.barchart.com/stocks/quotes/now/put-call-ratios" not in captured.out
    assert "second diagnostic line" not in captured.out
```

- [ ] **Step 5: Run targeted tests to verify they fail**

Run:

```bash
pytest tests/test_cli.py::test_run_no_email_prints_concise_progress tests/test_cli.py::test_run_reports_partial_failures_without_stopping tests/test_cli.py::test_run_send_email_loads_keychain_and_sends_report tests/test_cli.py::test_run_progress_omits_raw_symbol_url_from_failure -q
```

Expected: FAIL because `src/reporter/cli.py` does not print start, per-symbol, rendering, email success, or sanitized failure progress yet.

---

### Task 2: Implement concise progress output

**Files:**
- Modify: `src/reporter/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Add CLI progress helpers**

In `src/reporter/cli.py`, replace this import:

```python
from reporter.models import EmailConfig, SymbolAnalysis, SymbolReport
```

with:

```python
from reporter.models import EmailConfig, SymbolAnalysis, SymbolConfig, SymbolReport
```

Then add these helper functions after `_write_email_config`:

```python
def _progress(message: str) -> None:
    print(message, flush=True)


def _short_symbol_error(exc: Exception, symbol_config: SymbolConfig) -> str:
    raw_message = str(exc).strip()
    message = raw_message.splitlines()[0] if raw_message else exc.__class__.__name__
    message = message.replace(symbol_config.url, "<url omitted>")
    if len(message) > 160:
        return f"{message[:157]}..."
    return message
```

- [ ] **Step 2: Add start and per-symbol progress**

In `src/reporter/cli.py`, replace the body of `_run_async` with this implementation:

```python
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
            _progress("Email sent.")
        except Exception as exc:
            print(f"Email was not sent: {exc}. Report remains at {bundle.html_path}", file=sys.stderr)
            exit_code = 1

    _progress(f"Report written to {bundle.html_path}")
    return exit_code
```

- [ ] **Step 3: Run targeted tests to verify they pass**

Run:

```bash
pytest tests/test_cli.py::test_run_no_email_prints_concise_progress tests/test_cli.py::test_run_reports_partial_failures_without_stopping tests/test_cli.py::test_run_send_email_loads_keychain_and_sends_report tests/test_cli.py::test_run_progress_omits_raw_symbol_url_from_failure -q
```

Expected: PASS.

- [ ] **Step 4: Run all CLI tests**

Run:

```bash
pytest tests/test_cli.py -q
```

Expected: PASS.

---

### Task 3: Document default progress output

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update manual run documentation**

In `README.md`, add this paragraph after the manual no-email run command block:

```markdown
Runs print concise progress by default, including the symbol count, each symbol collection step, report rendering, and email send status when email is enabled.
```

- [ ] **Step 2: Update scheduler logging documentation**

In `README.md`, add this sentence after the log file list:

```markdown
The scheduled runner captures the same concise progress output in these logs, so a daily run can be checked without waiting for the final report.
```

- [ ] **Step 3: Review the README snippet**

Run:

```bash
sed -n '24,100p' README.md
```

Expected: the manual run section mentions concise progress, and the scheduler section notes that logs capture the same progress output.

---

### Task 4: Final verification and commit

**Files:**
- Modify: `src/reporter/cli.py`
- Modify: `tests/test_cli.py`
- Modify: `README.md`

- [ ] **Step 1: Run full test suite**

Run:

```bash
pytest -q
```

Expected: PASS.

- [ ] **Step 2: Check worktree status**

Run:

```bash
git --no-pager status --short
```

Expected: only these files are modified:

```text
 M README.md
 M src/reporter/cli.py
 M tests/test_cli.py
?? docs/superpowers/plans/2026-06-05-concise-run-progress.md
```

- [ ] **Step 3: Commit implementation**

Run:

```bash
git add README.md src/reporter/cli.py tests/test_cli.py docs/superpowers/plans/2026-06-05-concise-run-progress.md
git commit -m "Add concise run progress output" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

Expected: commit succeeds.

- [ ] **Step 4: Confirm clean worktree**

Run:

```bash
git --no-pager status --short
```

Expected: no output.

---

## Self-Review

- Spec coverage: Task 1 covers all requested test cases; Task 2 implements default flushed start, per-symbol, rendering, email, and final progress output; Task 3 documents manual and scheduled behavior.
- Scope check: The plan changes only CLI progress behavior and related tests/docs. It does not add a quiet flag, restructure modules, or alter collector/reporting internals.
- Type consistency: `_short_symbol_error` accepts `SymbolConfig`, which Task 2 imports from `reporter.models`. `_run_async` keeps the existing `SymbolAnalysis` and `SymbolReport` usage.
