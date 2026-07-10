# WorldLinco V.2 — 보안 심화 설계 (STRIDE · Zero-Trust SSOT)

> **상태:** 설계 반영(Future) + **Phase 0 코드 레벨 일부 강제(§11)**. GPU·K8s·Istio 의존 항목은 GPU 증설 후 동결. 본 문서는 STT/MT/CodeGen 분리·Redis Streams 디커플링 시스템의 보안 설계 SSOT다.
> **연계:** [`SCALING_STT_MT_SEPARATION.md`](SCALING_STT_MT_SEPARATION.md) §9(R9)·§11·§14(P7) · [`WORLDLINCO_V2_ROADMAP.md`](WORLDLINCO_V2_ROADMAP.md)
> **불변 원칙(P0):** GPU 미확장 현재는 Phase 0 동결. 인프라/CI 레벨(TLS·이미지 스캔)만 선적용하고, GPU 분리·오토스케일·서비스메시 mTLS는 **GPU 증설 완료 후** 순차 도입.

---

## 목표

“STT / MT / 코드생성 세 워크로드를 물리·논리 분리하고 Redis Streams로 디커플링한 시스템”을 공격 면역화한다. STRIDE 관점으로 위험→완화를 정리하고, 컴포넌트별 구현 레벨 방어를 제시한다.

### 핵심 원칙
1. **Zero-Trust Network** — 서비스 간 통신은 전부 mTLS 암호화 + 최소 권한(Least-Privilege).
2. **데이터 최소화·암호화** — 오디오·번역·코드 결과는 전송·저장 모두 TLS·AES-256 보호, 필요 시 즉시 소멸.
3. **관측·자동 대응** — 모든 인증·인가·변경·오류를 Audit-Log/SIEM에 기록, Alert-Driven Auto-Remediation 구비.

---

## 1. 전체 Threat Model (Trust-Zone)

```text
+----------------------+  TLS/mTLS  +----------------------+  TLS/mTLS  +----------------------+
| Mobile App (iOS/AOS) | <--------> | API Gateway (CPU)    | <--------> | Redis Cluster (TLS)  |
+----------------------+            +----------------------+            +----------------------+
   (JWT, short-lived)                (rate-limit, RBAC)                    (ACL, AUTH)
                                              |
              +-------------------------------+-------------------------------+
              v                               v                               v
   +-------------------+  mTLS   +-------------------------+  mTLS  +-------------------+
   |  STT Worker Pod   | <-----> | K8s Service Mesh (Istio)| <----> |  MT Worker Pod    |
   +-------------------+         +-------------------------+        +-------------------+
   GPU device-plugin              (NetworkPolicy)                   GPU device-plugin
              |                                                             |
   +-------------------+  mTLS   +-------------------------+  mTLS  +-------------------+
   | CodeGen Worker    | <-----> | Orchestrator/SmartRouter| <----> | Admin UI/Dashboard|
   | (32B Coder)       |         +-------------------------+        +-------------------+
   +-------------------+
```

**Trust Boundary**
1. Mobile ↔ Gateway (Internet) — 외부 위험.
2. Gateway ↔ Redis — 내부망이지만 민감 데이터(오디오/번역)가 흐름.
3. Gateway ↔ Worker Pods — 내부지만 GPU 노드는 특권 필요 → 격리.
4. Worker ↔ Worker — 동일 클러스터지만 워크로드(STT/MT/CodeGen) 상이 → NetworkPolicy 격리.

---

## 2. STRIDE별 위험·완화

### S — Spoofing
- **위험:** JWT 탈취로 타 사용자 요청 수행 / WS URL에 임의 토큰 삽입해 다른 `call_id` 접속.
- **완화:**
  1. JWT 짧은 TTL(5분), `aud`/`iss` 검증.
  2. JWKS 키 로테이션(K8s CronJob).
  3. WS 인증: query-token + device-fingerprint(앱 버전·bundle-id)를 `sub`에 포함.
  4. mTLS(Istio sidecar)로 서비스 간 신뢰 보장.

### T — Tampering
- **위험:** Redis에 직접 `XADD`로 가짜 `stt-queue` 삽입(무한 루프) / `mt-queue` 프롬프트 오염 / 악성 이미지 삽입.
- **완화:**
  1. Redis ACL: `stt-queue`/`mt-queue` 전용 계정, `+XREADGROUP +XADD`만 허용, `FLUSHALL/CONFIG/SCRIPT` 차단.
  2. Redis TLS(stunnel) 전송 암호화.
  3. Image Signing(cosign) + SBOM 무결성 검증.
  4. PodSecurityAdmission → `runAsNonRoot`, `readOnlyRootFilesystem`, `capabilities: drop[ALL]`.

