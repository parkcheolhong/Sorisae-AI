# FILE-ID: FILE-TESTS-CONFTEST-PY
# SECTION-ID: SECTION-TESTS-CONFTEST-PY-MAIN
# FEATURE-ID: FEATURE-TESTS-CONFTEST-PY-RUNTIME
# CHUNK-ID: CHUNK-TESTS-CONFTEST-PY-001

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
