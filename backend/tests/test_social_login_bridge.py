from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.auth_router import router as auth_router
import backend.auth_router as auth_router_module
import backend.database as database_module
from backend.database import Base, get_db
from backend.marketplace import models


class _FakeResponse:
    def __init__(self, payload: dict[str, object]):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


class _FakeHttpxClient:
    def __init__(self, *args, **kwargs):
        self.requests: list[tuple[str, str, dict[str, str] | None]] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def request(self, method: str, url: str, data=None, headers=None):
        self.requests.append((method, url, headers))
        if url.endswith('/token'):
            return _FakeResponse(
                {
                    'access_token': 'provider-access-token',
                    'refresh_token': 'provider-refresh-token',
                    'id_token': 'provider-id-token',
                    'expires_in': 3600,
                }
            )
        raise AssertionError(f'unexpected request: {method} {url}')

    def get(self, url: str, headers=None):
        self.requests.append(('GET', url, headers))
        if url.endswith('/userinfo') or url.endswith('/v1/userinfo'):
            return _FakeResponse(
                {
                    'sub': 'google-user-123',
                    'email': 'user@example.com',
                    'name': 'User Name',
                }
            )
        raise AssertionError(f'unexpected request: GET {url}')


def _build_client() -> tuple[TestClient, sessionmaker[Session]]:
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    Base.metadata.create_all(bind=engine)

    app = FastAPI()
    app.include_router(auth_router, prefix='/api/auth')

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    database_module.SessionLocal = testing_session_local
    return TestClient(app), testing_session_local


def test_social_login_start_redirects_to_provider_authorization_url(monkeypatch):
    client, _ = _build_client()
    monkeypatch.setattr(auth_router_module.httpx, 'Client', _FakeHttpxClient)
    monkeypatch.setenv('GOOGLE_CLIENT_ID', 'google-client-id')
    monkeypatch.setenv('GOOGLE_CLIENT_SECRET', 'google-client-secret')
    monkeypatch.setenv('SOCIAL_LOGIN_CALLBACK_BASE_URL', 'https://api.example.com')

    response = client.get(
        '/api/auth/social/google/start',
        params={'redirect_uri': 'worldlingo://auth/callback'},
        follow_redirects=False,
    )

    assert response.status_code == 302, response.text
    location = response.headers['location']
    parsed = urlparse(location)
    assert parsed.netloc == 'accounts.google.com'

    query = parse_qs(parsed.query)
    assert query['client_id'][0] == 'google-client-id'
    assert query['redirect_uri'][0] == 'https://api.example.com/api/auth/social/google/callback'
    assert query['state'][0]


def test_social_login_callback_issues_app_token_and_updates_user(monkeypatch):
    client, testing_session_local = _build_client()
    monkeypatch.setattr(auth_router_module.httpx, 'Client', _FakeHttpxClient)
    monkeypatch.setenv('GOOGLE_CLIENT_ID', 'google-client-id')
    monkeypatch.setenv('GOOGLE_CLIENT_SECRET', 'google-client-secret')
    monkeypatch.setenv('SOCIAL_LOGIN_CALLBACK_BASE_URL', 'https://api.example.com')

    start_response = client.get(
        '/api/auth/social/google/start',
        params={'redirect_uri': 'worldlingo://auth/callback'},
        follow_redirects=False,
    )
    start_location = urlparse(start_response.headers['location'])
    start_query = parse_qs(start_location.query)
    state = start_query['state'][0]

    callback_response = client.get(
        '/api/auth/social/google/callback',
        params={'code': 'provider-code', 'state': state},
        follow_redirects=False,
    )

    assert callback_response.status_code == 302, callback_response.text
    final_location = urlparse(callback_response.headers['location'])
    assert f'{final_location.scheme}://{final_location.netloc}{final_location.path}' == 'worldlingo://auth/callback'

    final_query = parse_qs(final_location.query)
    app_access_token = final_query['access_token'][0]
    assert final_query['provider'][0] == 'google'
    assert app_access_token

    me = client.get(
        '/api/auth/me',
        headers={'Authorization': f'Bearer {app_access_token}'},
    )
    assert me.status_code == 200, me.text
    assert me.json()['email'] == 'user@example.com'

    with testing_session_local() as db:
        user = db.query(models.User).filter(models.User.email == 'user@example.com').first()
        assert user is not None
        assert user.username.startswith('google_')


def test_social_login_start_rejects_bad_redirect_uri(monkeypatch):
    client, _ = _build_client()
    monkeypatch.setenv('GOOGLE_CLIENT_ID', 'google-client-id')
    monkeypatch.setenv('GOOGLE_CLIENT_SECRET', 'google-client-secret')

    response = client.get(
        '/api/auth/social/kakao/start',
        params={'redirect_uri': 'https://example.com/callback'},
        follow_redirects=False,
    )

    assert response.status_code == 400
