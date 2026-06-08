# Maintenance

This project is maintained as a Python 3.11+ CLI package with protected `main`, GitHub Actions CI, and Dependabot.

## Local validation

From a development checkout:

```bash
python3.11 scripts/setup_local.py
source .venv/bin/activate
pytest -q
python -m build
```

Run `pytest -q` and `python -m build` before publishing or claiming a change is complete.

## Secret storage maintenance

- macOS: `setup-email` stores the Resend API key in macOS Keychain. Rotate by rerunning setup, or delete stale entries with Keychain Access.
- Windows: `setup-email` stores the key in Windows Credential Manager. Rotate by rerunning setup, or delete stale entries with Credential Manager.
- Linux desktop: `setup-email` requires an available Secret Service/KWallet backend. If the keyring is locked or unavailable, unlock it or use `RESEND_API_KEY` / `RESEND_API_KEY_FILE`.
- Linux headless/server: prefer `RESEND_API_KEY` or `RESEND_API_KEY_FILE`; restart scheduled jobs after rotating the secret.
- Containers/Kubernetes: mount the key as a secret file and set `RESEND_API_KEY_FILE`.
- GitHub Actions: store the key in repository or environment secrets and expose it as `RESEND_API_KEY`.

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

## Auto-merge policy

Dependabot opens weekly PRs for:

- GitHub Actions updates.
- Python package updates.

The repository allows GitHub native auto-merge and delete-branch-on-merge. `.github/workflows/dependabot-auto-merge.yml` enables auto-merge only for semver patch and minor updates when:

- The event is `pull_request_target`.
- `github.event.pull_request.user.login == 'dependabot[bot]'`.
- The PR is not a draft.
- `dependabot/fetch-metadata` reports `version-update:semver-patch` or `version-update:semver-minor`.

By policy, major updates remain manual. If an auto-merge job is skipped, inspect the run and metadata:

### Owner auto-merge

BlancosWay PRs are eligible for auto-merge when:

- The event is `pull_request_target`.
- `github.event.pull_request.user.login == 'BlancosWay'`.
- The PR is not a draft.

The workflow runs `gh pr merge --auto --squash`, which enables native GitHub auto-merge. Protected branch required checks still gate the final merge; GitHub waits for Python 3.11 and Python 3.12 checks to pass before merging.

```bash
gh run list --workflow "Dependabot auto-merge" --limit 10
gh run view <run-id> --log
gh pr checks <number> --watch
```

Common skip causes:

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Dependabot job skipped on a non-Dependabot PR | PR author is not `dependabot[bot]` | Expected; only Dependabot PRs are eligible for that job. |
| Owner job skipped on a non-BlancosWay PR | PR author is not `BlancosWay` | Expected; only BlancosWay PRs are eligible for owner auto-merge. |
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

Keep `README.md` as the concise landing page. Update it only when the quick start, common command list, or documentation map changes.

Update `docs/SETUP.md` when install paths, local setup, Windows commands, or setup troubleshooting changes.

Update `docs/EMAIL.md` when Resend setup, keyring behavior, secret lookup, or email troubleshooting changes.

Update `docs/OUTPUTS.md` when report files, signal descriptions, data-source fallback behavior, or diagnostic artifacts change.

Update `docs/ARCHITECTURE.md` when module responsibilities, data flow, persistence, or report outputs change.

Update assistant docs when commands, safety rules, or repo layout changes.

For keyring setup failures, `setup-email` reuses an already-readable matching keyring item if macOS refuses to rewrite it. Other setup failures print a sanitized `Keyring error:` detail that includes the underlying Python `keyring` exception class and message while omitting the Resend API key. Use that detail to diagnose locked, stale, or unavailable desktop keyrings, and recommend `RESEND_API_KEY` or `RESEND_API_KEY_FILE` when keyring storage is not practical.
