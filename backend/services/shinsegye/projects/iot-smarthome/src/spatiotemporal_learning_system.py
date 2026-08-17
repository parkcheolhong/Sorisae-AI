#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
소리새 시공간 학습 확장 시스템 (Sorisae Spatiotemporal Learning Expansion)
시간과 공간을 인식하는 혁신적인 4차원 학습 엔진
"""

import json
import math
import os
import random
import sqlite3
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class TimeScale(Enum):
    """시간 스케일"""
    MICROSECOND = "microsecond"
    MILLISECOND = "millisecond"
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    SEASON = "season"
    YEAR = "year"
    DECADE = "decade"


class SpatialScale(Enum):
    """공간 스케일"""
    PERSONAL = "personal"        # 개인 공간 (1m 이내)
    ROOM = "room"               # 방 단위 (10m 이내)
    BUILDING = "building"       # 건물 단위 (100m 이내)
    DISTRICT = "district"       # 지역 단위 (1km 이내)
    CITY = "city"              # 도시 단위 (10km 이내)
    REGION = "region"          # 지역 단위 (100km 이내)
    COUNTRY = "country"        # 국가 단위 (1000km 이내)
    CONTINENT = "continent"    # 대륙 단위 (10000km 이내)
    GLOBAL = "global"          # 전 세계


class LearningDimension(Enum):
    """학습 차원"""
    TEMPORAL = "temporal"      # 시간적 학습
    SPATIAL = "spatial"        # 공간적 학습
    CONTEXTUAL = "contextual"  # 맥락적 학습
    BEHAVIORAL = "behavioral"  # 행동적 학습
    EMOTIONAL = "emotional"    # 감정적 학습
    COGNITIVE = "cognitive"    # 인지적 학습


@dataclass
class SpatiotemporalContext:
    """시공간 맥락 정보"""
    timestamp: datetime
    location: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # x, y, z 좌표
    time_scale: TimeScale = TimeScale.SECOND
    spatial_scale: SpatialScale = SpatialScale.PERSONAL
    context_tags: List[str] = field(default_factory=list)
    user_state: str = "active"
    environment_factors: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LearningPattern:
    """학습 패턴"""
    pattern_id: str
    dimension: LearningDimension
    pattern_data: Dict[str, Any]
    confidence: float
    frequency: int
    last_updated: datetime
    spatial_bounds: Tuple[Tuple[float, float, float], Tuple[float, float, float]] = None
    temporal_bounds: Tuple[datetime, datetime] = None


class SpatiotemporalLearningEngine:
    """소리새 시공간 학습 엔진"""

    def __init__(self, db_path: str = "sorisae_spatiotemporal.db"):
        self.db_path = db_path
        self.learning_patterns = {}
        self.temporal_memory = defaultdict(deque)
        self.spatial_memory = defaultdict(dict)
        self.context_history = deque(maxlen=10000)
        self.learning_models = {}

        # 시공간 인덱스
        self.time_index = defaultdict(list)
        self.space_index = defaultdict(list)

        # 학습 통계
        self.learning_stats = {
            'total_patterns': 0,
            'active_contexts': 0,
            'learning_rate': 0.0,
            'prediction_accuracy': 0.0
        }

        self._initialize_database()
        self._initialize_learning_models()

        print("🌌 소리새 시공간 학습 엔진 초기화 완료!")
        print(f"📊 데이터베이스: {db_path}")

    def _initialize_database(self):
        """데이터베이스 초기화"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 시공간 맥락 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS spatiotemporal_contexts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                location_x REAL,
                location_y REAL,
                location_z REAL,
                time_scale TEXT,
                spatial_scale TEXT,
                context_tags TEXT,
                user_state TEXT,
                environment_factors TEXT
            )
        ''')

        # 학습 패턴 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_patterns (
                pattern_id TEXT PRIMARY KEY,
                dimension TEXT NOT NULL,
                pattern_data TEXT NOT NULL,
                confidence REAL,
                frequency INTEGER,
                last_updated TEXT,
                spatial_bounds TEXT,
                temporal_bounds TEXT
            )
        ''')

        # 예측 결과 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                prediction_type TEXT,
                predicted_value TEXT,
                actual_value TEXT,
                accuracy REAL,
                context_id INTEGER,
                FOREIGN KEY (context_id) REFERENCES spatiotemporal_contexts (id)
            )
        ''')

        conn.commit()
        conn.close()

    def _initialize_learning_models(self):
        """학습 모델 초기화"""
        # 시간 패턴 학습 모델
        self.learning_models[LearningDimension.TEMPORAL] = {
            'circadian_rhythm': CircadianLearningModel(),
            'seasonal_pattern': SeasonalLearningModel(),
            'habit_tracker': HabitLearningModel()
        }

        # 공간 패턴 학습 모델
        self.learning_models[LearningDimension.SPATIAL] = {
            'location_preference': LocationPreferenceModel(),
            'movement_pattern': MovementPatternModel(),
            'spatial_association': SpatialAssociationModel()
        }

        # 맥락 학습 모델
        self.learning_models[LearningDimension.CONTEXTUAL] = {
            'context_predictor': ContextPredictionModel(),
            'pattern_matcher': PatternMatchingModel()
        }

        print("🧠 학습 모델 초기화 완료")
        print(f"   시간 모델: {len(self.learning_models[LearningDimension.TEMPORAL])}개")
        print(f"   공간 모델: {len(self.learning_models[LearningDimension.SPATIAL])}개")
        print(f"   맥락 모델: {len(self.learning_models[LearningDimension.CONTEXTUAL])}개")

    def add_spatiotemporal_context(self, context: SpatiotemporalContext) -> str:
        """시공간 맥락 추가"""
        context_id = f"ctx_{int(time.time() * 1000000)}"

        # 메모리에 저장
        self.context_history.append((context_id, context))

        # 시간 인덱스 업데이트
        time_key = self._get_time_key(context.timestamp, context.time_scale)
        self.time_index[time_key].append(context_id)

        # 공간 인덱스 업데이트
        space_key = self._get_space_key(context.location, context.spatial_scale)
        self.space_index[space_key].append(context_id)

        # 데이터베이스에 저장
        self._save_context_to_db(context_id, context)

        # 실시간 학습 수행
        self._perform_realtime_learning(context_id, context)

        self.learning_stats['active_contexts'] += 1

        return context_id

    def _get_time_key(self, timestamp: datetime, scale: TimeScale) -> str:
        """시간 키 생성"""
        if scale == TimeScale.HOUR:
            return f"hour_{timestamp.strftime('%Y%m%d_%H')}"
        elif scale == TimeScale.DAY:
            return f"day_{timestamp.strftime('%Y%m%d')}"
        elif scale == TimeScale.WEEK:
            year, week, _ = timestamp.isocalendar()
            return f"week_{year}_{week:02d}"
        elif scale == TimeScale.MONTH:
            return f"month_{timestamp.strftime('%Y%m')}"
        elif scale == TimeScale.SEASON:
            season = self._get_season(timestamp)
            return f"season_{timestamp.year}_{season}"
        else:
            return f"second_{timestamp.strftime('%Y%m%d_%H%M%S')}"

    def _get_space_key(self, location: Tuple[float, float, float], scale: SpatialScale) -> str:
        """공간 키 생성"""
        x, y, z = location

        if scale == SpatialScale.PERSONAL:
            return f"personal_{int(x)}_{int(y)}_{int(z)}"
        elif scale == SpatialScale.ROOM:
            return f"room_{int(x / 10)}_{int(y / 10)}_{int(z / 10)}"
        elif scale == SpatialScale.BUILDING:
            return f"building_{int(x / 100)}_{int(y / 100)}_{int(z / 100)}"
        elif scale == SpatialScale.CITY:
            return f"city_{int(x / 10000)}_{int(y / 10000)}"
        else:
            return f"global_{int(x / 100000)}_{int(y / 100000)}"

    def _get_season(self, timestamp: datetime) -> str:
        """계절 계산"""
        month = timestamp.month
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "autumn"

    def _save_context_to_db(self, context_id: str, context: SpatiotemporalContext):
        """맥락을 데이터베이스에 저장"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO spatiotemporal_contexts
            (timestamp, location_x, location_y, location_z, time_scale, spatial_scale,
             context_tags, user_state, environment_factors)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            context.timestamp.isoformat(),
            context.location[0], context.location[1], context.location[2],
            context.time_scale.value, context.spatial_scale.value,
            json.dumps(context.context_tags, ensure_ascii=False),
            context.user_state,
            json.dumps(context.environment_factors, ensure_ascii=False)
        ))

        conn.commit()
        conn.close()

    def _perform_realtime_learning(self, context_id: str, context: SpatiotemporalContext):
        """실시간 학습 수행"""
        # 시간적 패턴 학습
        for model_name, model in self.learning_models[LearningDimension.TEMPORAL].items():
            pattern = model.learn_from_context(context)
            if pattern:
                self._update_learning_pattern(pattern)

        # 공간적 패턴 학습
        for model_name, model in self.learning_models[LearningDimension.SPATIAL].items():
            pattern = model.learn_from_context(context)
            if pattern:
                self._update_learning_pattern(pattern)

        # 맥락적 패턴 학습
        for model_name, model in self.learning_models[LearningDimension.CONTEXTUAL].items():
            pattern = model.learn_from_context(context)
            if pattern:
                self._update_learning_pattern(pattern)

    def _update_learning_pattern(self, pattern: LearningPattern):
        """학습 패턴 업데이트"""
        if pattern.pattern_id in self.learning_patterns:
            existing = self.learning_patterns[pattern.pattern_id]
            existing.frequency += 1
            existing.confidence = (existing.confidence + pattern.confidence) / 2
            existing.last_updated = datetime.now()
        else:
            self.learning_patterns[pattern.pattern_id] = pattern
            self.learning_stats['total_patterns'] += 1

        # 데이터베이스에 저장
        self._save_pattern_to_db(pattern)

    def _save_pattern_to_db(self, pattern: LearningPattern):
        """패턴을 데이터베이스에 저장"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO learning_patterns
            (pattern_id, dimension, pattern_data, confidence, frequency, last_updated,
             spatial_bounds, temporal_bounds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            pattern.pattern_id,
            pattern.dimension.value,
            json.dumps(pattern.pattern_data, ensure_ascii=False),
            pattern.confidence,
            pattern.frequency,
            pattern.last_updated.isoformat(),
            json.dumps(pattern.spatial_bounds) if pattern.spatial_bounds else None,
            json.dumps([b.isoformat() for b in pattern.temporal_bounds]) if pattern.temporal_bounds else None
        ))

        conn.commit()
        conn.close()

    def predict_next_context(self, current_context: SpatiotemporalContext) -> Dict[str, Any]:
        """다음 맥락 예측"""
        predictions = {}

        # 시간적 예측
        temporal_predictions = self._predict_temporal_patterns(current_context)
        predictions['temporal'] = temporal_predictions

        # 공간적 예측
        spatial_predictions = self._predict_spatial_patterns(current_context)
        predictions['spatial'] = spatial_predictions

        # 맥락적 예측
        contextual_predictions = self._predict_contextual_patterns(current_context)
        predictions['contextual'] = contextual_predictions

        # 종합 예측 신뢰도 계산
        overall_confidence = self._calculate_prediction_confidence(predictions)
        predictions['overall_confidence'] = overall_confidence

        return predictions

    def _predict_temporal_patterns(self, context: SpatiotemporalContext) -> Dict[str, Any]:
        """시간적 패턴 예측"""
        predictions = {}

        # 일주기 리듬 예측
        circadian_model = self.learning_models[LearningDimension.TEMPORAL]['circadian_rhythm']
        predictions['next_active_time'] = circadian_model.predict_next_activity(context)

        # 습관 패턴 예측
        habit_model = self.learning_models[LearningDimension.TEMPORAL]['habit_tracker']
        predictions['likely_activities'] = habit_model.predict_activities(context)

        # 계절적 패턴 예측
        seasonal_model = self.learning_models[LearningDimension.TEMPORAL]['seasonal_pattern']
        predictions['seasonal_preferences'] = seasonal_model.predict_preferences(context)

        return predictions

    def _predict_spatial_patterns(self, context: SpatiotemporalContext) -> Dict[str, Any]:
        """공간적 패턴 예측"""
        predictions = {}

        # 위치 선호도 예측
        location_model = self.learning_models[LearningDimension.SPATIAL]['location_preference']
        predictions['preferred_locations'] = location_model.predict_locations(context)

        # 이동 패턴 예측
        movement_model = self.learning_models[LearningDimension.SPATIAL]['movement_pattern']
        predictions['next_location'] = movement_model.predict_movement(context)

        return predictions

    def _predict_contextual_patterns(self, context: SpatiotemporalContext) -> Dict[str, Any]:
        """맥락적 패턴 예측"""
        predictions = {}

        # 맥락 예측
        context_model = self.learning_models[LearningDimension.CONTEXTUAL]['context_predictor']
        predictions['likely_contexts'] = context_model.predict_context(context)

        return predictions

    def _calculate_prediction_confidence(self, predictions: Dict[str, Any]) -> float:
        """예측 신뢰도 계산"""
        confidences = []

        for category, preds in predictions.items():
            if category != 'overall_confidence' and isinstance(preds, dict):
                for pred_key, pred_value in preds.items():
                    if isinstance(pred_value, dict) and 'confidence' in pred_value:
                        confidences.append(pred_value['confidence'])

        return sum(confidences) / len(confidences) if confidences else 0.0

    def get_temporal_insights(self, time_range: Tuple[datetime, datetime] = None) -> Dict[str, Any]:
        """시간적 인사이트 분석"""
        if not time_range:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=30)
            time_range = (start_time, end_time)

        insights = {
            'activity_patterns': self._analyze_activity_patterns(time_range),
            'peak_hours': self._find_peak_activity_hours(time_range),
            'rhythm_analysis': self._analyze_circadian_rhythm(time_range),
            'habit_strength': self._calculate_habit_strength(time_range)
        }

        return insights

    def _analyze_activity_patterns(self, time_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """활동 패턴 분석"""
        patterns = {}
        hour_activity = defaultdict(int)

        for context_id, context in self.context_history:
            if time_range[0] <= context.timestamp <= time_range[1]:
                hour_activity[context.timestamp.hour] += 1

        patterns['hourly_distribution'] = dict(hour_activity)
        patterns['most_active_hour'] = max(hour_activity.items(), key=lambda x: x[1])[0] if hour_activity else 0
        patterns['total_activities'] = sum(hour_activity.values())

        return patterns

    def _find_peak_activity_hours(self, time_range: Tuple[datetime, datetime]) -> List[int]:
        """피크 활동 시간대 찾기"""
        hour_activity = defaultdict(int)

        for context_id, context in self.context_history:
            if time_range[0] <= context.timestamp <= time_range[1]:
                if context.user_state == "active":
                    hour_activity[context.timestamp.hour] += 1

        if not hour_activity:
            return []

        max_activity = max(hour_activity.values())
        peak_hours = [hour for hour, activity in hour_activity.items()
                      if activity >= max_activity * 0.8]

        return sorted(peak_hours)

    def _analyze_circadian_rhythm(self, time_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """일주기 리듬 분석"""
        rhythm_data = {
            'morning_activity': 0,
            'afternoon_activity': 0,
            'evening_activity': 0,
            'night_activity': 0
        }

        for context_id, context in self.context_history:
            if time_range[0] <= context.timestamp <= time_range[1]:
                hour = context.timestamp.hour
                if 6 <= hour < 12:
                    rhythm_data['morning_activity'] += 1
                elif 12 <= hour < 18:
                    rhythm_data['afternoon_activity'] += 1
                elif 18 <= hour < 24:
                    rhythm_data['evening_activity'] += 1
                else:
                    rhythm_data['night_activity'] += 1

        total = sum(rhythm_data.values())
        if total > 0:
            for key in rhythm_data:
                rhythm_data[key] = rhythm_data[key] / total

        return rhythm_data

    def _calculate_habit_strength(self, time_range: Tuple[datetime, datetime]) -> Dict[str, float]:
        """습관 강도 계산"""
        habit_patterns = defaultdict(lambda: defaultdict(int))

        for context_id, context in self.context_history:
            if time_range[0] <= context.timestamp <= time_range[1]:
                time_slot = f"{context.timestamp.hour:02d}:00"
                for tag in context.context_tags:
                    habit_patterns[time_slot][tag] += 1

        habit_strength = {}
        for time_slot, activities in habit_patterns.items():
            if activities:
                max_activity = max(activities.values())
                total_activity = sum(activities.values())
                strength = max_activity / total_activity if total_activity > 0 else 0
                habit_strength[time_slot] = strength

        return habit_strength

    def get_spatial_insights(self, location_center: Tuple[float,
                             float, float] = None, radius: float = 1000) -> Dict[str, Any]:
        """공간적 인사이트 분석"""
        insights = {
            'location_preferences': self._analyze_location_preferences(location_center, radius),
            'movement_efficiency': self._calculate_movement_efficiency(location_center, radius),
            'spatial_clusters': self._find_spatial_clusters(location_center, radius),
            'territory_analysis': self._analyze_territory_usage(location_center, radius)
        }

        return insights

    def _analyze_location_preferences(self, center: Tuple[float, float, float], radius: float) -> Dict[str, Any]:
        """위치 선호도 분석"""
        location_visits = defaultdict(int)

        for context_id, context in self.context_history:
            if center is None or self._calculate_distance(context.location, center) <= radius:
                location_key = f"{int(context.location[0] / 10)}_{int(context.location[1] / 10)}"
                location_visits[location_key] += 1

        preferences = {
            'most_visited': sorted(location_visits.items(), key=lambda x: x[1], reverse=True)[:5],
            'total_locations': len(location_visits),
            'visit_distribution': dict(location_visits)
        }

        return preferences

    def _calculate_movement_efficiency(self, center: Tuple[float, float, float], radius: float) -> Dict[str, Any]:
        """이동 효율성 계산"""
        movements = []
        prev_location = None

        for context_id, context in self.context_history:
            if center is None or self._calculate_distance(context.location, center) <= radius:
                if prev_location:
                    distance = self._calculate_distance(prev_location, context.location)
                    movements.append(distance)
                prev_location = context.location

        if movements:
            avg_distance = sum(movements) / len(movements)
            max_distance = max(movements)
            min_distance = min(movements)
        else:
            avg_distance = max_distance = min_distance = 0

        return {
            'average_movement_distance': avg_distance,
            'max_movement_distance': max_distance,
            'min_movement_distance': min_distance,
            'total_movements': len(movements)
        }

    def _find_spatial_clusters(self, center: Tuple[float, float, float], radius: float) -> List[Dict[str, Any]]:
        """공간 클러스터 찾기"""
        locations = []

        for context_id, context in self.context_history:
            if center is None or self._calculate_distance(context.location, center) <= radius:
                locations.append(context.location)

        # 간단한 클러스터링 (거리 기반)
        clusters = []
        cluster_radius = 50  # 50 단위 내 위치들을 하나의 클러스터로 그룹화

        for location in locations:
            found_cluster = False
            for cluster in clusters:
                if self._calculate_distance(location, cluster['center']) <= cluster_radius:
                    cluster['locations'].append(location)
                    cluster['size'] += 1
                    found_cluster = True
                    break

            if not found_cluster:
                clusters.append({
                    'center': location,
                    'locations': [location],
                    'size': 1
                })

        return sorted(clusters, key=lambda x: x['size'], reverse=True)[:10]

    def _analyze_territory_usage(self, center: Tuple[float, float, float], radius: float) -> Dict[str, Any]:
        """영역 사용 분석"""
        territory_usage = {
            'core_area': 0,      # 중심부 (반경의 25% 이내)
            'frequent_area': 0,  # 빈번한 지역 (반경의 50% 이내)
            'occasional_area': 0,  # 가끔 방문 (반경의 75% 이내)
            'rare_area': 0       # 드문 방문 (반경의 100% 이내)
        }

        if center is None:
            center = (0, 0, 0)

        for context_id, context in self.context_history:
            distance = self._calculate_distance(context.location, center)

            if distance <= radius * 0.25:
                territory_usage['core_area'] += 1
            elif distance <= radius * 0.5:
                territory_usage['frequent_area'] += 1
            elif distance <= radius * 0.75:
                territory_usage['occasional_area'] += 1
            elif distance <= radius:
                territory_usage['rare_area'] += 1

        return territory_usage

    def _calculate_distance(self, loc1: Tuple[float, float, float], loc2: Tuple[float, float, float]) -> float:
        """두 위치 간 거리 계산"""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(loc1, loc2)))

    def get_learning_statistics(self) -> Dict[str, Any]:
        """학습 통계 조회"""
        # 패턴별 통계
        pattern_stats = defaultdict(int)
        confidence_stats = defaultdict(list)

        for pattern in self.learning_patterns.values():
            pattern_stats[pattern.dimension.value] += 1
            confidence_stats[pattern.dimension.value].append(pattern.confidence)

        # 평균 신뢰도 계산
        avg_confidence = {}
        for dimension, confidences in confidence_stats.items():
            avg_confidence[dimension] = sum(confidences) / len(confidences) if confidences else 0.0

        return {
            'total_patterns': len(self.learning_patterns),
            'pattern_by_dimension': dict(pattern_stats),
            'average_confidence_by_dimension': avg_confidence,
            'active_contexts': len(self.context_history),
            'database_size': os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0,
            'learning_uptime': time.time() - self._start_time if hasattr(self, '_start_time') else 0
        }

    def optimize_learning_models(self) -> Dict[str, Any]:
        """학습 모델 최적화"""
        optimization_results = {}

        for dimension, models in self.learning_models.items():
            dimension_results = {}

            for model_name, model in models.items():
                if hasattr(model, 'optimize'):
                    result = model.optimize(self.learning_patterns)
                    dimension_results[model_name] = result
                else:
                    dimension_results[model_name] = "optimization_not_available"

            optimization_results[dimension.value] = dimension_results

        return optimization_results

# 학습 모델 클래스들


class CircadianLearningModel:
    """일주기 리듬 학습 모델"""

    def __init__(self):
        self.activity_hours = defaultdict(int)
        self.sleep_patterns = {}

    def learn_from_context(self, context: SpatiotemporalContext) -> Optional[LearningPattern]:
        hour = context.timestamp.hour
        self.activity_hours[hour] += 1

        if context.user_state == "active":
            pattern_id = f"circadian_active_{hour}"
            return LearningPattern(
                pattern_id=pattern_id,
                dimension=LearningDimension.TEMPORAL,
                pattern_data={"hour": hour, "activity": "active"},
                confidence=0.8,
                frequency=1,
                last_updated=datetime.now()
            )
        return None

    def predict_next_activity(self, context: SpatiotemporalContext) -> Dict[str, Any]:
        current_hour = context.timestamp.hour
        next_hour = (current_hour + 1) % 24

        activity_score = self.activity_hours.get(next_hour, 0)
        total_activities = sum(self.activity_hours.values())

        return {
            "next_hour": next_hour,
            "activity_probability": activity_score / total_activities if total_activities > 0 else 0,
            "confidence": min(activity_score / 10, 1.0)  # 최대 1.0
        }


class SeasonalLearningModel:
    """계절적 패턴 학습 모델"""

    def __init__(self):
        self.seasonal_preferences = defaultdict(dict)

    def learn_from_context(self, context: SpatiotemporalContext) -> Optional[LearningPattern]:
        season = self._get_season(context.timestamp)

        for tag in context.context_tags:
            if tag not in self.seasonal_preferences[season]:
                self.seasonal_preferences[season][tag] = 0
            self.seasonal_preferences[season][tag] += 1

        if context.context_tags:
            pattern_id = f"seasonal_{season}_{hash(str(sorted(context.context_tags)))}"
            return LearningPattern(
                pattern_id=pattern_id,
                dimension=LearningDimension.TEMPORAL,
                pattern_data={"season": season, "preferences": context.context_tags},
                confidence=0.7,
                frequency=1,
                last_updated=datetime.now()
            )
        return None

    def _get_season(self, timestamp: datetime) -> str:
        month = timestamp.month
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "autumn"

    def predict_preferences(self, context: SpatiotemporalContext) -> Dict[str, Any]:
        season = self._get_season(context.timestamp)
        preferences = self.seasonal_preferences.get(season, {})

        return {
            "season": season,
            "top_preferences": sorted(preferences.items(), key=lambda x: x[1], reverse=True)[:5],
            "confidence": 0.6
        }


class HabitLearningModel:
    """습관 학습 모델"""

    def __init__(self):
        self.habits = defaultdict(lambda: defaultdict(int))

    def learn_from_context(self, context: SpatiotemporalContext) -> Optional[LearningPattern]:
        time_key = f"{context.timestamp.hour:02d}:{(context.timestamp.minute // 15) * 15:02d}"

        for tag in context.context_tags:
            self.habits[time_key][tag] += 1

        if context.context_tags:
            pattern_id = f"habit_{time_key}_{hash(str(sorted(context.context_tags)))}"
            return LearningPattern(
                pattern_id=pattern_id,
                dimension=LearningDimension.TEMPORAL,
                pattern_data={"time": time_key, "activities": context.context_tags},
                confidence=0.75,
                frequency=1,
                last_updated=datetime.now()
            )
        return None

    def predict_activities(self, context: SpatiotemporalContext) -> Dict[str, Any]:
        time_key = f"{context.timestamp.hour:02d}:{(context.timestamp.minute // 15) * 15:02d}"
        activities = self.habits.get(time_key, {})

        return {
            "time_slot": time_key,
            "likely_activities": sorted(activities.items(), key=lambda x: x[1], reverse=True)[:3],
            "confidence": 0.7
        }


class LocationPreferenceModel:
    """위치 선호도 모델"""

    def __init__(self):
        self.location_visits = defaultdict(int)
        self.location_durations = defaultdict(list)

    def learn_from_context(self, context: SpatiotemporalContext) -> Optional[LearningPattern]:
        location_key = f"{int(context.location[0] / 10)}_{int(context.location[1] / 10)}"
        self.location_visits[location_key] += 1

        pattern_id = f"location_pref_{location_key}"
        return LearningPattern(
            pattern_id=pattern_id,
            dimension=LearningDimension.SPATIAL,
            pattern_data={"location": location_key, "visit_count": self.location_visits[location_key]},
            confidence=0.8,
            frequency=1,
            last_updated=datetime.now()
        )

    def predict_locations(self, context: SpatiotemporalContext) -> Dict[str, Any]:
        sorted_locations = sorted(self.location_visits.items(), key=lambda x: x[1], reverse=True)

        return {
            "preferred_locations": sorted_locations[:5],
            "confidence": 0.75
        }


class MovementPatternModel:
    """이동 패턴 모델"""

    def __init__(self):
        self.movement_history = deque(maxlen=1000)
        self.transition_matrix = defaultdict(lambda: defaultdict(int))

    def learn_from_context(self, context: SpatiotemporalContext) -> Optional[LearningPattern]:
        location_key = f"{int(context.location[0] / 100)}_{int(context.location[1] / 100)}"

        if self.movement_history:
            prev_location = self.movement_history[-1]
            self.transition_matrix[prev_location][location_key] += 1

        self.movement_history.append(location_key)

        pattern_id = f"movement_{location_key}"
        return LearningPattern(
            pattern_id=pattern_id,
            dimension=LearningDimension.SPATIAL,
            pattern_data={"from": self.movement_history[-2] if len(self.movement_history) > 1 else None,
                          "to": location_key},
            confidence=0.7,
            frequency=1,
            last_updated=datetime.now()
        )

    def predict_movement(self, context: SpatiotemporalContext) -> Dict[str, Any]:
        current_location = f"{int(context.location[0] / 100)}_{int(context.location[1] / 100)}"

        if current_location in self.transition_matrix:
            possible_moves = self.transition_matrix[current_location]
            most_likely = max(possible_moves.items(), key=lambda x: x[1]) if possible_moves else None

            return {
                "current_location": current_location,
                "most_likely_next": most_likely,
                "confidence": 0.6
            }

        return {"current_location": current_location, "confidence": 0.1}


class SpatialAssociationModel:
    """공간 연관성 모델"""

    def __init__(self):
        self.spatial_associations = defaultdict(lambda: defaultdict(int))

    def learn_from_context(self, context: SpatiotemporalContext) -> Optional[LearningPattern]:
        location_key = f"{int(context.location[0] / 50)}_{int(context.location[1] / 50)}"

        for tag in context.context_tags:
            self.spatial_associations[location_key][tag] += 1

        if context.context_tags:
            pattern_id = f"spatial_assoc_{location_key}_{hash(str(sorted(context.context_tags)))}"
            return LearningPattern(
                pattern_id=pattern_id,
                dimension=LearningDimension.SPATIAL,
                pattern_data={"location": location_key, "associations": context.context_tags},
                confidence=0.75,
                frequency=1,
                last_updated=datetime.now()
            )
        return None


class ContextPredictionModel:
    """맥락 예측 모델"""

    def __init__(self):
        self.context_sequences = deque(maxlen=5000)
        self.context_patterns = defaultdict(int)

    def learn_from_context(self, context: SpatiotemporalContext) -> Optional[LearningPattern]:
        context_signature = self._create_context_signature(context)
        self.context_sequences.append(context_signature)
        self.context_patterns[context_signature] += 1

        pattern_id = f"context_{hash(context_signature)}"
        return LearningPattern(
            pattern_id=pattern_id,
            dimension=LearningDimension.CONTEXTUAL,
            pattern_data={"signature": context_signature},
            confidence=0.8,
            frequency=1,
            last_updated=datetime.now()
        )

    def _create_context_signature(self, context: SpatiotemporalContext) -> str:
        return f"{context.timestamp.hour}_{context.user_state}_{sorted(context.context_tags)}"

    def predict_context(self, context: SpatiotemporalContext) -> Dict[str, Any]:
        current_signature = self._create_context_signature(context)
        similar_contexts = [sig for sig in self.context_patterns.keys()
                            if current_signature[:5] in sig]

        return {
            "similar_contexts": similar_contexts[:5],
            "confidence": 0.65
        }


class PatternMatchingModel:
    """패턴 매칭 모델"""

    def __init__(self):
        self.pattern_library = {}

    def learn_from_context(self, context: SpatiotemporalContext) -> Optional[LearningPattern]:
        # 간단한 패턴 매칭 구현
        return None


# 전역 시공간 학습 엔진 인스턴스
spatiotemporal_engine = SpatiotemporalLearningEngine()


def test_spatiotemporal_learning():
    """시공간 학습 시스템 테스트"""
    print("\n🌌 소리새 시공간 학습 시스템 테스트")
    print("=" * 60)

    engine = SpatiotemporalLearningEngine()
    engine._start_time = time.time()

    # 테스트 데이터 생성
    test_contexts = [
        SpatiotemporalContext(
            timestamp=datetime.now() - timedelta(hours=i),
            location=(random.uniform(-100, 100), random.uniform(-100, 100), 0),
            time_scale=TimeScale.HOUR,
            spatial_scale=SpatialScale.ROOM,
            context_tags=random.choices(["작업", "휴식", "음악", "학습", "소통"], k=2),
            user_state=random.choice(["active", "idle", "focused"])
        )
        for i in range(50)
    ]

    # 맥락 데이터 추가
    print("\n📊 테스트 맥락 데이터 추가 중...")
    context_ids = []
    for i, context in enumerate(test_contexts):
        context_id = engine.add_spatiotemporal_context(context)
        context_ids.append(context_id)
        if (i + 1) % 10 == 0:
            print(f"   {i + 1}/50 맥락 추가 완료")

    # 학습 통계 확인
    print(f"\n📈 학습 통계:")
    stats = engine.get_learning_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # 예측 테스트
    print(f"\n🔮 예측 테스트:")
    current_context = SpatiotemporalContext(
        timestamp=datetime.now(),
        location=(50, 25, 0),
        context_tags=["음악", "창작"],
        user_state="active"
    )

    predictions = engine.predict_next_context(current_context)
    print(f"   전체 예측 신뢰도: {predictions['overall_confidence']:.2f}")

    for category, preds in predictions.items():
        if category != 'overall_confidence':
            print(f"   {category}: {len(preds) if isinstance(preds, dict) else preds}개 예측")

    # 시간적 인사이트 분석
    print(f"\n⏰ 시간적 인사이트:")
    temporal_insights = engine.get_temporal_insights()
    for insight_type, data in temporal_insights.items():
        print(f"   {insight_type}: {type(data).__name__}")

    # 공간적 인사이트 분석
    print(f"\n🗺️ 공간적 인사이트:")
    spatial_insights = engine.get_spatial_insights((0, 0, 0), 1000)
    for insight_type, data in spatial_insights.items():
        print(f"   {insight_type}: {type(data).__name__}")

    # 모델 최적화
    print(f"\n⚙️ 학습 모델 최적화:")
    optimization_results = engine.optimize_learning_models()
    for dimension, results in optimization_results.items():
        print(f"   {dimension}: {len(results)}개 모델 최적화")

    print(f"\n🎉 시공간 학습 시스템 테스트 완료!")
    return True


if __name__ == "__main__":
    test_spatiotemporal_learning()
