# GitHub Publishing and Agent Distribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare and publish `options-put-call-reporter` as a production-ready public GitHub CLI tool with portable assistant/skill instructions for Claude Code, GitHub Copilot, Codex, and Gemini.

**Architecture:** Keep the Python package layout unchanged, but add production metadata, packaged default configuration, repository docs, CI gates, and assistant instruction surfaces. Treat assistant support as documentation/instruction assets in the repo, not runtime code, so the CLI remains focused on collection, analysis, reporting, email, and scheduling.

**Tech Stack:** Python 3.11+, setuptools, pytest, Playwright, GitHub Actions, Markdown assistant instruction files, GitHub CLI or Git remote commands for publishing.

---

## File Structure

- Modify `pyproject.toml`: package metadata, build dev dependency, package-data config inclusion.
- Modify `src/reporter/config.py`: load packaged default config when the default repo config path is absent.
- Create `src/reporter/default_symbols.json`: packaged default watchlist/settings copied from `config/symbols.json`.
- Modify `.gitignore`: expanded production ignore patterns.
- Replace `README.md`: public GitHub landing page.
- Create `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `docs/PUBLISHING.md`.
- Create assistant files: `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `.github/instructions/options-reporter.instructions.md`, `assistant-pack/README.md`, `assistant-pack/claude/options-put-call-reporter/SKILL.md`, `assistant-pack/prompts/options-report-agent.md`.
- Create GitHub gate files: `.github/workflows/ci.yml`, `.github/dependabot.yml`.
- Create tests: `tests/test_publication_assets.py`.

---

### Task 1: Package metadata and packaged default config

**Files:**
- Create: `src/reporter/default_symbols.json`
- Modify: `src/reporter/config.py`
- Modify: `pyproject.toml`
- Test: `tests/test_config.py`
- Test: `tests/test_publication_assets.py`

- [ ] **Step 1: Write failing config/package tests**

Append these tests to `tests/test_config.py`:

```python
def test_load_config_uses_packaged_default_when_default_repo_config_is_absent(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    loaded = load_config(Path("config/symbols.json"))

    assert loaded.archive_dir == Path("archive")
    assert loaded.database_path == Path("data/history.sqlite3")
    assert [symbol.symbol for symbol in loaded.symbols] == ["META", "GOOG", "MSFT", "NFLX", "NOW", "AAOI", "LITE"]
```

Create `tests/test_publication_assets.py` with:

```python
from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_pyproject_has_public_github_metadata() -> None:
    data = tomllib.loads(_read("pyproject.toml"))
    project = data["project"]

    assert project["name"] == "options-put-call-reporter"
    assert project["readme"] == "README.md"
    assert project["license"] == {"file": "LICENSE"}
    assert "Development Status :: 4 - Beta" in project["classifiers"]
    assert "Topic :: Office/Business :: Financial" in project["classifiers"]
    assert project["urls"]["Repository"] == "https://github.com/BlancosWay/options-put-call-reporter"
    assert project["urls"]["Issues"] == "https://github.com/BlancosWay/options-put-call-reporter/issues"
    assert "build>=1,<2" in data["project"]["optional-dependencies"]["dev"]


def test_packaged_default_config_is_included_as_package_data() -> None:
    data = tomllib.loads(_read("pyproject.toml"))

    assert data["tool"]["setuptools"]["package-data"]["reporter"] == ["default_symbols.json"]
    assert "META" in _read("src/reporter/default_symbols.json")
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" pytest tests/test_config.py::test_load_config_uses_packaged_default_when_default_repo_config_is_absent tests/test_publication_assets.py::test_pyproject_has_public_github_metadata tests/test_publication_assets.py::test_packaged_default_config_is_included_as_package_data -q
```

Expected: FAIL because the packaged default config and metadata do not exist yet.

- [ ] **Step 3: Add packaged default config**

Create `src/reporter/default_symbols.json` with the same content as `config/symbols.json`:

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

- [ ] **Step 4: Refactor config loading to support packaged default**

In `src/reporter/config.py`, add this import:

```python
from importlib import resources
```

Add this constant after `SYMBOL_PATTERN`:

