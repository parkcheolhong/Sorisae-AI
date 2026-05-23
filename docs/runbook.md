# 오케스트레이터-자가개선-실험-즉시-실행-원본-대상-경로-C-Use-88b347d566 runbook

## startup
- `/health` 확인
- `/runtime` 확인
- `/report` 확인
- `/auth/settings` 확인
- `/ops/status` 확인

## degraded mode
- 외부 연동 장애 시 `/ops/status` 의 provider 상태를 확인
- timeout/retry 값을 운영 SLA 기준으로 조정
- `scripts/check.sh` 와 ZIP 재현 결과를 다시 확인

## security
- JWT_SECRET 는 32자 이상 랜덤 값으로 교체
- ALLOWED_HOSTS / CORS_ALLOW_ORIGINS 를 운영 도메인만 허용하도록 설정
- 외부 연동 토큰은 env_file 또는 secret manager 로 주입
