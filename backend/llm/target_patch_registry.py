from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


TARGET_PATCH_REGISTRY: List[Dict[str, Any]] = [
    {
        "file_id": "FILE-ORCH-CORE",
        "path": "backend/llm/orchestrator.py",
        "section_id": "SECTION-PRODUCT-READINESS-HARD-GATE",
        "feature_id": "FEATURE-SHIPMENT-EVIDENCE",
        "chunk_id": "CHUNK-ORCH-HARD-GATE-001",
        "summary": "출고 hard gate, traceability, output audit, shipment evidence를 기록하는 핵심 조각입니다.",
        "reuse_ready": True,
        "capability_ids": ["code-generator", "self-healing-engine"],
    },
    {
        "file_id": "FILE-ADMIN-CAPABILITIES",
        "path": "backend/llm/admin_capabilities.py",
        "section_id": "SECTION-CAPABILITY-EVIDENCE-AGGREGATOR",
        "feature_id": "FEATURE-ID-BASED-TARGET-EXPOSURE",
        "chunk_id": "CHUNK-CAPABILITY-TARGET-REGISTRY-001",
        "summary": "capability가 output audit / traceability / hard gate evidence를 읽어 수정 대상 ID를 노출하는 조각입니다.",
        "reuse_ready": True,
        "capability_ids": ["code-generator", "self-healing-engine", "project-scanner"],
    },
    {
        "file_id": "FILE-ADMIN-CHAT-SERVICE",
        "path": "backend/orchestrator/chat/chat_service.py",
        "section_id": "SECTION-CONVERSATION-INTELLIGENCE",
        "feature_id": "FEATURE-TARGET-PATCH-HINTS",
        "chunk_id": "CHUNK-CONVERSATION-AI-001",
        "summary": "대화형 AI 엔진이 타겟 수정 힌트와 제안형 응답을 만드는 조각입니다.",
        "reuse_ready": True,
        "capability_ids": ["code-generator", "admin-command-interface"],
    },
    {
        "file_id": "FILE-ADMIN-LLM-PAGE",
        "path": "frontend/frontend/app/admin/llm/page.tsx",
        "section_id": "SECTION-CHAT-ADVISORY-PANEL",
        "feature_id": "FEATURE-EVIDENCE-FIRST-UX",
        "chunk_id": "CHUNK-ADMIN-CHAT-UI-001",
        "summary": "관리자 오케스트레이터 화면에서 AI 추론, hard gate, evidence, 타겟 수정 힌트를 보여주는 조각입니다.",
        "reuse_ready": True,
        "capability_ids": ["code-generator", "self-healing-engine", "admin-command-interface"],
    },
    {
        "file_id": "FILE-BACKEND-MAIN",
        "path": "backend/main.py",
        "section_id": "SECTION-ROUTER-ATTACHMENT",
        "feature_id": "FEATURE-ORCHESTRATOR-ENTRYPOINT",
        "chunk_id": "CHUNK-BACKEND-ENTRY-001",
        "summary": "오케스트레이터 및 관리자 capability 라우터를 메인 앱에 연결하는 엔트리 조각입니다.",
        "reuse_ready": True,
        "capability_ids": ["project-scanner", "dependency-graph"],
    },
]

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ID_REGISTRY_PATH = REPO_ROOT / "docs" / "id_registry.json"


def _normalize_path(value: Any) -> str:
    return str(value or "").strip().replace("\\", "/")


