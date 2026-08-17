#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌐 나도 통역사 - 소리새 실시간 통역 시스템
(I am also an Interpreter - Sorisae Real-time Interpretation System)

수아미코리아 x 신세계 소리새프로젝트 통합
실시간 음성-음성 통역 및 텍스트 번역 기능 제공
"""

import logging
import re
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
            "zh": "중국어 (Chinese)",
            "ja": "일본어 (Japanese)",
            "es": "스페인어 (Spanish)",
            "fr": "프랑스어 (French)",
            "de": "독일어 (German)",
            "pt": "포르투갈어 (Portuguese)",
            "ru": "러시아어 (Russian)",
            "ar": "아랍어 (Arabic)",
            "hi": "힌디어 (Hindi)",
            "it": "이탈리아어 (Italian)",
            "tr": "터키어 (Turkish)"
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
                    # 인사말 및 일상 표현 (Greetings & Daily Expressions)
            "greetings": {
            "안녕하세요": {
                    "en": "Hello",
                    "zh": "你好",
                    "ja": "こんにちは",
                    "es": "Hola",
                    "fr": "Bonjour",
                    "de": "Hallo",
                    "pt": "Olá",
                    "ru": "Здравствуйте",
                    "ar": "مرحبا",
                    "hi": "नमस्ते",
                    "it": "Ciao",
                    "tr": "Merhaba"
                },
            "물 한 잔 주세요": {
                    "en": "A glass of water please",
                    "zh": "请给我一杯水",
                    "ja": "水をください",
                    "es": "Un vaso de agua por favor",
                    "fr": "Un verre d'eau s'il vous plaît",
                    "de": "Ein Glas Wasser bitte",
                    "pt": "Um copo de água por favor",
                    "ru": "Стакан воды пожалуйста",
                    "ar": "كوب ماء من فضلك",
                    "hi": "कृपया एक गिलास पानी दें",
                    "it": "Un bicchiere d'acqua per favore",
                    "tr": "Lütfen bir bardak su"
                },
            "메뉴를 보여주세요": {
                    "en": "Please show me the menu",
                    "zh": "请给我看菜单",
                    "ja": "メニューを見せてください",
                    "es": "Muéstrame el menú por favor",
                    "fr": "Montrez-moi le menu s'il vous plaît",
                    "de": "Zeigen Sie mir bitte die Speisekarte",
                    "pt": "Me mostre o menu por favor",
                    "ru": "Покажите мне меню пожалуйста",
                    "ar": "أرني القائمة من فضلك",
                    "hi": "कृपया मुझे मेनू दिखाएं",
                    "it": "Mi mostri il menu per favore",
                    "tr": "Lütfen menüyü göster"
                },
            "얼마예요": {
                    "en": "How much is it",
                    "zh": "多少钱",
                    "ja": "いくらですか",
                    "es": "Cuánto cuesta",
                    "fr": "Combien ça coûte",
                    "de": "Wie viel kostet es",
                    "pt": "Quanto custa",
                    "ru": "Сколько стоит",
                    "ar": "كم السعر",
                    "hi": "यह कितना है",
                    "it": "Quanto costa",
                    "tr": "Fiyatı ne kadar"
                },
            "맛있습니다": {
                    "en": "It's delicious",
                    "zh": "很好吃",
                    "ja": "美味しいです",
                    "es": "Está delicioso",
                    "fr": "C'est délicieux",
                    "de": "Es ist köstlich",
                    "pt": "É delicioso",
                    "ru": "Это вкусно",
                    "ar": "إنه لذيذ",
                    "hi": "यह स्वादिष्ट है",
                    "it": "È delizioso",
                    "tr": "Lezzetli"
                },
            "방을 하나 예약하고 싶습니다": {
                    "en": "I want to book a room",
                    "zh": "我想预订一个房间",
                    "ja": "部屋を予約したいです",
                    "es": "Quiero reservar una habitación",
                    "fr": "Je veux réserver une chambre",
                    "de": "Ich möchte ein Zimmer buchen",
                    "pt": "Quero reservar um quarto",
                    "ru": "Я хочу забронировать номер",
                    "ar": "أريد حجز غرفة",
                    "hi": "मैं एक कमरा बुक करना चाहता हूँ",
                    "it": "Voglio prenotare una stanza",
                    "tr": "Bir oda ayırttırmak istiyorum"
                },
            "얼마 한 밤에": {
                    "en": "How much per night",
                    "zh": "每晚多少钱",
                    "ja": "1泊いくらですか",
                    "es": "Cuánto por noche",
                    "fr": "Combien par nuit",
                    "de": "Wie viel pro Nacht",
                    "pt": "Quanto por noite",
                    "ru": "Сколько за ночь",
                    "ar": "كم تكلفة الليلة",
                    "hi": "प्रति रात कितना",
                    "it": "Quanto a notte",
                    "tr": "Gecelik fiyat ne kadar"
                },
            "택시를 불러주세요": {
                    "en": "Please call a taxi",
                    "zh": "请叫一辆出租车",
                    "ja": "タクシーを呼んでください",
                    "es": "Llama un taxi por favor",
                    "fr": "Appelez un taxi s'il vous plaît",
                    "de": "Rufen Sie bitte ein Taxi",
                    "pt": "Chame um táxi por favor",
                    "ru": "Вызовите такси пожалуйста",
                    "ar": "اتصل بسيارة أجرة من فضلك",
                    "hi": "कृपया एक टैक्सी बुलाएं",
                    "it": "Chiami un taxi per favore",
                    "tr": "Lütfen bir taksi çağır"
                },
            "역은 어디입니까": {
                    "en": "Where is the station",
                    "zh": "车站在哪里",
                    "ja": "駅はどこですか",
                    "es": "Dónde está la estación",
                    "fr": "Où est la gare",
                    "de": "Wo ist der Bahnhof",
                    "pt": "Onde fica a estação",
                    "ru": "Где находится станция",
                    "ar": "أين المحطة",
                    "hi": "स्टेशन कहाँ है",
                    "it": "Dov'è la stazione",
                    "tr": "İstasyon nerede"
                },
            "병원을 찾고 있습니다": {
                    "en": "I'm looking for a hospital",
                    "zh": "我在找医院",
                    "ja": "病院を探しています",
                    "es": "Estoy buscando un hospital",
                    "fr": "Je cherche un hôpital",
                    "de": "Ich suche ein Krankenhaus",
                    "pt": "Estou procurando um hospital",
                    "ru": "Я ищу больницу",
                    "ar": "أبحث عن مستشفى",
                    "hi": "मैं एक अस्पताल ढूंढ रहा हूँ",
                    "it": "Sto cercando un ospedale",
                    "tr": "Hastane arıyorum"
                },
            "약국은 어디예요": {
                    "en": "Where is the pharmacy",
                    "zh": "药店在哪里",
                    "ja": "薬局はどこですか",
                    "es": "Dónde está la farmacia",
                    "fr": "Où est la pharmacie",
                    "de": "Wo ist die Apotheke",
                    "pt": "Onde fica a farmácia",
                    "ru": "Где аптека",
                    "ar": "أين الصيدلية",
                    "hi": "दवाखाना कहाँ है",
                    "it": "Dov'è la farmacia",
                    "tr": "Eczane nerede"
                },
            "도움이 필요합니다": {
                    "en": "I need help",
                    "zh": "我需要帮助",
                    "ja": "助けが必要です",
                    "es": "Necesito ayuda",
                    "fr": "J'ai besoin d'aide",
                    "de": "Ich brauche Hilfe",
                    "pt": "Preciso de ajuda",
                    "ru": "Мне нужна помощь",
                    "ar": "أنا بحاجة إلى مساعدة",
                    "hi": "मुझे मदद चाहिए",
                    "it": "Ho bisogno di aiuto",
                    "tr": "Yardıma ihtiyacım var"
                },
            "경찰을 불러주세요": {
                    "en": "Please call the police",
                    "zh": "请叫警察",
                    "ja": "警察を呼んでください",
                    "es": "Por favor llama a la policía",
                    "fr": "Appelez la police s'il vous plaît",
                    "de": "Rufen Sie bitte die Polizei",
                    "pt": "Chame a polícia por favor",
                    "ru": "Вызовите полицию пожалуйста",
                    "ar": "استدع الشرطة من فضلك",
                    "hi": "कृपया पुलिस बुलाएं",
                    "it": "Chiami la polizia per favore",
                    "tr": "Lütfen polisi çağır"
                },
            "응급실은 어디예요": {
                    "en": "Where is the emergency room",
                    "zh": "急诊室在哪里",
                    "ja": "救急外来はどこですか",
                    "es": "Dónde está la sala de emergencias",
                    "fr": "Où est la salle d'urgence",
                    "de": "Wo ist die Notaufnahme",
                    "pt": "Onde fica a sala de emergência",
                    "ru": "Где отделение скорой помощи",
                    "ar": "أين قسم الطوارئ",
                    "hi": "आपातकालीन कक्ष कहाँ है",
                    "it": "Dov'è il pronto soccorso",
                    "tr": "Acil bölüm nerede"
                },
            "이것을 사고 싶어요": {
                    "en": "I want to buy this",
                    "zh": "我想买这个",
                    "ja": "これを買いたいです",
                    "es": "Quiero comprar esto",
                    "fr": "Je veux acheter ceci",
                    "de": "Ich möchte das kaufen",
                    "pt": "Quero comprar isto",
                    "ru": "Я хочу это купить",
                    "ar": "أريد شراء هذا",
                    "hi": "मैं यह खरीदना चाहता हूँ",
                    "it": "Voglio comprare questo",
                    "tr": "Bunu satın almak istiyorum"
                },
            "카드로 낼 수 있습니까": {
                    "en": "Can I pay by card",
                    "zh": "我可以用卡支付吗",
                    "ja": "カードで支払えますか",
                    "es": "Puedo pagar con tarjeta",
                    "fr": "Puis-je payer par carte",
                    "de": "Kann ich mit Karte bezahlen",
                    "pt": "Posso pagar com cartão",
                    "ru": "Я могу расплатиться картой",
                    "ar": "هل يمكنني الدفع بالبطاقة",
                    "hi": "क्या मैं कार्ड से भुगतान कर सकता हूँ",
                    "it": "Posso pagare con carta",
                    "tr": "Kartla ödeyebilir miyim"
                },
            "내일 날씨가 어떻습니까": {
                    "en": "What's the weather like tomorrow",
                    "zh": "明天天气怎么样",
                    "ja": "明日の天気はどうですか",
                    "es": "Cómo es el clima mañana",
                    "fr": "Quel est le temps demain",
                    "de": "Wie ist das Wetter morgen",
                    "pt": "Como é o tempo amanhã",
                    "ru": "Какая погода завтра",
                    "ar": "كيف يكون الطقس غدا",
                    "hi": "कल का मौसम कैसा होगा",
                    "it": "Come sarà il tempo domani",
                    "tr": "Yarın hava nasıl olacak"
                },
            "비가 올 것 같은데요": {
                    "en": "It looks like it will rain",
                    "zh": "看起来会下雨",
                    "ja": "雨が降りそうです",
                    "es": "Parece que va a llover",
                    "fr": "Il semble qu'il va pleuvoir",
                    "de": "Es sieht aus wie Regen",
                    "pt": "Parece que vai chover",
                    "ru": "Похоже будет дождь",
                    "ar": "يبدو أنه سيمطر",
                    "hi": "ऐसा लगता है कि बारिश होगी",
                    "it": "Sembra che pioverà",
                    "tr": "Yağmur yağacak gibi görünüyor"
                },
            "이 길이 맞습니까": {
                    "en": "Is this the right way",
                    "zh": "这是对的路吗",
                    "ja": "これは正しい道ですか",
                    "es": "Es este el camino correcto",
                    "fr": "Est-ce le bon chemin",
                    "de": "Ist dies der richtige Weg",
                    "pt": "Este é o caminho certo",
                    "ru": "Это правильный путь",
                    "ar": "هل هذا الطريق صحيح",
                    "hi": "क्या यह सही रास्ता है",
                    "it": "È questa la strada giusta",
                    "tr": "Bu doğru yol mu"
                },
            "왼쪽으로 돌아주세요": {
                    "en": "Turn left",
                    "zh": "左转",
                    "ja": "左に曲がってください",
                    "es": "Gira a la izquierda",
                    "fr": "Tournez à gauche",
                    "de": "Biegen Sie links ab",
                    "pt": "Vire à esquerda",
                    "ru": "Поворот налево",
                    "ar": "استدر يسارا",
                    "hi": "बाएँ मुड़ें",
                    "it": "Gira a sinistra",
                    "tr": "Sola dön"
                },
            "오른쪽으로 돌아주세요": {
                    "en": "Turn right",
                    "zh": "右转",
                    "ja": "右に曲がってください",
                    "es": "Gira a la derecha",
                    "fr": "Tournez à droite",
                    "de": "Biegen Sie rechts ab",
                    "pt": "Vire à direita",
                    "ru": "Поворот направо",
                    "ar": "استدر يمينا",
                    "hi": "दाएँ मुड़ें",
                    "it": "Gira a destra",
                    "tr": "Sağa dön"
                },
            "이름이 뭐예요": {
                    "en": "What's your name",
                    "zh": "你叫什么名字",
                    "ja": "お名前は何ですか",
                    "es": "Cuál es tu nombre",
                    "fr": "Quel est votre nom",
                    "de": "Wie ist Ihr Name",
                    "pt": "Qual é o seu nome",
                    "ru": "Как вас зовут",
                    "ar": "ما اسمك",
                    "hi": "आपका नाम क्या है",
                    "it": "Qual è il tuo nome",
                    "tr": "Adın ne"
                },
            "저는 서울에서 왔습니다": {
                    "en": "I'm from Seoul",
                    "zh": "我来自首尔",
                    "ja": "私はソウルから来ました",
                    "es": "Soy de Seúl",
                    "fr": "Je suis de Séoul",
                    "de": "Ich komme aus Seoul",
                    "pt": "Sou de Seul",
                    "ru": "Я из Сеула",
                    "ar": "أنا من سيول",
                    "hi": "मैं सियोल से हूँ",
                    "it": "Sono da Seoul",
                    "tr": "Seoul'den geliyorum"
                },
            "처음 뵙겠습니다": {
                    "en": "Nice to meet you",
                    "zh": "很高兴认识你",
                    "ja": "はじめましてです",
                    "es": "Mucho gusto",
                    "fr": "Ravi de vous rencontrer",
                    "de": "Schön, Sie kennenzulernen",
                    "pt": "Prazer em conhecê-lo",
                    "ru": "Рад познакомиться",
                    "ar": "يسعدني التعرف عليك",
                    "hi": "आपसे मिलकर खुशी हुई",
                    "it": "Piacere di conoscerti",
                    "tr": "Tanıştığımız için sevindim"
                },
            },

            # 비즈니스 표현
            "business": {
                "회의": {
                    "en": "meeting",
                    "ja": "会議",
                    "zh": "会议",
                    "es": "reunión",
                    "fr": "réunion",
                    "de": "Besprechung"
                },
                "계약": {
                    "en": "contract",
                    "ja": "契約",
                    "zh": "合同",
                    "es": "contrato",
                    "fr": "contrat",
                    "de": "Vertrag"
                },
                "협상": {
                    "en": "negotiation",
                    "ja": "交渉",
                    "zh": "谈判",
                    "es": "negociación",
                    "fr": "négociation",
                    "de": "Verhandlung"
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
                    "de": "Schönes Wetter"
                },
                "도와주세요": {
                    "en": "Please help me",
                    "ja": "助けてください",
                    "zh": "请帮帮我",
                    "es": "Ayúdame por favor",
                    "fr": "Aidez-moi s'il vous plaît",
                    "de": "Bitte helfen Sie mir"
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

        # 번역 DB에 없더라도 사용자 체감이 가능하도록 기본 휴리스틱 번역을 시도한다.
        result = self._fallback_translate(text=text, source_lang=source_lang, target_lang=target_lang)
        self._log_translation(text, result, source_lang, target_lang)
        return result

    # googletrans 언어 코드 매핑 (내부 코드 → googletrans 코드)
    _GTRANS_LANG_MAP = {
        "zh": "zh-cn",
    }

    def _fallback_translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """번역 DB 미매칭 시 googletrans를 사용해 실제 번역을 수행한다."""
        try:
            import asyncio
            import concurrent.futures
            from googletrans import Translator as GTranslator

            src = self._GTRANS_LANG_MAP.get(source_lang, source_lang)
            dest = self._GTRANS_LANG_MAP.get(target_lang, target_lang)

            async def _do_translate():
                t = GTranslator()
                r = await t.translate(text, src=src, dest=dest)
                return r.text

            # 전용 스레드에서 새 이벤트 루프 생성 — FastAPI 루프와 충돌 방지
            def _run_in_thread():
                return asyncio.run(_do_translate())

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(_run_in_thread)
                return future.result(timeout=15)

        except Exception as exc:
            logger.warning("googletrans 번역 실패 (%s→%s): %s", source_lang, target_lang, exc)
            return f"[{target_lang}] {text}"

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
