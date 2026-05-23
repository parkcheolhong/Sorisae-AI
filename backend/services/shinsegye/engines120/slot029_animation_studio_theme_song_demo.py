#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
소리새 애니메이션 스튜디오 주제곡 기능 데모
주제곡 생성 기능을 테스트하는 데모 프로그램
"""

import time


def animation_studio_theme_song_demo():
    """애니메이션 스튜디오 주제곡 기능 데모"""

    print("🎵 소리새 애니메이션 스튜디오 - 주제곡 기능 데모")
    print("=" * 60)

    try:
        # 애니메이션 스튜디오 모듈 임포트
        from sorisae_animation_studio_ultra import SorisaeAnimationStudio

        print("🎬 애니메이션 스튜디오 초기화 중...")
        studio = SorisaeAnimationStudio()

        print("\n🎵 주제곡 생성 기능 테스트")
        print("-" * 40)

        # 테스트 영화 정보
        test_movies = [
            {
                'title': '겨울 여행',
                'genre': 'pop_ballad',
                'description': '눈 내리는 겨울날의 로맨틱한 여행 이야기'
            },
            {
                'title': '사이버 전사',
                'genre': 'electronic_dance',
                'description': '미래 도시에서 벌어지는 액션 모험'
            },
            {
                'title': '마법의 숲',
                'genre': 'epic_orchestral',
                'description': '환상적인 마법 세계의 모험담'
            }
        ]

        for i, movie in enumerate(test_movies, 1):
            print(f"\n🎬 테스트 {i}: '{movie['title']}' 주제곡 생성")
            print(f"   📖 설명: {movie['description']}")

            # 주제곡 생성
            theme_song = studio.audio_system.generate_theme_song(
                project_title=movie['title'],
                genre=movie['genre'],
                with_vocals=True
            )

            print(f"   🎵 생성된 주제곡:")
            print(f"      제목: {theme_song['title']}")
            print(f"      장르: {theme_song['genre']}")
            print(f"      길이: {theme_song['duration']}초")
            print(f"      키: {theme_song['key']}")
            print(f"      템포: {theme_song['tempo']} BPM")
            print(f"      분위기: {theme_song['mood']}")

            # 변주곡 생성
            print(f"\n   🎼 변주곡 생성 중...")
            variations = studio.audio_system.create_theme_song_variations(theme_song)

            print(f"   ✅ 총 {len(variations) + 1}개 트랙 생성!")
            for variation in variations:
                print(f"      - {variation['title']} ({variation.get('purpose', 'general')})")

            if i < len(test_movies):
                print("\n   ⏳ 다음 테스트로 이동...")
                time.sleep(1)

        print("\n🎵 자동 장르 선택 테스트")
        print("-" * 40)

        # 자동 장르 선택 테스트
        auto_genre_tests = [
            "Love Story Adventure",
            "Future Cyber Action",
            "Magic Fantasy World",
            "War Battle Epic",
            "Simple Life Story"
        ]

        for title in auto_genre_tests:
            print(f"\n🎬 '{title}' - 자동 장르 선택")
            selected_genre = studio.audio_system._select_theme_song_genre(title)
            print(f"   🎵 선택된 장르: {selected_genre}")

            # 간단한 주제곡 정보만 표시
            key = studio.audio_system._select_theme_song_key(selected_genre)
            tempo = studio.audio_system._get_theme_song_tempo(selected_genre)
            mood = studio.audio_system._get_theme_song_mood(selected_genre)

            print(f"   🎼 키: {key}, 템포: {tempo} BPM")
            print(f"   🎭 분위기: {mood}")

        print("\n✅ 주제곡 시스템 테스트 완료!")
        print("🎵 모든 기능이 정상적으로 작동합니다!")

    except ImportError as e:
        print(f"❌ 모듈 임포트 오류: {e}")
        print("   소리새 애니메이션 스튜디오 모듈을 찾을 수 없습니다.")
        return False

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


def main():
    """메인 실행 함수"""
    try:
        success = animation_studio_theme_song_demo()

        if success:
            print("\n🎊 데모 완료!")
            print("주제곡 기능이 성공적으로 애니메이션 스튜디오에 통합되었습니다.")
        else:
            print("\n❌ 데모 실행 중 문제가 발생했습니다.")

    except KeyboardInterrupt:
        print("\n\n👋 데모가 중단되었습니다.")

    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")


if __name__ == "__main__":
    def main(context: dict = None) -> dict:
        """dispatch API용 메인 - 애니메이션 테마곡 생성"""
        context = context or {}
        title = str(context.get('title', '소리새 애니메이션'))
        genre = str(context.get('genre', 'pop_ballad'))

        genre_info = {
            'pop_ballad':        {'tempo': 76,  'key': 'D major',  'mood': '서정적·감동적'},
            'electronic_dance':  {'tempo': 128, 'key': 'A minor',  'mood': '에너지·미래적'},
            'epic_orchestral':   {'tempo': 92,  'key': 'E minor',  'mood': '웅장·서사적'},
            'jazz_fusion':       {'tempo': 110, 'key': 'Bb major', 'mood': '세련·즉흥적'},
            'acoustic_indie':    {'tempo': 85,  'key': 'G major',  'mood': '따뜻·자연적'},
        }
        gd = genre_info.get(genre, genre_info['pop_ballad'])

        return {
            'status': 'ok',
            'theme_song': {
                'title':       f'{title} OST',
                'genre':       genre,
                'tempo_bpm':   gd['tempo'],
                'key':         gd['key'],
                'duration_sec': 180,
                'mood':        gd['mood'],
                'instruments': ['피아노', '현악기', '기타', '타악기'],
                'variations':  ['오프닝', '엔딩', '배경음악'],
            },
        }