def _unique_ordered(values: List[Any]) -> List[str]:
    ordered: List[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _load_workspace_id_registry_entries() -> List[Dict[str, Any]]:
    if not WORKSPACE_ID_REGISTRY_PATH.exists():
        return []
    try:
        payload = json.loads(WORKSPACE_ID_REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []

    files = payload.get("files") if isinstance(payload, dict) else []
    if not isinstance(files, list):
        return []

    entries: List[Dict[str, Any]] = []
    for file_item in files:
        if not isinstance(file_item, dict):
            continue
        file_id = str(file_item.get("file_id") or "").strip()
        path = _normalize_path(file_item.get("path"))
        owner_capabilities = [
            str(item).strip()
            for item in (file_item.get("owner_capabilities") or [])
            if str(item).strip()
        ]
        sections = file_item.get("sections") if isinstance(file_item.get("sections"), list) else []
        for section in sections:
            if not isinstance(section, dict):
                continue
            section_id = str(section.get("section_id") or "").strip()
            feature_ids = [
                str(item).strip()
                for item in (section.get("feature_ids") or [])
                if str(item).strip()
            ]
            chunks = section.get("chunks") if isinstance(section.get("chunks"), list) else []
            for chunk in chunks:
                if not isinstance(chunk, dict):
                    continue
                entries.append(
                    {
                        "file_id": file_id,
                        "path": path,
                        "section_id": section_id,
                        "feature_id": feature_ids[0] if feature_ids else "",
                        "feature_ids": feature_ids,
                        "chunk_id": str(chunk.get("chunk_id") or "").strip(),
                        "summary": str(chunk.get("summary") or section.get("summary") or file_item.get("summary") or "").strip(),
                        "reuse_ready": bool(file_item.get("selective_apply_ready")) and bool(chunk.get("targetable", True)),
                        "capability_ids": owner_capabilities,
                        "failure_tags": [
                            str(item).strip()
                            for item in (chunk.get("failure_tags") or [])
                            if str(item).strip()
                        ],
                        "repair_tags": [
                            str(item).strip()
                            for item in (chunk.get("repair_tags") or [])
                            if str(item).strip()
                        ],
                        "layer": str(file_item.get("layer") or "").strip(),
                    }
                )
    return entries


def _registry_entries() -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for entry in [*TARGET_PATCH_REGISTRY, *_load_workspace_id_registry_entries()]:
        key = (
            str(entry.get("file_id") or "").strip(),
            _normalize_path(entry.get("path")),
            str(entry.get("section_id") or "").strip(),
            str(entry.get("chunk_id") or "").strip(),
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(dict(entry))
    return merged


def _match_entry(entry: Dict[str, Any], candidate_paths: List[str]) -> bool:
    entry_path = _normalize_path(entry.get("path"))
    if not entry_path:
        return False
    for candidate_path in candidate_paths:
        normalized = _normalize_path(candidate_path)
        if not normalized:
            continue
        if normalized == entry_path or normalized.endswith(entry_path) or entry_path.endswith(normalized):
            return True
    return False


def match_target_patch_registry(candidate_paths: List[str]) -> List[Dict[str, Any]]:
    normalized_candidates = [_normalize_path(item) for item in candidate_paths if _normalize_path(item)]
    matched: List[Dict[str, Any]] = []
    for entry in _registry_entries():
        if _match_entry(entry, normalized_candidates):
            matched.append(dict(entry))
    return matched


def build_target_patch_registry_snapshot(
    *,
    written_files: List[str],
    target_paths: List[str] | None = None,
    capability_ids: List[str] | None = None,
) -> Dict[str, Any]:
    candidate_paths = list(
        dict.fromkeys(
            [
                *[_normalize_path(item) for item in written_files],
                *[_normalize_path(item) for item in (target_paths or [])],
            ]
        )
    )
    matched_entries = match_target_patch_registry(candidate_paths)
    reusable_patch_units = [
        {
            "file_id": entry.get("file_id"),
            "section_id": entry.get("section_id"),
            "feature_id": entry.get("feature_id"),
            "chunk_id": entry.get("chunk_id"),
            "path": entry.get("path"),
            "failure_tags": list(entry.get("failure_tags") or []),
            "repair_tags": list(entry.get("repair_tags") or []),
        }
        for entry in matched_entries
        if bool(entry.get("reuse_ready"))
    ]
    target_file_ids = _unique_ordered([entry.get("file_id") for entry in matched_entries])
    target_section_ids = _unique_ordered([entry.get("section_id") for entry in matched_entries])
    target_feature_ids = _unique_ordered(
        [entry.get("feature_id") for entry in matched_entries]
        + [feature_id for entry in matched_entries for feature_id in (entry.get("feature_ids") or [])]
    )
    target_chunk_ids = _unique_ordered([entry.get("chunk_id") for entry in matched_entries])
    failure_tags = _unique_ordered([tag for entry in matched_entries for tag in (entry.get("failure_tags") or [])])
    repair_tags = _unique_ordered([tag for entry in matched_entries for tag in (entry.get("repair_tags") or [])])
    return {
        "registry_version": 1,
        "capability_ids": list(dict.fromkeys(str(item).strip() for item in (capability_ids or []) if str(item).strip())),
        "candidate_paths": candidate_paths,
        "matched_entries": matched_entries,
        "reusable_patch_units": reusable_patch_units,
        "target_file_ids": target_file_ids,
        "target_section_ids": target_section_ids,
        "target_feature_ids": target_feature_ids,
        "target_chunk_ids": target_chunk_ids,
        "failure_tags": failure_tags,
        "repair_tags": repair_tags,
        "matched_count": len(matched_entries),
        "reusable_count": len(reusable_patch_units),
        "selective_apply_ready": len(reusable_patch_units) > 0,
    }


def format_target_patch_candidate(entry: Dict[str, Any]) -> str:
    parts = [
        str(entry.get("file_id") or "").strip(),
        str(entry.get("section_id") or "").strip(),
        str(entry.get("feature_id") or "").strip(),
        str(entry.get("chunk_id") or "").strip(),
    ]
    compact_parts = [part for part in parts if part]
    path = _normalize_path(entry.get("path"))
    return f"{' / '.join(compact_parts)} -> {path}" if compact_parts else path


__all__ = [
    "TARGET_PATCH_REGISTRY",
    "build_target_patch_registry_snapshot",
    "format_target_patch_candidate",
    "match_target_patch_registry",
]
