#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
소리새 다국어 시스템 (Sorisae Multilingual System)
컨트롤 타워에서 관리하는 통합 다국어 지원 시스템
"""

import re
from typing import Dict, List

import pyttsx3

# 오프라인 번역 시스템 (기본 사전 기반)
try:
    from googletrans import Translator
    ONLINE_TRANSLATION = True
except ImportError:
    ONLINE_TRANSLATION = False
    print("⚠️ googletrans 패키지 없음 - 오프라인 모드로 실행")


class MultilingualSystem:
    """소리새 다국어 시스템 - 컨트롤 타워 관리"""

    def __init__(self):
        if ONLINE_TRANSLATION:
            self.translator = Translator()
        else:
            self.translator = None
        self.current_language = 'ko'  # 기본 언어: 한국어
        self.supported_languages = {
            'ko': {'name': '한국어', 'code': 'ko', 'tts_voice': 'korean'},
            'en': {'name': 'English', 'code': 'en', 'tts_voice': 'english'},
            'ja': {'name': '日本語', 'code': 'ja', 'tts_voice': 'japanese'},
            'zh': {'name': '中文', 'code': 'zh', 'tts_voice': 'chinese'},
            'es': {'name': 'Español', 'code': 'es', 'tts_voice': 'spanish'},
            'fr': {'name': 'Français', 'code': 'fr', 'tts_voice': 'french'},
            'de': {'name': 'Deutsch', 'code': 'de', 'tts_voice': 'german'},
            'ru': {'name': 'Русский', 'code': 'ru', 'tts_voice': 'russian'},
            'sorisae': {'name': '소리새어', 'code': 'sorisae', 'tts_voice': 'english'}
        }

        # TTS 엔진들 (언어별)
        self.tts_engines = {}
        self._initialize_tts_engines()

        # 다국어 메시지 템플릿
        self.messages = self._load_multilingual_templates()

        # 언어 감지 패턴
        self.language_patterns = self._initialize_language_patterns()

        print(f"🌍 소리새 다국어 시스템 초기화 완료!")
        print(f"📍 현재 언어: {self.supported_languages[self.current_language]['name']}")
        print(f"🗣️ 지원 언어: {len(self.supported_languages)}개")

    def _initialize_tts_engines(self):
        """언어별 TTS 엔진 초기화"""
        try:
            # 기본 TTS 엔진
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')

            # 언어별 음성 찾기
            for lang_code, lang_info in self.supported_languages.items():
                lang_engine = pyttsx3.init()

                # 해당 언어의 음성 찾기
                for voice in voices:
                    voice_name = voice.name.lower()
                    if any(keyword in voice_name for keyword in [
                        lang_info['tts_voice'], lang_code, lang_info['name'].lower()
                    ]):
                        lang_engine.setProperty('voice', voice.id)
                        break

                # 기본 설정
                lang_engine.setProperty('rate', 150)
                lang_engine.setProperty('volume', 0.9)

                self.tts_engines[lang_code] = lang_engine

            print(f"🎤 {len(self.tts_engines)}개 언어 TTS 엔진 초기화 완료")

        except Exception as e:
            print(f"⚠️ TTS 엔진 초기화 오류: {e}")
            self.tts_engines = {}

    def _load_multilingual_templates(self) -> Dict:
        """다국어 메시지 템플릿 로드"""
        templates = {
            'greetings': {
                'ko': ['안녕하세요!', '반갑습니다!', '어서오세요!'],
                'en': ['Hello!', 'Welcome!', 'Nice to meet you!'],
                'ja': ['こんにちは！', 'いらっしゃいませ！', 'はじめまして！'],
                'zh': ['你好！', '欢迎！', '很高兴见到你！'],
                'es': ['¡Hola!', '¡Bienvenido!', '¡Mucho gusto!'],
                'fr': ['Bonjour!', 'Bienvenue!', 'Enchanté!'],
                'de': ['Hallo!', 'Willkommen!', 'Freut mich!'],
                'ru': ['Привет!', 'Добро пожаловать!', 'Приятно познакомиться!'],
                'sorisae': ['Sora-hel!', 'Sora-wel!', 'Sora-meet-nice!']
            },
            'system_messages': {
                'ko': {
                    'language_changed': '{language}로 언어가 변경되었습니다.',
                    'translation_complete': '번역이 완료되었습니다.',
                    'voice_call_received': '{caller}님이 호출하고 있습니다.',
                    'music_playing': '음악을 재생합니다.',
                    'error_occurred': '오류가 발생했습니다: {error}'
                },
                'en': {
                    'language_changed': 'Language changed to {language}.',
                    'translation_complete': 'Translation completed.',
                    'voice_call_received': '{caller} is calling you.',
                    'music_playing': 'Now playing music.',
                    'error_occurred': 'An error occurred: {error}'
                },
                'ja': {
                    'language_changed': '言語が{language}に変更されました。',
                    'translation_complete': '翻訳が完了しました。',
                    'voice_call_received': '{caller}さんからの呼び出しです。',
                    'music_playing': '音楽を再生します。',
                    'error_occurred': 'エラーが発生しました: {error}'
                },
                'zh': {
                    'language_changed': '语言已更改为{language}。',
                    'translation_complete': '翻译完成。',
                    'voice_call_received': '{caller}正在呼叫您。',
                    'music_playing': '正在播放音乐。',
                    'error_occurred': '发生错误: {error}'
                },
                'sorisae': {
                    'language_changed': 'Sora-lang change-to {language}.',
                    'translation_complete': 'Sora-trans done-ok.',
                    'voice_call_received': '{caller} call-you-now.',
                    'music_playing': 'Sora-music play-now.',
                    'error_occurred': 'Sora-error: {error}'
                }
            },
            'commands': {
                'ko': {
                    'change_language': ['언어 변경', '언어 바꿔', '다른 언어로'],
                    'translate': ['번역해줘', '번역', 'translate'],
                    'speak': ['말해줘', '읽어줘', '발음해줘'],
                    'help': ['도움말', '사용법', '명령어']
                },
                'en': {
                    'change_language': ['change language', 'switch language', 'language'],
                    'translate': ['translate', 'translation', 'convert'],
                    'speak': ['speak', 'say', 'pronounce'],
                    'help': ['help', 'usage', 'commands']
                }
            }
        }
        return templates

    def _initialize_language_patterns(self) -> Dict:
        """언어 감지 패턴 초기화"""
        patterns = {
            'ko': [
                r'[ㄱ-ㅎ가-힣]',  # 한글
                r'(입니다|습니다|해요|해|줘|님|씨)'
            ],
            'en': [
                r'\b(the|and|or|in|on|at|to|for|of|with|by)\b',
                r'\b(hello|hi|thank|please|yes|no)\b'
            ],
            'ja': [
                r'[ひらがな-ゟカタカナ-ヿ]',  # 히라가나, 카타카나
                r'[一-龯]',  # 한자
                r'(です|ます|だ|である|さん|kun|chan)'
            ],
            'zh': [
                r'[一-龯]',  # 중국어 한자
                r'(的|了|是|在|有|和|我|你|他)'
            ]
        }
        return patterns

    def detect_language(self, text: str) -> str:
        """텍스트 언어 자동 감지"""
        try:
            # 온라인 번역이 가능한 경우
            if ONLINE_TRANSLATION and self.translator:
                detected = self.translator.detect(text)
                detected_lang = detected.lang

                # 지원 언어인지 확인
                if detected_lang in self.supported_languages:
                    return detected_lang

            # 패턴 기반 감지 (오프라인)
            for lang_code, patterns in self.language_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, text, re.IGNORECASE):
                        return lang_code

            return 'ko'  # 기본값

        except Exception as e:
            print(f"⚠️ 언어 감지 오류: {e}")
            return 'ko'  # 기본값

    def translate_text(self, text: str, target_lang: str = None, source_lang: str = None) -> Dict:
        """텍스트 번역"""
        try:
            if not target_lang:
                target_lang = self.current_language

            if not source_lang:
                source_lang = self.detect_language(text)

            # 같은 언어면 번역 불필요
            if source_lang == target_lang:
                return {
                    'success': True,
                    'original_text': text,
                    'translated_text': text,
                    'source_language': source_lang,
                    'target_language': target_lang,
                    'confidence': 1.0
                }

            # 온라인 번역 시도
            if ONLINE_TRANSLATION and self.translator:
                result = self.translator.translate(text, src=source_lang, dest=target_lang)
                return {
                    'success': True,
                    'original_text': text,
                    'translated_text': result.text,
                    'source_language': source_lang,
                    'target_language': target_lang,
                    'confidence': getattr(result, 'confidence', 0.9)
                }
            else:
                # 오프라인 기본 번역 (간단한 사전)
                translated = self._offline_translate(text, source_lang, target_lang)
                return {
                    'success': True,
                    'original_text': text,
                    'translated_text': translated,
                    'source_language': source_lang,
                    'target_language': target_lang,
                    'confidence': 0.7
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'original_text': text
            }

    def _offline_translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """오프라인 기본 번역 (간단한 사전 기반)"""
        # 기본 번역 사전
        basic_dict = {
            ('ko', 'en'): {
                '안녕하세요': 'Hello',
                '감사합니다': 'Thank you',
                '죄송합니다': 'Sorry',
                '네': 'Yes',
                '아니오': 'No',
                '소리새': 'Sorisae',
                '음악': 'Music',
                '채팅': 'Chat',
                '호출': 'Call'
            },
            ('en', 'ko'): {
                'hello': '안녕하세요',
                'thank you': '감사합니다',
                'sorry': '죄송합니다',
                'yes': '네',
                'no': '아니오',
                'music': '음악',
                'chat': '채팅',
                'call': '호출'
            }
        }

        # 사전에서 찾기
        dict_key = (source_lang, target_lang)
        if dict_key in basic_dict:
            dictionary = basic_dict[dict_key]
            text_lower = text.lower()

            for original, translated in dictionary.items():
                if original in text_lower:
                    return text.replace(original, translated)

        # 번역할 수 없으면 원문 반환
        return f"[{target_lang.upper()}] {text}"

    def speak_multilingual(self, text: str, language: str = None) -> bool:
        """다국어 TTS 음성 출력"""
        try:
            if not language:
                language = self.current_language

            # 해당 언어의 TTS 엔진 사용
            if language in self.tts_engines:
                engine = self.tts_engines[language]
                engine.say(text)
                engine.runAndWait()
                return True
            else:
                # 기본 TTS 사용
                print(f"🔊 [{language.upper()}] {text}")
                return False

        except Exception as e:
            print(f"⚠️ TTS 오류: {e}")
            print(f"🔊 [{language.upper()}] {text}")
            return False

    def change_language(self, new_language: str) -> Dict:
        """시스템 언어 변경"""
        try:
            if new_language not in self.supported_languages:
                return {
                    'success': False,
                    'error': f"지원하지 않는 언어입니다: {new_language}"
                }

            old_language = self.current_language
            self.current_language = new_language

            # 언어 변경 알림
            lang_name = self.supported_languages[new_language]['name']
            message_template = self.messages['system_messages'][new_language]['language_changed']
            message = message_template.format(language=lang_name)

            self.speak_multilingual(message, new_language)

            return {
                'success': True,
                'old_language': old_language,
                'new_language': new_language,
                'message': message
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_multilingual_response(self, message_key: str, **kwargs) -> str:
        """다국어 응답 메시지 생성"""
        try:
            templates = self.messages['system_messages'].get(self.current_language, {})
            template = templates.get(message_key, message_key)
            return template.format(**kwargs)
        except Exception:
            return message_key

    def get_supported_languages(self) -> List[Dict]:
        """지원 언어 목록 조회"""
        return [
            {
                'code': code,
                'name': info['name'],
                'current': code == self.current_language
            }
            for code, info in self.supported_languages.items()
        ]

    def multilingual_voice_call(self, caller: str, target: str, message: str = None) -> str:
        """다국어 음성 호출"""
        try:
            if not message:
                message = self.get_multilingual_response(
                    'voice_call_received',
                    caller=caller
                )

            # 대상의 언어로 번역
            # (실제로는 사용자 프로필에서 선호 언어를 가져와야 함)
            translated = self.translate_text(message, self.current_language)

            if translated['success']:
                call_message = f"{target}님! {target}님! {translated['translated_text']}"
                self.speak_multilingual(call_message, self.current_language)
                return call_message
            else:
                return message

        except Exception as e:
            return f"다국어 호출 오류: {e}"


# 전역 다국어 시스템 인스턴스
multilingual_system = MultilingualSystem()


def test_multilingual_system():
    """다국어 시스템 테스트"""
    print("\n🌍 소리새 다국어 시스템 테스트")
    print("=" * 50)

    # 1. 언어 감지 테스트
    test_texts = [
        "안녕하세요! 반갑습니다!",
        "Hello! How are you?",
        "こんにちは！元気ですか？",
        "你好！你好吗？"
    ]

    print("\n1. 언어 감지 테스트:")
    for text in test_texts:
        detected = multilingual_system.detect_language(text)
        lang_name = multilingual_system.supported_languages[detected]['name']
        print(f"   '{text[:20]}...' → {lang_name} ({detected})")

    # 2. 번역 테스트
    print("\n2. 번역 테스트:")
    test_text = "안녕하세요! 소리새 AI입니다."

    for lang_code in ['en', 'ja', 'zh']:
        result = multilingual_system.translate_text(test_text, lang_code)
        if result['success']:
            lang_name = multilingual_system.supported_languages[lang_code]['name']
            print(f"   {lang_name}: {result['translated_text']}")

    # 3. 언어 변경 테스트
    print("\n3. 언어 변경 테스트:")
    for lang_code in ['en', 'ja', 'ko']:
        result = multilingual_system.change_language(lang_code)
        if result['success']:
            print(f"   ✅ {result['message']}")

    # 4. 다국어 음성 호출 테스트
    print("\n4. 다국어 음성 호출 테스트:")
    call_message = multilingual_system.multilingual_voice_call(
        "철홍", "소리새", "음성 채팅을 시작하겠습니다!"
    )
    print(f"   호출 메시지: {call_message}")

    # 5. 지원 언어 목록
    print("\n5. 지원 언어 목록:")
    languages = multilingual_system.get_supported_languages()
    for lang in languages:
        status = "🌟 현재" if lang['current'] else "  "
        print(f"   {status} {lang['name']} ({lang['code']})")

    print("\n🎉 다국어 시스템 테스트 완료!")
    return True


def main(context: dict = None) -> dict:
    context = context or {}
    text = str(context.get('text', '안녕하세요'))
    target_lang = str(context.get('target_lang', 'en'))
    result = multilingual_system.translate_text(text, target_lang)
    return {
        'status': 'ok',
        'original_text': text,
        'target_lang': target_lang,
        'translated_text': result.get('translated_text', '') if isinstance(result, dict) else str(result),
    }


if __name__ == "__main__":
    test_multilingual_system()
