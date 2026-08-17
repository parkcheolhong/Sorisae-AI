#!/usr/bin/env python3
"""
🧪 소리새 음성 반응형 시스템 테스트
Sorisae Voice Reactive System Tests
"""

import os
import sys
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

# 모듈 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 테스트 대상 모듈 import
from sorisae_voice_reactive import (
    EmotionAnalyzer,
    QuickCommand,
    QuickCommandEngine,
    ReactiveResponse,
    SorisaeVoiceReactive,
    UserPatternLearner,
    VoiceEmotion,
    WakeWordDetector,
)


class TestEmotionAnalyzer(unittest.TestCase):
    """감정 분석기 테스트"""

    def setUp(self):
        self.analyzer = EmotionAnalyzer()

    def test_analyze_happy_emotion(self):
        """기쁜 감정 분석 테스트"""
        result = self.analyzer.analyze_emotion("너무 행복해! 좋아요!")
        self.assertEqual(result.emotion, 'happy')
        self.assertGreater(result.confidence, 0)

    def test_analyze_sad_emotion(self):
        """슬픈 감정 분석 테스트"""
        result = self.analyzer.analyze_emotion("너무 슬퍼요. 우울해요.")
        self.assertEqual(result.emotion, 'sad')
        self.assertGreater(result.confidence, 0)

    def test_analyze_angry_emotion(self):
        """화난 감정 분석 테스트"""
        result = self.analyzer.analyze_emotion("정말 화나! 짜증나!")
        self.assertEqual(result.emotion, 'angry')
        self.assertGreater(result.confidence, 0)

    def test_analyze_neutral_emotion(self):
        """중립 감정 분석 테스트"""
        result = self.analyzer.analyze_emotion("안녕하세요")
        self.assertEqual(result.emotion, 'neutral')

    def test_get_response_style(self):
        """응답 스타일 가져오기 테스트"""
        emotion = VoiceEmotion(
            emotion='happy',
            confidence=0.8,
            intensity=0.5,
            timestamp=datetime.now().isoformat()
        )
        style = self.analyzer.get_response_style(emotion)
        self.assertIn('tone', style)
        self.assertEqual(style['tone'], 'cheerful')


class TestQuickCommandEngine(unittest.TestCase):
    """빠른 명령 엔진 테스트"""

    def setUp(self):
        self.engine = QuickCommandEngine()

    def test_find_light_on_command(self):
        """조명 켜기 명령 찾기 테스트"""
        result = self.engine.find_quick_command("불 켜줘")
        self.assertIsNotNone(result)
        self.assertEqual(result.action, 'light_on')

    def test_find_light_off_command(self):
        """조명 끄기 명령 찾기 테스트"""
        result = self.engine.find_quick_command("불 꺼")
        self.assertIsNotNone(result)
        self.assertEqual(result.action, 'light_off')

    def test_find_music_command(self):
        """음악 명령 찾기 테스트"""
        result = self.engine.find_quick_command("음악 틀어줘")
        self.assertIsNotNone(result)
        self.assertEqual(result.action, 'music_play')

    def test_find_time_command(self):
        """시간 명령 찾기 테스트"""
        result = self.engine.find_quick_command("지금 몇 시야?")
        self.assertIsNotNone(result)
        self.assertEqual(result.action, 'time')

    def test_find_emergency_command(self):
        """비상 명령 찾기 테스트"""
        result = self.engine.find_quick_command("비상 상황이야!")
        self.assertIsNotNone(result)
        self.assertEqual(result.action, 'emergency')

    def test_add_quick_command(self):
        """빠른 명령 추가 테스트"""
        new_cmd = QuickCommand("커피 만들어", "make_coffee", "커피를 만듭니다", priority=5)
        self.engine.add_quick_command(new_cmd)

        result = self.engine.find_quick_command("커피 만들어줘")
        self.assertIsNotNone(result)
        self.assertEqual(result.action, 'make_coffee')

    def test_command_not_found(self):
        """명령을 찾을 수 없는 경우 테스트"""
        result = self.engine.find_quick_command("완전 랜덤한 문장입니다")
        self.assertIsNone(result)

    def test_get_all_commands(self):
        """모든 명령 가져오기 테스트"""
        commands = self.engine.get_all_commands()
        self.assertIsInstance(commands, list)
        self.assertGreater(len(commands), 0)


