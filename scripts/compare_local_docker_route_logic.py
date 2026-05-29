from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request


EXPECTED_ACTIONS = {
    "admin-runtime-verification": ("POST", "/api/admin/orchestrator/runtime-verification"),
    "admin-auto-connect-logs": ("GET", "/api/admin/auto-connect-graph/logs"),
    "admin-auto-connect-completions": ("GET", "/api/admin/auto-connect-graph/completions"),
    "admin-auto-connect-retry-queue": ("GET", "/api/admin/auto-connect-graph/retry-queue"),
    "admin-ad-video-orders": ("GET", "/api/admin/ad-video-orders"),
    "admin-ad-video-orders-monitor-summary": ("GET", "/api/admin/ad-video-orders/monitor-summary"),
    "admin-ad-video-orders-settlement-dashboard": ("GET", "/api/admin/ad-video-orders/settlement-dashboard"),
}

GET_PROBE_ACTIONS = [
    "admin-auto-connect-logs",
    "admin-auto-connect-completions",
    "admin-auto-connect-retry-queue",
    "admin-ad-video-orders",
    "admin-ad-video-orders-monitor-summary",
    "admin-ad-video-orders-settlement-dashboard",
]


@dataclass
class Finding:
    severity: str
    code: str
    summary: str
    detail: str


@dataclass
class ProbeResult:
    surface: str
    name: str
    method: str
    url: str
    status: int | None
    outcome: str
    detail: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_constant(text: str, name: str) -> str | None:
    pattern = rf"const\s+{re.escape(name)}\s*=\s*['\"]([^'\"]+)['\"]"
    match = re.search(pattern, text)
    return match.group(1) if match else None


def parse_array_constant(text: str, name: str) -> list[str]:
    pattern = rf"const\s+{re.escape(name)}\s*=\s*\[([^\]]*)\]"
    match = re.search(pattern, text, re.S)
    if not match:
        return []
    return re.findall(r"['\"]([^'\"]+)['\"]", match.group(1))


def parse_exported_route_methods(text: str) -> set[str]:
    return {
        method.upper()
        for method in re.findall(
            r"export\s+async\s+function\s+(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\b",
            text,
        )
    }


def parse_backend_routes(text: str) -> dict[str, str]:
    routes: dict[str, str] = {}
    for method, route in re.findall(r'@router\.(get|post|put|patch|delete)\("([^"]+)"\)', text):
        routes[f"/api/admin{route}"] = method.upper()
    return routes


def parse_frontend_actions(text: str) -> dict[str, tuple[str, str]]:
    actions: dict[str, tuple[str, str]] = {}
    current_method: str | None = None
    pending_action: str | None = None
    block_lines: list[str] = []

    def flush_pending_action() -> None:
        nonlocal pending_action, block_lines
        if not pending_action or not current_method:
            pending_action = None
            block_lines = []
            return
        block_text = "\n".join(block_lines)
        path_matches = re.findall(r"/api/admin[\w\-./?${}]+", block_text)
        if path_matches:
            normalized_path = path_matches[0].split("?")[0]
            actions[pending_action] = (current_method, normalized_path)
        pending_action = None
        block_lines = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("function resolveAdminGetPath"):
            flush_pending_action()
            current_method = "GET"
            continue
        if stripped.startswith("function resolveAdminPostPath"):
            flush_pending_action()
            current_method = "POST"
            continue
        if stripped.startswith("function resolveAdminPatchPath"):
            flush_pending_action()
            current_method = "PATCH"
            continue
        if stripped.startswith("function resolveAdminPutPath"):
            flush_pending_action()
            current_method = "PUT"
            continue

        action_match = re.search(r"if \(action === '([^']+)'\)", stripped)
        if action_match:
            flush_pending_action()
            pending_action = action_match.group(1)
            block_lines = [stripped]
            continue

        if pending_action:
            block_lines.append(stripped)
            if stripped == "}":
                flush_pending_action()

    flush_pending_action()
    return actions


