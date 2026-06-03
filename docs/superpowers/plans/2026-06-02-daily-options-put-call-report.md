# Daily Options Put/Call Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local daily automation that collects Barchart put/call ratio data for META, GOOG, MSFT, NFLX, NOW, AAOI, and LITE, analyzes month-over-month signals and drift, archives the results, and emails a detailed Gmail report after market close.

**Architecture:** A Python package drives a headless Playwright collector, normalizes and analyzes option-expiration rows, persists snapshots in SQLite, renders Markdown/HTML/CSV artifacts, and sends the HTML report through Gmail SMTP using an app password stored in macOS Keychain. A launchd-backed scheduler runs the same CLI command daily at 2:30 PM Pacific Time.

**Tech Stack:** Python 3.11+, Playwright Chromium, SQLite, pytest, standard-library `smtplib`, macOS `security` CLI, launchd.

---

## File Structure

- Create: `.gitignore` — excludes local virtualenvs, generated archives, SQLite databases, local email config, and Playwright artifacts.
- Create: `pyproject.toml` — package metadata, console script, dependencies, pytest config.
- Create: `README.md` — local setup, Gmail app-password/Keychain setup, manual run, scheduler install.
- Create: `config/symbols.json` — non-secret watchlist, Barchart URLs, thresholds, archive/database paths.
- Create: `src/reporter/__init__.py` — package marker and version.
- Create: `src/reporter/models.py` — dataclasses for config, metrics, expiration rows, snapshots, signals, reports, and failures.
- Create: `src/reporter/config.py` — config loader and validation.
- Create: `src/reporter/parsing.py` — parsing helpers for percentages, numbers, expiration labels, and dates.
- Create: `src/reporter/analyzer.py` — monthly row selection, signal classification, summary commentary.
- Create: `src/reporter/history.py` — SQLite schema, snapshot persistence, nearest-prior snapshot lookup.
- Create: `src/reporter/drift.py` — previous-day/week/month drift comparisons and commentary.
- Create: `src/reporter/reporting.py` — Markdown, HTML, and CSV report rendering.
- Create: `src/reporter/keychain.py` — macOS Keychain read/write wrapper using `security`.
- Create: `src/reporter/emailer.py` — Gmail SMTP sender.
- Create: `src/reporter/collector.py` — Playwright Barchart collector and diagnostic artifact writer.
- Create: `src/reporter/cli.py` — commands for setup, manual run, no-email run, and scheduler support.
- Create: `scripts/run_daily.sh` — shell entrypoint used by launchd.
- Create: `scripts/install_launch_agent.sh` — writes and loads the launchd plist.
- Create: `tests/fixtures/barchart_put_call_sample.html` — stable fixture based on the Barchart table shape.
- Create: `tests/test_config.py` — config validation tests.
- Create: `tests/test_parsing.py` — number/date parsing tests.
- Create: `tests/test_analyzer.py` — signal and monthly selection tests.
- Create: `tests/test_history.py` — SQLite persistence and nearest-prior lookup tests.
- Create: `tests/test_drift.py` — drift summary tests.
- Create: `tests/test_reporting.py` — report rendering tests.
- Create: `tests/test_keychain_emailer.py` — Keychain and email sender tests with subprocess/SMTP fakes.
- Create: `tests/test_collector.py` — DOM extraction tests using fixture HTML and Playwright.
- Create: `tests/test_cli.py` — CLI orchestration tests with collector/email fakes.

---

### Task 1: Bootstrap Python Project

**Files:**
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `config/symbols.json`
- Create: `src/reporter/__init__.py`

- [ ] **Step 1: Create the project metadata and dependency file**

Add `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=70", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "options-put-call-reporter"
version = "0.1.0"
description = "Daily Barchart put/call ratio report generator"
requires-python = ">=3.11"
dependencies = [
  "playwright>=1.46,<2"
]

[project.optional-dependencies]
dev = [
  "pytest>=8,<9"
]

[project.scripts]
options-put-call-report = "reporter.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-q"
```

- [ ] **Step 2: Create the git ignore file**

Add `.gitignore`:

```gitignore
.venv/
__pycache__/
*.pyc
.pytest_cache/
.DS_Store
archive/
data/
config/email.local.json
playwright-report/
test-results/
```

- [ ] **Step 3: Create the non-secret symbol config**

Add `config/symbols.json`:

```json
{
  "archive_dir": "archive",
  "database_path": "data/history.sqlite3",
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
    "min_total_volume_for_commentary": 1000
  },
  "symbols": [
    {"symbol": "META", "url": "https://www.barchart.com/stocks/quotes/meta/put-call-ratios"},
    {"symbol": "GOOG", "url": "https://www.barchart.com/stocks/quotes/goog/put-call-ratios"},
    {"symbol": "MSFT", "url": "https://www.barchart.com/stocks/quotes/msft/put-call-ratios"},
    {"symbol": "NFLX", "url": "https://www.barchart.com/stocks/quotes/nflx/put-call-ratios"},
    {"symbol": "NOW", "url": "https://www.barchart.com/stocks/quotes/now/put-call-ratios"},
    {"symbol": "AAOI", "url": "https://www.barchart.com/stocks/quotes/aaoi/put-call-ratios"},
    {"symbol": "LITE", "url": "https://www.barchart.com/stocks/quotes/lite/put-call-ratios"}
  ]
}
```

- [ ] **Step 4: Create the package marker**

Add `src/reporter/__init__.py`:

```python
__version__ = "0.1.0"
```

- [ ] **Step 5: Create the setup README**

Add `README.md`:

````markdown
# Options Put/Call Reporter

Local daily reporter for Barchart put/call ratio pages.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m playwright install chromium
```

## Gmail setup

Run the interactive setup command. It asks for the sender email, recipient email, and Gmail App Password. The app password is stored in macOS Keychain under `options-put-call-reporter:gmail-app-password`.

```bash
source .venv/bin/activate
options-put-call-report setup-email
```

## Manual run

Save the report locally without sending email:

```bash
source .venv/bin/activate
options-put-call-report run --no-email
```

Collect, analyze, archive, and send email:

```bash
source .venv/bin/activate
options-put-call-report run --send-email
```

## Scheduler

Install the launchd job:

```bash
./scripts/install_launch_agent.sh
```

The scheduled job runs at 2:30 PM Pacific Time, which corresponds to 5:30 PM Eastern Time.
````

- [ ] **Step 6: Install dependencies**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m playwright install chromium
```

Expected: dependency install succeeds and Playwright installs Chromium.

- [ ] **Step 7: Run baseline tests**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
source .venv/bin/activate
pytest
```

Expected: pytest exits successfully with no tests collected or with the current tests passing.

- [ ] **Step 8: Commit bootstrap files**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
git add .gitignore pyproject.toml README.md config/symbols.json src/reporter/__init__.py
git commit -m "Bootstrap options put-call reporter project

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

Expected: commit succeeds.

---

### Task 2: Models and Config Loader

**Files:**
- Create: `src/reporter/models.py`
- Create: `src/reporter/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing config tests**

Add `tests/test_config.py`:

```python
import json
from pathlib import Path

import pytest

from reporter.config import ConfigError, load_config


def write_config(path: Path, overrides: dict | None = None) -> None:
    config = {
        "archive_dir": "archive",
        "database_path": "data/history.sqlite3",
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
            "min_total_volume_for_commentary": 1000
        },
        "symbols": [
            {"symbol": "NOW", "url": "https://www.barchart.com/stocks/quotes/now/put-call-ratios"}
        ]
    }
    if overrides:
        config.update(overrides)
    path.write_text(json.dumps(config), encoding="utf-8")


def test_load_config_returns_typed_values(tmp_path: Path) -> None:
    config_path = tmp_path / "symbols.json"
    write_config(config_path)

    config = load_config(config_path)

    assert config.archive_dir == Path("archive")
    assert config.database_path == Path("data/history.sqlite3")
    assert config.report_time_local == "14:30"
    assert config.symbols[0].symbol == "NOW"
    assert config.symbols[0].url == "https://www.barchart.com/stocks/quotes/now/put-call-ratios"
    assert config.thresholds.strong_bullish_volume_max == 0.35


def test_load_config_rejects_missing_symbols(tmp_path: Path) -> None:
    config_path = tmp_path / "symbols.json"
    write_config(config_path, {"symbols": []})

    with pytest.raises(ConfigError, match="at least one symbol"):
        load_config(config_path)


def test_load_config_rejects_non_barchart_url(tmp_path: Path) -> None:
    config_path = tmp_path / "symbols.json"
    write_config(config_path, {"symbols": [{"symbol": "NOW", "url": "https://example.com/now"}]})

    with pytest.raises(ConfigError, match="Barchart"):
        load_config(config_path)
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
source .venv/bin/activate
pytest tests/test_config.py
```