```python
DEFAULT_CONFIG_PATH = Path("config/symbols.json")
```

Replace `load_config` with:

```python
def _config_from_data(data: Any) -> AppConfig:
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


def _load_default_config_data() -> Any:
    return json.loads(resources.files("reporter").joinpath("default_symbols.json").read_text(encoding="utf-8"))


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    if config_path == DEFAULT_CONFIG_PATH and not config_path.exists():
        return _config_from_data(_load_default_config_data())
    return _config_from_data(json.loads(config_path.read_text(encoding="utf-8")))
```

- [ ] **Step 5: Update package metadata**

Replace `pyproject.toml` with:

```toml
[build-system]
requires = ["setuptools>=70", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "options-put-call-reporter"
version = "0.1.0"
description = "Daily Barchart put/call ratio sentiment report generator"
readme = "README.md"
license = { file = "LICENSE" }
requires-python = ">=3.11"
authors = [
  { name = "Sri", email = "BlancosWay@users.noreply.github.com" }
]
maintainers = [
  { name = "Sri", email = "BlancosWay@users.noreply.github.com" }
]
keywords = ["options", "put-call-ratio", "barchart", "sentiment", "reporting", "playwright"]
classifiers = [
  "Development Status :: 4 - Beta",
  "Environment :: Console",
  "Intended Audience :: Financial and Insurance Industry",
  "License :: OSI Approved :: MIT License",
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3.11",
  "Programming Language :: Python :: 3.12",
  "Topic :: Office/Business :: Financial",
  "Topic :: Utilities"
]
dependencies = [
  "playwright>=1.46,<2"
]

[project.optional-dependencies]
dev = [
  "build>=1,<2",
  "pytest>=8,<9",
  "pytest-asyncio>=0.23,<1"
]

[project.urls]
Repository = "https://github.com/BlancosWay/options-put-call-reporter"
Issues = "https://github.com/BlancosWay/options-put-call-reporter/issues"
Documentation = "https://github.com/BlancosWay/options-put-call-reporter#readme"

[project.scripts]
options-put-call-report = "reporter.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
reporter = ["default_symbols.json"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-q"
```

- [ ] **Step 6: Run tests to verify they pass**

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" pytest tests/test_config.py::test_load_config_uses_packaged_default_when_default_repo_config_is_absent tests/test_publication_assets.py::test_pyproject_has_public_github_metadata tests/test_publication_assets.py::test_packaged_default_config_is_included_as_package_data -q
```

Expected: PASS.

- [ ] **Step 7: Commit package metadata work**

Run:

```bash
git add pyproject.toml src/reporter/config.py src/reporter/default_symbols.json tests/test_config.py tests/test_publication_assets.py
git commit -m "Prepare package metadata for GitHub installs" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

Expected: commit succeeds.

---

### Task 2: Public README, license, community docs, and ignore rules

**Files:**
- Modify: `README.md`
- Modify: `.gitignore`
- Create: `LICENSE`
- Create: `CONTRIBUTING.md`
- Create: `SECURITY.md`
- Create: `CODE_OF_CONDUCT.md`
- Create: `docs/PUBLISHING.md`
- Test: `tests/test_publication_assets.py`

- [ ] **Step 1: Add failing tests for public docs**

Append these tests to `tests/test_publication_assets.py`:

```python
def test_public_repository_docs_exist_and_cover_required_topics() -> None:
    required_files = [
        "README.md",
        "LICENSE",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
        "docs/PUBLISHING.md",
    ]

    for path in required_files:
        assert (ROOT / path).exists(), path

    readme = _read("README.md")
    for text in [
        "pipx install git+https://github.com/BlancosWay/options-put-call-reporter.git",
        "pipx run --spec playwright playwright install chromium",
        "python -m playwright install chromium",
        "options-put-call-report run --no-email",
        "options-put-call-report run --no-email META MSFT NOW",
        "options-put-call-report setup-email",
        "launchd",
        "Not financial advice",
    ]:
        assert text in readme


def test_gitignore_covers_public_repo_runtime_and_build_artifacts() -> None:
    gitignore = _read(".gitignore")

    for pattern in [
        ".venv/",
        "archive/",
        "data/",
        "config/email.local.json",
        "dist/",
        "build/",
        "*.egg-info/",
        ".coverage",
        ".env",
    ]:
        assert pattern in gitignore
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" pytest tests/test_publication_assets.py::test_public_repository_docs_exist_and_cover_required_topics tests/test_publication_assets.py::test_gitignore_covers_public_repo_runtime_and_build_artifacts -q
```

