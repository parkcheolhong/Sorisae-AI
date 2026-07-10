# schemas — 직렬화 스키마(SSOT)

`market.fbs` 는 daytrade-ai 의 **직렬화 SSOT**(FlatBuffers IDL)다. C++ 코어(M3)와 Python 이
동일한 바이너리 레이아웃으로 `MarketTick`/`FeatureVector`/`Signal`/`Order`/`Fill` 을 주고받기 위함이다.

- **의미론적 SSOT**: `daytrade/types.py`
- **직렬화 SSOT**: `schemas/market.fbs`
- 두 정의의 일치는 `tests/test_schema_consistency.py` 골든 테스트로 강제한다.
  - 특히 `FeatureVector` 필드 순서는 `features/engine.py` 의 `FEATURE_NAMES` 와 반드시 같아야 한다(AI 입력 텐서 순서).

## 코드 생성(M3에서 사용)
```bash
# C++ / Python 바인딩 생성
flatc --cpp --python -o generated schemas/market.fbs
```

## 변경 규칙
필드 추가/순서 변경 시: `types.py` → `market.fbs` → 골든 테스트 순으로 동기화하고,
하위호환(append-only, deprecated 표기)을 우선한다.
