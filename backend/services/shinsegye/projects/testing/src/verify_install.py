#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
설치 확인 스크립트 (Installation Verification Script)
소리새 AI가 올바르게 설치되었는지 확인합니다.
"""

import os
import sys
from importlib import import_module
from typing import Tuple


def check_python_version() -> Tuple[bool, str]:
    """Python 버전 확인"""
    version = sys.version_info
    required = (3, 8)

    if version >= required:
        return True, f"✅ Python {version.major}.{version.minor}.{version.micro}"
    else:
        return False, f"❌ Python {version.major}.{version.minor}.{version.micro} (3.8 이상 필요)"


def check_package(package_name: str, import_name: str = None) -> Tuple[bool, str]:
    """패키지 설치 확인"""
    if import_name is None:
        import_name = package_name

    try:
        import_module(import_name)
        return True, f"✅ {package_name}"
    except ImportError:
        return False, f"❌ {package_name} (설치 필요)"
    except Exception as exc:
        return False, f"⚠️  {package_name} (설치는 됐지만 import 실패: {exc.__class__.__name__})"


def check_directory(dir_path: str) -> Tuple[bool, str]:
    """디렉토리 존재 확인"""
    if os.path.exists(dir_path) and os.path.isdir(dir_path):
        return True, f"✅ {dir_path}/"
    else:
        return False, f"❌ {dir_path}/ (생성 필요)"


def check_file(file_path: str) -> Tuple[bool, str]:
    """파일 존재 확인"""
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return True, f"✅ {file_path}"
    else:
        return False, f"⚠️  {file_path} (선택사항)"


def main():
    """메인 실행 함수"""
    print("=" * 50)
    print("🌟 소리새 AI 설치 확인")
    print("🌟 Sorisae AI Installation Verification")
    print("=" * 50)
    print()

    all_checks = []

    # 1. Python 버전 확인
    print("📋 1. Python 버전 확인")
    success, msg = check_python_version()
    print(f"   {msg}")
    all_checks.append(success)
    print()

    # 2. 필수 패키지 확인
    print("📋 2. 필수 패키지 확인")
    required_packages = [
        ("speechrecognition", "speech_recognition"),
        ("pyttsx3", "pyttsx3"),
        ("pyaudio", "pyaudio"),
        ("flask", "flask"),
        ("flask-socketio", "flask_socketio"),
        ("nltk", "nltk"),
    ]

    for pkg_name, import_name in required_packages:
        success, msg = check_package(pkg_name, import_name)
        print(f"   {msg}")
        all_checks.append(success)
    print()

    # 3. 선택적 패키지 확인
    print("📋 3. 선택적 패키지 확인")
    optional_packages = [
        ("transformers", "transformers"),
        ("torch", "torch"),
        ("konlpy", "konlpy"),
    ]

    for pkg_name, import_name in optional_packages:
        success, msg = check_package(pkg_name, import_name)
        print(f"   {msg}")
        if pkg_name in ["transformers", "torch"]:
            print(f"      (AI 기능에 필요, 시간이 오래 걸릴 수 있음)")
    print()

    # 4. 필수 디렉토리 확인
    print("📋 4. 필수 디렉토리 확인")
    required_dirs = ["logs", "data", "config", "memories", "modules"]

    for dir_name in required_dirs:
        success, msg = check_directory(dir_name)
        print(f"   {msg}")
        all_checks.append(success)
    print()

    # 5. 핵심 파일 확인
    print("📋 5. 핵심 파일 확인")
    core_files = [
        "run_all_shinsegye.py",
        "requirements.txt",
        "README.md",
        "INSTALL.md",
    ]

    for file_name in core_files:
        success, msg = check_file(file_name)
        print(f"   {msg}")
    print()

    # 6. 결과 요약
    print("=" * 50)
    if all(all_checks):
        print("✅ 모든 필수 항목이 확인되었습니다!")
        print("🚀 소리새 AI를 실행할 준비가 완료되었습니다.")
        print()
        print("실행 방법:")
        print("  python run_all_shinsegye.py")
        print("  또는")
        print("  ./start_sorisae.sh    (Linux/Mac)")
        print("  start_sorisae.bat     (Windows)")
        return 0
    else:
        print("⚠️  일부 항목에 문제가 있습니다.")
        print("📖 INSTALL.md를 참조하여 누락된 항목을 설치하세요.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