Expected: FAIL because the public docs and expanded ignore rules do not exist yet.

- [ ] **Step 3: Expand `.gitignore`**

Replace `.gitignore` with:

```gitignore
.worktrees/
.venv/
venv/
env/
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
coverage.xml
htmlcov/
.DS_Store
.env
.env.*
!.env.example
archive/
data/
config/email.local.json
playwright-report/
test-results/
dist/
build/
*.egg-info/
pip-wheel-metadata/
```

- [ ] **Step 4: Add MIT license**

Create `LICENSE`:

```text
MIT License

Copyright (c) 2026 Sri

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 5: Replace README with public landing page**

Replace `README.md` with:

```markdown
# Options Put/Call Reporter

Daily Barchart put/call ratio sentiment reporter for a stock watchlist. The tool collects live options-expiration data, classifies monthly put/call signals, tracks historical drift, renders clean HTML/Markdown/CSV reports, and can optionally email the report through Gmail.

> Not financial advice. This project summarizes options sentiment data for research and automation. Verify all market data independently before making trading or investment decisions.

## Features

- Collects Barchart put/call ratio data with Playwright Chromium.
- Produces a clean HTML dashboard plus Markdown and CSV outputs.
- Tracks history in SQLite and reports day/week/month drift where prior data exists.
- Supports default symbols, terminal symbols, or a plain-text symbol file.
- Sends Gmail reports using a macOS Keychain-stored app password.
- Includes launchd scheduling scripts for local daily runs on macOS.
- Ships assistant instructions for Claude Code, GitHub Copilot, Codex, and Gemini.

## Install from GitHub

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
pipx install git+https://github.com/BlancosWay/options-put-call-reporter.git
pipx run --spec playwright playwright install chromium
```

For development:

```bash
git clone https://github.com/BlancosWay/options-put-call-reporter.git
cd options-put-call-reporter
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m playwright install chromium
```

## Quickstart

Run the default watchlist and save the report locally:

```bash
options-put-call-report run --no-email
```

Runs print concise progress by default, including the symbol count, each symbol collection step, report rendering, and email send status when email is enabled.

Run a one-off report for symbols entered in the terminal:

```bash
options-put-call-report run --no-email META MSFT NOW
```

Run from a plain text symbol file:

```bash
options-put-call-report run --no-email --symbols-file watchlist.txt
```

Symbol files can use one symbol per line, spaces, commas, and `#` comments:

```text
# watchlist.txt
META, MSFT
NOW AAOI
LITE  # comments are ignored
```

## Outputs

By default, reports and raw collection artifacts are written under `archive/YYYY-MM-DD/`:

- `report.html` - polished dashboard report.
- `report.md` - Markdown report.
- `{SYMBOL}-expirations.csv` - raw expiration table.
- `{SYMBOL}-snapshot.json` - normalized snapshot.
- `{SYMBOL}-raw.json` and `{SYMBOL}-raw.html` - collection diagnostics.

History is stored in `data/history.sqlite3`.

## Email setup

Run the interactive setup command. It asks for sender email, recipient email, and a Gmail App Password. The app password is stored in macOS Keychain under `options-put-call-reporter:gmail-app-password`.

```bash
options-put-call-report setup-email
options-put-call-report run --send-email
```

The local email config is written to `config/email.local.json`, which is intentionally ignored by git.

## Scheduler

Before installing the scheduler, confirm that a manual email run succeeds:

```bash
options-put-call-report run --send-email
```

Install the launchd job from a cloned checkout:

```bash
./scripts/install_launch_agent.sh
```

The scheduled job runs at 2:30 PM Pacific Time, which corresponds to 5:30 PM Eastern Time. Logs are written to:

