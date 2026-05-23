#!/usr/bin/env python3
"""Quick test of Korean to other languages"""

import requests

test_langs = ['en', 'pt', 'hi', 'it', 'tr']
print("ko에서 다른 언어로의 번역 테스트:")
print("=" * 50)

for lang in test_langs:
    r = requests.post(
        'http://127.0.0.1:8000/api/llm/translate',
        json={'text': '안녕하세요', 'from_lang': 'ko', 'to_lang': lang},
        timeout=8
    )
    if r.status_code == 200:
        result = r.json()
        translated = result.get('translated', '?')
        print(f'ko→{lang}: {translated}')
    else:
        print(f'ko→{lang}: Error {r.status_code}')
