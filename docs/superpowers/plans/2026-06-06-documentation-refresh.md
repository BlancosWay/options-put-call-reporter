# Documentation Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refresh the README and supporting docs so users, maintainers, and AI assistants can install, run, understand, troubleshoot, and maintain the tool without reading source code.

**Architecture:** Keep `README.md` as the public landing page and move deeper operational details into focused docs. Add `docs/ARCHITECTURE.md` for data flow and change hotspots, add `docs/MAINTENANCE.md` for CI/branch/Dependabot/release workflows, and keep assistant docs short with links to those deeper docs. Lock the documentation contract with publication-asset tests.

**Tech Stack:** Markdown, pytest documentation assertions, Python package build.

---

## Files

- Modify `README.md`: add navigation, output explanation, signal interpretation, data-source/fallback behavior, CLI reference, troubleshooting table, and links to deeper docs.
- Create `docs/ARCHITECTURE.md`: describe CLI, collector, analyzer, history, reporting, email, scheduler, data-source metadata, and safe change points.
- Create `docs/MAINTENANCE.md`: describe local validation, protected-branch workflow, CI, Dependabot auto-merge, release checklist, and generated-file safety.
- Modify `docs/PUBLISHING.md`: keep initial publishing guidance and link ongoing release/maintenance work to `docs/MAINTENANCE.md`.
- Modify `CONTRIBUTING.md`: add PR checklist and links to architecture/maintenance docs.
- Modify `SECURITY.md`: keep concise security guidance and cross-link maintenance docs where relevant.
- Modify `assistant-pack/README.md`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, and `.github/instructions/options-reporter.instructions.md`: link to architecture and maintenance docs while preserving existing commands and safety rules.
- Modify `tests/test_publication_assets.py`: require the new docs and key topics.

## Task 1: Lock documentation coverage with failing tests

**Files:**
- Modify: `tests/test_publication_assets.py`

- [x] **Step 1: Extend required public docs**

Add `docs/ARCHITECTURE.md` and `docs/MAINTENANCE.md` to the required public files in `test_public_repository_docs_exist_and_cover_required_topics()`:

```python
    required_files = [
        "README.md",
        "LICENSE",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
        "docs/PUBLISHING.md",
        "docs/ARCHITECTURE.md",
        "docs/MAINTENANCE.md",
    ]
```

- [x] **Step 2: Add README topic assertions**

Add these strings to the README assertion list in `test_public_repository_docs_exist_and_cover_required_topics()`:

```python
        "## Table of contents",
        "## What this produces",
        "## How to read the signal",
        "## Data sources and fallback behavior",
        "## CLI command reference",
        "Symptom",
        "Likely cause",
        "Fix",
        "docs/ARCHITECTURE.md",
        "docs/MAINTENANCE.md",
```

- [x] **Step 3: Add architecture/maintenance doc tests**

Append these tests to `tests/test_publication_assets.py`:

```python
def test_architecture_doc_covers_runtime_flow_and_change_points() -> None:
    architecture = _read("docs/ARCHITECTURE.md")

    for text in [
        "CLI orchestration",
        "src/reporter/cli.py",
        "Barchart primary collection",
        "yfin.dev fallback",
        "DataSource",
        "src/reporter/collector.py",
        "src/reporter/analyzer.py",
        "src/reporter/history.py",
        "src/reporter/reporting.py",
        "archive/YYYY-MM-DD/",
        "data/history.sqlite3",
        "macOS Keychain",
        "launchd",
        "Safe change points",
    ]:
        assert text in architecture


def test_maintenance_doc_covers_ci_dependabot_and_release_workflow() -> None:
    maintenance = _read("docs/MAINTENANCE.md")

    for text in [
        "pytest -q",
        "python -m build",
        "protected `main`",
        "Python 3.11",
        "Python 3.12",
        "Dependabot auto-merge",
        "semver patch and minor",
        "major updates remain manual",
        "github.event.pull_request.user.login",
        "gh pr checks",
        "gh run list",
        "archive/",
        "data/",
        "config/email.local.json",
    ]:
        assert text in maintenance
```

