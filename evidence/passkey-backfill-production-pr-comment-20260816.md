## Passkey Multi-device Backfill: Production Closure

Production backfill verification is completed.

### What was validated
- Health endpoint checks
  - `https://xn--114-2p7l635dz3bh5j.com/api/health` -> 200
  - `https://metanova1004.com/api/health` -> 200
- Backfill execution
  - `python scripts/backfill_passkey_credentials.py`
  - Result: `PASSKEY_BACKFILL scanned=1 inserted=0 updated=0 unchanged=1 skipped=0`
- Idempotency re-check
  - `python scripts/backfill_passkey_credentials.py --dry-run`
  - Result: `PASSKEY_BACKFILL scanned=1 inserted=0 updated=0 unchanged=1 skipped=0`
- Production passkey start endpoint
  - `POST /api/auth/passkey/login/start` on both domains -> 200

### Conclusion
- Legacy passkey migration state is converged.
- Backfill is idempotent in production.
- Passkey login start path is healthy after migration.

Evidence document:
- `evidence/passkey-backfill-production-closure-20260816.md`

---

## PR Paste Option A (Concise/Executive Tone)

### 3-line summary
1. Production passkey backfill verification is complete; both production domains are healthy (`/api/health` = 200).
2. Backfill apply and idempotency re-check both converged (`scanned=1 inserted=0 updated=0 unchanged=1 skipped=0`).
3. Passkey login start endpoint is healthy on both domains (`POST /api/auth/passkey/login/start` = 200).

### Detailed comment (with validation logs)
Production passkey multi-device backfill has been validated and closed.

- Health checks
  - `https://xn--114-2p7l635dz3bh5j.com/api/health` -> `HTTP:200`
  - `https://metanova1004.com/api/health` -> `HTTP:200`
- Backfill apply
  - Command: `python scripts/backfill_passkey_credentials.py`
  - Result: `PASSKEY_BACKFILL scanned=1 inserted=0 updated=0 unchanged=1 skipped=0`
- Idempotency re-check
  - Command: `python scripts/backfill_passkey_credentials.py --dry-run`
  - Result: `PASSKEY_BACKFILL scanned=1 inserted=0 updated=0 unchanged=1 skipped=0`
- Passkey start endpoint
  - `POST https://xn--114-2p7l635dz3bh5j.com/api/auth/passkey/login/start` -> `HTTP:200`
  - `POST https://metanova1004.com/api/auth/passkey/login/start` -> `HTTP:200`

Validation log snapshot:

```text
=== RUN: health-xn
HTTP:200
=== RUN: health-metanova
HTTP:200
=== RUN: backfill-apply
PASSKEY_BACKFILL scanned=1 inserted=0 updated=0 unchanged=1 skipped=0
=== RUN: backfill-dryrun
PASSKEY_BACKFILL scanned=1 inserted=0 updated=0 unchanged=1 skipped=0
=== RUN: passkey-start-xn
HTTP:200
=== RUN: passkey-start-metanova
HTTP:200
```

Evidence: `evidence/passkey-backfill-production-closure-20260816.md`

---

## PR Paste Option B (Operational/Checklist Tone)

### 3-line summary
1. 운영 게이트 1(Health): 양 도메인 `/api/health` 200 통과.
2. 운영 게이트 2(Backfill + 멱등성): apply/dry-run 모두 `inserted=0 updated=0 unchanged=1`로 수렴 확인.
3. 운영 게이트 3(Auth API): 패스키 시작 엔드포인트 양 도메인 200 확인, 종료 기준 충족.

### Detailed comment (with validation logs)
Passkey legacy -> credential table 전환 백필에 대해 운영 검증을 체크리스트 기준으로 완료했습니다.

- Gate 1: Runtime health
  - `curl https://xn--114-2p7l635dz3bh5j.com/api/health` -> `200`
  - `curl https://metanova1004.com/api/health` -> `200`
- Gate 2: Backfill apply + idempotency
  - `python scripts/backfill_passkey_credentials.py`
    - `PASSKEY_BACKFILL scanned=1 inserted=0 updated=0 unchanged=1 skipped=0`
  - `python scripts/backfill_passkey_credentials.py --dry-run`
    - `PASSKEY_BACKFILL scanned=1 inserted=0 updated=0 unchanged=1 skipped=0`
- Gate 3: Passkey login/start health
  - `POST /api/auth/passkey/login/start` (xn domain) -> `200`
  - `POST /api/auth/passkey/login/start` (metanova domain) -> `200`

실행 로그:

```text
=== RUN: health-xn
HTTP:200
=== RUN: health-metanova
HTTP:200
=== RUN: backfill-apply
PASSKEY_BACKFILL scanned=1 inserted=0 updated=0 unchanged=1 skipped=0
=== RUN: backfill-dryrun
PASSKEY_BACKFILL scanned=1 inserted=0 updated=0 unchanged=1 skipped=0
=== RUN: passkey-start-xn
HTTP:200
=== RUN: passkey-start-metanova
HTTP:200
```

판정: **완료됨** (운영 백필 수렴 + 멱등성 + 인증 API 정상)

Evidence: `evidence/passkey-backfill-production-closure-20260816.md`