Expected: FAIL because `reporter.config` does not exist.

- [ ] **Step 3: Add model dataclasses**

Add `src/reporter/models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from pathlib import Path


class Signal(str, Enum):
    STRONG_BULLISH = "Strong bullish"
    BULLISH = "Bullish"
    NEUTRAL = "Neutral"
    MIXED = "Mixed"
    MIXED_CAUTION = "Mixed / caution"
    BEARISH_HEDGING = "Bearish / hedging-heavy"
    FAILED = "Failed"


@dataclass(frozen=True)
class Thresholds:
    strong_bullish_volume_max: float
    strong_bullish_oi_max: float
    bullish_volume_max: float
    bullish_oi_max: float
    bearish_volume_min: float
    bearish_oi_min: float
    mixed_oi_min: float
    mixed_oi_max: float
    neutral_volume_min: float
    neutral_volume_max: float
    neutral_oi_max: float
    min_total_volume_for_commentary: int


@dataclass(frozen=True)
class SymbolConfig:
    symbol: str
    url: str


@dataclass(frozen=True)
class AppConfig:
    archive_dir: Path
    database_path: Path
    report_time_local: str
    keychain_service: str
    gmail_smtp_host: str
    gmail_smtp_port: int
    thresholds: Thresholds
    symbols: list[SymbolConfig]


@dataclass(frozen=True)
class EmailConfig:
    from_email: str
    to_email: str


@dataclass(frozen=True)
class TopMetrics:
    latest_earnings: str | None
    implied_volatility: float | None
    historic_volatility: float | None
    iv_rank: float | None
    iv_percentile: float | None


@dataclass(frozen=True)
class ExpirationRow:
    expiration_label: str
    expiration_date: date
    dte: int
    put_volume: int
    call_volume: int
    total_volume: int
    put_call_volume_ratio: float
    put_open_interest: int
    call_open_interest: int
    total_open_interest: int
    put_call_open_interest_ratio: float
    implied_volatility: float | None
    is_monthly: bool


@dataclass(frozen=True)
class Snapshot:
    symbol: str
    url: str
    captured_at: datetime
    metrics: TopMetrics
    rows: list[ExpirationRow]


@dataclass(frozen=True)
class MonthlySignal:
    month: str
    expiration_label: str
    put_call_volume_ratio: float
    put_call_open_interest_ratio: float
    total_volume: int
    total_open_interest: int
    signal: Signal


@dataclass(frozen=True)
class SymbolAnalysis:
    symbol: str
    captured_at: datetime
    metrics: TopMetrics
    monthly_signals: list[MonthlySignal]
    commentary: str


@dataclass(frozen=True)
class DriftItem:
    period: str
    summary: str
    signal_flips: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SymbolReport:
    symbol: str
    snapshot: Snapshot | None
    analysis: SymbolAnalysis | None
    drift: list[DriftItem]
    error: str | None = None


@dataclass(frozen=True)
class ReportBundle:
    generated_at: datetime
    symbol_reports: list[SymbolReport]
    archive_dir: Path
    markdown_path: Path
    html_path: Path
```

- [ ] **Step 4: Add config loader**

Add `src/reporter/config.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reporter.models import AppConfig, SymbolConfig, Thresholds


class ConfigError(ValueError):
    pass


def _require_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ConfigError(f"Config value '{key}' must be a non-empty string")
    return value


def _require_int(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int):
        raise ConfigError(f"Config value '{key}' must be an integer")
    return value


def _thresholds(data: dict[str, Any]) -> Thresholds:
    raw = data.get("thresholds")
    if not isinstance(raw, dict):
        raise ConfigError("Config value 'thresholds' must be an object")
    values: dict[str, float | int] = {}
    for key in Thresholds.__dataclass_fields__:
        value = raw.get(key)
        if not isinstance(value, (int, float)):
            raise ConfigError(f"Threshold '{key}' must be numeric")
        values[key] = int(value) if key == "min_total_volume_for_commentary" else float(value)
    return Thresholds(**values)


def _symbols(data: dict[str, Any]) -> list[SymbolConfig]:
    raw_symbols = data.get("symbols")
    if not isinstance(raw_symbols, list) or not raw_symbols:
        raise ConfigError("Config must include at least one symbol")
    symbols: list[SymbolConfig] = []
    seen: set[str] = set()
    for raw in raw_symbols:
        if not isinstance(raw, dict):
            raise ConfigError("Each symbol entry must be an object")
        symbol = _require_string(raw, "symbol").upper()
        url = _require_string(raw, "url")
        if "barchart.com" not in url or "/put-call-ratios" not in url:
            raise ConfigError(f"Symbol {symbol} must use a Barchart put-call-ratios URL")
        if symbol in seen:
            raise ConfigError(f"Duplicate symbol '{symbol}'")
        seen.add(symbol)
        symbols.append(SymbolConfig(symbol=symbol, url=url))
    return symbols


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ConfigError("Config root must be an object")
    return AppConfig(
        archive_dir=Path(_require_string(data, "archive_dir")),
        database_path=Path(_require_string(data, "database_path")),
        report_time_local=_require_string(data, "report_time_local"),
        keychain_service=_require_string(data, "keychain_service"),
        gmail_smtp_host=_require_string(data, "gmail_smtp_host"),
        gmail_smtp_port=_require_int(data, "gmail_smtp_port"),
        thresholds=_thresholds(data),
        symbols=_symbols(data),
    )
```

- [ ] **Step 5: Run config tests**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
source .venv/bin/activate
pytest tests/test_config.py
```

Expected: PASS.

- [ ] **Step 6: Commit models and config**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
git add src/reporter/models.py src/reporter/config.py tests/test_config.py
git commit -m "Add typed config loader

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

Expected: commit succeeds.

---

### Task 3: Parsing Helpers

**Files:**
- Create: `src/reporter/parsing.py`
- Create: `tests/test_parsing.py`

- [ ] **Step 1: Write failing parser tests**

Add `tests/test_parsing.py`:

```python
from datetime import date

import pytest

from reporter.parsing import ParseError, parse_expiration_label, parse_float, parse_int, parse_percent


def test_parse_percent_removes_percent_symbol() -> None:
    assert parse_percent("31.62%") == 31.62
    assert parse_percent("") is None
    assert parse_percent("—") is None


def test_parse_int_removes_commas() -> None:
    assert parse_int("154,342") == 154342
    assert parse_int("0") == 0


def test_parse_float_handles_commas_and_zero() -> None:
    assert parse_float("1.49") == 1.49
    assert parse_float("2,001.5") == 2001.5


def test_parse_expiration_label_detects_monthly() -> None:
    parsed = parse_expiration_label("06/18/26 (m)")
    assert parsed.expiration_date == date(2026, 6, 18)
    assert parsed.is_monthly is True


def test_parse_expiration_label_detects_weekly() -> None:
    parsed = parse_expiration_label("06/05/26 (w)")
    assert parsed.expiration_date == date(2026, 6, 5)
    assert parsed.is_monthly is False


def test_parse_expiration_label_rejects_bad_value() -> None:
    with pytest.raises(ParseError, match="expiration"):
        parse_expiration_label("June 2026")
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
source .venv/bin/activate
pytest tests/test_parsing.py
```

Expected: FAIL because `reporter.parsing` does not exist.

- [ ] **Step 3: Add parsing helpers**

Add `src/reporter/parsing.py`:

```python
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime


class ParseError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedExpiration:
    expiration_date: date
    is_monthly: bool


def parse_percent(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = value.strip().replace("%", "")
    if cleaned in {"", "—", "-", "N/A"}:
        return None
    return float(cleaned.replace(",", ""))


def parse_int(value: str) -> int:
    cleaned = value.strip().replace(",", "")
    if cleaned in {"", "—", "-", "N/A"}:
        raise ParseError(f"Cannot parse integer from '{value}'")
    return int(cleaned)


def parse_float(value: str) -> float:
    cleaned = value.strip().replace(",", "")
    if cleaned in {"", "—", "-", "N/A"}:
        raise ParseError(f"Cannot parse float from '{value}'")
    return float(cleaned)


def parse_expiration_label(value: str) -> ParsedExpiration:
    cleaned = " ".join(value.strip().split())
    match = re.match(r"^(?P<month>\d{2})/(?P<day>\d{2})/(?P<year>\d{2})(?:\s+\((?P<kind>[mw])\))?$", cleaned)
    if not match:
        raise ParseError(f"Cannot parse expiration label '{value}'")
    expiration_date = datetime.strptime(
        f"{match.group('month')}/{match.group('day')}/{match.group('year')}",
        "%m/%d/%y",
    ).date()
    return ParsedExpiration(
        expiration_date=expiration_date,
        is_monthly=match.group("kind") == "m",
    )
```

- [ ] **Step 4: Run parser tests**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
source .venv/bin/activate
pytest tests/test_parsing.py
```

Expected: PASS.

- [ ] **Step 5: Commit parser helpers**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
git add src/reporter/parsing.py tests/test_parsing.py
git commit -m "Add parsing helpers for Barchart values

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

Expected: commit succeeds.

---

### Task 4: Analyzer and Monthly Signal Classification

**Files:**
- Create: `src/reporter/analyzer.py`
- Create: `tests/test_analyzer.py`

- [ ] **Step 1: Write failing analyzer tests**

Add `tests/test_analyzer.py`:

```python
from datetime import date, datetime

from reporter.analyzer import analyze_snapshot, classify_signal, select_monthly_rows
from reporter.models import ExpirationRow, Signal, Snapshot, Thresholds, TopMetrics


def thresholds() -> Thresholds:
    return Thresholds(
        strong_bullish_volume_max=0.35,
        strong_bullish_oi_max=0.7,
        bullish_volume_max=0.7,
        bullish_oi_max=0.9,
        bearish_volume_min=1.1,
        bearish_oi_min=1.25,
        mixed_oi_min=1.0,
        mixed_oi_max=1.25,
        neutral_volume_min=0.7,
        neutral_volume_max=1.1,
        neutral_oi_max=1.1,
        min_total_volume_for_commentary=1000,
    )


def row(label: str, vol_ratio: float, oi_ratio: float, total_volume: int, is_monthly: bool = True) -> ExpirationRow:
    month, day, year = label[:2], label[3:5], label[6:8]
    return ExpirationRow(
        expiration_label=label,
        expiration_date=date(2000 + int(year), int(month), int(day)),
        dte=30,
        put_volume=int(total_volume * vol_ratio / 2),
        call_volume=max(1, int(total_volume / 2)),
        total_volume=total_volume,
        put_call_volume_ratio=vol_ratio,
        put_open_interest=int(10000 * oi_ratio),
        call_open_interest=10000,
        total_open_interest=int(10000 + 10000 * oi_ratio),
        put_call_open_interest_ratio=oi_ratio,
        implied_volatility=33.3,
        is_monthly=is_monthly,
    )


def test_classify_signal_uses_ordered_thresholds() -> None:
    t = thresholds()
    assert classify_signal(0.20, 0.50, t) is Signal.STRONG_BULLISH
    assert classify_signal(0.50, 0.80, t) is Signal.BULLISH
    assert classify_signal(0.50, 1.10, t) is Signal.MIXED_CAUTION
    assert classify_signal(0.90, 0.80, t) is Signal.NEUTRAL
    assert classify_signal(1.20, 0.80, t) is Signal.BEARISH_HEDGING
    assert classify_signal(0.20, 1.40, t) is Signal.BEARISH_HEDGING


def test_select_monthly_rows_prefers_monthly_expiration() -> None:
    rows = [
        row("06/05/26 (w)", 0.60, 0.80, 5000, is_monthly=False),
        row("06/18/26 (m)", 0.31, 0.54, 111014, is_monthly=True),
        row("07/02/26 (w)", 0.33, 0.31, 15395, is_monthly=False),
        row("07/17/26 (m)", 0.29, 0.43, 69554, is_monthly=True),
    ]

    selected = select_monthly_rows(rows, months=2)

    assert [item.expiration_label for item in selected] == ["06/18/26 (m)", "07/17/26 (m)"]


def test_select_monthly_rows_falls_back_to_highest_volume_when_no_monthly() -> None:
    rows = [
        row("06/05/26 (w)", 0.60, 0.80, 5000, is_monthly=False),
        row("06/12/26 (w)", 0.35, 0.52, 39171, is_monthly=False),
    ]

    selected = select_monthly_rows(rows, months=1)

    assert selected[0].expiration_label == "06/12/26 (w)"


def test_analyze_snapshot_creates_commentary_and_monthly_signals() -> None:
    snapshot = Snapshot(
        symbol="MSFT",
        url="https://www.barchart.com/stocks/quotes/msft/put-call-ratios",
        captured_at=datetime(2026, 6, 2, 21, 30),
        metrics=TopMetrics("07/29/26", 31.62, 33.28, 61.17, 85.0),
        rows=[
            row("06/18/26 (m)", 0.31, 0.54, 111014),
            row("07/17/26 (m)", 0.29, 0.43, 69554),
            row("10/16/26 (m)", 0.89, 1.49, 6748),
        ],
    )

    analysis = analyze_snapshot(snapshot, thresholds(), months=12)

    assert analysis.symbol == "MSFT"
    assert analysis.monthly_signals[0].month == "2026-06"
    assert analysis.monthly_signals[0].signal is Signal.STRONG_BULLISH
    assert analysis.monthly_signals[2].signal is Signal.BEARISH_HEDGING
    assert "2 bullish" in analysis.commentary
    assert "1 bearish" in analysis.commentary
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
source .venv/bin/activate
pytest tests/test_analyzer.py
```

Expected: FAIL because `reporter.analyzer` does not exist.

- [ ] **Step 3: Add analyzer implementation**

Add `src/reporter/analyzer.py`:

```python
from __future__ import annotations

from collections import defaultdict

from reporter.models import ExpirationRow, MonthlySignal, Signal, Snapshot, SymbolAnalysis, Thresholds


def classify_signal(volume_ratio: float, oi_ratio: float, thresholds: Thresholds) -> Signal:
    if volume_ratio <= thresholds.strong_bullish_volume_max and oi_ratio <= thresholds.strong_bullish_oi_max:
        return Signal.STRONG_BULLISH
    if volume_ratio < thresholds.bullish_volume_max and oi_ratio < thresholds.bullish_oi_max:
        return Signal.BULLISH
    if volume_ratio > thresholds.bearish_volume_min or oi_ratio > thresholds.bearish_oi_min:
        return Signal.BEARISH_HEDGING
    if volume_ratio < thresholds.bullish_volume_max and thresholds.mixed_oi_min <= oi_ratio <= thresholds.mixed_oi_max:
        return Signal.MIXED_CAUTION
    if thresholds.neutral_volume_min <= volume_ratio <= thresholds.neutral_volume_max and oi_ratio < thresholds.neutral_oi_max:
        return Signal.NEUTRAL
    return Signal.MIXED


def select_monthly_rows(rows: list[ExpirationRow], months: int = 12) -> list[ExpirationRow]:
    grouped: dict[str, list[ExpirationRow]] = defaultdict(list)
    for item in rows:
        grouped[item.expiration_date.strftime("%Y-%m")].append(item)

    selected: list[ExpirationRow] = []
    for month in sorted(grouped):
        candidates = grouped[month]
        monthly = [item for item in candidates if item.is_monthly]
        pool = monthly if monthly else candidates
        selected.append(max(pool, key=lambda item: (item.total_volume, item.total_open_interest)))
        if len(selected) == months:
            break
    return selected


def _count_signals(signals: list[MonthlySignal]) -> tuple[int, int, int, int]:
    bullish = sum(1 for item in signals if item.signal in {Signal.STRONG_BULLISH, Signal.BULLISH})
    neutral = sum(1 for item in signals if item.signal is Signal.NEUTRAL)
    mixed = sum(1 for item in signals if item.signal in {Signal.MIXED, Signal.MIXED_CAUTION})
    bearish = sum(1 for item in signals if item.signal is Signal.BEARISH_HEDGING)
    return bullish, neutral, mixed, bearish


def _commentary(symbol: str, signals: list[MonthlySignal]) -> str:
    bullish, neutral, mixed, bearish = _count_signals(signals)
    if not signals:
        return f"{symbol}: no expiration rows were available for analysis."
    if bullish > bearish and bullish >= mixed:
        tone = "bullish overall"
    elif bearish > bullish and bearish >= mixed:
        tone = "bearish or hedging-heavy overall"
    else:
        tone = "mixed overall"
    return f"{symbol}: {tone} with {bullish} bullish, {neutral} neutral, {mixed} mixed, and {bearish} bearish monthly signals."


def analyze_snapshot(snapshot: Snapshot, thresholds: Thresholds, months: int = 12) -> SymbolAnalysis:
    monthly_rows = select_monthly_rows(snapshot.rows, months=months)
    monthly_signals = [
        MonthlySignal(
            month=row.expiration_date.strftime("%Y-%m"),
            expiration_label=row.expiration_label,
            put_call_volume_ratio=row.put_call_volume_ratio,
            put_call_open_interest_ratio=row.put_call_open_interest_ratio,
            total_volume=row.total_volume,
            total_open_interest=row.total_open_interest,
            signal=classify_signal(row.put_call_volume_ratio, row.put_call_open_interest_ratio, thresholds),
        )
        for row in monthly_rows
    ]
    return SymbolAnalysis(
        symbol=snapshot.symbol,
        captured_at=snapshot.captured_at,
        metrics=snapshot.metrics,
        monthly_signals=monthly_signals,
        commentary=_commentary(snapshot.symbol, monthly_signals),
    )
```

- [ ] **Step 4: Run analyzer tests**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
source .venv/bin/activate
pytest tests/test_analyzer.py
```

Expected: PASS.

- [ ] **Step 5: Commit analyzer**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
git add src/reporter/analyzer.py tests/test_analyzer.py
git commit -m "Add monthly put-call signal analyzer

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

Expected: commit succeeds.

---

### Task 5: SQLite History Store

**Files:**
- Create: `src/reporter/history.py`
- Create: `tests/test_history.py`

- [ ] **Step 1: Write failing history tests**

Add `tests/test_history.py`:

```python
from datetime import date, datetime, timedelta
from pathlib import Path

from reporter.history import HistoryStore
from reporter.models import ExpirationRow, Snapshot, TopMetrics


def snapshot(symbol: str, captured_at: datetime, ratio: float) -> Snapshot:
    return Snapshot(
        symbol=symbol,
        url=f"https://www.barchart.com/stocks/quotes/{symbol.lower()}/put-call-ratios",
        captured_at=captured_at,
        metrics=TopMetrics("07/29/26", 31.62, 33.28, 61.17, 85.0),
        rows=[
            ExpirationRow(
                expiration_label="06/18/26 (m)",
                expiration_date=date(2026, 6, 18),
                dte=16,
                put_volume=26096,
                call_volume=84918,
                total_volume=111014,
                put_call_volume_ratio=ratio,
                put_open_interest=244398,
                call_open_interest=454545,
                total_open_interest=698943,
                put_call_open_interest_ratio=0.54,
                implied_volatility=32.94,
                is_monthly=True,
            )
        ],
    )


def test_history_store_round_trips_snapshot(tmp_path: Path) -> None:
    store = HistoryStore(tmp_path / "history.sqlite3")
    current = snapshot("MSFT", datetime(2026, 6, 2, 21, 30), 0.31)

    store.save_snapshot(current)
    loaded = store.latest_snapshot("MSFT")

    assert loaded is not None
    assert loaded.symbol == "MSFT"
    assert loaded.rows[0].put_call_volume_ratio == 0.31


def test_history_store_finds_prior_day_week_month(tmp_path: Path) -> None:
    store = HistoryStore(tmp_path / "history.sqlite3")
    now = datetime(2026, 6, 30, 21, 30)
    store.save_snapshot(snapshot("MSFT", now - timedelta(days=1), 0.40))
    store.save_snapshot(snapshot("MSFT", now - timedelta(days=7), 0.50))
    store.save_snapshot(snapshot("MSFT", now - timedelta(days=30), 0.60))
    store.save_snapshot(snapshot("MSFT", now, 0.31))

    priors = store.prior_snapshots("MSFT", now)

    assert priors["previous_day"].rows[0].put_call_volume_ratio == 0.40
    assert priors["previous_week"].rows[0].put_call_volume_ratio == 0.50
    assert priors["previous_month"].rows[0].put_call_volume_ratio == 0.60
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
source .venv/bin/activate
pytest tests/test_history.py
```

Expected: FAIL because `reporter.history` does not exist.

- [ ] **Step 3: Add SQLite history store**

Add `src/reporter/history.py`:

```python
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from reporter.models import ExpirationRow, Snapshot, TopMetrics


class HistoryStore:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    url TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    metrics_json TEXT NOT NULL,
                    rows_json TEXT NOT NULL,
                    UNIQUE(symbol, captured_at)
                )
                """
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_symbol_time ON snapshots(symbol, captured_at)")

    def save_snapshot(self, snapshot: Snapshot) -> None:
        rows_json = json.dumps([self._row_to_json(row) for row in snapshot.rows])
        metrics_json = json.dumps(asdict(snapshot.metrics))
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO snapshots(symbol, url, captured_at, metrics_json, rows_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (snapshot.symbol, snapshot.url, snapshot.captured_at.isoformat(), metrics_json, rows_json),
            )

    def latest_snapshot(self, symbol: str) -> Snapshot | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM snapshots
                WHERE symbol = ?
                ORDER BY captured_at DESC
                LIMIT 1
                """,
                (symbol.upper(),),
            ).fetchone()
        return self._snapshot_from_row(row) if row else None

    def prior_snapshots(self, symbol: str, captured_at: datetime) -> dict[str, Snapshot | None]:
        return {
            "previous_day": self._most_recent_before(symbol, captured_at),
            "previous_week": self._nearest_to(symbol, captured_at, timedelta(days=7)),
            "previous_month": self._nearest_to(symbol, captured_at, timedelta(days=30)),
        }

    def _most_recent_before(self, symbol: str, captured_at: datetime) -> Snapshot | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM snapshots
                WHERE symbol = ? AND captured_at < ?
                ORDER BY captured_at DESC
                LIMIT 1
                """,
                (symbol.upper(), captured_at.isoformat()),
            ).fetchone()
        return self._snapshot_from_row(row) if row else None

    def _nearest_to(self, symbol: str, captured_at: datetime, offset: timedelta) -> Snapshot | None:
        target = captured_at - offset
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM snapshots
                WHERE symbol = ? AND captured_at < ?
                ORDER BY ABS(julianday(captured_at) - julianday(?)) ASC
                LIMIT 1
                """,
                (symbol.upper(), captured_at.isoformat(), target.isoformat()),
            ).fetchone()
        return self._snapshot_from_row(row) if row else None

    @staticmethod
    def _row_to_json(row: ExpirationRow) -> dict[str, Any]:
        data = asdict(row)
        data["expiration_date"] = row.expiration_date.isoformat()
        return data

    @staticmethod
    def _snapshot_from_row(row: sqlite3.Row) -> Snapshot:
        metrics_data = json.loads(row["metrics_json"])
        rows_data = json.loads(row["rows_json"])
        return Snapshot(
            symbol=row["symbol"],
            url=row["url"],
            captured_at=datetime.fromisoformat(row["captured_at"]),
            metrics=TopMetrics(**metrics_data),
            rows=[
                ExpirationRow(
                    **{
                        **item,
                        "expiration_date": date.fromisoformat(item["expiration_date"]),
                    }
                )
                for item in rows_data
            ],
        )
