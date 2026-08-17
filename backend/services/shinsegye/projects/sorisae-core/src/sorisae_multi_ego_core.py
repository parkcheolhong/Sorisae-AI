#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
소리새 코어에 다중 자아 엔진 통합
Sorisae Core integration with Multi-Ego Engine
"""

import os
import sys

from multi_ego_engine import MultiEgoEngine

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


class SorisaeMultiEgoCore:
    """소리새 다중 자아 통합 코어"""

    def __init__(self):
        self.multi_ego_engine = MultiEgoEngine()
        self.current_active_ego = None
        self.conversation_mode = "single"  # single, multi, discussion
        print("🧠 소리새 다중 자아 코어 시스템 초기화 완료")

    def process_ego_command(self, command: str) -> str:
        """다중 자아 명령 처리"""
        command = command.lower().strip()

        # 자아 전환 명령
        if command.startswith("자아 전환") or command.startswith("switch ego"):
            return self._handle_ego_switch(command)

        # 자아 토론 명령
        elif command.startswith("자아 토론") or command.startswith("ego discussion"):
            return self._handle_ego_discussion(command)

        # 자아 협업 명령
        elif command.startswith("자아 협업") or command.startswith("ego collaboration"):
            return self._handle_ego_collaboration(command)

        # 자아 상태 확인
        elif command.startswith("자아 상태") or command.startswith("ego status"):
            return self._handle_ego_status()

        # 자아 기분 변경
        elif command.startswith("자아 기분") or command.startswith("ego mood"):
            return self._handle_ego_mood_change(command)

        # 다중 모드 전환
        elif command.startswith("다중 모드") or command.startswith("multi mode"):
            return self._handle_mode_switch(command)

        # 기본 자아 응답 (현재 활성 자아가 있는 경우)
        elif self.current_active_ego:
            return self.multi_ego_engine.get_ego_response(
                self.current_active_ego,
                command,
                f"모드: {self.conversation_mode}"
            )

        else:
            return self._get_default_multi_ego_response(command)

    def _handle_ego_switch(self, command: str) -> str:
        """자아 전환 처리"""
        # 명령에서 자아 이름 추출
        ego_names = list(self.multi_ego_engine.egos.keys())

        for ego_name in ego_names:
            if ego_name.lower() in command or ego_name in command:
                self.current_active_ego = ego_name
                ego = self.multi_ego_engine.egos[ego_name]
                return f"{ego.emoji} **{ego.name}**로 전환되었습니다! 안녕하세요, 저는 {ego.expertise}를 전문으로 하는 {ego.name}입니다."

        # 자아 목록 제공
        ego_list = "\n".join([f"  {ego.emoji} {name} ({ego.ego_type.value})"
                             for name, ego in self.multi_ego_engine.egos.items()])
        return f"🧠 사용 가능한 자아들:\n{ego_list}\n\n예: '자아 전환 크리에이터'"

    def _handle_ego_discussion(self, command: str) -> str:
        """자아 토론 처리"""
        # 토론 주제 추출
        if ":" in command:
            topic = command.split(":", 1)[1].strip()
        elif "토론" in command:
            parts = command.split("토론", 1)
            if len(parts) > 1:
                topic = parts[1].strip()
            else:
                topic = "일반적인 주제"
        else:
            topic = "사용자 요청 사항"

        if not topic or len(topic) < 2:
            topic = "소리새 시스템 개선"

        # 토론 시작
        self.conversation_mode = "discussion"
        discussion = self.multi_ego_engine.multi_ego_discussion(topic, 4)

        result = f"🧠 다중 자아 토론 완료: '{topic}'\n"
        result += f"👥 참여자: {', '.join(discussion['participants'])}\n"
        result += f"🎯 합의점: {len(discussion['consensus_points'])}개\n"

        if discussion['consensus_points']:
            result += "주요 합의점:\n"
            for point in discussion['consensus_points'][:3]:
                result += f"  • {point}\n"

        return result

    def _handle_ego_collaboration(self, command: str) -> str:
        """자아 협업 처리"""
        # 작업과 필요 전문성 추출
        if ":" in command:
            task_info = command.split(":", 1)[1].strip()
        else:
            task_info = "일반적인 협업 작업"

        # 기본 전문성 요구사항
        required_expertise = ["창작", "분석", "기술", "소통"]

        # 명령에서 전문성 키워드 추출
        expertise_keywords = {
            "음악": ["음악", "예술", "창작"],
            "기술": ["기술 개발", "프로그래밍", "시스템"],
            "분석": ["데이터 분석", "연구", "통계"],
            "소통": ["커뮤니케이션", "팀워크", "협상"],
            "창의": ["창작", "예술", "아이디어 발상"]
        }

        for keyword, skills in expertise_keywords.items():
            if keyword in task_info:
                required_expertise = skills
                break

        collaboration = self.multi_ego_engine.get_ego_collaboration(task_info, required_expertise)

        result = f"🤝 자아 협업 팀 구성 완료\n"
        result += f"📋 작업: {collaboration['task']}\n"
        result += f"👥 참여 자아: {', '.join(collaboration['selected_egos'])}\n"
        result += f"🎯 협업 전략: {collaboration['collaboration_strategy']}\n\n"

        result += "역할 분담:\n"
        for ego_name, role_info in collaboration['ego_roles'].items():
            result += f"  • {ego_name}: {role_info['contribution']}\n"

        self.conversation_mode = "multi"
        return result

    def _handle_ego_status(self) -> str:
        """자아 상태 확인"""
        active_egos = self.multi_ego_engine.get_active_egos()

        result = f"🧠 소리새 다중 자아 시스템 현황\n"
        result += f"=" * 40 + "\n"
        result += f"현재 모드: {self.conversation_mode}\n"
        result += f"활성 자아: {self.current_active_ego or '없음'}\n"
        result += f"총 자아 수: {len(active_egos)}개\n\n"

        result += "자아별 현황:\n"
        for ego in active_egos:
            status_icon = "🟢" if ego['recent_activity'] > 0 else "⚪"
            result += f"  {status_icon} {ego['emoji']} {ego['name']} ({ego['type']})\n"
            result += f"     기분: {ego['mood']}, 에너지: {ego['energy']:.1f}, 활동: {ego['recent_activity']}회\n"

        return result

    def _handle_ego_mood_change(self, command: str) -> str:
        """자아 기분 변경"""
        # 자아 이름과 기분 추출
        parts = command.split()
        if len(parts) < 3:
            return "사용법: 자아 기분 [자아이름] [기분] 예: '자아 기분 크리에이터 신남'"

        ego_name = parts[2]
        mood = parts[3] if len(parts) > 3 else "좋음"

        # 자아 이름 매칭
        matched_ego = None
        for name in self.multi_ego_engine.egos.keys():
            if ego_name in name or name in ego_name:
                matched_ego = name
                break

        if matched_ego:
            success = self.multi_ego_engine.ego_personality_shift(matched_ego, mood)
            if success:
                ego = self.multi_ego_engine.egos[matched_ego]
                return f"{ego.emoji} {matched_ego}의 기분이 '{mood}'로 변경되었습니다!"

        ego_list = ", ".join(self.multi_ego_engine.egos.keys())
        return f"자아를 찾을 수 없습니다. 사용 가능한 자아: {ego_list}"

    def _handle_mode_switch(self, command: str) -> str:
        """모드 전환 처리"""
        if "단일" in command or "single" in command:
            self.conversation_mode = "single"
            return "🔄 단일 자아 모드로 전환되었습니다."
        elif "다중" in command or "multi" in command:
            self.conversation_mode = "multi"
            return "🔄 다중 자아 모드로 전환되었습니다."
        elif "토론" in command or "discussion" in command:
            self.conversation_mode = "discussion"
            return "🔄 토론 모드로 전환되었습니다."
        else:
            return f"현재 모드: {self.conversation_mode}\n사용 가능한 모드: single(단일), multi(다중), discussion(토론)"

    def _get_default_multi_ego_response(self, command: str) -> str:
        """기본 다중 자아 응답"""
        # 주제에 따라 적절한 자아들 선택
        if any(keyword in command.lower() for keyword in ["음악", "예술", "창작"]):
            selected_egos = ["크리에이터", "아티스트"]
        elif any(keyword in command.lower() for keyword in ["분석", "데이터", "논리"]):
            selected_egos = ["로직", "애널리스트"]
        elif any(keyword in command.lower() for keyword in ["감정", "기분", "마음"]):
            selected_egos = ["하트", "소셜"]
        elif any(keyword in command.lower() for keyword in ["기술", "프로그래밍", "시스템"]):
            selected_egos = ["테키", "로직"]
        else:
            selected_egos = ["크리에이터", "로직", "하트"]

        responses = []
        for ego_name in selected_egos:
            if ego_name in self.multi_ego_engine.egos:
                response = self.multi_ego_engine.get_ego_response(ego_name, command)
                responses.append(response)

        if responses:
            return "\n".join(responses)
        else:
            return "🧠 다중 자아 시스템에서 적절한 응답을 찾을 수 없습니다."


# 전역 다중 자아 코어 인스턴스
sorisae_multi_ego_core = SorisaeMultiEgoCore()


def test_sorisae_multi_ego_integration():
    """소리새 다중 자아 통합 테스트"""
    print("🧠 소리새 다중 자아 통합 시스템 테스트")
    print("=" * 50)

    core = SorisaeMultiEgoCore()

    # 테스트 명령들
    test_commands = [
        "자아 상태",
        "자아 전환 크리에이터",
        "음악 작곡에 대해 어떻게 생각해?",
        "자아 토론: AI의 미래",
        "자아 협업: 음성 인식 시스템 개선",
        "자아 기분 하트 행복함",
        "다중 모드 토론",
        "기술적인 문제 해결이 필요해"
    ]

    for i, command in enumerate(test_commands, 1):
        print(f"\n🎯 테스트 {i}: '{command}'")
        print("-" * 30)
        response = core.process_ego_command(command)
        print(response)

    print(f"\n🎉 통합 테스트 완료!")
    return True


if __name__ == "__main__":
    test_sorisae_multi_ego_integration()
