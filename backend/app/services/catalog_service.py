from __future__ import annotations


def list_catalog_items() -> list[dict]:
    return [
        {
            "catalog_id": "runtime-core",
            "name": "Runtime Core",
            "status": "ready",
        },
        {
            "catalog_id": "ops-observability",
            "name": "Ops Observability",
            "status": "ready",
        },
    ]