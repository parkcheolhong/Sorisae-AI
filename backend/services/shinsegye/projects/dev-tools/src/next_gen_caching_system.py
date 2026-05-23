#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
차세대 캐싱 시스템
메모리 효율적인 다단계 캐싱 및 자동 최적화
"""

import hashlib
import json
import sqlite3
import threading
import time
from collections import OrderedDict, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class MemoryCache:
    """메모리 캐시"""

    def __init__(self, max_size=1000, ttl=3600):
        self.max_size = max_size
        self.ttl = ttl
        self.cache = OrderedDict()
        self.access_count = defaultdict(int)
        self.timestamps = {}
        self.lock = threading.RLock()

    def get(self, key):
        """캐시에서 값 가져오기"""
        with self.lock:
            if key not in self.cache:
                return None

            # TTL 확인
            if self._is_expired(key):
                self._remove(key)
                return None

            # LRU 업데이트
            value = self.cache.pop(key)
            self.cache[key] = value
            self.access_count[key] += 1

            return value

    def set(self, key, value):
        """캐시에 값 저장"""
        with self.lock:
            # 기존 키 제거
            if key in self.cache:
                self.cache.pop(key)

            # 공간 확보
            while len(self.cache) >= self.max_size:
                self._evict_lru()

            # 새 값 저장
            self.cache[key] = value
            self.timestamps[key] = datetime.now()
            self.access_count[key] = 1

    def _is_expired(self, key):
        """만료 확인"""
        if key not in self.timestamps:
            return True

        age = datetime.now() - self.timestamps[key]
        return age.total_seconds() > self.ttl

    def _evict_lru(self):
        """LRU 방식으로 제거"""
        if not self.cache:
            return

        # 가장 적게 사용된 키 찾기
        least_used_key = min(self.cache.keys(), key=lambda k: self.access_count[k])
        self._remove(least_used_key)

    def _remove(self, key):
        """키 제거"""
        self.cache.pop(key, None)
        self.access_count.pop(key, None)
        self.timestamps.pop(key, None)

    def clear(self):
        """캐시 비우기"""
        with self.lock:
            self.cache.clear()
            self.access_count.clear()
            self.timestamps.clear()

    def stats(self):
        """캐시 통계"""
        with self.lock:
            total_access = sum(self.access_count.values())

            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'utilization': len(self.cache) / self.max_size if self.max_size > 0 else 0,
                'total_access': total_access,
                'avg_access': total_access / len(self.cache) if len(self.cache) > 0 else 0,
                'ttl': self.ttl
            }


class FileCache:
    """파일 캐시"""

    def __init__(self, cache_dir="cache", max_size_mb=100):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_size_mb = max_size_mb
        self.index_file = self.cache_dir / "cache_index.json"
        self.lock = threading.RLock()

        self.index = self._load_index()

    def _load_index(self):
        """인덱스 로드"""
        try:
            if self.index_file.exists():
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"캐시 인덱스 로드 오류: {e}")

        return {}

    def _save_index(self):
        """인덱스 저장"""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.index, f, indent=2, default=str)
        except Exception as e:
            print(f"캐시 인덱스 저장 오류: {e}")

    def _get_cache_path(self, key):
        """캐시 파일 경로"""
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"

    def get(self, key):
        """캐시에서 파일 가져오기"""
        with self.lock:
            if key not in self.index:
                return None

            entry = self.index[key]
            cache_path = self._get_cache_path(key)

            if not cache_path.exists():
                del self.index[key]
                self._save_index()
                return None

            # TTL 확인
            created_time = datetime.fromisoformat(entry['created_time'])
            if datetime.now() - created_time > timedelta(seconds=entry.get('ttl', 3600)):
                self._remove(key)
                return None

            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 액세스 정보 업데이트
                entry['last_access'] = datetime.now().isoformat()
                entry['access_count'] = entry.get('access_count', 0) + 1
                self._save_index()

                return data

            except Exception as e:
                print(f"캐시 파일 읽기 오류: {e}")
                self._remove(key)
                return None

    def set(self, key, data, ttl=3600):
        """캐시에 파일 저장"""
        with self.lock:
            try:
                # 공간 확보
                self._ensure_space()

                cache_path = self._get_cache_path(key)

                # 데이터 저장
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, default=str)
                self.index[key] = {
                    'created_time': datetime.now().isoformat(),
                    'last_access': datetime.now().isoformat(),
                    'access_count': 1,
                    'size': cache_path.stat().st_size,
                    'ttl': ttl
                }

                self._save_index()

            except Exception as e:
                print(f"캐시 파일 저장 오류: {e}")

    def _ensure_space(self):
        """공간 확보"""
        total_size = sum(entry['size'] for entry in self.index.values())
        max_size_bytes = self.max_size_mb * 1024 * 1024

        if total_size <= max_size_bytes:
            return

        # 액세스 시간 기준으로 정렬
        sorted_keys = sorted(
            self.index.keys(),
            key=lambda k: (
                self.index[k].get('access_count', 0),
                self.index[k].get('last_access', '1970-01-01')
            )
        )

        # 오래된 캐시부터 제거
        for key in sorted_keys:
            self._remove(key)
            total_size = sum(entry['size'] for entry in self.index.values())
            if total_size <= max_size_bytes * 0.8:  # 80%까지 줄임
                break

    def _remove(self, key):
        """캐시 제거"""
        if key in self.index:
            cache_path = self._get_cache_path(key)
            try:
                if cache_path.exists():
                    cache_path.unlink()
            except Exception as e:
                print(f"캐시 파일 삭제 오류: {e}")

            del self.index[key]
            self._save_index()

    def clear(self):
        """캐시 비우기"""
        with self.lock:
            try:
                for cache_file in self.cache_dir.glob("*.cache"):
                    cache_file.unlink()

                self.index.clear()
                self._save_index()

            except Exception as e:
                print(f"캐시 비우기 오류: {e}")

    def stats(self):
        """캐시 통계"""
        with self.lock:
            total_size = sum(entry['size'] for entry in self.index.values())
            total_access = sum(entry.get('access_count', 0) for entry in self.index.values())

            return {
                'entries': len(self.index),
                'total_size_mb': total_size / (1024 * 1024),
                'max_size_mb': self.max_size_mb,
                'utilization': total_size / (self.max_size_mb * 1024 * 1024) if self.max_size_mb > 0 else 0,
                'total_access': total_access,
                'avg_access': total_access / len(self.index) if len(self.index) > 0 else 0
            }

class DatabaseCache:
    """데이터베이스 캐시"""

    def __init__(self, db_path="cache.db"):
        self.db_path = db_path
        self.lock = threading.RLock()

        self.init_database()

    def init_database(self):
        """데이터베이스 초기화"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    value BLOB,
                    created_time TEXT,
                    last_access TEXT,
                    access_count INTEGER DEFAULT 1,
                    ttl INTEGER DEFAULT 3600,
                    size INTEGER
                )
            ''')

            # 인덱스 생성
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_last_access ON cache_entries(last_access)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_time ON cache_entries(created_time)')

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"데이터베이스 초기화 오류: {e}")

    def get(self, key):
        """캐시에서 값 가져오기"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT value, created_time, ttl FROM cache_entries WHERE key = ?
                ''', (key,))

                row = cursor.fetchone()
                if not row:
                    conn.close()
                    return None

                value_blob, created_time, ttl = row

                # TTL 확인
                created = datetime.fromisoformat(created_time)
                if datetime.now() - created > timedelta(seconds=ttl):
                    cursor.execute('DELETE FROM cache_entries WHERE key = ?', (key,))
                    conn.commit()
                    conn.close()
                    return None

                # 액세스 정보 업데이트
                cursor.execute('''
                    UPDATE cache_entries
                    SET last_access = ?, access_count = access_count + 1
                    WHERE key = ?
                ''', (datetime.now().isoformat(), key))

                conn.commit()
                conn.close()

                import json as _json
                return _json.loads(value_blob.decode('utf-8') if isinstance(value_blob, (bytes, bytearray)) else value_blob)

            except Exception as e:
                print(f"데이터베이스 캐시 읽기 오류: {e}")
                return None

    def set(self, key, value, ttl=3600):
        """캐시에 값 저장"""
        with self.lock:
            try:
                import json as _json
                value_blob = _json.dumps(value, ensure_ascii=False, default=str).encode('utf-8')
                now = datetime.now().isoformat()

                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT OR REPLACE INTO cache_entries
                    (key, value, created_time, last_access, access_count, ttl, size)
                    VALUES (?, ?, ?, ?, 1, ?, ?)
                ''', (key, value_blob, now, now, ttl, len(value_blob)))

                conn.commit()
                conn.close()

            except Exception as e:
                print(f"데이터베이스 캐시 저장 오류: {e}")

    def clear(self):
        """캐시 비우기"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('DELETE FROM cache_entries')
                conn.commit()
                conn.close()

            except Exception as e:
                print(f"데이터베이스 캐시 비우기 오류: {e}")

    def cleanup_expired(self):
        """만료된 항목 정리"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute('''
                    DELETE FROM cache_entries
                    WHERE datetime(created_time, '+' || ttl || ' seconds') < datetime('now')
                ''')

                deleted = cursor.rowcount
                conn.commit()
                conn.close()

                return deleted

            except Exception as e:
                print(f"만료된 캐시 정리 오류: {e}")
                return 0

    def stats(self):
        """캐시 통계"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT
                        COUNT(*) as entries,
                        SUM(size) as total_size,
                        SUM(access_count) as total_access,
                        AVG(access_count) as avg_access
                    FROM cache_entries
                ''')

                row = cursor.fetchone()
                conn.close()

                if row:
                    return {
                        'entries': row[0] or 0,
                        'total_size_mb': (row[1] or 0) / (1024 * 1024),
                        'total_access': row[2] or 0,
                        'avg_access': row[3] or 0
                    }

            except Exception as e:
                print(f"데이터베이스 캐시 통계 오류: {e}")

            return {
                'entries': 0,
                'total_size_mb': 0,
                'total_access': 0,
                'avg_access': 0
            }


