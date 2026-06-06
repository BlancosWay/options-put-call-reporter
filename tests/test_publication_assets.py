from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_pyproject_has_public_github_metadata() -> None:
    data = tomllib.loads(_read("pyproject.toml"))
    project = data["project"]

    assert project["name"] == "options-put-call-reporter"
    assert project["readme"] == "README.md"
    assert project["license"] == "MIT"
    assert project["license-files"] == ["LICENSE"]
    assert "Development Status :: 4 - Beta" in project["classifiers"]
    assert "License :: OSI Approved :: MIT License" not in project["classifiers"]
    assert "Topic :: Office/Business :: Financial" in project["classifiers"]
    assert project["authors"] == [{"name": "Sri", "email": "BlancosWay@users.noreply.github.com"}]
    assert project["maintainers"] == [{"name": "Sri", "email": "BlancosWay@users.noreply.github.com"}]
    assert project["urls"]["Repository"] == "https://github.com/BlancosWay/options-put-call-reporter"
    assert project["urls"]["Issues"] == "https://github.com/BlancosWay/options-put-call-reporter/issues"
    assert "build>=1,<2" in data["project"]["optional-dependencies"]["dev"]
    assert "setuptools>=77.0.3" in data["build-system"]["requires"]


def test_packaged_default_config_is_included_as_package_data() -> None:
    data = tomllib.loads(_read("pyproject.toml"))

    assert data["tool"]["setuptools"]["package-data"]["reporter"] == ["default_symbols.json"]
    assert "META" in _read("src/reporter/default_symbols.json")


def test_public_repository_docs_exist_and_cover_required_topics() -> None:
    required_files = [
        "README.md",
        "LICENSE",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
        "docs/PUBLISHING.md",
        "docs/ARCHITECTURE.md",
        "docs/MAINTENANCE.md",
    ]

    for path in required_files:
        assert (ROOT / path).exists(), path

    readme = _read("README.md")
    for text in [
        "python3 -m pipx install git+https://github.com/BlancosWay/options-put-call-reporter.git",
        "python3 -m pipx run --spec playwright playwright install chromium",
        "python -m playwright install chromium",
        "options-put-call-report run --no-email",
        "options-put-call-report run --no-email META MSFT NOW",
        "options-put-call-report setup-email",
        "launchd",
        "Not financial advice",
        "Ships assistant instructions for Claude Code, GitHub Copilot, Codex, and Gemini.",
        "After `ensurepath`, restart your shell",
        "Falls back to yfin.dev options-chain data when Barchart collection fails.",
        "Reports disclose the data source used for each symbol.",
        "`{SYMBOL}-yfin-raw.json` - fallback yfin.dev raw responses, written only when yfin.dev fallback is used.",
        "## Table of contents",
        "## What this produces",
        "## How to read the signal",
        "## Data sources and fallback behavior",
        "## CLI command reference",
        "Symptom",
        "Likely cause",
        "Fix",
        "`{SYMBOL}-failure.html`",
        "`{SYMBOL}-failure.png`",
        "docs/ARCHITECTURE.md",
        "docs/MAINTENANCE.md",
    ]:
        assert text in readme


def test_architecture_doc_covers_runtime_flow_and_change_points() -> None:
    architecture = _read("docs/ARCHITECTURE.md")

    for text in [
        "CLI orchestration",
        "src/reporter/cli.py",
        "Barchart primary collection",
        "{SYMBOL}-failure.html",
        "{SYMBOL}-failure.png",
        "yfin.dev fallback",
        "DataSource",
        "src/reporter/collector.py",
        "src/reporter/analyzer.py",
        "src/reporter/history.py",
        "src/reporter/reporting.py",
        "archive/YYYY-MM-DD/",
        "data/history.sqlite3",
        "macOS Keychain",
        "launchd",
        "Safe change points",
    ]:
        assert text in architecture


def test_maintenance_doc_covers_ci_dependabot_and_release_workflow() -> None:
    maintenance = _read("docs/MAINTENANCE.md")

    for text in [
        "pytest -q",
        "python -m build",
        "protected `main`",
        "Python 3.11",
        "Python 3.12",
        "Dependabot auto-merge",
        "semver patch and minor",
        "major updates remain manual",
        "github.event.pull_request.user.login",
        "gh pr checks",
        "gh run list",
        "archive/",
        "data/",
        "config/email.local.json",
    ]:
        assert text in maintenance


def test_public_docs_describe_existing_assistant_assets() -> None:
    readme = _read("README.md")

    for text in [
        "This repository includes assistant instructions for maintaining and operating the tool:",
        "`AGENTS.md` for Codex-style agents.",
        "`CLAUDE.md` for Claude Code.",
        "`GEMINI.md` for Gemini CLI.",
        "`.github/copilot-instructions.md` for GitHub Copilot.",
        "`assistant-pack/` for portable skill/prompt files.",
        "See `assistant-pack/README.md` for copy/install guidance.",
    ]:
        assert text in readme


