from __future__ import annotations

import sys
import types
from types import SimpleNamespace

from sqlalchemy import create_engine, inspect, text

import backend.database as backend_database


def test_ensure_traceability_schema_adds_feature_retry_queue_columns_on_sqlite(monkeypatch) -> None:
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

    fake_mobile_package = types.ModuleType("backend.mobile.song_translation")
    fake_mobile_models = types.ModuleType("backend.mobile.song_translation.models")
    fake_mobile_package.models = fake_mobile_models
    monkeypatch.setitem(sys.modules, "backend.mobile.song_translation", fake_mobile_package)
    monkeypatch.setitem(sys.modules, "backend.mobile.song_translation.models", fake_mobile_models)
    monkeypatch.setattr(backend_database, "engine", sqlite_engine)
    monkeypatch.setattr(
        backend_database,
        "Base",
        SimpleNamespace(metadata=SimpleNamespace(create_all=lambda bind: None)),
    )

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

    assert dict(row) == {
        "id": 1,
        "status": "pending",
        "trace_id": "trace-1",
        "retry_count": 2,
        "created_at": None,
        "feature_id": "feature_retry",
        "entity_type": "feature_retry",
        "entity_id": "trace-1",
        "queue_name": "feature_retry",
        "attempt_count": 2,
        "max_attempts": 3,
    }
