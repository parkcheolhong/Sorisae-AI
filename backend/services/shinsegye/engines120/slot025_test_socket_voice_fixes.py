#!/usr/bin/env python3
"""
🔧 소켓 및 음성 루프 수정사항 테스트
Socket and Voice Loop Fixes Test

WinError 10038 소켓 오류 및 음성 무한 루프 수정사항 검증
"""

import sys
import unittest
from pathlib import Path

# 프로젝트 루트를 PYTHONPATH에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class SocketVoiceFixesTests(unittest.TestCase):
    """소켓 및 음성 루프 수정사항 테스트"""

    @classmethod
    def setUpClass(cls):
        """테스트 클래스 셋업"""
        try:
            from sorisae_integrated_dashboard import app, socketio, state

            cls.app = app
            cls.socketio = socketio
            cls.state = state
            cls.client = app.test_client()
            cls.available = True
        except ImportError as e:
            cls.available = False
            cls.import_error = str(e)

    def test_socketio_configuration(self):
        """SocketIO 설정 테스트 - 타임아웃 및 로거 설정 확인"""
        if not self.available:
            self.skipTest(f"대시보드 모듈 import 실패: {self.import_error}")

        # SocketIO 인스턴스가 올바르게 설정되었는지 확인
        self.assertIsNotNone(self.socketio)

        # 설정 확인 (내부 속성)
        server_options = self.socketio.server.eio.ping_timeout
        self.assertIsNotNone(server_options)
        print(f"✅ SocketIO ping_timeout 설정됨: {server_options}초")

    def test_disconnect_handler_exists(self):
        """disconnect 핸들러 존재 확인"""
        if not self.available:
            self.skipTest(f"대시보드 모듈 import 실패: {self.import_error}")

        # disconnect 핸들러가 등록되어 있는지 확인
        from sorisae_integrated_dashboard import handle_disconnect

        self.assertIsNotNone(handle_disconnect)
        self.assertTrue(callable(handle_disconnect))
        print("✅ disconnect 핸들러가 정의되어 있습니다")

    def test_remote_command_error_handling(self):
        """remote_command 핸들러 오류 처리 테스트"""
        if not self.available:
            self.skipTest(f"대시보드 모듈 import 실패: {self.import_error}")

        from sorisae_integrated_dashboard import handle_remote_command

        # 핸들러가 존재하는지 확인
        self.assertIsNotNone(handle_remote_command)
        self.assertTrue(callable(handle_remote_command))

        # 핸들러가 try-except 블록을 사용하는지 소스 코드로 확인
        import inspect

        source = inspect.getsource(handle_remote_command)
        self.assertIn("try:", source)
        self.assertIn("except Exception", source)
        print("✅ remote_command 핸들러에 오류 처리가 포함되어 있습니다")

    def test_get_stats_error_handling(self):
        """get_stats 핸들러 오류 처리 테스트"""
        if not self.available:
            self.skipTest(f"대시보드 모듈 import 실패: {self.import_error}")

        from sorisae_integrated_dashboard import handle_get_stats

        # 핸들러가 존재하는지 확인
        self.assertIsNotNone(handle_get_stats)
        self.assertTrue(callable(handle_get_stats))

        # 핸들러가 try-except 블록을 사용하는지 소스 코드로 확인
        import inspect

        source = inspect.getsource(handle_get_stats)
        self.assertIn("try:", source)
        self.assertIn("except Exception", source)
        print("✅ get_stats 핸들러에 오류 처리가 포함되어 있습니다")

    def test_voice_response_generation(self):
        """음성 응답 생성 테스트"""
        if not self.available:
            self.skipTest(f"대시보드 모듈 import 실패: {self.import_error}")

        from sorisae_integrated_dashboard import generate_voice_response

        # 다양한 명령어에 대한 응답 생성 테스트
        test_cases = [
            ("상태", "시스템"),
            ("듀얼브레인", "분석"),
            ("IoT", "동기화"),
            ("쇼핑몰", "최적화"),
            ("테스트", "테스트"),
            ("알 수 없는 명령", "명령을 처리했습니다"),
        ]

        for command, expected_keyword in test_cases:
            response = generate_voice_response(command)
            self.assertIsNotNone(response)
            self.assertIsInstance(response, str)
            self.assertGreater(len(response), 0)
            self.assertIn(expected_keyword, response)  # 응답에 예상 키워드 포함 확인
            print(f"✅ '{command}' 명령에 대한 응답 생성: {response[:50]}...")

    def test_html_contains_voice_loop_prevention(self):
        """HTML에 음성 루프 방지 로직이 포함되어 있는지 확인"""
        if not self.available:
            self.skipTest(f"대시보드 모듈 import 실패: {self.import_error}")

        # HTML 템플릿 가져오기
        from sorisae_integrated_dashboard import DASHBOARD_HTML

        # 음성 루프 방지 관련 코드가 포함되어 있는지 확인
        self.assertIn("isSpeaking", DASHBOARD_HTML)
        self.assertIn("TTS 발화 중", DASHBOARD_HTML)
        print("✅ HTML에 isSpeaking 플래그가 포함되어 있습니다")

        # TTS 이벤트 핸들러 확인
        self.assertIn("utterance.onstart", DASHBOARD_HTML)
        self.assertIn("utterance.onend", DASHBOARD_HTML)
        self.assertIn("utterance.onerror", DASHBOARD_HTML)
        print("✅ HTML에 TTS 이벤트 핸들러가 포함되어 있습니다")

        # 음성 인식 중지 로직 확인
        self.assertIn("recognition.stop()", DASHBOARD_HTML)
        print("✅ HTML에 음성 인식 중지 로직이 포함되어 있습니다")

    def test_api_health_endpoint(self):
        """헬스체크 API 테스트"""
        if not self.available:
            self.skipTest(f"대시보드 모듈 import 실패: {self.import_error}")

        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertIsNotNone(data)
        self.assertEqual(data.get("status"), "healthy")
        self.assertIn("timestamp", data)
        print("✅ 헬스체크 API가 정상 작동합니다")

    def test_state_management(self):
        """상태 관리 테스트"""
        if not self.available:
            self.skipTest(f"대시보드 모듈 import 실패: {self.import_error}")

        # 명령 추가 테스트
        initial_count = self.state.command_count
        command_data = self.state.add_voice_command("테스트 명령", "성공")

        self.assertIsNotNone(command_data)
        self.assertEqual(command_data["command"], "테스트 명령")
        self.assertEqual(command_data["status"], "성공")
        self.assertEqual(self.state.command_count, initial_count + 1)
        print("✅ 상태 관리가 정상 작동합니다")


def run_tests():
    """테스트 실행"""
    print("=" * 60)
    print("🔧 소켓 및 음성 루프 수정사항 테스트 시작")
    print("=" * 60)

    # 테스트 스위트 생성
    suite = unittest.TestLoader().loadTestsFromTestCase(SocketVoiceFixesTests)

    # 테스트 실행
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ 모든 테스트 통과!")
    else:
        print("❌ 일부 테스트 실패")
    print("=" * 60)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
