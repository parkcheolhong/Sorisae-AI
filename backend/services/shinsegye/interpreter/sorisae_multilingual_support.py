#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌍 소리새 다국어 지원 시스템 (Sorisae Multilingual Support System)
여러 언어를 지원하는 소리새의 다국어 기능 모듈
"""

from typing import Dict, Optional


class SorisaeMultilingualSupport:
    """소리새 다국어 지원 클래스"""

    def __init__(self):
        """다국어 지원 초기화"""
        self.current_language = "ko"  # 기본 언어: 한국어
        self.supported_languages = ["ko", "en", "ja", "zh", "sorisae"]

        # 다국어 메시지 딕셔너리
        self.messages = {
            "ko": {
                "welcome": "🎵 소리새에 오신 것을 환영합니다!",
                "system_ready": "✅ 시스템이 준비되었습니다.",
                "starting": "🚀 소리새 시스템을 시작합니다...",
                "ai_partner": "🤖 AI 파트너가 준비되었습니다.",
                "game_economy": "🎮 게임 경제 시스템 활성화",
                "creative_mode": "🎨 창작 모드 시작",
                "voice_ready": "🎤 음성 인식 준비 완료",
                "music_composer": "🎵 AI 작곡가 활성화",
                "iot_connected": "🌐 IoT 디바이스 연결됨",
                "goodbye": "👋 안녕히 가세요!"
            },
            "en": {
                "welcome": "🎵 Welcome to Sorisae!",
                "system_ready": "✅ System is ready.",
                "starting": "🚀 Starting Sorisae system...",
                "ai_partner": "🤖 AI Partner is ready.",
                "game_economy": "🎮 Game Economy System Activated",
                "creative_mode": "🎨 Creative Mode Started",
                "voice_ready": "🎤 Voice Recognition Ready",
                "music_composer": "🎵 AI Music Composer Activated",
                "iot_connected": "🌐 IoT Device Connected",
                "goodbye": "👋 Goodbye!"
            },
            "ja": {
                "welcome": "🎵 ソリセへようこそ！",
                "system_ready": "✅ システムの準備ができました。",
                "starting": "🚀 ソリセシステムを起動しています...",
                "ai_partner": "🤖 AIパートナーの準備ができました。",
                "game_economy": "🎮 ゲーム経済システム有効化",
                "creative_mode": "🎨 クリエイティブモード開始",
                "voice_ready": "🎤 音声認識準備完了",
                "music_composer": "🎵 AI作曲家有効化",
                "iot_connected": "🌐 IoTデバイス接続済み",
                "goodbye": "👋 さようなら！"
            },
            "zh": {
                "welcome": "🎵 欢迎来到声鸟！",
                "system_ready": "✅ 系统已准备就绪。",
                "starting": "🚀 正在启动声鸟系统...",
                "ai_partner": "🤖 AI伙伴已准备就绪。",
                "game_economy": "🎮 游戏经济系统已激活",
                "creative_mode": "🎨 创作模式已开始",
                "voice_ready": "🎤 语音识别准备完毕",
                "music_composer": "🎵 AI作曲家已激活",
                "iot_connected": "🌐 IoT设备已连接",
                "goodbye": "👋 再见！"
            },
            "sorisae": {
                "welcome": "🎵 Sora-wel to Sorisae!",
                "system_ready": "✅ Sora-sys ready-ok.",
                "starting": "🚀 Sora-sys start-now...",
                "ai_partner": "🤖 Sora-AI ready-ok.",
                "game_economy": "🎮 Sora-game eco-on",
                "creative_mode": "🎨 Sora-create mode-start",
                "voice_ready": "🎤 Sora-voice ready-ok",
                "music_composer": "🎵 Sora-music AI-on",
                "iot_connected": "🌐 Sora-IoT link-ok",
                "goodbye": "👋 Sora-bye!"
            }
        }

        print(f"🌍 다국어 지원 시스템 초기화 완료 (지원 언어: {', '.join(self.supported_languages)})")

    def set_language(self, language_code: str) -> bool:
        """
        현재 언어 설정

        Args:
            language_code: 언어 코드 (ko, en, ja, zh)

        Returns:
            bool: 설정 성공 여부
        """
        if language_code in self.supported_languages:
            self.current_language = language_code
            print(f"✅ 언어가 '{language_code}'로 설정되었습니다.")
            return True
        else:
            print(f"❌ 지원하지 않는 언어입니다: {language_code}")
            return False

    def get_message(self, key: str, language: Optional[str] = None) -> str:
        """
        다국어 메시지 가져오기

        Args:
            key: 메시지 키
            language: 언어 코드 (None이면 현재 설정된 언어 사용)

        Returns:
            str: 해당 언어의 메시지
        """
        lang = language or self.current_language

        if lang not in self.messages:
            lang = "ko"  # 기본값

        return self.messages[lang].get(key, f"[{key}]")

    def get_all_messages(self, language: Optional[str] = None) -> Dict[str, str]:
        """
        모든 메시지 가져오기

        Args:
            language: 언어 코드 (None이면 현재 설정된 언어 사용)

        Returns:
            dict: 해당 언어의 모든 메시지
        """
        lang = language or self.current_language
        return self.messages.get(lang, self.messages["ko"])

    def add_custom_message(self, key: str, translations: Dict[str, str]):
        """
        사용자 정의 메시지 추가

        Args:
            key: 메시지 키
            translations: 언어별 번역 딕셔너리
        """
        for lang in self.supported_languages:
            if lang in translations:
                self.messages[lang][key] = translations[lang]

        print(f"✅ 사용자 정의 메시지 '{key}' 추가 완료")

    def display_language_menu(self):
        """언어 선택 메뉴 표시"""
        print("\n🌍 언어 선택 / Language Selection")
        print("=" * 50)
        print("1. 🇰🇷 한국어 (Korean)")
        print("2. 🇺🇸 English")
        print("3. 🇯🇵 日本語 (Japanese)")
        print("4. 🇨🇳 中文 (Chinese)")
        print("5. 🎵 소리새어 (Sorisae Language)")
        print("=" * 50)

    def get_language_name(self, code: str) -> str:
        """언어 코드를 언어 이름으로 변환"""
        names = {
            "ko": "한국어",
            "en": "English",
            "ja": "日本語",
            "zh": "中文",
            "sorisae": "소리새어 (Sorisae)"
        }
        return names.get(code, code)

    def demo(self):
        """다국어 지원 데모"""
        print("\n" + "=" * 60)
        print("🌍 소리새 다국어 지원 시스템 데모")
        print("=" * 60)

        for lang in self.supported_languages:
            print(f"\n--- {self.get_language_name(lang)} ---")
            self.set_language(lang)

            # 주요 메시지 출력
            print(self.get_message("welcome"))
            print(self.get_message("starting"))
            print(self.get_message("system_ready"))
            print(self.get_message("ai_partner"))
            print(self.get_message("goodbye"))

        # 원래 언어로 복구
        self.set_language("ko")
        print("\n✅ 다국어 지원 데모 완료!")


def main():
    """메인 함수"""
    print("🌍 소리새 다국어 지원 시스템")
    print("=" * 60)

    # 다국어 지원 시스템 생성
    multilang = SorisaeMultilingualSupport()

    # 데모 실행
    multilang.demo()

    # 대화형 모드
    print("\n" + "=" * 60)
    print("🎯 대화형 언어 변경 테스트")
    print("=" * 60)

    while True:
        multilang.display_language_menu()
        choice = input("\n언어를 선택하세요 (1-5, 0=종료): ").strip()

        if choice == "0":
            print(multilang.get_message("goodbye"))
            break
        elif choice == "1":
            multilang.set_language("ko")
            print(multilang.get_message("welcome"))
        elif choice == "2":
            multilang.set_language("en")
            print(multilang.get_message("welcome"))
        elif choice == "3":
            multilang.set_language("ja")
            print(multilang.get_message("welcome"))
        elif choice == "4":
            multilang.set_language("zh")
            print(multilang.get_message("welcome"))
        elif choice == "5":
            multilang.set_language("sorisae")
            print(multilang.get_message("welcome"))
        else:
            print("❌ 잘못된 선택입니다.")


if __name__ == "__main__":
    main()
