# Publishing to GitHub

Target repository: `https://github.com/srinadel/options-put-call-reporter`

## Create the public repository with GitHub CLI

```bash
gh repo create srinadel/options-put-call-reporter --public --source=. --remote=origin --push
```

## Manual fallback

If GitHub CLI is unavailable:

```bash
git remote add origin https://github.com/srinadel/options-put-call-reporter.git 2>/dev/null || git remote set-url origin https://github.com/srinadel/options-put-call-reporter.git
git push -u origin feature/daily-options-report
```

Then open GitHub, create a pull request into `main`, and require the CI workflow before merging.

## Release checklist

1. Run `pytest -q`.
2. Run `python -m build`.
3. Confirm `git status --short` is clean.
4. Push the branch.
5. Confirm GitHub Actions passes.
