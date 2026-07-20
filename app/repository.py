"""Small SQLite repository for capacity-planning scenarios."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


class ScenarioNotFoundError(LookupError):
    """Raised when a scenario identifier has no persisted record."""

    def __init__(self, scenario_id: int) -> None:
        self.scenario_id = scenario_id
        super().__init__(f"Scenario {scenario_id} was not found.")


@dataclass(frozen=True, slots=True)
class ScenarioRecord:
    """Immutable persisted scenario projection."""

    id: int
    name: str
    description: str | None
    workload_mode: str
    inputs: dict[str, Any]
    created_at: str
    updated_at: str


class ScenarioRepository:
    """Persist complete scenario documents without coupling storage to engine internals."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def _session(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._session() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS scenarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    workload_mode TEXT NOT NULL,
                    inputs_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def create(self, payload: Mapping[str, Any]) -> ScenarioRecord:
        timestamp = _utc_timestamp()
        with self._session() as connection:
            cursor = connection.execute(
                """
                INSERT INTO scenarios (
                    name, description, workload_mode, inputs_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["name"],
                    payload.get("description"),
                    payload["workload_mode"],
                    _canonical_json(payload["inputs"]),
                    timestamp,
                    timestamp,
                ),
            )
            scenario_id = int(cursor.lastrowid or 0)
        return self.get(scenario_id)

    def list(self) -> list[ScenarioRecord]:
        with self._session() as connection:
            rows = connection.execute("SELECT * FROM scenarios ORDER BY id ASC").fetchall()
        return [_row_to_record(row) for row in rows]

    def get(self, scenario_id: int) -> ScenarioRecord:
        with self._session() as connection:
            row = connection.execute(
                "SELECT * FROM scenarios WHERE id = ?",
                (scenario_id,),
            ).fetchone()
        if row is None:
            raise ScenarioNotFoundError(scenario_id)
        return _row_to_record(row)

    def update(self, scenario_id: int, payload: Mapping[str, Any]) -> ScenarioRecord:
        existing = self.get(scenario_id)
        timestamp = _utc_timestamp()
        if timestamp <= existing.updated_at:
            timestamp = _next_microsecond(existing.updated_at)
        with self._session() as connection:
            connection.execute(
                """
                UPDATE scenarios
                SET name = ?, description = ?, workload_mode = ?, inputs_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    payload["name"],
                    payload.get("description"),
                    payload["workload_mode"],
                    _canonical_json(payload["inputs"]),
                    timestamp,
                    scenario_id,
                ),
            )
        return self.get(scenario_id)

    def delete(self, scenario_id: int) -> None:
        self.get(scenario_id)
        with self._session() as connection:
            connection.execute("DELETE FROM scenarios WHERE id = ?", (scenario_id,))


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _row_to_record(row: sqlite3.Row) -> ScenarioRecord:
    return ScenarioRecord(
        id=int(row["id"]),
        name=str(row["name"]),
        description=row["description"],
        workload_mode=str(row["workload_mode"]),
        inputs=json.loads(row["inputs_json"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _utc_timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def _next_microsecond(timestamp: str) -> str:
    value = datetime.fromisoformat(timestamp) + timedelta(microseconds=1)
    return value.isoformat(timespec="microseconds")
