# FILE-ID: FILE-SCRIPTS-DEV-SH
# SECTION-ID: SECTION-SCRIPTS-DEV-SH-MAIN
# FEATURE-ID: FEATURE-SCRIPTS-DEV-SH-RUNTIME
# CHUNK-ID: CHUNK-SCRIPTS-DEV-SH-001

#!/usr/bin/env bash
set -euo pipefail

python -m compileall app backend >/dev/null
uvicorn app.main:create_application --factory --reload --host 0.0.0.0 --port 8000
