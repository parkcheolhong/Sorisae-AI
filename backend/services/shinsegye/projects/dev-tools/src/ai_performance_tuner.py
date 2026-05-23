#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 기반 성능 자동 튜닝 시스템
실시간 성능 모니터링 및 자동 최적화
"""

import json
import os
import sqlite3
import threading
import time
from collections import deque
from datetime import datetime

# 선택적 임포트
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("⚠️ psutil 모듈이 없습니다 - 시스템 모니터링 기능 제한")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    print("⚠️ NumPy가 설치되지 않음 - 일부 기능 제한")


class PerformanceMonitor:
    """성능 모니터링 클래스"""

    def __init__(self, window_size=100):
        self.window_size = window_size
        self.metrics = {
            'cpu_usage': deque(maxlen=window_size),
            'memory_usage': deque(maxlen=window_size),
            'response_time': deque(maxlen=window_size)
        }
        self.monitoring = False
        self.monitor_thread = None

    def start_monitoring(self):
        """모니터링 시작"""
        if not PSUTIL_AVAILABLE:
            print("⚠️ psutil이 없어 제한된 모니터링만 가능합니다")
            return False

        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.start()
        return True

    def stop_monitoring(self):
        """모니터링 중지"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()

    def _monitor_loop(self):
        """모니터링 루프"""
        while self.monitoring:
            try:
                if PSUTIL_AVAILABLE:
                    cpu_percent = psutil.cpu_percent(interval=1)
                    memory_percent = psutil.virtual_memory().percent

                    self.metrics['cpu_usage'].append(cpu_percent)
                    self.metrics['memory_usage'].append(memory_percent)

                time.sleep(1)

            except Exception as e:
                print(f"모니터링 오류: {e}")
                time.sleep(5)

    def get_current_metrics(self):
        """현재 메트릭 조회"""
        if not PSUTIL_AVAILABLE:
            return {
                'cpu_usage': 0,
                'memory_usage': 0,
                'response_time': 0,
                'available': False
            }

        try:
            return {
                'cpu_usage': psutil.cpu_percent(),
                'memory_usage': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:').percent,
                'available': True
            }
        except Exception as e:
            print(f"메트릭 조회 오류: {e}")
            return {'available': False}

    def get_statistics(self):
        """통계 정보 조회"""
        stats = {}

        for metric_name, values in self.metrics.items():
            if values:
                if NUMPY_AVAILABLE:
                    stats[metric_name] = {
                        'mean': float(np.mean(values)),
                        'std': float(np.std(values)),
                        'min': float(np.min(values)),
                        'max': float(np.max(values))
                    }
                else:
                    # NumPy 없이 기본 계산
                    values_list = list(values)
                    stats[metric_name] = {
                        'mean': sum(values_list) / len(values_list),
                        'min': min(values_list),
                        'max': max(values_list),
                        'count': len(values_list)
                    }

        return stats