- [x] **Step 4: Require assistant docs to point to deeper docs**

In `test_assistant_instruction_pack_targets_all_supported_agents()`, add `docs/ARCHITECTURE.md` and `docs/MAINTENANCE.md` to the combined text assertion list:

```python
        "docs/ARCHITECTURE.md",
        "docs/MAINTENANCE.md",
```

- [x] **Step 5: Run focused test and confirm RED**

Run:

```bash
./.venv/bin/python -m pytest tests/test_publication_assets.py -q
```

Expected: fails because `docs/ARCHITECTURE.md`, `docs/MAINTENANCE.md`, and new README/assistant doc strings are missing.

## Task 2: Refresh the public README

**Files:**
- Modify: `README.md`

- [x] **Step 1: Rewrite README with the approved structure**

Replace `README.md` with content that preserves existing install/run commands and adds these sections in order:

```markdown
# Options Put/Call Reporter

Daily Barchart put/call ratio sentiment reporter for a stock watchlist. The tool collects live options-expiration data, classifies monthly put/call signals, tracks historical drift, renders clean HTML/Markdown/CSV reports, and can optionally email the report through Gmail.

> Not financial advice. This project summarizes options sentiment data for research and automation. Verify all market data independently before making trading or investment decisions.

## Table of contents

- [Features](#features)
- [Install from GitHub](#install-from-github)
- [Quickstart](#quickstart)
- [What this produces](#what-this-produces)
- [How to read the signal](#how-to-read-the-signal)
- [Data sources and fallback behavior](#data-sources-and-fallback-behavior)
- [CLI command reference](#cli-command-reference)
- [Outputs](#outputs)
- [Email setup](#email-setup)
- [Scheduler](#scheduler)
- [Documentation for maintainers and agents](#documentation-for-maintainers-and-agents)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Security and privacy](#security-and-privacy)
- [License](#license)

## Features

- Collects Barchart put/call ratio data with Playwright Chromium.
- Falls back to yfin.dev options-chain data when Barchart collection fails.
- Produces a clean HTML dashboard plus Markdown and CSV outputs.
- Reports disclose the data source used for each symbol.
- Tracks history in SQLite and reports day/week/month drift where prior data exists.
- Supports default symbols, terminal symbols, or a plain-text symbol file.
- Sends Gmail reports using a macOS Keychain-stored app password.
- Includes launchd scheduling scripts for local daily runs on macOS.
- Ships assistant instructions for Claude Code, GitHub Copilot, Codex, and Gemini.

## Install from GitHub

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
python3 -m pipx install git+https://github.com/BlancosWay/options-put-call-reporter.git
python3 -m pipx run --spec playwright playwright install chromium
```

After `ensurepath`, restart your shell or source your shell profile before running `options-put-call-report`.

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

## What this produces

A run creates a dated archive folder and writes a human-readable report plus raw diagnostics:

```text
archive/YYYY-MM-DD/
├── report.html
├── report.md
├── META-expirations.csv
├── META-snapshot.json
├── META-raw.json
└── META-raw.html
```

The HTML report summarizes each symbol with a monthly signal, put/call ratios, drift from prior saved runs, and the data source used for that symbol.

## How to read the signal

- **Put/call ratio:** compares put activity to call activity. Higher values are more put-heavy; lower values are more call-heavy.
- **Monthly signal:** classifies monthly expiration rows as bullish, bearish, or neutral using the reporter's ratio thresholds.
- **Drift:** compares the current snapshot with prior history in `data/history.sqlite3` when enough previous data exists.
- **Data source:** each generated report discloses whether a symbol used Barchart primary data or yfin.dev fallback data.

Use the report as options-sentiment research, not as a trade recommendation.

## Data sources and fallback behavior

Barchart is the primary source. The collector uses Playwright Chromium to load Barchart put/call pages and stores raw diagnostics in the daily archive.

