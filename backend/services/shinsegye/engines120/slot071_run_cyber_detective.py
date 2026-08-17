#!/usr/bin/env python3
"""
사이버 탐정 실행 스크립트
Cyber Detective Launch Script

이 스크립트는 프로젝트를 독립적으로 실행합니다.
"""

import runpy
import sys
import os
from pathlib import Path

# 루트 디렉토리를 Python 경로에 추가
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

def main():
    """메인 실행 함수"""
    print("=" * 80)
    print(f"🚀 사이버 탐정 시작")
    print(f"   AI 기반 사이버 수사 시스템")
    print("=" * 80)
    print()

    # 작업 디렉토리를 루트로 변경
    os.chdir(root_dir)

    # 메인 파일 실행
    main_file = root_dir / "cyber_detective_ai.py"

    if not main_file.exists():
        print(f"❌ 오류: {main_file} 파일을 찾을 수 없습니다.")
        sys.exit(1)

    print(f"📂 실행 파일: {main_file}")
    print()

    # 파일 실행 (runpy 기반 런처로 안전 실행)
    runpy.run_path(str(main_file), run_name='__main__')


if __name__ == "__main__":
    main()
