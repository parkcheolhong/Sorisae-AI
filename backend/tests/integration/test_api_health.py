"""
통합 테스트: 핵심 API 엔드포인트 헬스체크

실행:
  pytest backend/tests/integration/test_api_health.py -v
"""
from __future__ import annotations

import pytest


class TestHealthEndpoints:
    """헬스체크 엔드포인트 통합 테스트"""

    def test_root_health_returns_200(self, test_client):
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_api_health_returns_200(self, test_client):
        response = test_client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_health_head_returns_200(self, test_client):
        response = test_client.head("/health")
        assert response.status_code == 200


class TestMetricsEndpoints:
    """Prometheus 메트릭 엔드포인트 통합 테스트"""

    def test_metrics_returns_text(self, test_client):
        response = test_client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")

    def test_metrics_summary_returns_json(self, test_client):
        response = test_client.get("/api/metrics/summary")
        assert response.status_code == 200
        data = response.json()
        assert "http_requests_total" in data
        assert "active_connections" in data


class TestMarketplaceEndpoints:
    """마켓플레이스 API 기본 통합 테스트"""

    def test_projects_list(self, test_client):
        response = test_client.get("/api/marketplace/projects")
        assert response.status_code == 200
        data = response.json()
        assert "projects" in data

    def test_categories_list(self, test_client):
        response = test_client.get("/api/marketplace/categories")
        assert response.status_code == 200

    def test_semantic_search_empty_query(self, test_client):
        response = test_client.get("/api/marketplace/search/semantic?q=")
        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []
        assert data["count"] == 0

    def test_vector_search_stats(self, test_client):
        response = test_client.get("/api/marketplace/search/stats")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_campaign_strategies(self, test_client):
        response = test_client.get("/api/marketplace/campaign-orchestrate/strategies")
        assert response.status_code == 200
        data = response.json()
        assert "strategies" in data
        assert "campaign_goals" in data


class TestAuthEndpoints:
    """인증 API 기본 통합 테스트"""

    def test_login_without_credentials_returns_error(self, test_client):
        response = test_client.post(
            "/api/auth/login",
            data={"username": "", "password": ""},
        )
        # 자격 증명 없이는 401 또는 422 반환
        assert response.status_code in (401, 422, 400)

    def test_me_without_token_returns_401(self, test_client):
        response = test_client.get("/api/auth/me")
        assert response.status_code in (401, 403)
