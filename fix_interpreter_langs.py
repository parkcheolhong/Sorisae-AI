#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix interpreter language support to match app requirements"""

import os

def fix_interpreter():
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

    print(f'Found: {path}')
    
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find and replace supported_languages
    new_lines = []
    i = 0
    replaced = False
    
    while i < len(lines):
        line = lines[i]
        
        # Find the start of supported_languages definition
        if 'self.supported_languages = {' in line and not replaced:
            # Replace the entire block
            new_lines.append('        self.supported_languages = {\n')
            new_lines.append('            "ko": "한국어 (Korean)",\n')
            new_lines.append('            "en": "영어 (English)",\n')
            new_lines.append('            "zh": "중국어 (Chinese)",\n')
            new_lines.append('            "ja": "일본어 (Japanese)",\n')
            new_lines.append('            "es": "스페인어 (Spanish)",\n')
            new_lines.append('            "fr": "프랑스어 (French)",\n')
            new_lines.append('            "de": "독일어 (German)",\n')
            new_lines.append('            "pt": "포르투갈어 (Portuguese)",\n')
            new_lines.append('            "ru": "러시아어 (Russian)",\n')
            new_lines.append('            "ar": "아랍어 (Arabic)",\n')
            new_lines.append('            "hi": "힌디어 (Hindi)",\n')
            new_lines.append('            "it": "이탈리아어 (Italian)",\n')
            new_lines.append('            "tr": "터키어 (Turkish)"\n')
            new_lines.append('        }\n')
            
            # Skip old entries until we find the closing }
            i += 1
            while i < len(lines):
                if '}' in lines[i] and 'sorisae' not in lines[i]:
                    i += 1  # Skip the closing }
                    break
                i += 1
            
            replaced = True
            continue
        
        new_lines.append(line)
        i += 1
    
    if replaced:
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print('✅ supported_languages 수정 완료!')
        return True
    else:
        print('❌ supported_languages 블록을 찾을 수 없음')
        return False

if __name__ == '__main__':
    success = fix_interpreter()
    exit(0 if success else 1)
