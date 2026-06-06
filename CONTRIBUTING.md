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

## Local data

The reporter writes runtime files to `archive/` and `data/`. These paths are ignored and should not be committed.
