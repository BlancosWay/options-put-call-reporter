from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from reporter.models import AppConfig, SymbolConfig, Thresholds


class ConfigError(ValueError):
    pass


def _require_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ConfigError(f"Config value '{key}' must be a non-empty string")
    return value


def _require_int(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int):
        raise ConfigError(f"Config value '{key}' must be an integer")
    return value


def _thresholds(data: dict[str, Any]) -> Thresholds:
    raw = data.get("thresholds")
    if not isinstance(raw, dict):
        raise ConfigError("Config value 'thresholds' must be an object")
    values: dict[str, float | int] = {}
    for key in Thresholds.__dataclass_fields__:
        value = raw.get(key)
        if not isinstance(value, (int, float)):
            raise ConfigError(f"Threshold '{key}' must be numeric")
        values[key] = int(value) if key == "min_total_volume_for_commentary" else float(value)
    return Thresholds(**values)


def _is_barchart_put_call_url(url: str) -> bool:
    parsed = urlparse(url)
    hostname = parsed.hostname
    if hostname is None:
        return False
    hostname = hostname.lower().rstrip(".")
    if hostname != "barchart.com" and not hostname.endswith(".barchart.com"):
        return False
    return parsed.path.rstrip("/").endswith("/put-call-ratios")


def _symbols(data: dict[str, Any]) -> list[SymbolConfig]:
    raw_symbols = data.get("symbols")
    if not isinstance(raw_symbols, list) or not raw_symbols:
        raise ConfigError("Config must include at least one symbol")
    symbols: list[SymbolConfig] = []
    seen: set[str] = set()
    for raw in raw_symbols:
        if not isinstance(raw, dict):
            raise ConfigError("Each symbol entry must be an object")
        symbol = _require_string(raw, "symbol").upper()
        url = _require_string(raw, "url")
        if not _is_barchart_put_call_url(url):
            raise ConfigError(f"Symbol {symbol} must use a Barchart put-call-ratios URL")
        if symbol in seen:
            raise ConfigError(f"Duplicate symbol '{symbol}'")
        seen.add(symbol)
        symbols.append(SymbolConfig(symbol=symbol, url=url))
    return symbols


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ConfigError("Config root must be an object")
    return AppConfig(
        archive_dir=Path(_require_string(data, "archive_dir")),
        database_path=Path(_require_string(data, "database_path")),
        report_time_local=_require_string(data, "report_time_local"),
        keychain_service=_require_string(data, "keychain_service"),
        gmail_smtp_host=_require_string(data, "gmail_smtp_host"),
        gmail_smtp_port=_require_int(data, "gmail_smtp_port"),
        thresholds=_thresholds(data),
        symbols=_symbols(data),
    )
