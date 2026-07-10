# orchestrator.py 핵심 실행 루프 분리 설계 (5차)

> 상태: **구현 완료(P1–P4)**. `_run_orchestration_core` 의 ②중간 스테이지(~240줄)를
> `backend/orchestrator/customer/validation_stages_service.py` 의 `run_customer_validation_stages` 로
> byte-동일 이동(DI 43 파라미터, 반환 18키). 검증: 자유이름 미해소 0, baseline 30 + 컨트랙트 10 그린, lint clean.
> orchestrator.py **6.4k→6.27k**, `_run_orchestration_core` 402→~80줄(prepare→stages→finalize→assemble 와이어링).
> 선행: 템플릿뱅크/검증기/실행검증기/주문프로파일 4개 클러스터 분리 완료 → orchestrator.py **13.3k→6.4k**.

## 1. 현재 구조 (근거)

`_run_orchestration_core`(현재 `orchestrator.py` L5806–6208, ~402줄)는 **이미 서비스 레이어로의 seam**을 갖고 있다.
이미 `backend/orchestrator/customer/` 패키지가 단계별 서비스로 존재하며, **orchestrator.py 를 import 하지 않고**
필요한 함수·상수를 **DI(함수 주입, `*_func=`)** 로만 받는다(순환 import 0, `from __future__ import annotations` + stdlib + `utcnow`).

```
run_orchestration  ──►  run_customer_orchestration_service(run_orchestration_impl=_run_orchestration_core)
_run_orchestration_core:
  ① prepare_customer_orchestration_context_service(...DI...)        # preparation_service.py ✅ 분리됨
  ② [인라인 중간 스테이지 ~240줄]  ← 미분리(이번 대상)
  ③ finalize_customer_validation_bundle_service(...DI...)           # finalization_service.py ✅ 분리됨
  ④ assemble_customer_orchestration_response_service(...DI...)      # finalization_service.py ✅ 분리됨
```

기존 패키지:
- `customer/preparation_service.py` — `prepare_customer_orchestration_context`
- `customer/finalization_service.py` — `finalize_customer_validation_bundle`, `assemble_customer_orchestration_response`
- `customer/run_service.py` — `run_customer_orchestration`
- `customer/execution_service.py` — `execute_orchestration`

## 2. 분리 대상: 「②인라인 중간 스테이지」

`_run_orchestration_core` 의 prepare 결과 언팩(L5857) ~ finalize 호출 직전(L6098), **약 240줄**.
포함 단계(순서 보존 필수):

1. b-brain 멀티 제너레이터 실행 → 산출물 기록
2. compat manifest 작성 + 생성 파일 병합
3. `semantic_manifest_by_path` 빌드(파일 읽기)
4. semantic gate 실행
5. packaging audit
6. domain integration test engine (`asyncio.to_thread`)
7. framework e2e validator (`asyncio.to_thread`)
8. external integration validator
9. completion judge(1차) + semantic audit score
10. seed 아티팩트(artifact_log / traceability_map / python_security_report) + semantic audit report + auxiliary outputs 작성
11. written_files 정규화 + evidence_bundle_seed 갱신 + 아티팩트 재기록

## 3. 타깃 모듈/함수

`backend/orchestrator/customer/validation_stages_service.py` (신규)

