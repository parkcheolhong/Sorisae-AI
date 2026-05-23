from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class PythonRoleContract:
    kind: str
    name: str
    role: str
    target_path: str
    layer: str
    required: bool = True


@dataclass(frozen=True)
class PythonProfileContract:
    profile: str
    runtime: str
    roles: List[PythonRoleContract]
    quality_gates: List[str]
    safety_hooks: List[str]

    @property
    def required_files(self) -> List[str]:
        return list(dict.fromkeys(role.target_path for role in self.roles if role.required))

    @property
    def core_files(self) -> List[str]:
        return [
            role.target_path
            for role in self.roles
            if role.layer in {"entry", "api", "config", "security", "service", "adapter", "agent", "test"}
            and role.required
        ]

    @property
    def meta_files(self) -> List[str]:
        return [
            role.target_path
            for role in self.roles
            if role.layer in {"meta", "governance", "template"}
            and role.required
        ]

    @property
    def target_paths(self) -> Dict[str, str]:
        return {role.name: role.target_path for role in self.roles}


PYTHON_PROFILE_CONTRACTS: Dict[str, PythonProfileContract] = {
    "python_fastapi": PythonProfileContract(
        profile="python_fastapi",
        runtime="fastapi",
        roles=[
            PythonRoleContract("entrypoint", "main", "api-entrypoint", "app/main.py", "entry"),
            PythonRoleContract("route", "health", "health-route", "app/api/routes/health.py", "api"),
            PythonRoleContract("service", "service_package", "service-package-export", "app/services/__init__.py", "service"),
            PythonRoleContract("service", "runtime_service", "runtime-service", "app/services/runtime_service.py", "service"),
            PythonRoleContract("config", "settings", "runtime-config", "app/core/config.py", "config"),
            PythonRoleContract("guard", "security", "security-guard", "app/core/security.py", "security"),
            PythonRoleContract("adapter", "status_client", "upstream-status-adapter", "app/external_adapters/status_client.py", "adapter"),
            PythonRoleContract("agent", "multi_role_registry", "multi-role-orchestrator", "app/agents/orchestrator_roles.py", "agent"),
            PythonRoleContract("test", "test_health", "health-test", "tests/test_health.py", "test"),
            PythonRoleContract("doc", "file_manifest", "file-manifest", "docs/file_manifest.md", "meta"),
            PythonRoleContract("doc", "orchestrator_checklist", "orchestrator-checklist", "docs/orchestrator_checklist.md", "meta"),
            PythonRoleContract("doc", "output_audit", "output-audit", "docs/output_audit.json", "meta"),
            PythonRoleContract("doc", "orchestrator_artifacts", "artifact-ledger", "docs/orchestrator_artifacts.json", "meta"),
            PythonRoleContract("doc", "traceability", "traceability-map", "docs/traceability_map.json", "meta"),
            PythonRoleContract("doc", "auto_link_map", "auto-link-map", "docs/auto_link_map.json", "governance"),
            PythonRoleContract("doc", "architecture_contract", "architecture-contract", "docs/architecture.contract.json", "governance"),
            PythonRoleContract("doc", "role_separation", "role-separation", "docs/role_separation.md", "governance"),
            PythonRoleContract("doc", "generator_checklist", "generator-checklist", "docs/generator_checklist.md", "governance"),
            PythonRoleContract("doc", "multi_role_contract", "multi-role-contract", "docs/multi_role_contract.json", "governance"),
            PythonRoleContract("doc", "operational_readiness", "operational-readiness", "docs/operational_readiness.md", "governance"),
            PythonRoleContract("template", "template_contract", "template-contract", ".codeai-template.json", "template"),
        ],
        quality_gates=[
            "required-files-present",
            "service-package-contract",
            "multi-role-contract-generated",
            "auto-link-map-generated",
            "architecture-contract-generated",
            "role-separation-generated",
            "generator-checklist-generated",
            "output-audit-generated",
            "traceability-generated",
            "self-configurable-settings",
            "syntax-verifiable",
        ],
        safety_hooks=[
            "id-based-auto-link",
            "role-separation-contract",
            "service-package-export",
            "multi-role-orchestrator",
            "security-baseline",
            "status-adapter-default",
            "generation-checklist",
            "runtime-entrypoint-check",
        ],
    ),
    "python_worker": PythonProfileContract(
        profile="python_worker",
        runtime="python-worker",
        roles=[
            PythonRoleContract("entrypoint", "main", "worker-entrypoint", "app/main.py", "entry"),
            PythonRoleContract("worker", "worker_runner", "worker-runner", "app/workers/runner.py", "service"),
            PythonRoleContract("service", "service_package", "service-package-export", "app/services/__init__.py", "service"),
            PythonRoleContract("service", "runtime_service", "runtime-service", "app/services/runtime_service.py", "service"),
            PythonRoleContract("config", "settings", "runtime-config", "app/core/config.py", "config"),
            PythonRoleContract("guard", "security", "security-guard", "app/core/security.py", "security"),
            PythonRoleContract("adapter", "status_client", "upstream-status-adapter", "app/external_adapters/status_client.py", "adapter"),
            PythonRoleContract("agent", "multi_role_registry", "multi-role-orchestrator", "app/agents/orchestrator_roles.py", "agent"),
            PythonRoleContract("test", "test_worker", "worker-test", "tests/test_worker.py", "test"),
            PythonRoleContract("doc", "file_manifest", "file-manifest", "docs/file_manifest.md", "meta"),
            PythonRoleContract("doc", "orchestrator_checklist", "orchestrator-checklist", "docs/orchestrator_checklist.md", "meta"),
            PythonRoleContract("doc", "output_audit", "output-audit", "docs/output_audit.json", "meta"),
            PythonRoleContract("doc", "orchestrator_artifacts", "artifact-ledger", "docs/orchestrator_artifacts.json", "meta"),
            PythonRoleContract("doc", "traceability", "traceability-map", "docs/traceability_map.json", "meta"),
            PythonRoleContract("doc", "auto_link_map", "auto-link-map", "docs/auto_link_map.json", "governance"),
            PythonRoleContract("doc", "architecture_contract", "architecture-contract", "docs/architecture.contract.json", "governance"),
            PythonRoleContract("doc", "role_separation", "role-separation", "docs/role_separation.md", "governance"),
            PythonRoleContract("doc", "generator_checklist", "generator-checklist", "docs/generator_checklist.md", "governance"),
            PythonRoleContract("doc", "multi_role_contract", "multi-role-contract", "docs/multi_role_contract.json", "governance"),
            PythonRoleContract("doc", "operational_readiness", "operational-readiness", "docs/operational_readiness.md", "governance"),
            PythonRoleContract("template", "template_contract", "template-contract", ".codeai-template.json", "template"),
        ],
        quality_gates=[
            "required-files-present",
            "service-package-contract",
            "multi-role-contract-generated",
            "worker-entrypoint-generated",
            "checklist-generated",
            "traceability-generated",
            "self-configurable-settings",
            "syntax-verifiable",
        ],
        safety_hooks=[
            "id-based-auto-link",
            "role-separation-contract",
            "service-package-export",
            "multi-role-orchestrator",
            "security-baseline",
            "status-adapter-default",
            "generation-checklist",
            "worker-entrypoint-check",
        ],
    ),
    "generic": PythonProfileContract(
        profile="generic",
        runtime="python",
        roles=[
            PythonRoleContract("entrypoint", "main", "generic-entrypoint", "app/main.py", "entry"),
            PythonRoleContract("task", "runtime_task", "runtime-task", "app/tasks/runtime_task.py", "service"),
            PythonRoleContract("service", "service_package", "service-package-export", "app/services/__init__.py", "service"),
            PythonRoleContract("service", "runtime_service", "runtime-service", "app/services/runtime_service.py", "service"),
            PythonRoleContract("config", "settings", "runtime-config", "app/core/config.py", "config"),
            PythonRoleContract("guard", "security", "security-guard", "app/core/security.py", "security"),
            PythonRoleContract("adapter", "status_client", "upstream-status-adapter", "app/external_adapters/status_client.py", "adapter"),
            PythonRoleContract("agent", "multi_role_registry", "multi-role-orchestrator", "app/agents/orchestrator_roles.py", "agent"),
            PythonRoleContract("test", "test_runtime", "runtime-test", "tests/test_runtime.py", "test"),
            PythonRoleContract("doc", "file_manifest", "file-manifest", "docs/file_manifest.md", "meta"),
            PythonRoleContract("doc", "orchestrator_checklist", "orchestrator-checklist", "docs/orchestrator_checklist.md", "meta"),
            PythonRoleContract("doc", "output_audit", "output-audit", "docs/output_audit.json", "meta"),
            PythonRoleContract("doc", "orchestrator_artifacts", "artifact-ledger", "docs/orchestrator_artifacts.json", "meta"),
            PythonRoleContract("doc", "traceability", "traceability-map", "docs/traceability_map.json", "meta"),
            PythonRoleContract("doc", "auto_link_map", "auto-link-map", "docs/auto_link_map.json", "governance"),
            PythonRoleContract("doc", "architecture_contract", "architecture-contract", "docs/architecture.contract.json", "governance"),
            PythonRoleContract("doc", "role_separation", "role-separation", "docs/role_separation.md", "governance"),
            PythonRoleContract("doc", "generator_checklist", "generator-checklist", "docs/generator_checklist.md", "governance"),
            PythonRoleContract("doc", "multi_role_contract", "multi-role-contract", "docs/multi_role_contract.json", "governance"),
            PythonRoleContract("doc", "operational_readiness", "operational-readiness", "docs/operational_readiness.md", "governance"),
            PythonRoleContract("template", "template_contract", "template-contract", ".codeai-template.json", "template"),
        ],
        quality_gates=[
            "required-files-present",
            "service-package-contract",
            "multi-role-contract-generated",
            "runtime-task-generated",
            "checklist-generated",
            "traceability-generated",
            "self-configurable-settings",
            "syntax-verifiable",
        ],
        safety_hooks=[
            "id-based-auto-link",
            "role-separation-contract",
            "service-package-export",
            "multi-role-orchestrator",
            "security-baseline",
            "status-adapter-default",
            "generation-checklist",
            "runtime-entrypoint-check",
        ],
    ),
}


DEFAULT_PYTHON_PROFILE_CONTRACT = PYTHON_PROFILE_CONTRACTS["generic"]


def get_python_profile_contract(profile: str) -> PythonProfileContract:
    return PYTHON_PROFILE_CONTRACTS.get(str(profile or "generic").strip().lower(), DEFAULT_PYTHON_PROFILE_CONTRACT)


def get_python_profile_target_paths(profile: str) -> Dict[str, str]:
    return dict(get_python_profile_contract(profile).target_paths)
