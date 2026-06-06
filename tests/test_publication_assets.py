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
    assert project["license"] == {"file": "LICENSE"}
    assert "Development Status :: 4 - Beta" in project["classifiers"]
    assert "Topic :: Office/Business :: Financial" in project["classifiers"]
    assert project["urls"]["Repository"] == "https://github.com/srinadel/options-put-call-reporter"
    assert project["urls"]["Issues"] == "https://github.com/srinadel/options-put-call-reporter/issues"
    assert "build>=1,<2" in data["project"]["optional-dependencies"]["dev"]


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
    ]

    for path in required_files:
        assert (ROOT / path).exists(), path

    readme = _read("README.md")
    for text in [
        "python3 -m pipx install git+https://github.com/srinadel/options-put-call-reporter.git",
        "python3 -m pipx run --spec playwright playwright install chromium",
        "python -m playwright install chromium",
        "options-put-call-report run --no-email",
        "options-put-call-report run --no-email META MSFT NOW",
        "options-put-call-report setup-email",
        "launchd",
        "Not financial advice",
        "Ships assistant instructions for Claude Code, GitHub Copilot, Codex, and Gemini.",
        "After `ensurepath`, restart your shell",
    ]:
        assert text in readme


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

    assert "git remote add origin https://github.com/srinadel/options-put-call-reporter.git 2>/dev/null || git remote set-url origin https://github.com/srinadel/options-put-call-reporter.git" in publishing
    assert "git push -u origin HEAD" in publishing
    assert "gh repo create srinadel/options-put-call-reporter --public --source=. --remote=origin --push" not in publishing


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
        "python -m playwright install chromium",
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