- `archive/runner.log`
- `archive/launchd.out.log`
- `archive/launchd.err.log`

The scheduled runner captures the same concise progress output in these logs.

## Assistant pack

This repository includes assistant instructions for maintaining and operating the tool:

- `AGENTS.md` for Codex-style agents.
- `CLAUDE.md` for Claude Code.
- `GEMINI.md` for Gemini CLI.
- `.github/copilot-instructions.md` for GitHub Copilot.
- `assistant-pack/` for portable skill/prompt files.

See `assistant-pack/README.md` for copy/install guidance.

## Development

```bash
source .venv/bin/activate
pytest -q
python -m build
```

CI runs the test suite on Python 3.11 and 3.12 and builds the package.

## Troubleshooting

- If Barchart collection fails after a GitHub/pipx install, run `pipx run --spec playwright playwright install chromium`.
- In a development checkout, install Chromium with `python -m playwright install chromium`.
- If a symbol fails, inspect the daily `archive/YYYY-MM-DD/` diagnostics.
- If email fails, confirm the Gmail App Password is present in Keychain and the recipient config exists.
- If running from a fresh GitHub install, the packaged default watchlist is used when `config/symbols.json` is absent.

## Security and privacy

Do not commit `config/email.local.json`, Gmail app passwords, `archive/`, or `data/`. Generated archives can include local diagnostics and market snapshots.

## License

MIT. See `LICENSE`.
```

- [ ] **Step 6: Add community and publishing docs**

Create `CONTRIBUTING.md`:

```markdown
# Contributing

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m playwright install chromium
pytest -q
```

## Pull request expectations

- Keep generated archives, SQLite history, and local email config out of commits.
- Add or update tests for behavior changes.
- Run `pytest -q` before opening a pull request.
- Keep report output clear and avoid financial-advice language.

## Local data

The reporter writes runtime files to `archive/` and `data/`. These paths are ignored and should not be committed.
```

Create `SECURITY.md`:

```markdown
# Security Policy

## Reporting a vulnerability

Open a private security advisory on GitHub if available, or contact the repository owner through GitHub.

## Sensitive data

Never commit Gmail App Passwords, `config/email.local.json`, generated `archive/` files, or `data/history.sqlite3`. The tool stores Gmail app passwords in macOS Keychain through the `setup-email` command.

## Market data disclaimer

This project collects third-party market data for research reporting. It does not provide financial advice or trade execution.
```

Create `CODE_OF_CONDUCT.md`:

```markdown
# Code of Conduct

Be respectful, constructive, and focused on improving the project. Harassment, abuse, and discriminatory behavior are not welcome.

If a conduct issue occurs, contact the repository owner through GitHub. Maintainers may remove comments, close issues, or block participants to keep the project healthy.
```

Create `docs/PUBLISHING.md`:

```markdown
# Publishing to GitHub

Target repository: `https://github.com/BlancosWay/options-put-call-reporter`

## Create the public repository with GitHub CLI

```bash
gh repo create BlancosWay/options-put-call-reporter --public --source=. --remote=origin --push
```

## Manual fallback

If GitHub CLI is unavailable:

```bash
git remote add origin https://github.com/BlancosWay/options-put-call-reporter.git 2>/dev/null || git remote set-url origin https://github.com/BlancosWay/options-put-call-reporter.git
git push -u origin feature/daily-options-report
```

Then open GitHub, create a pull request into `main`, and require the CI workflow before merging.

## Release checklist

1. Run `pytest -q`.
2. Run `python -m build`.
3. Confirm `git status --short` is clean.
4. Push the branch.
5. Confirm GitHub Actions passes.
```

- [ ] **Step 7: Run tests to verify docs pass**

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" pytest tests/test_publication_assets.py::test_public_repository_docs_exist_and_cover_required_topics tests/test_publication_assets.py::test_gitignore_covers_public_repo_runtime_and_build_artifacts -q
```

Expected: PASS.

- [ ] **Step 8: Commit docs work**

Run:

