# 오케스트레이터-자가개선-실험-즉시-실행-원본-대상-경로-C-Use-9b4c2cd6f4 automatic validation result

- status: failed
- validation_profile: nextjs_app
- output_archive_path: C:\Users\WORK\source\repos\parkcheolhong\codeAI\uploads\tmp\codeai_admin_runtime\admin_self_experiments\codeAI_20260423_045333\오케스트레이터-자가개선-실험-즉시-실행-원본-대상-경로-C-Use-9b4c2cd6f4_shipment.zip

## 실행 방법
1. `pip install -r requirements.delivery.lock.txt`
2. `uvicorn app.main:create_application --factory --host 0.0.0.0 --port 8000`
3. `pytest -q`
4. `오케스트레이터-자가개선-실험-즉시-실행-원본-대상-경로-C-Use-9b4c2cd6f4_shipment.zip` 압축 해제 후 `scripts/check.sh` 재실행

## 검증 결과
- semantic_gate: fail
- integration_test_engine: pass
- framework_e2e_validation: pass
- external_integration_validation: pass
- shipping_zip_validation: fail

- product_readiness_hard_gate: fail

## operational latency evidence
- latency_warning: true
- warning_targets: system_settings, workspace_self_run_record
- max_latency_ms: 185.8
- warning_threshold_ms: admin=150.0ms, marketplace=200.0ms, system_settings=120.0ms, websocket=150.0ms, workspace_self_run_record=120.0ms

## hard gate closed evidence
- [ ] dependency install
- [ ] standalone boot
- [ ] core api smoke
- [ ] pytest
- [ ] zip reproduction

## 실패 원인
- semantic gate failed
- shipping zip reproduction validation failed
- test coverage too small: 0
- commerce backend implementation too small: 0
- runtime scenario marker missing: catalog flow
- runtime scenario marker missing: marketplace publish payload
- thin implementation files detected: scripts/check.sh
