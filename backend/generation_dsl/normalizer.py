from __future__ import annotations

from .models import DslNode, GenerationDslDocument


def normalize_generation_dsl(document: GenerationDslDocument) -> GenerationDslDocument:
    normalized_nodes = []
    for index, node in enumerate(document.nodes, start=1):
        normalized_nodes.append(
            DslNode(
                id=node.id or f"DSL-NODE-{index:03d}",
                kind=node.kind.strip().lower(),
                name=node.name.strip(),
                role=node.role.strip(),
                metadata={
                    **node.metadata,
                    "document_id": document.document_id,
                    "project_id": document.project_id,
                },
            )
        )
    return GenerationDslDocument(
        document_id=document.document_id,
        project_id=document.project_id,
        project_name=document.project_name.strip(),
        profile=document.profile.strip().lower(),
        task=document.task.strip(),
        runtime=document.runtime.strip().lower(),
        nodes=normalized_nodes,
        quality_gates=list(dict.fromkeys(document.quality_gates)),
        safety_hooks=list(dict.fromkeys(document.safety_hooks)),
    )
