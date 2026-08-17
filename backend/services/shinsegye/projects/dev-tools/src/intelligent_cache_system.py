#!/usr/bin/env python3
"""
🚀 Sorisae 지능형 캐싱 시스템 v2.0

고급 캐싱 전략과 자동 최적화를 제공하는 지능형 캐시 시스템
- LRU/LFU 다중 캐시 전략
- TTL 기반 자동 만료
- 성능 메트릭 기반 자동 최적화
- 메모리 사용량 자동 관리
- 캐시 히트율 실시간 모니터링

Created: 2024-12-19
Author: Sorisae Team
"""

import asyncio
import gc
import hashlib
import sys
import threading
import time
from collections import OrderedDict, defaultdict
from dataclasses import asdict, dataclass
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union


@dataclass
class CacheEntry:
    """캐시 엔트리 데이터 구조"""
    value: Any
    created_at: float
    last_accessed: float
    access_count: int
    ttl: Optional[float]
    size: int

    def is_expired(self) -> bool:
        """TTL 기반 만료 확인"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl

    def touch(self):
        """액세스 시간 업데이트"""
        self.last_accessed = time.time()
        self.access_count += 1


@dataclass
class CacheStats:
    """캐시 통계 정보"""
    hits: int = 0
    misses: int = 0
    total_requests: int = 0
    cache_size: int = 0
    memory_usage: int = 0
    hit_rate: float = 0.0
    avg_access_time: float = 0.0

    def update_hit_rate(self):
        """히트율 업데이트"""
        if self.total_requests > 0:
            self.hit_rate = self.hits / self.total_requests * 100


class LRUCache:
    """고성능 LRU 캐시 구현"""

    def __init__(self, max_size: int = 1000, default_ttl: Optional[float] = None):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self.stats = CacheStats()

    def _calculate_size(self, value: Any) -> int:
        """객체 크기 계산"""
        try:
            return sys.getsizeof(value)
        except Exception:
            return 100  # 기본값

    def _evict_expired(self):
        """만료된 항목 제거"""
        time.time()
        expired_keys = []

        for key, entry in self._cache.items():
            if entry.is_expired():
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache[key]

    def _evict_lru(self):
        """LRU 정책으로 항목 제거"""
        if len(self._cache) >= self.max_size:
            # 가장 오래된 항목 제거
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

    def get(self, key: str, default: Any = None) -> Any:
        """캐시에서 값 가져오기"""
        start_time = time.time()

        with self._lock:
            self.stats.total_requests += 1

            # 만료된 항목 제거
            self._evict_expired()

            if key in self._cache:
                entry = self._cache[key]

                if not entry.is_expired():
                    # LRU 순서 업데이트
                    self._cache.move_to_end(key)
                    entry.touch()

                    self.stats.hits += 1
                    self.stats.update_hit_rate()
                    self.stats.avg_access_time = (time.time() - start_time) * 1000

                    return entry.value
                else:
                    # 만료된 항목 제거
                    del self._cache[key]

            self.stats.misses += 1
            self.stats.update_hit_rate()

            return default

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """캐시에 값 저장"""
        with self._lock:
            # 공간 확보
            self._evict_expired()
            self._evict_lru()

            # 새 엔트리 생성
            size = self._calculate_size(value)
            entry = CacheEntry(
                value=value,
                created_at=time.time(),
                last_accessed=time.time(),
                access_count=1,
                ttl=ttl or self.default_ttl,
                size=size
            )

            self._cache[key] = entry
            self._cache.move_to_end(key)

            # 통계 업데이트
            self.stats.cache_size = len(self._cache)
            self.stats.memory_usage = sum(entry.size for entry in self._cache.values())

            return True

    def delete(self, key: str) -> bool:
        """캐시에서 항목 삭제"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self.stats.cache_size = len(self._cache)
                self.stats.memory_usage = sum(entry.size for entry in self._cache.values())
                return True
            return False

    def clear(self):
        """캐시 전체 삭제"""
        with self._lock:
            self._cache.clear()
            self.stats = CacheStats()

    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환"""
        with self._lock:
            return asdict(self.stats)


class LFUCache:
    """Least Frequently Used 캐시 구현"""

    def __init__(self, max_size: int = 1000, default_ttl: Optional[float] = None):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._frequencies: Dict[str, int] = defaultdict(int)
        self._lock = threading.RLock()
        self.stats = CacheStats()

    def _evict_lfu(self):
        """LFU 정책으로 항목 제거"""
        if len(self._cache) >= self.max_size:
            # 가장 적게 사용된 항목 찾기
            min_freq_key = min(self._frequencies, key=self._frequencies.get)
            del self._cache[min_freq_key]
            del self._frequencies[min_freq_key]

    def get(self, key: str, default: Any = None) -> Any:
        """캐시에서 값 가져오기"""
        with self._lock:
            self.stats.total_requests += 1

            if key in self._cache:
                entry = self._cache[key]

                if not entry.is_expired():
                    entry.touch()
                    self._frequencies[key] += 1

                    self.stats.hits += 1
                    self.stats.update_hit_rate()

                    return entry.value
                else:
                    # 만료된 항목 제거
                    del self._cache[key]
                    del self._frequencies[key]

            self.stats.misses += 1
            self.stats.update_hit_rate()

            return default

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """캐시에 값 저장"""
        with self._lock:
            # 공간 확보
            self._evict_lfu()

            # 새 엔트리 생성
            size = sys.getsizeof(value) if hasattr(sys, 'getsizeof') else 100
            entry = CacheEntry(
                value=value,
                created_at=time.time(),
                last_accessed=time.time(),
                access_count=1,
                ttl=ttl or self.default_ttl,
                size=size
            )

            self._cache[key] = entry
            self._frequencies[key] = 1

            # 통계 업데이트
            self.stats.cache_size = len(self._cache)
            self.stats.memory_usage = sum(entry.size for entry in self._cache.values())

            return True


class AdaptiveCache:
    """성능 기반 적응형 캐시 시스템"""

    def __init__(self, max_size: int = 2000, analysis_interval: int = 100):
        self.max_size = max_size
        self.analysis_interval = analysis_interval

        # 다중 캐시 전략
        self.lru_cache = LRUCache(max_size // 2)
        self.lfu_cache = LFUCache(max_size // 2)

        # 성능 분석
        self.request_count = 0
        self.performance_history: List[Dict[str, float]] = []
        self.current_strategy = "lru"  # lru, lfu, adaptive

        self._lock = threading.RLock()

    def _analyze_performance(self):
        """성능 분석 및 전략 조정"""
        if self.request_count % self.analysis_interval == 0:
            lru_stats = self.lru_cache.get_stats()
            lfu_stats = self.lfu_cache.get_stats()

            # 성능 메트릭 계산
            lru_score = lru_stats.get('hit_rate', 0) * 0.7 + \
                (100 - lru_stats.get('avg_access_time', 100)) * 0.3
            lfu_score = lfu_stats.get('hit_rate', 0) * 0.7 + \
                (100 - lfu_stats.get('avg_access_time', 100)) * 0.3

            # 최적 전략 선택
            if lru_score > lfu_score * 1.1:
                self.current_strategy = "lru"
            elif lfu_score > lru_score * 1.1:
                self.current_strategy = "lfu"
            else:
                self.current_strategy = "adaptive"

            # 성능 히스토리 저장
            self.performance_history.append({
                'timestamp': time.time(),
                'lru_score': lru_score,
                'lfu_score': lfu_score,
                'strategy': self.current_strategy
            })

            # 히스토리 크기 제한
            if len(self.performance_history) > 100:
                self.performance_history = self.performance_history[-100:]

    def get(self, key: str, default: Any = None) -> Any:
        """적응형 캐시에서 값 가져오기"""
        with self._lock:
            self.request_count += 1

            # 전략별 캐시 선택
            if self.current_strategy == "lru":
                result = self.lru_cache.get(key, None)
                if result is not None:
                    return result
                return self.lfu_cache.get(key, default)

            elif self.current_strategy == "lfu":
                result = self.lfu_cache.get(key, None)
                if result is not None:
                    return result
                return self.lru_cache.get(key, default)

            else:  # adaptive
                # 두 캐시에서 모두 확인
                lru_result = self.lru_cache.get(key, None)
                lfu_result = self.lfu_cache.get(key, None)

                if lru_result is not None:
                    return lru_result
                elif lfu_result is not None:
                    return lfu_result
                else:
                    return default

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """적응형 캐시에 값 저장"""
        with self._lock:
            # 성능 분석
            self._analyze_performance()

            # 전략별 저장
            if self.current_strategy == "lru":
                return self.lru_cache.set(key, value, ttl)
            elif self.current_strategy == "lfu":
                return self.lfu_cache.set(key, value, ttl)
            else:  # adaptive
                # 두 캐시에 모두 저장 (공간이 허용하는 경우)
                success1 = self.lru_cache.set(key, value, ttl)
                success2 = self.lfu_cache.set(key, value, ttl)
                return success1 or success2

    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """종합 통계 정보"""
        lru_stats = self.lru_cache.get_stats()
        lfu_stats = self.lfu_cache.get_stats()

        return {
            'current_strategy': self.current_strategy,
            'total_requests': self.request_count,
            'lru_cache': lru_stats,
            'lfu_cache': lfu_stats,
            'performance_history': self.performance_history[-10:],  # 최근 10개
        }


class IntelligentCacheManager:
    """지능형 캐시 관리자"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
            'max_memory_mb': 100,
            'default_ttl': 3600,  # 1시간
            'auto_cleanup_interval': 300,  # 5분
            'performance_analysis_interval': 1000
        }

        # 캐시 인스턴스들
        self.caches: Dict[str, Union[LRUCache, LFUCache, AdaptiveCache]] = {}

        # 전역 통계
        self.global_stats = {
            'total_memory_usage': 0,
            'total_cache_size': 0,
            'active_caches': 0,
            'cleanup_runs': 0
        }

        # 자동 정리 타이머
        self._cleanup_timer: Optional[threading.Timer] = None
        self._start_auto_cleanup()

        print("🚀 지능형 캐시 관리자 초기화 완료")

    def create_cache(self, name: str, cache_type: str = "adaptive",
                     max_size: int = 1000, ttl: Optional[float] = None) -> bool:
        """새 캐시 인스턴스 생성"""
        try:
            ttl = ttl or self.config['default_ttl']

            if cache_type == "lru":
                cache = LRUCache(max_size, ttl)
            elif cache_type == "lfu":
                cache = LFUCache(max_size, ttl)
            elif cache_type == "adaptive":
                cache = AdaptiveCache(max_size)
            else:
                raise ValueError(f"지원하지 않는 캐시 타입: {cache_type}")

            self.caches[name] = cache
            self.global_stats['active_caches'] = len(self.caches)

            print(f"✅ {cache_type.upper()} 캐시 '{name}' 생성 (크기: {max_size}, TTL: {ttl}초)")
            return True

        except Exception as e:
            print(f"❌ 캐시 생성 실패: {e}")
            return False

    def get_cache(self, name: str) -> Optional[Union[LRUCache, LFUCache, AdaptiveCache]]:
        """캐시 인스턴스 가져오기"""
        return self.caches.get(name)

    def _start_auto_cleanup(self):
        """자동 정리 시작"""

        def cleanup():
            self._perform_cleanup()
            # 다음 정리 스케줄
            self._cleanup_timer = threading.Timer(
                self.config['auto_cleanup_interval'],
                cleanup
            )
            self._cleanup_timer.start()

        self._cleanup_timer = threading.Timer(
            self.config['auto_cleanup_interval'],
            cleanup
        )
        self._cleanup_timer.start()

    def _perform_cleanup(self):
        """메모리 정리 수행"""
        try:
            total_memory = 0
            total_size = 0

            for name, cache in self.caches.items():
                if hasattr(cache, 'stats'):
                    stats = cache.get_stats() if hasattr(cache, 'get_stats') else cache.stats
                    if isinstance(stats, dict):
                        total_memory += stats.get('memory_usage', 0)
                        total_size += stats.get('cache_size', 0)
                    else:
                        total_memory += getattr(stats, 'memory_usage', 0)
                        total_size += getattr(stats, 'cache_size', 0)

            self.global_stats.update({
                'total_memory_usage': total_memory,
                'total_cache_size': total_size,
                'cleanup_runs': self.global_stats['cleanup_runs'] + 1
            })

            # 메모리 사용량이 임계값을 초과하면 강제 정리
            max_memory_bytes = self.config['max_memory_mb'] * 1024 * 1024
            if total_memory > max_memory_bytes:
                self._force_cleanup()

        except Exception as e:
            print(f"⚠️ 자동 정리 중 오류: {e}")

    def _force_cleanup(self):
        """강제 메모리 정리"""
        print("🧹 메모리 사용량 초과 - 강제 정리 시작")

        for name, cache in self.caches.items():
            if hasattr(cache, '_evict_expired'):
                cache._evict_expired()

        # 가비지 컬렉션 실행
        gc.collect()

        print("✅ 강제 정리 완료")

    def get_global_stats(self) -> Dict[str, Any]:
        """전역 통계 정보"""
        cache_stats = {}
        for name, cache in self.caches.items():
            if hasattr(cache, 'get_stats'):
                cache_stats[name] = cache.get_stats()
            elif hasattr(cache, 'get_comprehensive_stats'):
                cache_stats[name] = cache.get_comprehensive_stats()

        return {
            'global': self.global_stats,
            'caches': cache_stats,
            'config': self.config
        }

    def shutdown(self):
        """캐시 매니저 종료"""
        if self._cleanup_timer:
            self._cleanup_timer.cancel()

        for cache in self.caches.values():
            if hasattr(cache, 'clear'):
                cache.clear()

        self.caches.clear()
        print("🔄 캐시 매니저 종료 완료")


