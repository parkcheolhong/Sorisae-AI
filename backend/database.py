"""공용 백엔드 데이터베이스 호환 레이어"""
from sqlalchemy import inspect, text

from backend.marketplace.database import Base, SessionLocal, check_database_availability, engine, get_db


def ensure_user_role_columns() -> None:
    """기존 users 테이블에 관리자 권한 및 가입 유형 컬럼이 없으면 추가한다."""
    inspector = inspect(engine)
    if not inspector.has_table("users"):
        return

    columns = {
        column["name"]
        for column in inspector.get_columns("users")
    }
    statements = []
    if "is_active" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE"
        )
    if "is_admin" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT FALSE"
        )
    if "is_superuser" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN is_superuser BOOLEAN NOT NULL DEFAULT FALSE"
        )
    if "member_type" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN member_type VARCHAR(30) NOT NULL DEFAULT 'individual'"
        )
    if "business_name" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN business_name VARCHAR(200)"
        )
    if "business_registration_number" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN business_registration_number VARCHAR(50)"
        )
    if "representative_name" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN representative_name VARCHAR(120)"
        )
    if "preferred_language" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN preferred_language VARCHAR(16)"
        )
    if "country_code" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN country_code VARCHAR(8)"
        )
    if "phone_number" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN phone_number VARCHAR(40)"
        )
        statements.append(
            "CREATE INDEX IF NOT EXISTS ix_users_phone_number ON users (phone_number)"
        )
    if "is_staff" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN is_staff BOOLEAN NOT NULL DEFAULT FALSE"
        )
    if "passkey_enabled" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN passkey_enabled BOOLEAN NOT NULL DEFAULT FALSE"
        )
    if "passkey_credential_id" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN passkey_credential_id VARCHAR(255) UNIQUE"
        )
    if "passkey_public_key" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN passkey_public_key TEXT"
        )
    if "passkey_device_label" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN passkey_device_label VARCHAR(120)"
        )
    if "passkey_sign_count" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN passkey_sign_count INTEGER NOT NULL DEFAULT 0"
        )
    if "passkey_registered_at" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN passkey_registered_at TIMESTAMP"
        )

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


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
            if not inspector.has_table(table_name):
                continue
            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, column_type in columns.items():
                if column_name in existing_columns:
                    continue
                connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))

        if inspector.has_table("feature_execution_logs"):
            existing_columns = {column["name"] for column in inspector.get_columns("feature_execution_logs")}
            feature_execution_columns = {
                "feature_id": "VARCHAR(100)",
                "entity_type": "VARCHAR(80)",
                "entity_id": "VARCHAR(120)",
                "run_id": "VARCHAR(120)",
                "prompt": "TEXT",
                "message": "TEXT",
                "payload_json": "TEXT",
                "output_payload_json": "TEXT",
                "error_message": "TEXT",
            }
            for column_name, column_type in feature_execution_columns.items():
                if column_name in existing_columns:
                    continue
                connection.execute(text(
                    f"ALTER TABLE feature_execution_logs ADD COLUMN {column_name} {column_type}"
                ))
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
            feature_retry_columns = {column["name"] for column in inspector.get_columns("feature_retry_queue")}
            feature_retry_column_specs = {
                "user_id": "INTEGER",
                "feature_id": "VARCHAR(100)",
                "entity_type": "VARCHAR(80)",
                "entity_id": "VARCHAR(120)",
                "queue_name": "VARCHAR(80)",
                "last_error": "TEXT",
                "attempt_count": "INTEGER",
                "max_attempts": "INTEGER",
                "retry_count": "INTEGER",
            }
            for column_name, column_type in feature_retry_column_specs.items():
                if column_name in feature_retry_columns:
                    continue
                connection.execute(
                    text(f"ALTER TABLE feature_retry_queue ADD COLUMN {column_name} {column_type}")
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