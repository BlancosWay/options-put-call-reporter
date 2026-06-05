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
    assert loaded.url == current.url
    assert loaded.captured_at == current.captured_at
    assert loaded.metrics.latest_earnings == "07/29/26"
    assert loaded.metrics.implied_volatility == 31.62
    assert loaded.metrics.historic_volatility == 33.28
    assert loaded.metrics.iv_rank == 61.17
    assert loaded.metrics.iv_percentile == 85.0
    assert loaded.rows[0].expiration_label == "06/18/26 (m)"
    assert loaded.rows[0].expiration_date == date(2026, 6, 18)
    assert loaded.rows[0].dte == 16
    assert loaded.rows[0].put_volume == 26096
    assert loaded.rows[0].call_volume == 84918
    assert loaded.rows[0].total_volume == 111014
    assert loaded.rows[0].put_call_volume_ratio == 0.31
    assert loaded.rows[0].put_open_interest == 244398
    assert loaded.rows[0].call_open_interest == 454545
    assert loaded.rows[0].total_open_interest == 698943
    assert loaded.rows[0].put_call_open_interest_ratio == 0.54
    assert loaded.rows[0].implied_volatility == 32.94
    assert loaded.rows[0].is_monthly is True


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


def test_history_store_uses_nearest_prior_trading_snapshots(tmp_path: Path) -> None:
    store = HistoryStore(tmp_path / "history.sqlite3")
    now = datetime(2026, 6, 30, 21, 30)
    store.save_snapshot(snapshot("MSFT", now - timedelta(hours=1), 0.10))
    store.save_snapshot(snapshot("MSFT", now - timedelta(days=1, hours=1), 0.40))
    store.save_snapshot(snapshot("MSFT", now - timedelta(days=6), 0.50))
    store.save_snapshot(snapshot("MSFT", now - timedelta(days=31), 0.60))
    store.save_snapshot(snapshot("MSFT", now, 0.31))

    priors = store.prior_snapshots("MSFT", now)

    assert priors["previous_day"].rows[0].put_call_volume_ratio == 0.40
    assert priors["previous_week"].rows[0].put_call_volume_ratio == 0.50
    assert priors["previous_month"].rows[0].put_call_volume_ratio == 0.60


def test_history_store_does_not_reuse_previous_day_for_week_or_month(tmp_path: Path) -> None:
    store = HistoryStore(tmp_path / "history.sqlite3")
    now = datetime(2026, 6, 30, 21, 30)
    store.save_snapshot(snapshot("MSFT", now - timedelta(days=1), 0.40))
    store.save_snapshot(snapshot("MSFT", now, 0.31))

    priors = store.prior_snapshots("MSFT", now)

    assert priors["previous_day"].rows[0].put_call_volume_ratio == 0.40
    assert priors["previous_week"] is None
    assert priors["previous_month"] is None


def test_history_store_prior_snapshots_are_symbol_specific_and_exclude_current(
    tmp_path: Path,
) -> None:
    store = HistoryStore(tmp_path / "history.sqlite3")
    now = datetime(2026, 6, 30, 21, 30)
    store.save_snapshot(snapshot("MSFT", now, 0.31))
    store.save_snapshot(snapshot("GOOG", now - timedelta(days=1), 0.88))

    priors = store.prior_snapshots("MSFT", now)

    assert priors["previous_day"] is None


def test_history_store_prior_snapshots_ignore_same_day_reruns(tmp_path: Path) -> None:
    store = HistoryStore(tmp_path / "history.sqlite3")
    now = datetime(2026, 6, 30, 21, 30)
    store.save_snapshot(snapshot("MSFT", now - timedelta(hours=1), 0.10))

    priors = store.prior_snapshots("MSFT", now)

    assert priors["previous_day"] is None
    assert priors["previous_week"] is None
    assert priors["previous_month"] is None


def test_history_store_normalizes_saved_symbol(tmp_path: Path) -> None:
    store = HistoryStore(tmp_path / "history.sqlite3")
    current = snapshot("msft", datetime(2026, 6, 2, 21, 30), 0.31)

    store.save_snapshot(current)
    loaded = store.latest_snapshot("MSFT")

    assert loaded is not None
    assert loaded.symbol == "MSFT"


def test_history_store_nearest_lookup_breaks_ties_with_newer_snapshot(
    tmp_path: Path,
) -> None:
    store = HistoryStore(tmp_path / "history.sqlite3")
    now = datetime(2026, 6, 30, 21, 30)
    store.save_snapshot(snapshot("MSFT", now - timedelta(days=8), 0.80))
    store.save_snapshot(snapshot("MSFT", now - timedelta(days=6), 0.60))

    priors = store.prior_snapshots("MSFT", now)

    assert priors["previous_week"].rows[0].put_call_volume_ratio == 0.60