def parse_service_blocks(compose_text: str) -> dict[str, dict[str, Any]]:
    services: dict[str, dict[str, Any]] = {}
    lines = compose_text.splitlines()
    in_services = False
    current_service: str | None = None
    current_section: str | None = None

    for raw_line in lines:
        if re.match(r"^services:\s*$", raw_line):
            in_services = True
            continue
        if not in_services:
            continue
        if re.match(r"^[A-Za-z0-9_-]+:\s*$", raw_line):
            break

        service_match = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", raw_line)
        if service_match:
            service_name = service_match.group(1)
            current_service = service_name
            services[service_name] = {
                "environment": {},
                "build_args": {},
                "ports": [],
            }
            current_section = None
            continue

        if current_service is None:
            continue

        section_match = re.match(r"^    ([A-Za-z0-9_-]+):\s*$", raw_line)
        if section_match:
            current_section = section_match.group(1)
            continue

        if current_section == "environment":
            env_match = re.match(r"^      ([A-Za-z0-9_]+):\s*(.*)$", raw_line)
            if env_match:
                services[current_service]["environment"][env_match.group(1)] = env_match.group(2).strip()
            continue

        if current_section == "args":
            arg_match = re.match(r"^        ([A-Za-z0-9_]+):\s*(.*)$", raw_line)
            if arg_match:
                services[current_service]["build_args"][arg_match.group(1)] = arg_match.group(2).strip()
            continue

        if current_section == "ports":
            quoted_port = re.match(r'^      - "([^"]+)"\s*$', raw_line)
            if quoted_port:
                services[current_service]["ports"].append(quoted_port.group(1))
                continue
            published_match = re.match(r"^        published:\s*(.*)$", raw_line)
            if published_match:
                services[current_service]["ports"].append(f"published={published_match.group(1).strip()}")
                continue
            target_match = re.match(r"^      - target:\s*(.*)$", raw_line)
            if target_match:
                services[current_service]["ports"].append(f"target={target_match.group(1).strip()}")
                continue

    return services


def find_port_switch_mode(text: str) -> str:
    uses_port_check = "isCurrentPortInSet" in text
    uses_hostname_check = "window.location.hostname" in text or "window.location.host" in text
    if uses_port_check and uses_hostname_check:
        return "port+hostname"
    if uses_port_check:
        return "port-only"
    if uses_hostname_check:
        return "hostname-only"
    return "unknown"


def compose_has_explicit_admin_marketplace_split(compose_text: str) -> bool:
    has_3000 = bool(re.search(r'"[^\"]*:3000(?::\d+)?"|published:\s*\$?\{[^\n]*3000[^\n]*\}|published:\s*3000', compose_text))
    has_3005 = bool(re.search(r'"[^\"]*:3005(?::\d+)?"|published:\s*\$?\{[^\n]*3005[^\n]*\}|published:\s*3005', compose_text))
    return has_3000 and has_3005


