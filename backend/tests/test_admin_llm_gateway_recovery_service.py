from __future__ import annotations

from typing import Any

from backend.admin import llm_gateway_recovery_service as svc


def _base_gateway_inspect(networks: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "Config": {"Image": "nginx:alpine"},
        "Mounts": [],
        "NetworkSettings": {"Networks": networks or {}},
        "State": {"Running": True},
    }


def test_collect_llm_gateway_diagnostics_uses_running_operating_container(monkeypatch):
    monkeypatch.setattr(svc, "DEFAULT_GATEWAY_CONTAINER", "llm-nginx")
    monkeypatch.setattr(svc, "DEFAULT_PRIMARY_INGRESS_CONTAINER", "devanalysis114-nginx")
    monkeypatch.setattr(
        svc,
        "_docker_ps_rows",
        lambda: [
            {
                "Names": "devanalysis114-nginx",
                "Status": "Up 2 hours",
                "Ports": "127.0.0.1:80->80/tcp, 127.0.0.1:443->443/tcp",
            }
        ],
    )
    monkeypatch.setattr(
        svc,
        "_docker_ps_row",
        lambda container_name: {
            "Names": container_name,
            "Status": "Up 2 hours",
            "Ports": "127.0.0.1:80->80/tcp, 127.0.0.1:443->443/tcp",
        }
        if container_name == "devanalysis114-nginx"
        else {},
    )
    monkeypatch.setattr(
        svc,
        "_docker_inspect",
        lambda container_name: _base_gateway_inspect(networks={svc.DEFAULT_LLM_NETWORK: {}})
        if container_name == "devanalysis114-nginx"
        else None,
    )
    monkeypatch.setattr(svc, "_docker_exec_http_status", lambda container_name, _url: 200 if container_name == "devanalysis114-nginx" else 0)
    monkeypatch.setattr(svc, "_docker_available", lambda: True)

    result = svc.collect_llm_gateway_diagnostics()

    assert result["containers"]["gateway"]["name"] == "devanalysis114-nginx"
    assert result["containers"]["gateway"]["running"] is True
    assert result["containers"]["gateway"]["health_http_code"] == 200


def test_collect_llm_gateway_diagnostics_reports_docker_daemon_unavailable(monkeypatch):
    monkeypatch.setattr(svc, "_docker_available", lambda: False)

    result = svc.collect_llm_gateway_diagnostics()

    assert result["status"] == "error"
    assert result["root_causes"] == ["docker_daemon_unavailable"]
    assert "Docker 데몬에 접근할 수 없습니다" in result["message"]
    assert "근본원인: docker_daemon_unavailable" in result["recommendations"]
    assert any("그룹/소켓 권한" in item for item in result["recommendations"])


def test_auto_recover_dry_run_includes_gateway_network_reattach(monkeypatch):
    monkeypatch.setattr(
        svc,
        "collect_llm_gateway_diagnostics",
        lambda: {"status": "critical", "root_causes": ["gateway_network_detached"]},
    )

    def fake_inspect(container_name: str):
        if container_name == svc.DEFAULT_GATEWAY_CONTAINER:
            return _base_gateway_inspect(networks={})
        return None

    monkeypatch.setattr(svc, "_docker_inspect", fake_inspect)

    result = svc.auto_recover_llm_gateway(mode="port_shift_shadow", dry_run=True)
    steps = [item.get("step") for item in result.get("actions", [])]

    assert "dry_run_gateway_network_reattach" in steps
    assert "dry_run_shadow_create" in steps


