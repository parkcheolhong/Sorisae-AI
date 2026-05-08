# 전체 설계변경 요약 및 PR 본문 초안

## 문서 목적
- 현재 저장소 문서 기준으로 전체 설계변경 내용을 한 번에 검토할 수 있도록 정리한다.
- 바로 복사해 사용할 수 있는 실제 PR 본문 초안을 남긴다.
- 설계변경 요약과 PR 설명의 근거 문서를 함께 묶어 추적 가능하게 유지한다.

## 근거 문서
- `README.md`
- `docs/orchestrator-multigenerator-upgrade-status.md`
- `docs/final_readiness_checklist.md`
- `docs/admin-dashboard-ui-ux-browser-blueprint.md`
- `docs/admin-dashboard-section-linkage-checklist.md`
- `gpu-llm-server/reports/pr-body-2026-04-27.md`

---

## 1. 전체 설계변경 요약

### 1-1. 플랫폼 운영 구조 재정렬
- 공개 메인 앱과 관리자 앱의 운영 기준을 분리했다.
- 공개 메인 앱은 `frontend`, 관리자 앱은 `frontend/frontend` 기준으로 정렬했다.
- 운영 진입 경로를 `marketplace`, `admin`, `/api/llm/ws` 중심으로 고정했다.
- 운영 판정은 단순 구현 여부가 아니라 운영 경로 실검증 기준으로 묶었다.

### 1-2. 오케스트레이터 및 멀티 생성기 계약 단일화
- Python 산출물 서비스 구조를 `app/services/__init__.py`, `app/services/runtime_service.py` 패키지 기준으로 통일했다.
- 레거시 `app/services.py` 단일 파일 기준과 신규 패키지 기준이 동시에 유지되지 않도록 계약을 정렬했다.
- 템플릿, 검증기, 체크리스트, capability 진단 규칙이 같은 서비스 패키지 기준을 보도록 재정리했다.

### 1-3. 생성 직후 hard gate 검증 체계 강화
- 생성 직후 결과물 폴더에서 의존성 설치, 단독 기동, 핵심 API 호출, 테스트, ZIP 재현 검증까지 한 흐름으로 묶었다.
- readiness checklist, semantic gate, completion gate, packaging audit, output audit의 연결 구조를 강화했다.
- 산출물 문서와 운영 증거가 분리되지 않도록 `final_readiness_checklist.md` 중심의 판정 체계를 유지했다.

### 1-4. capability evidence 및 self-run 추적 강화
- 관리자 capability 진단에 summary/detail 분리와 evidence bundle 해석을 반영했다.
- `completion_gate_ok`, `self_run_status`, `failure_tags`, `target_file_ids`, `evidence_digest` 등 추적 요약을 노출하도록 정리했다.
- self-run terminal state, `applied_to_source`, runtime artifact, operational evidence를 같은 흐름에서 확인할 수 있게 했다.

### 1-5. 운영 경로 실검증 기준 고정
- 운영 경로 검증 대상을 `admin`, `marketplace`, websocket, system settings, workspace self-run record까지 포함해 정리했다.
- 로컬 성능 및 검증 기준은 `localhost` 대신 `127.0.0.1:8000` 또는 운영 도메인 기준으로 고정했다.
- 완료 판정은 운영 경로 실검증과 readiness evidence가 함께 닫혀야만 가능하도록 유지했다.

### 1-6. 관리자 대시보드 UI/UX 구조 재설계
- 관리자 대시보드를 중앙 오케스트레이터 허브 중심 구조로 재배치했다.
- 상단 바, 히어로 액션, 중앙 런처 허브, 양측 레일, 오버레이 창형 섹션 구조를 연결했다.
- 인라인 접기 카드 위주 화면에서 운영자가 실제 제어에 집중할 수 있는 실행형 패널 구조로 전환했다.

### 1-7. 신규 생성 프로그램의 운영형 기본 규칙 확대
- 새로 생성되는 프로그램에도 운영형 설정, 보안 파일, 상태 클라이언트, 최소 코드량, self-configurable 검증 규칙을 공통 적용하는 방향으로 확장했다.
- 단순 스캐폴드가 아니라 운영 준비도와 검증 문서까지 포함하는 생성기 구조를 목표 상태로 정리했다.

---

## 2. 실제 PR 제목 제안

### 추천 제목
`오케스트레이터·멀티 생성기·운영 검증 체계 전면 정렬 및 관리자 UI 구조 재설계`

### 대안 제목
- `생성기 계약 단일화와 hard gate 검증 체계 정렬, 관리자 허브 UI 재설계`
- `운영형 오케스트레이터 증거 체계 정렬 및 admin/marketplace 검증 구조 고도화`

---

## 3. 실제 PR 본문 초안

## Summary

This PR consolidates the repository-wide design changes into a single operational baseline. It aligns the public/admin runtime structure, unifies the generator contract around the `app/services/` package layout, strengthens post-generation hard-gate validation, and reorganizes the admin dashboard into an operator-centric orchestration hub. It also ties readiness evidence, self-run traces, and operational verification into a single reviewable flow.

## Why

