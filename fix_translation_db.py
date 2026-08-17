#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix translation database to support only app-required languages"""

import os
import re

def fix_translation_db():
    # Find the interpreter file
    root = r'C:\Users\WORK\source\repos\parkcheolhong\codeAI\backend\services'
    path = None
    for r, d, f in os.walk(root):
        if 'sorisae_interpreter.py' in f and 'projects' not in r and 'engines120' not in r:
            path = os.path.join(r, 'sorisae_interpreter.py')
            break

    if not path:
        print('❌ sorisae_interpreter.py를 찾을 수 없음')
        return False

    print(f'Processing: {path}')
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace all translation entries to remove vi, th, id, sorisae
    # and add pt, hi, it, tr
    
    # Pattern for translation dictionaries
    replacements = [
        # "안녕하세요" greeting
        (r'"안녕하세요":\s*\{\s*"en":\s*"Hello",\s*"ja":\s*"こんにちは",\s*"zh":\s*"你好",\s*"es":\s*"Hola",\s*"fr":\s*"Bonjour",\s*"de":\s*"Hallo",\s*"ru":\s*"Здравствуйте",\s*"ar":\s*"مرحبا",\s*"vi":\s*"Xin\s+chào",\s*"th":\s*"สวัสดี",\s*"id":\s*"Halo",\s*"sorisae":\s*"Sora-hel"\s*\}',
         '"안녕하세요": {\n                    "en": "Hello",\n                    "ja": "こんにちは",\n                    "zh": "你好",\n                    "es": "Hola",\n                    "fr": "Bonjour",\n                    "de": "Hallo",\n                    "pt": "Olá",\n                    "ru": "Здравствуйте",\n                    "ar": "مرحبا",\n                    "hi": "नमस्ते",\n                    "it": "Ciao",\n                    "tr": "Merhaba"\n                }'),
    ]
    
    # Just remove all references to unsupported languages
    # This is a simpler approach: remove them from all dictionaries
    
    unsupported_langs = ['vi', 'th', 'id', 'sorisae']
    
    for lang in unsupported_langs:
        # Pattern: "langcode": "value", (with optional whitespace/newlines)
        pattern = f'\\s*"{lang}":\\s*"[^"]*",?\\n'
        content = re.sub(pattern, '\n', content)
    
    # Also fix any trailing commas that might be left
    content = re.sub(r',(\s*[\}])', r'\1', content)
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print('✅ translation_db에서 unsupported 언어 제거 완료!')
    return True

if __name__ == '__main__':
    success = fix_translation_db()
    exit(0 if success else 1)
