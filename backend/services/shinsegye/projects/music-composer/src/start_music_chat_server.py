#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🎵 소리새 음악 채팅 통합 서버 실행기
완성된 작사, 작곡 프로그램에 사용자들 채팅장이 통합된 웹 서버
"""

from modules.sorisae_dashboard_web import app, music_chat_system, socketio


def start_server():
    """통합된 음악 채팅 서버 시작"""
    print("🎵 소리새 음악 채팅 통합 대시보드 시작!")
    print("=" * 50)
    print("📊 메인 대시보드: http://localhost:5050")
    print("🎵 음악 채팅방: http://localhost:5050/music-chat")
    print("💬 채팅방 API: http://localhost:5050/api/music-chat/rooms")
    print("=" * 50)

    # 음악 채팅 시스템 상태 확인
    if music_chat_system:
        print("✅ 음악 채팅 시스템: 활성화")
    else:
        print("⚠️ 음악 채팅 시스템: 비활성화")

    print("🔥 서버가 시작되었습니다. 브라우저에서 접속하세요!")
    print("종료하려면 Ctrl+C를 누르세요.")
    print()

    try:
        socketio.run(app, host="0.0.0.0", port=5050, debug=False)
    except KeyboardInterrupt:
        print("\n🛑 서버를 종료합니다.")
    except Exception as e:
        print(f"❌ 서버 오류: {e}")


if __name__ == "__main__":
    start_server()
