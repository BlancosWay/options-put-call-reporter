# Concise Run Progress Output Design

## Goal

Make `options-put-call-report run` feel active during long collection runs by printing concise, default progress messages while preserving the existing final result output.

## Behavior

The `run` command will print progress to stdout with `flush=True` so messages appear immediately:

- Start summary: `Starting options report for N symbols: META, GOOG, ...`
- Per-symbol start: `[i/N] Collecting SYMBOL...`
- Per-symbol success: `[i/N] SYMBOL complete: X monthly signals, Y raw rows`
- Per-symbol failure: `[i/N] SYMBOL failed: <short error>`
- Report rendering: `Rendering report...`
- Email send, only when enabled: `Sending email...` and `Email sent.`
- Existing final line remains: `Report written to <path>`

The command will not print secrets, Gmail app password details, full tracebacks, or verbose archive paths. Detailed diagnostics remain in the generated report and archive artifacts.

## Data Flow

`_run_async` already owns config loading, symbol resolution, collection, analysis, report rendering, and optional email delivery. Progress output will stay in that orchestration layer so collector, analyzer, reporting, and email modules remain focused on their domain logic.

For each symbol, `_run_async` will print before `collect_symbol`. On success, it will summarize the analyzed snapshot using counts already available on the snapshot. On handled per-symbol failure, it will print the same short failure message that is stored in the run result and continue with the remaining symbols.

## Error Handling

Configuration and CLI validation errors keep the existing clean stderr behavior and exit code. Per-symbol collection failures remain non-fatal when at least one symbol succeeds, but now also appear in stdout progress. Email failures keep the existing stderr message and nonzero exit behavior after the local report is written.

## Tests

Add CLI tests that verify:

- a successful default run prints start, per-symbol, rendering, and final lines;
- per-symbol failures print a concise failure progress line and still write the report when other symbols succeed;
- `--send-email` prints send progress and success when delivery works;
- sensitive values such as email passwords do not appear in stdout or stderr.