def test_auto_recover_real_run_reattaches_gateway_network(monkeypatch):
    monkeypatch.setattr(
        svc,
        "collect_llm_gateway_diagnostics",
        lambda: {"status": "critical", "root_causes": ["gateway_network_detached"]},
    )

    state = {"attached": False}

    def fake_container_network_names(container_name: str):
        if container_name != svc.DEFAULT_GATEWAY_CONTAINER:
            return []
        return [svc.DEFAULT_LLM_NETWORK] if state["attached"] else []

    def fake_inspect(container_name: str):
        if container_name == svc.DEFAULT_GATEWAY_CONTAINER:
            networks = {svc.DEFAULT_LLM_NETWORK: {}} if state["attached"] else {}
            return _base_gateway_inspect(networks=networks)
        return None

    def fake_run_command(args, *, timeout=25):
        key = tuple(args)
        if key[:4] == ("docker", "network", "connect", svc.DEFAULT_LLM_NETWORK):
            state["attached"] = True
            return svc.CommandResult(ok=True, code=0, stdout="connected", stderr="")
        if key[:3] == ("docker", "rm", "-f"):
            return svc.CommandResult(ok=True, code=0, stdout=svc.DEFAULT_SHADOW_CONTAINER, stderr="")
        if key[:3] == ("docker", "run", "-d"):
            return svc.CommandResult(ok=True, code=0, stdout="shadow-container-id", stderr="")
        return svc.CommandResult(ok=True, code=0, stdout="", stderr="")

    monkeypatch.setattr(svc, "_container_network_names", fake_container_network_names)
    monkeypatch.setattr(svc, "_docker_inspect", fake_inspect)
    monkeypatch.setattr(svc, "_run_command", fake_run_command)
    monkeypatch.setattr(svc, "_docker_exec_http_status", lambda *_args, **_kwargs: 200)

    result = svc.auto_recover_llm_gateway(mode="port_shift_shadow", dry_run=False)

    reattach_steps = [
        item for item in result.get("actions", []) if item.get("step") == "reattach_gateway_network"
    ]
    assert reattach_steps
    assert reattach_steps[0].get("ok") is True
    assert svc.DEFAULT_LLM_NETWORK in (reattach_steps[0].get("networks_after") or [])


def test_auto_recover_recreates_gateway_on_port_conflict(monkeypatch):
    monkeypatch.setattr(
        svc,
        "collect_llm_gateway_diagnostics",
        lambda: {"status": "critical", "root_causes": ["gateway_network_detached", "host_port_80_conflict_risk"]},
    )

    state = {"attached": False, "removed": False}

    def fake_container_network_names(container_name: str):
        if container_name != svc.DEFAULT_GATEWAY_CONTAINER:
            return []
        return [svc.DEFAULT_LLM_NETWORK] if state["attached"] else []

    def fake_inspect(container_name: str):
        if container_name == svc.DEFAULT_GATEWAY_CONTAINER:
            networks = {svc.DEFAULT_LLM_NETWORK: {}} if state["attached"] else {}
            return {
                "Config": {
                    "Image": "nginx:alpine",
                    "Env": ["CANARY_PERCENT=100"],
                },
                "Mounts": [],
                "NetworkSettings": {"Networks": networks},
                "State": {"Running": not state["removed"]},
            }
        return None

    def fake_run_command(args, *, timeout=25):
        key = tuple(args)
        if key[:4] == ("docker", "network", "connect", svc.DEFAULT_LLM_NETWORK):
            return svc.CommandResult(
                ok=False,
                code=1,
                stdout="",
                stderr="Error response from daemon: Bind for 0.0.0.0:80 failed: port is already allocated",
            )
        if key[:3] == ("docker", "rm", "-f") and key[-1] == svc.DEFAULT_GATEWAY_CONTAINER:
            state["removed"] = True
            return svc.CommandResult(ok=True, code=0, stdout=svc.DEFAULT_GATEWAY_CONTAINER, stderr="")
        if key[:3] == ("docker", "run", "-d") and svc.DEFAULT_GATEWAY_CONTAINER in key:
            state["attached"] = True
            state["removed"] = False
            return svc.CommandResult(ok=True, code=0, stdout="gateway-recreated", stderr="")
        if key[:3] == ("docker", "rm", "-f") and key[-1] == svc.DEFAULT_SHADOW_CONTAINER:
            return svc.CommandResult(ok=True, code=0, stdout=svc.DEFAULT_SHADOW_CONTAINER, stderr="")
        if key[:3] == ("docker", "run", "-d") and svc.DEFAULT_SHADOW_CONTAINER in key:
            return svc.CommandResult(ok=True, code=0, stdout="shadow-created", stderr="")
        return svc.CommandResult(ok=True, code=0, stdout="", stderr="")

    monkeypatch.setattr(svc, "_container_network_names", fake_container_network_names)
    monkeypatch.setattr(svc, "_docker_inspect", fake_inspect)
    monkeypatch.setattr(svc, "_run_command", fake_run_command)
    monkeypatch.setattr(svc, "_docker_exec_http_status", lambda *_args, **_kwargs: 200)

    result = svc.auto_recover_llm_gateway(mode="port_shift_shadow", dry_run=False)

    reattach = [item for item in result.get("actions", []) if item.get("step") == "reattach_gateway_network"][0]
    recreate = [item for item in result.get("actions", []) if item.get("step") == "recreate_gateway_without_host_ports"][0]

    assert reattach.get("ok") is True
    assert reattach.get("conflict_recreated") is True
    assert svc.DEFAULT_LLM_NETWORK in (reattach.get("networks_after") or [])
    assert recreate.get("create_ok") is True


