import pytest

from app.core.security import build_security_headers, get_allowed_hosts, get_cors_allow_origins


def test_app_security_defaults_are_explicit(monkeypatch):
    monkeypatch.delenv('ALLOWED_HOSTS', raising=False)
    monkeypatch.delenv('CORS_ALLOW_ORIGINS', raising=False)

    headers = build_security_headers()

    assert chr(42) not in headers['allowed_hosts']
    assert chr(42) not in headers['cors_allow_origins']
    assert headers['allowed_hosts'] == ['localhost', '127.0.0.1']
    assert headers['cors_allow_origins'] == [
        'http://localhost:8000',
        'http://127.0.0.1:8000',
    ]


def test_app_security_env_values_are_explicit(monkeypatch):
    monkeypatch.setenv('ALLOWED_HOSTS', 'metanova1004.com,admin.metanova1004.com')
    monkeypatch.setenv('CORS_ALLOW_ORIGINS', 'https://metanova1004.com,https://admin.metanova1004.com')

    assert get_allowed_hosts() == ['metanova1004.com', 'admin.metanova1004.com']
    assert get_cors_allow_origins() == ['https://metanova1004.com', 'https://admin.metanova1004.com']


def test_app_security_rejects_wildcards(monkeypatch):
    wildcard = chr(42)

    monkeypatch.setenv('ALLOWED_HOSTS', wildcard)
    with pytest.raises(RuntimeError, match='ALLOWED_HOSTS'):
        get_allowed_hosts()

    monkeypatch.setenv('ALLOWED_HOSTS', 'localhost')
    monkeypatch.setenv('CORS_ALLOW_ORIGINS', wildcard)
    with pytest.raises(RuntimeError, match='CORS_ALLOW_ORIGINS'):
        get_cors_allow_origins()