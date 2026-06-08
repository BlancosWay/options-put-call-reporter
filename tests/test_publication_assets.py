from __future__ import annotations

import tomllib
import subprocess
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
        "docs/EMAIL.md",
        "docs/OUTPUTS.md",
        "docs/PUBLISHING.md",
        "docs/SETUP.md",
        "docs/ARCHITECTURE.md",
        "docs/MAINTENANCE.md",
    ]

    for path in required_files:
        assert (ROOT / path).exists(), path

    readme = _read("README.md")
    # README is intentionally a landing page; detailed references belong in docs/.
    assert len(readme.splitlines()) <= 180
    for text in [
        "python3 -m pipx install git+https://github.com/BlancosWay/options-put-call-reporter.git",
        "python3 -m pipx run --spec 'playwright>=1.46,<2' playwright install chromium",
        "python3.11 scripts/setup_local.py",
        "For Windows commands and Linux browser dependencies, see [docs/SETUP.md](docs/SETUP.md).",
        "Email delivery reads the Resend API key from `RESEND_API_KEY`, `RESEND_API_KEY_FILE`, or the system keyring.",
        "options-put-call-report run --no-email",
        "./.venv/bin/options-put-call-report run --no-email",
        "options-put-call-report run --no-email META MSFT NOW",
        "options-put-call-report setup-email",
        "Resend API key",
        "launchd",
        "Not financial advice",
        "assistant instructions for Claude Code, GitHub Copilot, Codex, and Gemini",
        "Start with a watchlist.",
        "Collect each symbol's options sentiment.",
        "Turn the data into a report you can compare over time.",
        "Optionally send or schedule the report when you want it automated.",
        "Falls back to yfin.dev options-chain data when Barchart collection fails.",
        "Reports disclose the data source used for each symbol.",
        "docs/SETUP.md",
        "docs/EMAIL.md",
        "docs/OUTPUTS.md",
        "docs/ARCHITECTURE.md",
        "docs/MAINTENANCE.md",
    ]:
        assert text in readme
    assert "| Area | Summary |" not in readme

    setup = _read("docs/SETUP.md")
    for text in [
        "## Prerequisites",
        "`python3.11 --version`",
        "`py -3.11 --version`",
        "### macOS",
        "### Linux",
        "python3 -m pipx run --spec 'playwright>=1.46,<2' playwright install --with-deps chromium",
        "### Windows PowerShell",
        "py -m pipx install git+https://github.com/BlancosWay/options-put-call-reporter.git",
        "py -m pipx run --spec 'playwright>=1.46,<2' playwright install chromium",
        "After `ensurepath`, restart your shell",
        "python3.11 -m venv --symlinks .venv",
        r".\.venv\Scripts\options-put-call-report.exe run --no-email",
        "python -m playwright install chromium",
        "python -m playwright install --with-deps chromium",
        "options-put-call-report run --config config/symbols.json --no-email",
        "options-put-call-report run --send-email --email-config path/to/email.local.json",
        "options-put-call-report run --no-email --run-date 2026-06-02T21:30:00",
        "| Windows | Windows Task Scheduler | Schedule `options-put-call-report run --send-email`",
        "set the working directory",
        "prefer an absolute executable path",
    ]:
        assert text in setup

    email = _read("docs/EMAIL.md")
    for text in [
        "Create a free Resend account, verify a sender identity or domain, and create a Resend API key.",
        "read -r -s -p \"Resend API key: \" RESEND_API_KEY",
        "Re-run `options-put-call-report setup-email`",
        "Older custom app configs",
        '"keychain_service": "options-put-call-reporter:resend-api-key"',
        '"resend_api_url": "https://api.resend.com/emails"',
        "Email failures include Resend stage diagnostics",
        "mkdir -p ~/.config/options-put-call-report",
        "Every `run --send-email` invocation also needs sender/recipient metadata",
        "`--email-config`",
        "`from_email` and `to_email`",
        "( umask 077; printf '%s\\n' \"$RESEND_API_KEY\" > ~/.config/options-put-call-report/resend-api-key )",
        "{\n  \"keychain_service\": \"options-put-call-reporter:resend-api-key\",",
    ]:
        assert text in email
    assert 'export RESEND_API_KEY="re_..."' not in email

    outputs = _read("docs/OUTPUTS.md")
    for text in [
        "`{SYMBOL}-yfin-raw.json` | Fallback yfin.dev raw responses, written only when yfin.dev fallback is used.",
        "`{SYMBOL}-failure.html`",
        "`{SYMBOL}-failure.png`",
        "## How to read the signal",
        "## Data sources and fallback behavior",
    ]:
        assert text in outputs

    security = _read("SECURITY.md")
    assert "data/history.sqlite3" not in security
    assert "`data`" in security

    contributing = _read("CONTRIBUTING.md")
    for text in [
        "python3.11 scripts/setup_local.py",
        "Update `docs/SETUP.md` when install, setup, or troubleshooting commands change.",
        "Update `docs/EMAIL.md` when email setup, keyring, or secret handling changes.",
        "Update `docs/OUTPUTS.md` when outputs, data sources, fallback behavior, or report diagnostics change.",
    ]:
        assert text in contributing


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
        "system keyring",
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
        "Owner auto-merge",
        "github.event.pull_request.user.login == 'BlancosWay'",
        "BlancosWay PRs",
        "required checks still gate the final merge",
        "github.event.pull_request.user.login",
        "gh pr checks",
        "gh run list",
        "archive/",
        "data/",
        "config/email.local.json",
        "docs/SETUP.md",
        "docs/EMAIL.md",
        "docs/OUTPUTS.md",
    ]:
        assert text in maintenance


