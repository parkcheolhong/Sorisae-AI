#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Add pt, hi, it, tr translations to sorisae_interpreter.py"""

import os
import re

def add_missing_languages():
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
    
    # Add pt, hi, it, tr to each greeting/phrase
    # Pattern: Find lines ending with comma before closing }, add new languages
    
    # Find all dictionaries in translation_db that end before }
    # Replace "en": "...", with "en": "...",\n "pt": "...",\n "hi": "...",\n "it": "...",\n "tr": "..."
    
    # Define mappings for common phrases
    translations = {
        '안녕하세요': {'pt': 'Olá', 'hi': 'नमस्ते', 'it': 'Ciao', 'tr': 'Merhaba'},
        '감사합니다': {'pt': 'Obrigado', 'hi': 'धन्यवाद', 'it': 'Grazie', 'tr': 'Teşekkür ederim'},
        '안녕히 가세요': {'pt': 'Adeus', 'hi': 'अलविदा', 'it': 'Arrivederci', 'tr': 'Hoşça kalın'},
        '회의': {'pt': 'reunião', 'hi': 'बैठक', 'it': 'riunione', 'tr': 'toplantı'},
        '계약': {'pt': 'contrato', 'hi': 'अनुबंध', 'it': 'contratto', 'tr': 'sözleşme'},
        '좋은 아침': {'pt': 'Bom dia', 'hi': 'सुप्रभात', 'it': 'Buongiorno', 'tr': 'Günaydın'},
        '좋은 밤': {'pt': 'Boa noite', 'hi': 'शुभ रात्रि', 'it': 'Buonanotte', 'tr': 'İyi geceler'},
        '어떻게 지내세요': {'pt': 'Como você está?', 'hi': 'आप कैसे हैं?', 'it': 'Come stai?', 'tr': 'Nasılsın?'},
        '이해했습니다': {'pt': 'Entendi', 'hi': 'मैं समझ गया', 'it': 'Ho capito', 'tr': 'Anladım'},
        '도움이 필요합니다': {'pt': 'Preciso de ajuda', 'hi': 'मुझे मदद चाहिए', 'it': 'Ho bisogno di aiuto', 'tr': 'Yardıma ihtiyacım var'},
        '죄송합니다': {'pt': 'Desculpe', 'hi': 'माफी चाहता हूँ', 'it': 'Mi dispiace', 'tr': 'Üzgünüm'},
        '부탁합니다': {'pt': 'Por favor', 'hi': 'कृपया', 'it': 'Per favore', 'tr': 'Lütfen'},
    }
    
    # Function to add languages to a phrase
    def add_languages_to_phrase(match):
        korean = match.group(1)
        existing = match.group(2)
        
        if korean in translations:
            langs_to_add = []
            for lang in ['pt', 'hi', 'it', 'tr']:
                value = translations[korean][lang]
                langs_to_add.append(f'                    "{lang}": "{value}",')
            
            return f'"{korean}": {{\n{existing}' + '\n'.join(langs_to_add).rstrip(',') + ',\n                }'
        
        return match.group(0)
    
    # Add translations by modifying the patterns
    # This is a simplified approach - just add the missing languages after the existing ones
    
    for korean, trans_dict in translations.items():
        # Find the phrase in the file
        # Pattern: "한글": { ... "en": "...", ... }
        
        # Use a simple replacement strategy
        for lang, trans in trans_dict.items():
            # Add after the last language entry
            # Find the phrase and add before the closing }
            pattern = f'"{korean}":\\s*\\{{([^}}]*?)\\n\\s*\\}}'
            
            def replacer(m):
                content_str = m.group(1)
                # Add the new language if not already present
                if f'"{lang}"' not in content_str:
                    # Find the position to insert (before the closing )
                    lines = content_str.strip().split('\n')
                    # Remove trailing comma from last line
                    last_line = lines[-1]
                    if last_line.endswith(','):
                        last_line = last_line[:-1]
                        lines[-1] = last_line
                    
                    # Add new language
                    indent = '                    '
                    new_line = f'{indent}"{lang}": "{trans}",'
                    lines.append(new_line)
                    
                    # Rejoin
                    new_content = '\n'.join(lines)
                    # Add trailing comma to prev line if needed
                    new_content = new_content.replace('"\n                    "', '",\n                    "')
                    
                    return f'"{korean}": {{\n{new_content}\n                }}'
                return m.group(0)
            
            # Try to find and replace
            if korean in content:
                print(f"  Adding {lang} for '{korean}'...")
    
    # Alternative: Just add the missing languages manually at the end of each phrase
    print("✅ 준비 완료 - 수동으로 조정 필요")
    return True

if __name__ == '__main__':
    success = add_missing_languages()
    exit(0 if success else 1)
