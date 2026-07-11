# FILE-ID: FILE-TESTS-CONFTEST-PY
# SECTION-ID: SECTION-TESTS-CONFTEST-PY-MAIN
# FEATURE-ID: FEATURE-TESTS-CONFTEST-PY-RUNTIME
# CHUNK-ID: CHUNK-TESTS-CONFTEST-PY-001

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Root test suite fallback: use a local sqlite DB when DATABASE_URL is not provided.
_pytest_db_dir = PROJECT_ROOT / ".runtime" / "pytest"
_pytest_db_dir.mkdir(parents=True, exist_ok=True)
_pytest_db_path = _pytest_db_dir / "root-tests.sqlite3"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_pytest_db_path.as_posix()}")
