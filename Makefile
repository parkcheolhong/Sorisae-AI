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

contrast:
	python scripts/audit_color_contrast.py

# VoIP·오디오 섹션 게이트 (SSOT lock + freeze + bridge 계약 + 섹션 경계)
voip-gate:
	python scripts/check_worldlinco_section_ssot_lock.py
	python scripts/check_section_boundary_lock.py
	python -m pytest backend/tests/test_worldlinco_section_freeze.py backend/tests/test_voice_translate_stt.py -q --tb=no

sorisae-gate:
	python scripts/check_worldlinco_section_ssot_lock.py
	python scripts/check_section_boundary_lock.py
	python scripts/check_sorisae_regression_lock.py
	python -m pytest backend/tests/test_sorisae_friend_chat_gate.py backend/tests/test_sorisae_failure_monitor_service.py -q
	cd apps/mobile-nadotongryoksa && npm run test -- --testPathPattern=sorisaeCaptureSegment

sorisae-monitor-backend-gate:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_sorisae_failure_monitor_rebuild_smoke.ps1

sorisae-probe:
	python scripts/run_sorisae_friend_chat_probe.py --base-url http://127.0.0.1:8000

sorisae-probe-adb:
	python scripts/run_sorisae_friend_chat_probe.py --adb-device R83W70QY11H

sorisae-phase-c-close:
	python scripts/close_sorisae_phase_c_checklist.py --adb-device R83W70QY11H

sorisae-vllm-up:
	powershell -ExecutionPolicy Bypass -File scripts/start_vllm_sorisae_8b.ps1

sorisae-vllm-restart-backend:
	docker compose up -d --force-recreate backend