class TestWakeWordDetector(unittest.TestCase):
    """웨이크 워드 감지기 테스트"""

    def setUp(self):
        self.detector = WakeWordDetector()

    def test_detect_sorisae(self):
        """소리새 웨이크 워드 감지 테스트"""
        # 비상 워드가 없는 경우
        detected, word, is_emergency = self.detector.detect("소리새야 안녕")
        self.assertTrue(detected)
        self.assertEqual(word, '소리새야')
        self.assertFalse(is_emergency)

    def test_detect_alias(self):
        """별칭 감지 테스트"""
        detected, word, is_emergency = self.detector.detect("새야 뭐해?")
        self.assertTrue(detected)
        self.assertEqual(word, '새야')
        self.assertFalse(is_emergency)

    def test_detect_emergency(self):
        """비상 웨이크 워드 감지 테스트"""
        detected, word, is_emergency = self.detector.detect("도와줘!")
        self.assertTrue(detected)
        self.assertTrue(is_emergency)

    def test_no_wake_word(self):
        """웨이크 워드 없는 경우 테스트"""
        detected, word, is_emergency = self.detector.detect("그냥 일반 문장입니다")
        self.assertFalse(detected)
        self.assertEqual(word, '')

    def test_add_wake_word(self):
        """웨이크 워드 추가 테스트"""
        self.detector.add_wake_word("테스트워드")
        detected, word, is_emergency = self.detector.detect("테스트워드 말해봐")
        self.assertTrue(detected)

    def test_add_emergency_wake_word(self):
        """비상 웨이크 워드 추가 테스트"""
        self.detector.add_wake_word("코드레드", is_emergency=True)
        detected, word, is_emergency = self.detector.detect("코드레드!")
        self.assertTrue(detected)
        self.assertTrue(is_emergency)


class TestUserPatternLearner(unittest.TestCase):
    """사용자 패턴 학습기 테스트"""

    def setUp(self):
        self.learner = UserPatternLearner()
        self.test_user_id = "test_user"

    def test_record_command(self):
        """명령 기록 테스트"""
        self.learner.record_command(self.test_user_id, "불 켜줘")
        self.learner.record_command(self.test_user_id, "불 꺼줘")
        self.learner.record_command(self.test_user_id, "음악 틀어줘")

        pattern = self.learner.user_patterns.get(self.test_user_id)
        self.assertIsNotNone(pattern)
        self.assertEqual(pattern.total_interactions, 3)

    def test_get_most_frequent_commands(self):
        """자주 사용하는 명령 가져오기 테스트"""
        # 조명 명령 5번
        for _ in range(5):
            self.learner.record_command(self.test_user_id, "불 켜줘")
        # 음악 명령 3번
        for _ in range(3):
            self.learner.record_command(self.test_user_id, "음악 틀어줘")
        # 날씨 명령 1번
        self.learner.record_command(self.test_user_id, "날씨 어때")

        frequent = self.learner.get_most_frequent_commands(self.test_user_id, top_n=3)
        self.assertEqual(len(frequent), 3)
        # 가장 자주 사용한 명령이 첫 번째
        self.assertEqual(frequent[0][0], 'light')
        self.assertEqual(frequent[0][1], 5)

    def test_record_emotion(self):
        """감정 기록 테스트"""
        emotion = VoiceEmotion(
            emotion='happy',
            confidence=0.9,
            intensity=0.8,
            timestamp=datetime.now().isoformat()
        )
        self.learner.record_command(self.test_user_id, "좋아요!", emotion)

        pattern = self.learner.user_patterns.get(self.test_user_id)
        self.assertEqual(len(pattern.emotion_history), 1)
        self.assertEqual(pattern.emotion_history[0].emotion, 'happy')

    def test_get_average_emotion(self):
        """평균 감정 가져오기 테스트"""
        # 기쁜 감정 3번
        for _ in range(3):
            emotion = VoiceEmotion('happy', 0.8, 0.5, datetime.now().isoformat())
            self.learner.record_command(self.test_user_id, "좋아!", emotion)
        # 슬픈 감정 1번
        emotion = VoiceEmotion('sad', 0.7, 0.4, datetime.now().isoformat())
        self.learner.record_command(self.test_user_id, "슬퍼", emotion)

        avg_emotion = self.learner.get_average_emotion(self.test_user_id)
        self.assertEqual(avg_emotion, 'happy')


