#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENV_DIR = ROOT / ".venv"
MIN_PYTHON = (3, 11)


class SetupStepError(Exception):
    def __init__(self, display: str, detail: str) -> None:
        super().__init__(display)
        self.display = display
        self.detail = detail


def _run(command: list[str], display: str) -> None:
    print(f"$ {display}", flush=True)
    try:
        subprocess.run(command, cwd=ROOT, check=True)
    except (OSError, subprocess.CalledProcessError) as error:
        raise SetupStepError(display, _error_detail(error)) from error


def _error_detail(error: BaseException) -> str:
    if isinstance(error, subprocess.CalledProcessError):
        details = [
            str(output).strip()
            for output in (error.stderr, error.stdout)
            if output is not None and str(output).strip()
        ]
        if details:
            return "\n".join(details)
        return ""
    return str(error)


def _venv_python() -> Path:
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def _format_version(version: tuple[int, int, int]) -> str:
    return ".".join(str(part) for part in version)


def _probe_python_version(python: Path) -> tuple[int, int, int] | None:
    if not python.exists():
        return None
    try:
        result = subprocess.run(
            [
                str(python),
                "-c",
                "import sys; print('.'.join(str(part) for part in sys.version_info[:3]))",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    parts = result.stdout.strip().split(".")
    if len(parts) < 2:
        return None
    try:
        major = int(parts[0])
        minor = int(parts[1])
        micro = int(parts[2]) if len(parts) > 2 else 0
    except ValueError:
        return None
    return major, minor, micro


def _existing_venv_error(python: Path) -> str | None:
    version = _probe_python_version(python)
    if version is None:
        return f"Existing .venv is not usable because {python} does not exist or cannot run."
    if version < MIN_PYTHON:
        return f"Existing .venv is not usable because it uses Python {_format_version(version)}."
    try:
        subprocess.run(
            [str(python), "-m", "pip", "--version"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return f"Existing .venv is not usable because pip is missing or broken in {python}."
    return None


def main() -> int:
    if sys.version_info < MIN_PYTHON:
        print("Requires Python 3.11 or newer. Re-run with python3.11 or python3.12.", file=sys.stderr)
        return 2

    print(f"Setting up local checkout at {ROOT}", flush=True)
    if not VENV_DIR.exists():
        print("$ python -m venv --symlinks .venv", flush=True)
        try:
            venv.create(VENV_DIR, with_pip=True, symlinks=True)
        except (OSError, subprocess.CalledProcessError) as error:
            print(f"Setup failed while creating .venv: {_error_detail(error)}", file=sys.stderr)
            print("Fix the error above, then rerun this script.", file=sys.stderr)
            return 1
    else:
        print("Using existing .venv", flush=True)
        existing_error = _existing_venv_error(_venv_python())
        if existing_error is not None:
            print(existing_error, file=sys.stderr)
            print("Remove .venv and rerun with Python 3.11 or newer.", file=sys.stderr)
            return 2

    python = str(_venv_python())
    try:
        _run([python, "-m", "pip", "install", "--upgrade", "pip"], "python -m pip install --upgrade pip")
        _run([python, "-m", "pip", "install", "-e", ".[dev]"], 'python -m pip install -e ".[dev]"')
        _run([python, "-m", "playwright", "install", "chromium"], "python -m playwright install chromium")
    except SetupStepError as error:
        print(f"Setup failed while running: {error.display}", file=sys.stderr)
        if error.detail:
            print(error.detail, file=sys.stderr)
        print("Fix the error above, then rerun this script.", file=sys.stderr)
        return 1

    if sys.platform == "win32":
        run_command = r".\.venv\Scripts\options-put-call-report.exe run --no-email"
        activate_command = r".\.venv\Scripts\Activate.ps1"
    else:
        run_command = "./.venv/bin/options-put-call-report run --no-email"
        activate_command = "source .venv/bin/activate"
    print("\nSetup complete. Run a report with:", flush=True)
    print(run_command, flush=True)
    print("\nOr activate the venv and run:", flush=True)
    print(activate_command, flush=True)
    print("options-put-call-report run --no-email", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