```bash
git add .gitignore README.md LICENSE CONTRIBUTING.md SECURITY.md CODE_OF_CONDUCT.md docs/PUBLISHING.md tests/test_publication_assets.py
git commit -m "Add public repository documentation" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

Expected: commit succeeds.

---

### Task 3: Cross-agent instruction pack

**Files:**
- Create: `AGENTS.md`
- Create: `CLAUDE.md`
- Create: `GEMINI.md`
- Create: `.github/copilot-instructions.md`
- Create: `.github/instructions/options-reporter.instructions.md`
- Create: `assistant-pack/README.md`
- Create: `assistant-pack/claude/options-put-call-reporter/SKILL.md`
- Create: `assistant-pack/prompts/options-report-agent.md`
- Test: `tests/test_publication_assets.py`

- [ ] **Step 1: Add failing tests for assistant assets**

Append this test to `tests/test_publication_assets.py`:

```python
def test_assistant_instruction_pack_targets_all_supported_agents() -> None:
    required_files = [
        "AGENTS.md",
        "CLAUDE.md",
        "GEMINI.md",
        ".github/copilot-instructions.md",
        ".github/instructions/options-reporter.instructions.md",
        "assistant-pack/README.md",
        "assistant-pack/claude/options-put-call-reporter/SKILL.md",
        "assistant-pack/prompts/options-report-agent.md",
    ]

    for path in required_files:
        assert (ROOT / path).exists(), path

    combined = "\n".join(_read(path) for path in required_files)
    for text in [
        "options-put-call-report run --no-email",
        "pytest -q",
        "python -m build",
        "python -m playwright install chromium",
        "config/symbols.json",
        "archive/YYYY-MM-DD",
        "data/history.sqlite3",
        "Barchart",
        "macOS Keychain",
        "not financial advice",
        "Claude Code",
        "GitHub Copilot",
        "Codex",
        "Gemini",
    ]:
        assert text in combined

    for native_file in ["AGENTS.md", "CLAUDE.md", "GEMINI.md", ".github/copilot-instructions.md"]:
        content = _read(native_file)
        for text in ["config/symbols.json", "archive/YYYY-MM-DD", "data/history.sqlite3", "pytest -q", "python -m build", "Barchart"]:
            assert text in content, f"{native_file} missing {text}"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" pytest tests/test_publication_assets.py::test_assistant_instruction_pack_targets_all_supported_agents -q
```

Expected: FAIL because assistant files do not exist.

- [ ] **Step 3: Add shared root agent instructions**

Create `AGENTS.md`:

```markdown
# Agent Instructions

This repository contains a Python CLI that creates Barchart options put/call sentiment reports. Treat outputs as research summaries, not financial advice.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m playwright install chromium
pytest -q
```

## Run commands

- Default local report: `options-put-call-report run --no-email`
- Symbol override: `options-put-call-report run --no-email META MSFT NOW`
- Symbol file: `options-put-call-report run --no-email --symbols-file watchlist.txt`
- Email setup: `options-put-call-report setup-email`

## Locations

- Default config: `config/symbols.json`; packaged default config is used when this file is absent.
- Reports and diagnostics: `archive/YYYY-MM-DD/`.
- SQLite history: `data/history.sqlite3`.

## CI-equivalent checks

Run `pytest -q` and `python -m build` before publishing or claiming completion.

## Barchart collection

The collector depends on Playwright Chromium and Barchart put/call pages. Keep Barchart API parsing changes isolated in `src/reporter/collector.py` and preserve archived diagnostics for failures.

## Safety

- Do not commit `archive/`, `data/`, or `config/email.local.json`.
- Gmail App Passwords belong in macOS Keychain.
- Preserve tests for parser, collector, reporting, CLI, history, drift, scheduler, and security behavior.
```

Create `CLAUDE.md`:

