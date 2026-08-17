from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    addon_src = Path(__file__).resolve().parent / "src"
    sys.path.insert(0, str(addon_src))

    from ai_music_composer import AIMusicLyricsStudio
    from emotion_based_music_generator import EmotionBasedMusicGenerator
    from music_chat_friend_system import get_friend_system

    generator = EmotionBasedMusicGenerator()
    composition = generator.create_musical_composition("happy", 0.8)
    print("MUSIC_ROUND1_TITLE", composition["title"])
    print("MUSIC_ROUND1_TEMPO", composition["musical_elements"]["tempo"])

    studio = AIMusicLyricsStudio()
    song = studio.create_complete_song(emotion="romantic", theme="소리새 테마")
    print("MUSIC_ROUND2_SONG", song["title"])
    print("MUSIC_ROUND2_LYRICS", song["lyrics"]["title"])

    friend_system = get_friend_system()
    request_id = friend_system.send_friend_request("user_a", "user_b", "함께 음악 만들기")
    friend_system.respond_to_friend_request(request_id, "accept")
    collaboration_id = friend_system.start_collaboration("user_a", "user_b", "작곡", "우정의 노래")
    print("MUSIC_ROUND3_REQUEST", request_id)
    print("MUSIC_ROUND3_COLLAB", collaboration_id)


if __name__ == "__main__":
    main()