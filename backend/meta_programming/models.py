from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class ProjectGraphNode:
    id: str
    source_dsl_id: str
    role: str
    target_path: str
    template_id: str
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ProjectGraphEdge:
    id: str
    source_id: str
    target_id: str
    relation: str


@dataclass(frozen=True)
class ProjectGraph:
    graph_id: str
    project_id: str
    profile: str
    nodes: List[ProjectGraphNode]
    edges: List[ProjectGraphEdge]

    def auto_link_map(self) -> Dict[str, object]:
        return {
            "graph_id": self.graph_id,
            "project_id": self.project_id,
            "nodes": [node.__dict__ for node in self.nodes],
            "edges": [edge.__dict__ for edge in self.edges],
        }
