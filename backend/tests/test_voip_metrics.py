"""#7 VoIP 메트릭 + #6 TURN env 정합화 단위 테스트.

- TURN env 이름 불일치 수정: `config.py`가 `VOIP_TURN_*`/`TURN_*`(접두 없음, 운영 compose)
  를 모두 수용하고 `VOIP_*`가 우선하는지.
- VoIP 메트릭 record 함수가 throw 없이 동작하고 `voip_*` 시리즈를 노출하는지.
"""

from backend.voip import config as voip_config
from backend.voip import metrics as voip_metrics


# ---- #6 TURN env 정합화 ----

def test_turn_secret_unprefixed_alias(monkeypatch):
    # 운영 compose는 접두 없는 TURN_SECRET을 주입 → dynamic 자격이 동작해야 한다.
    monkeypatch.delenv("VOIP_TURN_STATIC_AUTH_SECRET", raising=False)
    monkeypatch.setenv("TURN_SECRET", "compose-injected-secret")
    creds = voip_config.dynamic_turn_credentials("user-9", now=1_000_000)
    assert creds is not None
    assert creds[0] == "1086400:user-9"  # now + default ttl(86400)


def test_voip_prefixed_secret_takes_precedence(monkeypatch):
    monkeypatch.setenv("VOIP_TURN_STATIC_AUTH_SECRET", "voip-wins")
    monkeypatch.setenv("TURN_SECRET", "compose-loses")
    a = voip_config.dynamic_turn_credentials("u", now=10)
    monkeypatch.delenv("VOIP_TURN_STATIC_AUTH_SECRET", raising=False)
    b = voip_config.dynamic_turn_credentials("u", now=10)  # 이제 TURN_SECRET 사용
    assert a is not None and b is not None
    assert a[1] != b[1]  # 시크릿이 다르므로 HMAC 자격도 달라야 한다


def test_turn_urls_unprefixed_alias(monkeypatch):
    monkeypatch.delenv("VOIP_TURN_URLS", raising=False)
    monkeypatch.delenv("VOIP_STUN_URLS", raising=False)
    monkeypatch.delenv("VOIP_TURN_STATIC_AUTH_SECRET", raising=False)
    monkeypatch.delenv("TURN_SECRET", raising=False)
    monkeypatch.setenv("TURN_URLS", "turn:turn.example.com:3478")
    monkeypatch.setenv("STUN_URLS", "stun:stun.example.com:3478")
    monkeypatch.setenv("TURN_USERNAME", "static-u")
    monkeypatch.setenv("TURN_CREDENTIAL", "static-c")
    servers = voip_config.get_ice_servers(user_key="c-1")
    turn = [s for s in servers if any(u.startswith("turn:") for u in s["urls"])]
    stun = [s for s in servers if any(u.startswith("stun:") for u in s["urls"])]
    assert turn and stun
    assert turn[0]["username"] == "static-u"
    assert turn[0]["credential"] == "static-c"


def test_turn_ttl_unprefixed_alias(monkeypatch):
    monkeypatch.delenv("VOIP_TURN_TOKEN_TTL_SEC", raising=False)
    monkeypatch.setenv("TURN_TTL", "3600")
    monkeypatch.setenv("TURN_SECRET", "s")
    creds = voip_config.dynamic_turn_credentials("u", now=100)
    assert creds is not None and creds[0] == "3700:u"


# ---- #7 메트릭 ----

def test_metrics_record_functions_never_throw():
    # prometheus_client 유무와 무관하게 예외 없이 동작해야 한다.
    voip_metrics.record_call_initiated("app", "designated")
    voip_metrics.record_turn_issued("dynamic")
    voip_metrics.ws_connected("caller")
    voip_metrics.record_signaling_message("offer", "caller")
    voip_metrics.record_signaling_error("auth_failed")
    voip_metrics.observe_call_join_latency(1.5)
    voip_metrics.observe_call_join_latency(-1)  # 음수는 무시(throw 금지)
    voip_metrics.observe_call_join_latency(None)  # type: ignore[arg-type]
    voip_metrics.ws_disconnected()


def test_metrics_exposed_in_registry():
    try:
        from prometheus_client import generate_latest
    except Exception:  # pragma: no cover - 의존성 없으면 스킵
        return
    voip_metrics.record_call_initiated("app", "designated")
    voip_metrics.record_signaling_message("answer", "callee")
    body = generate_latest().decode("utf-8", errors="ignore")
    assert "voip_calls_initiated_total" in body
    assert "voip_signaling_messages_total" in body
    assert "voip_active_ws_connections" in body
