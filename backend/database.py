"""공용 백엔드 데이터베이스 호환 레이어"""
from sqlalchemy import inspect, text

from backend.marketplace.database import (
    Base,
    SessionLocal,
    add_missing_columns,
    check_database_availability,
    engine,
    get_db,
)


def ensure_user_role_columns() -> None:
    """기존 users 테이블에 관리자 권한 및 가입 유형 컬럼이 없으면 추가한다."""
    inspector = inspect(engine)
    if not inspector.has_table("users"):
        return

    with engine.begin() as connection:
        add_missing_columns(
            connection,
            "users",
            {
                "is_active": "BOOLEAN NOT NULL DEFAULT TRUE",
                "is_admin": "BOOLEAN NOT NULL DEFAULT FALSE",
                "is_superuser": "BOOLEAN NOT NULL DEFAULT FALSE",
                "member_type": "VARCHAR(30) NOT NULL DEFAULT 'individual'",
                "business_name": "VARCHAR(200)",
                "business_registration_number": "VARCHAR(50)",
                "representative_name": "VARCHAR(120)",
                "passkey_enabled": "BOOLEAN NOT NULL DEFAULT FALSE",
                "passkey_credential_id": "VARCHAR(255) UNIQUE",
                "passkey_public_key": "TEXT",
                "passkey_device_label": "VARCHAR(120)",
                "passkey_sign_count": "INTEGER NOT NULL DEFAULT 0",
                "passkey_registered_at": "TIMESTAMP",
            },
            inspector=inspector,
        )


def ensure_traceability_schema() -> None:
    """기존 주요 테이블에 trace 컬럼을 추가하고 새 추적 테이블을 생성한다."""
    from backend.marketplace import models  # noqa: F401
    from backend.mobile.song_translation import models as mobile_song_translation_models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    table_column_specs = {
        "customer_orchestrator_completions": {
            "trace_id": "VARCHAR(120)",
            "flow_id": "VARCHAR(40)",
            "step_id": "VARCHAR(40)",
            "action": "VARCHAR(80)",
        },
        "ad_video_orders": {
            "trace_id": "VARCHAR(120)",
            "flow_id": "VARCHAR(40)",
            "step_id": "VARCHAR(40)",
            "action": "VARCHAR(80)",
        },
    }

    with engine.begin() as connection:
        for table_name, columns in table_column_specs.items():
            add_missing_columns(
                connection,
                table_name,
                columns,
                inspector=inspector,
            )

        if inspector.has_table("feature_execution_logs"):
            add_missing_columns(
                connection,
                "feature_execution_logs",
                {
                    "feature_id": "VARCHAR(100)",
                    "entity_type": "VARCHAR(80)",
                    "entity_id": "VARCHAR(120)",
                    "run_id": "VARCHAR(120)",
                    "prompt": "TEXT",
                    "message": "TEXT",
                    "payload_json": "TEXT",
                    "output_payload_json": "TEXT",
                    "error_message": "TEXT",
                },
                inspector=inspector,
            )
            connection.execute(text(
                "UPDATE feature_execution_logs SET feature_id = COALESCE(NULLIF(feature_id, ''), entity_type, 'feature_execution')"
            ))
            connection.execute(text(
                "UPDATE feature_execution_logs SET entity_type = COALESCE(NULLIF(entity_type, ''), feature_id, 'feature_execution')"
            ))
            connection.execute(text(
                "UPDATE feature_execution_logs SET entity_id = COALESCE(NULLIF(entity_id, ''), run_id, trace_id, CAST(id AS TEXT))"
            ))
            connection.execute(text(
                "UPDATE feature_execution_logs SET message = COALESCE(NULLIF(message, ''), error_message, prompt, '')"
            ))
            connection.execute(text(
                "UPDATE feature_execution_logs SET payload_json = COALESCE(payload_json, output_payload_json)"
            ))

        if inspector.has_table("feature_retry_queue"):
            add_missing_columns(
                connection,
                "feature_retry_queue",
                {
                    "user_id": "INTEGER",
                    "feature_id": "VARCHAR(100)",
                    "entity_type": "VARCHAR(80)",
                    "entity_id": "VARCHAR(120)",
                    "queue_name": "VARCHAR(80)",
                    "last_error": "TEXT",
                    "attempt_count": "INTEGER",
                    "max_attempts": "INTEGER",
                    "retry_count": "INTEGER",
                },
                inspector=inspector,
            )
            connection.execute(text(
                "UPDATE feature_retry_queue SET feature_id = COALESCE(NULLIF(feature_id, ''), entity_type, queue_name, 'feature_retry')"
            ))
            connection.execute(text(
                "UPDATE feature_retry_queue SET entity_type = COALESCE(NULLIF(entity_type, ''), feature_id, 'feature_retry')"
            ))
            connection.execute(text(
                "UPDATE feature_retry_queue SET entity_id = COALESCE(NULLIF(entity_id, ''), trace_id, CAST(id AS TEXT))"
            ))
            connection.execute(text(
                "UPDATE feature_retry_queue SET queue_name = COALESCE(NULLIF(queue_name, ''), feature_id, 'feature_retry_queue')"
            ))
            connection.execute(text(
                "UPDATE feature_retry_queue SET attempt_count = COALESCE(attempt_count, retry_count, 0)"
            ))
            connection.execute(text(
                "UPDATE feature_retry_queue SET max_attempts = COALESCE(max_attempts, 3)"
            ))