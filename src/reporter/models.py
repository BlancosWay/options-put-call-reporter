from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from pathlib import Path


class Signal(str, Enum):
    STRONG_BULLISH = "Strong bullish"
    BULLISH = "Bullish"
    NEUTRAL = "Neutral"
    MIXED = "Mixed"
    MIXED_CAUTION = "Mixed / caution"
    BEARISH_HEDGING = "Bearish / hedging-heavy"
    FAILED = "Failed"


@dataclass(frozen=True)
class Thresholds:
    strong_bullish_volume_max: float
    strong_bullish_oi_max: float
    bullish_volume_max: float
    bullish_oi_max: float
    bearish_volume_min: float
    bearish_oi_min: float
    mixed_oi_min: float
    mixed_oi_max: float
    neutral_volume_min: float
    neutral_volume_max: float
    neutral_oi_max: float
    min_total_volume_for_commentary: int


@dataclass(frozen=True)
class SymbolConfig:
    symbol: str
    url: str


@dataclass(frozen=True)
class AppConfig:
    archive_dir: Path
    database_path: Path
    report_time_local: str
    keychain_service: str
    resend_api_url: str
    thresholds: Thresholds
    symbols: list[SymbolConfig]


@dataclass(frozen=True)
class EmailConfig:
    from_email: str
    to_email: str


@dataclass(frozen=True)
class TopMetrics:
    latest_earnings: str | None
    implied_volatility: float | None
    historic_volatility: float | None
    iv_rank: float | None
    iv_percentile: float | None


@dataclass(frozen=True)
class ExpirationRow:
    expiration_label: str
    expiration_date: date
    dte: int
    put_volume: int
    call_volume: int
    total_volume: int
    put_call_volume_ratio: float
    put_open_interest: int
    call_open_interest: int
    total_open_interest: int
    put_call_open_interest_ratio: float
    implied_volatility: float | None
    is_monthly: bool


@dataclass(frozen=True)
class DataSource:
    name: str
    url: str
    is_fallback: bool = False
    note: str | None = None


def default_barchart_source() -> DataSource:
    return DataSource(name="Barchart", url="https://www.barchart.com", is_fallback=False)


@dataclass(frozen=True)
class Snapshot:
    symbol: str
    url: str
    captured_at: datetime
    metrics: TopMetrics
    rows: list[ExpirationRow]
    data_source: DataSource = field(default_factory=default_barchart_source)


@dataclass(frozen=True)
class MonthlySignal:
    month: str
    expiration_label: str
    put_call_volume_ratio: float
    put_call_open_interest_ratio: float
    total_volume: int
    total_open_interest: int
    signal: Signal


@dataclass(frozen=True)
class SymbolAnalysis:
    symbol: str
    captured_at: datetime
    metrics: TopMetrics
    monthly_signals: list[MonthlySignal]
    commentary: str


@dataclass(frozen=True)
class DriftItem:
    period: str
    summary: str
    signal_flips: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SymbolReport:
    symbol: str
    snapshot: Snapshot | None
    analysis: SymbolAnalysis | None
    drift: list[DriftItem]
    error: str | None = None


@dataclass(frozen=True)
class ReportBundle:
    generated_at: datetime
    symbol_reports: list[SymbolReport]
    archive_dir: Path
    markdown_path: Path
    html_path: Path
