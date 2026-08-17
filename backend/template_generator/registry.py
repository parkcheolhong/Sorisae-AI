from __future__ import annotations

from dataclasses import dataclass
from typing import List

from backend.meta_programming.models import ProjectGraph


@dataclass(frozen=True)
class TemplateBinding:
    binding_id: str
    node_id: str
    template_id: str
    target_path: str
    role: str


def select_template_bindings(graph: ProjectGraph) -> List[TemplateBinding]:
    bindings: List[TemplateBinding] = []
    for index, node in enumerate(graph.nodes, start=1):
        bindings.append(
            TemplateBinding(
                binding_id=f"BIND-{index:03d}",
                node_id=node.id,
                template_id=node.template_id,
                target_path=node.target_path,
                role=node.role,
            )
        )
    return bindings
