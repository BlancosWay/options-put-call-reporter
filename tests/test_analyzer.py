from datetime import date, datetime

from reporter.analyzer import analyze_snapshot, classify_signal, select_monthly_rows
from reporter.models import ExpirationRow, Signal, Snapshot, Thresholds, TopMetrics


def thresholds() -> Thresholds:
    return Thresholds(
        strong_bullish_volume_max=0.35,
        strong_bullish_oi_max=0.7,
        bullish_volume_max=0.7,
        bullish_oi_max=0.9,
        bearish_volume_min=1.1,
        bearish_oi_min=1.25,
        mixed_oi_min=1.0,
        mixed_oi_max=1.25,
        neutral_volume_min=0.7,
        neutral_volume_max=1.1,
        neutral_oi_max=1.1,
        min_total_volume_for_commentary=1000,
    )


def row(label: str, vol_ratio: float, oi_ratio: float, total_volume: int, is_monthly: bool = True) -> ExpirationRow:
    month, day, year = label[:2], label[3:5], label[6:8]
    return ExpirationRow(
        expiration_label=label,
        expiration_date=date(2000 + int(year), int(month), int(day)),
        dte=30,
        put_volume=int(total_volume * vol_ratio / 2),
        call_volume=max(1, int(total_volume / 2)),
        total_volume=total_volume,
        put_call_volume_ratio=vol_ratio,
        put_open_interest=int(10000 * oi_ratio),
        call_open_interest=10000,
        total_open_interest=int(10000 + 10000 * oi_ratio),
        put_call_open_interest_ratio=oi_ratio,
        implied_volatility=33.3,
        is_monthly=is_monthly,
    )


def test_classify_signal_uses_ordered_thresholds() -> None:
    t = thresholds()
    assert classify_signal(0.20, 0.50, t) is Signal.STRONG_BULLISH
    assert classify_signal(0.50, 0.80, t) is Signal.BULLISH
    assert classify_signal(0.50, 1.10, t) is Signal.MIXED_CAUTION
    assert classify_signal(0.90, 0.80, t) is Signal.NEUTRAL
    assert classify_signal(1.20, 0.80, t) is Signal.BEARISH_HEDGING
    assert classify_signal(0.20, 1.40, t) is Signal.BEARISH_HEDGING


def test_select_monthly_rows_prefers_monthly_expiration() -> None:
    rows = [
        row("06/05/26 (w)", 0.60, 0.80, 5000, is_monthly=False),
        row("06/18/26 (m)", 0.31, 0.54, 111014, is_monthly=True),
        row("07/02/26 (w)", 0.33, 0.31, 15395, is_monthly=False),
        row("07/17/26 (m)", 0.29, 0.43, 69554, is_monthly=True),
    ]

    selected = select_monthly_rows(rows, months=2)

    assert [item.expiration_label for item in selected] == ["06/18/26 (m)", "07/17/26 (m)"]


def test_select_monthly_rows_falls_back_to_highest_volume_when_no_monthly() -> None:
    rows = [
        row("06/05/26 (w)", 0.60, 0.80, 5000, is_monthly=False),
        row("06/12/26 (w)", 0.35, 0.52, 39171, is_monthly=False),
    ]

    selected = select_monthly_rows(rows, months=1)

    assert selected[0].expiration_label == "06/12/26 (w)"


def test_analyze_snapshot_creates_commentary_and_monthly_signals() -> None:
    snapshot = Snapshot(
        symbol="MSFT",
        url="https://www.barchart.com/stocks/quotes/msft/put-call-ratios",
        captured_at=datetime(2026, 6, 2, 21, 30),
        metrics=TopMetrics("07/29/26", 31.62, 33.28, 61.17, 85.0),
        rows=[
            row("06/18/26 (m)", 0.31, 0.54, 111014),
            row("07/17/26 (m)", 0.29, 0.43, 69554),
            row("10/16/26 (m)", 0.89, 1.49, 6748),
        ],
    )

    analysis = analyze_snapshot(snapshot, thresholds(), months=12)

    assert analysis.symbol == "MSFT"
    assert analysis.monthly_signals[0].month == "2026-06"
    assert analysis.monthly_signals[0].signal is Signal.STRONG_BULLISH
    assert analysis.monthly_signals[2].signal is Signal.BEARISH_HEDGING
    assert "2 bullish" in analysis.commentary
    assert "1 bearish" in analysis.commentary


def test_analyze_snapshot_commentary_reports_neutral_when_neutral_signals_dominate() -> None:
    snapshot = Snapshot(
        symbol="MSFT",
        url="https://www.barchart.com/stocks/quotes/msft/put-call-ratios",
        captured_at=datetime(2026, 6, 2, 21, 30),
        metrics=TopMetrics("07/29/26", 31.62, 33.28, 61.17, 85.0),
        rows=[
            row("06/18/26 (m)", 0.90, 0.80, 111014),
            row("07/17/26 (m)", 0.95, 0.85, 69554),
            row("08/21/26 (m)", 0.50, 0.80, 42000),
        ],
    )

    analysis = analyze_snapshot(snapshot, thresholds(), months=12)

    assert "neutral overall" in analysis.commentary


def test_analyze_snapshot_commentary_reports_mixed_when_bullish_and_mixed_tie_for_lead() -> None:
    snapshot = Snapshot(
        symbol="MSFT",
        url="https://www.barchart.com/stocks/quotes/msft/put-call-ratios",
        captured_at=datetime(2026, 6, 2, 21, 30),
        metrics=TopMetrics("07/29/26", 31.62, 33.28, 61.17, 85.0),
        rows=[
            row("06/18/26 (m)", 0.50, 0.80, 111014),
            row("07/17/26 (m)", 0.80, 1.20, 69554),
        ],
    )

    analysis = analyze_snapshot(snapshot, thresholds(), months=12)

    assert "mixed overall" in analysis.commentary
