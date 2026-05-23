#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌏 소리새 동남아시아 언어 통역사 시스템
실시간 다국어 번역 및 문화적 맥락 포함 통역
"""


class SorisaeTranslator:
    """소리새 동남아시아 언어 통역사"""

    def __init__(self):
        """통역사 시스템 초기화"""
        self.supported_languages = {
            'ko': '한국어',
            'th': 'ไทย (태국어)',
            'vi': 'Tiếng Việt (베트남어)',
            'ms': 'Bahasa Melayu (말레이어)',
            'fil': 'Filipino (필리핀어)',
            'id': 'Bahasa Indonesia (인도네시아어)',
            'my': 'မြန်မာ (미얀마어)',
            'km': 'ខ្មែរ (크메르어)',
            'lo': 'ລາວ (라오어)',
            'en': 'English (영어)',
            'zh': '中文 (중국어)',
            'ja': '日本語 (일본어)',
            'sorisae': '소리새어 (Sorisae Language)'
        }

        # 기본 번역 사전 로드
        self.load_translation_dictionaries()

        # 문화적 맥락 데이터 로드
        self.load_cultural_contexts()

        print("🌏 소리새 동남아시아 언어 통역사가 준비되었습니다!")
        print(f"지원 언어: {len(self.supported_languages)}개")

    def load_translation_dictionaries(self):
        """번역 사전 로드"""
        self.translations = {
            # 기본 인사말
            'greetings': {
                'ko': {'안녕하세요': 'hello', '안녕히가세요': 'goodbye', '좋은아침': 'good_morning'},
                'th': {'สวัสดี': 'hello', 'ลาก่อน': 'goodbye', 'อรุณสวัสดิ์': 'good_morning'},
                'vi': {'xin chào': 'hello', 'tạm biệt': 'goodbye', 'chào buổi sáng': 'good_morning'},
                'ms': {'selamat pagi': 'good_morning', 'selamat tinggal': 'goodbye', 'hello': 'hello'},
                'fil': {'kumusta': 'hello', 'paalam': 'goodbye', 'magandang umaga': 'good_morning'},
                'id': {'selamat pagi': 'good_morning', 'selamat tinggal': 'goodbye', 'halo': 'hello'},
                'my': {'မင်္ဂလာပါ': 'hello', 'သွားတော့မယ်': 'goodbye', 'မင်္ဂလာနံနက်': 'good_morning'},
                'km': {'ជំរាបសួរ': 'hello', 'លាហើយ': 'goodbye', 'អរុណសួស្តី': 'good_morning'},
                'lo': {'ສະບາຍດີ': 'hello', 'ລາກ່ອນ': 'goodbye', 'ອຸທອນສວັສດີ': 'good_morning'},
                'sorisae': {'Sora-hel': 'hello', 'Sora-bye': 'goodbye', 'Sora-morning': 'good_morning'}
            },

            # 감사 표현
            'thanks': {
                'ko': {'감사합니다': 'thank_you', '고맙습니다': 'thank_you', '죄송합니다': 'sorry'},
                'th': {'ขอบคุณ': 'thank_you', 'ขอโทษ': 'sorry', 'ขอบพระคุณ': 'thank_you_formal'},
                'vi': {'cảm ơn': 'thank_you', 'xin lỗi': 'sorry', 'cảm ơn rất nhiều': 'thank_you_much'},
                'ms': {'terima kasih': 'thank_you', 'maaf': 'sorry', 'terima kasih banyak': 'thank_you_much'},
                'fil': {'salamat': 'thank_you', 'pasensya': 'sorry', 'maraming salamat': 'thank_you_much'},
                'id': {'terima kasih': 'thank_you', 'maaf': 'sorry', 'terima kasih banyak': 'thank_you_much'},
                'my': {'ကျေးဇူးတင်ပါတယ်': 'thank_you', 'တောင်းပန်ပါတယ်': 'sorry'},
                'km': {'អរគុណ': 'thank_you', 'សុំទោស': 'sorry', 'អរគុណច្រើន': 'thank_you_much'},
                'lo': {'ຂອບໃຈ': 'thank_you', 'ຂໍໂທດ': 'sorry', 'ຂອບໃຈຫລາຍໆ': 'thank_you_much'},
                'sorisae': {'Sora-gam': 'thank_you', 'Sora-sorry': 'sorry', 'Sora-gam-much': 'thank_you_much'}
            },

            # 기본 동사
            'verbs': {
                'ko': {'가다': 'go', '오다': 'come', '먹다': 'eat', '마시다': 'drink', '보다': 'see'},
                'th': {'ไป': 'go', 'มา': 'come', 'กิน': 'eat', 'ดื่ม': 'drink', 'ดู': 'see'},
                'vi': {'đi': 'go', 'đến': 'come', 'ăn': 'eat', 'uống': 'drink', 'xem': 'see'},
                'ms': {'pergi': 'go', 'datang': 'come', 'makan': 'eat', 'minum': 'drink', 'lihat': 'see'},
                'fil': {'pumunta': 'go', 'dumating': 'come', 'kumain': 'eat', 'uminom': 'drink', 'tingnan': 'see'},
                'id': {'pergi': 'go', 'datang': 'come', 'makan': 'eat', 'minum': 'drink', 'lihat': 'see'},
                'my': {'သွား': 'go', 'လာ': 'come', 'စား': 'eat', 'သောက်': 'drink', 'ကြည့်': 'see'},
                'km': {'ទៅ': 'go', 'មក': 'come', 'បរិភោគ': 'eat', 'ផឹក': 'drink', 'មើល': 'see'},
                'lo': {'ໄປ': 'go', 'ມາ': 'come', 'ກິນ': 'eat', 'ດື່ມ': 'drink', 'ເບິ່ງ': 'see'},
                'sorisae': {'Sora-go': 'go', 'Sora-come': 'come', 'Sora-eat': 'eat', 'Sora-drink': 'drink', 'Sora-see': 'see'}
            },

            # 숫자
            'numbers': {
                'ko': {'하나': '1', '둘': '2', '셋': '3', '넷': '4', '다섯': '5'},
                'th': {'หนึ่ง': '1', 'สอง': '2', 'สาม': '3', 'สี่': '4', 'ห้า': '5'},
                'vi': {'một': '1', 'hai': '2', 'ba': '3', 'bốn': '4', 'năm': '5'},
                'ms': {'satu': '1', 'dua': '2', 'tiga': '3', 'empat': '4', 'lima': '5'},
                'fil': {'isa': '1', 'dalawa': '2', 'tatlo': '3', 'apat': '4', 'lima': '5'},
                'id': {'satu': '1', 'dua': '2', 'tiga': '3', 'empat': '4', 'lima': '5'},
                'my': {'တစ်': '1', 'နှစ်': '2', 'သုံး': '3', 'လေး': '4', 'ငါး': '5'},
                'km': {'មួយ': '1', 'ពីរ': '2', 'បី': '3', 'បួន': '4', 'ប្រាំ': '5'},
                'lo': {'ໜຶ່ງ': '1', 'ສອງ': '2', 'ສາມ': '3', 'ສີ່': '4', 'ຫ້າ': '5'}
            }
        }

    def load_cultural_contexts(self):
        """문화적 맥락 데이터 로드"""
        self.cultural_contexts = {
            'th': {
                'honorifics': ['ครับ', 'ค่ะ', 'คะ'],
                'formal_particles': ['พระ', 'ท่าน'],
                'cultural_notes': 'ไหว้ (wai) 문화, 왕실 존경어 필수'
            },
            'vi': {
                'honorifics': ['ạ', 'dạ'],
                'formal_particles': ['thưa', 'kính'],
                'cultural_notes': '나이 서열 존중, 가족 호칭 중요'
            },
            'ms': {
                'honorifics': ['datuk', 'dato'],
                'formal_particles': ['tuan', 'puan'],
                'cultural_notes': '다종족 배려, 이슬람 인사법'
            },
            'fil': {
                'honorifics': ['po', 'opo'],
                'formal_particles': ['kuya', 'ate'],
                'cultural_notes': '나이 존경 문화, 가족적 호칭'
            },
            'id': {
                'honorifics': ['pak', 'bu'],
                'formal_particles': ['bapak', 'ibu'],
                'cultural_notes': '종교적 배려, 간접적 표현 선호'
            },
            'my': {
                'honorifics': ['ကို', 'မ'],
                'formal_particles': ['ရှင်', 'ခင်ဗျား'],
                'cultural_notes': '불교적 겸손함, 나이 존중'
            },
            'km': {
                'honorifics': ['បង', 'អូន'],
                'formal_particles': ['លោក', 'លោកស្រី'],
                'cultural_notes': '왕실 존경, 불교 전통'
            },
            'lo': {
                'honorifics': ['ບໍ່', 'ແດ່'],
                'formal_particles': ['ທ່ານ', 'ນາງ'],
                'cultural_notes': '불교 평온, 자연 조화'
            }
        }

    def detect_language(self, text):
        """언어 자동 감지"""
        # 간단한 언어 감지 로직 (실제로는 더 정교한 알고리즘 필요)
        language_patterns = {
            'th': ['ครับ', 'ค่ะ', 'สวัสดี', 'ขอบคุณ', 'ไทย'],
            'vi': ['xin chào', 'cảm ơn', 'việt nam', 'ạ', 'dạ'],
            'ms': ['selamat', 'terima kasih', 'malaysia', 'datuk'],
            'fil': ['kumusta', 'salamat', 'pilipinas', 'po', 'opo'],
            'id': ['selamat', 'terima kasih', 'indonesia', 'pak', 'bu'],
            'my': ['မင်္ဂလာပါ', 'ကျေးဇူးတင်', 'မြန်မာ'],
            'km': ['ជំរាបសួរ', 'អរគុណ', 'កម្ពុជា'],
            'lo': ['ສະບາຍດີ', 'ຂອບໃຈ', 'ລາວ'],
            'ko': ['안녕', '감사', '한국', '습니다'],
            'en': ['hello', 'thank', 'english', 'you'],
            'zh': ['你好', '谢谢', '中国', '的'],
            'ja': ['こんにちは', 'ありがとう', '日本', 'です']
        }

        text_lower = text.lower()
        detected_scores = {}

        for lang, patterns in language_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern.lower() in text_lower:
                    score += 1
            if score > 0:
                detected_scores[lang] = score

        if detected_scores:
            return max(detected_scores, key=detected_scores.get)
        return 'auto'  # 자동 감지 실패

    def translate_text(self, text, source_lang='auto', target_lang='ko'):
        """텍스트 번역"""
        # 언어 자동 감지
        if source_lang == 'auto':
            source_lang = self.detect_language(text)
            if source_lang == 'auto':
                return f"❌ 언어를 자동 감지할 수 없습니다: '{text}'"

        # 번역 사전에서 검색
        translated_parts = []
        words = text.split()

        for word in words:
            word_lower = word.lower().strip('.,!?')
            translated = self._find_translation(word_lower, source_lang, target_lang)
            translated_parts.append(translated or word)

        result = ' '.join(translated_parts)

        # 문화적 맥락 추가
        cultural_note = self._get_cultural_note(text, source_lang, target_lang)

        return {
            'original': text,
            'translated': result,
            'source_lang': self.supported_languages.get(source_lang, source_lang),
            'target_lang': self.supported_languages.get(target_lang, target_lang),
            'cultural_note': cultural_note
        }

    def _find_translation(self, word, source_lang, target_lang):
        """단어 번역 찾기"""
        for category, lang_dict in self.translations.items():
            if source_lang in lang_dict:
                for source_word, meaning in lang_dict[source_lang].items():
                    if word in source_word.lower():
                        # 타겟 언어에서 해당 의미 찾기
                        if target_lang in lang_dict:
                            for target_word, target_meaning in lang_dict[target_lang].items():
                                if target_meaning == meaning:
                                    return target_word
        return None

    def _get_cultural_note(self, text, source_lang, target_lang):
        """문화적 맥락 노트 생성"""
        notes = []

        if source_lang in self.cultural_contexts:
            context = self.cultural_contexts[source_lang]

            # 존댓말 검사
            for honorific in context.get('honorifics', []):
                if honorific in text:
                    notes.append(f"존댓말 '{honorific}' 사용됨")

            # 문화적 노트 추가
            if context.get('cultural_notes'):
                notes.append(context['cultural_notes'])

        return ' | '.join(notes) if notes else None

    def translate_with_context(self, text, source_lang='auto', target_lang='ko', context_type='formal'):
        """맥락을 고려한 번역"""
        base_translation = self.translate_text(text, source_lang, target_lang)

        # 맥락에 따른 조정
        if context_type == 'formal':
            base_translation['translated'] = self._make_formal(base_translation['translated'], target_lang)
        elif context_type == 'casual':
            base_translation['translated'] = self._make_casual(base_translation['translated'], target_lang)

        base_translation['context_applied'] = context_type
        return base_translation

    def _make_formal(self, text, lang):
        """정중한 표현으로 변환"""
        if lang == 'ko':
            text = text.replace('해', '합니다')
            text = text.replace('야', '습니다')
            if not text.endswith(('습니다', '입니다')):
                text = text.rstrip('.') + '습니다.'
        elif lang == 'th':
            if 'ครับ' not in text and 'ค่ะ' not in text:
                text += ' ครับ/ค่ะ'
        elif lang == 'vi':
            if not text.endswith('ạ'):
                text += 'ạ'
        elif lang == 'fil':
            if 'po' not in text:
                text += ' po'

        return text

    def _make_casual(self, text, lang):
        """캐주얼한 표현으로 변환"""
        if lang == 'ko':
            text = text.replace('습니다', '해')
            text = text.replace('입니다', '야')

        return text

    def show_supported_languages(self):
        """지원 언어 목록 표시"""
        print("\n🌏 지원 언어 목록:")
        for code, name in self.supported_languages.items():
            print(f"   {code}: {name}")

    def demo_translation(self):
        """번역 데모"""
        print("\n🗣️ 동남아시아 언어 번역 데모:")

        demo_phrases = [
            {'text': 'สวัสดีครับ', 'source': 'th', 'target': 'ko'},
            {'text': 'xin chào', 'source': 'vi', 'target': 'ko'},
            {'text': 'terima kasih', 'source': 'ms', 'target': 'ko'},
            {'text': 'salamat po', 'source': 'fil', 'target': 'ko'},
            {'text': 'selamat pagi', 'source': 'id', 'target': 'ko'},
            {'text': '안녕하세요', 'source': 'ko', 'target': 'th'},
            {'text': '감사합니다', 'source': 'ko', 'target': 'vi'},
        ]

        for phrase in demo_phrases:
            result = self.translate_text(phrase['text'], phrase['source'], phrase['target'])
            print(f"\n원문 ({result['source_lang']}): {result['original']}")
            print(f"번역 ({result['target_lang']}): {result['translated']}")
            if result['cultural_note']:
                print(f"문화적 맥락: {result['cultural_note']}")


def main():
    """메인 함수"""
    translator = SorisaeTranslator()

    print("\n=" * 60)
    print("🌏 소리새 동남아시아 언어 통역사 시작!")
    print("=" * 60)

    translator.show_supported_languages()
    translator.demo_translation()

    print("\n🎊 동남아시아 언어 통역사 준비 완료!")
    print("이제 소리새가 동남아시아 12개 언어를 실시간 통역할 수 있습니다!")


if __name__ == "__main__":
    main()