```

- [ ] **Step 4: Run history tests**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
source .venv/bin/activate
pytest tests/test_history.py
```

Expected: PASS.

- [ ] **Step 5: Commit history store**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
git add src/reporter/history.py tests/test_history.py
git commit -m "Add SQLite snapshot history

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

Expected: commit succeeds.

---

### Task 6: Drift Analysis

**Files:**
- Create: `src/reporter/drift.py`
- Create: `tests/test_drift.py`

- [ ] **Step 1: Write failing drift tests**

Add `tests/test_drift.py`:

```python
from datetime import datetime

from reporter.drift import build_drift
from reporter.models import DriftItem, MonthlySignal, Signal, SymbolAnalysis, Thresholds, TopMetrics


def thresholds() -> Thresholds:
    return Thresholds(0.35, 0.7, 0.7, 0.9, 1.1, 1.25, 1.0, 1.25, 0.7, 1.1, 1.1, 1000)


def analysis(symbol: str, month_signal: Signal, vol_ratio: float, oi_ratio: float) -> SymbolAnalysis:
    return SymbolAnalysis(
        symbol=symbol,
        captured_at=datetime(2026, 6, 30, 21, 30),
        metrics=TopMetrics("07/29/26", 31.0, 33.0, 60.0, 80.0),
        monthly_signals=[
            MonthlySignal("2026-06", "06/18/26 (m)", vol_ratio, oi_ratio, 10000, 20000, month_signal),
            MonthlySignal("2026-07", "07/17/26 (m)", 0.30, 0.50, 15000, 25000, Signal.STRONG_BULLISH),
        ],
        commentary="summary",
    )


def test_build_drift_reports_missing_prior() -> None:
    current = analysis("MSFT", Signal.BULLISH, 0.50, 0.80)

    drift = build_drift(current, {"previous_day": None}, thresholds())

    assert drift == [DriftItem(period="previous_day", summary="No previous_day snapshot is available yet.", signal_flips=[])]


def test_build_drift_reports_signal_flip_and_ratio_changes() -> None:
    current = analysis("MSFT", Signal.BEARISH_HEDGING, 1.20, 1.40)
    previous = analysis("MSFT", Signal.BULLISH, 0.50, 0.80)

    drift = build_drift(current, {"previous_day": previous}, thresholds())

    assert len(drift) == 1
    assert "bearish increased" in drift[0].summary
    assert "2026-06: Bullish -> Bearish / hedging-heavy" in drift[0].signal_flips
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
source .venv/bin/activate
pytest tests/test_drift.py
```

