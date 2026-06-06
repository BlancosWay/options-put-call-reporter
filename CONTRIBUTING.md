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
