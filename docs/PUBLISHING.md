# Publishing to GitHub

Target repository: `https://github.com/BlancosWay/options-put-call-reporter`

For ongoing branch protection, CI, Dependabot, and release maintenance after the repository exists, see `docs/MAINTENANCE.md`.

## Create the public repository with GitHub CLI

```bash
gh repo create BlancosWay/options-put-call-reporter --public
```

Then set or update `origin` and push the current branch:

```bash
git remote add origin https://github.com/BlancosWay/options-put-call-reporter.git 2>/dev/null || git remote set-url origin https://github.com/BlancosWay/options-put-call-reporter.git
git push -u origin HEAD
```

## Manual fallback

If GitHub CLI is unavailable:

Create an empty public GitHub repository named `BlancosWay/options-put-call-reporter` before running the fallback commands.

```bash
git remote add origin https://github.com/BlancosWay/options-put-call-reporter.git 2>/dev/null || git remote set-url origin https://github.com/BlancosWay/options-put-call-reporter.git
git push -u origin HEAD
```

Then open GitHub, create a pull request into `main`, and require the CI workflow before merging.

## Release checklist

1. Run `pytest -q`.
2. Run `python -m build`.
3. Confirm `git status --short` is clean.
4. Push the branch.
5. Confirm GitHub Actions passes.
