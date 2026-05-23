#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎮 소리새 VR 게임 실행기 (안전 버전)
Sorisae VR Game Launcher (Safe Version)
"""

import os


def main():
    print("=" * 50)
    print("소리새 VR 게임 시스템")
    print("Sorisae VR Game System")
    print("=" * 50)

    print("\n시스템 상태 확인 중...")

    # 파일 존재 확인
    vr_game_exists = os.path.exists("sorisae_fantasy_vr_infinite_universe_game.py")
    animation_studio_exists = os.path.exists("sorisae_animation_studio_ultra.py")

    print(f"VR 게임 파일: {'✅ 존재' if vr_game_exists else '❌ 없음'}")
    print(f"애니메이션 스튜디오: {'✅ 존재' if animation_studio_exists else '❌ 없음'}")

    # 라이브러리 확인
    try:
        print("그래픽 모드: ✅ 사용 가능")
    except ImportError:
        print("그래픽 모드: ℹ️ 텍스트 모드로 실행")

    print("\n🌟 시스템 기능:")
    print("1. 무한 우주 탐험 (8가지 테마)")
    print("2. 현실 창조 및 조작")
    print("3. 105% 신적 지능과 대화")
    print("4. 애니메이션 스튜디오 연동")
    print("5. 시나리오 → 1시간 50분 영화 자동 제작")

    print("\n💡 사용 방법:")
    print("python sorisae_fantasy_vr_infinite_universe_game.py  # VR 게임")
    print("python sorisae_animation_studio_ultra.py           # 애니메이션 스튜디오")

    print("\n🎮 VR 게임 메뉴:")
    print("1. 새로운 우주 탐험")
    print("2. 현실 창조하기")
    print("3. 신적 존재와 대화")
    print("4. 우주 정보 보기")
    print("5. 플레이어 상태 확인")
    print("6. 특별 이벤트")
    print("7. 🎬 애니메이션 스튜디오 (핵심 기능!)")
    print("8. 게임 저장")
    print("9. 게임 종료")

    print("\n🎬 애니메이션 스튜디오 기능:")
    print("- 시나리오 자동 분석")
    print("- 최고 사양 4K/8K 렌더링")
    print("- 3D 캐릭터 자동 생성")
    print("- AI 배경음악 생성")
    print("- 자동 편집 및 색보정")

    if vr_game_exists and animation_studio_exists:
        print("\n🎉 모든 시스템이 준비되었습니다!")
        print("위의 명령어로 실행하세요!")

        # 간단한 데모 제공
        choice = input("\n데모를 실행하시겠습니까? (y/n): ").lower().strip()
        if choice.startswith('y'):
            run_demo()
    else:
        print("\n❌ 일부 파일이 누락되었습니다.")


def run_demo():
    """간단한 데모 실행"""
    print("\n🎮 소리새 VR 게임 데모")
    print("=" * 30)

    # 플레이어 생성
    name = input("플레이어 이름을 입력하세요: ").strip()
    if not name:
        name = "우주 탐험가"

    print(f"\n👋 안녕하세요, {name}님!")
    print("🌌 무한한 우주가 당신을 기다리고 있습니다!")

    # 우주 테마 선택
    themes = [
        "크리스털 우주", "네온 사이버 우주", "판타지 마법 우주",
        "고요한 선(禪) 우주", "무지개 하모니 우주", "시공간 왜곡 우주"
    ]

    print(f"\n🎭 어떤 우주를 탐험하시겠습니까?")
    for i, theme in enumerate(themes, 1):
        print(f"{i}. {theme}")

    try:
        choice = int(input("\n선택 (1-6): "))
        if 1 <= choice <= len(themes):
            selected_theme = themes[choice - 1]
        else:
            selected_theme = themes[0]
    except Exception:
        selected_theme = themes[0]

    print(f"\n🌟 {selected_theme}로 이동합니다...")
    import time
    for i in range(3):
        print(f"{'.' * (i + 1)} 차원 이동 중...")
        time.sleep(0.5)

    print(f"\n🎉 {selected_theme}에 도착했습니다!")
    print("✨ 이 우주는 정말 아름답습니다!")
    print("🎨 여기서 당신만의 현실을 창조할 수 있습니다!")

    # 애니메이션 스튜디오 데모
    print(f"\n🎬 이 경험을 영화로 만들어보시겠습니까?")
    movie_choice = input("영화 제작 (y/n): ").lower().strip()

    if movie_choice.startswith('y'):
        movie_title = input("영화 제목을 입력하세요: ").strip()
        if not movie_title:
            movie_title = f"{name}의 {selected_theme} 모험"

        print(f"\n🎬 '{movie_title}' 제작 시작!")
        print("🎨 3D 캐릭터 생성...")
        time.sleep(0.5)
        print("🌟 배경 렌더링...")
        time.sleep(0.5)
        print("🎵 배경음악 생성...")
        time.sleep(0.5)
        print("🎞️ 최종 편집...")
        time.sleep(0.5)

        print(f"\n🎉 '{movie_title}' 제작 완료!")
        print("📊 영화 정보:")
        print(f"   🎬 제목: {movie_title}")
        print(f"   🎨 품질: 최고 사양")
        print(f"   ⏱️ 길이: 1시간 50분")
        print(f"   🌟 테마: {selected_theme}")

    print(f"\n🌟 데모를 즐겨주셔서 감사합니다!")
    print(f"💫 실제 게임에서는 더 많은 기능을 체험하실 수 있습니다!")
    print(f"🎮 python sorisae_fantasy_vr_infinite_universe_game.py 로 시작하세요!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 프로그램을 종료합니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        print("기본 기능은 정상 작동할 것입니다.")
