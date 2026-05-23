# FILE-ID: FILE-BACKEND-CORE-FLOW-REGISTRY-PY
# SECTION-ID: SECTION-BACKEND-CORE-FLOW-REGISTRY-PY-MAIN
# FEATURE-ID: FEATURE-BACKEND-CORE-FLOW-REGISTRY-PY-RUNTIME
# CHUNK-ID: CHUNK-BACKEND-CORE-FLOW-REGISTRY-PY-001

FLOW_REGISTRY = [
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
]

def list_registered_steps() -> list[dict]:
    return [dict(item) for item in FLOW_REGISTRY]

def find_registered_step(step_id: str) -> dict | None:
    for item in FLOW_REGISTRY:
        if item.get('step_id') == step_id:
            return dict(item)
    return None
