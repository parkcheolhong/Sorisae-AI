#!/usr/bin/env python3
"""Test all 13 languages with multiple sentences"""

import requests
import time

# Sample test sentences and targets
TESTS = [
    ('안녕하세요', 'ko', 'en', 'Hello'),
    ('안녕하세요', 'ko', 'zh', '你好'),
    ('안녕하세요', 'ko', 'ja', 'こんにちは'),
    ('안녕하세요', 'ko', 'es', 'Hola'),
    ('안녕하세요', 'ko', 'fr', 'Bonjour'),
    ('안녕하세요', 'ko', 'de', 'Hallo'),
    ('안녕하세요', 'ko', 'pt', 'Olá'),
    ('안녕하세요', 'ko', 'ru', 'Здравствуйте'),
    ('안녕하세요', 'ko', 'ar', 'مرحبا'),
    ('안녕하세요', 'ko', 'hi', 'नमस्ते'),
    ('안녕하세요', 'ko', 'it', 'Ciao'),
    ('안녕하세요', 'ko', 'tr', 'Merhaba'),
    
    ('얼마예요', 'ko', 'en', 'How much is it'),
    ('얼마예요', 'ko', 'zh', '多少钱'),
    ('얼마예요', 'ko', 'ja', 'いくらですか'),
    
    ('도움이 필요합니다', 'ko', 'en', 'I need help'),
    ('도움이 필요합니다', 'ko', 'es', 'Necesito ayuda'),
    ('도움이 필요합니다', 'ko', 'ru', 'Мне нужна помощь'),
]

print("=" * 80)
print("🌍 13개 언어 번역 검증 (다양한 문장)")
print("=" * 80)

# Wait for backend
for i in range(30):
    try:
        requests.get('http://127.0.0.1:8000/health', timeout=2)
        break
    except:
        print(f"백엔드 대기 {i+1}/30...", end='\r')
        time.sleep(1)

print("\n테스트 중...\n")

success_count = 0
fail_count = 0

lang_map = {
    'ko': 'Korean',
    'en': 'English',
    'zh': 'Chinese',
    'ja': 'Japanese',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'ar': 'Arabic',
    'hi': 'Hindi',
    'it': 'Italian',
    'tr': 'Turkish'
}

for text, from_lang, to_lang, expected in TESTS:
    try:
        r = requests.post(
            'http://127.0.0.1:8000/api/llm/translate',
            json={'text': text, 'from_lang': from_lang, 'to_lang': to_lang},
            timeout=8
        )
        
        if r.status_code == 200:
            result = r.json()
            translated = result.get('translated', '?')
            
            # Check if translation matches expected
            if translated == expected:
                print(f'✅ {lang_map[from_lang]:8} → {lang_map[to_lang]:8} | {text:20} → {translated}')
                success_count += 1
            else:
                print(f'❌ {lang_map[from_lang]:8} → {lang_map[to_lang]:8} | {text:20} → {translated} (expected: {expected})')
                fail_count += 1
        else:
            print(f'❌ {lang_map[from_lang]:8} → {lang_map[to_lang]:8} | ERROR HTTP {r.status_code}')
            fail_count += 1
            
    except Exception as e:
        print(f'❌ {lang_map[from_lang]:8} → {lang_map[to_lang]:8} | ERROR: {str(e)[:40]}')
        fail_count += 1

print("\n" + "=" * 80)
print(f'✅ 성공: {success_count}/{len(TESTS)}')
print(f'❌ 실패: {fail_count}/{len(TESTS)}')
print("=" * 80)
