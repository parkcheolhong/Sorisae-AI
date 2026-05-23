#!/usr/bin/env python3
"""Test production domain translation"""

import requests

PROD_URL = 'https://metanova1004.com/api/llm/translate'
test_langs = ['ko', 'en', 'pt', 'hi', 'it', 'tr']

print("=" * 70)
print("운영 도메인 (https://metanova1004.com) 번역 테스트")
print("=" * 70)

success_count = 0

for lang in test_langs:
    from_lang = 'ko' if lang != 'ko' else 'en'
    to_lang = 'en' if lang == 'ko' else lang
    text = '안녕하세요' if lang != 'ko' else 'Hello'
    
    try:
        r = requests.post(
            PROD_URL,
            json={
                'text': text,
                'from_lang': from_lang,
                'to_lang': to_lang
            },
            timeout=10
        )
        
        if r.status_code == 200:
            result = r.json()
            translated = result.get('translated', '?')
            if translated and translated != text:
                print(f'✅ {from_lang}→{to_lang}: {translated}')
                success_count += 1
            else:
                print(f'❌ {from_lang}→{to_lang}: No translation')
        else:
            print(f'❌ {from_lang}→{to_lang}: HTTP {r.status_code}')
            
    except Exception as e:
        print(f'❌ {from_lang}→{to_lang}: {str(e)[:50]}')

print("=" * 70)
print(f'결과: {success_count}/{len(test_langs)} 성공')
print("=" * 70)