def collect_findings(repo_root: Path) -> tuple[list[Finding], dict[str, Any]]:
    proxy_route_path = repo_root / "frontend" / "frontend" / "app" / "api" / "proxy" / "route.ts"
    catchall_proxy_path = repo_root / "frontend" / "frontend" / "app" / "api" / "backend-proxy" / "[...path]" / "route.ts"
    canonical_path = repo_root / "frontend" / "frontend" / "lib" / "canonical-site.ts"
    proxy_host_path = repo_root / "frontend" / "frontend" / "proxy.ts"
    backend_router_path = repo_root / "backend" / "admin_router.py"
    compose_path = repo_root / "docker-compose.yml"

    proxy_route_text = read_text(proxy_route_path)
    catchall_proxy_text = read_text(catchall_proxy_path) if catchall_proxy_path.exists() else ""
    canonical_text = read_text(canonical_path)
    proxy_host_text = read_text(proxy_host_path)
    backend_router_text = read_text(backend_router_path)
    compose_text = read_text(compose_path)

    frontend_actions = parse_frontend_actions(proxy_route_text)
    backend_routes = parse_backend_routes(backend_router_text)
    catchall_methods = parse_exported_route_methods(catchall_proxy_text)
    services = parse_service_blocks(compose_text)

    findings: list[Finding] = []

    for action, (expected_method, expected_path) in EXPECTED_ACTIONS.items():
        actual = frontend_actions.get(action)
        if actual is None and expected_method in catchall_methods:
            actual = (expected_method, expected_path)
        if actual != (expected_method, expected_path):
            findings.append(
                Finding(
                    severity="error",
                    code="FRONTEND_PROXY_ACTION_MISMATCH",
                    summary=f"{action} does not match the expected backend route",
                    detail=f"Expected {expected_method} {expected_path}, got {actual!r}.",
                )
            )

        backend_method = backend_routes.get(expected_path)
        if backend_method != expected_method:
            findings.append(
                Finding(
                    severity="error",
                    code="BACKEND_ROUTE_MISSING_OR_MISMATCH",
                    summary=f"{expected_path} is missing or uses a different method in backend/admin_router.py",
                    detail=f"Expected {expected_method}, got {backend_method!r}.",
                )
            )

    canonical_mode = find_port_switch_mode(canonical_text)
    frontend_admin = services.get("frontend-admin", {})
    frontend_admin_env = frontend_admin.get("environment", {})
    frontend_admin_port = str(frontend_admin_env.get("PORT", "")).strip()
    nginx_service = services.get("nginx", {})
    nginx_ports = nginx_service.get("ports", [])

    if canonical_mode == "port-only" and any("published=80" in port or "published=${NGINX_HTTPS_PORT:-443}" in port or "published=${NGINX_HTTP_PORT:-80}" in port or "published=443" in port for port in nginx_ports):
        findings.append(
            Finding(
                severity="error",
                code="CANONICAL_SITE_PORT_ONLY_DEPLOY_GAP",
                summary="canonical-site.ts switches origins by port only, but docker ingress is on 80/443",
                detail=(
                    "resolveAdminSiteHref/resolveMarketplaceSiteHref currently depend on port membership, "
                    "while docker-compose routes browser traffic through nginx on 80/443. "
                    "On deployed domains this can keep admin-to-marketplace and marketplace-to-admin navigation relative instead of absolute."
                ),
            )
        )

    if frontend_admin_port and frontend_admin_port != "3005":
        findings.append(
            Finding(
                severity="error",
                code="FRONTEND_ADMIN_PORT_MISMATCH",
                summary="frontend-admin container runs on PORT 3000 instead of the local admin port assumption 3005",
                detail=f"docker-compose frontend-admin PORT={frontend_admin_port}.",
            )
        )

    if "frontend-marketplace" not in services:
        findings.append(
            Finding(
                severity="warning",
                code="FRONTEND_MARKETPLACE_SERVICE_MISSING",
                summary="docker-compose has no separate frontend-marketplace service",
                detail="Local verification assumes admin 3005 and marketplace 3000 are separate surfaces, but compose defines only frontend-admin plus nginx.",
            )
        )

    if not compose_has_explicit_admin_marketplace_split(compose_text):
        findings.append(
            Finding(
                severity="warning",
                code="DOCKER_FRONTEND_SPLIT_PORTS_MISSING",
                summary="docker-compose does not expose both 3000 and 3005 browser entrypoints",
                detail="The compose file exposes nginx on 80/443 and backend on 8000, but there is no explicit frontend browser split matching local 3000/3005 assumptions.",
            )
        )

    if not any(
        key in frontend_admin_env
        for key in (
            "ADMIN_ALLOWED_HOSTS",
            "NEXT_PUBLIC_ADMIN_ALLOWED_HOSTS",
            "BACKEND_PROXY_TARGET",
            "LOCAL_API_BASE_URL",
        )
    ):
        findings.append(
            Finding(
                severity="warning",
                code="ADMIN_ALLOWED_HOSTS_NOT_CONFIGURED",
                summary="frontend-admin runtime does not explicitly set ADMIN_ALLOWED_HOSTS",
                detail=(
                    "proxy.ts can fall back to the admin base URL hostname, but the docker runtime is not explicitly documenting the allowed admin hosts. "
                    "This makes environment parity harder to audit."
                ),
            )
        )

    facts = {
        "paths": {
            "proxy_route": str(proxy_route_path),
            "catchall_proxy_route": str(catchall_proxy_path),
            "canonical_site": str(canonical_path),
            "proxy_host_gate": str(proxy_host_path),
            "backend_admin_router": str(backend_router_path),
            "docker_compose": str(compose_path),
        },
        "canonical": {
            "mode": canonical_mode,
            "default_admin_base_url": parse_constant(canonical_text, "DEFAULT_ADMIN_BASE_URL"),
            "default_marketplace_base_url": parse_constant(canonical_text, "DEFAULT_MARKETPLACE_BASE_URL"),
            "default_admin_ports": parse_array_constant(canonical_text, "DEFAULT_ADMIN_PORTS"),
            "default_marketplace_ports": parse_array_constant(canonical_text, "DEFAULT_MARKETPLACE_PORTS"),
        },
        "proxy_host_gate": {
            "default_admin_base_url": parse_constant(proxy_host_text, "DEFAULT_ADMIN_BASE_URL"),
            "default_local_admin_ports": parse_array_constant(proxy_host_text, "DEFAULT_LOCAL_ADMIN_PORTS"),
        },
        "frontend_actions": {action: {"method": method, "path": path} for action, (method, path) in sorted(frontend_actions.items())},
        "catchall_proxy_methods": sorted(catchall_methods),
        "backend_routes": {path: method for path, method in sorted(backend_routes.items()) if path in {item[1] for item in EXPECTED_ACTIONS.values()}},
        "compose": {
            "services": services,
        },
    }
    return findings, facts


def probe_url(method: str, url: str, body: str | None) -> tuple[int | None, str, str]:
    req = urllib_request.Request(url=url, method=method)
    payload = None
    if body is not None:
        payload = body.encode("utf-8")
        req.add_header("Content-Type", "application/json")

    try:
        with urllib_request.urlopen(req, data=payload, timeout=8) as response:
            status = response.getcode()
            text = response.read(240).decode("utf-8", errors="replace")
            return status, "ok", text.strip()
    except urllib_error.HTTPError as exc:
        text = exc.read(240).decode("utf-8", errors="replace")
        return exc.code, "http-error", text.strip()
    except Exception as exc:  # noqa: BLE001
        return None, "network-error", str(exc)


