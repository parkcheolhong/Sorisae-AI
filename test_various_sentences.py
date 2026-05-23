#!/usr/bin/env python3
"""Test translator with various sentences"""

import requests
import time

# Test sentences in Korean
TEST_CASES = [
    '안녕하세요',
    '물 한 잔 주세요',
    '얼마예요',
    '맛있습니다',
    '방을 하나 예약하고 싶습니다',
    '택시를 불러주세요',
    '역은 어디입니까',
    '병원을 찾고 있습니다',
    '도움이 필요합니다',
    '이것을 사고 싶어요',
    '카드로 낼 수 있습니까',
    '내일 날씨가 어떻습니까',
    '왼쪽으로 돌아주세요',
    '이름이 뭐예요',
]

print("=" * 70)
print("🌐 다양한 문장 번역 테스트 (한국어 → 영어)")
print("=" * 70)

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

for text in TEST_CASES:
    try:
        r = requests.post(
            'http://127.0.0.1:8000/api/llm/translate',
            json={'text': text, 'from_lang': 'ko', 'to_lang': 'en'},
            timeout=8
        )
        
        if r.status_code == 200:
            result = r.json()
            translated = result.get('translated', '?')
            
            # Check if it's a real translation
            if translated and translated != text and '[' not in translated[:3]:
                print(f'✅ {text}')
                print(f'   → {translated}')
                success_count += 1
            else:
                print(f'❌ {text}')
                print(f'   → {translated} (번역 없음)')
                fail_count += 1
        else:
            print(f'❌ {text} (HTTP {r.status_code})')
            fail_count += 1
            
    except Exception as e:
        print(f'❌ {text} (Error: {str(e)[:40]})')
        fail_count += 1

print("\n" + "=" * 70)
print(f'✅ 성공: {success_count}/{len(TEST_CASES)}')
print(f'❌ 실패: {fail_count}/{len(TEST_CASES)}')
print("=" * 70)