def test_auto_recover_recreates_unhealthy_gateway_even_if_attached(monkeypatch):
    monkeypatch.setattr(
        svc,
        "collect_llm_gateway_diagnostics",
        lambda: {"status": "critical", "root_causes": ["gateway_upstream_502"]},
    )

    state = {"running": False, "attached": True}

    def fake_container_network_names(container_name: str):
        if container_name != svc.DEFAULT_GATEWAY_CONTAINER:
            return []
        return [svc.DEFAULT_LLM_NETWORK] if state["attached"] else []

    def fake_inspect(container_name: str):
        if container_name == svc.DEFAULT_GATEWAY_CONTAINER:
            return {
                "Config": {
                    "Image": "nginx:alpine",
                    "Env": ["CANARY_PERCENT=100"],
                },
                "Mounts": [],
                "NetworkSettings": {"Networks": {svc.DEFAULT_LLM_NETWORK: {}}},
                "State": {"Running": state["running"]},
            }
        return None

    def fake_run_command(args, *, timeout=25):
        key = tuple(args)
        if key[:3] == ("docker", "rm", "-f") and key[-1] == svc.DEFAULT_GATEWAY_CONTAINER:
            state["running"] = False
            return svc.CommandResult(ok=True, code=0, stdout=svc.DEFAULT_GATEWAY_CONTAINER, stderr="")
        if key[:3] == ("docker", "run", "-d") and svc.DEFAULT_GATEWAY_CONTAINER in key:
            state["running"] = True
            return svc.CommandResult(ok=True, code=0, stdout="gateway-recreated", stderr="")
        if key[:3] == ("docker", "rm", "-f") and key[-1] == svc.DEFAULT_SHADOW_CONTAINER:
            return svc.CommandResult(ok=True, code=0, stdout=svc.DEFAULT_SHADOW_CONTAINER, stderr="")
        if key[:3] == ("docker", "run", "-d") and svc.DEFAULT_SHADOW_CONTAINER in key:
            return svc.CommandResult(ok=True, code=0, stdout="shadow-created", stderr="")
        return svc.CommandResult(ok=True, code=0, stdout="", stderr="")

    monkeypatch.setattr(svc, "_container_network_names", fake_container_network_names)
    monkeypatch.setattr(svc, "_docker_inspect", fake_inspect)
    monkeypatch.setattr(svc, "_run_command", fake_run_command)
    monkeypatch.setattr(svc, "_docker_exec_http_status", lambda *_args, **_kwargs: 0)

    result = svc.auto_recover_llm_gateway(mode="port_shift_shadow", dry_run=False)

    recreate = [item for item in result.get("actions", []) if item.get("step") == "recreate_gateway_on_unhealthy"][0]
    reattach = [item for item in result.get("actions", []) if item.get("step") == "reattach_gateway_network"][0]

    assert recreate.get("create_ok") is True
    assert reattach.get("reason") == "already_attached_but_recreated_unhealthy"
    assert reattach.get("ok") is True
