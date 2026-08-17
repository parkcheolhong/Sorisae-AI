#!/usr/bin/env python3
"""Test production domain with expanded translation database"""

import requests
import time

TESTS = [
    ('안녕하세요', 'ko', 'en', 'Hello'),
    ('물 한 잔 주세요', 'ko', 'en', 'A glass of water please'),
    ('얼마예요', 'ko', 'zh', '多少钱'),
    ('도움이 필요합니다', 'ko', 'es', 'Necesito ayuda'),
    ('병원을 찾고 있습니다', 'ko', 'fr', "Je cherche un hôpital"),
    ('이것을 사고 싶어요', 'ko', 'de', 'Ich möchte das kaufen'),
]

print("=" * 80)
print("🌐 운영 도메인 번역 검증 (https://metanova1004.com)")
print("=" * 80)
print("\n테스트 중...\n")

success_count = 0
fail_count = 0

for text, from_lang, to_lang, expected in TESTS:
    try:
        r = requests.post(
            'https://metanova1004.com/api/llm/translate',
            json={'text': text, 'from_lang': from_lang, 'to_lang': to_lang},
            timeout=15,
            verify=False  # Skip SSL verification for test
        )
        
        if r.status_code == 200:
            result = r.json()
            translated = result.get('translated', '?')
            
            if translated == expected:
                print(f'✅ {text:25} → {translated}')
                success_count += 1
            else:
                print(f'❌ {text:25} → {translated} (expected: {expected})')
                fail_count += 1
        else:
            print(f'❌ {text:25} → HTTP {r.status_code}')
            fail_count += 1
            
    except Exception as e:
        print(f'❌ {text:25} → ERROR: {str(e)[:50]}')
        fail_count += 1

print("\n" + "=" * 80)
print(f'✅ 성공: {success_count}/{len(TESTS)}')
print(f'❌ 실패: {fail_count}/{len(TESTS)}')
print("=" * 80)
