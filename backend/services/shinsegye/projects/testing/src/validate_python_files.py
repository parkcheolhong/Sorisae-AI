#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ast
import glob


def validate_python_files():
    """Python 파일들의 구문 유효성 검사"""
    print("🔍 Python 파일 구문 검사 시작...")
    print("=" * 50)

    python_files = glob.glob("*.py")
    valid_files = 0
    error_files = 0
    error_details = []

    for file_path in python_files:
        # 도구 파일들은 제외
        if file_path in ['syntax_error_fixer.py', 'file_recovery_master.py', 'validate_python_files.py']:
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # AST 파싱으로 구문 검사
            ast.parse(content)
            valid_files += 1
            print(f"✅ {file_path}")

        except Exception as e:
            error_files += 1
            error_msg = str(e).split('\n')[0][:100]
            error_details.append((file_path, error_msg))
            print(f"❌ {file_path}: {error_msg}")

    print("=" * 50)
    print(f"📊 결과 요약:")
    print(f"   ✅ 정상 파일: {valid_files}개")
    print(f"   ❌ 오류 파일: {error_files}개")

    if error_details:
        print("\n🔧 오류 세부사항:")
        for file_path, error in error_details[:10]:  # 최대 10개만 표시
            print(f"   • {file_path}: {error}")

    return valid_files, error_files


if __name__ == "__main__":
    validate_python_files()
