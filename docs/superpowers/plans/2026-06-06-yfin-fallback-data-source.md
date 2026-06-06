# yfin Fallback Data Source Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add yfin.dev as a free fallback source when Barchart collection fails, and disclose the source in generated HTML, Markdown, and CSV files.

**Architecture:** Keep `collect_symbol()` as the public collector entry point. Split the existing Barchart implementation into a private primary collector, add a yfin aggregation fallback, and attach `DataSource` metadata to every `Snapshot`. Reporting and history consume that metadata without changing analysis thresholds.

**Tech Stack:** Python 3.11+, stdlib `urllib.request` for fallback HTTP, Playwright for existing Barchart collection, pytest/pytest-asyncio.

---

## Files

- Modify `src/reporter/models.py`: add `DataSource` and `Snapshot.data_source`.
- Modify `src/reporter/collector.py`: split Barchart primary flow, add yfin fallback HTTP/aggregation helpers.
- Modify `src/reporter/reporting.py`: disclose source in HTML, Markdown, and CSV.
- Modify `src/reporter/history.py`: persist and restore `DataSource` metadata with an additive SQLite migration.
- Modify tests in `tests/test_collector.py`, `tests/test_reporting.py`, and `tests/test_history.py`.

## Task 1: Snapshot source metadata

- [ ] Write failing tests that assert a `Snapshot` can carry `DataSource` metadata and that `HistoryStore` round-trips it.
- [ ] Add `DataSource` to `models.py` with fields `name`, `url`, `is_fallback`, and `note`.
- [ ] Add `data_source` to `Snapshot` with a default Barchart value so existing tests and old history rows keep working.
- [ ] Add `data_source_json` to the SQLite snapshots table when missing.
- [ ] Save and load `data_source_json`, defaulting missing values to the Barchart source.
- [ ] Run `pytest tests/test_history.py -q`.

## Task 2: yfin fallback collector

- [ ] Write failing collector tests that simulate Barchart failure and yfin success.
- [ ] Add a private `_collect_symbol_from_barchart()` containing the current Playwright implementation.
- [ ] Make `collect_symbol()` try Barchart first, then yfin on `CollectionError`.
- [ ] Add yfin HTTP helpers using `asyncio.to_thread()` around `urllib.request.urlopen()`.
- [ ] Aggregate yfin calls/puts into `ExpirationRow` values.
- [ ] Archive fallback raw JSON as `{symbol}-yfin-raw.json` and snapshot JSON as before.
- [ ] If yfin also fails, raise `CollectionError` with both primary and fallback causes.
- [ ] Run `pytest tests/test_collector.py -q`.

## Task 3: Source disclosure in generated files

- [ ] Write failing report tests for source disclosure in HTML, Markdown, and raw CSV.
- [ ] Add a Source column to the summary HTML table.
- [ ] Add a data-source paragraph to each successful symbol card.
- [ ] Add a `### Data Source` section to each successful Markdown symbol section.
- [ ] Add `data_source_name`, `data_source_url`, `data_source_is_fallback`, and `data_source_note` columns to raw CSV rows.
- [ ] Run `pytest tests/test_reporting.py -q`.

## Task 4: Final verification and publish

- [ ] Run `pytest -q`.
- [ ] Run `python -m build`.
- [ ] Commit the fallback implementation.
- [ ] Push `HEAD` to `origin main`.
- [ ] Confirm GitHub Actions passes for `main`.
