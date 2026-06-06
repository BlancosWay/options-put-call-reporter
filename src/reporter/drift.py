from __future__ import annotations

import math

from reporter.models import DriftItem, MonthlySignal, Signal, SymbolAnalysis, Thresholds


def _index(signals: list[MonthlySignal]) -> dict[str, MonthlySignal]:
    return {signal.month: signal for signal in signals}


def _bearish_count(signals: list[MonthlySignal]) -> int:
    return sum(1 for signal in signals if signal.signal is Signal.BEARISH_HEDGING)


def _bullish_count(signals: list[MonthlySignal]) -> int:
    return sum(1 for signal in signals if signal.signal in {Signal.STRONG_BULLISH, Signal.BULLISH})


def _average_volume_ratio(signals: list[MonthlySignal]) -> float:
    return sum(signal.put_call_volume_ratio for signal in signals) / max(1, len(signals))


def _average_oi_ratio(signals: list[MonthlySignal]) -> float:
    return sum(signal.put_call_open_interest_ratio for signal in signals) / max(1, len(signals))


def _direction(current: float, previous: float, label: str) -> str:
    if math.isinf(current) and current > 0 and math.isinf(previous) and previous > 0:
        return f"{label} remained extremely put-heavy"
    if math.isinf(current) and current > 0 and math.isfinite(previous):
        return f"{label} moved to an extremely put-heavy reading"
    if math.isfinite(current) and math.isinf(previous) and previous > 0:
        return f"{label} moved back from an extremely put-heavy reading"
    delta = current - previous
    if abs(delta) < 0.05:
        return f"{label} was mostly unchanged"
    direction = "increased" if delta > 0 else "decreased"
    return f"{label} {direction} by {delta:+.2f}"


def build_drift(
    current: SymbolAnalysis,
    priors: dict[str, SymbolAnalysis | None],
    thresholds: Thresholds,
) -> list[DriftItem]:
    items: list[DriftItem] = []
    for period, prior in priors.items():
        if prior is None:
            items.append(DriftItem(period=period, summary=f"No {period} snapshot is available yet."))
            continue

        if not current.monthly_signals:
            items.append(
                DriftItem(
                    period=period,
                    summary=f"No current monthly signals are available for {period} comparison.",
                )
            )
            continue
        if not prior.monthly_signals:
            items.append(
                DriftItem(
                    period=period,
                    summary=f"No prior monthly signals are available for {period} comparison.",
                )
            )
            continue

        current_by_month = _index(current.monthly_signals)
        prior_by_month = _index(prior.monthly_signals)
        flips: list[str] = []
        for month in sorted(current_by_month.keys() & prior_by_month.keys()):
            current_signal = current_by_month[month].signal
            prior_signal = prior_by_month[month].signal
            if current_signal is not prior_signal:
                flips.append(f"{month}: {prior_signal.value} -> {current_signal.value}")

        bullish_delta = _bullish_count(current.monthly_signals) - _bullish_count(prior.monthly_signals)
        bearish_delta = _bearish_count(current.monthly_signals) - _bearish_count(prior.monthly_signals)
        volume_text = _direction(
            _average_volume_ratio(current.monthly_signals),
            _average_volume_ratio(prior.monthly_signals),
            "average put/call volume ratio",
        )
        oi_text = _direction(
            _average_oi_ratio(current.monthly_signals),
            _average_oi_ratio(prior.monthly_signals),
            "average put/call open-interest ratio",
        )
        bullish_text = "bullish increased" if bullish_delta > 0 else "bullish decreased" if bullish_delta < 0 else "bullish count unchanged"
        bearish_text = "bearish increased" if bearish_delta > 0 else "bearish decreased" if bearish_delta < 0 else "bearish count unchanged"
        summary = f"{bullish_text}; {bearish_text}; {volume_text}; {oi_text}."
        items.append(DriftItem(period=period, summary=summary, signal_flips=flips))
    return items