### R — Repudiation
- **위험:** “번역 결과 오염” 부인 / 토큰 발급 로그 손실로 추적 불가.
- **완화:**
  1. Audit-Log: 모든 `/voice-translate`·`/ws/*`를 JSON-Lined로 ELK 기록(`user_id·job_id·ip·ts·signature`).
  2. Log-Integrity: Hash-chain(SHA-256), logrotate 시 검증.
  3. Non-repudiation Token: `job_id`+nonce 서명 JWS 반환, 클라이언트 저장 권고.

### I — Information Disclosure
- **위험:** 오디오/번역 텍스트 Redis 평문 저장 / GPU device-plugin 노출 / 코드생성 결과에 비밀키 유출.
- **완화:**
  1. Encrypt-at-Rest: `stt-queue`/`mt-queue` AES-256 암호화.
  2. Transient Storage: 오디오 Base64 → `torch.cuda` 이송 후 `empty_cache()`로 즉시 삭제.
  3. GPU device-plugin cgroup-memory-limit, `nvidia.com/gpu` Pod-level 할당(물리 공유 금지).
  4. CodeGen: 입력은 whitelist 파라미터만, 출력은 sensitive-field scrubber로 사전 검열.

### D — Denial of Service
- **위험:** audio upload 폭주로 `stt-queue` OOM / WS 무차별 생성 / `XADD` 폭주 메모리 고갈.
- **완화:**
  1. Rate-Limiting: Gateway(Envoy/Ingress) JWT 쿼터(burst=5, rate=10/min). **[Phase 0 선적용]** 앱 레벨에서 통화 개시·LLM/이미지/관리자 변경 라우트에 인메모리 쿼터(429+`Retry-After`)를 강제 중 → §11.
  2. Circuit-Breaker(Istio `outlierDetection`).
  3. Queue-Depth Alert: `XLEN(stt-queue) > workers*3` → KEDA 증설 + Back-Pressure(429 + `Retry-After`).
  4. `maxmemory` 정책(volatile-lru)로 오래된 메시지 eviction.
  5. WS Keep-Alive: 20s ping/pong, 미응답 시 종료.

### E — Elevation of Privilege
- **위험:** GPU driver/NVIDIA Container-Toolkit 취약점으로 루트 획득 / `privileged` 잔존으로 호스트 접근.
- **완화:**
  1. PodSecurityAdmission: `runAsNonRoot`, `allowPrivilegeEscalation:false`, `readOnlyRootFilesystem:true`.
  2. Seccomp(`RuntimeDefault`)로 `ptrace`/`process_vm_writev` 차단.
  3. NVIDIA Driver 최신 패치(CVE 자동 스캔).
  4. Node-level AppArmor/SELinux 제한 프로파일.

---

## 3. 서비스별 보안 구현 체크리스트

### API Gateway (FastAPI + Uvicorn)
- TLS(cert-manager + Ingress), OAuth2 Bearer JWT + scope(`voice.translate`), Rate-limit(Envoy), WAF(ModSecurity).

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/limit-rps: "30"
    nginx.ingress.kubernetes.io/limit-burst: "60"
spec:
  tls:
    - hosts: [api.worldlinco.com]
      secretName: api-tls
  rules:
    - host: api.worldlinco.com
      http:
        paths:
          - path: /api/v1/voip/
            pathType: Prefix
            backend:
              service:
                name: voip-gateway
                port: { number: 80 }
```

### Redis Cluster
- TLS, ACL(`user stt on >… +XREADGROUP +XADD`), 비밀번호 K8s Secret(at-rest 암호화), `volatile-lru`/`maxmemory 8GB`.

```yaml
apiVersion: v1
kind: Secret
metadata: { name: redis-auth }
type: Opaque
stringData: { password: "<from-vault>" }
---
apiVersion: apps/v1
kind: StatefulSet
metadata: { name: redis }
spec:
  template:
    spec:
      containers:
        - name: redis
          image: redis:7-alpine
          command: ["redis-server","/usr/local/etc/redis/redis.conf","--tls-port","6379"]
          envFrom: [{ secretRef: { name: redis-auth } }]
          resources: { limits: { memory: "8Gi" } }
