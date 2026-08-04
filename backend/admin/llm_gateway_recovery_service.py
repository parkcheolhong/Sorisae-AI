from __future__ import annotations

# ruff: noqa: E501

import json
import os
import shlex
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence


DEFAULT_PRIMARY_INGRESS_CONTAINER = os.getenv("ADMIN_LLM_PRIMARY_INGRESS_CONTAINER", "devanalysis114-nginx").strip() or "devanalysis114-nginx"
DEFAULT_GATEWAY_CONTAINER = os.getenv("ADMIN_LLM_GATEWAY_CONTAINER", DEFAULT_PRIMARY_INGRESS_CONTAINER).strip() or DEFAULT_PRIMARY_INGRESS_CONTAINER
DEFAULT_SHADOW_CONTAINER = os.getenv(
    "ADMIN_LLM_GATEWAY_SHADOW_CONTAINER",
    f"{DEFAULT_GATEWAY_CONTAINER}-shadow",
).strip() or f"{DEFAULT_GATEWAY_CONTAINER}-shadow"
DEFAULT_LLM_NETWORK = os.getenv("ADMIN_LLM_NETWORK", "gpu-llm-server_llm-network").strip() or "gpu-llm-server_llm-network"
DEFAULT_SHIFT_HTTP_PORT = int(os.getenv("ADMIN_LLM_SHIFT_HTTP_PORT", "18080"))
DEFAULT_SHIFT_HTTPS_PORT = int(os.getenv("ADMIN_LLM_SHIFT_HTTPS_PORT", "18443"))
DEFAULT_AUTO_REATTACH_GATEWAY_NETWORK = os.getenv("ADMIN_LLM_AUTO_REATTACH_GATEWAY_NETWORK", "1").strip().lower() not in {"0", "false", "no", "off", ""}


@dataclass(frozen=True)
class CommandResult:
    ok: bool
    code: int
    stdout: str
    stderr: str


