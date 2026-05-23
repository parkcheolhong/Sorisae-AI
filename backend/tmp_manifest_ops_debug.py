from backend.llm.orchestrator import (
    _build_customer_order_profile,
    _compat_build_manifest_lookup,
    _compat_domain_required_files,
    _compat_manifest_for_request,
    _compat_run_semantic_gate,
)


def main() -> None:
    task = "FastAPI 기반 운영형 샘플 서비스를 생성하고 hard gate 산출물 consistency를 확인한다. health API, docs 산출물, traceability map, output audit를 포함하라."
    project = "hard-gate-consistency-rerun-container"
    order_profile = _build_customer_order_profile(task, project)
    required = _compat_domain_required_files(order_profile, "python_fastapi")
    anchor, manifest, state = _compat_manifest_for_request(task, project, "python_fastapi", required)
    lookup = _compat_build_manifest_lookup(manifest)
    content = lookup.get("app/ops_routes.py", "")
    print("PROFILE", order_profile.get("profile_id"), order_profile.get("ai_enabled"))
    print("ANCHOR", anchor)
    print("STATE", state)
    print("HAS_METRICS", "@ops_router.get('/metrics')" in content)
    print("CONTENT_START")
    print(content[:1500])
    print("CONTENT_END")
    gate = _compat_run_semantic_gate(task, project, order_profile, "python_fastapi", manifest)
    print("GATE_OK", gate.get("ok"))
    print("CHECKLIST", gate.get("checklist"))


if __name__ == "__main__":
    main()
