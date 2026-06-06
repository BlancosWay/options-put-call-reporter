# Owner Auto-Merge Design

## Goal

Automatically enable GitHub native auto-merge for non-draft pull requests authored by `BlancosWay` after required branch-protection checks pass.

## Current state

The repository already has:

- Protected `main` with required Python 3.11 and Python 3.12 checks.
- Repository-level auto-merge enabled.
- `.github/workflows/dependabot-auto-merge.yml`, which runs on `pull_request_target`.
- Dependabot policy that enables auto-merge only for semver patch and minor updates.

## Design

Extend the existing auto-merge workflow rather than creating a second workflow.

Keep the Dependabot policy separate from the owner policy:

- Dependabot job:
  - Runs only when `github.event.pull_request.user.login == 'dependabot[bot]'`.
  - Requires non-draft PRs.
  - Uses `dependabot/fetch-metadata`.
  - Enables auto-merge only for semver patch and minor updates.
  - Leaves major updates manual.

- Owner job:
  - Runs only when `github.event.pull_request.user.login == 'BlancosWay'`.
  - Requires non-draft PRs.
  - Runs `gh pr merge --auto --squash "$PR_URL"`.
  - Relies on branch protection to wait for required Python 3.11 and Python 3.12 checks before GitHub performs the merge.

The workflow should not auto-merge PRs authored by any other user or app.

## Documentation

Update `docs/MAINTENANCE.md` so maintainers understand:

- `BlancosWay` PRs are eligible for auto-merge after checks pass.
- Dependabot patch/minor PRs remain eligible.
- Dependabot major updates remain manual.
- Non-draft status is required.
- Required checks still gate the final merge.

## Testing

Update `tests/test_publication_assets.py` to assert:

- The workflow contains a `BlancosWay` author gate.
- The owner job uses `gh pr merge --auto --squash "$PR_URL"`.
- The maintenance doc describes owner PR auto-merge and required-check gating.
- The existing Dependabot patch/minor constraints remain in place.

Run:

```bash
./.venv/bin/python -m pytest tests/test_publication_assets.py -q
./.venv/bin/python -m pytest -q
./.venv/bin/python -m build
```

## Out of scope

- Auto-merging PRs from other users.
- Auto-merging draft PRs.
- Changing branch protection.
- Bypassing required CI checks.
- Changing the Dependabot major-update policy.