```markdown
# Claude Code Instructions

Use this project as a Python CLI/package. Follow TDD for behavior changes and run `pytest -q` before reporting completion.

## Project context

`options-put-call-report` collects Barchart put/call ratio data with Playwright, analyzes monthly sentiment, stores SQLite history, renders reports, and can send Gmail email through macOS Keychain.

## Locations

- Config: `config/symbols.json`; packaged defaults are used if missing after GitHub install.
- Reports and raw diagnostics: `archive/YYYY-MM-DD/`.
- History: `data/history.sqlite3`.

## CI-equivalent checks

Run `pytest -q` and `python -m build`.

## Maintenance rules

- Keep generated files out of git: `archive/`, `data/`, `config/email.local.json`.
- Use `python -m playwright install chromium` when browser collection fails.
- Keep Barchart parsing changes focused in `src/reporter/collector.py`.
- Do not describe report output as financial advice.
- Update README and assistant-pack docs when CLI behavior changes.
```

Create `GEMINI.md`:

```markdown
# Gemini CLI Instructions

This repository is a Python 3.11+ CLI for Barchart options put/call sentiment reporting.

## Commands

```bash
python -m pip install -e ".[dev]"
python -m playwright install chromium
pytest -q
options-put-call-report run --no-email
```

## Guidance

- Reports summarize options sentiment and are not financial advice.
- Do not expose Gmail App Passwords; they are stored in macOS Keychain.
- Keep local runtime output in ignored paths only.
- Config lives in `config/symbols.json`; reports and diagnostics live in `archive/YYYY-MM-DD/`; history lives in `data/history.sqlite3`.
- Run `pytest -q` and `python -m build` before publishing changes.
- Keep Barchart/Playwright collection changes isolated in `src/reporter/collector.py`.
```

- [ ] **Step 4: Add Copilot instructions**

Create `.github/copilot-instructions.md`:

```markdown
# GitHub Copilot Instructions

This repository builds `options-put-call-report`, a Python CLI for Barchart options put/call sentiment reports.

## Standards

- Follow existing Python dataclass and pytest patterns.
- Run `pytest -q` after changes.
- Run `python -m build` before publishing changes.
- Use Playwright only through existing collector boundaries.
- Keep secrets and generated archives out of git.
- Market commentary must say research/sentiment, not financial advice.

## Common commands

```bash
python -m pip install -e ".[dev]"
python -m playwright install chromium
options-put-call-report run --no-email
pytest -q
```

## Locations

- Config: `config/symbols.json`; packaged defaults are used when the repo config is absent.
- Reports and raw diagnostics: `archive/YYYY-MM-DD/`.
- SQLite history: `data/history.sqlite3`.
- Barchart/Playwright collection code: `src/reporter/collector.py`.
```

Create `.github/instructions/options-reporter.instructions.md`:

```markdown
---
applyTo: "**/*"
---

# Options Reporter Guidance

- CLI entry point: `options-put-call-report`.
- Main orchestration: `src/reporter/cli.py`.
- Live Barchart collection: `src/reporter/collector.py`.
- Report rendering: `src/reporter/reporting.py`.
- Config: `config/symbols.json` with packaged fallback defaults.
- Reports/diagnostics: `archive/YYYY-MM-DD/`.
- History database: `data/history.sqlite3`.
- CI-equivalent checks: `pytest -q` and `python -m build`.
- Tests live in `tests/` and should use deterministic fixtures.
- Do not commit `archive/`, `data/`, or `config/email.local.json`.
```

- [ ] **Step 5: Add portable assistant pack**

Create `assistant-pack/README.md`:

```markdown
# Options Put/Call Reporter Assistant Pack

Portable instructions for using AI assistants with `options-put-call-reporter`.

## Claude Code

Copy `assistant-pack/claude/options-put-call-reporter/` into your Claude/Superpowers skills directory, or paste the `SKILL.md` content into your local skill system.

## GitHub Copilot

Use `.github/copilot-instructions.md` and `.github/instructions/options-reporter.instructions.md` in the repository.

## Codex

Use the root `AGENTS.md` file.

## Gemini

Use the root `GEMINI.md` file.

## Platform-neutral prompt

Paste `assistant-pack/prompts/options-report-agent.md` into assistants that do not support file-based instructions.
```

Create `assistant-pack/claude/options-put-call-reporter/SKILL.md`:

