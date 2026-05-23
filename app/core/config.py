# FILE-ID: FILE-APP-CORE-CONFIG-PY
# SECTION-ID: SECTION-APP-CORE-CONFIG-PY-MAIN
# FEATURE-ID: FEATURE-APP-CORE-CONFIG-PY-RUNTIME
# CHUNK-ID: CHUNK-APP-CORE-CONFIG-PY-001

import functools
from functools import lru_cache
from pydantic import BaseModel
import os

class Settings(BaseModel):
    app_name: str = '오케스트레이터-자가개선-실험-즉시-실행-원본-대상-경로-C-Use-88b347d566'
    app_env: str = os.getenv('APP_ENV', 'development')
    app_debug: bool = os.getenv('APP_DEBUG', 'true').lower() in {'1', 'true', 'yes', 'on'}
    app_secret_key: str = os.getenv('APP_SECRET_KEY', '')
    status_endpoint: str = os.getenv('STATUS_ENDPOINT', 'http://localhost:8000/health')

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
