#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌐 나도 통역사 - 소리새 실시간 통역 시스템
(I am also an Interpreter - Sorisae Real-time Interpretation System)

수아미코리아 x 신세계 소리새프로젝트 통합
실시간 음성-음성 통역 및 텍스트 번역 기능 제공
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# 로깅 설정
logger = logging.getLogger(__name__)


class InterpreterCore:
    """통역 핵심 엔진"""

    def __init__(self):
        """통역 엔진 초기화"""
        self.supported_languages = {
            "ko": "한국어 (Korean)",
            "en": "영어 (English)",
            "ja": "일본어 (Japanese)",
            "zh": "중국어 (Chinese)",
            "es": "스페인어 (Spanish)",
            "fr": "프랑스어 (French)",
            "de": "독일어 (German)",
            "ru": "러시아어 (Russian)",
            "ar": "아랍어 (Arabic)",
            "vi": "베트남어 (Vietnamese)",
            "th": "태국어 (Thai)",
            "id": "인도네시아어 (Indonesian)",
            "sorisae": "소리새어 (Sorisae Language)"
        }

        # 통역 패턴 데이터베이스
        self.translation_db = self._initialize_translation_db()

        # 통역 히스토리
        self.history = []

        # 통계
        self.stats = {
            "total_translations": 0,
            "by_language": {},
            "session_start": datetime.now()
        }

        logger.info("통역 엔진 초기화 완료")

    def _initialize_translation_db(self) -> Dict:
        """기본 번역 패턴 데이터베이스 초기화"""
        return {
            # 인사말
            "greetings": {
                "안녕하세요": {
                    "en": "Hello",
                    "ja": "こんにちは",
                    "zh": "你好",
                    "es": "Hola",
                    "fr": "Bonjour",
                    "de": "Hallo",
                    "ru": "Здравствуйте",
                    "ar": "مرحبا",
                    "vi": "Xin chào",
                    "th": "สวัสดี",
                    "id": "Halo",
                    "sorisae": "Sora-hel"
                },
                "감사합니다": {
                    "en": "Thank you",
                    "ja": "ありがとうございます",
                    "zh": "谢谢",
                    "es": "Gracias",
                    "fr": "Merci",
                    "de": "Danke",
                    "ru": "Спасибо",
                    "ar": "شكرا",
                    "vi": "Cảm ơn",
                    "th": "ขอบคุณ",
                    "id": "Terima kasih",
                    "sorisae": "Sora-gam"
                },
                "안녕히 가세요": {
                    "en": "Goodbye",
                    "ja": "さようなら",
                    "zh": "再见",
                    "es": "Adiós",
                    "fr": "Au revoir",
                    "de": "Auf Wiedersehen",
                    "ru": "До свидания",
                    "ar": "وداعا",
                    "vi": "Tạm biệt",
                    "th": "ลาก่อน",
                    "id": "Selamat tinggal",
                    "sorisae": "Sora-bye"
                }
            },
            # 비즈니스 표현
            "business": {
                "회의": {
                    "en": "meeting",
                    "ja": "会議",
                    "zh": "会议",
                    "es": "reunión",
                    "fr": "réunion",
                    "de": "Besprechung",
                    "sorisae": "Sora-meet"
                },
                "계약": {
                    "en": "contract",
                    "ja": "契約",
                    "zh": "合同",
                    "es": "contrato",
                    "fr": "contrat",
                    "de": "Vertrag",
                    "sorisae": "Sora-tract"
                },
                "협상": {
                    "en": "negotiation",
                    "ja": "交渉",
                    "zh": "谈判",
                    "es": "negociación",
                    "fr": "négociation",
                    "de": "Verhandlung",
                    "sorisae": "Sora-nego"
                }
            },
            # 일상 대화
            "daily": {
                "날씨가 좋네요": {
                    "en": "Nice weather",
                    "ja": "いい天気ですね",
                    "zh": "天气真好",
                    "es": "Buen tiempo",
                    "fr": "Beau temps",
                    "de": "Schönes Wetter",
                    "sorisae": "Sora-sun-good"
                },
                "도와주세요": {
                    "en": "Please help me",
                    "ja": "助けてください",
                    "zh": "请帮帮我",
                    "es": "Ayúdame por favor",
                    "fr": "Aidez-moi s'il vous plaît",
                    "de": "Bitte helfen Sie mir",
                    "sorisae": "Sora-help-pls"
                }
            }
        }

    def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        텍스트 번역

        Args:
            text: 번역할 텍스트
            source_lang: 원본 언어 코드
            target_lang: 대상 언어 코드

        Returns:
            str: 번역된 텍스트
        """
        # 입력 검증
        if source_lang not in self.supported_languages:
            return f"[오류: 지원하지 않는 원본 언어 '{source_lang}']"

        if target_lang not in self.supported_languages:
            return f"[오류: 지원하지 않는 대상 언어 '{target_lang}']"

        # 같은 언어면 그대로 반환
        if source_lang == target_lang:
            return text

        # 데이터베이스에서 번역 검색
        for category in self.translation_db.values():
            for key, translations in category.items():
                if text.strip() == key and target_lang in translations:
                    result = translations[target_lang]
                    self._log_translation(text, result, source_lang, target_lang)
                    return result

        # 번역을 찾지 못한 경우 - 실제 환경에서는 API 호출
        result = f"[{target_lang}] {text}"
        self._log_translation(text, result, source_lang, target_lang)
        return result

    def _log_translation(self, source: str, target: str, source_lang: str, target_lang: str):
        """번역 로그 기록"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "target": target,
            "source_lang": source_lang,
            "target_lang": target_lang
        }
        self.history.append(entry)

        # 통계 업데이트
        self.stats["total_translations"] += 1
        lang_pair = f"{source_lang}->{target_lang}"
        if lang_pair not in self.stats["by_language"]:
            self.stats["by_language"][lang_pair] = 0
        self.stats["by_language"][lang_pair] += 1

    def get_history(self, limit: int = 10) -> List[Dict]:
        """
        번역 히스토리 조회

        Args:
            limit: 조회할 최대 개수

        Returns:
            List[Dict]: 번역 히스토리 목록
        """
        return self.history[-limit:]

    def get_stats(self) -> Dict:
        """통계 정보 조회"""
        return {
            **self.stats,
            "session_duration": str(datetime.now() - self.stats["session_start"])
        }


