# WorldLinco build35 · Git/GitHub 정합성 정리 (2026-06-13)

## 기준 상태 (Canonical)

| 항목 | 값 |
|------|-----|
| 앱 버전 | `1.0.25` / `versionCode=35` |
| 패키지 | `com.parkcheolhong.worldlinco` |
| API | `https://metanova1004.com` |
| App.tsx | ~10,000줄 풀기능 (5레일 UI) |
| 백엔드 라우터 | `voip` + `nadotongryoksa_friends` + `nadotongryoksa_chat` + `mobile_image_translation` |

프로덕션 검증 (백엔드 재시작 후):
- `/api/friends/discovery/nearby` → **401** (라우트 존재, 인증 필요)
- `/api/users/1/friends` → **401**
- `/api/mobile/chat/rooms` → **401**
- 탭 채팅 레일: **404 문구 사라짐**, 친구·대화방 목록 표시

---

## 정리 전 문제

1. **스테이징 ≠ 작업트리** (`MM`): `main.py`, `app.json`, `friends.ts` 등 index와 디스크 불일치
2. **스테이징된 `main.py`**: friends/chat 라우터 **삭제** + autonomous만 추가 (배포 시 404 재발 위험)
3. **untracked**: `nadotongryoksa_friends_router.py`, `nadotongryoksa_chat_router.py`, 채팅/지도 친구 TSX
4. **GitHub `origin/main`**: 모바일 v1.0.15, App.tsx 3,467줄, friends/chat 라우터 없음 (로컬과 211커밋 분기)

---

## 정리 조치 (이 커밋)

### 백엔드
- `backend/main.py` — 작업트리 기준으로 index 동기화 (voip + friends + chat + OCR)
- `backend/marketplace/nadotongryoksa_friends_router.py` — 신규 추적 (km 제한 optional)
- `backend/marketplace/nadotongryoksa_chat_router.py` — 신규 추적
- `backend/tests/test_nadotongryoksa_*_contract.py` — 계약 테스트 추적

### 모바일
- `App.tsx` — km 제한 없이 UI 문구
- `app.json` — 1.0.25 / build 35
- `src/api/friends.ts` — radius_m 미전송 = 무제한 조회
- `FriendMapDiscoveryScreen.tsx`, `useAutoNearbyFriendDiscovery.ts` — 추적
- `src/features/chat/*` — 채팅 API/화면 추적

### 증거
- `evidence/mobile-restore-functional-verify-20260613/` — 배포 전후 캡처·API 검증
- `evidence/mobile-morning-downgrade-session-20260613/ROOT_CAUSE_AND_RESTORE.md`

### 제외 (커밋 안 함)
- `mobile_voip_*.xml/png/log` — 실기기 디버그 산출물
- `.gradle-tmp/`, `builds/`, `coverage/` — 빌드 캐시
- `src/features/chat/dist/` — 컴파일 산출물

---

## 스테이징/미커밋 diff (정리 후)

| 파일 | HEAD 대비 | 비고 |
|------|-----------|------|
| `backend/main.py` | 스테이징 완료 | friends/chat/voip/OCR 마운트 |
| `app.json` | 스테이징 완료 | 1.0.25 / 35 |
| `App.tsx` | 스테이징 완료 | 1줄: km 제한 문구 |
| `friends.ts` | 스테이징 완료 | unlimited nearby |
| `types.ts` | 스테이징 완료 | AcceptFriendRequestResponse 등 |

**작업트리 = index** (MM 해소)

---

## `origin/main` 머지 시 충돌 예상 (High)

| 파일 | 이유 |
|------|------|
| `backend/main.py` | 양쪽 대규모 수정 (라우터 마운트 블록) |
| `apps/mobile-nadotongryoksa/App.tsx` | GitHub 3.4k줄 vs 로컬 10k줄 |
| `apps/mobile-nadotongryoksa/app.json` | 버전·패키지명 전면 변경 |
| `backend/auth_router.py` | 보안/인증 PR 양쪽 수정 |
| `backend/llm/orchestrator.py` | autonomous orchestrator PR |
| `docker-compose.yml` | 환경/서비스 설정 |
| `frontend/frontend/package.json` | dependabot bump |

**권장 머지 순서**: WorldLinco 복원 브랜치를 `main`에 머지할 때 `main.py` 라우터 블록·`App.tsx`·`app.json`을 수동 검토.

---

## 브랜치

- 작업 브랜치: `gpu-llm-server-awq-20260427`
- 푸시 대상: `origin/gpu-llm-server-awq-20260427`
- `origin/main`과는 별도 — main 동기화는 후속 PR 필요
