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

The repository allows GitHub native auto-merge and delete-branch-on-merge. `.github/workflows/dependabot-auto-merge.yml` enables auto-merge only for semver patch and minor updates when:

- The event is `pull_request_target`.
- `github.event.pull_request.user.login == 'dependabot[bot]'`.
- The PR is not a draft.
- `dependabot/fetch-metadata` reports `version-update:semver-patch` or `version-update:semver-minor`.

By policy, major updates remain manual. If a Dependabot auto-merge job is skipped, inspect the run and metadata:

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
