# 기능별 로그/터미널 분리 (Feature-isolated logs)

마스터 기술서 [`docs/worldlinco-v2/FEATURE_SEPARATION_MASTER_SPEC.md`](../../docs/worldlinco-v2/FEATURE_SEPARATION_MASTER_SPEC.md) Phase 6.

사용자는 한 번에 한 기능만 사용하므로, 디버깅·검증도 기능별로 **로그 스트림을 분리**해서 본다.

## A. 로그 스트림 분리

### 클라이언트(logcat)
```powershell
pwsh -File scripts/logs/tail_feature_logcat.ps1 -Feature face      # 대면 통역
pwsh -File scripts/logs/tail_feature_logcat.ps1 -Feature sorisae   # 소리새AI
pwsh -File scripts/logs/tail_feature_logcat.ps1 -Feature voip      # VOIP
pwsh -File scripts/logs/tail_feature_logcat.ps1 -Feature chat      # 채팅
pwsh -File scripts/logs/tail_feature_logcat.ps1 -Feature phone     # 일반전화/예약
pwsh -File scripts/logs/tail_feature_logcat.ps1 -Feature song      # 노래번역
```

### 백엔드(docker)
```powershell
pwsh -File scripts/logs/tail_feature_backend.ps1 -Feature voip
pwsh -File scripts/logs/tail_feature_backend.ps1 -Feature bridge -Since 10m   # 미디어 브리지 통역
pwsh -File scripts/logs/tail_feature_backend.ps1 -Feature face
```

분리 기준: 콘솔 태그(`[FACE_CONVERSATION]`, `[VoIP]`, `[bridge]` 등) + correlation 접두
(`face.interpret`, `voip.voice_relay`, `song.translate` …, `src/features/correlation/correlationId.ts` `FEATURE_IDS`).

권장: 기능별로 **별도 터미널 창** 하나씩 띄워 두고, 해당 기능 테스트 시 그 터미널만 본다.

## B. 프로세스 분리 옵션

현재 백엔드는 단일 컨테이너(`devanalysis114-backend`)에서 모든 기능 라우터를 서빙한다.
기능별 프로세스/스케일 분리가 필요해지면(부하·격리), V2 `backend/communication/` Delivery
어댑터 승격 시점에 다음을 분리 배포한다(마스터 기술서 §2, ROADMAP 연계):

- VOIP/시그널링: `nadotongryoksa_voip_router` + `voip/media_bridge`
- 통역 hot path: `POST /api/llm/voice-translate` (face/voip 공유 코어)
- 채팅: `nadotongryoksa_chat_router`
- 소리새/오케스트레이션: `voice/friend-chat`, `voice/orchestrate`

분리 전까지는 단일 컨테이너 + 위 로그 필터로 기능 단위 관측을 확보한다.
(hot path 계약 동결 원칙 — 분리는 배포 토폴로지만 바꾸고 엔드포인트 계약은 유지.)
