# Owner Auto-Merge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically enable GitHub native squash auto-merge for non-draft pull requests authored by `BlancosWay` once protected-branch checks pass.

**Architecture:** Extend the existing `.github/workflows/dependabot-auto-merge.yml` workflow instead of adding another workflow. Keep the Dependabot patch/minor policy in its own job and add a separate owner job gated by `github.event.pull_request.user.login == 'BlancosWay'`. Branch protection remains the final gate for Python 3.11 and Python 3.12 checks.

**Tech Stack:** GitHub Actions, GitHub CLI, pytest documentation/workflow assertions.

---

## Files

- Modify `.github/workflows/dependabot-auto-merge.yml`: add a separate `owner-auto-merge` job for `BlancosWay` PRs.
- Modify `tests/test_publication_assets.py`: assert the owner policy exists and does not weaken Dependabot patch/minor restrictions.
- Modify `docs/MAINTENANCE.md`: document owner PR auto-merge policy and required-check behavior.

## Task 1: Add failing tests for owner auto-merge policy

**Files:**
- Modify: `tests/test_publication_assets.py`

- [ ] **Step 1: Add workflow assertions**

Append this test after `test_dependabot_auto_merge_only_allows_patch_and_minor_updates()`:

```python
def test_owner_auto_merge_enables_auto_merge_for_blancosway_prs() -> None:
    workflow = _read(".github/workflows/dependabot-auto-merge.yml")

    for text in [
        "owner-auto-merge:",
        "github.event.pull_request.user.login == 'BlancosWay'",
        "!github.event.pull_request.draft",
        "Enable auto-merge for BlancosWay PRs",
        "gh pr merge --auto --squash \"$PR_URL\"",
        "PR_URL: \"${{ github.event.pull_request.html_url }}\"",
    ]:
        assert text in workflow
```

- [ ] **Step 2: Add maintenance doc assertions**

In `test_maintenance_doc_covers_ci_dependabot_and_release_workflow()`, add these required strings:

```python
        "Owner auto-merge",
        "github.event.pull_request.user.login == 'BlancosWay'",
        "BlancosWay PRs",
        "required checks still gate the final merge",
```

- [ ] **Step 3: Run focused test and confirm RED**

Run:

```bash
./.venv/bin/python -m pytest tests/test_publication_assets.py -q
```

Expected: fails because the owner auto-merge workflow job and maintenance doc text do not exist yet.

## Task 2: Add owner auto-merge workflow job

**Files:**
- Modify `.github/workflows/dependabot-auto-merge.yml`

- [ ] **Step 1: Add a separate owner job**

Append this job under `jobs:` beside the existing Dependabot job:

```yaml
  owner-auto-merge:
    if: github.event.pull_request.user.login == 'BlancosWay' && !github.event.pull_request.draft
    runs-on: ubuntu-latest

    steps:
      - name: Enable auto-merge for BlancosWay PRs
        run: gh pr merge --auto --squash "$PR_URL"
        env:
          GH_TOKEN: "${{ secrets.GITHUB_TOKEN }}"
          PR_URL: "${{ github.event.pull_request.html_url }}"
```

- [ ] **Step 2: Run focused workflow tests**

Run:

```bash
./.venv/bin/python -m pytest tests/test_publication_assets.py::test_dependabot_auto_merge_only_allows_patch_and_minor_updates tests/test_publication_assets.py::test_owner_auto_merge_enables_auto_merge_for_blancosway_prs -q
```

Expected: owner workflow test passes; maintenance doc test still fails until docs are updated.

## Task 3: Document owner auto-merge policy

**Files:**
- Modify `docs/MAINTENANCE.md`

- [ ] **Step 1: Rename policy heading**

Change:

```markdown
## Dependabot auto-merge
```

to:

```markdown
## Auto-merge policy
```

- [ ] **Step 2: Add owner policy section**

Add this section after the Dependabot policy paragraph and before "Common skip causes":

```markdown
### Owner auto-merge

BlancosWay PRs are eligible for auto-merge when:

- The event is `pull_request_target`.
- `github.event.pull_request.user.login == 'BlancosWay'`.
- The PR is not a draft.

The workflow runs `gh pr merge --auto --squash`, which enables native GitHub auto-merge. Protected branch required checks still gate the final merge; GitHub waits for Python 3.11 and Python 3.12 checks to pass before merging.
```

- [ ] **Step 3: Update skip table**

Replace the first skip table row:

```markdown
| Job skipped on a non-Dependabot PR | PR author is not `dependabot[bot]` | Expected; only Dependabot PRs are eligible. |
```

with:

```markdown
| Dependabot job skipped on a non-Dependabot PR | PR author is not `dependabot[bot]` | Expected; only Dependabot PRs are eligible for that job. |
| Owner job skipped on a non-BlancosWay PR | PR author is not `BlancosWay` | Expected; only BlancosWay PRs are eligible for owner auto-merge. |
```

- [ ] **Step 4: Run focused publication tests and confirm GREEN**

Run:

```bash
./.venv/bin/python -m pytest tests/test_publication_assets.py -q
```

Expected: all publication asset tests pass.

## Task 4: Verify, review, and publish

**Files:**
- `.github/workflows/dependabot-auto-merge.yml`
- `tests/test_publication_assets.py`
- `docs/MAINTENANCE.md`
- `docs/superpowers/plans/2026-06-06-owner-auto-merge.md`

- [ ] **Step 1: Run full local checks**

Run:

```bash
./.venv/bin/python -m pytest -q
./.venv/bin/python -m build
```

Expected: all tests pass and the package builds.

- [ ] **Step 2: Inspect diff**

Run:

```bash
git --no-pager diff --stat
git --no-pager diff -- .github/workflows/dependabot-auto-merge.yml tests/test_publication_assets.py docs/MAINTENANCE.md docs/superpowers/plans/2026-06-06-owner-auto-merge.md
```

Expected: only workflow policy, documentation, tests, and plan files changed.

- [ ] **Step 3: Commit the owner auto-merge change**

Run:

```bash
git add .github/workflows/dependabot-auto-merge.yml tests/test_publication_assets.py docs/MAINTENANCE.md docs/superpowers/plans/2026-06-06-owner-auto-merge.md
git commit -m "ci: auto-merge owner pull requests" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

- [ ] **Step 4: Request code review**

Use `superpowers:requesting-code-review` on the branch diff against `origin/main`. Review focus:

- Owner job does not apply to other users.
- Dependabot major-update policy remains manual.
- Required checks still gate final native GitHub auto-merge.
- Workflow permissions remain no broader than current needs.

- [ ] **Step 5: Finish the development branch**

Use `superpowers:finishing-a-development-branch`. Use the PR workflow unless the user explicitly requests a local-only merge.