If Barchart collection fails for a symbol, the tool falls back to the free yfin.dev options-chain API. yfin.dev fallback can still calculate expiration-level put/call volume and open-interest ratios, but it does not provide Barchart-only top metrics such as IV Rank or IV Percentile. Fallback runs write `{SYMBOL}-yfin-raw.json` and mark the report source as `yfin.dev`.

## CLI command reference

| Task | Command |
| --- | --- |
| Run default watchlist without email | `options-put-call-report run --no-email` |
| Run selected symbols | `options-put-call-report run --no-email META MSFT NOW` |
| Run symbols from a file | `options-put-call-report run --no-email --symbols-file watchlist.txt` |
| Configure Gmail email | `options-put-call-report setup-email` |
| Run and send email | `options-put-call-report run --send-email` |
| Install Playwright Chromium for pipx install | `python3 -m pipx run --spec playwright playwright install chromium` |
| Install Playwright Chromium in a checkout | `python -m playwright install chromium` |

## Outputs

By default, reports and raw collection artifacts are written under `archive/YYYY-MM-DD/`:

- `report.html` - polished dashboard report.
- `report.md` - Markdown report.
- `{SYMBOL}-expirations.csv` - raw expiration table.
- `{SYMBOL}-snapshot.json` - normalized snapshot.
- `{SYMBOL}-raw.json` and `{SYMBOL}-raw.html` - collection diagnostics.
- `{SYMBOL}-yfin-raw.json` - fallback yfin.dev raw responses, written only when yfin.dev fallback is used.

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
launchctl list | grep com.sri.options-put-call-reporter
```

The scheduled job runs at 2:30 PM Pacific Time, which corresponds to 5:30 PM Eastern Time. Logs are written to:

- `archive/runner.log`
- `archive/launchd.out.log`
- `archive/launchd.err.log`

The scheduled runner captures the same concise progress output in these logs.

## Documentation for maintainers and agents

- `docs/ARCHITECTURE.md` explains runtime flow, source metadata, module responsibilities, and safe change points.
- `docs/MAINTENANCE.md` explains local validation, protected `main`, CI, Dependabot auto-merge, and release checks.
- `docs/PUBLISHING.md` explains initial GitHub publication.
- `CONTRIBUTING.md` explains contributor expectations.
- `SECURITY.md` explains vulnerability reporting and sensitive local files.
- `assistant-pack/README.md` explains portable assistant instructions.

This repository includes assistant instructions for maintaining and operating the tool:

- `AGENTS.md` for Codex-style agents.
- `CLAUDE.md` for Claude Code.
- `GEMINI.md` for Gemini CLI.
- `.github/copilot-instructions.md` for GitHub Copilot.
- `assistant-pack/` for portable skill/prompt files.

## Development

```bash
source .venv/bin/activate
pytest -q
python -m build
```

CI runs the test suite on Python 3.11 and 3.12 and builds the package.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `options-put-call-report` is not found after install | Shell has not picked up pipx's PATH update | Restart the shell or source your shell profile after `python3 -m pipx ensurepath`. |
| Browser collection fails immediately | Playwright Chromium is missing | For pipx installs, run `python3 -m pipx run --spec playwright playwright install chromium`. In a checkout, run `python -m playwright install chromium`. |
| Barchart collection fails for one symbol | Barchart page or network response failed | Inspect `archive/YYYY-MM-DD/{SYMBOL}-raw.html` and `{SYMBOL}-raw.json`; the tool may use yfin.dev fallback. |
| Report uses yfin.dev fallback | Barchart failed and fallback succeeded | Check the report data-source disclosure and `{SYMBOL}-yfin-raw.json`; Barchart-only IV Rank/Percentile metrics may be unavailable. |
| Email send fails | Gmail App Password or local recipient config is missing | Run `options-put-call-report setup-email` and confirm `config/email.local.json` exists locally. |
| Fresh install has no `config/symbols.json` | GitHub install uses packaged defaults | Run without a config file to use packaged defaults, or pass symbols in the terminal or via `--symbols-file`. |

## Security and privacy

Do not commit `config/email.local.json`, Gmail app passwords, `archive/`, or `data/`. Generated archives can include local diagnostics and market snapshots.

## License

MIT. See `LICENSE`.
```