def _run_command(args: Sequence[str], *, timeout: int = 25) -> CommandResult:
    try:
        proc = subprocess.run(
            list(args),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return CommandResult(
            ok=proc.returncode == 0,
            code=int(proc.returncode),
            stdout=str(proc.stdout or "").strip(),
            stderr=str(proc.stderr or "").strip(),
        )
    except FileNotFoundError:
        return CommandResult(ok=False, code=127, stdout="", stderr="docker command not found")
    except subprocess.TimeoutExpired:
        return CommandResult(ok=False, code=124, stdout="", stderr=f"timeout after {timeout}s")


def _docker_available() -> bool:
    result = _run_command(["docker", "version", "--format", "{{.Server.Version}}"], timeout=10)
    return result.ok and bool(result.stdout)


def _docker_inspect(container_name: str) -> Optional[Dict[str, Any]]:
    result = _run_command(["docker", "inspect", container_name], timeout=12)
    if not result.ok:
        return None
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        return payload[0]
    return None


def _docker_ps_row(container_name: str) -> Dict[str, Any]:
    result = _run_command(
        [
            "docker",
            "ps",
            "-a",
            "--filter",
            f"name=^{container_name}$",
            "--format",
            "{{json .}}",
        ],
        timeout=10,
    )
    if not result.ok or not result.stdout:
        return {}
    first = result.stdout.splitlines()[0].strip()
    try:
        row = json.loads(first)
    except json.JSONDecodeError:
        return {}
    return row if isinstance(row, dict) else {}


def _docker_exec_http_status(container_name: str, url: str) -> int:
    cmd = (
        "wget -qSO- "
        + shlex.quote(url)
        + " -O /dev/null 2>&1 | awk '/HTTP\\// {print $2; exit}'"
    )
    result = _run_command(["docker", "exec", container_name, "sh", "-lc", cmd], timeout=15)
    if not result.ok:
        return 0
    try:
        return int((result.stdout or "0").strip())
    except ValueError:
        return 0


def _container_network_names(container_name: str) -> List[str]:
    inspect = _docker_inspect(container_name)
    if not inspect:
        return []
    networks = (
        inspect.get("NetworkSettings", {})
        .get("Networks", {})
    )
    if not isinstance(networks, dict):
        return []
    return sorted(str(name) for name in networks.keys())


def _container_has_network(container_name: str, network_name: str) -> bool:
    wanted = str(network_name or "").strip()
    if not wanted:
        return False
    return wanted in _container_network_names(container_name)


def _extract_host_port_tokens(ports_text: str) -> List[str]:
    tokens: List[str] = []
    for part in str(ports_text or "").split(","):
        segment = part.strip()
        if "->" not in segment:
            continue
        host = segment.split("->", 1)[0].strip()
        if ":" not in host:
            continue
        token = host.rsplit(":", 1)[-1]
        tokens.append(token)
    return tokens


def _build_mount_args(mounts: List[Dict[str, Any]]) -> List[str]:
    args: List[str] = []
    for mount in mounts:
        if str(mount.get("Type") or "") != "bind":
            continue
        source = str(mount.get("Source") or "").strip()
        target = str(mount.get("Destination") or "").strip()
        if not source or not target:
            continue
        mode = "rw" if bool(mount.get("RW")) else "ro"
        args.extend(["-v", f"{source}:{target}:{mode}"])
    return args


def _find_template_mount_source(mounts: List[Dict[str, Any]]) -> Optional[str]:
    for mount in mounts:
        destination = str(mount.get("Destination") or "").strip()
        if destination in {"/etc/nginx/templates/nginx.conf.template", "/etc/nginx/nginx.conf"}:
            source = str(mount.get("Source") or "").strip()
            if source:
                return source
    return None


def _build_safe_shadow_mount_args(mounts: List[Dict[str, Any]]) -> List[str]:
    template_source = _find_template_mount_source(mounts)
    if template_source:
        return ["-v", f"{template_source}:/etc/nginx/templates/nginx.conf.template:ro"]

    args: List[str] = []
    for mount in mounts:
        destination = str(mount.get("Destination") or "").strip()
        if destination.startswith("/etc/nginx/conf.d"):
            continue
        if destination == "/etc/nginx/nginx.conf":
            source = str(mount.get("Source") or "").strip()
            if source:
                args.extend(["-v", f"{source}:/etc/nginx/nginx.conf:ro"])
    return args


def _build_env_args(env_values: List[str]) -> List[str]:
    args: List[str] = []
    for env_value in env_values:
        value = str(env_value or "").strip()
        if not value or "=" not in value:
            continue
        args.extend(["-e", value])
    return args


def collect_llm_gateway_diagnostics() -> Dict[str, Any]:
    if not _docker_available():
        return {
            "status": "error",
            "root_causes": ["docker_daemon_unavailable"],
            "message": "Docker 데몬에 접근할 수 없어 llm gateway 진단을 수행할 수 없습니다.",
            "containers": {},
            "recommendations": [
                "Docker Desktop/Engine 상태를 먼저 복구하세요.",
                "관리자 API가 도커 명령을 실행할 권한(그룹/소켓)에 포함되는지 확인하세요.",
            ],
        }

    gateway_row = _docker_ps_row(DEFAULT_GATEWAY_CONTAINER)
    shadow_row = _docker_ps_row(DEFAULT_SHADOW_CONTAINER)
    ingress_row = _docker_ps_row(DEFAULT_PRIMARY_INGRESS_CONTAINER)

    gateway_inspect = _docker_inspect(DEFAULT_GATEWAY_CONTAINER)
    shadow_inspect = _docker_inspect(DEFAULT_SHADOW_CONTAINER)

    gateway_networks = (
        (gateway_inspect or {})
        .get("NetworkSettings", {})
        .get("Networks", {})
    )
    shadow_networks = (
        (shadow_inspect or {})
        .get("NetworkSettings", {})
        .get("Networks", {})
    )

    gateway_ports = _extract_host_port_tokens(str(gateway_row.get("Ports") or ""))
    ingress_ports = _extract_host_port_tokens(str(ingress_row.get("Ports") or ""))

    gateway_running = bool((gateway_inspect or {}).get("State", {}).get("Running"))
    shadow_running = bool((shadow_inspect or {}).get("State", {}).get("Running"))
    gateway_network_attached = bool(gateway_networks)
    shadow_network_attached = bool(shadow_networks)

    gateway_health_code = _docker_exec_http_status(DEFAULT_GATEWAY_CONTAINER, "http://127.0.0.1/health") if gateway_running else 0
    gateway_proxy_code = _docker_exec_http_status(DEFAULT_GATEWAY_CONTAINER, "http://127.0.0.1/api/v1/models") if gateway_running else 0

    root_causes: List[str] = []
    recommendations: List[str] = []

    if not gateway_running:
        root_causes.append("gateway_not_running")
        recommendations.append(f"{DEFAULT_GATEWAY_CONTAINER}을(를) 정식 compose 또는 shadow 포트(18080/18443)로 재생성하세요.")
    if gateway_running and not gateway_network_attached:
        root_causes.append("gateway_network_detached")
        recommendations.append(f"{DEFAULT_GATEWAY_CONTAINER}를 {DEFAULT_LLM_NETWORK} 네트워크에 재연결하세요.")
    if gateway_running and gateway_health_code != 200:
        root_causes.append("gateway_healthcheck_failed")
        recommendations.append("nginx config mount 경로와 컨테이너 내부 nginx -T 결과를 다시 정합화하세요.")
    if gateway_running and gateway_proxy_code >= 500:
        root_causes.append("gateway_upstream_502")
        recommendations.append("업스트림 DNS/네트워크 또는 release-track map이 실제 reachable backend를 가리키는지 점검하세요.")

    if "80" in ingress_ports and ("80" in gateway_ports or (not gateway_ports and gateway_running)):
        root_causes.append("host_port_80_conflict_risk")
        recommendations.append(f"무중단 우선으로 {DEFAULT_GATEWAY_CONTAINER}을(를) 18080/18443 포트로 재배치하세요.")

    if shadow_running and shadow_network_attached:
        recommendations.append("shadow 컨테이너가 정상 구동 중이면 운영 트래픽 전환 전에 health/proxy smoke를 먼저 확인하세요.")

    status = "ok"
    if root_causes:
        status = "warning" if "host_port_80_conflict_risk" in root_causes and len(root_causes) == 1 else "critical"

    return {
        "status": status,
        "root_causes": root_causes,
        "message": "근본 원인 기반 진단 결과입니다. 포트/네트워크/업스트림 상태를 함께 확인했습니다.",
        "containers": {
            "gateway": {
                "name": DEFAULT_GATEWAY_CONTAINER,
                "running": gateway_running,
                "ports": str(gateway_row.get("Ports") or ""),
                "status": str(gateway_row.get("Status") or ""),
                "network_attached": gateway_network_attached,
                "network_names": sorted(list(gateway_networks.keys())),
                "health_http_code": gateway_health_code,
                "proxy_http_code": gateway_proxy_code,
            },
            "shadow": {
                "name": DEFAULT_SHADOW_CONTAINER,
                "running": shadow_running,
                "ports": str(shadow_row.get("Ports") or ""),
                "status": str(shadow_row.get("Status") or ""),
                "network_attached": shadow_network_attached,
                "network_names": sorted(list(shadow_networks.keys())),
            },
            "primary_ingress": {
                "name": DEFAULT_PRIMARY_INGRESS_CONTAINER,
                "ports": str(ingress_row.get("Ports") or ""),
                "status": str(ingress_row.get("Status") or ""),
            },
        },
        "recommendations": recommendations,
        "safe_strategy": {
            "mode": "port_shift_shadow",
            "http_port": DEFAULT_SHIFT_HTTP_PORT,
            "https_port": DEFAULT_SHIFT_HTTPS_PORT,
            "network": DEFAULT_LLM_NETWORK,
            "target_container": DEFAULT_SHADOW_CONTAINER,
        },
    }


def _build_shadow_run_command(
    *,
    image: str,
    network: str,
    mounts: List[Dict[str, Any]],
    http_port: int,
    https_port: int,
) -> List[str]:
    cmd: List[str] = [
        "docker",
        "run",
        "-d",
        "--name",
        DEFAULT_SHADOW_CONTAINER,
        "--restart",
        "unless-stopped",
        "--network",
        network,
        "-e",
        "CANARY_PERCENT=100",
        "-e",
        "NGINX_ENVSUBST_OUTPUT_DIR=/etc/nginx",
        "-p",
        f"127.0.0.1:{http_port}:80",
        "-p",
        f"127.0.0.1:{https_port}:443",
    ]
    safe_mount_args = _build_safe_shadow_mount_args(mounts)
    if safe_mount_args:
        cmd.extend(safe_mount_args)
    else:
        cmd.extend(_build_mount_args(mounts))
    cmd.append(image)
    return cmd


def _build_gateway_recreate_command(
    *,
    image: str,
    network: str,
    mounts: List[Dict[str, Any]],
    env_values: List[str],
) -> List[str]:
    cmd: List[str] = [
        "docker",
        "run",
        "-d",
        "--name",
        DEFAULT_GATEWAY_CONTAINER,
        "--restart",
        "unless-stopped",
        "--network",
        network,
        "-e",
        "NGINX_ENVSUBST_OUTPUT_DIR=/etc/nginx",
    ]
    mount_args = _build_safe_shadow_mount_args(mounts)
    if mount_args:
        cmd.extend(mount_args)
    else:
        cmd.extend(_build_mount_args(mounts))
    cmd.extend(_build_env_args(env_values))
    cmd.append(image)
    return cmd


def auto_recover_llm_gateway(*, mode: str = "port_shift_shadow", dry_run: bool = False) -> Dict[str, Any]:
    diagnostics_before = collect_llm_gateway_diagnostics()
    actions: List[Dict[str, Any]] = []

    if mode == "disable_nonessential":
        for container in (DEFAULT_GATEWAY_CONTAINER, DEFAULT_SHADOW_CONTAINER):
            if dry_run:
                actions.append({"step": "dry_run_stop", "container": container, "command": f"docker rm -f {container}"})
                continue
            result = _run_command(["docker", "rm", "-f", container], timeout=20)
            actions.append(
                {
                    "step": "stop_container",
                    "container": container,
                    "ok": result.ok,
                    "code": result.code,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            )
        diagnostics_after = collect_llm_gateway_diagnostics()
        return {
            "mode": mode,
            "dry_run": dry_run,
            "actions": actions,
            "diagnostics_before": diagnostics_before,
            "diagnostics_after": diagnostics_after,
            "message": f"{DEFAULT_GATEWAY_CONTAINER} 경로를 운영 트래픽에서 분리(비활성)했습니다.",
        }

    if mode != "port_shift_shadow":
        return {
            "mode": mode,
            "dry_run": dry_run,
            "actions": actions,
            "diagnostics_before": diagnostics_before,
            "diagnostics_after": diagnostics_before,
            "message": "지원하지 않는 복구 모드입니다.",
        }

    base_inspect = _docker_inspect(DEFAULT_GATEWAY_CONTAINER)
    if not base_inspect:
        return {
            "mode": mode,
            "dry_run": dry_run,
            "actions": actions,
            "diagnostics_before": diagnostics_before,
            "diagnostics_after": diagnostics_before,
            "message": f"기준 컨테이너 {DEFAULT_GATEWAY_CONTAINER}을(를) 찾을 수 없어 shadow 재생성을 진행할 수 없습니다.",
        }

    image = str(base_inspect.get("Config", {}).get("Image") or "nginx:alpine")
    mounts = [m for m in (base_inspect.get("Mounts") or []) if isinstance(m, dict)]

    if dry_run:
        if DEFAULT_AUTO_REATTACH_GATEWAY_NETWORK and not _container_has_network(DEFAULT_GATEWAY_CONTAINER, DEFAULT_LLM_NETWORK):
            actions.append(
                {
                    "step": "dry_run_gateway_network_reattach",
                    "container": DEFAULT_GATEWAY_CONTAINER,
                    "command": f"docker network connect {DEFAULT_LLM_NETWORK} {DEFAULT_GATEWAY_CONTAINER}",
                }
            )
        cmd_preview = _build_shadow_run_command(
            image=image,
            network=DEFAULT_LLM_NETWORK,
            mounts=mounts,
            http_port=DEFAULT_SHIFT_HTTP_PORT,
            https_port=DEFAULT_SHIFT_HTTPS_PORT,
        )
        actions.append({"step": "dry_run_shadow_create", "command": " ".join(shlex.quote(part) for part in cmd_preview)})
        diagnostics_after = collect_llm_gateway_diagnostics()
        return {
            "mode": mode,
            "dry_run": dry_run,
            "actions": actions,
            "diagnostics_before": diagnostics_before,
            "diagnostics_after": diagnostics_after,
            "message": "dry-run 완료: 포트 재배치 명령을 미리 생성했습니다.",
        }

    if DEFAULT_AUTO_REATTACH_GATEWAY_NETWORK:
        gateway_networks_before = _container_network_names(DEFAULT_GATEWAY_CONTAINER)
        if DEFAULT_LLM_NETWORK not in gateway_networks_before:
            attach_result = _run_command(
                ["docker", "network", "connect", DEFAULT_LLM_NETWORK, DEFAULT_GATEWAY_CONTAINER],
                timeout=15,
            )
            gateway_networks_after = _container_network_names(DEFAULT_GATEWAY_CONTAINER)
            attach_ok = bool(attach_result.ok or DEFAULT_LLM_NETWORK in gateway_networks_after)
            conflict_recreated = False
            conflict_detected = (
                not attach_ok
                and "port is already allocated" in str(attach_result.stderr or "").lower()
            )

            if conflict_detected:
                recreate_remove = _run_command(["docker", "rm", "-f", DEFAULT_GATEWAY_CONTAINER], timeout=20)
                recreate_cmd = _build_gateway_recreate_command(
                    image=image,
                    network=DEFAULT_LLM_NETWORK,
                    mounts=mounts,
                    env_values=list(base_inspect.get("Config", {}).get("Env") or []),
                )
                recreate_run = _run_command(recreate_cmd, timeout=25)
                gateway_networks_after = _container_network_names(DEFAULT_GATEWAY_CONTAINER)
                attach_ok = bool(recreate_run.ok and DEFAULT_LLM_NETWORK in gateway_networks_after)
                conflict_recreated = attach_ok
                actions.append(
                    {
                        "step": "recreate_gateway_without_host_ports",
                        "container": DEFAULT_GATEWAY_CONTAINER,
                        "network": DEFAULT_LLM_NETWORK,
                        "remove_ok": recreate_remove.ok,
                        "remove_code": recreate_remove.code,
                        "remove_stdout": recreate_remove.stdout,
                        "remove_stderr": recreate_remove.stderr,
                        "create_ok": recreate_run.ok,
                        "create_code": recreate_run.code,
                        "create_stdout": recreate_run.stdout,
                        "create_stderr": recreate_run.stderr,
                        "command": " ".join(shlex.quote(part) for part in recreate_cmd),
                    }
                )
            actions.append(
                {
                    "step": "reattach_gateway_network",
                    "container": DEFAULT_GATEWAY_CONTAINER,
                    "network": DEFAULT_LLM_NETWORK,
                    "ok": attach_ok,
                    "code": attach_result.code,
                    "stdout": attach_result.stdout,
                    "stderr": attach_result.stderr,
                    "conflict_recreated": conflict_recreated,
                    "networks_before": gateway_networks_before,
                    "networks_after": gateway_networks_after,
                }
            )
        else:
            gateway_state = (base_inspect.get("State") or {}) if isinstance(base_inspect, dict) else {}
            gateway_running = bool(gateway_state.get("Running"))
            gateway_health = _docker_exec_http_status(DEFAULT_GATEWAY_CONTAINER, "http://127.0.0.1/health") if gateway_running else 0
            gateway_unhealthy = (not gateway_running) or gateway_health != 200
            if gateway_unhealthy:
                recreate_remove = _run_command(["docker", "rm", "-f", DEFAULT_GATEWAY_CONTAINER], timeout=20)
                recreate_cmd = _build_gateway_recreate_command(
                    image=image,
                    network=DEFAULT_LLM_NETWORK,
                    mounts=mounts,
                    env_values=list(base_inspect.get("Config", {}).get("Env") or []),
                )
                recreate_run = _run_command(recreate_cmd, timeout=25)
                gateway_networks_after = _container_network_names(DEFAULT_GATEWAY_CONTAINER)
                actions.append(
                    {
                        "step": "recreate_gateway_on_unhealthy",
                        "container": DEFAULT_GATEWAY_CONTAINER,
                        "network": DEFAULT_LLM_NETWORK,
                        "health_before": gateway_health,
                        "running_before": gateway_running,
                        "remove_ok": recreate_remove.ok,
                        "remove_code": recreate_remove.code,
                        "remove_stdout": recreate_remove.stdout,
                        "remove_stderr": recreate_remove.stderr,
                        "create_ok": recreate_run.ok,
                        "create_code": recreate_run.code,
                        "create_stdout": recreate_run.stdout,
                        "create_stderr": recreate_run.stderr,
                        "command": " ".join(shlex.quote(part) for part in recreate_cmd),
                        "networks_after": gateway_networks_after,
                    }
                )
                actions.append(
                    {
                        "step": "reattach_gateway_network",
                        "container": DEFAULT_GATEWAY_CONTAINER,
                        "network": DEFAULT_LLM_NETWORK,
                        "ok": bool(recreate_run.ok and DEFAULT_LLM_NETWORK in gateway_networks_after),
                        "skipped": True,
                        "reason": "already_attached_but_recreated_unhealthy",
                        "networks_before": gateway_networks_before,
                        "networks_after": gateway_networks_after,
                    }
                )
            else:
                actions.append(
                    {
                        "step": "reattach_gateway_network",
                        "container": DEFAULT_GATEWAY_CONTAINER,
                        "network": DEFAULT_LLM_NETWORK,
                        "ok": True,
                        "skipped": True,
                        "reason": "already_attached",
                        "networks_before": gateway_networks_before,
                        "networks_after": gateway_networks_before,
                    }
                )

    rm_old_shadow = _run_command(["docker", "rm", "-f", DEFAULT_SHADOW_CONTAINER], timeout=20)
    actions.append(
        {
            "step": "remove_old_shadow",
            "container": DEFAULT_SHADOW_CONTAINER,
            "ok": rm_old_shadow.ok,
            "code": rm_old_shadow.code,
            "stdout": rm_old_shadow.stdout,
            "stderr": rm_old_shadow.stderr,
        }
    )

    run_cmd = _build_shadow_run_command(
        image=image,
        network=DEFAULT_LLM_NETWORK,
        mounts=mounts,
        http_port=DEFAULT_SHIFT_HTTP_PORT,
        https_port=DEFAULT_SHIFT_HTTPS_PORT,
    )
    run_result = _run_command(run_cmd, timeout=25)
    actions.append(
        {
            "step": "create_shadow",
            "container": DEFAULT_SHADOW_CONTAINER,
            "ok": run_result.ok,
            "code": run_result.code,
            "stdout": run_result.stdout,
            "stderr": run_result.stderr,
            "command": " ".join(shlex.quote(part) for part in run_cmd),
        }
    )

    shadow_health = _docker_exec_http_status(DEFAULT_SHADOW_CONTAINER, "http://127.0.0.1/health")
    shadow_proxy = _docker_exec_http_status(DEFAULT_SHADOW_CONTAINER, "http://127.0.0.1/api/v1/models")
    actions.append(
        {
            "step": "shadow_smoke",
            "container": DEFAULT_SHADOW_CONTAINER,
            "health_http_code": shadow_health,
            "proxy_http_code": shadow_proxy,
            "ok": shadow_health == 200,
        }
    )

    diagnostics_after = collect_llm_gateway_diagnostics()
    message = (
        f"{DEFAULT_GATEWAY_CONTAINER} shadow를 18080/18443으로 재배치했습니다. 본 운영 인입(80/443)은 중단 없이 유지됩니다."
        if run_result.ok
        else "포트 재배치 shadow 생성에 실패했습니다. actions 항목의 stderr를 확인하세요."
    )
    return {
        "mode": mode,
        "dry_run": dry_run,
        "actions": actions,
        "diagnostics_before": diagnostics_before,
        "diagnostics_after": diagnostics_after,
        "message": message,
    }
