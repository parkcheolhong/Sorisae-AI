from __future__ import annotations

from sqlalchemy import create_engine, inspect, text

import backend.database as backend_database


def test_ensure_user_role_columns_adds_legacy_user_columns_idempotently(monkeypatch) -> None:
    sqlite_engine = create_engine("sqlite:///:memory:")
    with sqlite_engine.begin() as connection:
        connection.execute(text(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                email VARCHAR(255) NOT NULL
            )
            """
        ))

    monkeypatch.setattr(backend_database, "engine", sqlite_engine)

    backend_database.ensure_user_role_columns()
    backend_database.ensure_user_role_columns()

    columns = {column["name"] for column in inspect(sqlite_engine).get_columns("users")}
    assert {
        "is_active",
        "is_admin",
        "is_superuser",
        "member_type",
        "business_name",
        "business_registration_number",
        "representative_name",
        "preferred_language",
        "country_code",
        "phone_number",
        "is_staff",
        "passkey_enabled",
        "passkey_credential_id",
        "passkey_public_key",
        "passkey_device_label",
        "passkey_sign_count",
        "passkey_registered_at",
        "native_language",
        "country",
    }.issubset(columns)

    with sqlite_engine.begin() as connection:
        connection.execute(text("INSERT INTO users (id, email) VALUES (1, 'user@example.com')"))
        row = connection.execute(text(
            """
            SELECT
                is_active,
                is_admin,
                is_superuser,
                member_type,
                is_staff,
                passkey_enabled,
                passkey_sign_count
            FROM users
            WHERE id = 1
            """
        )).mappings().one()

    assert row["is_active"] == 1
    assert row["is_admin"] == 0
    assert row["is_superuser"] == 0
    assert row["member_type"] == "individual"
    assert row["is_staff"] == 0
    assert row["passkey_enabled"] == 0
    assert row["passkey_sign_count"] == 0
