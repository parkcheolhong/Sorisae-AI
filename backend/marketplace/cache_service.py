"""
Redis 캐싱 서비스
"""
import json
import os
from typing import Any, Optional
from redis import Redis
from redis.exceptions import RedisError

class CacheService:
    """Redis 기반 캐싱 서비스"""
    
    def __init__(self):
        """Redis 클라이언트 초기화"""
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self.client = Redis.from_url(redis_url, decode_responses=True)
            # 연결 테스트
            self.client.ping()
            print("✅ Redis 연결 성공")
        except RedisError as e:
            print(f"⚠️ Redis 연결 실패: {e}")
            print("⚠️ 캐싱이 비활성화됩니다")
            self.client = None
    
    def get(self, key: str) -> Optional[Any]:
        """캐시에서 데이터 조회
        
        Args:
            key: 캐시 키
            
        Returns:
            캐시된 데이터 또는 None
        """
        if not self.client:
            return None
        
        try:
            data = self.client.get(key)
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
        if not self.client:
            return False
        
        try:
            self.client.setex(key, ttl, json.dumps(value))
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
        if not self.client:
            return False
        
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            print(f"❌ 캐시 삭제 실패 ({key}): {e}")
            return False
    
    def clear(self) -> bool:
        """모든 캐시 삭제
        
        Returns:
            성공 여부
        """
        if not self.client:
            return False
        
        try:
            self.client.flushdb()
            return True
        except Exception as e:
            print(f"❌ 캐시 전체 삭제 실패: {e}")
            return False
    
    def get_stats(self) -> dict:
        """캐시 통계 조회
        
        Returns:
            캐시 통계
        """
        if not self.client:
            return {"status": "disconnected"}
        
        try:
            info = self.client.info()
            return {
                "status": "connected",
                "memory_used_mb": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "total_keys": self.client.dbsize()
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
