# B-2-6 VoIP 통화 시그널링 E2E (2026-06-13 최종)

## 기기 구성 (확인됨)

| 역할 | adb | 모델 | serial |
|------|-----|------|--------|
| 탭 (발신) | `R83W70QY11H` | SM-T225N | R83W70QY11H |
| S10 (착신) | `172.30.1.19:5555` | **SM-G973N** | **R39M20E0MLA** |

> 이전 `10.92.246.175:5555`는 탭과 **동일 기기**였음. `172.30.1.19`가 실제 별도 S10.

## 계정

| 역할 | 이메일 | user_id | voice_id |
|------|--------|---------|----------|
| 발신 | `119cash@naver.com` | 1 | `nado-000001` |
| 착신(친구) | `burumi69@gmail.com` | 226 | `nado-000226` |

## 완료 항목

### 1. 백엔드 `/calls/{id}/accept` — **추가·검증 200**
- `nadotongryoksa_voip_router.py`에 `POST /api/v1/voip/calls/{call_id}/accept` 등록
- `119cash` initiate → `burumi69` accept E2E 확인

### 2. 서버 시그널링 2회 — **PASS**
- nginx `wss://…/signal` offer→answer 릴레이 2/2

### 3. Dockerfile RapidOCR 영구화 — **완료**
- `docker compose build backend` + `--force-recreate`
- 재생성 컨테이너: `from rapidocr_onnxruntime import RapidOCR` ✅

## 실기기 logcat 게이트 — **r5 Round1 시그널 PASS / WebRTC 미완 (2026-06-13)**

| Round | 계정 방향 | Offer (탭) | Incoming (S10) | Answer | connected | 비고 |
|-------|-----------|------------|----------------|--------|-----------|------|
| r5-1 | ✅ 119cash→burumi | ✅ ×3 | ✅ ×3 (`nado-000001`) | ❌ | ❌ | S10 **받기** adb 탭 실패 |
| r5-2 | — | ❌ | ❌ | ❌ | ❌ | 장시간 대기 중 로그 비움 |
| r2 (이전) | ❌ 역방향 | ✅ | ✅ | ✅ | ✅ | 데모계정→119cash |

**r5-1 증거** (`verify_r5_tab_r1.log`, `verify_r5_s10_r1.log`):
- 딥링크 `action=validation&callee_voice_id=nado-000226` 정상 파싱
- `VOIP_VALIDATION_AUTO_CALL_DEEPLINK` → `callee_user_id:226`, `caller_id:119cash@naver.com`
- 탭 `VOIP_FRIEND_CALL_SUCCESS` + `[VoIP] Offer sent`
- S10 `VOIP_INCOMING_CALL_RECEIVED` (`caller_voice_id:nado-000001`)

**수동 마무리 (30초 ×2)**

1. S10 `burumi69` / 탭 `119cash` 포그라운드 유지
2. 탭에서 친구 **박** 보이스톡 (또는 딥링크):
   `adb -s R83W70QY11H shell "am start -a android.intent.action.VIEW -d 'worldlingo://voip/open?action=validation&callee_voice_id=nado-000226'"`
3. S10 화면에서 **수신 보이스톡 받기** 직접 탭 ×2
4. logcat 게이트: `Answer applied` · `Connection state: connected` (양쪽)

## 판정

| 항목 | 상태 |
|------|------|
| B-2-6 서버 시그널링 2회 | ✅ PASS |
| B-2-6 accept REST | ✅ PASS (신규) |
| B-2-6 실기기 2대 WebRTC logcat | ⏳ 수동 2회 필요 |
| RapidOCR 이미지 영구화 | ✅ PASS |

## 증거 파일

- `round*_tab.log`, `round*_s10.log`, `round_final_*.log`
- `s10_ui_login.xml`
