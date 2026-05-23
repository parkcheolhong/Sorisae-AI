# 오케스트레이터-자가개선-실험-즉시-실행-원본-대상-경로-C-Use-88b347d566 operational readiness

- profile: python_fastapi
- runtime: fastapi
- multi_role_count: 21

## Required role contract

- api-entrypoint => app/main.py (entry)
- health-route => app/api/routes/health.py (api)
- service-package-export => app/services/__init__.py (service)
- runtime-service => app/services/runtime_service.py (service)
- runtime-config => app/core/config.py (config)
- security-guard => app/core/security.py (security)
- upstream-status-adapter => app/external_adapters/status_client.py (adapter)
- multi-role-orchestrator => app/agents/orchestrator_roles.py (agent)
- health-test => tests/test_health.py (test)
- file-manifest => docs/file_manifest.md (meta)
- orchestrator-checklist => docs/orchestrator_checklist.md (meta)
- output-audit => docs/output_audit.json (meta)
- artifact-ledger => docs/orchestrator_artifacts.json (meta)
- traceability-map => docs/traceability_map.json (meta)
- auto-link-map => docs/auto_link_map.json (governance)
- architecture-contract => docs/architecture.contract.json (governance)
- role-separation => docs/role_separation.md (governance)
- generator-checklist => docs/generator_checklist.md (governance)
- multi-role-contract => docs/multi_role_contract.json (governance)
- operational-readiness => docs/operational_readiness.md (governance)
- template-contract => .codeai-template.json (template)

## Quality gates

- [ ] required-files-present
- [ ] service-package-contract
- [ ] multi-role-contract-generated
- [ ] auto-link-map-generated
- [ ] architecture-contract-generated
- [ ] role-separation-generated
- [ ] generator-checklist-generated
- [ ] output-audit-generated
- [ ] traceability-generated
- [ ] self-configurable-settings
- [ ] syntax-verifiable

## Safety hooks

- [x] id-based-auto-link
- [x] role-separation-contract
- [x] service-package-export
- [x] multi-role-orchestrator
- [x] security-baseline
- [x] status-adapter-default
- [x] generation-checklist
- [x] runtime-entrypoint-check
