from __future__ import annotations

from typing import List

from backend.generators.python_contract_registry import get_python_profile_contract

from .models import DslNode, GenerationDslDocument


def _build_nodes(profile: str) -> List[DslNode]:
    contract = get_python_profile_contract(profile)
    nodes: List[DslNode] = []
    for index, role_contract in enumerate(contract.roles, start=1):
        nodes.append(
            DslNode(
                id=f"DSL-NODE-{index:03d}",
                kind=role_contract.kind,
                name=role_contract.name,
                role=role_contract.role,
                metadata={
                    "auto_link_key": f"{role_contract.kind}:{role_contract.name}",
                    "target_path": role_contract.target_path,
                    "layer": role_contract.layer,
                },
            )
        )
    return nodes


def parse_request_to_generation_dsl(task: str, project_name: str, profile: str) -> GenerationDslDocument:
    normalized_profile = str(profile or "generic").strip().lower()
    contract = get_python_profile_contract(normalized_profile)
    return GenerationDslDocument(
        document_id="GEN-DSL-001",
        project_id="GEN-PROJECT-001",
        project_name=project_name,
        profile=normalized_profile,
        task=task,
        runtime=contract.runtime,
        nodes=_build_nodes(normalized_profile),
        quality_gates=list(contract.quality_gates),
        safety_hooks=list(contract.safety_hooks),
    )
