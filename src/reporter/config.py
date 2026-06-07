from __future__ import annotations

import json
import re
from importlib import resources
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from reporter.models import AppConfig, SymbolConfig, Thresholds


class ConfigError(ValueError):
    pass


SYMBOL_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9.-]*$")
DEFAULT_CONFIG_PATH = Path("config/symbols.json")


def _require_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ConfigError(f"Config value '{key}' must be a non-empty string")
    return value


def _require_https_url(data: dict[str, Any], key: str) -> str:
    value = _require_string(data, key)
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname is None:
        raise ConfigError(f"Config value '{key}' must be an HTTPS URL")
    return value


def _thresholds(data: dict[str, Any]) -> Thresholds:
    raw = data.get("thresholds")
    if not isinstance(raw, dict):
        raise ConfigError("Config value 'thresholds' must be an object")
    values: dict[str, float | int] = {}
    for key in Thresholds.__dataclass_fields__:
        value = raw.get(key)
        if key == "min_total_volume_for_commentary":
            if not isinstance(value, int) or isinstance(value, bool):
                raise ConfigError(f"Threshold '{key}' must be an integer")
            values[key] = value
            continue
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ConfigError(f"Threshold '{key}' must be numeric")
        values[key] = float(value)
    return Thresholds(**values)


def _is_barchart_put_call_url(url: str, symbol: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False
    hostname = parsed.hostname
    if hostname is None:
        return False
    hostname = hostname.lower().rstrip(".")
    if hostname != "barchart.com" and not hostname.endswith(".barchart.com"):
        return False
    expected_path = f"/stocks/quotes/{symbol.lower()}/put-call-ratios"
    return parsed.path.rstrip("/").lower() == expected_path


def _symbol_url(symbol: str) -> str:
    return f"https://www.barchart.com/stocks/quotes/{symbol.lower()}/put-call-ratios"


def parse_symbol_tokens(values: list[str]) -> list[str]:
    symbols: list[str] = []
    seen: set[str] = set()
    for value in values:
        body = value.split("#", 1)[0]
        for raw_token in re.split(r"[\s,]+", body):
            token = raw_token.strip().upper()
            if not token:
                continue
            if not SYMBOL_PATTERN.fullmatch(token):
                raise ConfigError(f"Invalid symbol '{raw_token.strip()}'")
            if token in seen:
                continue
            seen.add(token)
            symbols.append(token)
    if not symbols:
        raise ConfigError("At least one symbol is required")
    return symbols


def load_symbol_file(path: str | Path) -> list[str]:
    symbol_path = Path(path)
    try:
        content = symbol_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Could not read symbols file {symbol_path}: {exc.strerror}") from exc
    except UnicodeDecodeError as exc:
        raise ConfigError(f"Could not read symbols file {symbol_path}: file must be UTF-8 text") from exc
    return parse_symbol_tokens(content.splitlines())


def symbols_from_names(names: list[str]) -> list[SymbolConfig]:
    symbols = parse_symbol_tokens(names)
    return [SymbolConfig(symbol=symbol, url=_symbol_url(symbol)) for symbol in symbols]


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
        if not _is_barchart_put_call_url(url, symbol):
            raise ConfigError(
                f"Symbol {symbol} must use a Barchart URL matching "
                f"/stocks/quotes/{symbol.lower()}/put-call-ratios"
            )
        if symbol in seen:
            raise ConfigError(f"Duplicate symbol '{symbol}'")
        seen.add(symbol)
        symbols.append(SymbolConfig(symbol=symbol, url=url))
    return symbols


def _config_from_data(data: Any) -> AppConfig:
    if not isinstance(data, dict):
        raise ConfigError("Config root must be an object")
    return AppConfig(
        archive_dir=Path(_require_string(data, "archive_dir")),
        database_path=Path(_require_string(data, "database_path")),
        report_time_local=_require_string(data, "report_time_local"),
        keychain_service=_require_string(data, "keychain_service"),
        resend_api_url=_require_https_url(data, "resend_api_url"),
        thresholds=_thresholds(data),
        symbols=_symbols(data),
    )


def _load_default_config_data() -> Any:
    return json.loads(resources.files("reporter").joinpath("default_symbols.json").read_text(encoding="utf-8"))


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    if config_path == DEFAULT_CONFIG_PATH and not config_path.exists():
        return _config_from_data(_load_default_config_data())
    return _config_from_data(json.loads(config_path.read_text(encoding="utf-8")))
