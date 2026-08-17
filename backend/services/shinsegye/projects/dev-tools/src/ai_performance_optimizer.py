#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 성능 최적화 도구
소리새 시스템의 AI 성능을 분석하고 최적화하는 도구입니다.
"""

import json
from datetime import datetime

import psutil


class AIPerformanceOptimizer:
    def __init__(self):
        self.performance_data = {}
        self.optimization_rules = {
            'memory_threshold': 80,
            'cpu_threshold': 85,
            'response_time_threshold': 2.0
        }

    def analyze_system_performance(self):
        """시스템 성능 분석"""
        print("🔍 AI 시스템 성능 분석 중...")

        # CPU 사용률 체크
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_info = psutil.virtual_memory()

        performance_report = {
            'timestamp': datetime.now().isoformat(),
            'cpu_usage': cpu_percent,
            'memory_usage': memory_info.percent,
            'available_memory': memory_info.available / (1024**3),  # GB
            'total_memory': memory_info.total / (1024**3)  # GB
        }

        return performance_report

    def optimize_ai_performance(self):
        """AI 성능 최적화 실행"""
        print("⚡ AI 성능 최적화 시작...")

        # 성능 데이터 수집
        perf_data = self.analyze_system_performance()

        optimization_suggestions = []

        # 메모리 최적화 체크
        if perf_data['memory_usage'] > self.optimization_rules['memory_threshold']:
            optimization_suggestions.append("메모리 사용량 최적화 필요")

        # CPU 최적화 체크
        if perf_data['cpu_usage'] > self.optimization_rules['cpu_threshold']:
            optimization_suggestions.append("CPU 사용량 최적화 필요")

        return {
            'performance_data': perf_data,
            'suggestions': optimization_suggestions,
            'optimization_score': self.calculate_optimization_score(perf_data)
        }

    def calculate_optimization_score(self, perf_data):
        """최적화 점수 계산"""
        memory_score = max(0, 100 - perf_data['memory_usage'])
        cpu_score = max(0, 100 - perf_data['cpu_usage'])

        total_score = (memory_score + cpu_score) / 2
        return round(total_score, 2)

    def generate_performance_report(self):
        """성능 보고서 생성"""
        optimization_result = self.optimize_ai_performance()

        print("📊 AI 성능 최적화 보고서")
        print("=" * 50)
        print(f"최적화 점수: {optimization_result['optimization_score']}/100")
        print(f"CPU 사용률: {optimization_result['performance_data']['cpu_usage']:.1f}%")
        print(f"메모리 사용률: {optimization_result['performance_data']['memory_usage']:.1f}%")
        print(f"사용 가능 메모리: {optimization_result['performance_data']['available_memory']:.2f}GB")

        if optimization_result['suggestions']:
            print("\n🔧 최적화 제안:")
            for suggestion in optimization_result['suggestions']:
                print(f"  • {suggestion}")
        else:
            print("\n✅ 시스템이 최적 상태입니다!")

        return optimization_result


def main():
    """메인 실행 함수"""
    print("🚀 소리새 AI 성능 최적화 도구")
    print("================================")

    optimizer = AIPerformanceOptimizer()
    result = optimizer.generate_performance_report()

    # 결과를 JSON 파일로 저장
    with open('ai_performance_report.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n💾 성능 보고서가 'ai_performance_report.json'에 저장되었습니다.")


if __name__ == "__main__":
    main()
