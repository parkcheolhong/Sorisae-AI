#!/usr/bin/env python3
"""
VR/게임 실행 스크립트
VR & Games Launch Script

이 스크립트는 프로젝트를 독립적으로 실행합니다.
"""

import sys
import os
import runpy
from pathlib import Path

# 루트 디렉토리를 Python 경로에 추가
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

def main():
    """메인 실행 함수"""
    print("=" * 80)
    print(f"🚀 VR/게임 시작")
    print(f"   VR 및 게임 생성 시스템")
    print("=" * 80)
    print()

    # 작업 디렉토리를 루트로 변경
    os.chdir(root_dir)

    # 메인 파일 실행
    main_file = root_dir / "sorisae_fantasy_vr_infinite_universe_game.py"

    if not main_file.exists():
        print(f"❌ 오류: {main_file} 파일을 찾을 수 없습니다.")
        sys.exit(1)

    print(f"📂 실행 파일: {main_file}")
    print()

    # 파일 실행 (직접 exec 대신 runpy 사용)
    runpy.run_path(str(main_file), run_name='__main__')


if __name__ == "__main__":
    main()
