# FILE-ID: FILE-INFRA-DEPLOY-SECURITY-MD
# SECTION-ID: SECTION-INFRA-DEPLOY-SECURITY-MD-MAIN
# FEATURE-ID: FEATURE-INFRA-DEPLOY-SECURITY-MD-RUNTIME
# CHUNK-ID: CHUNK-INFRA-DEPLOY-SECURITY-MD-001

# production security

- JWT_SECRET 는 32자 이상 랜덤 값으로 교체하고 주기적으로 rotation
- DATABASE_URL 은 managed database 또는 운영 DB 로 변경
- OPS_LOG_PATH 는 중앙 로그 수집 경로로 연결
- ALLOWED_HOSTS / CORS_ALLOW_ORIGINS 는 운영 도메인만 허용
- REQUEST_TIMEOUT_SEC 와 retry 정책을 운영 SLA 기준으로 조정
- 외부 연동 URL 은 https 와 allow-list 기준으로 제한
- ingress/load balancer 에서 TLS 강제
