"""
Redis 캐싱 서비스
"""
import json
import os
from typing import Any, Optional

Redis = globals().get("Redis")
RedisError = globals().get("RedisError")
if Redis is None:
    try:
        from redis import Redis as _Redis
        from redis.exceptions import RedisError as _RedisError
        Redis = _Redis
        RedisError = _RedisError
    except Exception:  # pragma: no cover - dependency may be absent in local/test envs
        Redis = None  # type: ignore[assignment]
        class RedisError(Exception):
            pass

class CacheService:
    """Redis 기반 캐싱 서비스.

    로그인 경로에서 키를 DB 우회하는 목적의 캐시이므로, 모듈 import 시점에 Redis
    ping 을 수행해 연결 시간을 늘리는 것은 매우 비싸다. 초기화는 즉시 반환하고,
    실제 사용 시점에 lazy 연결을 시도해 느린/불가한 Redis 환경에서도 요청이
    멈추지 않도록 한다.
    """

    def __init__(self):
        """Redis 클라이언트는 즉시 생성하지 않고 lazy 연결로 전환한다."""
        self.client = None
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.socket_connect_timeout = float(os.getenv("REDIS_CONNECT_TIMEOUT_SEC", "0.35"))
        self.socket_timeout = float(os.getenv("REDIS_TIMEOUT_SEC", "0.35"))
        if Redis is not None and os.getenv("CACHE_SERVICE_DISABLED", "0").strip().lower() not in {"1", "true", "yes", "on"}:
            try:
                Redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=self.socket_connect_timeout,
                    socket_timeout=self.socket_timeout,
                    health_check_interval=30,
                )
            except Exception:
                pass

    def _connect(self):
        if self.client is not None:
            return self.client
        if Redis is None:
            return None
        if os.getenv("CACHE_SERVICE_DISABLED", "0").strip().lower() in {"1", "true", "yes", "on"}:
            return None
        try:
            self.client = Redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=self.socket_connect_timeout,
                socket_timeout=self.socket_timeout,
                health_check_interval=30,
            )
            return self.client
        except RedisError:
            self.client = None
            return None
        except Exception:
            self.client = None
            return None
    
    def get(self, key: str) -> Optional[Any]:
        """캐시에서 데이터 조회
        
        Args:
            key: 캐시 키
            
        Returns:
            캐시된 데이터 또는 None
        """
        client = self._connect()
        if not client:
            return None
        
        try:
            data = client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"❌ 캐시 조회 실패 ({key}): {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """캐시에 데이터 저장
        
        Args:
            key: 캐시 키
            value: 저장할 데이터
            ttl: 유효 시간 (초)
            
        Returns:
            성공 여부
        """
        client = self._connect()
        if not client:
            return False
        
        try:
            client.setex(key, ttl, json.dumps(value))
            return True
        except Exception as e:
            print(f"❌ 캐시 저장 실패 ({key}): {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """캐시에서 데이터 삭제
        
        Args:
            key: 캐시 키
            
        Returns:
            성공 여부
        """
        client = self._connect()
        if not client:
            return False
        
        try:
            client.delete(key)
            return True
        except Exception as e:
            print(f"❌ 캐시 삭제 실패 ({key}): {e}")
            return False
    
    def clear(self) -> bool:
        """모든 캐시 삭제
        
        Returns:
            성공 여부
        """
        client = self._connect()
        if not client:
            return False
        
        try:
            client.flushdb()
            return True
        except Exception as e:
            print(f"❌ 캐시 전체 삭제 실패: {e}")
            return False
    
    def get_stats(self) -> dict:
        """캐시 통계 조회
        
        Returns:
            캐시 통계
        """
        client = self._connect()
        if not client:
            return {"status": "disconnected"}
        
        try:
            info = client.info()
            return {
                "status": "connected",
                "memory_used_mb": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "total_keys": client.dbsize()
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# 글로벌 캐시 인스턴스
cache_service = CacheService()


def cache_key(*args, prefix: str = "app") -> str:
    """캐시 키 생성
    
    Args:
        *args: 키 구성 요소
        prefix: 키 접두사
        
    Returns:
        생성된 캐시 키
    """
    return f"{prefix}:{':'.join(str(arg) for arg in args)}"
