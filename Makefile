# FILE-ID: FILE-MAKEFILE
# SECTION-ID: SECTION-MAKEFILE-MAIN
# FEATURE-ID: FEATURE-MAKEFILE-RUNTIME
# CHUNK-ID: CHUNK-MAKEFILE-001

run:
	uvicorn app.main:create_application --factory --reload

test:
	pytest -q -s

check:
	python -m compileall app backend tests ai
	pytest -q -s tests/test_health.py tests/test_routes.py tests/test_runtime.py tests/test_security_runtime.py
