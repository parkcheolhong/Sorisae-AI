from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.marketplace import models


REPO_ROOT = Path(models.__file__).resolve().parents[2]
WORKSPACE_ROOT_SCOPE_KEY = "."
PROJECT_MEMORY_MODEL = getattr(models, "AdminOrchestratorProjectMemory", None)
EXPERIMENT_MODEL = getattr(models, "AdminOrchestratorExperimentRecord", None)
APPROVAL_GATE_MODEL = getattr(models, "AdminOrchestratorApprovalGateRecord", None)
GLOBAL_APPROVAL_POLICY_MODEL = getattr(models, "AdminOrchestratorGlobalApprovalPolicy", None)


def _safe_json_load_dict(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    text = str(raw or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _safe_json_load_list(raw: Any) -> List[Any]:
    if isinstance(raw, list):
        return list(raw)
    text = str(raw or "").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except Exception:
        return []
    return parsed if isinstance(parsed, list) else []


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def normalize_project_root(project_root: str) -> str:
    raw = str(project_root or "").strip().replace("\\", "/")
    if not raw:
        return ""
    repo_root = str(REPO_ROOT).replace("\\", "/")
    normalized = raw
    if normalized.lower().startswith(repo_root.lower()):
        normalized = normalized[len(repo_root):].lstrip("/")
    elif normalized.lower().startswith("/app/"):
        normalized = normalized[len("/app/"):]
    else:
        parts = [part for part in normalized.split("/") if part]
        lowered_parts = [part.lower() for part in parts]
        if "codeai" in lowered_parts:
            index = lowered_parts.index("codeai")
            normalized = "/".join(parts[index + 1:])
    return normalized.strip("/")


def is_workspace_root_scope(value: Any) -> bool:
    raw = str(value or "").strip().replace("\\", "/")
    normalized = normalize_project_root(raw)
    return raw in {"", ".", "/", "/app"} or normalized == ""


def _normalize_global_policy_scope_entries(values: List[Any]) -> List[str]:
    normalized_items: List[str] = []
    for value in values:
        raw = str(value or "").strip()
        if not raw:
            continue
        if is_workspace_root_scope(raw):
            normalized_key = WORKSPACE_ROOT_SCOPE_KEY
        else:
            normalized_key = normalize_project_root(raw)
        if not normalized_key:
            normalized_key = WORKSPACE_ROOT_SCOPE_KEY
        if normalized_key not in normalized_items:
            normalized_items.append(normalized_key)
    return normalized_items


def _normalize_global_policy_blocked_paths(values: List[Any]) -> List[str]:
    normalized_items: List[str] = []
    for value in values:
        raw = str(value or "").strip()
        if not raw or is_workspace_root_scope(raw):
            continue
        normalized_key = normalize_project_root(raw) or raw.replace("\\", "/").strip("/")
        if normalized_key in {"frontend", "frontend/frontend"}:
            continue
        if normalized_key and normalized_key not in normalized_items:
            normalized_items.append(normalized_key)
    return normalized_items


def _normalize_global_policy_record(
    representative_project_root: Any,
    scope: List[Any],
    blocked_paths: List[Any],
    validation_rules: List[Any],
) -> Dict[str, Any]:
    normalized_rules = [str(item).strip() for item in validation_rules if str(item).strip()]
    whole_project_rule = "workspace self-run 은 전체 프로젝트 루트 기준으로만 실행"
    if whole_project_rule not in normalized_rules:
        normalized_rules.append(whole_project_rule)
    return {
        "representative_project_root": WORKSPACE_ROOT_SCOPE_KEY,
        "scope": [WORKSPACE_ROOT_SCOPE_KEY],
        "blocked_paths": _normalize_global_policy_blocked_paths(blocked_paths),
        "validation_rules": normalized_rules,
    }


def _keyword_priority_boost(text: str) -> int:
    lowered = str(text or "").lower()
    score = 50
    keyword_weights = {
        "보안": 25,
        "security": 25,
        "오류": 20,
        "error": 20,
        "실패": 18,
        "failure": 18,
        "인증": 16,
        "auth": 16,
        "테스트": 14,
        "test": 14,
        "실험": 12,
        "experiment": 12,
        "확장": 10,
        "extension": 10,
        "개선": 9,
        "improve": 9,
        "구현": 8,
        "implement": 8,
        "디버그": 12,
        "debug": 12,
    }
    for keyword, weight in keyword_weights.items():
        if keyword in lowered:
            score += weight
    return min(score, 100)


def compute_priority_tasks(
    memory: Dict[str, Any],
    experiments: List[Dict[str, Any]],
    approval_gate: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    priorities: List[Dict[str, Any]] = []
    seen_titles: set[str] = set()

    def append_task(title: str, reason: str, source: str, priority: int, ready: bool = True) -> None:
        normalized_title = str(title or "").strip()
        if not normalized_title or normalized_title in seen_titles:
            return
        seen_titles.add(normalized_title)
        priorities.append(
            {
                "title": normalized_title,
                "reason": reason,
                "source": source,
                "priority": max(1, min(int(priority), 100)),
                "ready": bool(ready),
            }
        )

    remembered_goal = str(memory.get("remembered_goal") or "").strip()
    if remembered_goal:
        append_task(
            title=f"핵심 목표 유지: {remembered_goal[:80]}",
            reason="현재 프로젝트의 장기 목표를 기준으로 다음 작업 우선순위를 정렬합니다.",
            source="goal",
            priority=_keyword_priority_boost(remembered_goal),
        )

    for pending_task in [str(item).strip() for item in (memory.get("pending_tasks") or []) if str(item).strip()]:
        append_task(
            title=pending_task,
            reason="프로젝트 메모리에 남은 작업으로 기록되어 있습니다.",
            source="pending_task",
            priority=_keyword_priority_boost(pending_task),
        )

    if experiments:
        latest_experiment = experiments[0]
        if not bool(latest_experiment.get("applied")):
            append_task(
                title="최근 실험 결과 반영 여부 결정",
                reason="최근 실험이 아직 코드나 설정에 반영되지 않았습니다.",
                source="experiment",
                priority=92,
            )

    gate_status = str((approval_gate or {}).get("status") or "review_required").strip() or "review_required"
    if gate_status != "approved":
        append_task(
            title="자가확장 승인 게이트 확인",
            reason="자동 구현 전에 승인 범위와 금지 영역, 검증 조건을 먼저 맞춰야 합니다.",
            source="approval_gate",
            priority=95,
            ready=False,
        )

    priorities.sort(key=lambda item: (-int(item.get("priority") or 0), str(item.get("title") or "")))
    return priorities[:8]


def _serialize_experiment(record: Any) -> Dict[str, Any]:
    raw_evidence = record.evidence_json
    parsed_evidence: Any
    try:
        parsed_evidence = json.loads(str(raw_evidence or "[]"))
    except Exception:
        parsed_evidence = []
    return {
        "id": record.id,
        "project_root": record.project_root,
        "hypothesis": str(record.hypothesis or ""),
        "method": str(record.method or ""),
        "result_summary": str(record.result_summary or ""),
        "conclusion": str(record.conclusion or ""),
        "applied": bool(record.applied),
        "evidence": parsed_evidence,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


def _serialize_approval_gate(record: Optional[Any]) -> Dict[str, Any]:
    if record is None:
        return {
            "status": "review_required",
            "scope": [],
            "blocked_paths": [],
            "validation_rules": [],
            "rationale": "",
            "updated_at": None,
        }
    return {
        "id": record.id,
        "status": str(record.status or "review_required"),
        "scope": _safe_json_load_list(record.scope_json),
        "blocked_paths": _safe_json_load_list(record.blocked_paths_json),
        "validation_rules": _safe_json_load_list(record.validation_rules_json),
        "rationale": str(record.rationale or ""),
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


def _serialize_global_policy(record: Optional[models.AdminOrchestratorGlobalApprovalPolicy]) -> Dict[str, Any]:
    if record is None:
        return {
            "representative_project_root": "",
            "status": "review_required",
            "scope": [],
            "blocked_paths": [],
            "validation_rules": [],
            "rationale": "",
            "is_active": False,
            "updated_at": None,
        }
    return {
        "id": record.id,
        "representative_project_root": str(record.representative_project_root or ""),
        "status": str(record.status or "review_required"),
        "scope": _safe_json_load_list(record.scope_json),
        "blocked_paths": _safe_json_load_list(record.blocked_paths_json),
        "validation_rules": _safe_json_load_list(record.validation_rules_json),
        "rationale": str(record.rationale or ""),
        "is_active": bool(record.is_active),
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


def get_active_global_approval_policy(db: Session) -> Dict[str, Any]:
    if GLOBAL_APPROVAL_POLICY_MODEL is None:
        return _serialize_global_policy(None)
    row = (
        db.query(GLOBAL_APPROVAL_POLICY_MODEL)
        .filter(GLOBAL_APPROVAL_POLICY_MODEL.is_active.is_(True))
        .order_by(GLOBAL_APPROVAL_POLICY_MODEL.updated_at.desc(), GLOBAL_APPROVAL_POLICY_MODEL.created_at.desc())
        .first()
    )
    if row is not None:
        normalized = _normalize_global_policy_record(
            row.representative_project_root,
            _safe_json_load_list(row.scope_json),
            _safe_json_load_list(row.blocked_paths_json),
            _safe_json_load_list(row.validation_rules_json),
        )
        changed = (
            str(row.representative_project_root or "") != normalized["representative_project_root"]
            or _safe_json_load_list(row.scope_json) != normalized["scope"]
            or _safe_json_load_list(row.blocked_paths_json) != normalized["blocked_paths"]
            or _safe_json_load_list(row.validation_rules_json) != normalized["validation_rules"]
        )
        if changed:
            row.representative_project_root = normalized["representative_project_root"]
            row.scope_json = _json_text(normalized["scope"])
            row.blocked_paths_json = _json_text(normalized["blocked_paths"])
            row.validation_rules_json = _json_text(normalized["validation_rules"])
            db.add(row)
            db.commit()
            db.refresh(row)
    return _serialize_global_policy(row)


def get_project_context_bundle(db: Session, project_root: str) -> Dict[str, Any]:
    normalized_root = normalize_project_root(project_root)
    memory_row = None
    if normalized_root and PROJECT_MEMORY_MODEL is not None:
        memory_row = (
            db.query(PROJECT_MEMORY_MODEL)
            .filter(PROJECT_MEMORY_MODEL.project_root == normalized_root)
            .first()
        )
    experiments = [
        _serialize_experiment(item)
        for item in (
            db.query(EXPERIMENT_MODEL)
            .filter(EXPERIMENT_MODEL.project_root == normalized_root)
            .order_by(EXPERIMENT_MODEL.created_at.desc())
            .limit(10)
            .all()
            if normalized_root and EXPERIMENT_MODEL is not None else []
        )
    ]
    approval_row = None
    if normalized_root and APPROVAL_GATE_MODEL is not None:
        approval_row = (
            db.query(APPROVAL_GATE_MODEL)
            .filter(APPROVAL_GATE_MODEL.project_root == normalized_root)
            .order_by(APPROVAL_GATE_MODEL.updated_at.desc(), APPROVAL_GATE_MODEL.created_at.desc())
            .first()
        )
    approval_gate = _serialize_approval_gate(approval_row)
    memory = _safe_json_load_dict(memory_row.memory_json if memory_row else {})
    if memory_row:
        if memory_row.project_name and not memory.get("project_name"):
            memory["project_name"] = memory_row.project_name
        if memory_row.remembered_goal and not memory.get("remembered_goal"):
            memory["remembered_goal"] = memory_row.remembered_goal
    if normalized_root and not memory.get("project_root"):
        memory["project_root"] = normalized_root
    priority_tasks = compute_priority_tasks(memory, experiments, approval_gate)
    if memory_row and PROJECT_MEMORY_MODEL is not None:
        memory_row.priority_tasks_json = _json_text(priority_tasks)
        db.add(memory_row)
        db.commit()
        db.refresh(memory_row)
    return {
        "project_root": normalized_root,
        "memory": memory,
        "experiments": experiments,
        "approval_gate": approval_gate,
        "global_approval_policy": get_active_global_approval_policy(db),
        "priority_tasks": priority_tasks,
        "updated_at": memory_row.updated_at.isoformat() if memory_row and memory_row.updated_at else None,
    }


def upsert_project_memory_snapshot(
    db: Session,
    *,
    project_root: str,
    memory: Dict[str, Any],
    approval_gate: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    normalized_root = normalize_project_root(project_root)
    if not normalized_root:
        return {
            "project_root": "",
            "memory": dict(memory or {}),
            "experiments": [],
            "approval_gate": approval_gate or _serialize_approval_gate(None),
            "priority_tasks": [],
            "updated_at": None,
        }
    if PROJECT_MEMORY_MODEL is None:
        return get_project_context_bundle(db, normalized_root)

    row = (
        db.query(PROJECT_MEMORY_MODEL)
        .filter(PROJECT_MEMORY_MODEL.project_root == normalized_root)
        .first()
    )
    if row is None:
        row = PROJECT_MEMORY_MODEL(project_root=normalized_root)
    next_memory = dict(memory or {})
    next_memory["project_root"] = normalized_root
    row.project_name = str(next_memory.get("project_name") or "").strip() or None
    row.remembered_goal = str(next_memory.get("remembered_goal") or "").strip() or None
    row.memory_json = _json_text(next_memory)
    approval_payload = approval_gate if approval_gate is not None else get_project_context_bundle(db, normalized_root).get("approval_gate")
    experiments = get_project_context_bundle(db, normalized_root).get("experiments")
    priority_tasks = compute_priority_tasks(next_memory, experiments, approval_payload)
    row.priority_tasks_json = _json_text(priority_tasks)
    db.add(row)
    db.commit()
    db.refresh(row)
    return get_project_context_bundle(db, normalized_root)


def append_experiment_record(
    db: Session,
    *,
    project_root: str,
    hypothesis: str,
    method: str,
    result_summary: str,
    conclusion: str,
    applied: bool,
    evidence: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    normalized_root = normalize_project_root(project_root)
    if EXPERIMENT_MODEL is None:
        return get_project_context_bundle(db, normalized_root)

    record = EXPERIMENT_MODEL(
        project_root=normalized_root,
        hypothesis=str(hypothesis or "").strip(),
        method=str(method or "").strip(),
        result_summary=str(result_summary or "").strip(),
        conclusion=str(conclusion or "").strip(),
        applied=bool(applied),
        evidence_json=_json_text(evidence or []),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _serialize_experiment(record)


def enrich_experiment_with_debug_validation(
    db: Session,
    *,
    project_root: str,
    debug_profile: Dict[str, Any],
    verification_items: List[Dict[str, Any]],
    traceback_text: str,
) -> Dict[str, Any]:
    bundle = get_project_context_bundle(db, project_root)
    experiments = list(bundle.get("experiments") or [])
    if not experiments:
        return bundle
    latest = experiments[0]
    latest["debug_profile"] = debug_profile
    latest["verification_items"] = verification_items
    latest["traceback_text"] = traceback_text[-4000:] if traceback_text else ""
    if EXPERIMENT_MODEL is None:
        return bundle
    row = (
        db.query(EXPERIMENT_MODEL)
        .filter(EXPERIMENT_MODEL.id == latest.get("id"))
        .first()
    )
    if row is not None:
        row.evidence_json = _json_text({
            "evidence": latest.get("evidence") or [],
            "debug_profile": debug_profile,
            "verification_items": verification_items,
            "traceback_text": latest.get("traceback_text") or "",
        })
        db.add(row)
        db.commit()
    return get_project_context_bundle(db, project_root)


def append_approval_gate_record(
    db: Session,
    *,
    project_root: str,
    status: str,
    scope: List[str],
    blocked_paths: List[str],
    validation_rules: List[str],
    rationale: str,
) -> Dict[str, Any]:
    normalized_root = normalize_project_root(project_root)
    if APPROVAL_GATE_MODEL is None:
        return _serialize_approval_gate(None)

    record = APPROVAL_GATE_MODEL(
        project_root=normalized_root,
        status=str(status or "review_required").strip() or "review_required",
        scope_json=_json_text(scope),
        blocked_paths_json=_json_text(blocked_paths),
        validation_rules_json=_json_text(validation_rules),
        rationale=str(rationale or "").strip(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _serialize_approval_gate(record)


def upsert_global_approval_policy(
    db: Session,
    *,
    representative_project_root: str,
    status: str,
    scope: List[str],
    blocked_paths: List[str],
    validation_rules: List[str],
    rationale: str,
) -> Dict[str, Any]:
    if GLOBAL_APPROVAL_POLICY_MODEL is None:
        return _serialize_global_policy(None)

    active_rows = db.query(GLOBAL_APPROVAL_POLICY_MODEL).all()
    for row in active_rows:
        row.is_active = False
        db.add(row)

    normalized = _normalize_global_policy_record(
        representative_project_root,
        scope,
        blocked_paths,
        validation_rules,
    )

    record = GLOBAL_APPROVAL_POLICY_MODEL(
        representative_project_root=normalized["representative_project_root"],
        status=str(status or "review_required").strip() or "review_required",
        scope_json=_json_text(normalized["scope"]),
        blocked_paths_json=_json_text(normalized["blocked_paths"]),
        validation_rules_json=_json_text(normalized["validation_rules"]),
        rationale=str(rationale or "").strip(),
        is_active=True,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _serialize_global_policy(record)
