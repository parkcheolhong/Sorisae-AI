# 오케스트레이터-자가개선-실험-즉시-실행-원본-대상-경로-C-Use-88b347d566 role separation

- document_id: GEN-DSL-001
- project_id: GEN-PROJECT-001
- profile: python_fastapi

## Auto-linked roles

- GRAPH-NODE-001 / api-entrypoint / app/main.py / TPL-PYTHON_FASTAPI-001
- GRAPH-NODE-002 / health-route / app/api/routes/health.py / TPL-PYTHON_FASTAPI-002
- GRAPH-NODE-003 / service-package-export / app/services/__init__.py / TPL-PYTHON_FASTAPI-003
- GRAPH-NODE-004 / runtime-service / app/services/runtime_service.py / TPL-PYTHON_FASTAPI-004
- GRAPH-NODE-005 / runtime-config / app/core/config.py / TPL-PYTHON_FASTAPI-005
- GRAPH-NODE-006 / security-guard / app/core/security.py / TPL-PYTHON_FASTAPI-006
- GRAPH-NODE-007 / upstream-status-adapter / app/external_adapters/status_client.py / TPL-PYTHON_FASTAPI-007
- GRAPH-NODE-008 / multi-role-orchestrator / app/agents/orchestrator_roles.py / TPL-PYTHON_FASTAPI-008
- GRAPH-NODE-009 / health-test / tests/test_health.py / TPL-PYTHON_FASTAPI-009
- GRAPH-NODE-010 / file-manifest / docs/file_manifest.md / TPL-PYTHON_FASTAPI-010
- GRAPH-NODE-011 / orchestrator-checklist / docs/orchestrator_checklist.md / TPL-PYTHON_FASTAPI-011
- GRAPH-NODE-012 / output-audit / docs/output_audit.json / TPL-PYTHON_FASTAPI-012
- GRAPH-NODE-013 / artifact-ledger / docs/orchestrator_artifacts.json / TPL-PYTHON_FASTAPI-013
- GRAPH-NODE-014 / traceability-map / docs/traceability_map.json / TPL-PYTHON_FASTAPI-014
- GRAPH-NODE-015 / auto-link-map / docs/auto_link_map.json / TPL-PYTHON_FASTAPI-015
- GRAPH-NODE-016 / architecture-contract / docs/architecture.contract.json / TPL-PYTHON_FASTAPI-016
- GRAPH-NODE-017 / role-separation / docs/role_separation.md / TPL-PYTHON_FASTAPI-017
- GRAPH-NODE-018 / generator-checklist / docs/generator_checklist.md / TPL-PYTHON_FASTAPI-018
- GRAPH-NODE-019 / multi-role-contract / docs/multi_role_contract.json / TPL-PYTHON_FASTAPI-019
- GRAPH-NODE-020 / operational-readiness / docs/operational_readiness.md / TPL-PYTHON_FASTAPI-020
- GRAPH-NODE-021 / template-contract / .codeai-template.json / TPL-PYTHON_FASTAPI-021

## Template bindings

- BIND-001 => GRAPH-NODE-001 => app/main.py
- BIND-002 => GRAPH-NODE-002 => app/api/routes/health.py
- BIND-003 => GRAPH-NODE-003 => app/services/__init__.py
- BIND-004 => GRAPH-NODE-004 => app/services/runtime_service.py
- BIND-005 => GRAPH-NODE-005 => app/core/config.py
- BIND-006 => GRAPH-NODE-006 => app/core/security.py
- BIND-007 => GRAPH-NODE-007 => app/external_adapters/status_client.py
- BIND-008 => GRAPH-NODE-008 => app/agents/orchestrator_roles.py
- BIND-009 => GRAPH-NODE-009 => tests/test_health.py
- BIND-010 => GRAPH-NODE-010 => docs/file_manifest.md
- BIND-011 => GRAPH-NODE-011 => docs/orchestrator_checklist.md
- BIND-012 => GRAPH-NODE-012 => docs/output_audit.json
- BIND-013 => GRAPH-NODE-013 => docs/orchestrator_artifacts.json
- BIND-014 => GRAPH-NODE-014 => docs/traceability_map.json
- BIND-015 => GRAPH-NODE-015 => docs/auto_link_map.json
- BIND-016 => GRAPH-NODE-016 => docs/architecture.contract.json
- BIND-017 => GRAPH-NODE-017 => docs/role_separation.md
- BIND-018 => GRAPH-NODE-018 => docs/generator_checklist.md
- BIND-019 => GRAPH-NODE-019 => docs/multi_role_contract.json
- BIND-020 => GRAPH-NODE-020 => docs/operational_readiness.md
- BIND-021 => GRAPH-NODE-021 => .codeai-template.json

## Quality gates

- required-files-present
- service-package-contract
- multi-role-contract-generated
- auto-link-map-generated

## [운영 주의] app/ 패키지 역할 명시 — 2026-05-01

### 위치

저장소 루트 `app/` 디렉토리

### 역할

`app/`은 __헌법 규칙 적합성 참조용 패키지__이며 __운영 진입점이 아니다.__

- 실제 운영 서비스 진입점: `backend/main.py` (docker-compose.yml 기준)
- `app/`은 생성기 템플릿 계약(`app/services/__init__.py` + `app/services/runtime_service.py`)을 유지하기 위한 참조 구조로만 존재한다.
- `docker-compose.yml`의 backend 서비스는 `backend/main.py`만 기동하며, `app/`은 컨테이너에 별도 마운트되지 않는다.

### 금지 사항

- `app/services` 단일 모듈 파일을 만드는 것을 __금지__한다. 반드시 `app/services/` 패키지 구조(`__init__.py` + `runtime_service.py`)를 유지해야 한다.
- 신규 기여자가 `app/main.py`를 실제 API 진입점으로 수정하거나 compose에 추가하면 안 된다.

### 헌법 규칙 연계

`.github/copilot-instructions.md` 기준: `app/services` 단일 모듈과 `app/services/` 패키지 구조 동시 유지 금지. Python 생성 산출물 기준은 `app/services/__init__.py`와 `app/services/runtime_service.py`로 통일.

- architecture-contract-generated
- role-separation-generated
- generator-checklist-generated
- output-audit-generated
- traceability-generated
- self-configurable-settings
- syntax-verifiable
