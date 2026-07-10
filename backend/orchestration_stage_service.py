from __future__ import annotations

from datetime import datetime

from backend.time_utils import utcnow
from pathlib import Path
from secrets import token_urlsafe
from typing import Any, Dict, List, Optional
import json


_STAGE_RUN_ROOT = Path(__file__).resolve().parent.parent / "uploads" / "tmp" / "orchestration_stage_runs"


ORCHESTRATION_STAGE_DEFINITIONS: List[Dict[str, str]] = [
    {"id": "ARCH-001", "label": "1단계", "title": "구조 설계", "summary": "요구사항, 구조, 책임 경계를 먼저 고정합니다."},
    {"id": "ARCH-002", "label": "2단계", "title": "폴더 및 기초 구현", "summary": "폴더 배치, 엔트리, 기본 실행 파일을 생성합니다."},
    {"id": "ARCH-003", "label": "3단계", "title": "설계반영된 골조구현", "summary": "설계를 반영한 골조와 레이어 연결을 맞춥니다."},
    {"id": "ARCH-004", "label": "4단계", "title": "핵심엔진 구성", "summary": "핵심 엔진 계약과 모듈 흐름을 구성합니다."},
    {"id": "ARCH-0045", "label": "4.5단계", "title": "Refiner/Fixer", "summary": "핵심엔진 직후 로직 진입 전에 구조 정리, 계약 보정, 자동 수정 안전고리를 닫습니다."},
    {"id": "ARCH-005", "label": "5단계", "title": "로직(ID식별)", "summary": "핵심 로직과 ID 식별 규칙을 고정합니다."},
    {"id": "ARCH-006", "label": "6단계", "title": "데이터", "summary": "데이터 계약, 스키마, 공급 레이어를 연결합니다."},
    {"id": "ARCH-007", "label": "7단계", "title": "서비스", "summary": "서비스 레이어와 상태 전이를 조립합니다."},
    {"id": "ARCH-008", "label": "8단계", "title": "API", "summary": "요청/응답 계약과 엔드포인트를 연결합니다."},
    {"id": "ARCH-009", "label": "9단계", "title": "프론트", "summary": "화면, 상태 표현, 최종 사용자 동선을 마감합니다."},
    {"id": "ARCH-010", "label": "10단계", "title": "운영 협업/검증", "summary": "운영 협업 대화, 검색 지시, 중간 설계 변경, 최종 검증/재개 흐름을 고정합니다."},
]

