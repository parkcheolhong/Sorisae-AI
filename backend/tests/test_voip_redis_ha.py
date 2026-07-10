"""#4 Redis HA — 연결 모드 결정(_client_plan) 단위 테스트.

순수 결정 로직이라 redis 미설치/서버 없이도 검증 가능. 실제 연결(get_client)은
운영 통합 단계에서 Sentinel/Cluster 환경으로 확인한다.
"""

from backend.voip import redis_backend as rb


def _clear(monkeypatch):
    for k in (
        "VOIP_REDIS_SENTINELS", "VOIP_REDIS_SENTINEL_MASTER", "VOIP_REDIS_CLUSTER",
        "VOIP_REDIS_MAX_CONNECTIONS", "VOIP_REDIS_HEALTH_CHECK_INTERVAL",
        "VOIP_REDIS_SOCKET_TIMEOUT", "VOIP_REDIS_SOCKET_CONNECT_TIMEOUT",
    ):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("VOIP_REDIS_URL", "redis://redis:6379/1")


def test_plan_standalone_default(monkeypatch):
    _clear(monkeypatch)
    mode, plan = rb._client_plan()
    assert mode == "standalone"
    assert plan["url"] == "redis://redis:6379/1"
    common = plan["common"]
    assert common["max_connections"] == 50
    assert common["health_check_interval"] == 30
    assert common["retry_on_timeout"] is True
    assert common["decode_responses"] is True


def test_plan_sentinel(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("VOIP_REDIS_SENTINELS", "s1:26379, s2:26380 ,s3")
    mode, plan = rb._client_plan()
    assert mode == "sentinel"
    assert plan["sentinels"] == [("s1", 26379), ("s2", 26380), ("s3", 26379)]
    assert plan["master"] == "mymaster"  # default


def test_plan_sentinel_master_override(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("VOIP_REDIS_SENTINELS", "s1:26379")
    monkeypatch.setenv("VOIP_REDIS_SENTINEL_MASTER", "voip-master")
    mode, plan = rb._client_plan()
    assert mode == "sentinel" and plan["master"] == "voip-master"


def test_plan_cluster_optin(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("VOIP_REDIS_CLUSTER", "true")
    mode, plan = rb._client_plan()
    assert mode == "cluster"
    assert plan["url"] == "redis://redis:6379/1"


def test_plan_sentinel_takes_precedence_over_cluster(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("VOIP_REDIS_SENTINELS", "s1:26379")
    monkeypatch.setenv("VOIP_REDIS_CLUSTER", "true")
    mode, _ = rb._client_plan()
    assert mode == "sentinel"


def test_plan_tuning_overrides(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("VOIP_REDIS_MAX_CONNECTIONS", "120")
    monkeypatch.setenv("VOIP_REDIS_SOCKET_TIMEOUT", "2.5")
    monkeypatch.setenv("VOIP_REDIS_HEALTH_CHECK_INTERVAL", "10")
    _, plan = rb._client_plan()
    common = plan["common"]
    assert common["max_connections"] == 120
    assert common["socket_timeout"] == 2.5
    assert common["health_check_interval"] == 10
