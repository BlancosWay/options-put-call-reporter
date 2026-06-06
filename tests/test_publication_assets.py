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
