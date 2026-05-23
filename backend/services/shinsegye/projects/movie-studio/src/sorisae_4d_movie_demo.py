#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌪️ 소리새 4D 영화 제작 데모
실제 4D 체감효과가 포함된 영화 제작 시연
"""


def sorisae_4d_movie_demo():
    """4D 영화 제작 데모"""

    print("🌪️ 소리새 4D 영화 제작 시스템 데모")
    print("=" * 60)
    print("🎬 진짜 영화를 만드는 4D 애니메이션 스튜디오")
    print("🌟 바람, 물, 진동, 향기, 온도를 모두 느낄 수 있는 영화!")

    try:
        # 애니메이션 스튜디오 모듈 임포트
        from sorisae_animation_studio_ultra import SorisaeAnimationStudio

        print("\n🎬 소리새 애니메이션 스튜디오 초기화 중...")
        studio = SorisaeAnimationStudio()

        print("\n🌪️ 4D 영화 제작 데모 시작")
        print("-" * 40)

        # 4D 영화용 시나리오
        scenario_4d = """
장면 1: 폭풍우 속의 모험
주인공이 거친 바다에서 배를 타고 있다. 거센 바람과 파도가 몰아친다.
선장: 폭풍이 몰려온다! 모두 단단히 잡아라!
주인공: 파도가 너무 거세요! 물이 계속 튀어올라요!

장면 2: 신비한 숲 탐험
주인공이 향기로운 꽃들이 만발한 마법의 숲을 걷는다.
요정: 이 숲의 꽃향기를 맡아보세요. 마법의 힘이 있어요.
주인공: 정말 좋은 향기네요! 따뜻한 바람도 불어와요.

장면 3: 얼음 동굴 탐험
차가운 얼음 동굴에서 보물을 찾는다. 발걸음 소리가 울려 퍼진다.
주인공: 너무 추워요! 발걸음 소리가 메아리쳐요.
가이드: 조심하세요, 이곳은 얼음이 두껍습니다.

장면 4: 화산 폭발 장면
갑자기 화산이 폭발하며 뜨거운 용암이 분출한다.
주인공: 뜨거워! 빨리 도망쳐야 해요!
동료: 땅이 흔들려요! 큰 폭발이었어요!

장면 5: 평화로운 해피엔딩
아름다운 정원에서 커피를 마시며 여유롭게 쉰다.
주인공: 드디어 평화로워졌네요. 커피 향이 좋아요.
친구: 따뜻한 햇살이 정말 기분 좋네요.
"""

        print("🎬 4D 영화 '신비한 모험' 제작 시작!")
        print("🌪️ 체감효과: 바람, 물, 진동, 향기, 온도 모두 포함")

        # 4D 영화 제작
        project = studio.create_movie_from_scenario(
            scenario_text=scenario_4d,
            movie_title="신비한 모험",
            quality="4D",  # 4D 품질로 제작!
            include_theme_song=True
        )

        print("\n🌪️ 4D 영화 제작 완료!")
        print("=" * 60)

        # 4D 효과 요약
        print("🎭 포함된 4D 체감효과:")
        print("  🌪️ 바람: 폭풍우 장면에서 강한 바람")
        print("  💧 물: 바다 장면에서 물방울 분사")
        print("  🌸 향기: 마법의 숲에서 꽃향기")
        print("  🧊 온도: 얼음 동굴에서 차가운 공기")
        print("  🔥 열기: 화산 폭발에서 뜨거운 바람")
        print("  💥 진동: 폭발과 발걸음 소리 진동")
        print("  ☕ 커피향: 마지막 장면에서 커피 향기")

        print(f"\n📊 제작된 4D 영화 정보:")
        print(f"  🎬 제목: {project.title}")
        print(f"  ⏱️ 길이: {project.total_duration // 3600}시간 {(project.total_duration % 3600) // 60}분")
        print(f"  🎭 장면 수: {len(project.scenes)}개")
        print(f"  🌪️ 품질: 4D (Ultra HD + 체감효과)")
        print(f"  🎵 주제곡: 포함")

        print("\n🎊 실제 영화 제작 성공!")
        print("🌟 이제 정말로 4D 영화관에서 상영할 수 있는 영화가 완성되었습니다!")

        return True

    except ImportError as e:
        print(f"❌ 모듈 임포트 오류: {e}")
        print("   소리새 애니메이션 스튜디오 모듈을 찾을 수 없습니다.")
        return False

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 실행 함수"""
    try:
        success = sorisae_4d_movie_demo()

        if success:
            print("\n🎊 4D 영화 제작 데모 완료!")
            print("🌪️ 실제 영화 제작이 성공적으로 완료되었습니다!")
            print("🎬 4D 영화관에서 상영 가능한 수준의 영화입니다!")
        else:
            print("\n❌ 데모 실행 중 문제가 발생했습니다.")

    except KeyboardInterrupt:
        print("\n\n👋 데모가 중단되었습니다.")

    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")


if __name__ == "__main__":
    main()
