# daytrade-ai — C++ 저지연 코어 (M3)

설계서 §3-2 의 sub-ms 처리 루프(FeatureEngine / DetectionEngine)를 C++20 로 구현한 모듈입니다.
**Python 레퍼런스(`daytrade/features/engine.py`, `daytrade/detection/engine.py`)와 수치 동일성**을
보장하는 것이 1차 목표이며, 골든 테스트(`tests/test_cpp_golden.py`)로 1e-9 이내 일치를 검증합니다.

> 현재 개발 PC 에는 C++ 빌드 툴체인(MSVC C++ 워크로드 / CMake)이 설치되어 있지 않습니다.
> 따라서 빌드는 **실서버(RTX 5090 호스트)** 또는 C++ 워크로드가 설치된 환경에서 수행합니다.
> 빌드 전에는 골든 테스트가 자동 skip 되며, 나머지 112개 Python 테스트는 정상 통과합니다.

## 구성

```
cpp/
  CMakeLists.txt              # pybind11 모듈 daytrade_cpp 빌드
  build.ps1 / build.sh        # 빌드 + .pyd|.so 를 패키지 루트로 복사
  include/daytrade/
    market.hpp                # OrderBookLevel / FeatureVector / Signal (types.py·market.fbs 미러)
    feature_engine.hpp        # FeatureEngine — engine.py 라인 미러 (연산 순서 동일)
    detection_engine.hpp      # DetectionEngine — detection/engine.py 미러 (가중치/스쿼시 동일)
  src/bindings.cpp            # pybind11 바인딩
```

## 빌드 (서버)

전제: C++20 컴파일러 + CMake ≥ 3.18. pybind11 은 스크립트가 `pip install` 합니다.

### Windows (MSVC)
- Visual Studio Build Tools 의 **"C++를 사용한 데스크톱 개발"** 워크로드(VCTools + Windows SDK) 설치.

```powershell
pwsh cpp/build.ps1
```

### Linux (GCC/Clang)

```bash
bash cpp/build.sh
```

빌드가 끝나면 `daytrade_cpp.*.pyd`(Windows) 또는 `daytrade_cpp.*.so`(Linux)가
`apps/daytrade-ai/` 루트로 복사되어 `import daytrade_cpp` 가 가능해집니다.

## 검증 (골든 동일성)

```bash
python -m pytest tests/test_cpp_golden.py -q
```

- `test_feature_engine_equivalence`: 시드 고정 SimulatedFeed 1,500틱을 양쪽 FeatureEngine 에
  주입 → 8개 피처(FEATURE_NAMES)가 모두 `|Δ| ≤ 1e-9`.
- `test_detection_engine_equivalence`: 동일 틱에 대해 side(buy/sell/flat) 일치 + confidence `|Δ| ≤ 1e-9`.

## 수치 동일성 유지 규칙 (중요)

C++ 와 Python 의 부동소수 결과를 일치시키려면 **연산 순서**를 동일하게 유지해야 합니다.

- 합/분산/VWAP 누적은 deque **front→back** 순회(=Python `sum()`)와 동일하게 구현.
- z-score 는 표본분산(`n-1`), `var<=0 → 0.0`, `n<2 → 0.0` 규칙 동일.
- 윈도 캡: `obi_stat_window`, `vwap_window`, `momentum_window+1` 경계 동일.
- spread/mid 폴백: 호가가 비면 각각 `0.0` / `last_price`.

Python 레퍼런스를 수정하면 위 헤더도 함께 갱신하고 골든 테스트로 재검증하십시오.
