# GitHub Publishing and Agent Distribution Design

## Goal

Publish `options-put-call-reporter` as a production-ready public GitHub project under `BlancosWay/options-put-call-reporter`, usable as a Python CLI tool and as an assistant-ready workflow package for Claude Code, GitHub Copilot, Codex, and Gemini.

## Scope

This release is GitHub-first. It will prepare and publish a public repository, but it will not publish to PyPI in this iteration. The CLI install path will be from GitHub, such as `pipx install git+https://github.com/BlancosWay/options-put-call-reporter.git`.

The assistant distribution will be marketplace-style and portable: platform-native instruction files in the repository plus a reusable `assistant-pack/` directory that can be copied into assistant ecosystems. If official marketplace publication requires accounts, APIs, or tools unavailable in the local environment, the repository will include exact publishing instructions and remain ready for manual submission.

## Repository Packaging

The project will keep the existing Python package layout:

- CLI entry point: `options-put-call-report`
- Source package: `src/reporter/`
- Tests: `tests/`
- Default watchlist config: `config/symbols.json`

Production metadata will be added or expanded:

- `pyproject.toml` will include README, MIT license metadata, keywords, classifiers, project URLs, and author/maintainer information for `@BlancosWay`.
- `LICENSE` will use the MIT license with copyright attribution to Sri.
- `.gitignore` will continue excluding local runtime files and will also cover build artifacts, coverage files, environment files, and common tool caches.
- README will become the public landing page with features, install, quickstart, custom symbols, email setup, scheduler setup, generated outputs, troubleshooting, security/privacy notes, and a financial-disclaimer section.

## Assistant and Skill Distribution

The repository will ship two complementary assistant surfaces.

### Platform-native instruction files

Root and platform-specific files will give coding agents project context automatically:

- `AGENTS.md` for Codex-style agents.
- `CLAUDE.md` for Claude Code.
- `GEMINI.md` for Gemini CLI.
- `.github/copilot-instructions.md` for GitHub Copilot repository instructions.
- `.github/instructions/options-reporter.instructions.md` for Copilot path/task-specific guidance.

These files will cover:

- how to install and run the tool;
- where configuration, reports, archives, and history live;
- how to run tests and CI-equivalent checks;
- safe handling of Gmail app passwords and local archives;
- expectations for Playwright/Barchart collection changes;
- the rule that outputs are options-sentiment research, not financial advice.

### Portable assistant pack

The `assistant-pack/` directory will make the workflow reusable outside this repo:

- `assistant-pack/README.md` will explain how to install or copy the assistant instructions for Claude Code, GitHub Copilot, Codex, and Gemini.
- `assistant-pack/claude/options-put-call-reporter/SKILL.md` will provide a Claude/Superpowers-style skill definition for helping users install, run, interpret, and maintain the reporter.
- `assistant-pack/prompts/options-report-agent.md` will provide a platform-neutral agent prompt that can be pasted into assistants that do not support file-based skills.

The assistant pack will not claim to provide investment advice. It will frame reports as put/call sentiment summaries and require users to verify outputs before acting.

## GitHub Gates

GitHub Actions will provide the first production gate:

- Workflow: `.github/workflows/ci.yml`
- Triggers: `push` and `pull_request`
- Runtime: Python 3.11 and 3.12 on Ubuntu
- Steps:
  - checkout;
  - set up Python;
  - install the package with dev dependencies;
  - install Playwright Chromium;
  - run `pytest -q`;
  - build the Python package with `python -m build`.

Dependabot will be configured for:

- GitHub Actions updates;
- Python package updates for `pyproject.toml`.

Branch protection cannot be enforced until the GitHub repository exists, so the README or contributing docs will state that CI should be required before merging.

## Community and Security Docs

The repository will include:

- `CONTRIBUTING.md` with setup, test, and PR expectations.
- `SECURITY.md` with vulnerability reporting guidance and reminders not to share Gmail app passwords or generated archives containing local data.
- `CODE_OF_CONDUCT.md` using a concise contributor covenant style.

## Publishing Flow

The implementation will attempt to publish to GitHub only through authenticated local tooling if available without exposing secrets. Preferred flow:

1. Confirm the worktree is clean after implementation.
2. Verify tests pass.
3. Create or connect the public GitHub repository `BlancosWay/options-put-call-reporter`.
4. Add `origin` if missing.
5. Push the publication branch.

If GitHub CLI/API authentication is unavailable, the implementation will leave the repository ready and provide exact commands for manual repository creation and push.

## Testing

Tests will cover new behavior where practical:

- repository hygiene tests for required public files;
- CI workflow structure checks;
- package metadata checks;
- assistant-pack file existence and core content checks.

The full test suite must pass before any completion claim or publishing step.

## Out of Scope

- PyPI release automation.
- Paid marketplace submissions.
- Cloud hosting or a web UI.
- Financial recommendations or trade execution.
- Storing credentials outside the existing macOS Keychain flow.