def cache_decorator(cache_name: str = "default", ttl: Optional[float] = None,
                    key_func: Optional[Callable] = None):
    """함수 결과 캐싱 데코레이터"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = hashlib.sha256("|".join(key_parts).encode()).hexdigest()

            # 전역 캐시 매니저에서 캐시 가져오기
            if not hasattr(wrapper, '_cache_manager'):
                wrapper._cache_manager = IntelligentCacheManager()
                wrapper._cache_manager.create_cache(cache_name, "adaptive")

            cache = wrapper._cache_manager.get_cache(cache_name)
            if not cache:
                return func(*args, **kwargs)

            # 캐시에서 결과 확인
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # 함수 실행 및 결과 캐싱
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)

            return result

        return wrapper
    return decorator


async def async_cache_test():
    """비동기 캐시 테스트"""
    print("\n🔧 비동기 캐시 시스템 테스트")

    cache_manager = IntelligentCacheManager({
        'max_memory_mb': 50,
        'default_ttl': 60,
        'auto_cleanup_interval': 30
    })

    # 다양한 캐시 타입 생성
    cache_manager.create_cache("lru_test", "lru", 100)
    cache_manager.create_cache("lfu_test", "lfu", 100)
    cache_manager.create_cache("adaptive_test", "adaptive", 200)

    # 병렬 캐시 작업
    async def cache_worker(cache_name: str, worker_id: int):
        cache = cache_manager.get_cache(cache_name)
        if not cache:
            return

        for i in range(100):
            key = f"worker_{worker_id}_item_{i}"
            value = f"data_{i}" * 10

            cache.set(key, value)

            # 일부 값 다시 읽기 (캐시 히트 시뮬레이션)
            if i % 3 == 0:
                retrieved = cache.get(key)
                assert retrieved == value

            await asyncio.sleep(0.001)  # 작은 지연

    # 병렬 작업 실행
    tasks = []
    for cache_name in ["lru_test", "lfu_test", "adaptive_test"]:
        for worker_id in range(3):
            task = cache_worker(cache_name, worker_id)
            tasks.append(task)

    start_time = time.time()
    await asyncio.gather(*tasks)
    execution_time = time.time() - start_time

    # 결과 출력
    stats = cache_manager.get_global_stats()

    print(f"\n📊 캐시 테스트 결과:")
    print(f"⏱️ 실행 시간: {execution_time:.2f}초")
    print(f"🗄️ 활성 캐시: {stats['global']['active_caches']}개")
    print(f"💾 총 메모리 사용량: {stats['global']['total_memory_usage']:,} bytes")
    print(f"📦 총 캐시 아이템: {stats['global']['total_cache_size']}개")

    for cache_name, cache_stats in stats['caches'].items():
        if isinstance(cache_stats, dict):
            hit_rate = cache_stats.get('hit_rate', 0)
            total_requests = cache_stats.get('total_requests', 0)
            print(f"  📈 {cache_name}: 히트율 {hit_rate:.1f}% ({total_requests} 요청)")

    cache_manager.shutdown()
    print("✅ 지능형 캐싱 시스템 테스트 완료!")


def main():
    """메인 실행 함수"""
    print("🚀 Sorisae 지능형 캐싱 시스템 v2.0")
    print("=" * 50)

    # 비동기 테스트 실행
    try:
        asyncio.run(async_cache_test())
    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의해 중단됨")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
