from datetime import datetime

from reporter.drift import build_drift
from reporter.models import DriftItem, MonthlySignal, Signal, SymbolAnalysis, Thresholds, TopMetrics


def thresholds() -> Thresholds:
    return Thresholds(0.35, 0.7, 0.7, 0.9, 1.1, 1.25, 1.0, 1.25, 0.7, 1.1, 1.1, 1000)


def analysis(symbol: str, month_signal: Signal, vol_ratio: float, oi_ratio: float) -> SymbolAnalysis:
    return SymbolAnalysis(
        symbol=symbol,
        captured_at=datetime(2026, 6, 30, 21, 30),
        metrics=TopMetrics("07/29/26", 31.0, 33.0, 60.0, 80.0),
        monthly_signals=[
            MonthlySignal("2026-06", "06/18/26 (m)", vol_ratio, oi_ratio, 10000, 20000, month_signal),
            MonthlySignal("2026-07", "07/17/26 (m)", 0.30, 0.50, 15000, 25000, Signal.STRONG_BULLISH),
        ],
        commentary="summary",
    )


def test_build_drift_reports_missing_prior() -> None:
    current = analysis("MSFT", Signal.BULLISH, 0.50, 0.80)

    drift = build_drift(current, {"previous_day": None}, thresholds())

    assert drift == [DriftItem(period="previous_day", summary="No previous_day snapshot is available yet.", signal_flips=[])]


def test_build_drift_reports_signal_flip_and_ratio_changes() -> None:
    current = analysis("MSFT", Signal.BEARISH_HEDGING, 1.20, 1.40)
    previous = analysis("MSFT", Signal.BULLISH, 0.50, 0.80)

    drift = build_drift(current, {"previous_day": previous}, thresholds())

    assert len(drift) == 1
    assert "bullish decreased" in drift[0].summary
    assert "bearish increased" in drift[0].summary
    assert "average put/call volume ratio increased" in drift[0].summary
    assert "average put/call open-interest ratio increased" in drift[0].summary
    assert "2026-06: Bullish -> Bearish / hedging-heavy" in drift[0].signal_flips


def test_build_drift_reports_no_current_monthly_signals() -> None:
    current = SymbolAnalysis(
        symbol="MSFT",
        captured_at=datetime(2026, 6, 30, 21, 30),
        metrics=TopMetrics("07/29/26", 31.0, 33.0, 60.0, 80.0),
        monthly_signals=[],
        commentary="summary",
    )
    previous = analysis("MSFT", Signal.BULLISH, 0.50, 0.80)

    drift = build_drift(current, {"previous_day": previous}, thresholds())

    assert len(drift) == 1
    assert drift[0].period == "previous_day"
    assert "No current monthly signals" in drift[0].summary
    assert drift[0].signal_flips == []


def test_build_drift_reports_no_prior_monthly_signals() -> None:
    current = analysis("MSFT", Signal.BULLISH, 0.50, 0.80)
    previous = SymbolAnalysis(
        symbol="MSFT",
        captured_at=datetime(2026, 6, 30, 21, 30),
        metrics=TopMetrics("07/29/26", 31.0, 33.0, 60.0, 80.0),
        monthly_signals=[],
        commentary="summary",
    )

    drift = build_drift(current, {"previous_day": previous}, thresholds())

    assert len(drift) == 1
    assert drift[0].period == "previous_day"
    assert "No prior monthly signals" in drift[0].summary
    assert drift[0].signal_flips == []
