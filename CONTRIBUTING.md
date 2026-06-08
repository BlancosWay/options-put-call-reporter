# Contributing

## Development setup

```bash
python3.11 scripts/setup_local.py
source .venv/bin/activate
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
- Update `README.md` only when the concise landing page needs to change.
- Update `docs/SETUP.md` when install, setup, or troubleshooting commands change.
- Update `docs/EMAIL.md` when email setup, keyring, or secret handling changes.
- Update `docs/OUTPUTS.md` when outputs, data sources, fallback behavior, or report diagnostics change.
- Update `docs/ARCHITECTURE.md` when runtime flow, persistence, or report generation changes.
- Update `docs/MAINTENANCE.md` when CI, branch protection, Dependabot, or release workflow changes.
- Keep generated archives, SQLite history, build artifacts, and local email config out of commits.
- Keep report language framed as research/sentiment, not financial advice.

## Maintainer references

- `docs/ARCHITECTURE.md` explains module responsibilities and data flow.
- `docs/MAINTENANCE.md` explains validation, protected `main`, CI, Dependabot, and release workflow.

## Local data

The reporter writes runtime files to `archive/` and `data/`. These paths are ignored and should not be committed.
