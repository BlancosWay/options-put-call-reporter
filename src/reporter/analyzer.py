from __future__ import annotations

from collections import defaultdict

from reporter.models import ExpirationRow, MonthlySignal, Signal, Snapshot, SymbolAnalysis, Thresholds


def classify_signal(volume_ratio: float, oi_ratio: float, thresholds: Thresholds) -> Signal:
    if volume_ratio <= thresholds.strong_bullish_volume_max and oi_ratio <= thresholds.strong_bullish_oi_max:
        return Signal.STRONG_BULLISH
    if volume_ratio < thresholds.bullish_volume_max and oi_ratio < thresholds.bullish_oi_max:
        return Signal.BULLISH
    if volume_ratio > thresholds.bearish_volume_min or oi_ratio > thresholds.bearish_oi_min:
        return Signal.BEARISH_HEDGING
    if volume_ratio < thresholds.bullish_volume_max and thresholds.mixed_oi_min <= oi_ratio <= thresholds.mixed_oi_max:
        return Signal.MIXED_CAUTION
    if thresholds.neutral_volume_min <= volume_ratio <= thresholds.neutral_volume_max and oi_ratio < thresholds.neutral_oi_max:
        return Signal.NEUTRAL
    return Signal.MIXED


def select_monthly_rows(rows: list[ExpirationRow], months: int = 12) -> list[ExpirationRow]:
    grouped: dict[str, list[ExpirationRow]] = defaultdict(list)
    for item in rows:
        grouped[item.expiration_date.strftime("%Y-%m")].append(item)

    selected: list[ExpirationRow] = []
    for month in sorted(grouped):
        candidates = grouped[month]
        monthly = [item for item in candidates if item.is_monthly]
        pool = monthly if monthly else candidates
        selected.append(max(pool, key=lambda item: (item.total_volume, item.total_open_interest)))
        if len(selected) == months:
            break
    return selected


def _count_signals(signals: list[MonthlySignal]) -> tuple[int, int, int, int]:
    bullish = sum(1 for item in signals if item.signal in {Signal.STRONG_BULLISH, Signal.BULLISH})
    neutral = sum(1 for item in signals if item.signal is Signal.NEUTRAL)
    mixed = sum(1 for item in signals if item.signal in {Signal.MIXED, Signal.MIXED_CAUTION})
    bearish = sum(1 for item in signals if item.signal is Signal.BEARISH_HEDGING)
    return bullish, neutral, mixed, bearish


def _commentary(symbol: str, signals: list[MonthlySignal]) -> str:
    bullish, neutral, mixed, bearish = _count_signals(signals)
    if not signals:
        return f"{symbol}: no expiration rows were available for analysis."
    counts = {
        "bullish overall": bullish,
        "neutral overall": neutral,
        "mixed overall": mixed,
        "bearish or hedging-heavy overall": bearish,
    }
    highest_count = max(counts.values())
    leading_tones = [tone for tone, count in counts.items() if count == highest_count]
    tone = leading_tones[0] if len(leading_tones) == 1 else "mixed overall"
    return f"{symbol}: {tone} with {bullish} bullish, {neutral} neutral, {mixed} mixed, and {bearish} bearish monthly signals."


def analyze_snapshot(snapshot: Snapshot, thresholds: Thresholds, months: int = 12) -> SymbolAnalysis:
    monthly_rows = select_monthly_rows(snapshot.rows, months=months)
    monthly_signals = [
        MonthlySignal(
            month=row.expiration_date.strftime("%Y-%m"),
            expiration_label=row.expiration_label,
            put_call_volume_ratio=row.put_call_volume_ratio,
            put_call_open_interest_ratio=row.put_call_open_interest_ratio,
            total_volume=row.total_volume,
            total_open_interest=row.total_open_interest,
            signal=classify_signal(row.put_call_volume_ratio, row.put_call_open_interest_ratio, thresholds),
        )
        for row in monthly_rows
    ]
    return SymbolAnalysis(
        symbol=snapshot.symbol,
        captured_at=snapshot.captured_at,
        metrics=snapshot.metrics,
        monthly_signals=monthly_signals,
        commentary=_commentary(snapshot.symbol, monthly_signals),
    )
