#!/usr/bin/env python3
"""
프로젝트 파일 구문 오류 검사기
프로젝트 폴더 내의 Python 파일만 검사합니다.
"""

import ast
from pathlib import Path


def check_project_syntax_errors():
    """프로젝트 Python 파일의 구문 오류 확인 (venv 제외)"""
    error_files = []
    total_files = 0

    # 제외할 디렉토리
    exclude_dirs = {'venv', '__pycache__', '.git', 'node_modules'}

    # Python 파일 찾기 (프로젝트 폴더 내에서만)
    for py_file in Path('.').rglob('*.py'):
        # 제외 디렉토리 확인
        if any(part in exclude_dirs for part in py_file.parts):
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

    print(f"\n📊 총 {total_files}개 프로젝트 파일 검사 완료")
    print(f"❌ 오류 파일: {len(error_files)}개")

    if error_files:
        print("\n🔧 수정이 필요한 파일들:")
        for file_path, error in error_files:
            print(f"  - {file_path}: {error}")

    return error_files


if __name__ == "__main__":
    check_project_syntax_errors()
