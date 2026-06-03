from datetime import date, datetime, timedelta
from pathlib import Path

from reporter.history import HistoryStore
from reporter.models import ExpirationRow, Snapshot, TopMetrics


def snapshot(symbol: str, captured_at: datetime, ratio: float) -> Snapshot:
    return Snapshot(
        symbol=symbol,
        url=f"https://www.barchart.com/stocks/quotes/{symbol.lower()}/put-call-ratios",
        captured_at=captured_at,
        metrics=TopMetrics("07/29/26", 31.62, 33.28, 61.17, 85.0),
        rows=[
            ExpirationRow(
                expiration_label="06/18/26 (m)",
                expiration_date=date(2026, 6, 18),
                dte=16,
                put_volume=26096,
                call_volume=84918,
                total_volume=111014,
                put_call_volume_ratio=ratio,
                put_open_interest=244398,
                call_open_interest=454545,
                total_open_interest=698943,
                put_call_open_interest_ratio=0.54,
                implied_volatility=32.94,
                is_monthly=True,
            )
        ],
    )


def test_history_store_round_trips_snapshot(tmp_path: Path) -> None:
    store = HistoryStore(tmp_path / "history.sqlite3")
    current = snapshot("MSFT", datetime(2026, 6, 2, 21, 30), 0.31)

    store.save_snapshot(current)
    loaded = store.latest_snapshot("MSFT")

    assert loaded is not None
    assert loaded.symbol == "MSFT"
    assert loaded.rows[0].put_call_volume_ratio == 0.31


def test_history_store_finds_prior_day_week_month(tmp_path: Path) -> None:
    store = HistoryStore(tmp_path / "history.sqlite3")
    now = datetime(2026, 6, 30, 21, 30)
    store.save_snapshot(snapshot("MSFT", now - timedelta(days=1), 0.40))
    store.save_snapshot(snapshot("MSFT", now - timedelta(days=7), 0.50))
    store.save_snapshot(snapshot("MSFT", now - timedelta(days=30), 0.60))
    store.save_snapshot(snapshot("MSFT", now, 0.31))

    priors = store.prior_snapshots("MSFT", now)

    assert priors["previous_day"].rows[0].put_call_volume_ratio == 0.40
    assert priors["previous_week"].rows[0].put_call_volume_ratio == 0.50
    assert priors["previous_month"].rows[0].put_call_volume_ratio == 0.60
