#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Docstring 따옴표 수정 도구
4개 따옴표 문제를 일괄 수정합니다.
"""

import os
import re


def fix_docstring_quotes(file_path):
    """파일의 잘못된 docstring 따옴표를 수정"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 4개 따옴표를 3개 따옴표로 수정
        fixed_content = re.sub(r'"""', '"""', content)

        if content != fixed_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print(f"✅ 수정 완료: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"❌ 오류: {file_path} - {e}")
        return False


def main():
    """메인 실행 함수"""
    print("🔧 Docstring 따옴표 수정 시작...")

    current_dir = os.getcwd()
    fixed_count = 0

    # 현재 디렉토리의 모든 .py 파일 검사
    for root, dirs, files in os.walk(current_dir):
        # venv, __pycache__, .git 디렉토리 제외
        dirs[:] = [d for d in dirs if d not in ['venv', '__pycache__', '.git', 'backups']]

        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    if fix_docstring_quotes(file_path):
                        fixed_count += 1
                except Exception:
                    continue

    print(f"🎉 수정 완료! 총 {fixed_count}개 파일 수정됨")


if __name__ == "__main__":
    main()
