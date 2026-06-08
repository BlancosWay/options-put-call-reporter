from pathlib import Path
import stat


ROOT = Path(__file__).resolve().parents[1]


def test_run_daily_script_runs_email_report_and_prepares_log_directory() -> None:
    script = ROOT / "scripts" / "run_daily.sh"

    content = script.read_text(encoding="utf-8")

    assert script.stat().st_mode & stat.S_IXUSR
    assert 'mkdir -p "$PROJECT_DIR/archive"' in content
    assert 'source "$PROJECT_DIR/.venv/bin/activate"' in content
    assert 'options-put-call-report run --send-email >> "$PROJECT_DIR/archive/runner.log" 2>&1' in content


def test_launch_agent_installer_writes_expected_schedule_and_logs() -> None:
    script = ROOT / "scripts" / "install_launch_agent.sh"

    content = script.read_text(encoding="utf-8")

    assert script.stat().st_mode & stat.S_IXUSR
    assert "com.sri.options-put-call-reporter" in content
    assert "<key>Hour</key>" in content
    assert "<integer>14</integer>" in content
    assert "<key>Minute</key>" in content
    assert "<integer>30</integer>" in content
    assert "archive/launchd.out.log" in content
    assert "archive/launchd.err.log" in content
    assert "launchctl load" in content


def test_setup_local_script_bootstraps_checkout_environment() -> None:
    script = ROOT / "scripts" / "setup_local.py"

    content = script.read_text(encoding="utf-8")

    assert script.stat().st_mode & stat.S_IXUSR
    assert "Requires Python 3.11 or newer" in content
    assert "python -m venv --symlinks .venv" in content
    assert "venv.create" in content
    assert "python -m pip install --upgrade pip" in content
    assert 'python -m pip install -e ".[dev]"' in content
    assert "python -m playwright install chromium" in content
    assert "source .venv/bin/activate" in content
    assert "options-put-call-report run --no-email" in content


def test_readme_documents_scheduler_install_status_and_logs() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "options-put-call-report run --send-email" in readme
    assert "./scripts/install_launch_agent.sh" in readme
    assert "launchctl list | grep com.sri.options-put-call-reporter" in readme
    assert "archive/runner.log" in readme
    assert "archive/launchd.out.log" in readme
    assert "archive/launchd.err.log" in readme
