# WorldLinco build35 기능별 실검증 (2026-06-13)

**기기:** SM-T225N 탭 `R83W70QY11H` (+ S10 `172.30.1.19:5555` 동일 build35 확인)  
**APK:** `v1.0.25` · `versionCode=35` · `com.parkcheolhong.worldlinco`  
**API 서버:** `https://metanova1004.com` (app.json 고정)

## 결론 (한 줄)

**앱 UI/코드 원복은 됐지만, 친구·채팅·VoIP·이미지번역은 프로덕션 백엔드 라우터 미배포로 404 → 사용자 말씀대로 “연결 안 됨”이 맞습니다.**

---

## 기능별 결과

| 기능 | UI/화면 | 서버 연결 | 스크린샷 |
|------|---------|-----------|----------|
| 앱 기동·로그인 | ✅ build35, `119cash@naver.com` 로그인 | ✅ `/api/health` 200 | `01_launch.png`, `01_home_translate_build35.png` |
| 번역 홈 (대면 통역) | ✅ GPS·언어 선택·입력 UI 정상 | ✅ (기본 헬스 OK) | `01_launch.png` |
| 채팅 레일 | ✅ 채팅+친구 허브 UI 표시 | ❌ **친구 목록 조회 실패: 404** | `02b_chat_rail.png`, `02_chat_rail_404.png` |
| 친구 폴더 | ✅ 내 친구 목록 UI | ❌ **보낸 친구 요청 조회 실패: 404** | `04_friend_folder_404.png` |
| 주변 친구 자동감지 | ✅ UI 문구 **"km 제한 없이"** (build35 반영) | ❌ nearby API 404 (연동 불가) | `02b_chat_rail.png` |
| VoIP 레일 | ✅ 채팅 중심 통역 허브·요금제 UI | ❌ presence WS **close 1006**, pending call **404** | `03_voip_after_tap.png` |
| 노래 레일 | ✅ 노래 전용 모드 전체 UI | ⚠️ 미검증(결제/번역 API 별도) | `06_song_from_home.png` |
| 예약/주변 레일 | ✅ 주변검색·여행예약 UI | ⚠️ 주변검색 API 미호출 검증 | `07_booking_from_home.png` |

---

## 프로덕션 API 직접 확인

```
GET /api/health                              → 200
GET /api/friends/discovery/nearby?lat=...    → 404
GET /api/mobile/chat/rooms                   → 404
GET /api/users/1/friends                     → 404
GET /api/mobile/image-translation            → 404
GET /api/v1/voip/presence                    → 404
```

---

## logcat (앱 런타임)

```
친구/채팅: (화면) "친구 목록 조회 실패: 404"
VoIP pending_call_poll: status=404
VoIP presence: VOIP_PRESENCE_ERROR → close code 1006 (retry loop)
api_base: https://metanova1004.com
```

---

## 원인

로컬 `backend/main.py`에는 아래 라우터 마운트가 **추가됨** (아직 프로덕션 미배포 추정):

- `nadotongryoksa_friends_router` → `/api/users/.../friends`, `/api/friends/discovery/nearby`
- `nadotongryoksa_chat_router` → `/api/mobile/chat/*`
- `mobile_image_translation_router` → `/api/mobile/image-translation`

테스트 픽스처에는 있었으나 운영 `main.py`에 없어서, **build26/build35 APK를 아무리 올려도** 친구·채팅은 404입니다.

---

## 다음 조치 (백엔드 배포 후 재검증)

1. `main.py` 라우터 마운트 포함 버전을 `metanova1004.com`에 배포·재시작
2. 위 API 404 → 200/401 전환 확인
3. 탭에서 채팅 레일·친구 폴더 재캡처 (404 문구 사라져야 함)
4. VoIP presence 1006은 라우터 배포 후에도 WSS/프록시 설정 추가 점검 필요

---

## 증거 파일 위치

`evidence/mobile-restore-functional-verify-20260613/`
