#!/usr/bin/env python3
"""
🧪 대시보드 음성 2중 발화 문제 수정 테스트
Test for Dashboard Double Voice Utterance Fix
"""

import os
import sys
import unittest
from pathlib import Path

# 프로젝트 루트를 PYTHONPATH에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class VoiceDoubleUtteranceFixTest(unittest.TestCase):
    """음성 2중 발화 수정 테스트"""

    @classmethod
    def setUpClass(cls):
        """테스트 클래스 셋업"""
        try:
            # 대시보드 모듈 import
            import sorisae_integrated_dashboard

            cls.dashboard_module = sorisae_integrated_dashboard
            cls.available = True
        except ImportError as e:
            cls.available = False
            cls.import_error = str(e)

    def test_dashboard_html_has_no_duplicate_speak_calls(self):
        """대시보드 HTML에 중복된 speak 호출이 없는지 확인"""
        if not self.available:
            self.skipTest(f"대시보드 모듈 import 실패: {self.import_error}")

        # DASHBOARD_HTML 가져오기
        html_content = self.dashboard_module.DASHBOARD_HTML

        # processVoiceCommand 함수 찾기
        self.assertIn("function processVoiceCommand", html_content)

        # processVoiceCommand 함수 내용 추출
        start_idx = html_content.find("function processVoiceCommand")
        end_idx = html_content.find("function speak(text)", start_idx)

        self.assertGreater(start_idx, -1, "processVoiceCommand 함수를 찾을 수 없습니다")
        self.assertGreater(end_idx, start_idx, "speak 함수를 찾을 수 없습니다")

        process_voice_func = html_content[start_idx:end_idx]

        # 서버 응답 처리가 있는지 확인
        self.assertIn("voice_response", process_voice_func)
        self.assertIn("socket.once('voice_response'", process_voice_func)

        # setTimeout으로 speak를 호출하는 중복 코드가 없는지 확인
        self.assertNotIn("setTimeout", process_voice_func,
                         "processVoiceCommand에 setTimeout이 있으면 안됩니다 (중복 응답 발생)")

        # 로컬 responses 객체가 없는지 확인
        self.assertNotIn("const responses = {", process_voice_func,
                         "processVoiceCommand에 로컬 responses 객체가 있으면 안됩니다")

    def test_server_has_voice_response_generation(self):
        """서버에 음성 응답 생성 로직이 있는지 확인"""
        if not self.available:
            self.skipTest(f"대시보드 모듈 import 실패: {self.import_error}")

        # generate_voice_response 함수가 존재하는지 확인
        self.assertTrue(
            hasattr(self.dashboard_module, "generate_voice_response"),
            "generate_voice_response 함수가 존재해야 합니다"
        )

        # 함수 테스트
        response = self.dashboard_module.generate_voice_response("상태")
        self.assertIsNotNone(response)
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)

    def test_voice_response_keywords(self):
        """음성 응답이 주요 키워드에 대해 올바르게 생성되는지 확인"""
        if not self.available:
            self.skipTest(f"대시보드 모듈 import 실패: {self.import_error}")

        generate_voice_response = self.dashboard_module.generate_voice_response

        # 주요 키워드 테스트
        test_cases = {
            "상태": "시스템",
            "듀얼브레인": "분석",
            "iot": "IoT",
            "쇼핑몰": "쇼핑몰",
            "테스트": "테스트",
        }

        for keyword, expected_word in test_cases.items():
            with self.subTest(keyword=keyword):
                response = generate_voice_response(keyword)
                self.assertIsNotNone(response)
                self.assertIsInstance(response, str)
                # 응답에 예상 단어가 포함되어 있는지 확인
                self.assertTrue(
                    expected_word in response or keyword in response,
                    f"'{keyword}' 명령의 응답 '{response}'에 '{expected_word}' 또는 '{keyword}'가 포함되어야 합니다"
                )

    def test_socket_handler_emits_voice_response(self):
        """소켓 핸들러가 voice_response를 emit하는지 확인"""
        if not self.available:
            self.skipTest(f"대시보드 모듈 import 실패: {self.import_error}")

        # handle_remote_command 함수 소스 확인
        import inspect

        handler_source = inspect.getsource(
            self.dashboard_module.handle_remote_command
        )

        # voice_response emit 확인
        self.assertIn("emit", handler_source)
        self.assertIn("voice_response", handler_source)
        self.assertIn("generate_voice_response", handler_source)

    def test_no_duplicate_response_in_html(self):
        """HTML에 중복 응답 로직이 없는지 확인"""
        if not self.available:
            self.skipTest(f"대시보드 모듈 import 실패: {self.import_error}")

        html_content = self.dashboard_module.DASHBOARD_HTML

        # processVoiceCommand 함수 찾기
        start_idx = html_content.find("function processVoiceCommand")
        end_idx = html_content.find("}", start_idx)

        # 함수 끝까지 찾기 (중첩된 중괄호 고려)
        brace_count = 0
        for i in range(start_idx, len(html_content)):
            if html_content[i] == "{":
                brace_count += 1
            elif html_content[i] == "}":
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i + 1
                    break

        process_voice_func = html_content[start_idx:end_idx]

        # speak() 호출 횟수 세기
        speak_calls = process_voice_func.count("speak(")

        # socket.once 내부의 speak() 호출 1번만 있어야 함
        self.assertEqual(
            speak_calls, 1,
            f"processVoiceCommand에서 speak()는 1번만 호출되어야 합니다 (현재: {speak_calls}번)"
        )


def main():
    """테스트 실행"""
    print("=" * 70)
    print("🧪 대시보드 음성 2중 발화 문제 수정 테스트")
    print("=" * 70)

    # 테스트 로더
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 테스트 케이스 추가
    suite.addTests(loader.loadTestsFromTestCase(VoiceDoubleUtteranceFixTest))

    # 테스트 실행
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 결과 반환
    return result.wasSuccessful()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