```

### STT Worker
- `runAsNonRoot(1001)`, GPU device-plugin `limits.nvidia.com/gpu:1`, Seccomp, Read-Only FS, `CUDA_VISIBLE_DEVICES` + `TORCH_CUDA_ALLOC_CONF=max_split_size_mb:64`.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: stt-worker }
spec:
  replicas: 2
  template:
    spec:
      containers:
        - name: stt
          image: ghcr.io/worldlinco/stt:latest
          securityContext:
            runAsUser: 1001
            runAsGroup: 1001
            readOnlyRootFilesystem: true
            allowPrivilegeEscalation: false
            capabilities: { drop: ["ALL"] }
            seccompProfile: { type: RuntimeDefault }
          resources:
            limits: { nvidia.com/gpu: "1", memory: "12Gi" }
          env:
            - { name: CUDA_VISIBLE_DEVICES, value: "0" }
            - { name: TORCH_CUDA_ALLOC_CONF, value: "max_split_size_mb:64" }
```

### MT Worker (vLLM)
- STT와 동일 PodSecurity, 모델 파일 read-only(`immutable:true`), GPU 격리(`nvidia.com/gpu:2`, cgroup-v2 `memory:24Gi`), Redis와 mTLS(Istio).

### CodeGen Worker
- 최고 격리: 별도 node-pool(L40S/A100), NetworkPolicy로 orchestrator만 도달(인터넷 egress 차단), 비밀키는 Vault 단기 토큰 사이드카 주입.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: deny-external-cg }
spec:
  podSelector: { matchLabels: { app: codegen } }
  policyTypes: [Ingress, Egress]
  ingress:
    - from: [{ podSelector: { matchLabels: { app: orchestrator } } }]
  egress: []   # deny all outbound
