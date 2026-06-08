from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]


def _load_setup_local() -> ModuleType:
    script = ROOT / "scripts" / "setup_local.py"
    spec = importlib.util.spec_from_file_location("setup_local", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_setup_local_rejects_existing_venv_without_python(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    setup_local = _load_setup_local()
    venv_dir = tmp_path / ".venv"
    venv_dir.mkdir()

    monkeypatch.setattr(setup_local, "ROOT", tmp_path)
    monkeypatch.setattr(setup_local, "VENV_DIR", venv_dir)

    def fail_run(command: list[str], display: str) -> None:
        raise AssertionError(f"setup command should not run for a broken venv: {display}")

    monkeypatch.setattr(setup_local, "_run", fail_run)

    assert setup_local.main() == 2
    captured = capsys.readouterr()
    assert "Existing .venv is not usable" in captured.err
    assert "Remove .venv and rerun with Python 3.11 or newer." in captured.err


def test_setup_local_rejects_existing_venv_with_broken_pip(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    setup_local = _load_setup_local()
    venv_dir = tmp_path / ".venv"
    venv_dir.mkdir()

    monkeypatch.setattr(setup_local, "ROOT", tmp_path)
    monkeypatch.setattr(setup_local, "VENV_DIR", venv_dir)
    monkeypatch.setattr(setup_local, "_probe_python_version", lambda python: (3, 11, 9))

    def fail_pip_check(command, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=command)

    monkeypatch.setattr(setup_local.subprocess, "run", fail_pip_check)

    def fail_run(command: list[str], display: str) -> None:
        raise AssertionError(f"setup command should not run for a broken venv: {display}")

    monkeypatch.setattr(setup_local, "_run", fail_run)

    assert setup_local.main() == 2
    captured = capsys.readouterr()
    assert "pip is missing or broken" in captured.err
    assert "Remove .venv and rerun with Python 3.11 or newer." in captured.err


def test_setup_local_reports_venv_creation_failure_without_traceback(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    setup_local = _load_setup_local()

    monkeypatch.setattr(setup_local, "ROOT", tmp_path)
    monkeypatch.setattr(setup_local, "VENV_DIR", tmp_path / ".venv")

    def fail_create(*args, **kwargs) -> None:
        raise OSError("disk is full")

    monkeypatch.setattr(setup_local.venv, "create", fail_create)

    assert setup_local.main() == 1
    captured = capsys.readouterr()
    assert "Setup failed while creating .venv: disk is full" in captured.err
    assert "Fix the error above, then rerun this script." in captured.err
    assert "Traceback" not in captured.err


def test_setup_local_reports_venv_ensurepip_failure_without_traceback(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    setup_local = _load_setup_local()

    monkeypatch.setattr(setup_local, "ROOT", tmp_path)
    monkeypatch.setattr(setup_local, "VENV_DIR", tmp_path / ".venv")

    def fail_create(*args, **kwargs) -> None:
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=["python", "-m", "venv", ".venv"],
            stderr="ensurepip failed",
        )

    monkeypatch.setattr(setup_local.venv, "create", fail_create)

    assert setup_local.main() == 1
    captured = capsys.readouterr()
    assert "Setup failed while creating .venv" in captured.err
    assert "ensurepip failed" in captured.err
    assert "Fix the error above, then rerun this script." in captured.err
    assert "Traceback" not in captured.err


def test_setup_local_reports_install_failure_without_traceback(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    setup_local = _load_setup_local()
    venv_dir = tmp_path / ".venv"
    venv_dir.mkdir()

    monkeypatch.setattr(setup_local, "ROOT", tmp_path)
    monkeypatch.setattr(setup_local, "VENV_DIR", venv_dir)
    monkeypatch.setattr(setup_local, "_existing_venv_error", lambda python: None)

    def fail_run(command, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=command)

    monkeypatch.setattr(setup_local.subprocess, "run", fail_run)

    assert setup_local.main() == 1
    captured = capsys.readouterr()
    assert "Setup failed while running: python -m pip install --upgrade pip" in captured.err
    assert "Fix the error above, then rerun this script." in captured.err
    assert "returned non-zero exit status" not in captured.err
    assert "Traceback" not in captured.err


def test_setup_local_reports_install_spawn_error_detail(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    setup_local = _load_setup_local()
    venv_dir = tmp_path / ".venv"
    venv_dir.mkdir()

    monkeypatch.setattr(setup_local, "ROOT", tmp_path)
    monkeypatch.setattr(setup_local, "VENV_DIR", venv_dir)
    monkeypatch.setattr(setup_local, "_existing_venv_error", lambda python: None)

    def fail_run(command, **kwargs):
        raise OSError("permission denied")

    monkeypatch.setattr(setup_local.subprocess, "run", fail_run)

    assert setup_local.main() == 1
    captured = capsys.readouterr()
    assert "Setup failed while running: python -m pip install --upgrade pip" in captured.err
    assert "permission denied" in captured.err
    assert "Traceback" not in captured.err


def test_setup_local_runs_success_steps_in_order(tmp_path: Path, monkeypatch, capsys) -> None:
    setup_local = _load_setup_local()
    calls: list[str] = []

    monkeypatch.setattr(setup_local, "ROOT", tmp_path)
    monkeypatch.setattr(setup_local, "VENV_DIR", tmp_path / ".venv")

    def create_venv(path: Path, *, with_pip: bool, symlinks: bool) -> None:
        calls.append(f"create:{path.name}:{with_pip}:{symlinks}")

    def run_step(command: list[str], display: str) -> None:
        calls.append(display)

    monkeypatch.setattr(setup_local.venv, "create", create_venv)
    monkeypatch.setattr(setup_local, "_run", run_step)

    assert setup_local.main() == 0
    assert calls == [
        "create:.venv:True:True",
        "python -m pip install --upgrade pip",
        'python -m pip install -e ".[dev]"',
        "python -m playwright install chromium",
    ]
    captured = capsys.readouterr()
    assert "./.venv/bin/options-put-call-report run --no-email" in captured.out
    assert "source .venv/bin/activate" in captured.out
