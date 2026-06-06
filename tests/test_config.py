import json
from pathlib import Path

import pytest

from reporter import config
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


def write_config_with_threshold(path: Path, key: str, value: object) -> None:
    write_config(path)
    config = json.loads(path.read_text(encoding="utf-8"))
    config["thresholds"][key] = value
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


def test_load_config_rejects_symbol_that_does_not_match_barchart_url(tmp_path: Path) -> None:
    config_path = tmp_path / "symbols.json"
    write_config(
        config_path,
        {
            "symbols": [
                {
                    "symbol": "NOW",
                    "url": "https://www.barchart.com/stocks/quotes/msft/put-call-ratios",
                }
            ]
        },
    )

    with pytest.raises(ConfigError, match="symbol|URL"):
        load_config(config_path)


def test_load_config_rejects_non_barchart_url(tmp_path: Path) -> None:
    config_path = tmp_path / "symbols.json"
    write_config(config_path, {"symbols": [{"symbol": "NOW", "url": "https://example.com/now"}]})

    with pytest.raises(ConfigError, match="Barchart"):
        load_config(config_path)


def test_load_config_rejects_ftp_barchart_url(tmp_path: Path) -> None:
    config_path = tmp_path / "symbols.json"
    write_config(
        config_path,
        {
            "symbols": [
                {
                    "symbol": "NOW",
                    "url": "ftp://www.barchart.com/stocks/quotes/now/put-call-ratios",
                }
            ]
        },
    )

    with pytest.raises(ConfigError, match="Barchart"):
        load_config(config_path)


def test_load_config_rejects_scheme_relative_barchart_url(tmp_path: Path) -> None:
    config_path = tmp_path / "symbols.json"
    write_config(
        config_path,
        {
            "symbols": [
                {
                    "symbol": "NOW",
                    "url": "//www.barchart.com/stocks/quotes/now/put-call-ratios",
                }
            ]
        },
    )

    with pytest.raises(ConfigError, match="Barchart"):
        load_config(config_path)


def test_load_config_uppercases_lowercase_symbol(tmp_path: Path) -> None:
    config_path = tmp_path / "symbols.json"
    write_config(
        config_path,
        {
            "symbols": [
                {
                    "symbol": "now",
                    "url": "https://www.barchart.com/stocks/quotes/now/put-call-ratios",
                }
            ]
        },
    )

    config = load_config(config_path)

    assert config.symbols[0].symbol == "NOW"


def test_load_config_rejects_duplicate_symbols_after_uppercase(tmp_path: Path) -> None:
    config_path = tmp_path / "symbols.json"
    write_config(
        config_path,
        {
            "symbols": [
                {
                    "symbol": "now",
                    "url": "https://www.barchart.com/stocks/quotes/now/put-call-ratios",
                },
                {
                    "symbol": "NOW",
                    "url": "https://www.barchart.com/stocks/quotes/now/put-call-ratios",
                },
            ]
        },
    )

    with pytest.raises(ConfigError, match="Duplicate"):
        load_config(config_path)


def test_load_config_rejects_boolean_gmail_smtp_port(tmp_path: Path) -> None:
    config_path = tmp_path / "symbols.json"
    write_config(config_path, {"gmail_smtp_port": True})

    with pytest.raises(ConfigError, match="integer"):
        load_config(config_path)


def test_load_config_rejects_boolean_float_threshold(tmp_path: Path) -> None:
    config_path = tmp_path / "symbols.json"
    write_config_with_threshold(config_path, "strong_bullish_volume_max", True)

    with pytest.raises(ConfigError, match="numeric"):
        load_config(config_path)


def test_load_config_rejects_float_min_total_volume_for_commentary(tmp_path: Path) -> None:
    config_path = tmp_path / "symbols.json"
    write_config_with_threshold(config_path, "min_total_volume_for_commentary", 1000.9)

    with pytest.raises(ConfigError, match="integer"):
        load_config(config_path)


def test_parse_symbol_tokens_accepts_spaces_commas_case_and_comments() -> None:
    assert config.parse_symbol_tokens(["meta", "MSFT, now", "# comment", "AAOI # comment", "lite goog"]) == [
        "META",
        "MSFT",
        "NOW",
        "AAOI",
        "LITE",
        "GOOG",
    ]


def test_parse_symbol_tokens_dedupes_duplicates_after_uppercase() -> None:
    assert config.parse_symbol_tokens(["now", "MSFT", "NOW", "msft"]) == ["NOW", "MSFT"]


def test_parse_symbol_tokens_rejects_invalid_symbols() -> None:
    with pytest.raises(ConfigError, match="Invalid symbol"):
        config.parse_symbol_tokens(["META", "BAD/SYMBOL"])


def test_load_symbol_file_accepts_plain_text_symbols_commas_spaces_and_comments(tmp_path: Path) -> None:
    path = tmp_path / "watchlist.txt"
    path.write_text(
        """
        # mega-cap watchlist
        meta, msft, META
        now aaoi # growth names

        lite
        now
        """,
        encoding="utf-8",
    )

    assert config.load_symbol_file(path) == ["META", "MSFT", "NOW", "AAOI", "LITE"]


def test_symbols_from_names_builds_standard_barchart_urls() -> None:
    symbols = config.symbols_from_names(["META", "BRK.B"])

    assert symbols[0].symbol == "META"
    assert symbols[0].url == "https://www.barchart.com/stocks/quotes/meta/put-call-ratios"
    assert symbols[1].symbol == "BRK.B"
    assert symbols[1].url == "https://www.barchart.com/stocks/quotes/brk.b/put-call-ratios"