class RealtimeInterpreter:
    """실시간 통역 시스템"""

    def __init__(self):
        """실시간 통역 시스템 초기화"""
        self.engine = InterpreterCore()
        self.active_sessions = {}
        self.is_running = False

        logger.info("실시간 통역 시스템 초기화 완료")

    def create_session(self, session_id: str, source_lang: str, target_lang: str) -> Dict:
        """
        통역 세션 생성

        Args:
            session_id: 세션 ID
            source_lang: 원본 언어
            target_lang: 대상 언어

        Returns:
            Dict: 세션 정보
        """
        session = {
            "id": session_id,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "created_at": datetime.now(),
            "status": "active",
            "translations": []
        }

        self.active_sessions[session_id] = session
        logger.info(f"통역 세션 생성: {session_id} ({source_lang} -> {target_lang})")

        return session

    def interpret(self, session_id: str, text: str) -> Optional[str]:
        """
        실시간 통역 수행

        Args:
            session_id: 세션 ID
            text: 통역할 텍스트

        Returns:
            Optional[str]: 통역된 텍스트
        """
        if session_id not in self.active_sessions:
            logger.warning(f"세션을 찾을 수 없음: {session_id}")
            return None

        session = self.active_sessions[session_id]

        # 통역 수행
        translated = self.engine.translate_text(
            text,
            session["source_lang"],
            session["target_lang"]
        )

        # 세션에 기록
        session["translations"].append({
            "original": text,
            "translated": translated,
            "timestamp": datetime.now().isoformat()
        })

        return translated

    def end_session(self, session_id: str) -> bool:
        """
        통역 세션 종료

        Args:
            session_id: 세션 ID

        Returns:
            bool: 성공 여부
        """
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["status"] = "ended"
            self.active_sessions[session_id]["ended_at"] = datetime.now()
            logger.info(f"통역 세션 종료: {session_id}")
            return True
        return False

    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """세션 정보 조회"""
        return self.active_sessions.get(session_id)


