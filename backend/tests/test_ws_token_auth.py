"""[#6] WebSocket 토큰 추출 helper 단위 테스트.

Sec-WebSocket-Protocol 우선 + ?token= 레거시 폴백(무중단 점진 전환) 검증.
"""
from __future__ import annotations

from backend.auth import resolve_ws_token


class _FakeHeaders:
    def __init__(self, mapping):
        self._m = {k.lower(): v for k, v in mapping.items()}

    def get(self, key, default=None):
        return self._m.get(key.lower(), default)


class _FakeQuery:
    def __init__(self, mapping):
        self._m = dict(mapping)

    def get(self, key, default=None):
        return self._m.get(key, default)


class _FakeWebSocket:
    def __init__(self, headers=None, query=None):
        self.headers = _FakeHeaders(headers or {})
        self.query_params = _FakeQuery(query or {})


def test_header_bearer_scheme_extracts_token_and_echoes_subprotocol():
    ws = _FakeWebSocket(headers={"Sec-WebSocket-Protocol": "bearer, eyJabc.def.ghi"})
    token, sub = resolve_ws_token(ws)
    assert token == "eyJabc.def.ghi"
    assert sub == "bearer"


def test_header_access_token_scheme():
    ws = _FakeWebSocket(headers={"sec-websocket-protocol": "access_token, TKN"})
    token, sub = resolve_ws_token(ws)
    assert token == "TKN"
    assert sub == "access_token"


def test_legacy_query_token_fallback_no_subprotocol():
    ws = _FakeWebSocket(query={"token": "legacy-jwt"})
    token, sub = resolve_ws_token(ws)
    assert token == "legacy-jwt"
    assert sub is None


def test_unrecognized_subprotocol_falls_back_to_query():
    ws = _FakeWebSocket(headers={"Sec-WebSocket-Protocol": "graphql-ws"}, query={"token": "q"})
    token, sub = resolve_ws_token(ws)
    assert token == "q"
    assert sub is None


def test_explicit_query_token_arg_overrides_query_params():
    ws = _FakeWebSocket(query={"token": "from-params"})
    token, sub = resolve_ws_token(ws, "from-arg")
    assert token == "from-arg"
    assert sub is None


def test_nothing_provided_returns_empty():
    ws = _FakeWebSocket()
    token, sub = resolve_ws_token(ws)
    assert token == ""
    assert sub is None