Expected: FAIL because `reporter.drift` does not exist.

- [ ] **Step 3: Add drift implementation**

Add `src/reporter/drift.py`:

```python
from __future__ import annotations

from reporter.models import DriftItem, MonthlySignal, Signal, SymbolAnalysis, Thresholds


def _index(signals: list[MonthlySignal]) -> dict[str, MonthlySignal]:
    return {signal.month: signal for signal in signals}


def _bearish_count(signals: list[MonthlySignal]) -> int:
    return sum(1 for signal in signals if signal.signal is Signal.BEARISH_HEDGING)


def _bullish_count(signals: list[MonthlySignal]) -> int:
    return sum(1 for signal in signals if signal.signal in {Signal.STRONG_BULLISH, Signal.BULLISH})


def _average_volume_ratio(signals: list[MonthlySignal]) -> float:
    return sum(signal.put_call_volume_ratio for signal in signals) / max(1, len(signals))


def _average_oi_ratio(signals: list[MonthlySignal]) -> float:
    return sum(signal.put_call_open_interest_ratio for signal in signals) / max(1, len(signals))


def _direction(current: float, previous: float, label: str) -> str:
    delta = current - previous
    if abs(delta) < 0.05:
        return f"{label} was mostly unchanged"
    direction = "increased" if delta > 0 else "decreased"
    return f"{label} {direction} by {delta:+.2f}"


def build_drift(
    current: SymbolAnalysis,
    priors: dict[str, SymbolAnalysis | None],
    thresholds: Thresholds,
) -> list[DriftItem]:
    items: list[DriftItem] = []
    for period, prior in priors.items():
        if prior is None:
            items.append(DriftItem(period=period, summary=f"No {period} snapshot is available yet."))
            continue

        current_by_month = _index(current.monthly_signals)
        prior_by_month = _index(prior.monthly_signals)
        flips: list[str] = []
        for month in sorted(current_by_month.keys() & prior_by_month.keys()):
            current_signal = current_by_month[month].signal
            prior_signal = prior_by_month[month].signal
            if current_signal is not prior_signal:
                flips.append(f"{month}: {prior_signal.value} -> {current_signal.value}")

        bullish_delta = _bullish_count(current.monthly_signals) - _bullish_count(prior.monthly_signals)
        bearish_delta = _bearish_count(current.monthly_signals) - _bearish_count(prior.monthly_signals)
        volume_text = _direction(
            _average_volume_ratio(current.monthly_signals),
            _average_volume_ratio(prior.monthly_signals),
            "average put/call volume ratio",
        )
        oi_text = _direction(
            _average_oi_ratio(current.monthly_signals),
            _average_oi_ratio(prior.monthly_signals),
            "average put/call open-interest ratio",
        )
        bullish_text = "bullish increased" if bullish_delta > 0 else "bullish decreased" if bullish_delta < 0 else "bullish count unchanged"
        bearish_text = "bearish increased" if bearish_delta > 0 else "bearish decreased" if bearish_delta < 0 else "bearish count unchanged"
        summary = f"{bullish_text}; {bearish_text}; {volume_text}; {oi_text}."
        items.append(DriftItem(period=period, summary=summary, signal_flips=flips))
    return items
```

- [ ] **Step 4: Run drift tests**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
source .venv/bin/activate
pytest tests/test_drift.py
```

Expected: PASS.

- [ ] **Step 5: Commit drift analyzer**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
git add src/reporter/drift.py tests/test_drift.py
git commit -m "Add day week month drift summaries

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

Expected: commit succeeds.

---

### Task 7: Report Rendering

**Files:**
- Create: `src/reporter/reporting.py`
- Create: `tests/test_reporting.py`

- [ ] **Step 1: Write failing report tests**

Add `tests/test_reporting.py`:

```python
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
    assert (tmp_path / "NOW-expirations.csv").exists()
    html = bundle.html_path.read_text(encoding="utf-8")
    assert "NOW" in html
    assert "06/18/26 (m)" in html
    assert "Mixed" in html
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
source .venv/bin/activate
pytest tests/test_reporting.py
```

Expected: FAIL because `reporter.reporting` does not exist.

- [ ] **Step 3: Add report renderer**

Add `src/reporter/reporting.py`:

```python
from __future__ import annotations

import csv
from datetime import datetime
from html import escape
from pathlib import Path

from reporter.models import ReportBundle, SymbolReport