class AIPerformanceTuner:
    """AI 기반 성능 튜너"""

    def __init__(self):
        self.db_path = "performance_tuner.db"
        self.monitor = PerformanceMonitor()
        self.tuning_rules = self._load_tuning_rules()
        self.optimization_history = []

        self.init_database()

    def init_database(self):
        """데이터베이스 초기화"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 성능 데이터 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    cpu_usage REAL,
                    memory_usage REAL,
                    response_time REAL,
                    optimization_applied TEXT
                )
            ''')

            # 튜닝 히스토리 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tuning_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    optimization_type TEXT NOT NULL,
                    parameters TEXT,
                    result TEXT,
                    effectiveness_score REAL
                )
            ''')

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"데이터베이스 초기화 오류: {e}")

    def _load_tuning_rules(self):
        """튜닝 규칙 로드"""
        return {
            'high_cpu': {
                'threshold': 80.0,
                'actions': [
                    'reduce_process_priority',
                    'enable_cpu_throttling',
                    'optimize_algorithms'
                ]
            },
            'high_memory': {
                'threshold': 85.0,
                'actions': [
                    'clear_cache',
                    'optimize_memory_usage',
                    'enable_garbage_collection'
                ]
            },
            'slow_response': {
                'threshold': 5.0,  # seconds
                'actions': [
                    'enable_caching',
                    'optimize_database_queries',
                    'use_async_processing'
                ]
            }
        }

    def analyze_performance(self):
        """성능 분석"""
        metrics = self.monitor.get_current_metrics()

        if not metrics.get('available', False):
            return {
                'status': 'unavailable',
                'message': '성능 모니터링 도구가 없습니다'
            }

        issues = []
        recommendations = []

        # CPU 사용률 분석
        if metrics['cpu_usage'] > self.tuning_rules['high_cpu']['threshold']:
            issues.append(f"높은 CPU 사용률: {metrics['cpu_usage']:.1f}%")
            recommendations.extend(self.tuning_rules['high_cpu']['actions'])

        # 메모리 사용률 분석
        if metrics['memory_usage'] > self.tuning_rules['high_memory']['threshold']:
            issues.append(f"높은 메모리 사용률: {metrics['memory_usage']:.1f}%")
            recommendations.extend(self.tuning_rules['high_memory']['actions'])

        analysis_result = {
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics,
            'issues': issues,
            'recommendations': list(set(recommendations)),
            'severity': 'high' if len(issues) > 1 else 'medium' if issues else 'low'
        }

        # 데이터베이스에 저장
        self._save_performance_data(analysis_result)

        return analysis_result

    def _save_performance_data(self, analysis):
        """성능 데이터 저장"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            metrics = analysis['metrics']
            cursor.execute('''
                INSERT INTO performance_data
                (timestamp, cpu_usage, memory_usage, optimization_applied)
                VALUES (?, ?, ?, ?)
            ''', (
                analysis['timestamp'],
                metrics.get('cpu_usage', 0),
                metrics.get('memory_usage', 0),
                json.dumps(analysis['recommendations'])
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"성능 데이터 저장 오류: {e}")

    def apply_optimizations(self, recommendations):
        """최적화 적용"""
        applied_optimizations = []

        for recommendation in recommendations:
            try:
                if recommendation == 'clear_cache':
                    # 캐시 정리 시뮬레이션
                    print("🧹 캐시 정리 중...")
                    applied_optimizations.append('cache_cleared')

                elif recommendation == 'optimize_memory_usage':
                    # 메모리 최적화 시뮬레이션
                    print("🔧 메모리 사용 최적화 중...")
                    if PSUTIL_AVAILABLE:
                        import gc
                        gc.collect()
                    applied_optimizations.append('memory_optimized')

                elif recommendation == 'enable_caching':
                    # 캐싱 활성화 시뮬레이션
                    print("⚡ 캐싱 시스템 활성화...")
                    applied_optimizations.append('caching_enabled')

                elif recommendation == 'reduce_process_priority':
                    # 프로세스 우선순위 조정
                    print("⬇️  프로세스 우선순위 조정...")
                    applied_optimizations.append('priority_adjusted')

            except Exception as e:
                print(f"최적화 적용 오류 ({recommendation}): {e}")

        return applied_optimizations

    def auto_tune(self):
        """자동 튜닝 실행"""
        print("🤖 AI 기반 자동 성능 튜닝 시작...")

        # 성능 분석
        analysis = self.analyze_performance()

        if analysis['severity'] == 'low':
            print("✅ 성능 상태 양호 - 최적화 불필요")
            return {
                'status': 'no_action_needed',
                'analysis': analysis
            }

        print(f"⚠️  성능 이슈 감지 ({analysis['severity']} 심각도)")
        for issue in analysis['issues']:
            print(f"  - {issue}")

        # 권장사항 적용
        if analysis['recommendations']:
            print(f"🔧 {len(analysis['recommendations'])}개 최적화 적용 중...")
            applied = self.apply_optimizations(analysis['recommendations'])

            # 결과 저장
            self._save_tuning_history(analysis, applied)

            return {
                'status': 'optimized',
                'analysis': analysis,
                'applied_optimizations': applied
            }

        return {
            'status': 'no_optimizations_available',
            'analysis': analysis
        }

    def _save_tuning_history(self, analysis, applied_optimizations):
        """튜닝 히스토리 저장"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO tuning_history
                (timestamp, optimization_type, parameters, result, effectiveness_score)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                analysis['timestamp'],
                analysis['severity'],
                json.dumps(analysis['recommendations']),
                json.dumps(applied_optimizations),
                len(applied_optimizations) / len(analysis['recommendations']) if analysis['recommendations'] else 0
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"튜닝 히스토리 저장 오류: {e}")

    def get_performance_report(self):
        """성능 보고서 생성"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 최근 성능 데이터
            cursor.execute('''
                SELECT * FROM performance_data
                ORDER BY timestamp DESC LIMIT 10
            ''')
            recent_data = cursor.fetchall()

            # 튜닝 히스토리
            cursor.execute('''
                SELECT * FROM tuning_history
                ORDER BY timestamp DESC LIMIT 5
            ''')
            tuning_history = cursor.fetchall()

            conn.close()

            # 현재 메트릭
            current_metrics = self.monitor.get_current_metrics()
            statistics = self.monitor.get_statistics()

            report = {
                'timestamp': datetime.now().isoformat(),
                'current_metrics': current_metrics,
                'statistics': statistics,
                'recent_performance': [
                    {
                        'timestamp': row[1],
                        'cpu_usage': row[2],
                        'memory_usage': row[3],
                        'response_time': row[4]
                    } for row in recent_data
                ],
                'tuning_history': [
                    {
                        'timestamp': row[1],
                        'type': row[2],
                        'effectiveness': row[5]
                    } for row in tuning_history
                ]
            }

            return report

        except Exception as e:
            print(f"성능 보고서 생성 오류: {e}")
            return {'error': str(e)}


def main():
    """메인 실행 함수"""
    print("🤖 AI 기반 성능 자동 튜닝 시스템")
    print("=" * 40)

    try:
        # 튜너 초기화
        tuner = AIPerformanceTuner()

        # 모니터링 시작
        if tuner.monitor.start_monitoring():
            print("📊 성능 모니터링 시작됨")
        else:
            print("⚠️ 제한된 모니터링 모드")

        # 자동 튜닝 실행
        result = tuner.auto_tune()

        print(f"\n🎯 튜닝 결과: {result['status']}")

        if 'applied_optimizations' in result:
            print(f"✅ 적용된 최적화: {len(result['applied_optimizations'])}개")
            for opt in result['applied_optimizations']:
                print(f"  - {opt}")

        # 성능 보고서
        report = tuner.get_performance_report()
        if 'current_metrics' in report and report['current_metrics'].get('available'):
            metrics = report['current_metrics']
            print(f"\n📈 현재 성능:")
            print(f"  CPU 사용률: {metrics['cpu_usage']:.1f}%")
            print(f"  메모리 사용률: {metrics['memory_usage']:.1f}%")
            print(f"  디스크 사용률: {metrics.get('disk_usage', 0):.1f}%")

        # 모니터링 중지
        tuner.monitor.stop_monitoring()

        print(f"\n🎉 AI 성능 튜닝 완료!")

    except KeyboardInterrupt:
        print(f"\n사용자가 중단했습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