def test_public_docs_describe_existing_assistant_assets() -> None:
    readme = _read("README.md")

    for text in [
        "This repository ships assistant instructions for Claude Code, GitHub Copilot, Codex, and Gemini for maintaining and operating the tool:",
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


def test_superpowers_working_docs_are_not_public_repo_assets() -> None:
    gitignore = _read(".gitignore")

    assert "docs/superpowers/" in gitignore

    tracked = subprocess.run(
        ["git", "ls-files", "docs/superpowers"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    ignored = subprocess.run(
        ["git", "check-ignore", "docs/superpowers/example.md"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert tracked.stdout == ""
    assert ignored.stdout.strip() == "docs/superpowers/example.md"


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
        "system keyring",
        "not financial advice",
        "Claude Code",
        "GitHub Copilot",
        "Codex",
        "Gemini",
        "docs/ARCHITECTURE.md",
        "docs/MAINTENANCE.md",
        "Re-run `options-put-call-report setup-email`",
        "RESEND_API_KEY",
        "RESEND_API_KEY_FILE",
        "Resend API keys belong in `RESEND_API_KEY`, `RESEND_API_KEY_FILE`, or the system keyring",
        "Use the system keyring on desktop machines and environment variables or secret files for headless servers, containers, and CI",
        "stage=send",
    ]:
        assert text in combined

    assert "Resend API keys belong in `RESEND_API_KEY`, `RESEND_API_KEY_FILE`, or the system keyring" in _read("AGENTS.md")
    assert "RESEND_API_KEY" in _read("assistant-pack/README.md")
    assert "RESEND_API_KEY_FILE" in _read("assistant-pack/README.md")

    assistant_pack_expectations = {
        "assistant-pack/README.md": [
            "Resend API keys",
            "RESEND_API_KEY",
            "RESEND_API_KEY_FILE",
            "system keyring",
            "desktop",
            "headless servers, containers, and CI",
            "Never paste secrets into chat",
            "never commit keys",
            "stage=send",
            "HTTP status",
        ],
        "assistant-pack/prompts/options-report-agent.md": [
            "Resend API keys",
            "RESEND_API_KEY",
            "RESEND_API_KEY_FILE",
            "system keyring",
            "desktop",
            "headless/CI",
            "Never ask users to paste Resend API keys into chat",
            "Never commit Resend API keys",
            "stage=send",
            "HTTP status",
        ],
        "assistant-pack/claude/options-put-call-reporter/SKILL.md": [
            "Resend API keys",
            "RESEND_API_KEY",
            "RESEND_API_KEY_FILE",
            "system keyring",
            "desktop machines",
            "headless servers, containers, and CI",
            "Never ask users to paste Resend API keys into chat",
            "Never commit Resend API keys",
            "stage=send",
            "HTTP status",
        ],
    }
    for path, expected_texts in assistant_pack_expectations.items():
        content = _read(path)
        for text in expected_texts:
            assert text in content, f"{path} missing {text}"

    for native_file in [
        "AGENTS.md",
        "CLAUDE.md",
        "GEMINI.md",
        ".github/copilot-instructions.md",
        ".github/instructions/options-reporter.instructions.md",
    ]:
        content = _read(native_file)
        for text in ["config/symbols.json", "archive/YYYY-MM-DD", "data/history.sqlite3", "pytest -q", "python -m build", "Barchart"]:
            assert text in content, f"{native_file} missing {text}"
        for text in [
            "Resend API keys",
            "RESEND_API_KEY",
            "RESEND_API_KEY_FILE",
            "system keyring",
            "Never ask users to paste Resend API keys into chat",
            "stage=send",
            "HTTP status",
        ]:
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
