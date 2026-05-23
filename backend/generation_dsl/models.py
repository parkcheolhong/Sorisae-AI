from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class DslNode:
    id: str
    kind: str
    name: str
    role: str
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class GenerationDslDocument:
    document_id: str
    project_id: str
    project_name: str
    profile: str
    task: str
    runtime: str
    nodes: List[DslNode]
    quality_gates: List[str]
    safety_hooks: List[str]

    def summary(self) -> Dict[str, object]:
        return {
            "document_id": self.document_id,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "profile": self.profile,
            "runtime": self.runtime,
            "node_count": len(self.nodes),
            "quality_gates": list(self.quality_gates),
            "safety_hooks": list(self.safety_hooks),
        }