class NextGenCachingSystem:
    """차세대 캐싱 시스템"""

    def __init__(self, config=None):
        self.config = config or self._default_config()

        # 다단계 캐시 초기화
        self.memory_cache = MemoryCache(
            max_size=self.config['memory']['max_size'],
            ttl=self.config['memory']['ttl']
        )

        self.file_cache = FileCache(
            cache_dir=self.config['file']['cache_dir'],
            max_size_mb=self.config['file']['max_size_mb']
        )

        self.db_cache = DatabaseCache(
            db_path=self.config['database']['db_path']
        )

        # 통계 및 모니터링
        self.stats_db = "cache_stats.db"
        self.init_stats_database()

        # 자동 정리 스레드
        self.cleanup_thread = None
        self.start_auto_cleanup()

    def _default_config(self):
        """기본 설정"""
        return {
            'memory': {
                'max_size': 1000,
                'ttl': 1800  # 30분
            },
            'file': {
                'cache_dir': 'cache',
                'max_size_mb': 500
            },
            'database': {
                'db_path': 'cache.db'
            },
            'cleanup': {
                'interval': 300,  # 5분
                'enabled': True
            }
        }

    def init_stats_database(self):
        """통계 데이터베이스 초기화"""
        try:
            conn = sqlite3.connect(self.stats_db)
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cache_operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    operation TEXT,
                    cache_type TEXT,
                    key_hash TEXT,
                    hit INTEGER,
                    response_time REAL,
                    data_size INTEGER
                )
            ''')

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"통계 데이터베이스 초기화 오류: {e}")

    def get(self, key, cache_levels=None):
        """다단계 캐시에서 값 가져오기"""
        start_time = time.time()
        cache_levels = cache_levels or ['memory', 'file', 'database']

        try:
            # 메모리 캐시 확인
            if 'memory' in cache_levels:
                value = self.memory_cache.get(key)
                if value is not None:
                    self._log_operation('get', 'memory', key, True, time.time() - start_time)
                    return value

            # 파일 캐시 확인
            if 'file' in cache_levels:
                value = self.file_cache.get(key)
                if value is not None:
                    # 메모리 캐시에도 저장 (캐시 승격)
                    if 'memory' in cache_levels:
                        self.memory_cache.set(key, value)

                    self._log_operation('get', 'file', key, True, time.time() - start_time)
                    return value

            # 데이터베이스 캐시 확인
            if 'database' in cache_levels:
                value = self.db_cache.get(key)
                if value is not None:
                    # 상위 캐시에도 저장
                    if 'memory' in cache_levels:
                        self.memory_cache.set(key, value)
                    if 'file' in cache_levels:
                        self.file_cache.set(key, value)

                    self._log_operation('get', 'database', key, True, time.time() - start_time)
                    return value

            # 캐시 미스
            self._log_operation('get', 'all', key, False, time.time() - start_time)
            return None

        except Exception as e:
            print(f"캐시 조회 오류: {e}")
            return None

    def set(self, key, value, ttl=None, cache_levels=None):
        """다단계 캐시에 값 저장"""
        start_time = time.time()
        cache_levels = cache_levels or ['memory', 'file', 'database']
        ttl = ttl or self.config['memory']['ttl']

        try:
            import json as _json
            data_size = len(_json.dumps(value, ensure_ascii=False, default=str).encode('utf-8'))

            # 각 캐시 레벨에 저장
            if 'memory' in cache_levels:
                self.memory_cache.set(key, value)

            if 'file' in cache_levels:
                self.file_cache.set(key, value, ttl)

            if 'database' in cache_levels:
                self.db_cache.set(key, value, ttl)

            self._log_operation('set', 'all', key, True, time.time() - start_time, data_size)

        except Exception as e:
            print(f"캐시 저장 오류: {e}")

    def delete(self, key):
        """모든 캐시에서 키 삭제"""
        try:
            # 메모리 캐시에서 제거
            self.memory_cache._remove(key)

            # 파일 캐시에서 제거
            self.file_cache._remove(key)

            # 데이터베이스 캐시에서 제거
            conn = sqlite3.connect(self.db_cache.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM cache_entries WHERE key = ?', (key,))
            conn.commit()
            conn.close()

        except Exception as e:
            print(f"캐시 삭제 오류: {e}")

    def clear_all(self):
        """모든 캐시 비우기"""
        try:
            self.memory_cache.clear()
            self.file_cache.clear()
            self.db_cache.clear()

            print("🧹 모든 캐시가 비워졌습니다.")

        except Exception as e:
            print(f"캐시 비우기 오류: {e}")

    def start_auto_cleanup(self):
        """자동 정리 시작"""
        if not self.config['cleanup']['enabled']:
            return

        def cleanup_worker():
            while True:
                try:
                    time.sleep(self.config['cleanup']['interval'])

                    # 만료된 항목 정리
                    deleted_count = self.db_cache.cleanup_expired()

                    if deleted_count > 0:
                        print(f"🧹 만료된 캐시 {deleted_count}개 정리됨")

                    # 시스템 메모리 부족 시 캐시 크기 줄이기
                    if PSUTIL_AVAILABLE:
                        memory_percent = psutil.virtual_memory().percent
                        if memory_percent > 85:  # 85% 이상 사용 시
                            self.memory_cache.max_size = max(100, self.memory_cache.max_size // 2)
                            print(f"⚠️ 메모리 부족으로 캐시 크기 축소: {self.memory_cache.max_size}")

                except Exception as e:
                    print(f"자동 정리 오류: {e}")

        self.cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self.cleanup_thread.start()

    def _log_operation(self, operation, cache_type, key, hit, response_time, data_size=0):
        """캐시 작업 로깅"""
        try:
            key_hash = hashlib.sha256(key.encode()).hexdigest()[:8]

            conn = sqlite3.connect(self.stats_db)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO cache_operations
                (timestamp, operation, cache_type, key_hash, hit, response_time, data_size)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                operation,
                cache_type,
                key_hash,
                1 if hit else 0,
                response_time,
                data_size
            ))

            conn.commit()
            conn.close()

        except Exception:
            pass  # 로깅 실패는 무시

    def get_comprehensive_stats(self):
        """종합 통계"""
        try:
            # 각 캐시 통계
            memory_stats = self.memory_cache.stats()
            file_stats = self.file_cache.stats()
            db_stats = self.db_cache.stats()

            # 작업 통계
            conn = sqlite3.connect(self.stats_db)
            cursor = conn.cursor()

            # 최근 1시간 히트율
            cursor.execute('''
                SELECT
                    COUNT(*) as total_ops,
                    SUM(hit) as hits,
                    AVG(response_time) as avg_response_time
                FROM cache_operations
                WHERE datetime(timestamp) > datetime('now', '-1 hour')
            ''')

            recent_stats = cursor.fetchone()

            # 캐시 타입별 성능
            cursor.execute('''
                SELECT
                    cache_type,
                    COUNT(*) as operations,
                    SUM(hit) as hits,
                    AVG(response_time) as avg_response_time
                FROM cache_operations
                WHERE datetime(timestamp) > datetime('now', '-1 hour')
                GROUP BY cache_type
            ''')

            cache_performance = cursor.fetchall()
            conn.close()

            hit_rate = 0
            if recent_stats and recent_stats[0] > 0:
                hit_rate = (recent_stats[1] or 0) / recent_stats[0] * 100

            return {
                'timestamp': datetime.now().isoformat(),
                'hit_rate_percent': hit_rate,
                'avg_response_time_ms': (recent_stats[2] or 0) * 1000 if recent_stats else 0,
                'total_operations': recent_stats[0] if recent_stats else 0,
                'memory_cache': memory_stats,
                'file_cache': file_stats,
                'database_cache': db_stats,
                'cache_performance': [
                    {
                        'type': row[0],
                        'operations': row[1],
                        'hits': row[2],
                        'hit_rate': (row[2] / row[1] * 100) if row[1] > 0 else 0,
                        'avg_response_time_ms': row[3] * 1000
                    } for row in cache_performance
                ]
            }

        except Exception as e:
            print(f"통계 생성 오류: {e}")
            return {'error': str(e)}

    def optimize_cache_sizes(self):
        """캐시 크기 자동 최적화"""
        try:
            stats = self.get_comprehensive_stats()

            # 메모리 사용량 확인
            if PSUTIL_AVAILABLE:
                memory_percent = psutil.virtual_memory().percent

                if memory_percent > 80:
                    # 메모리 부족 시 크기 줄이기
                    self.memory_cache.max_size = max(100, int(self.memory_cache.max_size * 0.8))
                    self.file_cache.max_size_mb = max(10, int(self.file_cache.max_size_mb * 0.9))

                    print(f"⚠️ 메모리 최적화: 메모리 캐시 {self.memory_cache.max_size}, 파일 캐시 {self.file_cache.max_size_mb}MB")

                elif memory_percent < 50 and stats['hit_rate_percent'] > 80:
                    # 여유가 있고 히트율이 높으면 크기 늘리기
                    self.memory_cache.max_size = min(2000, int(self.memory_cache.max_size * 1.2))

                    print(f"📈 캐시 확장: 메모리 캐시 {self.memory_cache.max_size}")

            return True

        except Exception as e:
            print(f"캐시 최적화 오류: {e}")
            return False


def main():
    """메인 실행 함수"""
    print("🚀 차세대 캐싱 시스템")
    print("=" * 30)

    try:
        # 캐싱 시스템 초기화
        cache_system = NextGenCachingSystem()

        print("✅ 캐싱 시스템 초기화 완료")

        # 테스트 데이터
        test_data = {
            'user_1': {'name': 'Alice', 'age': 30, 'city': 'Seoul'},
            'user_2': {'name': 'Bob', 'age': 25, 'city': 'Busan'},
            'config': {'theme': 'dark', 'language': 'ko', 'auto_save': True}
        }

        print("\n📝 테스트 데이터 저장...")
        for key, value in test_data.items():
            cache_system.set(key, value)

        print("✅ 테스트 데이터 저장 완료")

        # 테스트 조회
        print("\n🔍 테스트 데이터 조회...")
        for key in test_data.keys():
            cached_value = cache_system.get(key)
            if cached_value:
                print(f"  ✅ {key}: {cached_value}")
            else:
                print(f"  ❌ {key}: 캐시 미스")

        # 통계 출력
        print("\n📊 캐시 통계:")
        stats = cache_system.get_comprehensive_stats()

        print(f"  히트율: {stats['hit_rate_percent']:.1f}%")
        print(f"  평균 응답시간: {stats['avg_response_time_ms']:.2f}ms")
        print(f"  전체 작업 수: {stats['total_operations']}")

        print(f"\n  메모리 캐시:")
        mem_stats = stats['memory_cache']
        print(f"    - 항목 수: {mem_stats['size']}/{mem_stats['max_size']}")
        print(f"    - 사용률: {mem_stats['utilization']:.1%}")

        print(f"\n  파일 캐시:")
        file_stats = stats['file_cache']
        print(f"    - 항목 수: {file_stats['entries']}")
        print(f"    - 크기: {file_stats['total_size_mb']:.1f}/{file_stats['max_size_mb']}MB")

        print(f"\n  데이터베이스 캐시:")
        db_stats = stats['database_cache']
        print(f"    - 항목 수: {db_stats['entries']}")
        print(f"    - 크기: {db_stats['total_size_mb']:.1f}MB")

        # 최적화 수행
        print(f"\n⚡ 캐시 최적화 수행...")
        if cache_system.optimize_cache_sizes():
            print("✅ 캐시 최적화 완료")

        print(f"\n🎉 차세대 캐싱 시스템 테스트 완료!")

    except KeyboardInterrupt:
        print(f"\n사용자가 중단했습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