class TestSorisaeVoiceReactive(unittest.TestCase):
    """소리새 음성 반응형 시스템 통합 테스트"""

    def setUp(self):
        # VoiceFeedbackSystem의 speak 메서드를 모킹
        with patch('sorisae_voice_reactive.VoiceFeedbackSystem.speak'):
            self.reactive = SorisaeVoiceReactive()
            self.reactive.feedback_system.speak = MagicMock()

    def test_process_quick_command(self):
        """빠른 명령 처리 테스트"""
        response = self.reactive.process_voice_input("불 켜")
        self.assertIsInstance(response, ReactiveResponse)
        self.assertIn("조명", response.text)

    def test_process_with_emotion(self):
        """감정이 포함된 명령 처리 테스트"""
        # '기뻐'는 'happy' 키워드로 인식됨
        response = self.reactive.process_voice_input("너무 기뻐! 정말 행복해!")
        self.assertIsInstance(response, ReactiveResponse)
        self.assertTrue(response.emotion_adapted)

    def test_process_greeting(self):
        """인사 처리 테스트"""
        response = self.reactive.process_voice_input("안녕하세요")
        self.assertIn("안녕", response.text)

    def test_process_thanks(self):
        """감사 인사 처리 테스트"""
        response = self.reactive.process_voice_input("고마워요")
        self.assertIn("천만", response.text)

    def test_statistics(self):
        """통계 테스트"""
        # 몇 가지 명령 처리
        self.reactive.process_voice_input("불 켜")
        self.reactive.process_voice_input("음악 틀어")
        self.reactive.process_voice_input("안녕")

        stats = self.reactive.get_statistics()
        self.assertEqual(stats['total_commands_processed'], 3)
        self.assertGreaterEqual(stats['total_quick_commands'], 2)

    def test_add_quick_command(self):
        """빠른 명령 추가 테스트"""
        self.reactive.add_quick_command("에어컨 켜", "ac_on", "에어컨을 켭니다", priority=8)

        # 새로 추가한 명령 테스트
        response = self.reactive.process_voice_input("에어컨 켜줘")
        self.assertIn("에어컨", response.text)

    def test_add_wake_word(self):
        """웨이크 워드 추가 테스트"""
        self.reactive.add_wake_word("새로운워드")

        detected, word, _ = self.reactive.wake_word_detector.detect("새로운워드 불 켜")
        self.assertTrue(detected)
        self.assertEqual(word, "새로운워드")

    def test_response_time(self):
        """응답 시간 테스트"""
        response = self.reactive.process_voice_input("불 켜")
        self.assertGreater(response.response_time_ms, 0)
        self.assertLess(response.response_time_ms, 1000)  # 1초 미만

    def test_help_command(self):
        """도움말 명령 테스트"""
        response = self.reactive.process_voice_input("도움말")
        self.assertIn("도움말", response.text)
        self.assertIn("소리새", response.text)


class TestVoiceEmotionDataclass(unittest.TestCase):
    """VoiceEmotion 데이터클래스 테스트"""

    def test_create_voice_emotion(self):
        """VoiceEmotion 생성 테스트"""
        emotion = VoiceEmotion(
            emotion='happy',
            confidence=0.9,
            intensity=0.8,
            timestamp='2025-01-01T00:00:00'
        )
        self.assertEqual(emotion.emotion, 'happy')
        self.assertEqual(emotion.confidence, 0.9)
        self.assertEqual(emotion.intensity, 0.8)


class TestReactiveResponseDataclass(unittest.TestCase):
    """ReactiveResponse 데이터클래스 테스트"""

    def test_create_reactive_response(self):
        """ReactiveResponse 생성 테스트"""
        response = ReactiveResponse(
            text="테스트 응답",
            emotion_adapted=True,
            user_pattern_applied=True,
            response_time_ms=50.5,
            feedback_type="audio"
        )
        self.assertEqual(response.text, "테스트 응답")
        self.assertTrue(response.emotion_adapted)
        self.assertEqual(response.response_time_ms, 50.5)


def run_tests():
    """테스트 실행"""
    print("🧪 소리새 음성 반응형 시스템 테스트 시작")
    print("=" * 60)

    # 테스트 스위트 생성
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 모든 테스트 클래스 추가
    suite.addTests(loader.loadTestsFromTestCase(TestEmotionAnalyzer))
    suite.addTests(loader.loadTestsFromTestCase(TestQuickCommandEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestWakeWordDetector))
    suite.addTests(loader.loadTestsFromTestCase(TestUserPatternLearner))
    suite.addTests(loader.loadTestsFromTestCase(TestSorisaeVoiceReactive))
    suite.addTests(loader.loadTestsFromTestCase(TestVoiceEmotionDataclass))
    suite.addTests(loader.loadTestsFromTestCase(TestReactiveResponseDataclass))

    # 테스트 실행
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 결과 출력
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ 모든 테스트 통과!")
    else:
        print(f"❌ 테스트 실패: {len(result.failures)} 실패, {len(result.errors)} 오류")

    return result


if __name__ == "__main__":
    run_tests()
