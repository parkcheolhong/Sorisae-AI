#!/usr/bin/env python3
"""
나도 통역사 실행 스크립트
Multi-Language Interpreter Launch Script

이 스크립트는 프로젝트를 독립적으로 실행합니다.
"""

import sys
import os
from pathlib import Path

# 루트 디렉토리를 Python 경로에 추가
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

def main():
    """메인 실행 함수"""
    print("=" * 80)
    print(f"🚀 나도 통역사 시작")
    print(f"   실시간 13개 언어 통역 시스템")
    print("=" * 80)
    print()

    # 작업 디렉토리를 루트로 변경
    os.chdir(root_dir)

    # 메인 파일 실행
    main_file = root_dir / "hybrid_conversation_translator.py"

    if not main_file.exists():
        print(f"❌ 오류: {main_file} 파일을 찾을 수 없습니다.")
        sys.exit(1)

    print(f"📂 실행 파일: {main_file}")
    print()

    # 파일 실행
    with open(main_file, 'r', encoding='utf-8') as f:
        code = compile(f.read(), main_file, 'exec')
        exec(code, {'__name__': '__main__', '__file__': str(main_file)})


if __name__ == "__main__":
    main()