ORCHESTRATION_STAGE_SUBSTEP_LIBRARY: Dict[str, List[Dict[str, Any]]] = {
    "ARCH-001": [
        {"id": "ARCH-001-CARD-01", "title": "요구사항 정규화", "summary": "자연어 요구를 구조/기능/제약으로 분리합니다.", "idea_template": "사용자 목표, 핵심 사용자, 금지사항을 3줄로 추가하세요.", "edit_template": "요구사항 누락 시 범위/제약/출력물을 다시 적으세요."},
        {"id": "ARCH-001-CARD-02", "title": "역할 경계 설계", "summary": "데이터/서비스/API/프론트 책임 경계를 고정합니다.", "idea_template": "레이어 간 직접 호출 금지 규칙을 보강하세요.", "edit_template": "역할 충돌 시 어느 레이어 책임인지 다시 고정하세요."},
        {"id": "ARCH-001-CARD-03", "title": "ID 자동연결 설계", "summary": "architecture/flow/step/action ID 연결을 정의합니다.", "idea_template": "추적해야 할 ID 조합을 추가하세요.", "edit_template": "누락된 연결 키를 보완하세요."},
    ],
    "ARCH-002": [
        {"id": "ARCH-002-CARD-01", "title": "폴더 골조 생성", "summary": "최소 실행 폴더 구조를 세웁니다.", "idea_template": "필수 폴더/파일을 더 추가하세요.", "edit_template": "비어 있거나 중복된 골조를 정리하세요."},
        {"id": "ARCH-002-CARD-02", "title": "엔트리 포인트 연결", "summary": "실행 진입점과 기본 설정 파일을 연결합니다.", "idea_template": "부팅에 필요한 설정 키를 추가하세요.", "edit_template": "엔트리 경로 오류를 수정하세요."},
    ],
    "ARCH-003": [
        {"id": "ARCH-003-CARD-01", "title": "골조 반영", "summary": "설계 문서를 코드 골조로 반영합니다.", "idea_template": "추가 skeleton 파일을 제안하세요.", "edit_template": "설계와 어긋난 파일을 바로잡으세요."},
        {"id": "ARCH-003-CARD-02", "title": "인터페이스 연결", "summary": "레이어 간 인터페이스를 최소 구현합니다.", "idea_template": "필요한 함수 시그니처를 추가하세요.", "edit_template": "누락된 인터페이스를 보정하세요."},
    ],
    "ARCH-004": [
        {"id": "ARCH-004-CARD-01", "title": "핵심 엔진 계약", "summary": "도메인 핵심 엔진 계약과 흐름을 고정합니다.", "idea_template": "핵심 엔진 capability를 추가하세요.", "edit_template": "엔진 계약 누락 지점을 수정하세요."},
        {"id": "ARCH-004-CARD-02", "title": "안전고리 삽입", "summary": "실패 시 차단 장치를 같이 심습니다.", "idea_template": "하드 게이트 조건을 추가하세요.", "edit_template": "약한 안전고리를 강화하세요."},
    ],
    "ARCH-0045": [
        {"id": "ARCH-0045-CARD-01", "title": "구조 정리", "summary": "핵심엔진 직후 중복·죽은 경로·느슨한 책임을 정리합니다.", "idea_template": "정리해야 할 중복 경로나 느슨한 책임을 추가하세요.", "edit_template": "구조 충돌과 중복 파일을 제거하세요."},
        {"id": "ARCH-0045-CARD-02", "title": "계약 보정 및 자동 수정", "summary": "로직 단계 진입 전에 필수 계약, import, 안전고리를 보정합니다.", "idea_template": "보정해야 할 계약/검증 규칙을 추가하세요.", "edit_template": "누락된 계약, import, 안전고리를 수정하세요."},
    ],
    "ARCH-005": [
        {"id": "ARCH-005-CARD-01", "title": "ID 규칙 구현", "summary": "logic/action/trace 식별 규칙을 코드에 반영합니다.", "idea_template": "추적 필드를 추가하세요.", "edit_template": "누락된 ID 필드를 채우세요."},
        {"id": "ARCH-005-CARD-02", "title": "로직 흐름 고정", "summary": "단계별 순차 흐름을 로직에 반영합니다.", "idea_template": "순서 제약을 추가하세요.", "edit_template": "건너뛴 로직 단계를 복구하세요."},
    ],
    "ARCH-006": [
        {"id": "ARCH-006-CARD-01", "title": "데이터 계약", "summary": "스키마와 데이터 계약을 확정합니다.", "idea_template": "필수 필드/검증 규칙을 추가하세요.", "edit_template": "잘못된 스키마 연결을 수정하세요."},
        {"id": "ARCH-006-CARD-02", "title": "공급 레이어 연결", "summary": "데이터 공급/저장 경로를 잇습니다.", "idea_template": "추가 데이터 소스를 제안하세요.", "edit_template": "데이터 공급 누락을 수정하세요."},
    ],
    "ARCH-007": [
        {"id": "ARCH-007-CARD-01", "title": "서비스 조립", "summary": "서비스 레이어를 유일한 조합 지점으로 유지합니다.", "idea_template": "서비스 조립 규칙을 추가하세요.", "edit_template": "API/로직 직접 결합을 제거하세요."},
        {"id": "ARCH-007-CARD-02", "title": "상태 전이", "summary": "상태 전이와 예외 흐름을 명시합니다.", "idea_template": "상태 전이 규칙을 보강하세요.", "edit_template": "누락된 예외 전이를 추가하세요."},
    ],
    "ARCH-008": [
        {"id": "ARCH-008-CARD-01", "title": "API 계약", "summary": "요청/응답 계약과 상태코드를 고정합니다.", "idea_template": "추가 엔드포인트를 제안하세요.", "edit_template": "응답 형식 불일치를 수정하세요."},
        {"id": "ARCH-008-CARD-02", "title": "보안/검증", "summary": "API 검증과 인증 흐름을 점검합니다.", "idea_template": "추가 인증 정책을 적으세요.", "edit_template": "권한 검증 누락을 수정하세요."},
    ],
    "ARCH-009": [
        {"id": "ARCH-009-CARD-01", "title": "UI 카드 반영", "summary": "단계 상태와 결과를 카드 UI로 표시합니다.", "idea_template": "추가 표시 카드나 필드를 적으세요.", "edit_template": "누락된 상태 표시를 수정하세요."},
        {"id": "ARCH-009-CARD-02", "title": "반자동 진행 UX", "summary": "한 단계 통과 후 다음 카드로 넘어가는 UX를 고정합니다.", "idea_template": "다음 카드 추천 문구를 추가하세요.", "edit_template": "단계 전환 UX를 수정하세요."},
    ],
    "ARCH-010": [
        {"id": "ARCH-010-CARD-01", "title": "협업 대화 연결", "summary": "오케스트레이터와 병렬 동료형 대화 흐름을 묶습니다.", "idea_template": "질문/검색/뉴스/설계 변경 프롬프트를 추가하세요.", "edit_template": "협업 대화가 끊기면 연결 규칙을 보정하세요."},
        {"id": "ARCH-010-CARD-02", "title": "중간 설계 변경/재개", "summary": "중간 수정 요청과 보정 메모를 반영한 뒤 단계 진행을 재개합니다.", "idea_template": "pause/resume/revise 규칙을 추가하세요.", "edit_template": "중간 설계 변경이 stage run에 남도록 수정하세요."},
    ],
}