```markdown
---
name: options-put-call-reporter
description: Use when users want to install, run, schedule, troubleshoot, or maintain the Options Put/Call Reporter CLI.
---

# Options Put/Call Reporter Skill

Help users work with `options-put-call-report`, a Python CLI that collects Barchart put/call ratio data, generates sentiment reports, stores local history, and optionally sends Gmail reports.

## Commands

```bash
python -m pip install -e ".[dev]"
python -m playwright install chromium
pytest -q
options-put-call-report run --no-email
options-put-call-report run --no-email META MSFT NOW
options-put-call-report setup-email
```

## Rules

- Treat output as options-sentiment research, not financial advice.
- Never ask users to paste Gmail App Passwords into chat.
- Use macOS Keychain via `setup-email`.
- Keep `archive/`, `data/`, and `config/email.local.json` out of git.
- When changing code, write tests first and run `pytest -q`.
```

Create `assistant-pack/prompts/options-report-agent.md`:

```markdown
# Options Put/Call Reporter Agent Prompt

You help operate and maintain `options-put-call-reporter`.

The tool:
- runs as `options-put-call-report`;
- collects Barchart put/call ratio pages with Playwright Chromium;
- generates HTML, Markdown, CSV, JSON, and SQLite history outputs;
- supports default symbols, terminal symbols, and `--symbols-file`;
- stores Gmail App Passwords in macOS Keychain.

Use these commands:

```bash
python -m pip install -e ".[dev]"
python -m playwright install chromium
pytest -q
options-put-call-report run --no-email
```

Safety:
- Do not provide financial advice.
- Do not expose secrets.
- Do not commit local archives, SQLite data, or email config.
```

- [ ] **Step 6: Run assistant asset test**

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" pytest tests/test_publication_assets.py::test_assistant_instruction_pack_targets_all_supported_agents -q
```

Expected: PASS.

- [ ] **Step 7: Commit assistant pack**

Run:

```bash
git add AGENTS.md CLAUDE.md GEMINI.md .github/copilot-instructions.md .github/instructions/options-reporter.instructions.md assistant-pack tests/test_publication_assets.py
git commit -m "Add cross-agent assistant pack" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

Expected: commit succeeds.

---

### Task 4: GitHub CI gates and dependency updates

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.github/dependabot.yml`
- Test: `tests/test_publication_assets.py`

- [ ] **Step 1: Add failing tests for GitHub gates**

Append these tests to `tests/test_publication_assets.py`:

```python
def test_github_ci_runs_tests_and_package_build() -> None:
    ci = _read(".github/workflows/ci.yml")

    for text in [
        "push:",
        "pull_request:",
        "python-version: ['3.11', '3.12']",
        "python -m pip install -e \".[dev]\"",
        "python -m playwright install chromium",
        "pytest -q",
        "python -m build",
    ]:
        assert text in ci


def test_dependabot_updates_actions_and_python_dependencies() -> None:
    dependabot = _read(".github/dependabot.yml")

    for text in [
        "package-ecosystem: \"github-actions\"",
        "directory: \"/\"",
        "package-ecosystem: \"pip\"",
        "interval: \"weekly\"",
    ]:
        assert text in dependabot
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" pytest tests/test_publication_assets.py::test_github_ci_runs_tests_and_package_build tests/test_publication_assets.py::test_dependabot_updates_actions_and_python_dependencies -q
```

Expected: FAIL because CI and Dependabot files do not exist.

- [ ] **Step 3: Add GitHub Actions CI**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  test:
    name: Python ${{ matrix.python-version }}
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ['3.11', '3.12']

    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install package
        run: |
          python -m pip install --upgrade pip
          python -m pip install -e ".[dev]"

      - name: Install Playwright Chromium
        run: python -m playwright install chromium

      - name: Run tests
        run: pytest -q

      - name: Build package
        run: python -m build
```

- [ ] **Step 4: Add Dependabot config**

Create `.github/dependabot.yml`:

```yaml
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"

  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
```

- [ ] **Step 5: Run gate tests**

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" pytest tests/test_publication_assets.py::test_github_ci_runs_tests_and_package_build tests/test_publication_assets.py::test_dependabot_updates_actions_and_python_dependencies -q
```

Expected: PASS.

- [ ] **Step 6: Commit gates**

Run:

```bash
git add .github/workflows/ci.yml .github/dependabot.yml tests/test_publication_assets.py
git commit -m "Add GitHub CI gates" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