- [x] **Step 2: Run focused docs test and confirm README assertions pass or only deeper docs fail**

Run:

```bash
./.venv/bin/python -m pytest tests/test_publication_assets.py -q
```

Expected: still fails until `docs/ARCHITECTURE.md`, `docs/MAINTENANCE.md`, and support-doc links are added.

## Task 3: Add architecture and maintenance docs

**Files:**
- Create: `docs/ARCHITECTURE.md`
- Create: `docs/MAINTENANCE.md`
- Modify: `docs/PUBLISHING.md`

- [x] **Step 1: Create architecture doc**

Create `docs/ARCHITECTURE.md`:

```markdown
# Architecture

`options-put-call-report` is a local Python CLI that collects options put/call data, normalizes it into snapshots, analyzes monthly sentiment, stores history, renders reports, and can email the results.

## Runtime flow

1. `src/reporter/cli.py` parses command-line arguments, loads symbols, opens history, starts collection, renders reports, and optionally sends email.
2. `src/reporter/collector.py` collects each symbol.
3. `src/reporter/analyzer.py` classifies expiration rows into research-oriented sentiment signals.
4. `src/reporter/history.py` persists snapshots in `data/history.sqlite3`.
5. `src/reporter/drift.py` compares current snapshots with prior saved rows.
6. `src/reporter/reporting.py` renders HTML, Markdown, and CSV files under `archive/YYYY-MM-DD/`.
7. `src/reporter/emailer.py` sends the HTML report when email is enabled.

## Collection and data sources

### Barchart primary collection

Barchart primary collection uses Playwright Chromium through `src/reporter/collector.py`. The collector archives raw diagnostics as `{SYMBOL}-raw.html` and `{SYMBOL}-raw.json` so failures can be investigated without repeating the live request.

### yfin.dev fallback

If Barchart collection raises a collection error for a symbol, `src/reporter/collector.py` falls back to yfin.dev options-chain data. The fallback aggregates contract-level calls and puts into expiration rows and archives `{SYMBOL}-yfin-raw.json`.

The fallback can produce expiration-level put/call volume and open-interest ratios. It does not provide Barchart-only top metrics such as IV Rank or IV Percentile, so reports disclose the source and fallback status.

## Snapshot and source metadata

`src/reporter/models.py` defines the snapshot data model. Each snapshot carries `DataSource` metadata so generated reports and saved history can show whether data came from Barchart or yfin.dev fallback.

`src/reporter/history.py` stores source metadata in SQLite alongside each snapshot. Older history rows default to the Barchart source when metadata is absent.

## Analysis and reporting

`src/reporter/analyzer.py` interprets monthly expiration rows and labels options sentiment as bullish, bearish, or neutral. These labels are research summaries, not financial advice.

`src/reporter/drift.py` compares current ratios with prior history and avoids emitting meaningless infinite or NaN drift text.

`src/reporter/reporting.py` renders:

- `report.html`
- `report.md`
- `{SYMBOL}-expirations.csv`
- `{SYMBOL}-snapshot.json`

Reports include data-source disclosure for every successful symbol.

## Email and scheduler boundaries

Email configuration lives in `config/email.local.json`, and Gmail App Passwords are stored in macOS Keychain. Email sending is isolated in `src/reporter/emailer.py` and `src/reporter/keychain.py`.

The macOS launchd scheduler scripts live under `scripts/`. Scheduled runs write logs to `archive/runner.log`, `archive/launchd.out.log`, and `archive/launchd.err.log`.

## Safe change points

- Change CLI behavior in `src/reporter/cli.py` and update README command examples.
- Change Barchart or yfin.dev parsing only in `src/reporter/collector.py`.
- Change sentiment thresholds in `src/reporter/analyzer.py` and update tests that describe signal meaning.
- Change saved history shape in `src/reporter/history.py` with additive migrations.
- Change report layout in `src/reporter/reporting.py` and update report tests.
- Change assistant guidance in `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `.github/instructions/options-reporter.instructions.md`, and `assistant-pack/`.
```

- [x] **Step 2: Create maintenance doc**

Create `docs/MAINTENANCE.md`:

```markdown
# Maintenance

