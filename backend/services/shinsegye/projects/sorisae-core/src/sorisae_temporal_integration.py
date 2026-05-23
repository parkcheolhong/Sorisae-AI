#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
소리새 시공간 학습 통합 시스템
Sorisae Spatiotemporal Learning Integration with Core System
"""

import os
import sys
import time
from datetime import datetime

from multi_ego_engine import MultiEgoEngine
from spatiotemporal_learning_system import SpatialScale, SpatiotemporalContext, SpatiotemporalLearningEngine, TimeScale

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


class SorisaeTemporalCore:
    """소리새 시공간 학습 통합 코어"""

    def __init__(self):
        self.spatiotemporal_engine = SpatiotemporalLearningEngine()
        self.multi_ego_engine = MultiEgoEngine()
        self.active_learning = True
        self.learning_thread = None
        self.context_buffer = []

        # 시공간 학습과 다중 자아 연동
        self._initialize_ego_temporal_integration()

        print("🌌 소리새 시공간 통합 코어 초기화 완료!")

    def _initialize_ego_temporal_integration(self):
        """자아와 시공간 학습 연동 초기화"""
        # 각 자아에 시공간 학습 능력 부여
        for ego_name, ego in self.multi_ego_engine.egos.items():
            ego.temporal_memory = []
            ego.spatial_awareness = {}
            ego.learning_preferences = {
                'temporal_focus': 0.5,
                'spatial_focus': 0.5,
                'context_sensitivity': 0.7
            }

        print("🧠 자아-시공간 학습 연동 완료")

    def process_temporal_command(self, command: str, user_location: tuple = (0, 0, 0)) -> str:
        """시공간 학습 명령 처리"""
        command = command.lower().strip()

        # 현재 맥락 생성
        current_context = SpatiotemporalContext(
            timestamp=datetime.now(),
            location=user_location,
            time_scale=TimeScale.MINUTE,
            spatial_scale=SpatialScale.ROOM,
            context_tags=self._extract_context_tags(command),
            user_state="active"
        )

        # 맥락 추가
        self.spatiotemporal_engine.add_spatiotemporal_context(current_context)

        # 명령별 처리
        if "시간 학습" in command or "temporal learning" in command:
            return self._handle_temporal_learning_command(command, current_context)

        elif "공간 학습" in command or "spatial learning" in command:
            return self._handle_spatial_learning_command(command, current_context)

        elif "패턴 분석" in command or "pattern analysis" in command:
            return self._handle_pattern_analysis_command(command, current_context)

        elif "예측" in command or "predict" in command:
            return self._handle_prediction_command(command, current_context)

        elif "학습 통계" in command or "learning stats" in command:
            return self._handle_learning_stats_command()

        elif "시공간 상태" in command or "spatiotemporal status" in command:
            return self._handle_spatiotemporal_status()

        elif "자아 시간 분석" in command:
            return self._handle_ego_temporal_analysis(command, current_context)

        else:
            # 일반적인 시공간 인식 응답
            return self._generate_contextual_response(command, current_context)

    def _extract_context_tags(self, command: str) -> list:
        """명령에서 맥락 태그 추출"""
        tag_keywords = {
            "음악": ["음악", "작곡", "노래", "멜로디"],
            "학습": ["학습", "공부", "연구", "분석"],
            "창작": ["창작", "아이디어", "디자인", "예술"],
            "소통": ["대화", "채팅", "소통", "메시지"],
            "휴식": ["휴식", "쉬기", "여가", "릴렉스"],
            "작업": ["작업", "업무", "프로젝트", "개발"]
        }

        extracted_tags = []
        for tag, keywords in tag_keywords.items():
            if any(keyword in command for keyword in keywords):
                extracted_tags.append(tag)

        return extracted_tags or ["일반"]

    def _handle_temporal_learning_command(self, command: str, context: SpatiotemporalContext) -> str:
        """시간 학습 명령 처리"""
        # 시간적 인사이트 분석
        temporal_insights = self.spatiotemporal_engine.get_temporal_insights()

        response = "⏰ **시간 학습 분석 결과**\n\n"

        # 활동 패턴 분석
        if 'activity_patterns' in temporal_insights:
            patterns = temporal_insights['activity_patterns']
            response += f"📊 **활동 패턴**:\n"
            response += f"   • 총 활동: {patterns.get('total_activities', 0)}회\n"
            response += f"   • 가장 활발한 시간: {patterns.get('most_active_hour', 0)}시\n"

        # 피크 시간대
        if 'peak_hours' in temporal_insights:
            peak_hours = temporal_insights['peak_hours']
            response += f"   • 피크 시간대: {', '.join(map(str, peak_hours))}시\n"

        # 일주기 리듬 분석
        if 'rhythm_analysis' in temporal_insights:
            rhythm = temporal_insights['rhythm_analysis']
            response += f"\n🔄 **일주기 리듬**:\n"
            response += f"   • 오전 활동: {rhythm.get('morning_activity', 0):.1%}\n"
            response += f"   • 오후 활동: {rhythm.get('afternoon_activity', 0):.1%}\n"
            response += f"   • 저녁 활동: {rhythm.get('evening_activity', 0):.1%}\n"
            response += f"   • 밤 활동: {rhythm.get('night_activity', 0):.1%}\n"

        # 다중 자아와 연동한 시간 학습
        ego_temporal_insights = self._get_ego_temporal_insights(context)
        response += f"\n🧠 **자아별 시간 학습**:\n{ego_temporal_insights}"

        return response

    def _handle_spatial_learning_command(self, command: str, context: SpatiotemporalContext) -> str:
        """공간 학습 명령 처리"""
        # 공간적 인사이트 분석
        spatial_insights = self.spatiotemporal_engine.get_spatial_insights(context.location, 1000)

        response = "🗺️ **공간 학습 분석 결과**\n\n"

        # 위치 선호도
        if 'location_preferences' in spatial_insights:
            prefs = spatial_insights['location_preferences']
            response += f"📍 **위치 선호도**:\n"
            response += f"   • 총 방문 위치: {prefs.get('total_locations', 0)}개\n"

            most_visited = prefs.get('most_visited', [])
            if most_visited:
                response += f"   • 최다 방문지: {most_visited[0][0]} ({most_visited[0][1]}회)\n"

        # 이동 효율성
        if 'movement_efficiency' in spatial_insights:
            movement = spatial_insights['movement_efficiency']
            response += f"\n🚶 **이동 패턴**:\n"
            response += f"   • 총 이동: {movement.get('total_movements', 0)}회\n"
            response += f"   • 평균 이동거리: {movement.get('average_movement_distance', 0):.1f}\n"

        # 공간 클러스터
        if 'spatial_clusters' in spatial_insights:
            clusters = spatial_insights['spatial_clusters']
            response += f"\n🏘️ **활동 영역**:\n"
            response += f"   • 주요 활동 클러스터: {len(clusters)}개\n"

            for i, cluster in enumerate(clusters[:3], 1):
                response += f"   • 클러스터 {i}: {cluster['size']}회 활동\n"

        # 자아별 공간 인식
        ego_spatial_insights = self._get_ego_spatial_insights(context)
        response += f"\n🧠 **자아별 공간 인식**:\n{ego_spatial_insights}"

        return response

    def _handle_pattern_analysis_command(self, command: str, context: SpatiotemporalContext) -> str:
        """패턴 분석 명령 처리"""
        # 학습된 패턴들 분석
        stats = self.spatiotemporal_engine.get_learning_statistics()

        response = "📊 **패턴 분석 결과**\n\n"
        response += f"🔍 **전체 패턴**: {stats['total_patterns']}개\n\n"

        # 차원별 패턴 분포
        pattern_dist = stats.get('pattern_by_dimension', {})
        response += f"📈 **차원별 패턴 분포**:\n"
        for dimension, count in pattern_dist.items():
            confidence = stats.get('average_confidence_by_dimension', {}).get(dimension, 0)
            response += f"   • {dimension}: {count}개 (신뢰도: {confidence:.1%})\n"

        # 최근 학습 패턴
        recent_patterns = self._get_recent_patterns(5)
        response += f"\n🆕 **최근 학습 패턴**:\n"
        for pattern in recent_patterns:
            response += f"   • {pattern['dimension']}: {pattern['confidence']:.1%} 신뢰도\n"

        # 다중 자아의 패턴 기여도
        ego_contributions = self._analyze_ego_learning_contributions()
        response += f"\n🧠 **자아별 학습 기여도**:\n{ego_contributions}"

        return response

    def _handle_prediction_command(self, command: str, context: SpatiotemporalContext) -> str:
        """예측 명령 처리"""
        # 다음 맥락 예측
        predictions = self.spatiotemporal_engine.predict_next_context(context)

        response = "🔮 **시공간 예측 결과**\n\n"
        response += f"🎯 **전체 예측 신뢰도**: {predictions.get('overall_confidence', 0):.1%}\n\n"

        # 시간적 예측
        if 'temporal' in predictions:
            temporal = predictions['temporal']
            response += f"⏰ **시간적 예측**:\n"

            if 'next_active_time' in temporal:
                next_time = temporal['next_active_time']
                response += f"   • 다음 활동 시간: {next_time.get('next_hour', 'unknown')}시\n"
                response += f"   • 활동 확률: {next_time.get('activity_probability', 0):.1%}\n"

            if 'likely_activities' in temporal:
                activities = temporal['likely_activities']
                response += f"   • 예상 활동: {activities.get('likely_activities', [])}\n"

        # 공간적 예측
        if 'spatial' in predictions:
            spatial = predictions['spatial']
            response += f"\n🗺️ **공간적 예측**:\n"

            if 'next_location' in spatial:
                next_loc = spatial['next_location']
                response += f"   • 다음 위치: {next_loc.get('most_likely_next', 'unknown')}\n"

        # 자아들의 예측 참여
        ego_predictions = self._get_ego_predictions(context)
        response += f"\n🧠 **자아별 예측**:\n{ego_predictions}"

        return response

    def _handle_learning_stats_command(self) -> str:
        """학습 통계 명령 처리"""
        stats = self.spatiotemporal_engine.get_learning_statistics()

        response = "📊 **시공간 학습 통계**\n\n"
        response += f"🔢 **기본 통계**:\n"
        response += f"   • 총 학습 패턴: {stats['total_patterns']}개\n"
        response += f"   • 활성 맥락: {stats['active_contexts']}개\n"
        response += f"   • 데이터베이스 크기: {stats['database_size']:,} bytes\n"
        response += f"   • 학습 가동시간: {stats.get('learning_uptime', 0):.1f}초\n\n"

        # 차원별 상세 통계
        response += f"📈 **차원별 상세**:\n"
        pattern_dist = stats.get('pattern_by_dimension', {})
        confidence_dist = stats.get('average_confidence_by_dimension', {})

        for dimension in ['temporal', 'spatial', 'contextual']:
            count = pattern_dist.get(dimension, 0)
            confidence = confidence_dist.get(dimension, 0)
            response += f"   • {dimension.title()}: {count}개 패턴, {confidence:.1%} 평균 신뢰도\n"

        # 자아별 학습 활동
        ego_stats = self._get_ego_learning_stats()
        response += f"\n🧠 **자아별 학습 활동**:\n{ego_stats}"

        return response

    def _handle_spatiotemporal_status(self) -> str:
        """시공간 상태 명령 처리"""
        current_time = datetime.now()

        response = "🌌 **시공간 학습 시스템 상태**\n\n"
        response += f"⏰ **현재 시간**: {current_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        response += f"🔄 **학습 상태**: {'활성' if self.active_learning else '비활성'}\n"
        response += f"🧠 **연동 자아**: {len(self.multi_ego_engine.egos)}개\n"
        response += f"📊 **맥락 버퍼**: {len(self.context_buffer)}개\n\n"

        # 시스템 성능 지표
        response += f"⚡ **성능 지표**:\n"
        response += f"   • 실시간 학습: 활성화\n"
        response += f"   • 예측 엔진: 가동 중\n"
        response += f"   • 패턴 매칭: 정상\n"
        response += f"   • 자아 연동: 완료\n"

        return response

    def _handle_ego_temporal_analysis(self, command: str, context: SpatiotemporalContext) -> str:
        """자아 시간 분석 명령 처리"""
        response = "🧠⏰ **자아별 시간 학습 분석**\n\n"

        for ego_name, ego in self.multi_ego_engine.egos.items():
            # 각 자아의 시간적 선호도 분석
            temporal_pref = ego.learning_preferences.get('temporal_focus', 0.5)

            response += f"{ego.emoji} **{ego_name}**:\n"
            response += f"   • 시간 집중도: {temporal_pref:.1%}\n"
            response += f"   • 메모리 항목: {len(ego.memories)}개\n"

            # 최근 활동 시간 패턴
            recent_times = [m['timestamp'] for m in ego.memories[-5:]]
            if recent_times:
                response += f"   • 최근 활동: {len(recent_times)}회\n"

            response += "\n"

        return response

    def _get_ego_temporal_insights(self, context: SpatiotemporalContext) -> str:
        """자아별 시간적 인사이트"""
        insights = []

        current_hour = context.timestamp.hour

        for ego_name, ego in self.multi_ego_engine.egos.items():
            # 해당 시간대에 활발한 자아 판단
            activity_score = 0

            if ego.ego_type.value == "creative" and 9 <= current_hour <= 11:
                activity_score = 0.8
            elif ego.ego_type.value == "logical" and 14 <= current_hour <= 17:
                activity_score = 0.9
            elif ego.ego_type.value == "emotional" and 19 <= current_hour <= 21:
                activity_score = 0.7
            else:
                activity_score = 0.5

            insights.append(f"   • {ego.emoji} {ego_name}: {activity_score:.1%} 활성도")

        return "\n".join(insights)

    def _get_ego_spatial_insights(self, context: SpatiotemporalContext) -> str:
        """자아별 공간적 인사이트"""
        insights = []

        for ego_name, ego in self.multi_ego_engine.egos.items():
            spatial_focus = ego.learning_preferences.get('spatial_focus', 0.5)
            insights.append(f"   • {ego.emoji} {ego_name}: {spatial_focus:.1%} 공간 인식도")

        return "\n".join(insights)

    def _get_recent_patterns(self, count: int) -> list:
        """최근 학습 패턴 조회"""
        patterns = list(self.spatiotemporal_engine.learning_patterns.values())
        patterns.sort(key=lambda x: x.last_updated, reverse=True)

        return [{
            'dimension': p.dimension.value,
            'confidence': p.confidence,
            'frequency': p.frequency
        } for p in patterns[:count]]

    def _analyze_ego_learning_contributions(self) -> str:
        """자아별 학습 기여도 분석"""
        contributions = []

        for ego_name, ego in self.multi_ego_engine.egos.items():
            contribution_score = len(ego.memories) * ego.learning_preferences.get('context_sensitivity', 0.5)
            contributions.append(f"   • {ego.emoji} {ego_name}: {contribution_score:.1f}점")

        return "\n".join(contributions)

    def _get_ego_predictions(self, context: SpatiotemporalContext) -> str:
        """자아별 예측 결과"""
        predictions = []

        for ego_name, ego in self.multi_ego_engine.egos.items():
            # 간단한 자아별 예측 로직
            prediction_confidence = ego.learning_preferences.get('temporal_focus', 0.5) * 0.8
            predictions.append(f"   • {ego.emoji} {ego_name}: {prediction_confidence:.1%} 예측 신뢰도")

        return "\n".join(predictions)

    def _get_ego_learning_stats(self) -> str:
        """자아별 학습 통계"""
        stats = []

        for ego_name, ego in self.multi_ego_engine.egos.items():
            memory_count = len(ego.memories)
            recent_activity = len([m for m in ego.memories if 'timestamp' in m])

            stats.append(f"   • {ego.emoji} {ego_name}: {memory_count}개 메모리, {recent_activity}회 최근 활동")

        return "\n".join(stats)

    def _generate_contextual_response(self, command: str, context: SpatiotemporalContext) -> str:
        """맥락적 응답 생성"""
        # 현재 시공간 맥락을 고려한 응답
        current_hour = context.timestamp.hour
        location_info = f"({context.location[0]:.1f}, {context.location[1]:.1f})"

        response = f"🌌 **시공간 인식 응답**\n\n"
        response += f"⏰ 현재 시간: {context.timestamp.strftime('%H:%M')}\n"
        response += f"📍 현재 위치: {location_info}\n"
        response += f"🏷️ 맥락 태그: {', '.join(context.context_tags)}\n"
        response += f"👤 사용자 상태: {context.user_state}\n\n"

        # 시간대별 맞춤 응답
        if 6 <= current_hour < 12:
            response += "☀️ 좋은 아침입니다! 오전 시간을 활용한 학습이 효과적일 것 같네요."
        elif 12 <= current_hour < 18:
            response += "☀️ 오후 시간이네요. 논리적 사고가 활발한 시간대입니다."
        elif 18 <= current_hour < 22:
            response += "🌆 저녁 시간입니다. 창의적 활동이나 휴식을 권장합니다."
        else:
            response += "🌙 늦은 시간이네요. 충분한 휴식을 취하시기 바랍니다."

        return response


# 전역 시공간 통합 코어 인스턴스
sorisae_temporal_core = SorisaeTemporalCore()


def test_temporal_integration():
    """시공간 통합 시스템 테스트"""
    print("🌌 소리새 시공간 통합 시스템 테스트")
    print("=" * 60)

    core = SorisaeTemporalCore()

    # 테스트 명령들
    test_commands = [
        ("시공간 상태", (0, 0, 0)),
        ("시간 학습 분석해줘", (10, 20, 0)),
        ("공간 학습 보고서", (50, 30, 0)),
        ("패턴 분석 실행", (25, 45, 0)),
        ("다음 행동 예측해줘", (75, 15, 0)),
        ("학습 통계 확인", (100, 50, 0)),
        ("자아 시간 분석", (40, 60, 0)),
        ("음악 작업 시작하자", (30, 40, 0))
    ]

    for i, (command, location) in enumerate(test_commands, 1):
        print(f"\n🎯 테스트 {i}: '{command}'")
        print("-" * 40)

        response = core.process_temporal_command(command, location)
        print(response)

        # 약간의 지연으로 자연스러운 테스트
        time.sleep(0.5)

    print(f"\n🎉 시공간 통합 시스템 테스트 완료!")
    return True


if __name__ == "__main__":
    test_temporal_integration()
