from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]
ID_REGISTRY_SCHEMA_RELATIVE = "docs/id_registry.schema.json"
SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".md", ".txt", ".sh", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".env", ".go", ".rs"}
BACKFILL_DISCOVERY_ROOT = Path("uploads") / "projects"


def _normalized_relative(path: Path) -> str:
    return str(path).replace("\\", "/")


def _parse_explicit_targets(raw: str) -> list[str]:
    value = raw.strip()
    if not value:
        return []
    if value.startswith("["):
        parsed = json.loads(value)
        return [_normalized_relative(Path(str(item).strip())) for item in parsed if str(item).strip()]
    parts = [item.strip() for item in re.split(r"[\r\n,]+", value) if item.strip()]
    return [_normalized_relative(Path(item)) for item in parts]


def discover_backfill_targets() -> list[str]:
    explicit_targets = _parse_explicit_targets(os.getenv("CODEAI_BACKFILL_TARGETS", ""))
    if explicit_targets:
        return explicit_targets

    discovery_root = ROOT / BACKFILL_DISCOVERY_ROOT
    if not discovery_root.exists():
        return []

    targets: list[str] = []
    for child in sorted(discovery_root.iterdir(), key=lambda item: item.name):
        if not child.is_dir():
            continue
        if not (child / ".codeai-template.json").exists():
            continue
        if not (child / "docs" / "traceability_map.json").exists():
            continue
        targets.append(_normalized_relative(child.relative_to(ROOT)))
    return targets