```python
async def run_customer_validation_stages(
    *,
    # ── 입력(prepare 산출) ──
    request, task, mode, order_profile, validation_profile,
    compat_required_files, normalized_requirements, domain_contract,
    integration_test_plan, project_name, output_dir, started_at,
    # ── 주입 함수(orchestrator 소유) ──
    log_orchestration_phase_func,
    emit_orchestration_progress_func,
    run_b_brain_multi_generator_func,
    compat_manifest_for_request_func,
    compat_write_manifest_func,
    compat_write_json_func,
    compat_relative_path_func,
    compat_write_auxiliary_outputs_func,
    compat_run_semantic_gate_func,
    build_packaging_audit_func,
    run_domain_integration_test_engine_func,
    run_framework_e2e_validator_func,
    run_external_integration_validator_func,
    build_completion_judge_func,
    build_operational_evidence_bundle_func,
    build_target_patch_registry_snapshot_func,
    # ── 주입 상수(경로/임계) ──
    orch_min_files, orch_min_dirs, orch_semantic_audit_min_score,
    orch_artifact_log_path, orch_traceability_map_path,
    orch_semantic_audit_report_path, orch_python_security_report_path,
    orch_validation_result_json_path, orch_validation_result_md_path,
    orch_failure_report_path, orch_root_cause_report_path,
    orch_output_audit_path, orch_id_registry_path, orch_id_registry_schema_path,
    progress_callback=None,
) -> Dict[str, Any]:
    """②중간 스테이지를 실행하고 finalize/assemble 에 넘길 번들을 반환."""
    ...
    return {
        "written_files": ..., "manifest": ..., "anchor_path": ...,
        "completion_state": ..., "semantic_gate": ..., "packaging_audit": ...,
        "integration_test_engine": ..., "framework_e2e_validation": ...,
        "external_integration_validation": ..., "completion_judge": ...,
        "semantic_audit_score": ..., "semantic_audit_ok": ...,
        "target_patch_registry_snapshot": ..., "artifact_log_path": ...,
        "traceability_map_path": ..., "semantic_audit_report_path": ...,
        "python_security_report_path": ..., "auxiliary_outputs": ...,
        "artifact_paths_seed": ..., "evidence_bundle_seed": ...,
        "b_brain_result": ...,
    }
```

분리 후 `_run_orchestration_core` 는 **얇은 와이어링**만 남는다(소리새 훅 + DI 4콜):

```python
async def _run_orchestration_core(request, progress_callback=None):
    started_at = time.perf_counter()
    preparation = await prepare_customer_orchestration_context_service(...)
    # 소리새 엔진 훅(non-blocking) — orchestrator 잔류
    stages = await run_customer_validation_stages_service(...DI...)
    finalized = finalize_customer_validation_bundle_service(...stages 풀어서 주입...)
    return assemble_customer_orchestration_response_service(...stages+finalized...)
```

## 4. 순환 import 안전성

신규 서비스는 `finalization_service.py` 와 동일하게 **orchestrator.py 를 import 하지 않음**.
모든 orchestrator-소유 의존(템플릿/검증기/실행검증기/주문프로파일/상수)은 **호출부(orchestrator)에서 주입**.
신규 서비스 자체 import 는 stdlib(`asyncio/time/json/pathlib/typing`) + `backend.time_utils.utcnow` 뿐.

## 5. 단계별 구현 + 검증 (구현 승인 시)

각 단계 후 baseline 27 + 보안게이트 3 그린, `__module__`/응답 동등성 확인.

- **P1**: 신규 모듈 골격 + 시그니처 + `return` 번들 정의(빈 본문, 미배선). 컴파일만.
- **P2**: 인라인 ②블록을 신규 함수 본문으로 **byte 이동**(주입 인자 치환), `_run_orchestration_core` 에서 호출 배선. `__init__` export 추가.
- **P3**: 회귀 검증 — `test_orchestrator_compat_manifest_write` 등 **출력 동등성**(written_files/anchor/manifest/semantic gate 결과) 확인. 가능하면 골든 1건.
- **P4**: 문서/AGENTS 갱신, 임시 스크립트 정리.

## 6. 리스크 & 완화

| 리스크 | 완화 |
|---|---|
| 순서 의존 단계(파일 I/O·아티팩트 재기록)의 미묘한 누락 | ②블록을 **byte 이동**(재작성 금지), 주입 인자만 치환 |
| DI 인자 누락/오타(런타임 NameError) | P1 시그니처 고정 후 AST로 ②블록 자유이름 ↔ 주입 인자 매핑 검증 |
| `evidence_bundle_seed` 가변 상태가 finalize 와 공유 | 번들 반환으로 명시 전달(현재도 dict 전달이라 동치) |
| 골든 테스트 비용(LLM/시간) | 출력 동등성 단위 테스트 우선, 골든은 선택 |

## 7. 기대 효과

`_run_orchestration_core` 402줄 → ~40줄(와이어링). orchestrator.py **6.4k→~6.2k**.
중간 스테이지 시퀀스가 `customer/` 단계 서비스로 통일 → prepare/stages/finalize/assemble 4-phase 완성, 테스트 표면 명확화.
