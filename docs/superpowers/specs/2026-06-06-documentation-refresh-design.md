# Documentation Refresh Design

## Goal

Improve the public README and supporting documentation so a new user can install, run, understand, troubleshoot, and maintain `options-put-call-report` without reading source code.

## Audience

- **Users:** want to install the CLI, run a report, understand the generated signal, and troubleshoot common setup issues.
- **Maintainers:** want to understand the data flow, branch protection, CI, Dependabot behavior, and safe release process.
- **AI assistants/agents:** need concise repo-specific instructions plus pointers to deeper architecture and maintenance docs.

## Approach

Keep `README.md` as the landing page and make it more navigable. Add focused supporting docs instead of making the README excessively long:

- `docs/ARCHITECTURE.md` for system flow, modules, data sources, outputs, and change hotspots.
- `docs/MAINTENANCE.md` for CI, branch protection, Dependabot auto-merge policy, release checks, and local upkeep.
- Existing `docs/PUBLISHING.md` remains as the initial GitHub publishing guide, but points to maintenance procedures for ongoing work.

## README Changes

Add:

- Table of contents.
- "What this produces" section with a compact example of the output shape and the files written.
- "How to read the signal" section explaining put/call ratio, bullish/bearish/neutral labels, monthly expirations, drift, and source disclosure.
- "Data sources and fallback behavior" section explaining Barchart primary collection, yfin.dev fallback, unavailable fallback metrics, and raw archive files.
- Compact CLI command reference.
- Troubleshooting table with symptom, likely cause, and fix.
- Links to architecture, maintenance, publishing, contributing, security, and assistant-pack docs.

Preserve:

- Not-financial-advice language.
- Existing install, quickstart, email, scheduler, security, and license coverage.
- Current GitHub repository URLs.

## Supporting Docs

### `docs/ARCHITECTURE.md`

Document:

- CLI orchestration through `src/reporter/cli.py`.
- Collection flow: Barchart primary, yfin.dev fallback, raw diagnostics.
- Analysis flow: monthly expiration rows, sentiment classification, drift summaries.
- Persistence and outputs: SQLite history, HTML/Markdown/CSV reports, archive files.
- Email and scheduler boundaries.
- Safe change points: collector, reporting, history, assistant docs.

### `docs/MAINTENANCE.md`

Document:

- Local setup and validation commands.
- Branch and PR workflow with protected `main`.
- Required GitHub Actions checks.
- Dependabot auto-merge policy: patch/minor only; major remains manual.
- How to inspect auto-merge runs and common skip causes.
- Release checklist.
- Generated/local files that must stay out of git.

### Existing support docs

- `CONTRIBUTING.md`: add docs/build/test checklist and link maintenance docs.
- `SECURITY.md`: keep concise, add direct reminders about generated archives and market-data disclaimer.
- `assistant-pack/README.md` and agent instruction files: link to architecture and maintenance docs to reduce duplicated context.

## Testing

Update `tests/test_publication_assets.py` to require the new documentation topics and links:

- README includes the new major sections and critical phrases.
- `docs/ARCHITECTURE.md` and `docs/MAINTENANCE.md` exist and cover core modules/policies.
- Assistant/contributor docs link to the deeper docs.

Run:

```bash
./.venv/bin/python -m pytest tests/test_publication_assets.py -q
./.venv/bin/python -m pytest -q
./.venv/bin/python -m build
```

## Out of Scope

- Changing CLI behavior.
- Adding screenshots or generated report images.
- Publishing to PyPI.
- Changing branch protection or Dependabot policy.
