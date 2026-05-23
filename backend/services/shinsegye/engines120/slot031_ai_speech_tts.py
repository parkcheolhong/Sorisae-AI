#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎤 소리새 AI 음성 테스트 (SoriSay Voice Test)
한국어 TTS 음성 출력 테스트 프로그램
"""

import sys

import pyttsx3


def speak(text: str):
    """텍스트를 한국어 음성으로 출력"""
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)  # 음성 속도 설정
        engine.setProperty('volume', 0.9)  # 볼륨 설정

        # 사용 가능한 음성 확인
        voices = engine.getProperty('voices')
        korean_voice = None

        for voice in voices:
            if 'korean' in voice.name.lower() or 'heami' in voice.name.lower():
                korean_voice = voice.id
                break

        if korean_voice:
            engine.setProperty('voice', korean_voice)
            print(f"✅ 한국어 음성 선택됨: {korean_voice}")
        else:
            print("⚠️ 한국어 음성을 찾을 수 없습니다. 기본 음성을 사용합니다.")

        print(f"🔊 음성 출력: {text}")
        engine.say(text)
        engine.runAndWait()
        print("✅ 음성 출력 완료!")

    except Exception as e:
        print(f"❌ 음성 출력 오류: {e}")


def test_voice():
    """음성 테스트 실행"""
    print("🎤=" * 40)
    print("🎤 소리새 AI 음성 테스트 시작!")
    print("🎤=" * 40)

    test_messages = [
        "안녕하세요! 소리새 AI입니다.",
        "음성 테스트를 시작하겠습니다.",
        "한국어 음성이 정상적으로 출력되는지 확인해주세요.",
        "소리새 월드에 오신 것을 환영합니다!",
        "AI와 함께 게임으로 돈을 벌어보세요!"
    ]

    for i, message in enumerate(test_messages, 1):
        print(f"\n🎯 테스트 {i}/5:")
        speak(message)
        input("⏸️  Enter를 눌러서 다음 테스트로 진행... ")

    print("\n🎉 음성 테스트 완료!")
    print("모든 메시지가 정상적으로 들리셨나요? 😊")


if __name__ == "__main__":
    try:
        test_voice()
    except KeyboardInterrupt:
        print("\n\n🛑 사용자에 의한 테스트 종료")
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        sys.exit(1)
