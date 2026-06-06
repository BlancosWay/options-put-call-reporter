# Dependabot Auto-Merge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable safe auto-merge for Dependabot patch and minor dependency PRs once required CI checks pass.

**Architecture:** Keep branch protection as the safety gate. Add a dedicated `pull_request_target` workflow that runs only for Dependabot PRs, fetches Dependabot metadata, and enables GitHub native auto-merge for semver patch/minor updates. Add publication-asset tests that verify the workflow exists, uses least practical permissions, targets Dependabot only, and excludes major updates.

**Tech Stack:** GitHub Actions, GitHub CLI, Dependabot metadata action, pytest.

---

## Files

- Create `.github/workflows/dependabot-auto-merge.yml`: GitHub Actions workflow for Dependabot patch/minor auto-merge.
- Modify `tests/test_publication_assets.py`: add deterministic checks for the auto-merge workflow policy.

## Task 1: Add tests for Dependabot auto-merge policy

- [x] Add a pytest that asserts `.github/workflows/dependabot-auto-merge.yml` exists.
- [x] Add assertions that the workflow uses `pull_request_target`, restricts execution to `dependabot[bot]`, grants `contents: write` and `pull-requests: write`, uses `dependabot/fetch-metadata@v2`, enables `gh pr merge --auto --squash`, includes semver patch and minor update types, and does not include semver major.
- [x] Run `./.venv/bin/python -m pytest tests/test_publication_assets.py -q` and confirm the new test fails because the workflow is missing.

## Task 2: Add Dependabot auto-merge workflow

- [x] Create `.github/workflows/dependabot-auto-merge.yml` with a single job that only runs when `github.actor == 'dependabot[bot]'` and the PR is not a draft.
- [x] Use `dependabot/fetch-metadata@v2` to classify update type.
- [x] Run `gh pr merge --auto --squash "$PR_URL"` only for `version-update:semver-patch` or `version-update:semver-minor`.
- [x] Run `./.venv/bin/python -m pytest tests/test_publication_assets.py -q` and confirm it passes.

## Task 3: Verify and publish

- [x] Enable repository auto-merge and delete-branch-on-merge with `gh repo edit BlancosWay/options-put-call-reporter --enable-auto-merge --delete-branch-on-merge`.
- [x] Run `./.venv/bin/python -m pytest -q`.
- [x] Run `./.venv/bin/python -m build`.
- [x] Commit the workflow and test changes.
- [ ] Push the branch and create a pull request.
- [ ] Confirm GitHub Actions passes for the pull request.