def _build_stage_substeps(stage_id: str, current_stage_id: str, created_at: str) -> List[Dict[str, Any]]:
    definitions = ORCHESTRATION_STAGE_SUBSTEP_LIBRARY.get(stage_id, [])
    substeps: List[Dict[str, Any]] = []
    for index, definition in enumerate(definitions, start=1):
        substeps.append({
            **definition,
            "sequence": index,
            "status": "running" if stage_id == current_stage_id and index == 1 else "pending",
            "check_label": "진행 중" if stage_id == current_stage_id and index == 1 else "대기",
            "note": "",
            "updated_at": created_at,
            "checked": False,
            "revision_history": [],
        })
    return substeps


def _now_iso() -> str:
    return utcnow().isoformat() + "Z"


def _stage_run_path(run_id: str) -> Path:
    _STAGE_RUN_ROOT.mkdir(parents=True, exist_ok=True)
    return _STAGE_RUN_ROOT / f"{run_id}.json"


def get_stage_definition(stage_id: str) -> Optional[Dict[str, str]]:
    normalized = str(stage_id or "").strip().upper()
    for stage in ORCHESTRATION_STAGE_DEFINITIONS:
        if stage["id"] == normalized:
            return dict(stage)
    return None


def get_next_stage_id(stage_id: str) -> str:
    ids = [item["id"] for item in ORCHESTRATION_STAGE_DEFINITIONS]
    normalized = str(stage_id or "").strip().upper()
    if normalized not in ids:
        return ""
    index = ids.index(normalized)
    if index >= len(ids) - 1:
        return ""
    return ids[index + 1]


