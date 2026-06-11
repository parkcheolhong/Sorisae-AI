"""P3-C: TURN 시간제한 토큰(coturn use-auth-secret) 단위 테스트."""
import base64
import time

from backend.voip import config as voip_config


def test_dynamic_turn_credentials_disabled_without_secret(monkeypatch):
    monkeypatch.delenv("VOIP_TURN_STATIC_AUTH_SECRET", raising=False)
    assert voip_config.dynamic_turn_credentials("user-1") is None


def test_dynamic_turn_credentials_hmac_and_expiry(monkeypatch):
    secret = "test-turn-secret"
    monkeypatch.setenv("VOIP_TURN_STATIC_AUTH_SECRET", secret)
    monkeypatch.setenv("VOIP_TURN_TOKEN_TTL_SEC", "3600")

    now = 1_000_000
    creds = voip_config.dynamic_turn_credentials("user-42", now=now)
    assert creds is not None
    username, credential = creds

    # username = "<expiry>:<user_key>", expiry = now + ttl
    assert username == f"{now + 3600}:user-42"

    expected = voip_config.dynamic_turn_credentials("user-42", now=now)
    assert expected is not None
    _, expected_credential = expected
    assert credential == expected_credential
    assert base64.b64decode(credential.encode("ascii"))

    # expiry는 미래 시점이어야 함
    expiry = int(username.split(":", 1)[0])
    assert expiry > now


def test_get_ice_servers_uses_dynamic_turn_when_secret_set(monkeypatch):
    monkeypatch.setenv("VOIP_TURN_STATIC_AUTH_SECRET", "s3cr3t")
    monkeypatch.setenv("VOIP_TURN_URLS", "turn:turn.example.com:3478")
    monkeypatch.setenv("VOIP_STUN_URLS", "stun:stun.l.google.com:19302")

    servers = voip_config.get_ice_servers(user_key="caller-7")
    stun = [s for s in servers if any(u.startswith("stun:") for u in s["urls"])]
    turn = [s for s in servers if any(u.startswith("turn:") for u in s["urls"])]
    assert stun and turn
    turn0 = turn[0]
    assert turn0["username"].endswith(":caller-7")
    assert turn0.get("credential")


def test_get_ice_servers_static_fallback(monkeypatch):
    monkeypatch.delenv("VOIP_TURN_STATIC_AUTH_SECRET", raising=False)
    monkeypatch.setenv("VOIP_TURN_URLS", "turn:turn.example.com:3478")
    monkeypatch.setenv("VOIP_TURN_USERNAME", "static-user")
    monkeypatch.setenv("VOIP_TURN_CREDENTIAL", "static-pass")

    servers = voip_config.get_ice_servers()
    turn = [s for s in servers if any(u.startswith("turn:") for u in s["urls"])][0]
    assert turn["username"] == "static-user"
    assert turn["credential"] == "static-pass"