def _metrics_html(report: SymbolReport) -> str:
    if report.snapshot is None:
        return "<p>No metrics available.</p>"
    metrics = report.snapshot.metrics
    return (
        "<table><tr><th>Latest Earnings</th><th>IV</th><th>Historic Vol</th><th>IV Rank</th><th>IV Percentile</th></tr>"
        f"<tr><td>{escape(str(metrics.latest_earnings))}</td>"
        f"<td>{metrics.implied_volatility}</td><td>{metrics.historic_volatility}</td>"
        f"<td>{metrics.iv_rank}</td><td>{metrics.iv_percentile}</td></tr></table>"
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


def _raw_csv(report: SymbolReport, archive_dir: Path) -> None:
    if report.snapshot is None:
        return
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


def render_reports(generated_at: datetime, symbol_reports: list[SymbolReport], archive_dir: Path) -> ReportBundle:
    archive_dir.mkdir(parents=True, exist_ok=True)
    html_sections = [
        "<html><body>",
        f"<h1>Daily Options Put/Call Report - {generated_at:%Y-%m-%d}</h1>",
    ]
    markdown_sections = [f"# Daily Options Put/Call Report - {generated_at:%Y-%m-%d}", ""]
    failures = [report for report in symbol_reports if report.error]
    if failures:
        html_sections.append("<h2>Failures</h2><ul>")
        for failure in failures:
            html_sections.append(f"<li>{escape(failure.symbol)}: {escape(failure.error or '')}</li>")
        html_sections.append("</ul>")

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
        markdown_sections.extend([f"## {report.symbol}", report.analysis.commentary if report.analysis else "", ""])
        _raw_csv(report, archive_dir)

    html_sections.append(f"<p>Archive: {escape(str(archive_dir))}</p>")
    html_sections.append("</body></html>")

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
```

- [ ] **Step 4: Run report tests**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
source .venv/bin/activate
pytest tests/test_reporting.py
```

Expected: PASS.

- [ ] **Step 5: Commit report renderer**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
git add src/reporter/reporting.py tests/test_reporting.py
git commit -m "Add report rendering and CSV export

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

Expected: commit succeeds.

---

### Task 8: Keychain and Gmail Sender

**Files:**
- Create: `src/reporter/keychain.py`
- Create: `src/reporter/emailer.py`
- Create: `tests/test_keychain_emailer.py`

- [ ] **Step 1: Write failing Keychain and email tests**

Add `tests/test_keychain_emailer.py`:

```python
from email.message import EmailMessage
from pathlib import Path

import pytest

from reporter.emailer import send_email_report
from reporter.keychain import KeychainError, get_password, set_password
from reporter.models import EmailConfig


class Completed:
    def __init__(self, stdout: str = "") -> None:
        self.stdout = stdout


def test_get_password_calls_security_find(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(args, check, capture_output, text):
        calls.append(args)
        return Completed(stdout="app-password\n")

    monkeypatch.setattr("subprocess.run", fake_run)

    assert get_password("service", "user@gmail.com") == "app-password"
    assert calls[0][:3] == ["security", "find-generic-password", "-a"]


def test_set_password_calls_security_add(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(args, check, capture_output, text):
        calls.append(args)
        return Completed()

    monkeypatch.setattr("subprocess.run", fake_run)

    set_password("service", "user@gmail.com", "secret")
    assert "add-generic-password" in calls[0]
    assert "-U" in calls[0]


def test_get_password_raises_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args, check, capture_output, text):
        raise OSError("security missing")

    monkeypatch.setattr("subprocess.run", fake_run)

    with pytest.raises(KeychainError, match="Keychain"):
        get_password("service", "user@gmail.com")


def test_send_email_report_uses_tls_and_login(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    html_path = tmp_path / "report.html"
    html_path.write_text("<h1>Report</h1>", encoding="utf-8")
    events: list[str] = []

    class FakeSMTP:
        def __init__(self, host: str, port: int) -> None:
            events.append(f"connect:{host}:{port}")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            events.append("close")

        def starttls(self) -> None:
            events.append("tls")

        def login(self, user: str, password: str) -> None:
            events.append(f"login:{user}:{password}")

        def send_message(self, message: EmailMessage) -> None:
            events.append(f"send:{message['To']}")

    monkeypatch.setattr("smtplib.SMTP", FakeSMTP)

    send_email_report(
        email_config=EmailConfig("sender@gmail.com", "recipient@gmail.com"),
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        app_password="abc123",
        subject="Daily report",
        html_path=html_path,
    )

    assert events == [
        "connect:smtp.gmail.com:587",
        "tls",
        "login:sender@gmail.com:abc123",
        "send:recipient@gmail.com",
        "close",
    ]
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
source .venv/bin/activate
pytest tests/test_keychain_emailer.py
```

Expected: FAIL because `reporter.keychain` and `reporter.emailer` do not exist.

- [ ] **Step 3: Add Keychain wrapper**

Add `src/reporter/keychain.py`:

```python
from __future__ import annotations

import subprocess


class KeychainError(RuntimeError):
    pass


def get_password(service: str, account: str) -> str:
    try:
        completed = subprocess.run(
            ["security", "find-generic-password", "-a", account, "-s", service, "-w"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception as exc:
        raise KeychainError(f"Keychain password not found for account '{account}' and service '{service}'") from exc
    password = completed.stdout.strip()
    if not password:
        raise KeychainError(f"Keychain returned an empty password for account '{account}' and service '{service}'")
    return password


def set_password(service: str, account: str, password: str) -> None:
    if not password:
        raise KeychainError("Cannot store an empty Gmail App Password in Keychain")
    try:
        subprocess.run(
            ["security", "add-generic-password", "-a", account, "-s", service, "-w", password, "-U"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception as exc:
        raise KeychainError(f"Unable to store Gmail App Password in Keychain for account '{account}'") from exc
```

- [ ] **Step 4: Add Gmail sender**

Add `src/reporter/emailer.py`:

```python
from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path

from reporter.models import EmailConfig


class EmailError(RuntimeError):
    pass


def send_email_report(
    email_config: EmailConfig,
    smtp_host: str,
    smtp_port: int,
    app_password: str,
    subject: str,
    html_path: Path,
) -> None:
    html = html_path.read_text(encoding="utf-8")
    message = EmailMessage()
    message["From"] = email_config.from_email
    message["To"] = email_config.to_email
    message["Subject"] = subject
    message.set_content("Daily options put/call report is attached as HTML content.")
    message.add_alternative(html, subtype="html")

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as smtp:
            smtp.starttls()
            smtp.login(email_config.from_email, app_password)
            smtp.send_message(message)
    except Exception as exc:
        raise EmailError(f"Failed to send report email to {email_config.to_email}") from exc
```

- [ ] **Step 5: Run Keychain and email tests**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
source .venv/bin/activate
pytest tests/test_keychain_emailer.py
```

Expected: PASS.

- [ ] **Step 6: Commit Keychain and email sender**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
git add src/reporter/keychain.py src/reporter/emailer.py tests/test_keychain_emailer.py
git commit -m "Add Keychain backed Gmail sender

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

Expected: commit succeeds.

---

### Task 9: Browser Collector

**Files:**
- Create: `src/reporter/collector.py`
- Create: `tests/fixtures/barchart_put_call_sample.html`
- Create: `tests/test_collector.py`

- [ ] **Step 1: Add a stable Barchart-like fixture**

Add `tests/fixtures/barchart_put_call_sample.html`:

```html
<!doctype html>
<html>
  <body>
    <div class="metrics">
      <span>Latest Earnings:</span><strong>07/29/26</strong>
      <span>Implied Volatility:</span><strong>31.62%</strong>
      <span>Historic Volatility:</span><strong>33.28%</strong>
      <span>IV Rank:</span><strong>61.17%</strong>
      <span>IV Percentile:</span><strong>85%</strong>
    </div>
    <table>
      <thead>
        <tr>
          <th>Expiration Date</th>
          <th>DTE</th>
          <th>Put Vol</th>
          <th>Call Vol</th>
          <th>Total Vol</th>
          <th>Put/Call Vol</th>
          <th>Put OI</th>
          <th>Call OI</th>
          <th>Total OI</th>
          <th>Put/Call OI</th>
          <th>Implied Volatility</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>06/18/26 (m)</td><td>16</td><td>26,096</td><td>84,918</td><td>111,014</td><td>0.31</td>
          <td>244,398</td><td>454,545</td><td>698,943</td><td>0.54</td><td>32.94%</td>
        </tr>
        <tr>
          <td>07/17/26 (m)</td><td>45</td><td>15,690</td><td>53,864</td><td>69,554</td><td>0.29</td>
          <td>117,940</td><td>271,884</td><td>389,824</td><td>0.43</td><td>31.11%</td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
```

- [ ] **Step 2: Write failing collector tests**

Add `tests/test_collector.py`:

```python
from datetime import datetime
from pathlib import Path

import pytest

from reporter.collector import collect_from_html


@pytest.mark.asyncio
async def test_collect_from_html_extracts_metrics_and_rows(tmp_path: Path) -> None:
    html = Path("tests/fixtures/barchart_put_call_sample.html").read_text(encoding="utf-8")

    snapshot = await collect_from_html(
        symbol="MSFT",
        url="https://www.barchart.com/stocks/quotes/msft/put-call-ratios",
        html=html,
        captured_at=datetime(2026, 6, 2, 21, 30),
    )

    assert snapshot.symbol == "MSFT"
    assert snapshot.metrics.latest_earnings == "07/29/26"
    assert snapshot.metrics.implied_volatility == 31.62
    assert len(snapshot.rows) == 2
    assert snapshot.rows[0].expiration_label == "06/18/26 (m)"
    assert snapshot.rows[0].put_call_volume_ratio == 0.31
    assert snapshot.rows[0].is_monthly is True
```

- [ ] **Step 3: Add pytest-asyncio dependency**

Modify `pyproject.toml` dev dependencies:

```toml
[project.optional-dependencies]
dev = [
  "pytest>=8,<9",
  "pytest-asyncio>=0.23,<1"
]
```

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Expected: install succeeds.

- [ ] **Step 4: Run tests and verify they fail**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
source .venv/bin/activate
pytest tests/test_collector.py
```

Expected: FAIL because `reporter.collector` does not exist.

- [ ] **Step 5: Add collector implementation**

Add `src/reporter/collector.py`:

```python
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

from reporter.models import ExpirationRow, Snapshot, SymbolConfig, TopMetrics
from reporter.parsing import parse_expiration_label, parse_float, parse_int, parse_percent


class CollectionError(RuntimeError):
    pass


async def collect_symbol(symbol_config: SymbolConfig, captured_at: datetime, archive_dir: Path) -> Snapshot:
    archive_dir.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(symbol_config.url, wait_until="networkidle", timeout=60000)
            await page.get_by_text("Expiration Date").first.wait_for(timeout=30000)
            html = await page.content()
            snapshot = await collect_from_html(symbol_config.symbol, symbol_config.url, html, captured_at)
            (archive_dir / f"{symbol_config.symbol}-raw.html").write_text(html, encoding="utf-8")
            (archive_dir / f"{symbol_config.symbol}-raw.json").write_text(_snapshot_json(snapshot), encoding="utf-8")
            return snapshot
        except Exception as exc:
            html_path = archive_dir / f"{symbol_config.symbol}-failure.html"
            png_path = archive_dir / f"{symbol_config.symbol}-failure.png"
            html_path.write_text(await page.content(), encoding="utf-8")
            await page.screenshot(path=png_path, full_page=True)
            raise CollectionError(f"{symbol_config.symbol} extraction failed; diagnostics saved to {html_path} and {png_path}") from exc
        finally:
            await browser.close()


async def collect_from_html(symbol: str, url: str, html: str, captured_at: datetime) -> Snapshot:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.set_content(html)
            metrics = await _extract_metrics(page)
            rows = await _extract_rows(page)
            if not rows:
                raise CollectionError(f"{symbol} extraction produced zero expiration rows")
            return Snapshot(symbol=symbol.upper(), url=url, captured_at=captured_at, metrics=metrics, rows=rows)
        finally:
            await browser.close()


async def _extract_metrics(page) -> TopMetrics:
    text = await page.locator("body").inner_text()

    def after(label: str) -> str | None:
        index = text.find(label)
        if index == -1:
            return None
        value = text[index + len(label):].strip().splitlines()[0].strip()
        return value.split()[0] if value else None

    return TopMetrics(
        latest_earnings=after("Latest Earnings:"),
        implied_volatility=parse_percent(after("Implied Volatility:")),
        historic_volatility=parse_percent(after("Historic Volatility:")),
        iv_rank=parse_percent(after("IV Rank:")),
        iv_percentile=parse_percent(after("IV Percentile:")),
    )


async def _extract_rows(page) -> list[ExpirationRow]:
    rows: list[ExpirationRow] = []
    table_rows = await page.locator("table tr").all()
    for table_row in table_rows[1:]:
        cells = [cell.strip() for cell in await table_row.locator("th,td").all_inner_texts()]
        if len(cells) < 11 or "/" not in cells[0]:
            continue
        parsed = parse_expiration_label(cells[0])
        rows.append(
            ExpirationRow(
                expiration_label=cells[0],
                expiration_date=parsed.expiration_date,
                dte=parse_int(cells[1]),
                put_volume=parse_int(cells[2]),
                call_volume=parse_int(cells[3]),
                total_volume=parse_int(cells[4]),
                put_call_volume_ratio=parse_float(cells[5]),
                put_open_interest=parse_int(cells[6]),
                call_open_interest=parse_int(cells[7]),
                total_open_interest=parse_int(cells[8]),
                put_call_open_interest_ratio=parse_float(cells[9]),
                implied_volatility=parse_percent(cells[10]),
                is_monthly=parsed.is_monthly,
            )
        )
    return rows


def _snapshot_json(snapshot: Snapshot) -> str:
    data = asdict(snapshot)
    data["captured_at"] = snapshot.captured_at.isoformat()
    data["metrics"] = asdict(snapshot.metrics)
    data["rows"] = [
        {
            **asdict(row),
            "expiration_date": row.expiration_date.isoformat(),
        }
        for row in snapshot.rows
    ]
    return json.dumps(data, indent=2)
```

- [ ] **Step 6: Run collector tests**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
source .venv/bin/activate
pytest tests/test_collector.py
```

Expected: PASS.

- [ ] **Step 7: Commit browser collector**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
git add pyproject.toml src/reporter/collector.py tests/fixtures/barchart_put_call_sample.html tests/test_collector.py
git commit -m "Add Playwright Barchart collector

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

Expected: commit succeeds.

---

### Task 10: CLI Orchestration

**Files:**
- Create: `src/reporter/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Add `tests/test_cli.py`:

```python
import json
from datetime import date, datetime
from pathlib import Path

from reporter.cli import main
from reporter.models import ExpirationRow, Snapshot, SymbolConfig, TopMetrics


def config(path: Path) -> None:
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
                    "min_total_volume_for_commentary": 1000
                },
                "symbols": [{"symbol": "NOW", "url": "https://www.barchart.com/stocks/quotes/now/put-call-ratios"}],
            }
        ),
        encoding="utf-8",
    )


def sample_snapshot(symbol_config: SymbolConfig, captured_at: datetime, archive_dir: Path) -> Snapshot:
    return Snapshot(
        symbol=symbol_config.symbol,
        url=symbol_config.url,
        captured_at=captured_at,
        metrics=TopMetrics("07/22/26", 30.86, 37.28, 29.62, 39.0),
        rows=[
            ExpirationRow("06/18/26 (m)", date(2026, 6, 18), 16, 11737, 26979, 38716, 0.44, 202821, 226097, 428918, 0.90, 31.92, True)
        ],
    )


def test_run_no_email_creates_report(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "symbols.json"
    config(config_path)

    async def fake_collect(symbol_config, captured_at, archive_dir):
        return sample_snapshot(symbol_config, captured_at, archive_dir)

    monkeypatch.setattr("reporter.cli.collect_symbol", fake_collect)

    exit_code = main(["run", "--config", str(config_path), "--no-email", "--run-date", "2026-06-02T21:30:00"])

    assert exit_code == 0
    assert list((tmp_path / "archive" / "2026-06-02").glob("report.html"))


def test_setup_email_writes_local_email_config_and_keychain(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "symbols.json"
    config(config_path)
    stored: dict[str, str] = {}
    answers = iter(["sender@gmail.com", "recipient@gmail.com", "app-password"])

    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    monkeypatch.setattr("getpass.getpass", lambda prompt: next(answers))
    monkeypatch.setattr("reporter.cli.set_password", lambda service, account, password: stored.update({"service": service, "account": account, "password": password}))

    exit_code = main(["setup-email", "--config", str(config_path), "--email-config", str(tmp_path / "email.local.json")])

    assert exit_code == 0
    assert stored == {
        "service": "options-put-call-reporter:gmail-app-password",
        "account": "sender@gmail.com",
        "password": "app-password",
    }
    email_config = json.loads((tmp_path / "email.local.json").read_text(encoding="utf-8"))
    assert email_config == {"from_email": "sender@gmail.com", "to_email": "recipient@gmail.com"}
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
source .venv/bin/activate
pytest tests/test_cli.py
```

Expected: FAIL because `reporter.cli` does not exist.

- [ ] **Step 3: Add CLI implementation**

Add `src/reporter/cli.py`:

```python
from __future__ import annotations

import argparse
import asyncio
import getpass
import json
from datetime import datetime
from pathlib import Path

from reporter.analyzer import analyze_snapshot
from reporter.collector import CollectionError, collect_symbol
from reporter.config import load_config
from reporter.drift import build_drift
from reporter.emailer import send_email_report
from reporter.history import HistoryStore
from reporter.keychain import get_password, set_password
from reporter.models import EmailConfig, Signal, SymbolAnalysis, SymbolReport
from reporter.reporting import render_reports


def _load_email_config(path: Path) -> EmailConfig:
    data = json.loads(path.read_text(encoding="utf-8"))
    return EmailConfig(from_email=data["from_email"], to_email=data["to_email"])


def _write_email_config(path: Path, email_config: EmailConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"from_email": email_config.from_email, "to_email": email_config.to_email}, indent=2), encoding="utf-8")


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
            symbol_reports.append(SymbolReport(symbol=symbol_config.symbol, snapshot=None, analysis=None, drift=[], error=str(exc)))

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
```

- [ ] **Step 4: Run CLI tests**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
source .venv/bin/activate
pytest tests/test_cli.py
```

Expected: PASS.

- [ ] **Step 5: Run full test suite**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
source .venv/bin/activate
pytest
```

Expected: PASS.

- [ ] **Step 6: Commit CLI orchestration**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
git add src/reporter/cli.py tests/test_cli.py
git commit -m "Add daily report CLI orchestration

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

Expected: commit succeeds.

---

### Task 11: Scheduler Scripts

**Files:**
- Create: `scripts/run_daily.sh`
- Create: `scripts/install_launch_agent.sh`
- Modify: `README.md`

- [ ] **Step 1: Add daily runner script**

Add `scripts/run_daily.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/Users/sri/personal/options-put-call-reporter"
cd "$PROJECT_DIR"
source "$PROJECT_DIR/.venv/bin/activate"
options-put-call-report run --send-email >> "$PROJECT_DIR/archive/runner.log" 2>&1
```

- [ ] **Step 2: Add launchd installer script**

Add `scripts/install_launch_agent.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/Users/sri/personal/options-put-call-reporter"
LABEL="com.sri.options-put-call-reporter"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

mkdir -p "$HOME/Library/LaunchAgents"
chmod +x "$PROJECT_DIR/scripts/run_daily.sh"

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PROJECT_DIR/scripts/run_daily.sh</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$PROJECT_DIR</string>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>14</integer>
    <key>Minute</key>
    <integer>30</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>$PROJECT_DIR/archive/launchd.out.log</string>
  <key>StandardErrorPath</key>
  <string>$PROJECT_DIR/archive/launchd.err.log</string>
</dict>
</plist>
PLIST

launchctl unload "$PLIST" >/dev/null 2>&1 || true
launchctl load "$PLIST"
launchctl list | grep "$LABEL"
```

- [ ] **Step 3: Make scripts executable**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
chmod +x scripts/run_daily.sh scripts/install_launch_agent.sh
```

Expected: command exits successfully.

- [ ] **Step 4: Update README scheduler section**

Modify `README.md` scheduler section to include:

````markdown
## Scheduler

Before installing the scheduler, confirm that a manual email run succeeds:

```bash
source .venv/bin/activate
options-put-call-report run --send-email
```

Install the launchd job:

```bash
./scripts/install_launch_agent.sh
```

Check scheduler status:

```bash
launchctl list | grep com.sri.options-put-call-reporter
```

Logs are written to:

- `archive/runner.log`
- `archive/launchd.out.log`
- `archive/launchd.err.log`
````

- [ ] **Step 5: Run full tests**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
source .venv/bin/activate
pytest
```

Expected: PASS.

- [ ] **Step 6: Commit scheduler scripts**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
git add scripts/run_daily.sh scripts/install_launch_agent.sh README.md
git commit -m "Add launchd scheduler scripts

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

Expected: commit succeeds.

---

### Task 12: End-to-End Validation and Documentation Polish

**Files:**
- Modify: `README.md`
- Generated and ignored: `archive/YYYY-MM-DD/`
- Generated and ignored: `data/history.sqlite3`

- [ ] **Step 1: Run the full unit test suite**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
source .venv/bin/activate
pytest
```

Expected: PASS.

- [ ] **Step 2: Run a no-email live collection**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
source .venv/bin/activate
options-put-call-report run --no-email
```

Expected: exits `0` if at least one symbol succeeds, prints `Report written to archive/YYYY-MM-DD/report.html`, and creates:

- `archive/YYYY-MM-DD/report.html`
- `archive/YYYY-MM-DD/report.md`
- one `*-expirations.csv` file for each successful symbol
- `data/history.sqlite3`

- [ ] **Step 3: Inspect extraction failures if any**

If the no-email run reports failures, open the diagnostic files named in the report:

```bash
open archive/$(date +%F)/*-failure.html
open archive/$(date +%F)/*-failure.png
```

Expected: any failing symbol has saved diagnostics that show whether Barchart blocked loading, changed markup, or delayed the table.

- [ ] **Step 4: Run the email setup command**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
source .venv/bin/activate
options-put-call-report setup-email
```

Expected: prompts for sender email, recipient email, and Gmail App Password; writes `config/email.local.json`; stores the app password in Keychain.

- [ ] **Step 5: Run a live email send**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
source .venv/bin/activate
options-put-call-report run --send-email
```

Expected: exits `0` if at least one symbol succeeds, writes the report archive, and sends an email with subject containing `Options Put/Call Report`.

- [ ] **Step 6: Install scheduler after email send succeeds**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
./scripts/install_launch_agent.sh
```

Expected: output includes `com.sri.options-put-call-reporter`.

- [ ] **Step 7: Update README with any observed live constraints**

If the live Barchart run needs a longer wait or a different table selector, document the exact observed behavior and the implemented setting in `README.md` under a new section:

```markdown
## Live collection notes

The collector waits for the Barchart expiration table before extracting rows. If a symbol fails, the run saves HTML and PNG diagnostics in the daily archive folder.
```

- [ ] **Step 8: Run final verification**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
source .venv/bin/activate
pytest
git --no-pager status --short
```

Expected: tests pass. Git status shows only intended README changes and ignored generated files.

- [ ] **Step 9: Commit validation documentation**

Run:

```bash
cd /Users/sri/personal/options-put-call-reporter
git add README.md
git commit -m "Document live report validation

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

Expected: commit succeeds if README changed. If README did not change, skip this commit.

---

## Self-Review

Spec coverage:

- Watchlist symbols and Barchart URLs: Task 1.
- Daily after-close schedule: Task 11.
- Manual command: Task 10.
- Browser collection and diagnostics: Task 9.
- Raw JSON/CSV/HTML/Markdown archive: Tasks 7, 9, and 10.
- SQLite history store: Task 5.
- Monthly signal analysis: Task 4.
- Previous day/week/month drift: Task 6.
- Gmail SMTP delivery with macOS Keychain secret storage: Task 8 and Task 10.
- Partial failure reporting: Task 7 and Task 10.
- End-to-end validation before enabling scheduler: Task 12.

Type consistency:

- `Snapshot`, `TopMetrics`, `ExpirationRow`, `MonthlySignal`, `SymbolAnalysis`, `DriftItem`, `SymbolReport`, and `ReportBundle` are defined in Task 2 and reused consistently in later tasks.
- `Thresholds` field names match `config/symbols.json`, `load_config`, and analyzer tests.
- CLI commands are consistently named `setup-email` and `run`.

Execution order:

- Tasks are ordered so each test can fail for the expected missing module or missing behavior, then pass after the implementation step.
- Commits are made after each independently working slice.
