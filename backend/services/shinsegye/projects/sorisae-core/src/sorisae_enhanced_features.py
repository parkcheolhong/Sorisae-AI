#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎵 소리새 추가 기능 모듈 (Sorisae Additional Features)
다국어 지원과 IoT 통합을 포함한 소리새의 확장 기능들
"""

import os
import sys
from datetime import datetime

# 프로젝트 경로 추가
sys.path.append(os.getcwd())

# 새로운 기능 모듈 import
try:
    from sorisae_multilingual_support import SorisaeMultilingualSupport
    print("✅ 다국어 지원 모듈 로드 완료")
    MULTILANG_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 다국어 지원 모듈 로드 실패: {e}")
    MULTILANG_AVAILABLE = False

try:
    from sorisae_iot_integration import SmartLight, SmartSpeaker, SmartThermostat, SorisaeIoTIntegration
    print("✅ IoT 통합 모듈 로드 완료")
    IOT_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ IoT 통합 모듈 로드 실패: {e}")
    IOT_AVAILABLE = False


class SorisaeEnhancedFeatures:
    """소리새 확장 기능 통합 클래스"""

    def __init__(self):
        """확장 기능 초기화"""
        print("\n🎵 소리새 확장 기능 초기화 중...")

        # 다국어 지원 시스템
        self.multilang = None
        if MULTILANG_AVAILABLE:
            self.multilang = SorisaeMultilingualSupport()

        # IoT 통합 시스템
        self.iot_system = None
        if IOT_AVAILABLE:
            self.iot_system = SorisaeIoTIntegration()

        self.current_mode = "standard"  # standard, creative, gaming
        self.features_enabled = {
            "multilingual": MULTILANG_AVAILABLE,
            "iot": IOT_AVAILABLE,
            "voice_control": True,
            "ai_collaboration": True
        }

        print("✅ 소리새 확장 기능 초기화 완료")

    def display_banner(self):
        """환영 배너 출력"""
        banner = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🎵 소리새 (Sorisae) 확장 기능 v1.0                         ║
║                     다국어 + IoT 통합 시스템                                   ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  🌍 다국어 지원:    한국어, English, 日本語, 中文                              ║
║  🌐 IoT 통합:       스마트홈 디바이스 제어                                     ║
║  🎤 음성 제어:      자연어 명령 처리                                          ║
║  🤖 AI 협업:        지능형 보조 시스템                                        ║
║                                                                              ║
║  🎯 시스템 상태: {'🟢 정상' if self.check_system_health() else '🟡 일부 제한'}                                                    ║
║  ⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                  ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """
        print(banner)

    def check_system_health(self) -> bool:
        """시스템 상태 확인"""
        return MULTILANG_AVAILABLE and IOT_AVAILABLE

    def setup_multilingual(self):
        """다국어 지원 설정"""
        if not self.multilang:
            print("❌ 다국어 지원 모듈이 로드되지 않았습니다.")
            return

        print("\n🌍 다국어 지원 설정")
        print("=" * 60)

        self.multilang.display_language_menu()

        choice = input("\n언어를 선택하세요 (1-4): ").strip()

        lang_map = {
            "1": "ko",
            "2": "en",
            "3": "ja",
            "4": "zh"
        }

        if choice in lang_map:
            self.multilang.set_language(lang_map[choice])
            print(self.multilang.get_message("system_ready"))
        else:
            print("❌ 잘못된 선택입니다.")

    def setup_iot_devices(self):
        """IoT 디바이스 설정"""
        if not self.iot_system:
            print("❌ IoT 통합 모듈이 로드되지 않았습니다.")
            return

        print("\n🌐 IoT 디바이스 설정")
        print("=" * 60)

        # 기본 디바이스 등록
        devices = [
            SmartSpeaker("speaker_001", "소리새 스피커"),
            SmartLight("light_living", "거실 조명"),
            SmartLight("light_bedroom", "침실 조명"),
            SmartThermostat("thermo_main", "중앙 온도조절기")
        ]

        for device in devices:
            self.iot_system.register_device(device)

        # 모든 디바이스 연결
        self.iot_system.connect_all_devices()

        # 디바이스 목록 표시
        self.iot_system.list_devices()

    def voice_command_handler(self, command: str):
        """
        통합 음성 명령 처리

        Args:
            command: 음성 명령 텍스트
        """
        print(f"\n🎤 음성 명령: '{command}'")

        # 언어 변경 명령
        if "언어" in command or "language" in command.lower():
            if self.multilang:
                self.setup_multilingual()
            return

        # IoT 제어 명령
        if self.iot_system:
            self.iot_system.voice_command(command)

        # AI 협업 명령
        if "ai" in command.lower() or "에이아이" in command:
            print("🤖 AI 협업 모드를 활성화합니다...")
            self.current_mode = "creative"

    def run_feature_demo(self):
        """기능 데모 실행"""
        print("\n" + "=" * 60)
        print("🎬 소리새 확장 기능 데모")
        print("=" * 60)

        # 1. 다국어 지원 데모
        if self.multilang:
            print("\n🌍 1. 다국어 지원 데모")
            print("-" * 60)

            for lang in ["ko", "en", "ja", "zh"]:
                self.multilang.set_language(lang)
                print(f"  {self.multilang.get_message('welcome')}")

            # 원래 언어로 복구
            self.multilang.set_language("ko")

        # 2. IoT 통합 데모
        if self.iot_system:
            print("\n🌐 2. IoT 통합 데모")
            print("-" * 60)

            # IoT 디바이스 설정 (이미 설정되지 않았다면)
            if not self.iot_system.devices:
                self.setup_iot_devices()

            # 간단한 시나리오
            print("\n  💡 스마트홈 시나리오 실행...")

            # 조명 제어
            for device in self.iot_system.devices.values():
                if hasattr(device, 'turn_on'):
                    device.turn_on()

            # 스피커로 안내
            for device in self.iot_system.devices.values():
                if hasattr(device, 'speak'):
                    device.speak("소리새 시스템이 준비되었습니다!")

        # 3. 음성 명령 데모
        print("\n🎤 3. 음성 명령 처리 데모")
        print("-" * 60)

        test_commands = [
            "조명 켜줘",
            "음악 재생해줘",
            "온도 22도로 설정해줘"
        ]

        for cmd in test_commands:
            self.voice_command_handler(cmd)

        print("\n✅ 모든 데모 완료!")

    def show_feature_status(self):
        """기능 상태 표시"""
        print("\n📊 소리새 확장 기능 상태")
        print("=" * 60)

        def status_icon(x): return "🟢 활성화" if x else "🔴 비활성화"

        print(f"  🌍 다국어 지원:    {status_icon(self.features_enabled['multilingual'])}")
        print(f"  🌐 IoT 통합:       {status_icon(self.features_enabled['iot'])}")
        print(f"  🎤 음성 제어:      {status_icon(self.features_enabled['voice_control'])}")
        print(f"  🤖 AI 협업:        {status_icon(self.features_enabled['ai_collaboration'])}")

        if self.multilang:
            print(f"\n  현재 언어: {self.multilang.get_language_name(self.multilang.current_language)}")

        if self.iot_system:
            iot_status = self.iot_system.get_system_status()
            print(f"\n  IoT 디바이스: {iot_status['online_devices']}/{iot_status['total_devices']} 온라인")

    def run_interactive_menu(self):
        """대화형 메뉴"""
        while True:
            print("\n" + "=" * 60)
            print("🎵 소리새 확장 기능 메뉴")
            print("=" * 60)
            print("1. 🌍 다국어 설정")
            print("2. 🌐 IoT 디바이스 설정")
            print("3. 🎬 기능 데모 실행")
            print("4. 📊 기능 상태 확인")
            print("5. 🎤 음성 명령 테스트")
            print("0. ❌ 종료")

            choice = input("\n선택하세요 (0-5): ").strip()

            if choice == "0":
                print("\n👋 소리새를 종료합니다.")
                if self.multilang:
                    print(self.multilang.get_message("goodbye"))
                break
            elif choice == "1":
                self.setup_multilingual()
            elif choice == "2":
                self.setup_iot_devices()
            elif choice == "3":
                self.run_feature_demo()
            elif choice == "4":
                self.show_feature_status()
            elif choice == "5":
                cmd = input("음성 명령을 입력하세요: ").strip()
                if cmd:
                    self.voice_command_handler(cmd)
            else:
                print("❌ 잘못된 선택입니다.")

    def run(self):
        """확장 기능 실행"""
        self.display_banner()

        # 초기 설정
        if self.iot_system:
            self.setup_iot_devices()

        # 기능 상태 표시
        self.show_feature_status()

        # 자동 데모 실행
        print("\n🎯 자동 데모를 실행합니다...")
        import time
        time.sleep(1)
        self.run_feature_demo()

        # 대화형 메뉴
        print("\n🎯 대화형 메뉴를 시작합니다...")
        time.sleep(1)

        try:
            self.run_interactive_menu()
        except KeyboardInterrupt:
            print("\n🛑 사용자에 의한 종료")

        # 정리
        if self.iot_system:
            self.iot_system.disconnect_all_devices()


def main():
    """메인 함수"""
    print("🎵 소리새 (Sorisae) 확장 기능 시스템")
    print("=" * 60)
    print("다국어 지원 + IoT 통합 + 음성 제어")
    print("=" * 60)

    try:
        # 확장 기능 시스템 생성 및 실행
        enhanced = SorisaeEnhancedFeatures()
        enhanced.run()

    except KeyboardInterrupt:
        print("\n🛑 프로그램이 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

    print("\n🌟 소리새 확장 기능을 종료합니다!")


if __name__ == "__main__":
    main()