- The generator contract, validation rules, and documentation needed to follow the same service-package standard.
- Completion status needed to be grounded in real operational evidence instead of partial implementation signals.
- Post-generation validation needed to verify dependency install, standalone boot, core API health, tests, and ZIP reproduction as one closed gate.
- The admin dashboard needed to shift from scattered inline sections to a workflow-centered control hub that exposes actionable evidence.

## Scope Of Changes

### 1. Runtime / Platform Structure
- Reaffirmed split operation between the public main app and the admin app.
- Kept operational routing focused on `marketplace`, `admin`, and `/api/llm/ws`.
- Synchronized runtime interpretation with the documented production entry points.

### 2. Generator Contract Unification
- Standardized Python service outputs on:
  - `app/services/__init__.py`
  - `app/services/runtime_service.py`
- Removed contract ambiguity between legacy single-file service references and package-based service structure.
- Kept templates, validators, checklists, and capability diagnostics aligned to the same package contract.

### 3. Hard-Gate Validation Baseline
- Strengthened the closed validation path executed immediately after generation:
  - dependency installation
  - standalone boot
  - core API smoke
  - test execution
  - ZIP reproduction verification
- Preserved semantic gate, completion gate, packaging audit, and readiness checklist linkage.
- Kept `final_readiness_checklist.md` as the central review artifact for closure.

### 4. Capability Evidence / Self-Run Traceability
- Expanded capability summary/detail separation and evidence bundle interpretation.
- Surfaced evidence-oriented fields such as:
  - `completion_gate_ok`
  - `self_run_status`
  - `failure_tags`
  - `target_file_ids`
  - `evidence_digest`
- Connected self-run terminal status and `applied_to_source` evidence to the admin-facing review flow.

### 5. Operational Verification Standards
- Kept operational verification centered on real production paths, including admin, marketplace, websocket, system-settings, and workspace self-run record flows.
- Kept local verification baselines on `127.0.0.1:8000` or the production domain rather than `localhost`.
- Maintained the rule that completion status requires operational evidence, not just code presence.

### 6. Admin Dashboard UX Redesign
- Reorganized the admin screen around a central orchestration hub.
- Connected top actions, hero actions, launcher tiles, inline surfaces, and modal/overlay sections into a more operator-focused UI.
- Shifted away from dense inline foldable cards toward a clearer action-and-control workflow.

### 7. Operational-Grade Output Defaults
- Extended generator expectations so newly produced applications follow operational-grade defaults rather than bare scaffolds.
- Preserved expectations for security/runtime/status components and stronger output quality gates.

## Validation Basis

- Operational readiness and completion status are documented in `docs/final_readiness_checklist.md`.
- Orchestrator and multi-generator alignment details are documented in `docs/orchestrator-multigenerator-upgrade-status.md`.
- Admin dashboard UX restructuring basis is documented in:
  - `docs/admin-dashboard-ui-ux-browser-blueprint.md`
  - `docs/admin-dashboard-section-linkage-checklist.md`
- Documentation-only baseline validation for this update:
  - `npm --prefix frontend/frontend run test`

## Risks

- Tightening contract alignment can expose stale references in secondary documents or auxiliary diagnostic paths.
- Evidence-first completion criteria can downgrade previously tolerated partial states into explicit blockers.
- Admin dashboard workflow changes may alter operator navigation expectations until the new hub pattern is fully internalized.

## Rollback Strategy

- Roll back documentation and PR narrative independently if wording or scope grouping needs refinement.
- If a runtime/design interpretation needs to be reverted, restore the corresponding baseline in the status/readiness documents first so the repository does not present mismatched closure criteria.
- Preserve the service-package contract and evidence-based completion rule unless a repository-wide alternative standard is intentionally adopted.

## Reviewer Focus

- Verify that generator, validator, checklist, and capability documentation all describe the same `app/services/` package contract.
- Check that hard-gate validation is represented as a closed operational path rather than a partial quality signal.
- Review whether the admin dashboard redesign description accurately matches the current launcher-hub and overlay-window structure.
- Confirm that completion claims stay anchored to documented operational evidence.

## Notes For Release / Reporting

- This PR body is intended as a consolidated reporting layer for the current repository baseline.
- It is suitable for follow-up release notes, readiness reviews, or status reports that need one narrative covering generator structure, operational verification, and admin UI direction.

---

## 4. 짧은 PR 본문 버전

## Summary
- 공개/관리자 운영 구조를 재정렬하고 생성기 계약을 `app/services/` 패키지 기준으로 단일화했다.
- 생성 직후 hard gate 검증, readiness checklist, self-run evidence, operational verification 흐름을 같은 판정 체계로 묶었다.
- 관리자 화면을 중앙 오케스트레이터 허브 기반 구조로 정리해 운영 제어와 증거 확인 흐름을 강화했다.

## Validation
- `docs/final_readiness_checklist.md`
- `docs/orchestrator-multigenerator-upgrade-status.md`
- `npm --prefix frontend/frontend run test`

## Reviewer Focus
- 서비스 패키지 계약 정합성
- hard gate 및 readiness evidence 표현 정확성
- 관리자 허브 UI 설명과 실제 구조의 일치 여부
