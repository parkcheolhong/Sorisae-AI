#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
소리새 통번역 프로그램 v1.0 ZIP 패키지 빌더
로컬 복사본을 ZIP으로 패키징합니다.
실행: python scripts/build_sorisae_interpreter_zip.py
출력: uploads/marketplace_local/zip/sorisae-interpreter-v1.zip
"""
import io
import sys
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_SRC_DIR = REPO_ROOT / "addons" / "shinsegye_extras" / "src" / "full_merge_all"
OUTPUT_DIR = REPO_ROOT / "uploads" / "marketplace_local" / "zip"
OUTPUT_ZIP = OUTPUT_DIR / "sorisae-interpreter-v1.zip"

SOURCE_FILES = [
    "sorisae_interpreter.py",
    "hybrid_interpreter_system.py",
    "sorisae_southeast_asia_translator.py",
    "hybrid_conversation_translator.py",
]

VERSION = "1.0.0"
BUILD_DATE = datetime.now().strftime("%Y-%m-%d")

README_CONTENT = (
    "소리새 통번역 프로그램 v" + VERSION + "\n"
    "신세계소리새(SoriSae) — 나도통역사 Python 패키지\n"
    "빌드일: " + BUILD_DATE + "\n"
    "출처: https://github.com/parkcheolhong/run_all_shinsegye.py\n"
    "=====================================================================\n\n"
    "[지원 언어 — 13개]\n"
    "한국어, 영어, 일본어, 중국어, 스페인어, 프랑스어,\n"
    "독일어, 러시아어, 아랍어, 베트남어, 태국어, 인도네시아어, 소리새어\n\n"
    "[설치 방법]\n"
    "1. Python 3.9 이상 설치: https://python.org\n"
    "2. pip install -r requirements.txt\n"
    "3. python sorisae_interpreter.py\n"
)

REQUIREMENTS_CONTENT = (
    "# 소리새 통번역 프로그램 Python 의존성\n"
    "SpeechRecognition>=3.10.0\n"
    "pyttsx3>=2.90\n"
    "requests>=2.31.0\n"
)


def build_zip() -> bool:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print()
    print("=" * 60)
    print("  소리새 통번역 패키지 빌더 v" + VERSION)
    print("  소스:", LOCAL_SRC_DIR)
    print("=" * 60)
    print()

    collected = {}

    for fname in SOURCE_FILES:
        src_path = LOCAL_SRC_DIR / fname
        print(f"  복사: {fname} ...", end=" ", flush=True)
        if src_path.exists():
            content = src_path.read_text(encoding="utf-8")
            collected[fname] = content
            print(f"OK ({len(content):,} bytes)")
        else:
            print(f"FAIL - 파일 없음: {src_path}")
            return False

    print()
    print(f"  ZIP 생성 중: {OUTPUT_ZIP.name}")

    buf = io.BytesIO()
    with ZipFile(buf, "w", compression=ZIP_DEFLATED) as zf:
        prefix = "sorisae-interpreter-v" + VERSION + "/"
        zf.writestr(prefix + "README.txt", README_CONTENT.encode("utf-8"))
        zf.writestr(prefix + "requirements.txt", REQUIREMENTS_CONTENT.encode("utf-8"))
        for fname, content in collected.items():
            zf.writestr(prefix + fname, content.encode("utf-8"))

    OUTPUT_ZIP.write_bytes(buf.getvalue())
    size = OUTPUT_ZIP.stat().st_size

    print()
    print(f"  완료: {OUTPUT_ZIP}")
    print(f"  크기: {size:,} bytes ({size/1024:.1f} KB)")
    print(f"  포함: {len(collected) + 2}개 파일")
    print()
    return True


if __name__ == "__main__":
    ok = build_zip()
    sys.exit(0 if ok else 1)