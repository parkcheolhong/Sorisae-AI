#!/usr/bin/env bash
# daytrade-ai C++ 코어 빌드 (Linux / GCC|Clang).
# 사전: gcc/clang(C++20), CMake. 실서버(RTX 5090 호스트)에서 빌드 권장.
#
# 사용:  bash cpp/build.sh
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python -m pip install --quiet pybind11 cmake
pybind="$(python -m pybind11 --cmakedir)"

cmake -S "$here" -B "$here/build" -Dpybind11_DIR="$pybind"
cmake --build "$here/build" --config Release -j

app="$(dirname "$here")"
pyd="$(find "$here/build" -name 'daytrade_cpp*.so' | head -n1 || true)"
if [[ -n "${pyd}" ]]; then
  cp -f "$pyd" "$app/"
  echo "[OK] copied $(basename "$pyd") -> $app"
  # 골든 동일성 테스트 자동 실행(Python 레퍼런스 대비 1e-9 수치 일치 검증)
  echo "[RUN] golden equivalence test ..."
  ( cd "$app" && python -m pytest tests/test_cpp_golden.py -q ) \
    && echo "[OK] 골든 동일성 통과 — C++ 코어가 Python 레퍼런스와 일치합니다." \
    || echo "[WARN] 골든 테스트 실패. 수치 동일성 회귀를 확인하세요." >&2
else
  echo "[WARN] 빌드 산출물(.so)을 찾지 못했습니다. 빌드 로그를 확인하세요." >&2
fi