def _build_id(prefix: str, value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", str(value or "").upper()).strip("-") or "UNKNOWN"
    return f"{prefix}-{normalized}"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _decorate_source_file(root: Path, relative_path: str) -> None:
    normalized = str(relative_path).replace("\\", "/").strip()
    if not normalized or normalized.startswith("docs/"):
        return
    path = root / normalized
    if not path.exists() or path.suffix.lower() not in SOURCE_SUFFIXES:
        return
    content = path.read_text(encoding="utf-8")
    file_stub = re.sub(r"[^A-Za-z0-9]+", "-", normalized.upper()).strip("-") or "GENERATED-FILE"
    section_stub = f"SECTION-{file_stub}-MAIN"
    feature_stub = f"FEATURE-{file_stub}-RUNTIME"
    chunk_stub = f"CHUNK-{file_stub}-001"
    if path.suffix.lower() in {".ts", ".tsx", ".js", ".jsx", ".css", ".scss"}:
        header = (
            f"/* FILE-ID: FILE-{file_stub} */\n"
            f"/* SECTION-ID: {section_stub} */\n"
            f"/* FEATURE-ID: {feature_stub} */\n"
            f"/* CHUNK-ID: {chunk_stub} */\n\n"
        )
        if "FILE-ID:" not in content[:200]:
            path.write_text(header + content, encoding="utf-8")
        return
    header = (
        f"# FILE-ID: FILE-{file_stub}\n"
        f"# SECTION-ID: {section_stub}\n"
        f"# FEATURE-ID: {feature_stub}\n"
        f"# CHUNK-ID: {chunk_stub}\n\n"
    )
    if not content.startswith("# FILE-ID:"):
        path.write_text(header + content, encoding="utf-8")


def _layer_for_path(relative_path: str) -> str:
    normalized = relative_path.replace("\\", "/")
    if normalized.startswith("app/") or normalized.startswith("backend/"):
        if "router" in normalized or "/api/" in normalized:
            return "backend-router"
        if "/service" in normalized or "/services/" in normalized:
            return "backend-service"
        if "/repository" in normalized:
            return "backend-repository"
        if "/infra/" in normalized:
            return "backend-infra"
        if "/worker" in normalized:
            return "backend-worker"
        if normalized.endswith("main.py"):
            return "backend-entry"
        return "backend-orchestrator"
    if normalized.startswith("frontend/"):
        if "/components/" in normalized:
            return "frontend-component"
        if "/lib/" in normalized:
            return "frontend-lib"
        return "frontend-page"
    if normalized.startswith("tests/"):
        return "test"
    if normalized.startswith("docs/"):
        return "docs"
    return "generated-template"


def _iter_target_files(written_files: Iterable[str]) -> list[str]:
    return [
        str(item).replace("\\", "/")
        for item in written_files
        if str(item).strip() and not str(item).replace("\\", "/").startswith("docs/")
    ]


def _build_id_registry(project_name: str, written_files: list[str]) -> dict:
    files = []
    traceability_links = []
    for index, relative_path in enumerate(_iter_target_files(written_files), start=1):
        file_id = _build_id("FILE", relative_path)
        section_id = _build_id("SECTION", f"{relative_path}-main")
        feature_id = _build_id("FEATURE", relative_path)
        chunk_id = _build_id("CHUNK", f"{relative_path}-001")
        files.append(
            {
                "file_id": file_id,
                "path": relative_path,
                "layer": _layer_for_path(relative_path),
                "summary": f"{relative_path} 소급 보정 산출물",
                "owner_capabilities": [feature_id.replace("FEATURE-", "feature-").lower()],
                "selective_apply_ready": True,
                "sections": [
                    {
                        "section_id": section_id,
                        "summary": f"{relative_path} 메인 섹션",
                        "feature_ids": [feature_id],
                        "chunks": [
                            {
                                "chunk_id": chunk_id,
                                "summary": f"{relative_path} 소급 보정 청크",
                                "stability": "stable",
                                "targetable": True,
                                "failure_tags": [],
                                "repair_tags": [],
                            }
                        ],
                    }
                ],
            }
        )
        traceability_links.append(
            {
                "trace_id": _build_id("TRACE", f"{project_name}-{index:03d}"),
                "design_item_id": _build_id("DESIGN", relative_path),
                "target_file_ids": [file_id],
                "target_section_ids": [section_id],
                "target_feature_ids": [feature_id],
                "target_chunk_ids": [chunk_id],
                "validation_evidence": [relative_path],
                "approval_status": "backfilled",
            }
        )
    return {
        "$schema": "./id_registry.schema.json",
        "schema_version": "id-registry.v1",
        "registry_id": _build_id("REG", project_name),
        "generated_at": datetime.now().isoformat(),
        "project": {
            "project_id": _build_id("PROJECT", project_name),
            "name": project_name,
            "root_path": ".",
            "scope": "generated-output",
        },
        "governance": {
            "required_documents": [
                "docs/id_registry.schema.json",
                "docs/id_registry.json",
                "docs/product_identity.json",
                "docs/traceability_map.json",
                "docs/auto_link_map.json",
                "docs/architecture.contract.json",
                "docs/generator_checklist.md",
            ],
            "required_id_levels": ["file", "section", "feature", "chunk", "flow", "trace", "failure_tag", "repair_tag"],
            "selective_apply_policy": "id-targeted-only",
            "future_generation_mandatory": True,
        },
        "files": files,
        "flows": [],
        "traceability_links": traceability_links,
        "failure_tags": [],
        "repair_tags": [],
        "validation_rules": {
            "hard_gate": [
                "모든 신규 소스 파일은 FILE-ID registry 항목이 있어야 한다.",
                "핵심 섹션은 SECTION-ID 와 최소 1개 CHUNK-ID를 가져야 한다.",
                "생성 프로그램은 docs/id_registry.json 과 docs/product_identity.json 을 반드시 포함해야 한다.",
            ],
            "generation_requirements": ["retrofit-backfill", "top10-program-only"],
        },
    }


def _build_product_identity(project_name: str) -> dict:
    return {
        "schema_version": "product-identity.v1",
        "product_id": _build_id("PID", project_name),
        "project_id": _build_id("PROJECT", project_name),
        "project_name": project_name,
        "profile": "python_fastapi",
        "runtime": "compat",
        "identity_policy": {
            "mandatory": True,
            "description": "생성 제품의 고유 인식표(주민번호 수준 식별자)입니다.",
        },
        "identity_links": {
            "id_registry_path": "docs/id_registry.json",
            "traceability_map_path": "docs/traceability_map.json",
            "auto_link_map_path": "docs/auto_link_map.json",
        },
    }


def backfill_target(target_relative: str) -> dict:
    target_root = ROOT / target_relative
    template_path = target_root / ".codeai-template.json"
    traceability_path = target_root / "docs" / "traceability_map.json"
    if not template_path.exists() or not traceability_path.exists():
        raise FileNotFoundError(target_relative)
    template_payload = _read_json(template_path)
    traceability_payload = _read_json(traceability_path)
    project_name = str(template_payload.get("project_name") or target_root.name)
    written_files = list(traceability_payload.get("written_files") or [])
    schema_source = ROOT / ID_REGISTRY_SCHEMA_RELATIVE
    schema_target = target_root / ID_REGISTRY_SCHEMA_RELATIVE
    schema_target.parent.mkdir(parents=True, exist_ok=True)
    schema_target.write_text(schema_source.read_text(encoding="utf-8"), encoding="utf-8")
    id_registry_payload = _build_id_registry(project_name, written_files)
    product_identity_payload = _build_product_identity(project_name)
    _write_json(target_root / "docs" / "id_registry.json", id_registry_payload)
    _write_json(target_root / "docs" / "product_identity.json", product_identity_payload)
    for relative_path in _iter_target_files(written_files):
        _decorate_source_file(target_root, relative_path)
    return {
        "target": target_relative,
        "project_name": project_name,
        "written_files": len(written_files),
        "source_markers_backfilled": len(_iter_target_files(written_files)),
    }


def main() -> None:
    targets = discover_backfill_targets()
    results = [backfill_target(target) for target in targets]
    report_path = ROOT / "uploads" / "tmp" / "retrofit_backfill_report.json"
    _write_json(
        report_path,
        {
            "generated_at": datetime.now().isoformat(),
            "targets": targets,
            "count": len(results),
            "results": results,
        },
    )
    print(report_path)


if __name__ == "__main__":
    main()
