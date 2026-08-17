#!/usr/bin/env python3
"""Count current phrases in translation_db"""

import os
import re

root = r'C:\Users\WORK\source\repos\parkcheolhong\codeAI\backend\services'
for r, d, f in os.walk(root):
    if 'sorisae_interpreter.py' in f and 'projects' not in r and 'engines120' not in r:
        path = os.path.join(r, 'sorisae_interpreter.py')
        with open(path, encoding='utf-8') as file:
            content = file.read()
        
        # Find translation_db section
        db_start = content.find('def _initialize_translation_db')
        db_end = content.find('def ', db_start + 10)
        db_section = content[db_start:db_end if db_end > 0 else len(content)]
        
        # Count dictionaries (phrases)
        phrases = re.findall(r'"([^"]+)":\s*\{[^}]*"en":', db_section)
        
        print(f'현재 번역 데이터베이스 상태')
        print('=' * 60)
        print(f'한글 구문 총: {len(phrases)}개')
        print(f'\n구문 목록:')
        for i, phrase in enumerate(phrases, 1):
            print(f'{i:2d}. {phrase}')
        
        break
