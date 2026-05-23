#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
음성 명령 처리기
소리새 시스템의 음성 명령을 인식하고 처리하는 핵심 모듈입니다.
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Tuple


@dataclass
class VoiceCommand:
    """음성 명령 데이터 클래스"""
    command: str
    intent: str
    entities: Dict[str, Any]
    confidence: float
    timestamp: str


class VoiceCommandProcessor:
    def __init__(self):
        # 명령 패턴 정의
        self.command_patterns = {
            'create_file': [
                r'파일을?\s*(?:만들어|생성해|만들어줘)\s*(.+)',
                r'(.+)\s*파일을?\s*(?:만들어|생성해)',
                r'create\s*(?:a\s*)?file\s*(.+)',
                r'new\s*file\s*(.+)'
            ],
            'open_file': [
                r'(.+)\s*파일을?\s*(?:열어|열어줘|오픈해)',
                r'open\s*(?:the\s*)?file\s*(.+)',
                r'파일\s*(.+)\s*열어'
            ],
            'run_code': [
                r'(?:코드를?\s*)?(?:실행해|런해|돌려|실행)',
                r'run\s*(?:the\s*)?(?:code|program)',
                r'execute\s*(?:the\s*)?(?:code|program)'
            ],
            'search': [
                r'(.+)\s*(?:검색해|찾아|서치해)',
                r'search\s*(?:for\s*)?(.+)',
                r'find\s*(.+)'
            ],
            'help': [
                r'(?:도움말|헬프|help)',
                r'어떻게\s*(?:사용|써)',
                r'사용법'
            ],
            'music_play': [
                r'음악\s*(?:틀어|재생해|들려줘)',
                r'play\s*music',
                r'음악\s*시작'
            ],
            'music_stop': [
                r'음악\s*(?:정지|멈춰|스톱)',
                r'stop\s*music',
                r'음악\s*그만'
            ],
            'weather': [
                r'날씨\s*(?:어때|알려줘)',
                r'weather\s*(?:today|now)',
                r'오늘\s*날씨'
            ],
            'time': [
                r'(?:시간|time)\s*(?:알려줘|what)',
                r'지금\s*몇시',
                r'현재\s*시간'
            ]
        }

        # 엔티티 추출 패턴
        self.entity_patterns = {
            'filename': r'([a-zA-Z0-9_가-힣]+\.(?:py|txt|json|md|html|css|js))',
            'number': r'(\d+)',
            'time': r'(\d{1,2}:\d{2})',
            'date': r'(\d{4}-\d{2}-\d{2})',
            'emotion': r'(기쁘|슬프|화나|즐거|우울|행복|신나)',
            'genre': r'(발라드|팝|재즈|클래식|록|힙합|댄스)'
        }

        # 컨텍스트 관리
        self.conversation_context = []
        self.last_command = None

        # 명령 핸들러 등록
        self.command_handlers = {
            'create_file': self._handle_create_file,
            'open_file': self._handle_open_file,
            'run_code': self._handle_run_code,
            'search': self._handle_search,
            'help': self._handle_help,
            'music_play': self._handle_music_play,
            'music_stop': self._handle_music_stop,
            'weather': self._handle_weather,
            'time': self._handle_time
        }

    def process_voice_input(self, voice_text: str) -> Dict[str, Any]:
        """음성 입력을 처리하여 명령으로 변환"""
        print(f"🎤 음성 입력 처리: '{voice_text}'")

        # 텍스트 정규화
        normalized_text = self._normalize_text(voice_text)

        # 명령 의도 분류
        intent, confidence = self._classify_intent(normalized_text)

        # 엔티티 추출
        entities = self._extract_entities(normalized_text)

        # 명령 객체 생성
        command = VoiceCommand(
            command=normalized_text,
            intent=intent,
            entities=entities,
            confidence=confidence,
            timestamp=datetime.now().isoformat()
        )

        # 컨텍스트에 추가
        self.conversation_context.append(command)
        self.last_command = command

        # 명령 실행
        result = self._execute_command(command)

        return {
            'command': command,
            'result': result,
            'success': result.get('success', False)
        }

    def _normalize_text(self, text: str) -> str:
        """텍스트 정규화"""
        # 소문자 변환 및 공백 정리
        normalized = text.lower().strip()

        # 연속된 공백 제거
        normalized = re.sub(r'\s+', ' ', normalized)

        # 구두점 정리
        normalized = re.sub(r'[^\w\s가-힣.:/-]', '', normalized)

        return normalized

    def _classify_intent(self, text: str) -> Tuple[str, float]:
        """명령 의도 분류"""
        best_intent = 'unknown'
        best_confidence = 0.0

        for intent, patterns in self.command_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    # 패턴 매칭 품질 기반 신뢰도 계산
                    confidence = len(match.group(0)) / len(text)
                    if confidence > best_confidence:
                        best_intent = intent
                        best_confidence = confidence

        return best_intent, min(best_confidence * 1.2, 1.0)  # 최대 1.0으로 제한

    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """텍스트에서 엔티티 추출"""
        entities = {}

        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                entities[entity_type] = matches

        return entities

    def _execute_command(self, command: VoiceCommand) -> Dict[str, Any]:
        """명령 실행"""
        handler = self.command_handlers.get(command.intent)

        if handler:
            try:
                return handler(command)
            except Exception as e:
                return {
                    'success': False,
                    'error': f'명령 실행 중 오류: {str(e)}',
                    'intent': command.intent
                }
        else:
            return {
                'success': False,
                'error': f'알 수 없는 명령: {command.intent}',
                'suggestion': '도움말을 요청해보세요'
            }

    def _handle_create_file(self, command: VoiceCommand) -> Dict[str, Any]:
        """파일 생성 명령 처리"""
        filename = None

        # 엔티티에서 파일명 찾기
        if 'filename' in command.entities:
            filename = command.entities['filename'][0]
        else:
            # 명령에서 파일명 추출 시도
            for pattern in self.command_patterns['create_file']:
                match = re.search(pattern, command.command)
                if match:
                    filename = match.group(1).strip()
                    break

        if filename:
            return {
                'success': True,
                'action': 'create_file',
                'filename': filename,
                'message': f'파일 "{filename}" 생성을 요청했습니다.'
            }
        else:
            return {
                'success': False,
                'error': '파일명을 찾을 수 없습니다.',
                'suggestion': '"example.py 파일 만들어줘"와 같이 말해보세요.'
            }

    def _handle_open_file(self, command: VoiceCommand) -> Dict[str, Any]:
        """파일 열기 명령 처리"""
        filename = None

        if 'filename' in command.entities:
            filename = command.entities['filename'][0]
        else:
            for pattern in self.command_patterns['open_file']:
                match = re.search(pattern, command.command)
                if match:
                    filename = match.group(1).strip()
                    break

        if filename:
            return {
                'success': True,
                'action': 'open_file',
                'filename': filename,
                'message': f'파일 "{filename}" 열기를 요청했습니다.'
            }
        else:
            return {
                'success': False,
                'error': '파일명을 찾을 수 없습니다.'
            }

    def _handle_run_code(self, command: VoiceCommand) -> Dict[str, Any]:
        """코드 실행 명령 처리"""
        return {
            'success': True,
            'action': 'run_code',
            'message': '코드 실행을 요청했습니다.'
        }

    def _handle_search(self, command: VoiceCommand) -> Dict[str, Any]:
        """검색 명령 처리"""
        query = None

        for pattern in self.command_patterns['search']:
            match = re.search(pattern, command.command)
            if match:
                query = match.group(1).strip()
                break

        return {
            'success': True,
            'action': 'search',
            'query': query or '검색어 없음',
            'message': f'검색 요청: "{query}"'
        }

    def _handle_help(self, command: VoiceCommand) -> Dict[str, Any]:
        """도움말 명령 처리"""
        help_text = """
🤖 소리새 음성 명령 도움말

📁 파일 관리:
- "example.py 파일 만들어줘"
- "config.json 파일 열어"

🔧 코드 실행:
- "코드 실행해"
- "프로그램 돌려"

🔍 검색:
- "Python 함수 검색해"
- "날씨 정보 찾아"

🎵 음악:
- "음악 틀어"
- "음악 정지"

🌤️ 정보:
- "날씨 어때?"
- "지금 몇시?"
        """

        return {
            'success': True,
            'action': 'help',
            'message': help_text.strip()
        }

    def _handle_music_play(self, command: VoiceCommand) -> Dict[str, Any]:
        """음악 재생 명령 처리"""
        genre = None
        if 'genre' in command.entities:
            genre = command.entities['genre'][0]

        return {
            'success': True,
            'action': 'music_play',
            'genre': genre,
            'message': f'음악 재생 요청{f" (장르: {genre})" if genre else ""}'
        }

    def _handle_music_stop(self, command: VoiceCommand) -> Dict[str, Any]:
        """음악 정지 명령 처리"""
        return {
            'success': True,
            'action': 'music_stop',
            'message': '음악 정지 요청'
        }

    def _handle_weather(self, command: VoiceCommand) -> Dict[str, Any]:
        """날씨 정보 명령 처리"""
        return {
            'success': True,
            'action': 'weather',
            'message': '날씨 정보 요청'
        }

    def _handle_time(self, command: VoiceCommand) -> Dict[str, Any]:
        """시간 정보 명령 처리"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return {
            'success': True,
            'action': 'time',
            'current_time': current_time,
            'message': f'현재 시간: {current_time}'
        }

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """대화 히스토리 반환"""
        return [
            {
                'command': cmd.command,
                'intent': cmd.intent,
                'confidence': cmd.confidence,
                'timestamp': cmd.timestamp
            }
            for cmd in self.conversation_context[-10:]  # 최근 10개
        ]

    def clear_context(self) -> None:
        """대화 컨텍스트 초기화"""
        self.conversation_context.clear()
        self.last_command = None


def main():
    """메인 실행 함수"""
    print("🎤 소리새 음성 명령 처리기")
    print("========================")

    processor = VoiceCommandProcessor()

    # 테스트 음성 명령들
    test_commands = [
        "example.py 파일 만들어줘",
        "config.json 파일 열어",
        "코드 실행해",
        "Python 함수 검색해",
        "음악 틀어",
        "발라드 음악 재생해",
        "날씨 어때?",
        "지금 몇시?",
        "도움말"
    ]

    print("📝 테스트 음성 명령 처리:")
    print("-" * 30)

    results = []
    for cmd_text in test_commands:
        result = processor.process_voice_input(cmd_text)
        results.append(result)

        print(f"\n입력: '{cmd_text}'")
        print(f"의도: {result['command'].intent} (신뢰도: {result['command'].confidence:.2f})")
        print(f"결과: {result['result']['message']}")

    # 결과를 JSON 파일로 저장
    with open('voice_command_test_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            'test_results': results,
            'conversation_history': processor.get_conversation_history()
        }, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n💾 테스트 결과가 'voice_command_test_results.json'에 저장되었습니다.")


if __name__ == "__main__":
    main()
