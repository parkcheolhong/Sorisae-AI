# WorldLinco · 소리새 구현 상태 SSOT (2026-07-02)

> 작업 착오 방지용 living document.

## 1. 성숙도 요약

| 영역 | 상태 | 비고 |
|------|------|------|
| VoIP / 대면 통역 | 🟢 | tuning SSOT + media_bridge |
| 추천(WL) / 영업(WS) / 정산 | 🟢 | 현지 매출 전액 + KR 폴백 (시뮬 이체) |
| 모바일 결제 | 🟡 | verify 훅 OK, 실 PG·현지 SKU 환경 의존 |
| Admin UI | 🟢 | WorldLinco 7패널 좌측 레일 런처 |
| 청구 정책 (무료 베타) | 🟢 | Phase A 서버 게이트 적용 |
| 소리새 companion | 🟢 | build **296** freeze · Phase C **17/31 자동 마감** (수동 14) |
| JSON SSOT ledger | 🟢 | PostgreSQL `worldlinco_json_documents` (+ file fallback) |

## 2. 정산·영업 SSOT

| 채널 | 코드 | 사용자 혜택 | 정산 |
|------|------|------------|------|
| 사용자 추천 | `WL` | 첫 결제 3% 할인 | 없음 |
| 영업 QR | `WS` | 할인 없음 | 수수료 30%/10% (장부) |
| 현지 매출 | — | — | 결제 전액 → 현지 통장, 없으면 **KR 폴백** |

**저장소:** PostgreSQL `worldlinco_json_documents` (키: `worldlinco_referrals`, `worldlinco_sales_commission`)  
**파일 미러(선택):** `.runtime/*.json` · `WORLDLINCO_JSON_STORE_FILE_MIRROR=1`

**핵심 모듈:** `worldlinco_json_store.py`, `worldlinco_sales_commission.py`, `worldlinco_referral.py`

## 3. Phase A ✅ (2026-07-02)

- confirm/callback 시점 정산 · billing policy license gate
- 테스트: `backend/tests/test_worldlinco_phase_a.py`

## 4. Phase C — 소리새 ✅ (자동 마감 2026-07-02)

- ✅ FAB + 전용 창 → `SorisaeCompanionFab.tsx`, `SorisaeCompanionWindow.tsx`
- ✅ 음성 파이프 + 웨이크워드 → `useSorisaeVoicePipeline.ts`
- ✅ friend-chat ↔ `trip_sessions` / `conversation_turns`
- ✅ **체크리스트 17/31 자동 PASS** → `SORISAE_LIVE_VERIFICATION_CHECKLIST.md` · `scripts/close_sorisae_phase_c_checklist.py`
- ✅ build **296** freeze · section SSOT lock · ADB probe `segment_200=True`
- 🔶 수동 14항: A2/A4–A7 일부, B3, C1–C4, D3 Admin UI, E1/E2 VoIP·대면

## 5. 알려진 부채

1. ~~JSON ledger multi-instance~~ → **PostgreSQL SSOT**
2. ~~Admin WorldLinco launcherHidden~~ → **레일 7패널 노출**
3. 지역 관리자 PUT UI 미연결
4. Telemetry 코드 중복 (router + admin_router)
5. CountryTourismPromoCard dead code
6. Deeplink scheme worldlinco vs worldlingo

## 6. 테스트

```bash
pytest backend/tests/test_worldlinco_json_store.py \
       backend/tests/test_worldlinco_sales_commission.py \
       backend/tests/test_worldlinco_local_revenue_settlement.py \
       backend/tests/test_worldlinco_regional_manager.py \
       backend/tests/test_worldlinco_referral_discount.py \
       backend/tests/test_worldlinco_phase_a.py \
       tests/test_worldlinco_billing_policy.py -q
```

## 7. 소리새 LLM 라우팅 (vLLM 분리)

| 용도 | 포트 | 모델 ID (`/v1/models`) | env |
|------|------|------------------------|-----|
| 통역·오케스트레이터 | **8008** | `Qwen/Qwen2.5-Coder-14B-Instruct-AWQ` | `OLLAMA_BASE`, `LLM_TRANSLATE_MODEL` |
| **소리새 friend-chat** | **8009** | `Qwen/Qwen3-8B-AWQ` | `LLM_VOICE_FRIEND_BASE_URL`, `LLM_MODEL_VOICE_CHAT` |

`LLM_MODEL_VOICE_CHAT` 은 **반드시** `:8009` vLLM `--served-model-name` 과 동일해야 한다 (alias `qwen3:8b` 사용 금지).

```powershell
.\scripts\start_vllm_sorisae_8b.ps1
docker compose up -d --force-recreate backend   # restart 만으로는 env 미반영
python scripts/run_sorisae_friend_chat_probe.py --base-url http://127.0.0.1:8000
```

Compose: `gpu-llm-server/docker-compose.vllm-sorisae-8b.yml` · env SSOT: `scripts/vllm-sorisae-8b.env`

## 8. 환경 플래그

| 변수 | 기본 | 의미 |
|------|------|------|
| `WORLDLINCO_JSON_STORE_BACKEND` | auto | `file` \| `postgres` \| DB 가용 시 postgres |
| `WORLDLINCO_JSON_STORE_FILE_MIRROR` | off | postgres 사용 시 `.runtime` 파일 동기화 |
| `WORLDLINCO_SALES_PAYOUT_ALLOW_SIMULATED` | true | 은행 이체 시뮬 |
| `MARKETPLACE_BILLING_ALLOW_SIMULATED_CHECKOUT` | true | Stripe sim |
| `MARKETPLACE_BILLING_ALLOW_SIMULATED_VERIFY` | false | 모바일 verify |
| `SORISAE_CENTRAL_ENABLED` | false (local) | orchestrator only |

## 9. APK

- build **296**, v1.0.233 (`app.json`) — 소리새 섹션 freeze · Phase C 자동 마감
- WS deeplink · 정산 — 백엔드 pytest ✅ · Admin UI(D3)·VoIP(E1) 수동만 남음

## 10. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-02 | Phase A: confirm 정산 + billing gate |
| 2026-07-02 | Phase C: useVoiceCaptureLoop 분리, APK 279 |
| 2026-07-02 | 소리새 vLLM :8009 + probe gate |
| 2026-07-02 | build 296 freeze + Phase C 체크리스트 17항 자동 마감 |