This project is maintained as a Python 3.11+ CLI package with protected `main`, GitHub Actions CI, and Dependabot.

## Local validation

From a development checkout:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m playwright install chromium
pytest -q
python -m build
```

Run `pytest -q` and `python -m build` before publishing or claiming a change is complete.

## Branch and PR workflow

`main` is protected. Use a feature branch and pull request for changes:

```bash
git checkout -b feature/my-change
pytest -q
python -m build
git push -u origin feature/my-change
gh pr create --base main --head feature/my-change
gh pr checks --watch
```

Keep generated files out of commits:

- `archive/`
- `data/`
- `config/email.local.json`
- `dist/`
- `build/`
- `*.egg-info/`

## Required CI checks

GitHub Actions runs the package on:

- Python 3.11
- Python 3.12

The CI workflow installs the package with development dependencies, installs Playwright Chromium, runs `pytest -q`, and runs `python -m build`.

## Dependabot auto-merge

Dependabot opens weekly PRs for:

- GitHub Actions updates.
- Python package updates.

The repository allows GitHub native auto-merge and delete-branch-on-merge. `.github/workflows/dependabot-auto-merge.yml` enables auto-merge only when:

- The event is `pull_request_target`.
- `github.event.pull_request.user.login == 'dependabot[bot]'`.
- The PR is not a draft.
- `dependabot/fetch-metadata` reports `version-update:semver-patch` or `version-update:semver-minor`.

Major updates remain manual. If a Dependabot auto-merge job is skipped, inspect the run and metadata:

```bash
gh run list --workflow "Dependabot auto-merge" --limit 10
gh run view <run-id> --log
gh pr checks <number> --watch
```

Common skip causes:

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Job skipped on a non-Dependabot PR | PR author is not `dependabot[bot]` | Expected; only Dependabot PRs are eligible. |
| Auto-merge step skipped but job succeeds | Update is semver-major | Review and merge manually if acceptable. |
| Required checks block auto-merge | Python 3.11 or Python 3.12 failed or is pending | Fix the failing check or wait for completion. |

## Release checklist

1. Confirm `git status --short` is clean.
2. Run `pytest -q`.
3. Run `python -m build`.
4. Push a feature branch.
5. Open a pull request into protected `main`.
6. Confirm GitHub Actions passes.
7. Squash-merge after review.
8. Confirm the `main` push workflow passes.

## Documentation upkeep

Update `README.md` when CLI usage, outputs, install steps, data-source behavior, or troubleshooting changes.

Update `docs/ARCHITECTURE.md` when module responsibilities, data flow, persistence, or report outputs change.

Update assistant docs when commands, safety rules, or repo layout changes.
```

- [x] **Step 3: Link publishing guide to maintenance**

Add this paragraph after the target repository line in `docs/PUBLISHING.md`:

```markdown
For ongoing branch protection, CI, Dependabot, and release maintenance after the repository exists, see `docs/MAINTENANCE.md`.
```

- [x] **Step 4: Run focused docs tests**

Run:

```bash
./.venv/bin/python -m pytest tests/test_publication_assets.py -q
```

Expected: still fails until contributor and assistant docs link to the deeper docs.

## Task 4: Update contributor and assistant docs

**Files:**
- Modify: `CONTRIBUTING.md`
- Modify: `SECURITY.md`
- Modify: `assistant-pack/README.md`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `GEMINI.md`
- Modify: `.github/copilot-instructions.md`
- Modify: `.github/instructions/options-reporter.instructions.md`

- [x] **Step 1: Update CONTRIBUTING.md**

Add this section after "Pull request expectations":