def run_probes(local_base_url: str | None, docker_base_url: str | None) -> list[ProbeResult]:
    probe_results: list[ProbeResult] = []
    surfaces = []
    if local_base_url:
        surfaces.append(("local", local_base_url.rstrip("/")))
    if docker_base_url:
        surfaces.append(("docker", docker_base_url.rstrip("/")))

    for surface, base_url in surfaces:
        docs_status, docs_outcome, docs_detail = probe_url("GET", f"{base_url}/docs", None)
        probe_results.append(ProbeResult(surface, "docs", "GET", f"{base_url}/docs", docs_status, docs_outcome, docs_detail))

        viewer_url = f"{base_url}/admin/docs-viewer?path=%2Fdocs"
        viewer_status, viewer_outcome, viewer_detail = probe_url("GET", viewer_url, None)
        probe_results.append(ProbeResult(surface, "admin-docs-viewer", "GET", viewer_url, viewer_status, viewer_outcome, viewer_detail))

        for action in GET_PROBE_ACTIONS:
            url = f"{base_url}/api/proxy?action={action}"
            status, outcome, detail = probe_url("GET", url, None)
            probe_results.append(ProbeResult(surface, action, "GET", url, status, outcome, detail))

        runtime_url = f"{base_url}/api/proxy?action=admin-runtime-verification"
        status, outcome, detail = probe_url("POST", runtime_url, "{}")
        probe_results.append(ProbeResult(surface, "admin-runtime-verification", "POST", runtime_url, status, outcome, detail))

    return probe_results


def print_report(findings: list[Finding], facts: dict[str, Any], probes: list[ProbeResult]) -> None:
    print("# Local vs Docker Route Logic Compare")
    print()
    print("## Summary")
    print(f"- Findings: {len(findings)}")
    print(f"- Canonical switch mode: {facts['canonical']['mode']}")
    print(f"- frontend-admin PORT: {facts['compose']['services'].get('frontend-admin', {}).get('environment', {}).get('PORT', '<missing>')}")
    print(f"- frontend-marketplace service present: {'frontend-marketplace' in facts['compose']['services']}")
    print()

    print("## Findings")
    if not findings:
        print("- No static mismatches found.")
    for finding in findings:
        print(f"- [{finding.severity.upper()}] {finding.code}: {finding.summary}")
        print(f"  {finding.detail}")
    print()

    print("## Route Inventory")
    for action, expected in EXPECTED_ACTIONS.items():
        actual = facts["frontend_actions"].get(action)
        backend_method = facts["backend_routes"].get(expected[1])
        frontend_method = actual["method"] if actual else "<missing>"
        frontend_path = actual["path"] if actual else "<missing>"
        print(
            f"- {action}: frontend={frontend_method} {frontend_path} | "
            f"backend={backend_method or '<missing>'} {expected[1]}"
        )
    print()

    if probes:
        print("## Live Probes")
        for probe in probes:
            status = probe.status if probe.status is not None else "n/a"
            print(f"- {probe.surface} {probe.method} {probe.name}: status={status}, outcome={probe.outcome}")
            print(f"  {probe.url}")
            if probe.detail:
                print(f"  {probe.detail}")


def build_output_payload(findings: list[Finding], facts: dict[str, Any], probes: list[ProbeResult]) -> dict[str, Any]:
    return {
        "findings": [asdict(item) for item in findings],
        "facts": facts,
        "probes": [asdict(item) for item in probes],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare local route assumptions against docker runtime wiring.")
    parser.add_argument("--repo-root", default=None, help="Repository root. Defaults to the parent of this script directory.")
    parser.add_argument("--local-base-url", default=None, help="Optional local base URL for live probes, e.g. http://127.0.0.1:3005")
    parser.add_argument("--docker-base-url", default=None, help="Optional docker/deployed base URL for live probes, e.g. https://devanalysis114.com")
    parser.add_argument("--json-output", default=None, help="Optional path for JSON output.")
    parser.add_argument("--fail-on-findings", action="store_true", help="Return exit code 1 when findings exist.")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path(__file__).resolve().parents[1]
    findings, facts = collect_findings(repo_root)
    probes = run_probes(args.local_base_url, args.docker_base_url)

    print_report(findings, facts, probes)

    if args.json_output:
        output_path = Path(args.json_output)
        if not output_path.is_absolute():
            output_path = repo_root / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(build_output_payload(findings, facts, probes), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print()
        print(f"JSON report written to {output_path}")

    if args.fail_on_findings and findings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())