class SorisaeInterpreter:
    """나도 통역사 - 소리새 통역 메인 클래스"""

    def __init__(self):
        """통역 시스템 초기화"""
        self.realtime = RealtimeInterpreter()
        self.engine = self.realtime.engine

        print("=" * 70)
        print("🌐 나도 통역사 - 소리새 실시간 통역 시스템")
        print("   I am also an Interpreter - Sorisae Real-time Interpretation System")
        print("=" * 70)
        print(f"✅ 지원 언어: {len(self.engine.supported_languages)}개")
        for code, name in self.engine.supported_languages.items():
            print(f"   • {code}: {name}")
        print("=" * 70)

    def quick_translate(self, text: str, source_lang: str = "ko", target_lang: str = "en") -> str:
        """
        빠른 번역

        Args:
            text: 번역할 텍스트
            source_lang: 원본 언어 (기본값: 한국어)
            target_lang: 대상 언어 (기본값: 영어)

        Returns:
            str: 번역된 텍스트
        """
        return self.engine.translate_text(text, source_lang, target_lang)

    def start_conversation_mode(self):
        """대화형 통역 모드 시작"""
        print("\n🎤 대화형 통역 모드")
        print("=" * 70)
        print("명령어:")
        print("  - 'quit' 또는 'exit': 종료")
        print("  - 'stats': 통계 보기")
        print("  - 'history': 최근 번역 보기")
        print("  - 'lang': 언어 변경")
        print("=" * 70)

        source_lang = "ko"
        target_lang = "en"

        # 세션 생성
        session_id = f"session_{int(time.time())}"
        self.realtime.create_session(session_id, source_lang, target_lang)

        print(f"\n현재 설정: {source_lang} -> {target_lang}")
        print("번역할 텍스트를 입력하세요:\n")

        try:
            while True:
                user_input = input(f"[{source_lang}] >>> ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ['quit', 'exit', '종료']:
                    print("👋 통역 세션을 종료합니다.")
                    break

                elif user_input.lower() == 'stats':
                    self._show_stats()
                    continue

                elif user_input.lower() == 'history':
                    self._show_history()
                    continue

                elif user_input.lower() == 'lang':
                    source_lang, target_lang = self._change_language()
                    # 새 세션 생성
                    self.realtime.end_session(session_id)
                    session_id = f"session_{int(time.time())}"
                    self.realtime.create_session(session_id, source_lang, target_lang)
                    continue

                # 통역 수행
                translated = self.realtime.interpret(session_id, user_input)
                print(f"[{target_lang}] >>> {translated}\n")

        except KeyboardInterrupt:
            print("\n\n⚠️ 사용자가 통역을 중단했습니다.")

        finally:
            self.realtime.end_session(session_id)
            self._show_stats()

    def _show_stats(self):
        """통계 정보 표시"""
        stats = self.engine.get_stats()
        print("\n📊 통역 통계")
        print("=" * 70)
        print(f"총 번역 횟수: {stats['total_translations']}")
        print(f"세션 시간: {stats['session_duration']}")
        print("\n언어별 번역:")
        for lang_pair, count in stats['by_language'].items():
            print(f"  • {lang_pair}: {count}회")
        print("=" * 70 + "\n")

    def _show_history(self, limit: int = 5):
        """최근 번역 히스토리 표시"""
        history = self.engine.get_history(limit)
        print(f"\n📜 최근 {len(history)}개 번역")
        print("=" * 70)
        for i, entry in enumerate(history, 1):
            print(f"{i}. [{entry['source_lang']}] {entry['source']}")
            print(f"   [{entry['target_lang']}] {entry['target']}")
            print(f"   시간: {entry['timestamp']}")
            print()
        print("=" * 70 + "\n")

    def _change_language(self) -> Tuple[str, str]:
        """언어 변경"""
        print("\n🌍 언어 선택")
        print("=" * 70)
        langs = list(self.engine.supported_languages.keys())
        for i, (code, name) in enumerate(self.engine.supported_languages.items(), 1):
            print(f"{i}. {code}: {name}")
        print("=" * 70)

        try:
            source_idx = int(input("원본 언어 번호: ")) - 1
            target_idx = int(input("대상 언어 번호: ")) - 1

            source_lang = langs[source_idx]
            target_lang = langs[target_idx]

            print(f"\n✅ 언어 변경: {source_lang} -> {target_lang}\n")
            return source_lang, target_lang

        except (ValueError, IndexError):
            print("❌ 잘못된 입력입니다. 기본 설정(ko->en)을 유지합니다.\n")
            return "ko", "en"

    def demo(self):
        """통역 시스템 데모"""
        print("\n🎬 통역 시스템 데모 시작")
        print("=" * 70)

        # 데모 번역 목록
        demo_translations = [
            ("안녕하세요", "ko", "en"),
            ("안녕하세요", "ko", "ja"),
            ("감사합니다", "ko", "zh"),
            ("안녕히 가세요", "ko", "es"),
        ]

        for text, src, tgt in demo_translations:
            result = self.quick_translate(text, src, tgt)
            print(f"\n[{src}] {text}")
            print(f"[{tgt}] {result}")
            time.sleep(0.5)

        print("\n" + "=" * 70)
        print("✅ 데모 완료!")
        print("=" * 70)


def main():
    """메인 함수"""
    print("\n")
    print("🌐" * 35)
    print()

    # 통역 시스템 생성
    interpreter = SorisaeInterpreter()

    # 데모 실행
    interpreter.demo()

    # 대화형 모드 시작
    print("\n")
    response = input("대화형 통역 모드를 시작하시겠습니까? (y/n): ").strip().lower()
    if response in ['y', 'yes', '네', 'ㅇ']:
        interpreter.start_conversation_mode()

    print("\n👋 나도 통역사를 이용해 주셔서 감사합니다!")
    print("   Thank you for using I am also an Interpreter!")
    print()


if __name__ == "__main__":
    main()
