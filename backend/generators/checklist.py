from __future__ import annotations

import json
import re
from typing import List

from backend.generation_dsl.models import GenerationDslDocument
from backend.generation_optimizer.scoring import GenerationScore
from backend.meta_programming.models import ProjectGraph
from backend.template_generator.registry import TemplateBinding


def _build_id(prefix: str, value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", str(value or "").upper()).strip("-") or "UNKNOWN"
    return f"{prefix}-{normalized}"


def build_auto_link_map_json(document: GenerationDslDocument, graph: ProjectGraph, bindings: List[TemplateBinding]) -> str:
    payload = {
        "document": document.summary(),
        "graph": graph.auto_link_map(),
        "bindings": [binding.__dict__ for binding in bindings],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_architecture_contract_json(document: GenerationDslDocument, graph: ProjectGraph) -> str:
    payload = {
        "contract_id": "ARCH-CONTRACT-001",
        "document_id": document.document_id,
        "project_id": document.project_id,
        "profile": document.profile,
        "runtime": document.runtime,
        "roles": [node.role for node in graph.nodes],
        "role_contracts": [
            {
                "node_id": node.id,
                "role": node.role,
                "target_path": node.target_path,
                "layer": node.metadata.get("layer", ""),
                "kind": node.metadata.get("kind", ""),
                "contract_target_path": node.metadata.get("contract_target_path", node.target_path),
            }
            for node in graph.nodes
        ],
        "target_paths": [node.target_path for node in graph.nodes],
        "safety_hooks": document.safety_hooks,
        "quality_gates": document.quality_gates,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_role_separation_markdown(document: GenerationDslDocument, graph: ProjectGraph, bindings: List[TemplateBinding]) -> str:
    lines = [
        f"# {document.project_name} role separation",
        "",
        f"- document_id: {document.document_id}",
        f"- project_id: {document.project_id}",
        f"- profile: {document.profile}",
        "",
        "## Auto-linked roles",
        "",
    ]
    for node in graph.nodes:
        lines.append(f"- {node.id} / {node.role} / {node.target_path} / {node.template_id}")
    lines.extend(["", "## Template bindings", ""])
    for binding in bindings:
        lines.append(f"- {binding.binding_id} => {binding.node_id} => {binding.target_path}")
    lines.extend(["", "## Quality gates", ""])
    for item in document.quality_gates:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def build_generator_checklist_markdown(document: GenerationDslDocument, graph: ProjectGraph, score: GenerationScore) -> str:
    lines = [
        f"# {document.project_name} generator checklist",
        "",
        f"- document_id: {document.document_id}",
        f"- graph_id: {graph.graph_id}",
        f"- generation_score: {score.score}",
        f"- generation_ok: {str(score.ok).lower()}",
        "",
        "## Required checks",
        "",
        "- [x] ID 기반 auto-link map 생성",
        "- [x] 역할 분리 문서 생성",
        "- [x] architecture contract 생성",
        "- [x] id registry 생성",
        "- [x] product identity 생성",
        "- [x] generator checklist 생성",
        "",
        "## Safety hooks",
        "",
    ]
    for item in document.safety_hooks:
        lines.append(f"- [x] {item}")
    lines.extend(["", "## Quality gate findings", ""])
    if score.checklist:
        for item in score.checklist:
            lines.append(f"- [ ] {item}")
    else:
        lines.append("- [x] all required generation artifacts present")
    return "\n".join(lines) + "\n"


def build_id_registry_json(document: GenerationDslDocument, graph: ProjectGraph, bindings: List[TemplateBinding]) -> str:
    files = []
    traceability_links = []
    for node in graph.nodes:
        file_id = _build_id("FILE", node.target_path)
        section_id = _build_id("SECTION", f"{node.target_path}-main")
        feature_id = _build_id("FEATURE", node.role)
        chunk_id = _build_id("CHUNK", f"{node.target_path}-001")
        files.append(
            {
                "file_id": file_id,
                "path": node.target_path,
                "layer": node.metadata.get("layer", "generated-template") or "generated-template",
                "summary": f"{node.role} 역할 산출물",
                "owner_capabilities": [node.role],
                "selective_apply_ready": True,
                "sections": [
                    {
                        "section_id": section_id,
                        "summary": f"{node.role} 메인 섹션",
                        "feature_ids": [feature_id],
                        "chunks": [
                            {
                                "chunk_id": chunk_id,
                                "summary": f"{node.target_path} 생성 청크",
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
                "trace_id": _build_id("TRACE", node.id),
                "design_item_id": node.source_dsl_id,
                "target_file_ids": [file_id],
                "target_section_ids": [section_id],
                "target_feature_ids": [feature_id],
                "target_chunk_ids": [chunk_id],
                "validation_evidence": [node.template_id, node.target_path],
                "approval_status": "generated",
            }
        )
    payload = {
        "$schema": "./id_registry.schema.json",
        "schema_version": "id-registry.v1",
        "registry_id": _build_id("REG", document.project_name),
        "generated_at": "generated-by-facade",
        "project": {
            "project_id": document.project_id,
            "name": document.project_name,
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
            "generation_requirements": list(document.quality_gates),
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_product_identity_json(document: GenerationDslDocument) -> str:
    payload = {
        "schema_version": "product-identity.v1",
        "product_id": _build_id("PID", document.project_name),
        "project_id": document.project_id,
        "project_name": document.project_name,
        "profile": document.profile,
        "runtime": document.runtime,
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
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
