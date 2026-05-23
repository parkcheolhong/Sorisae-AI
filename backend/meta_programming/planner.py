from __future__ import annotations

from typing import Dict, List

from backend.generators.python_contract_registry import get_python_profile_target_paths
from backend.generation_dsl.models import GenerationDslDocument

from .models import ProjectGraph, ProjectGraphEdge, ProjectGraphNode


PROFILE_TARGET_PATHS: Dict[str, Dict[str, str]] = {
    "python_fastapi": get_python_profile_target_paths("python_fastapi"),
    "python_worker": get_python_profile_target_paths("python_worker"),
    "generic": get_python_profile_target_paths("generic"),
}


def build_project_graph(document: GenerationDslDocument) -> ProjectGraph:
    profile_paths = PROFILE_TARGET_PATHS.get(document.profile, PROFILE_TARGET_PATHS["generic"])
    nodes: List[ProjectGraphNode] = []
    edges: List[ProjectGraphEdge] = []
    previous_node_id = ""
    for index, dsl_node in enumerate(document.nodes, start=1):
        target_path = profile_paths.get(dsl_node.name, profile_paths.get("main", "main.py"))
        node_id = f"GRAPH-NODE-{index:03d}"
        nodes.append(
            ProjectGraphNode(
                id=node_id,
                source_dsl_id=dsl_node.id,
                role=dsl_node.role,
                target_path=target_path,
                template_id=f"TPL-{document.profile.upper()}-{index:03d}",
                metadata={
                    "auto_link_key": dsl_node.metadata.get("auto_link_key", ""),
                    "kind": dsl_node.kind,
                    "layer": dsl_node.metadata.get("layer", ""),
                    "contract_target_path": dsl_node.metadata.get("target_path", target_path),
                },
            )
        )
        if previous_node_id:
            edges.append(
                ProjectGraphEdge(
                    id=f"GRAPH-EDGE-{index - 1:03d}",
                    source_id=previous_node_id,
                    target_id=node_id,
                    relation="auto-link",
                )
            )
        previous_node_id = node_id
    return ProjectGraph(
        graph_id="GRAPH-001",
        project_id=document.project_id,
        profile=document.profile,
        nodes=nodes,
        edges=edges,
    )