def initialize_stage_run(*, scope: str, project_name: str, mode: str, requested_by: Optional[Dict[str, Any]] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    run_id = f"stage_run_{token_urlsafe(18)}"
    created_at = _now_iso()
    stages: List[Dict[str, Any]] = []
    for index, definition in enumerate(ORCHESTRATION_STAGE_DEFINITIONS, start=1):
        stages.append({
            **definition,
            "sequence": index,
            "status": "running" if index == 1 else "pending",
            "check_label": "진행 중" if index == 1 else "대기",
            "note": "",
            "manual_correction": "",
            "updated_at": created_at,
            "substeps": _build_stage_substeps(definition["id"], ORCHESTRATION_STAGE_DEFINITIONS[0]["id"], created_at),
        })

    payload = {
        "run_id": run_id,
        "scope": scope,
        "project_name": project_name,
        "mode": mode,
        "semi_auto_step_count": len(ORCHESTRATION_STAGE_DEFINITIONS),
        "semi_auto_mode": "manual_10step",
        "command_modes": ["/run", "/pass", "/fix", "/fail", "/verify", "/search", "/news", "/ask", "/revise", "/resume"],
        "collaboration_modes": ["directive", "research", "news", "companion", "revision"],
        "status": "running",
        "current_stage_id": ORCHESTRATION_STAGE_DEFINITIONS[0]["id"],
        "final_completed": False,
        "requested_by": requested_by or {},
        "metadata": metadata or {},
        "created_at": created_at,
        "updated_at": created_at,
        "stages": stages,
    }
    _stage_run_path(run_id).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def load_stage_run(run_id: str) -> Optional[Dict[str, Any]]:
    path = _stage_run_path(run_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_stage_run(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload["updated_at"] = _now_iso()
    _stage_run_path(str(payload.get("run_id") or "")).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def update_stage_run(
    *,
    run_id: str,
    stage_id: str,
    status: str,
    note: str = "",
    manual_correction: str = "",
    substep_checks: Optional[Dict[str, bool]] = None,
    revision_note: str = "",
) -> Dict[str, Any]:
    payload = load_stage_run(run_id)
    if not payload:
        raise ValueError("stage run not found")

    normalized_stage_id = str(stage_id or "").strip().upper()
    normalized_status = str(status or "pending").strip().lower()
    valid_statuses = {"pending", "running", "passed", "failed", "manual_correction"}
    if normalized_status not in valid_statuses:
        raise ValueError("invalid stage status")

    found = False
    stages = payload.get("stages") or []
    now = _now_iso()
    for stage in stages:
        if str(stage.get("id") or "").upper() != normalized_stage_id:
            continue
        stage["status"] = normalized_status
        stage["check_label"] = {
            "pending": "대기",
            "running": "진행 중",
            "passed": "통과",
            "failed": "미통과",
            "manual_correction": "수동 보정 필요",
        }[normalized_status]
        stage["note"] = note
        stage["manual_correction"] = manual_correction
        stage["updated_at"] = now
        substeps = list(stage.get("substeps") or [])
        if substeps:
            checks_lookup = {
                str(key): bool(value)
                for key, value in (substep_checks or {}).items()
            }
            for substep in substeps:
                if substep.get("id") in checks_lookup:
                    substep["checked"] = checks_lookup[str(substep.get("id"))]
                if normalized_status == "passed":
                    substep["status"] = "passed"
                    substep["check_label"] = "통과"
                    substep["checked"] = True
                elif normalized_status == "failed":
                    substep["status"] = "failed"
                    substep["check_label"] = "미통과"
                elif normalized_status == "manual_correction":
                    substep["status"] = "manual_correction"
                    substep["check_label"] = "수정 필요"
                    substep["note"] = manual_correction or note
                else:
                    substep["status"] = "running"
                    substep["check_label"] = "진행 중"
                if revision_note.strip() or manual_correction.strip() or note.strip():
                    history = list(substep.get("revision_history") or [])
                    history.append({
                        "at": now,
                        "status": normalized_status,
                        "note": revision_note.strip() or manual_correction.strip() or note.strip(),
                    })
                    substep["revision_history"] = history[-10:]
                substep["updated_at"] = now
        found = True
        break

    if not found:
        raise ValueError("stage not found")

    if normalized_status == "passed":
        next_stage_id = get_next_stage_id(normalized_stage_id)
        payload["current_stage_id"] = next_stage_id
        if next_stage_id:
            for stage in stages:
                if stage.get("id") == next_stage_id and stage.get("status") == "pending":
                    stage["status"] = "running"
                    stage["check_label"] = "진행 중"
                    stage["updated_at"] = now
                    substeps = list(stage.get("substeps") or [])
                    for index, substep in enumerate(substeps, start=1):
                        substep["status"] = "running" if index == 1 else "pending"
                        substep["check_label"] = "진행 중" if index == 1 else "대기"
                        substep["checked"] = False
                        substep["updated_at"] = now
                    break
            payload["status"] = "running"
            payload["final_completed"] = False
        else:
            payload["status"] = "completed"
            payload["final_completed"] = True
    elif normalized_status in {"failed", "manual_correction"}:
        payload["current_stage_id"] = normalized_stage_id
        payload["status"] = "blocked"
        payload["final_completed"] = False
    elif normalized_status == "running":
        payload["current_stage_id"] = normalized_stage_id
        payload["status"] = "running"
        payload["final_completed"] = False

    return save_stage_run(payload)


def build_stage_tracking_payload(stage_id: str) -> Dict[str, str]:
    definition = get_stage_definition(stage_id)
    if not definition:
        return {}
    next_stage_id = get_next_stage_id(stage_id)
    sequence = next((index for index, item in enumerate(ORCHESTRATION_STAGE_DEFINITIONS, start=1) if item["id"] == definition["id"]), 1)
    return {
        "architecture_id": definition["id"],
        "flow_id": f"FLOW-009-{sequence:02d}",
        "step_id": definition["id"],
        "action": f"STAGE_{definition['id'].replace('-', '_')}",
        "next_architecture_id": next_stage_id or "END",
        "next_step_id": next_stage_id or "END",
        "next_action": f"STAGE_{next_stage_id.replace('-', '_')}" if next_stage_id else "END",
    }
