#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test translator with all 13 languages"""

import requests
import json
import sys
import time

# Test languages (matching app requirement)
LANGS = ['ko', 'en', 'zh', 'ja', 'es', 'fr', 'de', 'pt', 'ru', 'ar', 'hi', 'it', 'tr']

# Test sentences in Korean
test_sentences = [
    '안녕하세요',
    '감사합니다',
    '좋은 아침입니다',
    '도와주세요'
]

def test_translate():
    print("=" * 70)
    print("🌐 번역 기능 13개국어 테스트")
    print("=" * 70)
    
    success_count = 0
    fail_count = 0
    fail_langs = []
    
    for target_lang in LANGS:
        print(f"\n[{target_lang.upper()}] 테스트 중...", end=' ')
        
        try:
            # Test first sentence
            r = requests.post(
                'http://127.0.0.1:8000/api/llm/translate',
                json={
                    'text': test_sentences[0],
                    'from_lang': 'ko',
                    'to_lang': target_lang
                },
                timeout=8
            )
            
            if r.status_code == 200:
                result = r.json()
                translated = result.get('translated', '')
                
                # Check if it's actually translated (not just fallback)
                if translated and translated != test_sentences[0] and '[오류' not in translated and '[Error' not in translated:
                    print(f"✅ {translated}")
                    success_count += 1
                else:
                    print(f"❌ No translation: {translated}")
                    fail_count += 1
                    fail_langs.append(target_lang)
            else:
                print(f"❌ Status {r.status_code}")
                fail_count += 1
                fail_langs.append(target_lang)
                
        except Exception as e:
            print(f"❌ Error: {str(e)[:50]}")
            fail_count += 1
            fail_langs.append(target_lang)
    
    # Summary
    print("\n" + "=" * 70)
    print(f"✅ 성공: {success_count}/{len(LANGS)}")
    print(f"❌ 실패: {fail_count}/{len(LANGS)}")
    
    if fail_langs:
        print(f"\n실패한 언어: {', '.join(fail_langs)}")
    else:
        print("\n🎉 모든 언어 번역 성공!")
    
    print("=" * 70)
    
    return fail_count == 0

if __name__ == '__main__':
    # Wait for backend to start
    print("백엔드 시작 대기 중...")
    for i in range(30):
        try:
            requests.get('http://127.0.0.1:8000/health', timeout=2)
            print("✅ 백엔드 준비 완료!")
            break
        except:
            print(f"  {i+1}/30 대기 중...", end='\r')
            time.sleep(1)
    
    success = test_translate()
    sys.exit(0 if success else 1)
