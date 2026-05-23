# FILE-ID: FILE-APP-ORDER-PROFILE-PY
# SECTION-ID: SECTION-APP-ORDER-PROFILE-PY-MAIN
# FEATURE-ID: FEATURE-APP-ORDER-PROFILE-PY-RUNTIME
# CHUNK-ID: CHUNK-APP-ORDER-PROFILE-PY-001

import json

ORDER_PROFILE = json.loads(r'''{
  "profile_id": "automation_service",
  "label": "업무 자동화/에이전트 서비스",
  "summary": "작업 큐, 실행 기록, 스케줄, 경고를 포함하는 주문형 프로그램",
  "keywords": [
    "자동화",
    "workflow",
    "agent",
    "봇",
    "scheduler",
    "queue",
    "pipeline",
    "etl"
  ],
  "entities": [
    "jobs",
    "runs",
    "alerts",
    "artifacts",
    "ai_features",
    "model_versions",
    "inference_runs",
    "evaluation_reports"
  ],
  "requested_outcomes": [
    "잡 등록",
    "실행 추적",
    "경고 수집",
    "결과물 아카이브",
    "AI 엔진 구성",
    "학습 파이프라인",
    "추론 런타임",
    "평가 리포트",
    "전략/업무 서비스 연동"
  ],
  "ui_modules": [
    "작업 큐",
    "실행 히스토리",
    "알림 패널",
    "산출물 뷰어",
    "AI 상태 패널",
    "모델 버전 뷰",
    "평가 리포트 카드"
  ],
  "requested_stack": [
    "FastAPI",
    "queue-runtime",
    "ops-panel",
    "ai-engine",
    "training-pipeline",
    "model-registry"
  ],
  "project_name": "오케스트레이터-자가개선-실험-즉시-실행-원본-대상-경로-C-Use-88b347d566",
  "task_excerpt": "오케스트레이터 자가개선 실험 즉시 실행\n\n원본 대상 경로: C:\\Users\\WORK\\source\\repos\\parkcheolhong\\codeAI\n실험 복제본 경로: C:\\Users\\WORK\\source\\repos\\parkcheolhong\\codeAI\\uploads\\tmp\\codeai_admin_runtime\\admin_self_experiments\\codeAI_20260423_025814\n실행 모드: full\n\n[반드시 지킬 ",
  "flow_steps": [
    {
      "flow_id": "FLOW-001",
      "step_number": 1,
      "step_id": "FLOW-001-1",
      "action": "INTAKE",
      "title": "주문 해석",
      "trace_id": "FLOW-001:FLOW-001-1:INTAKE"
    },
    {
      "flow_id": "FLOW-001",
      "step_number": 2,
      "step_id": "FLOW-001-2",
      "action": "STRUCTURE",
      "title": "기능 구조화",
      "trace_id": "FLOW-001:FLOW-001-2:STRUCTURE"
    },
    {
      "flow_id": "FLOW-002",
      "step_number": 1,
      "step_id": "FLOW-002-1",
      "action": "SERVICE_BIND",
      "title": "서비스 연결",
      "trace_id": "FLOW-002:FLOW-002-1:SERVICE_BIND"
    },
    {
      "flow_id": "FLOW-003",
      "step_number": 1,
      "step_id": "FLOW-003-1",
      "action": "DELIVERY",
      "title": "산출물 패키징",
      "trace_id": "FLOW-003:FLOW-003-1:DELIVERY"
    }
  ],
  "validation_profile": "python_fastapi",
  "ai_enabled": true,
  "mandatory_engine_contracts": [
    "engine-core",
    "feature-pipeline",
    "training-pipeline",
    "inference-runtime",
    "evaluation-report",
    "service-integration"
  ],
  "ai_capabilities": [
    "feature-engineering",
    "model-training",
    "online-inference",
    "evaluation-report",
    "service-integration"
  ],
  "stage_chain": [
    {
      "index": 1,
      "tracking_id": "ARCH-001",
      "title": "구조",
      "summary": "프로젝트 골조와 실행 엔트리를 고정합니다."
    },
    {
      "index": 2,
      "tracking_id": "ARCH-002",
      "title": "순수 로직",
      "summary": "핵심 계산과 판정 로직을 분리합니다."
    },
    {
      "index": 3,
      "tracking_id": "ARCH-003",
      "title": "데이터",
      "summary": "입출력 계약과 데이터 공급 레이어를 분리합니다."
    },
    {
      "index": 4,
      "tracking_id": "ARCH-004",
      "title": "서비스",
      "summary": "로직과 데이터를 묶는 서비스 흐름을 구성합니다."
    },
    {
      "index": 5,
      "tracking_id": "ARCH-005",
      "title": "API",
      "summary": "외부 요청과 서비스 연결을 구성합니다."
    },
    {
      "index": 6,
      "tracking_id": "ARCH-006",
      "title": "프론트",
      "summary": "화면, 상태 표현, 시각화를 연결합니다."
    }
  ],
  "current_stage": {
    "index": 1,
    "tracking_id": "ARCH-001",
    "title": "구조",
    "summary": "프로젝트 골조와 실행 엔트리를 고정합니다."
  }
}''')

def get_order_profile() -> dict:
    return dict(ORDER_PROFILE)

def list_flow_steps() -> list[dict]:
    return [dict(item) for item in ORDER_PROFILE.get('flow_steps', [])]

def get_flow_step(step_id: str) -> dict | None:
    for item in ORDER_PROFILE.get('flow_steps', []):
        if item.get('step_id') == step_id:
            return dict(item)
    return None
