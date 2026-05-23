#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add pt, hi, it, tr translations to sorisae_interpreter.py
직접 고정 패턴으로 진행
"""

import os
import re

def fix_interpreter_translations():
    root = r'C:\Users\WORK\source\repos\parkcheolhong\codeAI\backend\services'
    path = None
    for r, d, f in os.walk(root):
        if 'sorisae_interpreter.py' in f and 'projects' not in r and 'engines120' not in r:
            path = os.path.join(r, 'sorisae_interpreter.py')
            break

    if not path:
        print('❌ sorisae_interpreter.py를 찾을 수 없음')
        return False

    print(f'Reading: {path}')
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Prepare the fixes
    fixes = []
    
    #  Fix 1: Add translations to "안녕하세요"
    old1 = '''"안녕하세요": {
                    "en": "Hello",
                    "ja": "こんにちは",
                    "zh": "你好",
                    "es": "Hola",
                    "fr": "Bonjour",
                    "de": "Hallo",
                    "ru": "Здравствуйте",
                    "ar": "مرحبا"
                }'''
    
    new1 = '''"안녕하세요": {
                    "en": "Hello",
                    "ja": "こんにちは",
                    "zh": "你好",
                    "es": "Hola",
                    "fr": "Bonjour",
                    "de": "Hallo",
                    "pt": "Olá",
                    "ru": "Здравствуйте",
                    "ar": "مرحبا",
                    "hi": "नमस्ते",
                    "it": "Ciao",
                    "tr": "Merhaba"
                }'''
    
    fixes.append((old1, new1))
    
    # Fix 2: Add to "감사합니다"
    old2 = '''"감사합니다": {
                    "en": "Thank you",
                    "ja": "ありがとうございます",
                    "zh": "谢谢",
                    "es": "Gracias",
                    "fr": "Merci",
                    "de": "Danke",
                    "ru": "Спасибо",
                    "ar": "شكرا"
                }'''
    
    new2 = '''"감사합니다": {
                    "en": "Thank you",
                    "ja": "ありがとうございます",
                    "zh": "谢谢",
                    "es": "Gracias",
                    "fr": "Merci",
                    "de": "Danke",
                    "pt": "Obrigado",
                    "ru": "Спасибо",
                    "ar": "شكرا",
                    "hi": "धन्यवाद",
                    "it": "Grazie",
                    "tr": "Teşekkür ederim"
                }'''
    
    fixes.append((old2, new2))
    
    # Fix 3: "안녕히 가세요"
    old3 = '''"안녕히 가세요": {
                    "en": "Goodbye",
                    "ja": "さようなら",
                    "zh": "再见",
                    "es": "Adiós",
                    "fr": "Au revoir",
                    "de": "Auf Wiedersehen",
                    "ru": "До свидания",
                    "ar": "وداعا"
                }'''
    
    new3 = '''"안녕히 가세요": {
                    "en": "Goodbye",
                    "ja": "さようなら",
                    "zh": "再见",
                    "es": "Adiós",
                    "fr": "Au revoir",
                    "de": "Auf Wiedersehen",
                    "pt": "Adeus",
                    "ru": "До свидания",
                    "ar": "وداعا",
                    "hi": "अलविदा",
                    "it": "Arrivederci",
                    "tr": "Hoşça kalın"
                }'''
    
    fixes.append((old3, new3))
    
    # Apply fixes
    updated = False
    for old, new in fixes:
        if old in content:
            content = content.replace(old, new)
            updated = True
            print(f"✅ Updated a translation block")
    
    if updated:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print('✅ interpreter 번역 추가 완료!')
        return True
    else:
        print('❌ 수정할 블록을 찾을 수 없음')
        # Try to show what we're looking for
        if '"안녕하세요"' in content:
            idx = content.find('"안녕하세요"')
            print(f"\nFound '안녕하세요' at index {idx}")
            print(content[idx:idx+300])
        return False

if __name__ == '__main__':
    success = fix_interpreter_translations()
    exit(0 if success else 1)