```markdown
## Pull request checklist

- Run `pytest -q`.
- Run `python -m build`.
- Add or update tests for behavior changes.
- Update `README.md` when commands, outputs, data sources, or troubleshooting change.
- Update `docs/ARCHITECTURE.md` when runtime flow, persistence, or report generation changes.
- Update `docs/MAINTENANCE.md` when CI, branch protection, Dependabot, or release workflow changes.
- Keep generated archives, SQLite history, build artifacts, and local email config out of commits.
- Keep report language framed as research/sentiment, not financial advice.

## Maintainer references

- `docs/ARCHITECTURE.md` explains module responsibilities and data flow.
- `docs/MAINTENANCE.md` explains validation, protected `main`, CI, Dependabot, and release workflow.
```

- [x] **Step 2: Update SECURITY.md**

Add this sentence to the "Sensitive data" section:

```markdown
See `docs/MAINTENANCE.md` for the generated-file checklist used before publishing changes.
```

- [x] **Step 3: Update assistant-pack/README.md**

Add this section before "Safety":

```markdown
## Deeper project context

- `docs/ARCHITECTURE.md` explains runtime flow, source metadata, module responsibilities, and safe change points.
- `docs/MAINTENANCE.md` explains local validation, protected `main`, CI, Dependabot auto-merge, and release workflow.
```

- [x] **Step 4: Update root assistant instruction files**

Add this "Reference docs" section to `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md`:

```markdown
## Reference docs

- `docs/ARCHITECTURE.md` explains runtime flow, source metadata, module responsibilities, and safe change points.
- `docs/MAINTENANCE.md` explains local validation, protected `main`, CI, Dependabot auto-merge, and release workflow.
```

- [x] **Step 5: Update Copilot instruction files**

Add these bullets to `.github/copilot-instructions.md` under "Locations":

```markdown
- Architecture guide: `docs/ARCHITECTURE.md`.
- Maintenance guide: `docs/MAINTENANCE.md`.
```

Add these bullets to `.github/instructions/options-reporter.instructions.md`:

```markdown
- Architecture guide: `docs/ARCHITECTURE.md`.
- Maintenance guide: `docs/MAINTENANCE.md`.
```

- [x] **Step 6: Run focused docs tests and confirm GREEN**

Run:

```bash
./.venv/bin/python -m pytest tests/test_publication_assets.py -q
```

Expected: all publication asset tests pass.

## Task 5: Verify, review, and publish

**Files:**
- All documentation and test files changed in Tasks 1-4.

- [x] **Step 1: Run full local checks**

Run:

```bash
./.venv/bin/python -m pytest -q
./.venv/bin/python -m build
```

Expected: all tests pass and package build succeeds.

- [x] **Step 2: Inspect diff**

Run:

```bash
git --no-pager diff --stat
git --no-pager diff -- README.md docs/ARCHITECTURE.md docs/MAINTENANCE.md docs/PUBLISHING.md CONTRIBUTING.md SECURITY.md assistant-pack/README.md AGENTS.md CLAUDE.md GEMINI.md .github/copilot-instructions.md .github/instructions/options-reporter.instructions.md tests/test_publication_assets.py
```

Expected: only documentation and publication-asset tests changed.

- [x] **Step 3: Commit the docs refresh**

Run:

```bash
git add README.md docs/ARCHITECTURE.md docs/MAINTENANCE.md docs/PUBLISHING.md CONTRIBUTING.md SECURITY.md assistant-pack/README.md AGENTS.md CLAUDE.md GEMINI.md .github/copilot-instructions.md .github/instructions/options-reporter.instructions.md tests/test_publication_assets.py docs/superpowers/plans/2026-06-06-documentation-refresh.md
git commit -m "docs: improve user and maintainer documentation" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

- [x] **Step 4: Request code review**

Use `superpowers:requesting-code-review` on the branch diff against `origin/main`. Important review focus:

- README remains accurate for installation and CLI usage.
- Architecture and maintenance docs do not contradict current code or GitHub workflows.
- Assistant docs link to deeper docs without dropping required safety rules.

- [ ] **Step 5: Finish the development branch**

Use `superpowers:finishing-a-development-branch`. Choose PR workflow unless the user explicitly requests local merge.
