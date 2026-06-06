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
        "pipx install git+https://github.com/srinadel/options-put-call-reporter.git",
        "pipx run --spec playwright playwright install chromium",
        "python -m playwright install chromium",
        "options-put-call-report run --no-email",
        "options-put-call-report run --no-email META MSFT NOW",
        "options-put-call-report setup-email",
        "launchd",
        "Not financial advice",
    ]:
        assert text in readme


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
