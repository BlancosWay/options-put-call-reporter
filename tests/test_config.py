import json
from pathlib import Path

import pytest

from reporter.config import ConfigError, load_config


def write_config(path: Path, overrides: dict | None = None) -> None:
    config = {
        "archive_dir": "archive",
        "database_path": "data/history.sqlite3",
        "report_time_local": "14:30",
        "keychain_service": "options-put-call-reporter:gmail-app-password",
        "gmail_smtp_host": "smtp.gmail.com",
        "gmail_smtp_port": 587,
        "thresholds": {
            "strong_bullish_volume_max": 0.35,
            "strong_bullish_oi_max": 0.7,
            "bullish_volume_max": 0.7,
            "bullish_oi_max": 0.9,
            "bearish_volume_min": 1.1,
            "bearish_oi_min": 1.25,
            "mixed_oi_min": 1.0,
            "mixed_oi_max": 1.25,
            "neutral_volume_min": 0.7,
            "neutral_volume_max": 1.1,
            "neutral_oi_max": 1.1,
            "min_total_volume_for_commentary": 1000
        },
        "symbols": [
            {"symbol": "NOW", "url": "https://www.barchart.com/stocks/quotes/now/put-call-ratios"}
        ]
    }
    if overrides:
        config.update(overrides)
    path.write_text(json.dumps(config), encoding="utf-8")


def test_load_config_returns_typed_values(tmp_path: Path) -> None:
    config_path = tmp_path / "symbols.json"
    write_config(config_path)

    config = load_config(config_path)

    assert config.archive_dir == Path("archive")
    assert config.database_path == Path("data/history.sqlite3")
    assert config.report_time_local == "14:30"
    assert config.symbols[0].symbol == "NOW"
    assert config.symbols[0].url == "https://www.barchart.com/stocks/quotes/now/put-call-ratios"
    assert config.thresholds.strong_bullish_volume_max == 0.35


def test_load_config_rejects_missing_symbols(tmp_path: Path) -> None:
    config_path = tmp_path / "symbols.json"
    write_config(config_path, {"symbols": []})

    with pytest.raises(ConfigError, match="at least one symbol"):
        load_config(config_path)


def test_load_config_rejects_non_barchart_host_with_barchart_substring(tmp_path: Path) -> None:
    config_path = tmp_path / "symbols.json"
    write_config(
        config_path,
        {
            "symbols": [
                {
                    "symbol": "NOW",
                    "url": "https://evilbarchart.com/stocks/quotes/now/put-call-ratios",
                }
            ]
        },
    )

    with pytest.raises(ConfigError, match="Barchart"):
        load_config(config_path)


def test_load_config_rejects_non_barchart_url(tmp_path: Path) -> None:
    config_path = tmp_path / "symbols.json"
    write_config(config_path, {"symbols": [{"symbol": "NOW", "url": "https://example.com/now"}]})

    with pytest.raises(ConfigError, match="Barchart"):
        load_config(config_path)