```

### Orchestrator / Smart-Router
- 다운스트림 전부 mTLS(Istio), RBAC(`serviceaccount: orchestrator`만 `codegen-queue` 호출), 라우팅 결정마다 Audit-Log(payload hash).

---

## 4. 데이터 흐름별 암호·보호

| 흐름 | 위치 | 보호 |
|------|------|------|
| Mobile → API | HTTPS(TLS1.3) | `TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384` 고정, HSTS(30d) |
| API → Redis(queue) | 내부망 | TLS(stunnel/redis-tls) + ACL 최소권한 |
| Redis → STT | 내부 메모리 | GPU 메모리와 동일, `empty_cache()` 즉시 소멸 |
| STT → Redis(mt-queue) | 내부 | TLS + ACL |
| MT → Redis(result) | Pub/Sub | TLS, `PEXPIRE` 5분 자동 삭제 |
| CodeGen → Redis | 내부 | TLS + ACL(codegen 전용) |
| Redis → UI/Admin | HTTPS + mTLS | UI Read-Only, audit 전용 파드만 리드 |
| Permanent logs | ELK/EFK | AES-256 at rest, 암호화 FS, 로그 서명(RSA-2048) |
| Model 파일 | Read-only PVC(CSI 암호화) | `readOnlyMany`, no-root, `chattr +i` |

---

## 5. 네트워크·인프라 레이어

| 레이어 | 방어 |
|--------|------|
| VPC/Subnet | API GW만 공용 서브넷, 나머지 프라이빗; NAT-GW 아웃바운드만 |
| Ingress | WAF(SQLi/XMLi/malicious base64), Rate-limit per IP/JWT |
| Service Mesh(Istio) | 전 파드 자동 mTLS, AuthorizationPolicy(role 기반) |
| Node | SSH키 Vault+MFA, OS harden(swap off, `kernel.randomize_va_space=2`) |
| GPU Node | device-plugin cgroup-v2 격리, driver read-only rootFS |
| Supply-Chain | SBOM(CycloneDX), CI에 trivy+grype, cosign+rekor |
| Secrets | K8s `EncryptionConfiguration`(AES-CTR), Vault 단기 JWT 서명키(TTL 5분) |

---

## 6. 관측·자동 대응

| 항목 | 구현 |
|------|------|
| Metrics | Prometheus: `gateway_http_requests_total`, `*_duration_seconds_bucket`, `redis_keyspace_*`, `gpu_utilization_percent`(DCGM) |
| Tracing | OpenTelemetry(FastAPI·Istio·vLLM) → Jaeger, `job_id`를 trace-ID로 REST→WS→worker 전파 |
| Logging | FluentBit → Elasticsearch(JSON: `user_id·job_id·service·event·signature`), HMAC-SHA256 서명(Vault 키) |
| Alerting | `5xx_rate>0.5%`→PagerDuty / `stt_queue_len>workers*5`→scale-out+slack / `gpu_util>85%(5m)`→증설/throttle |
| Auto-Remediation | KEDA(queue 임계 → 워커 스케일), OPA/Gatekeeper(privileged 파드 생성 거부) |
| Audit-Log | Write-only 버킷(object-level IAM), 보존 30일(GDPR Lifecycle) |
| Incident Playbook | 토큰 유출→서명키 로테이트 / Redis OOM→노드풀 오토스케일 / GPU CVE→패치 후 `rollout restart` |

---

## 7. GDPR / 개인정보 보호

| 요구사항 | 구현 |
|----------|------|
| 데이터 최소화 | 오디오 10s 초과 → `413`, 클라이언트 분할 전송 |
| 목적 제한 | 오디오는 STT 변환 후 메모리에만 존재, 디스크 미저장 |
| 보관 기간 | 변환/번역 결과는 5분 후 `PEXPIRE` |
| 삭제 요청 | `DELETE /api/v1/users/{user_id}/voip-data` → `XDEL`, audit는 익명화 후 보관 |
| 동의 기록 | 최초 `/voice-translate`에 `user_consent_hash`(SHA-256) 전송, audit 저장 |
| 전송 암호화 | TLS1.3 + PFS(ECDHE) |
| 데이터 흐름 시각화 | DFD를 CI에서 자동 생성(plantuml → PDF) |

---

## 8. “명확하고 확실한 보안” 검증 체크리스트

| # | 항목 | 검증 |
|---|------|------|
| 1 | 전 서비스 mTLS(Istio) | `istioctl proxy-config secret default` |
| 2 | JWT 짧은 TTL + 키 로테이션 | CI → Vault → CronJob(`rotate-jwt-key`) |
| 3 | Redis TLS + ACL | `redis-cli --tls -a <pwd>` → `ACL LIST` |
| 4 | PodSecurity(nonRoot/roFS/capDrop) | `kubectl get pods -o jsonpath="{.items[*].spec.securityContext}"` |
| 5 | GPU 격리(cgroup-v2/device-plugin) | `kubectl describe pod` 리소스 확인 |
| 6 | NetworkPolicy(deny-all → allow-only) | `kubectl get networkpolicy` |
| 7 | Audit-Log tamper-evidence | 24h `sha256sum` 검증 |
| 8 | Rate-limit/429 | `curl -I .../calls/initiate` 반복 → 429 |
| 9 | Secrets at-rest 암호화 | `kubectl get secret -o yaml` → aescbc 확인 |
| 10 | GDPR 보관·삭제 자동화 | `redis-cli TTL <key>`, 삭제 테스트 |

---

## 9. 로드맵 (Phase별)

| 단계 | 목표 | 주요 작업 | 예상 |
|------|------|-----------|------|
| **Phase 0(현재·동결)** | 단일 5090 유지 | CI에 보안 스캔(trivy), Ingress TLS | 2026-07-05 |
| Phase 1 — 비동기화 | REST→Redis Queue, WS keep-alive | Gateway(job_id/poll), Redis-TLS+ACL, KEDA 기본 | 2026-07-21 |
| Phase 2 — 워크로드 물리 분리 | STT/MT/CodeGen GPU 분리 | 별도 node-pool, PodSecurityAdmission, mesh mTLS 전면 | 2026-08-15 |
| Phase 3 — 오토스케일+관측 | KEDA+Prometheus+Alerting | DCGM-Exporter, Alertmanager/PagerDuty, ELK | 2026-09-01 |
| Phase 4 — 데이터 보호·컴플라이언스 | GDPR, TTL | `PEXPIRE`/삭제 API, consent-hash, 로그 익명화, DFD | 2026-09-20 |
| Phase 5 — 연속 운영 | Blue-Green 무중단 교체 | Canary(`LLM_TRANSLATE_MODEL`), cosign+Rekor, IR Playbook | 2026-10-10 |

---

## 10. 마무리 — 점진적 보안

현재 단일 GPU 구조를 유지하면서 **인프라 레벨(네트워크·TLS·ACL)** 과 **CI 레벨(이미지 스캔·SBOM)** 을 먼저 적용하고, **GPU 분리·오토스케일은 GPU 증설 완료 시점**에 순차 도입한다. Zero-Trust 강제 + 전 구간 TLS/암호화 + cgroup-v2 GPU 격리로 STT/MT/CodeGen이 상호 무간섭하면서 DDoS·데이터 유출 위협을 최소화한다. 관측·자동 대응(Prometheus+KEDA+Alertmanager+SIEM)을 파이프라인에 포함해 **P95 < 2s SLA**를 지속 검증하고 사고 시 즉시 격리·복구한다. 목표 수준: ISO 27001 / SOC-2, GDPR 충족.

---

## 11. Phase 0 코드 레벨 충족 현황 (현재 단일 GPU)

> §8의 검증 체크리스트 다수는 K8s/Istio/GPU-device-plugin 의존(Phase 1~5, GPU 증설 후)이라 현재 동결이다. 아래는 **GPU 비의존 · 애플리케이션/엣지 레벨에서 이미 강제되고 회귀 테스트로 고정된** 항목이다. (검증: 해당 pytest 그린)

| STRIDE | 위협 | 현재 코드 레벨 방어 | 위치 / 검증 |
|--------|------|--------------------|-------------|
| S | 미인증 변경 요청 | LLM/이미지/관리자 변경 라우트 Bearer 필수(미인증 401) | `backend/security_gates.py`, `tests/test_r1_r8_security_gates.py::test_llm_and_image_mutation_routes_require_auth` |
| S | 약한/누락 서명키 | `APP_ENV=production`에서 `SECRET_KEY`/`JWT_SECRET` 미설정 시 부팅 실패 | `backend/auth.py`, `…::test_production_requires_configured_secret_key` |
| S | 비밀번호 복구 우회 | 복구코드는 OTP 서비스가 `secrets.randbelow`로 난수 생성, 시도 횟수 초과 시 429 | `backend/services/contact_verification.py`, `backend/auth_router.py`(429/401 매핑), `tests/test_auth_router_security.py` |
| R | 진단 응답 정보 유출 | CPU/GPU 스냅샷 오류는 화이트리스트 코드(`cpu_load_unavailable`/`gpu_runtime_unavailable`)만 노출(경로/PII 비노출) | `tests/test_health_diagnostics_sanitization.py` |
| I | 내부 인프라 노출 | Postgres·Redis·Qdrant·MinIO·프론트·백엔드 포트 전부 `127.0.0.1` 바인드, `/docs`·`/openapi.json`은 `allow 127.0.0.1; deny all` | `docker-compose.yml`, `nginx/.../nginx.conf`, `tests/test_r6_r7_operational_risk_scan.py::test_r6_*` |
| D | 통화 개시 남용(룸 고갈·푸시 스팸) | `/api/v1/voip/calls/initiate` 사용자·클라이언트 단위 쿼터(기본 20/분, 초과 시 429+`Retry-After`) | `backend/security_gates.py::require_voip_call_quota`, `backend/tests/test_voip_presence_push.py::test_calls_initiate_enforces_rate_limit` |
| D | 변경 라우트 폭주 | LLM(60/분)·이미지(12/분)·관리자(120/분) 변경 쿼터 429+`Retry-After` | `backend/security_gates.py`, `…::test_admin_runtime_config_quota_returns_429` |
| D | WS 장기 점유로 자원 고갈 | 시그널링/WS 프록시 타임아웃을 `3600s`→`300s`로 하향(앱 20s ping/pong 유지), R7 게이트가 `3600s` 마커 부재 강제 | `nginx/.../nginx.conf`, `tests/test_r6_r7_operational_risk_scan.py::test_r7_long_timeout_markers_mitigated` |

**쿼터 환경변수(운영 조정):** `VOIP_CALL_QUOTA_MAX_REQUESTS`(기본 20) · `VOIP_CALL_QUOTA_WINDOW_SEC`(기본 60) — `0` 설정 시 비활성. 기존 `LLM_/IMAGE_/ADMIN_MUTATION_QUOTA_*` 와 동일 SSOT(`_InMemoryQuotaGate`).

**GPU 증설 후(Phase 1+) 잔여:** §8 #1(전 서비스 mTLS) · #4·#5(PodSecurity/GPU device-plugin) · #6(NetworkPolicy) · #7(Audit-Log tamper-evidence/ELK) · #9(Secrets at-rest aescbc) · #10(GDPR `PEXPIRE`/삭제 API) 는 클러스터·GPU 분리 환경 도입 시 적용한다(§9 로드맵).
