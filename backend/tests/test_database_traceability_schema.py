from __future__ import annotations

import sys
import types

from sqlalchemy import create_engine, inspect, text

import backend.database as backend_database


class _NoOpMetadata:
    def create_all(self, bind) -> None:
        return None


class _NoOpBase:
    metadata = _NoOpMetadata()


def _stub_backend_mobile_dependencies(monkeypatch) -> None:
    fake_mobile_package = types.ModuleType("backend.mobile.song_translation")
    fake_mobile_models = types.ModuleType("backend.mobile.song_translation.models")
    fake_mobile_package.models = fake_mobile_models
    monkeypatch.setitem(sys.modules, "backend.mobile.song_translation", fake_mobile_package)
    monkeypatch.setitem(sys.modules, "backend.mobile.song_translation.models", fake_mobile_models)


def test_ensure_traceability_schema_migrates_sqlite_feature_retry_queue(monkeypatch) -> None:
    sqlite_engine = create_engine("sqlite:///:memory:")
    with sqlite_engine.begin() as connection:
        connection.execute(text(
            """
            CREATE TABLE feature_retry_queue (
                id INTEGER PRIMARY KEY,
                status VARCHAR(40) NOT NULL,
                trace_id VARCHAR(120),
                retry_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP
            )
            """
        ))
        connection.execute(text(
            """
            INSERT INTO feature_retry_queue (id, status, trace_id, retry_count)
            VALUES (1, 'pending', 'trace-1', 2)
            """
        ))

    # ensure_traceability_schema imports backend.mobile.song_translation.models before migrating tables.
    _stub_backend_mobile_dependencies(monkeypatch)
    monkeypatch.setattr(backend_database, "engine", sqlite_engine)
    monkeypatch.setattr(backend_database, "Base", _NoOpBase())

    backend_database.ensure_traceability_schema()

    columns = {
        column["name"]
        for column in inspect(sqlite_engine).get_columns("feature_retry_queue")
    }
    assert {
        "id",
        "status",
        "trace_id",
        "retry_count",
        "created_at",
    }.issubset(columns)
    assert {
        "user_id",
        "feature_id",
        "entity_type",
        "entity_id",
        "queue_name",
        "last_error",
        "attempt_count",
        "max_attempts",
    }.issubset(columns)

    with sqlite_engine.begin() as connection:
        row = connection.execute(text(
            """
            SELECT
                id,
                status,
                trace_id,
                retry_count,
                created_at,
                feature_id,
                entity_type,
                entity_id,
                queue_name,
                attempt_count,
                max_attempts
            FROM feature_retry_queue
            WHERE id = 1
            """
        )).mappings().one()

    assert row["id"] == 1
    assert row["status"] == "pending"
    assert row["trace_id"] == "trace-1"
    assert row["retry_count"] == 2
    assert row["created_at"] is None
    assert row["feature_id"] == "feature_retry"
    assert row["entity_type"] == "feature_retry"
    assert row["entity_id"] == "trace-1"
    assert row["queue_name"] == "feature_retry"
    assert row["attempt_count"] == 2
    assert row["max_attempts"] == 3
