from datetime import datetime
from pathlib import Path

import pytest

from reporter.collector import collect_from_html


@pytest.mark.asyncio
async def test_collect_from_html_extracts_metrics_and_rows(tmp_path: Path) -> None:
    html = Path("tests/fixtures/barchart_put_call_sample.html").read_text(encoding="utf-8")

    snapshot = await collect_from_html(
        symbol="MSFT",
        url="https://www.barchart.com/stocks/quotes/msft/put-call-ratios",
        html=html,
        captured_at=datetime(2026, 6, 2, 21, 30),
    )

    assert snapshot.symbol == "MSFT"
    assert snapshot.metrics.latest_earnings == "07/29/26"
    assert snapshot.metrics.implied_volatility == 31.62
    assert len(snapshot.rows) == 2
    assert snapshot.rows[0].expiration_label == "06/18/26 (m)"
    assert snapshot.rows[0].put_call_volume_ratio == 0.31
    assert snapshot.rows[0].is_monthly is True
