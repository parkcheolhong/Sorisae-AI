# FILE-ID: FILE-BACKEND-CORE-DATABASE-PY
# SECTION-ID: SECTION-BACKEND-CORE-DATABASE-PY-MAIN
# FEATURE-ID: FEATURE-BACKEND-CORE-DATABASE-PY-RUNTIME
# CHUNK-ID: CHUNK-BACKEND-CORE-DATABASE-PY-001

DATABASE_TABLES = ["requests", "modules", "artifacts", "handoffs"]
DB_SETTINGS = {'url': 'sqlite:///./runtime.db', 'tables': list(DATABASE_TABLES)}

def get_database_settings() -> dict:
    return dict(DB_SETTINGS)

def ensure_database_ready() -> dict:
    return get_database_settings()
