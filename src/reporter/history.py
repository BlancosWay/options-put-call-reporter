from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from reporter.models import ExpirationRow, Snapshot, TopMetrics


class HistoryStore:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    url TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    metrics_json TEXT NOT NULL,
                    rows_json TEXT NOT NULL,
                    UNIQUE(symbol, captured_at)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_snapshots_symbol_time
                ON snapshots(symbol, captured_at)
                """
            )

    def save_snapshot(self, snapshot: Snapshot) -> None:
        rows_json = json.dumps([self._row_to_json(row) for row in snapshot.rows])
        metrics_json = json.dumps(asdict(snapshot.metrics))
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO snapshots(symbol, url, captured_at, metrics_json, rows_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    snapshot.symbol,
                    snapshot.url,
                    snapshot.captured_at.isoformat(),
                    metrics_json,
                    rows_json,
                ),
            )

    def latest_snapshot(self, symbol: str) -> Snapshot | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM snapshots
                WHERE symbol = ?
                ORDER BY captured_at DESC
                LIMIT 1
                """,
                (symbol.upper(),),
            ).fetchone()
        return self._snapshot_from_row(row) if row else None

    def prior_snapshots(self, symbol: str, captured_at: datetime) -> dict[str, Snapshot | None]:
        return {
            "previous_day": self._nearest_to(symbol, captured_at, timedelta(days=1)),
            "previous_week": self._nearest_to(symbol, captured_at, timedelta(days=7)),
            "previous_month": self._nearest_to(symbol, captured_at, timedelta(days=30)),
        }

    def _nearest_to(
        self, symbol: str, captured_at: datetime, offset: timedelta
    ) -> Snapshot | None:
        target = captured_at - offset
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM snapshots
                WHERE symbol = ? AND captured_at < ?
                ORDER BY ABS(julianday(captured_at) - julianday(?)) ASC
                LIMIT 1
                """,
                (symbol.upper(), captured_at.isoformat(), target.isoformat()),
            ).fetchone()
        return self._snapshot_from_row(row) if row else None

    @staticmethod
    def _row_to_json(row: ExpirationRow) -> dict[str, Any]:
        data = asdict(row)
        data["expiration_date"] = row.expiration_date.isoformat()
        return data

    @staticmethod
    def _snapshot_from_row(row: sqlite3.Row) -> Snapshot:
        metrics_data = json.loads(row["metrics_json"])
        rows_data = json.loads(row["rows_json"])
        return Snapshot(
            symbol=row["symbol"],
            url=row["url"],
            captured_at=datetime.fromisoformat(row["captured_at"]),
            metrics=TopMetrics(**metrics_data),
            rows=[
                ExpirationRow(
                    **{
                        **item,
                        "expiration_date": date.fromisoformat(item["expiration_date"]),
                    }
                )
                for item in rows_data
            ],
        )