Expected: commit succeeds.

---

### Task 5: Final verification, publish attempt, and handoff

**Files:**
- No required code files.
- May modify git remote configuration.

- [ ] **Step 1: Run full test suite**

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" pytest -q
```

Expected: PASS.

- [ ] **Step 2: Refresh dev install and build package**

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" python -m pip install -e ".[dev]"
PATH="$PWD/.venv/bin:$PATH" python -m build
```

Expected: dev dependencies are installed, then source distribution and wheel build successfully under `dist/`.

- [ ] **Step 3: Check worktree state**

Run:

```bash
git --no-pager status --short
```

Expected: only ignored build artifacts under `dist/` if `python -m build` created them, or no output if build artifacts are ignored and no source changes remain.

- [ ] **Step 4: Request final code review**

Capture the head SHA:

```bash
git rev-parse HEAD
```

Dispatch a final `superpowers:code-reviewer` review with this context, using the SHA printed by `git rev-parse HEAD` as the `HEAD_SHA` value:

```text
WHAT_WAS_IMPLEMENTED:
Production-ready GitHub publishing assets, packaged default config, assistant instruction pack, CI gates, community docs, and GitHub publishing docs.

PLAN_OR_REQUIREMENTS:
docs/superpowers/specs/2026-06-05-github-publishing-agent-distribution-design.md and docs/superpowers/plans/2026-06-06-github-publishing-agent-distribution.md.

BASE_SHA:
e2a6ae9

HEAD_SHA:
Use the exact SHA printed by `git rev-parse HEAD`.
```

Expected: no Critical or Important issues. Fix any Critical or Important issues before continuing.

- [ ] **Step 5: Check for GitHub CLI**

Run:

```bash
command -v gh && gh auth status
```

Expected: if `gh` exists and is authenticated, continue to Step 6. If not, skip to Step 7 and provide manual commands.

- [ ] **Step 6: Publish with GitHub CLI when authenticated**

Run:

```bash
gh repo create BlancosWay/options-put-call-reporter --public --source=. --remote=origin --push
```

If the repository already exists, run:

```bash
git remote add origin https://github.com/BlancosWay/options-put-call-reporter.git 2>/dev/null || git remote set-url origin https://github.com/BlancosWay/options-put-call-reporter.git
git push -u origin feature/daily-options-report
```

Expected: branch is pushed to GitHub.

- [ ] **Step 7: Manual publishing fallback if GitHub auth is unavailable**

Report these exact commands:

```bash
cd /Users/sri/personal/options-put-call-reporter/.worktrees/daily-options-report
git remote add origin https://github.com/BlancosWay/options-put-call-reporter.git 2>/dev/null || git remote set-url origin https://github.com/BlancosWay/options-put-call-reporter.git
git push -u origin feature/daily-options-report
```

Also state: create a public GitHub repository named `options-put-call-reporter` under `BlancosWay` before running them if it does not already exist.

- [ ] **Step 8: Record final status**

Run:

```bash
git --no-pager log --oneline -8
git remote -v
git --no-pager status --short
```

Expected: status has no source changes. Final response must include whether GitHub publication succeeded or needs manual authentication, plus the latest verification results.

---

## Self-Review

- Spec coverage: Task 1 covers package metadata and GitHub install usability; Task 2 covers README, license, `.gitignore`, community/security docs, and publishing docs; Task 3 covers Claude Code, Copilot, Codex, Gemini, and portable assistant pack; Task 4 covers CI and Dependabot gates; Task 5 covers verification, review, and publish/fallback flow.
- Scope check: The plan stays GitHub-first and does not add PyPI automation, web hosting, paid marketplace submission, or financial-advice features.
- Placeholder scan: The plan contains concrete file paths, commands, and file contents for implementation. No placeholder sections are left for implementers.
- Type consistency: Config changes use existing `AppConfig`, `ConfigError`, and `load_config` boundaries; tests use existing pytest style and Python 3.11 `tomllib`.