def test_publishing_docs_include_existing_origin_safe_commands() -> None:
    publishing = _read("docs/PUBLISHING.md")

    assert "Create an empty public GitHub repository named `BlancosWay/options-put-call-reporter` before running the fallback commands." in publishing
    assert "git remote add origin https://github.com/BlancosWay/options-put-call-reporter.git 2>/dev/null || git remote set-url origin https://github.com/BlancosWay/options-put-call-reporter.git" in publishing
    assert "git push -u origin HEAD" in publishing
    assert "gh repo create BlancosWay/options-put-call-reporter --public --source=. --remote=origin --push" not in publishing


def test_publication_guidance_uses_safe_push_commands() -> None:
    publication_paths = [
        "docs/PUBLISHING.md",
        "docs/superpowers/specs/2026-06-05-github-publishing-agent-distribution-design.md",
        "docs/superpowers/plans/2026-06-06-github-publishing-agent-distribution.md",
    ]

    for path in publication_paths:
        content = _read(path)
        assert "gh repo create BlancosWay/options-put-call-reporter --public --source=. --remote=origin --push" not in content
        assert "git push -u origin feature/daily-options-report" not in content


def test_publication_assets_target_blancosway_not_prior_owner() -> None:
    old_owner = "srina" + "del"
    publication_paths = [
        "pyproject.toml",
        "README.md",
        "docs/PUBLISHING.md",
        "docs/superpowers/specs/2026-06-05-github-publishing-agent-distribution-design.md",
        "docs/superpowers/plans/2026-06-06-github-publishing-agent-distribution.md",
    ]

    for path in publication_paths:
        content = _read(path)
        assert old_owner not in content
        assert "BlancosWay/options-put-call-reporter" in content or "BlancosWay@users.noreply.github.com" in content


def test_gitignore_covers_public_repo_runtime_and_build_artifacts() -> None:
    gitignore = _read(".gitignore")

    for pattern in [
        ".venv/",
        "archive/",
        "data/",
        "config/email.local.json",
        "dist/",
        "build/",
        "*.egg-info/",
        ".coverage",
        ".env",
    ]:
        assert pattern in gitignore


def test_assistant_instruction_pack_targets_all_supported_agents() -> None:
    required_files = [
        "AGENTS.md",
        "CLAUDE.md",
        "GEMINI.md",
        ".github/copilot-instructions.md",
        ".github/instructions/options-reporter.instructions.md",
        "assistant-pack/README.md",
        "assistant-pack/claude/options-put-call-reporter/SKILL.md",
        "assistant-pack/prompts/options-report-agent.md",
    ]

    for path in required_files:
        assert (ROOT / path).exists(), path

    combined = "\n".join(_read(path) for path in required_files)
    for text in [
        "options-put-call-report run --no-email",
        "pytest -q",
        "python -m build",
        "python -m playwright install chromium",
        "config/symbols.json",
        "archive/YYYY-MM-DD",
        "data/history.sqlite3",
        "Barchart",
        "macOS Keychain",
        "not financial advice",
        "Claude Code",
        "GitHub Copilot",
        "Codex",
        "Gemini",
        "docs/ARCHITECTURE.md",
        "docs/MAINTENANCE.md",
    ]:
        assert text in combined

    for native_file in ["AGENTS.md", "CLAUDE.md", "GEMINI.md", ".github/copilot-instructions.md"]:
        content = _read(native_file)
        for text in ["config/symbols.json", "archive/YYYY-MM-DD", "data/history.sqlite3", "pytest -q", "python -m build", "Barchart"]:
            assert text in content, f"{native_file} missing {text}"


def test_github_ci_runs_tests_and_package_build() -> None:
    ci = _read(".github/workflows/ci.yml")

    for text in [
        "push:",
        "pull_request:",
        "python-version: ['3.11', '3.12']",
        "python -m pip install -e \".[dev]\"",
        "python -m playwright install --with-deps chromium",
        "permissions:",
        "contents: read",
        "pytest -q",
        "python -m build",
    ]:
        assert text in ci


def test_dependabot_updates_actions_and_python_dependencies() -> None:
    dependabot = _read(".github/dependabot.yml")

    for text in [
        "package-ecosystem: \"github-actions\"",
        "directory: \"/\"",
        "package-ecosystem: \"pip\"",
        "interval: \"weekly\"",
    ]:
        assert text in dependabot


def test_dependabot_auto_merge_only_allows_patch_and_minor_updates() -> None:
    workflow_path = ROOT / ".github/workflows/dependabot-auto-merge.yml"

    assert workflow_path.exists()

    workflow = workflow_path.read_text(encoding="utf-8")

    for text in [
        "pull_request_target:",
        "github.event.pull_request.user.login == 'dependabot[bot]'",
        "!github.event.pull_request.draft",
        "contents: write",
        "pull-requests: write",
        "dependabot/fetch-metadata@v2",
        "version-update:semver-patch",
        "version-update:semver-minor",
        "gh pr merge --auto --squash \"$PR_URL\"",
    ]:
        assert text in workflow

    assert "github.actor == 'dependabot[bot]'" not in workflow
    assert "version-update:semver-major" not in workflow
