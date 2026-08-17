#!/usr/bin/env python3
"""
토목 입찰 시스템 실행 스크립트
Civil Engineering Bidding Launch Script

이 스크립트는 프로젝트를 독립적으로 실행합니다.
"""

import sys
import os
import subprocess
from pathlib import Path

# 루트 디렉토리를 Python 경로에 추가
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

def main():
    """메인 실행 함수"""
    print("=" * 80)
    print(f"🚀 토목 입찰 시스템 시작")
    print(f"   AI 기반 건설 프로젝트 입찰 분석")
    print("=" * 80)
    print()

    # 작업 디렉토리를 루트로 변경
    os.chdir(root_dir)

    # 메인 파일 실행
    main_file = root_dir / "civil_engineering_bidding_demo.py"

    if not main_file.exists():
        print(f"❌ 오류: {main_file} 파일을 찾을 수 없습니다.")
        sys.exit(1)

    print(f"📂 실행 파일: {main_file}")
    print()
    # 파일 실행 (subprocess로 별도 프로세스 기동, exec 직접 실행 금지 정책 준수)
    result = subprocess.run(
        [sys.executable, str(main_file)],
        cwd=str(root_dir),
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
