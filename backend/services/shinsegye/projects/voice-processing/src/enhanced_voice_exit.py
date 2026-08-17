#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🎤 소리새 음성 명령 종료 처리 개선 시스템
Enhanced Voice Command Exit System

음성 명령으로 "종료", "끝", "그만" 등을 말하면
시스템이 안전하게 종료되도록 개선된 처리 시스템
"""

import signal
import sys
import threading
import time

# 전역 종료 플래그
SYSTEM_SHUTDOWN = False


def set_shutdown_flag():
    """전역 종료 플래그 설정"""
    global SYSTEM_SHUTDOWN
    SYSTEM_SHUTDOWN = True


def is_shutdown_requested():
    """종료 요청 확인"""
    return SYSTEM_SHUTDOWN


class EnhancedVoiceExit:
    """개선된 음성 종료 처리 클래스"""

    def __init__(self):
        self.shutdown_callbacks = []
        self.setup_signal_handlers()

    def setup_signal_handlers(self):
        """신호 핸들러 설정"""

        def signal_handler(sig, frame):
            print(f"\n📡 종료 신호 수신: {sig}")
            self.graceful_shutdown()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def add_shutdown_callback(self, callback):
        """종료 콜백 추가"""
        self.shutdown_callbacks.append(callback)

    def graceful_shutdown(self):
        """안전한 종료 처리"""
        print("\n🛑 시스템 종료 시작...")
        set_shutdown_flag()

        # 등록된 콜백 실행
        for callback in self.shutdown_callbacks:
            try:
                callback()
            except Exception as e:
                print(f"⚠️ 종료 콜백 오류: {e}")

        print("✅ 시스템이 안전하게 종료되었습니다.")
        sys.exit(0)

    def check_voice_commands(self, text):
        """음성 명령에서 종료 키워드 확인"""
        exit_keywords = [
            '종료', '끝', '그만', '시스템종료', '시스템꺼줘',
            '꺼줘', '꺼', '닫아', '닫아줘', '그만해',
            'exit', 'quit', 'stop', 'shutdown', 'close'
        ]

        text_lower = text.lower()

        for keyword in exit_keywords:
            if keyword in text_lower:
                print(f"🔔 음성 종료 명령 감지: '{text}'")
                return True

        return False


# 전역 인스턴스
voice_exit_handler = EnhancedVoiceExit()


def register_shutdown_callback(callback):
    """종료 콜백 등록 (전역 함수)"""
    voice_exit_handler.add_shutdown_callback(callback)


def process_voice_command(text):
    """음성 명령 처리 (종료 체크 포함)"""
    if voice_exit_handler.check_voice_commands(text):
        # 종료 응답 후 실제 종료

        def delayed_shutdown():
            time.sleep(1)  # 응답 완료 대기
            voice_exit_handler.graceful_shutdown()

        threading.Thread(target=delayed_shutdown, daemon=True).start()
        return "네, 시스템을 종료합니다. 안녕히 가세요!"

    return None  # 종료 명령이 아님

# 테스트 함수


def test_voice_exit():
    """음성 종료 테스트"""
    print("🎤 음성 종료 테스트")
    print("=" * 50)

    test_commands = [
        "안녕하세요",
        "조명 켜줘",
        "종료",
        "그만해",
        "시스템 꺼줘",
        "quit"
    ]

    for cmd in test_commands:
        print(f"\n입력: '{cmd}'")
        result = process_voice_command(cmd)
        if result:
            print(f"응답: {result}")
            break
        else:
            print("응답: 명령을 처리합니다...")


if __name__ == "__main__":
    test_voice_exit()
