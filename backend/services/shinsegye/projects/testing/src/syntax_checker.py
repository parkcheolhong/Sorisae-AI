#!/usr/bin/env python3
"""
구문 오류 파일 검사기
정리 후 Python 파일들의 구문 오류를 검사합니다.
"""

import ast
from pathlib import Path


def check_syntax_errors():
    """모든 Python 파일의 구문 오류 확인"""
    error_files = []
    total_files = 0

    # Python 파일 찾기 (modules 폴더 중심)
    for py_file in Path('.').rglob('*.py'):
        if '__pycache__' in str(py_file):
            continue

        total_files += 1

        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # AST로 구문 검사
            ast.parse(content)
            print(f"✅ {py_file}")

        except SyntaxError as e:
            error_files.append((py_file, str(e)))
            print(f"❌ {py_file}: {e}")

        except UnicodeDecodeError as e:
            error_files.append((py_file, f"Encoding error: {e}"))
            print(f"📄 {py_file}: Encoding error")

        except Exception as e:
            error_files.append((py_file, str(e)))
            print(f"⚠️  {py_file}: {e}")

    print(f"\n📊 총 {total_files}개 파일 검사 완료")
    print(f"❌ 오류 파일: {len(error_files)}개")

    if error_files:
        print("\n🔧 수정이 필요한 파일들:")
        for file_path, error in error_files:
            print(f"  - {file_path}: {error}")

    return error_files


if __name__ == "__main__":
    check_syntax_errors()
