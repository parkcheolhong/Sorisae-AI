# 오케스트레이터-자가개선-실험-즉시-실행-원본-대상-경로-C-Use-9b4c2cd6f4 운영 가이드

## 실행 전
- configs/app.env.example 확인
- docs/runtime.md, docs/deployment.md, docs/testing.md 확인

## 실행 방법
- pip install -r requirements.delivery.lock.txt
- uvicorn app.main:create_application --factory --host 0.0.0.0 --port 8000
- pytest -q -s
- scripts/check.sh 또는 docs/automatic_validation_result.md 확인

## 운영 점검
- scripts/check.sh 실행
- runtime verification과 semantic audit 결과 확인
