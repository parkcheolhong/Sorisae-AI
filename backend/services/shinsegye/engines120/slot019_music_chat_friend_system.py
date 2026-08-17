#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🎵👥 소리새 음악 채팅 친구 시스템
음악 채팅에서 친구 추가, 신호 연결, 실시간 알림 기능
"""

import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class FriendRequest:
    """친구 요청 정보"""
    request_id: str
    sender_id: str
    receiver_id: str
    message: str = ""
    status: str = "pending"  # pending, accepted, rejected
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')


@dataclass
class FriendConnection:
    """친구 연결 정보"""
    connection_id: str
    user1_id: str
    user2_id: str
    connection_type: str = "friend"  # friend, close_friend, music_partner
    shared_rooms: List[str] = None
    signal_status: str = "offline"  # online, offline, busy, in_music_session
    last_interaction: str = ""

    def __post_init__(self):
        if self.shared_rooms is None:
            self.shared_rooms = []
        if not self.last_interaction:
            self.last_interaction = datetime.now().strftime('%Y-%m-%d %H:%M:%S')


@dataclass
class UserSignal:
    """사용자 신호 정보"""
    user_id: str
    signal_type: str  # music_invitation, collaboration_request, chat_ping, status_update
    target_user_id: str
    content: str
    data: Dict[str, Any] = None
    timestamp: str = ""

    def __post_init__(self):
        if self.data is None:
            self.data = {}
        if not self.timestamp:
            self.timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')


class MusicChatFriendSystem:
    """음악 채팅 친구 관리 시스템"""

    def __init__(self):
        """친구 시스템 초기화"""
        self.friend_requests: Dict[str, FriendRequest] = {}
        self.friend_connections: Dict[str, FriendConnection] = {}
        self.user_signals: Dict[str, List[UserSignal]] = {}  # user_id -> signals
        self.user_friends: Dict[str, List[str]] = {}  # user_id -> friend_user_ids
        self.online_users: Dict[str, str] = {}  # user_id -> status
        self.lock = threading.RLock()

        print("🤝 음악 채팅 친구 시스템 초기화 완료")

    def send_friend_request(self, sender_id: str, receiver_id: str, message: str = "") -> str:
        """친구 요청 보내기"""
        if sender_id == receiver_id:
            return ""

        # 이미 친구인지 확인
        if self.are_friends(sender_id, receiver_id):
            return ""

        request_id = str(uuid.uuid4())[:8]

        friend_request = FriendRequest(
            request_id=request_id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            message=message
        )

        with self.lock:
            self.friend_requests[request_id] = friend_request

            # 수신자에게 알림 신호 전송
            self.send_signal(
                sender_id,
                receiver_id,
                "friend_request",
                f"친구 요청이 도착했습니다: {message}",
                {"request_id": request_id}
            )

        print(f"👋 친구 요청 전송: {sender_id} → {receiver_id}")
        return request_id

    def respond_to_friend_request(self, request_id: str, response: str) -> bool:
        """친구 요청에 응답 (accept/reject)"""
        if request_id not in self.friend_requests:
            return False

        request = self.friend_requests[request_id]

        with self.lock:
            request.status = "accepted" if response == "accept" else "rejected"

            if response == "accept":
                # 친구 연결 생성
                connection_id = str(uuid.uuid4())[:8]

                connection = FriendConnection(
                    connection_id=connection_id,
                    user1_id=request.sender_id,
                    user2_id=request.receiver_id
                )

                self.friend_connections[connection_id] = connection

                # 양방향 친구 목록 업데이트
                if request.sender_id not in self.user_friends:
                    self.user_friends[request.sender_id] = []
                if request.receiver_id not in self.user_friends:
                    self.user_friends[request.receiver_id] = []

                self.user_friends[request.sender_id].append(request.receiver_id)
                self.user_friends[request.receiver_id].append(request.sender_id)

                # 승인 알림
                self.send_signal(
                    request.receiver_id,
                    request.sender_id,
                    "friend_accepted",
                    "친구 요청이 승인되었습니다! 🎉",
                    {"connection_id": connection_id}
                )

                print(f"🤝 친구 연결 생성: {request.sender_id} ↔ {request.receiver_id}")
            else:
                # 거절 알림
                self.send_signal(
                    request.receiver_id,
                    request.sender_id,
                    "friend_rejected",
                    "친구 요청이 거절되었습니다.",
                    {}
                )

        return True

    def send_signal(self, sender_id: str, target_id: str, signal_type: str,
                    content: str, data: Dict[str, Any] = None) -> str:
        """신호 전송"""
        signal = UserSignal(
            user_id=sender_id,
            signal_type=signal_type,
            target_user_id=target_id,
            content=content,
            data=data or {}
        )

        with self.lock:
            if target_id not in self.user_signals:
                self.user_signals[target_id] = []

            self.user_signals[target_id].append(signal)

        print(f"📡 신호 전송: {sender_id} → {target_id} ({signal_type})")
        return signal.user_id + signal.timestamp

    def get_user_signals(self, user_id: str, clear: bool = True) -> List[Dict[str, Any]]:
        """사용자가 받은 신호들 조회"""
        if user_id not in self.user_signals:
            return []

        with self.lock:
            signals = [asdict(signal) for signal in self.user_signals[user_id]]

            if clear:
                self.user_signals[user_id] = []

        return signals

    def are_friends(self, user1_id: str, user2_id: str) -> bool:
        """두 사용자가 친구인지 확인"""
        return (user1_id in self.user_friends
                and user2_id in self.user_friends[user1_id])

    def get_user_friends(self, user_id: str) -> List[str]:
        """사용자의 친구 목록 조회"""
        return self.user_friends.get(user_id, [])

    def update_user_status(self, user_id: str, status: str) -> None:
        """사용자 상태 업데이트"""
        with self.lock:
            self.online_users[user_id] = status

            # 친구들에게 상태 변경 알림
            friends = self.get_user_friends(user_id)
            for friend_id in friends:
                self.send_signal(
                    user_id,
                    friend_id,
                    "status_update",
                    f"상태가 {status}로 변경되었습니다.",
                    {"new_status": status}
                )

    def invite_friend_to_music_session(self, sender_id: str, friend_id: str,
                                       session_data: Dict[str, Any]) -> bool:
        """친구를 음악 세션에 초대"""
        if not self.are_friends(sender_id, friend_id):
            return False

        self.send_signal(
            sender_id,
            friend_id,
            "music_invitation",
            f"음악 세션에 초대하셨습니다: {session_data.get('title', '무제')}",
            session_data
        )

        return True

    def start_collaboration(self, initiator_id: str, friend_id: str,
                            collab_type: str, title: str) -> str:
        """친구와 협업 시작"""
        if not self.are_friends(initiator_id, friend_id):
            return ""

        collab_id = str(uuid.uuid4())[:8]

        collab_data = {
            "collaboration_id": collab_id,
            "type": collab_type,
            "title": title,
            "participants": [initiator_id, friend_id]
        }

        self.send_signal(
            initiator_id,
            friend_id,
            "collaboration_request",
            f"{collab_type} 협업을 시작하고 싶어합니다: {title}",
            collab_data
        )

        return collab_id

    def get_friend_status(self, user_id: str, friend_id: str) -> str:
        """친구의 현재 상태 조회"""
        if not self.are_friends(user_id, friend_id):
            return "not_friend"

        return self.online_users.get(friend_id, "offline")

    def get_mutual_rooms(self, user1_id: str, user2_id: str) -> List[str]:
        """두 사용자가 공통으로 있는 방 목록"""
        # 친구 연결에서 공유 방 정보 찾기
        for connection in self.friend_connections.values():
            if ((connection.user1_id == user1_id and connection.user2_id == user2_id)
                    or (connection.user1_id == user2_id and connection.user2_id == user1_id)):
                return connection.shared_rooms

        return []

    def add_shared_room(self, user1_id: str, user2_id: str, room_id: str) -> bool:
        """친구들이 공유하는 방 추가"""
        for connection in self.friend_connections.values():
            if ((connection.user1_id == user1_id and connection.user2_id == user2_id)
                    or (connection.user1_id == user2_id and connection.user2_id == user1_id)):
                if room_id not in connection.shared_rooms:
                    connection.shared_rooms.append(room_id)
                return True

        return False

    def get_friend_requests(self, user_id: str) -> List[Dict[str, Any]]:
        """사용자가 받은 친구 요청 목록"""
        requests = []

        for request in self.friend_requests.values():
            if request.receiver_id == user_id and request.status == "pending":
                requests.append(asdict(request))

        return requests

    def remove_friend(self, user_id: str, friend_id: str) -> bool:
        """친구 제거"""
        if not self.are_friends(user_id, friend_id):
            return False

        with self.lock:
            # 친구 목록에서 제거
            if user_id in self.user_friends:
                self.user_friends[user_id].remove(friend_id)
            if friend_id in self.user_friends:
                self.user_friends[friend_id].remove(user_id)

            # 친구 연결 제거
            to_remove = []
            for conn_id, connection in self.friend_connections.items():
                if ((connection.user1_id == user_id and connection.user2_id == friend_id)
                        or (connection.user1_id == friend_id and connection.user2_id == user_id)):
                    to_remove.append(conn_id)

            for conn_id in to_remove:
                del self.friend_connections[conn_id]

        print(f"💔 친구 연결 해제: {user_id} ↔ {friend_id}")
        return True


# 전역 친구 시스템 인스턴스
music_friend_system = MusicChatFriendSystem()


def get_friend_system():
    """친구 시스템 인스턴스 반환"""
    return music_friend_system


def demo_friend_system():
    """친구 시스템 데모"""
    print("🤝 음악 채팅 친구 시스템 데모")
    print("=" * 50)

    system = get_friend_system()

    # 1. 친구 요청 보내기
    print("\n1. 친구 요청 테스트:")
    request_id = system.send_friend_request(
        "user1", "user2",
        "안녕하세요! 함께 음악을 만들어요! 🎵"
    )
    print(f"   요청 ID: {request_id}")

    # 2. 친구 요청 승인
    print("\n2. 친구 요청 승인:")
    result = system.respond_to_friend_request(request_id, "accept")
    print(f"   승인 결과: {result}")

    # 3. 친구 상태 확인
    print("\n3. 친구 관계 확인:")
    are_friends = system.are_friends("user1", "user2")
    print(f"   친구 관계: {are_friends}")

    # 4. 신호 전송 테스트
    print("\n4. 신호 전송 테스트:")
    system.send_signal(
        "user1", "user2", "chat_ping",
        "안녕! 지금 뭐하고 있어? 🎤"
    )

    # 5. 신호 수신 확인
    print("\n5. 신호 수신 확인:")
    signals = system.get_user_signals("user2")
    for signal in signals:
        print(f"   📨 {signal['signal_type']}: {signal['content']}")

    # 6. 음악 세션 초대
    print("\n6. 음악 세션 초대:")
    session = {
        "title": "함께 만드는 발라드",
        "type": "collaboration",
        "genre": "ballad"
    }
    system.invite_friend_to_music_session("user1", "user2", session)

    # 7. 협업 시작
    print("\n7. 협업 시작:")
    collab_id = system.start_collaboration(
        "user1", "user2", "작곡", "우리들의 이야기"
    )
    print(f"   협업 ID: {collab_id}")

    print("\n✅ 친구 시스템 데모 완료!")
    print("🎵 이제 친구들과 함께 음악을 만들 수 있습니다!")



def main(context: dict = None) -> dict:
    """dispatch API용 메인 - 음악 채팅 친구 시스템"""
    context = context or {}
    user_id = str(context.get('user_id', 'user001'))
    target_id = str(context.get('target_id', 'user002'))
    try:
        system = get_friend_system()
        request = system.send_friend_request(user_id, target_id)
        friends = list(system.friend_connections.get(user_id, {}).keys())
        return {
            'status': 'ok',
            'user_id': user_id,
            'friend_request_sent': target_id,
            'request_id': request.request_id if hasattr(request, 'request_id') else str(request),
            'current_friends': friends[:5],
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

if __name__ == "__main__":
    demo_friend_system()
