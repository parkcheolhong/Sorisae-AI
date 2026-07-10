# 사용자 언어 우선 정책 (User Language Policy)

> **최우선 규칙:** 채팅 · 대면통역 · VoIP · 일반통화 · 공지 · 광고 · 설정 등 **앱 내 모든 기능**에서
> 표시(UI)와 발화(TTS)는 **무조건 사용자 지정 언어(`preferred_language` → `uiLang`)** 기준으로 일관되어야 한다.

## 사용자(유저) 정의

**사용자** = 실구매·실사용 고객. 운영·개발 **관계자**와 구분한다.

| 구분 | 대상 | 화면에 보이는 것 |
|------|------|------------------|
| **유저** | 회원가입·결제·통화·채팅 고객 | 번역된 대화·상태(「번역 중…」「나/상대」)만 |
| **관계자** | 운영·개발·QA | 언어 코드·call_id·감사 로그·파이프라인 메타 |

관계자 정보는 **웹 관리 대시보드** 또는 앱 **설정 → 관계자 로그**(버전 7회 탭 잠금 해제, `__DEV__` 즉시)에서만 확인한다.

## 양방향 통역 (기본 규칙)

설정에서 **수동 언어·국가 전환하기 전까지**:

1. **회원가입 시 등록된 `preferred_language` + 국가**가 SSOT이다.
2. **발신자 ↔ 수신자** 각자의 등록 언어로 자동 소통한다 (채팅·VoIP·PSTN 착신·공지·광고 포함).
3. 사용자는 통화/채팅 화면에서 **언어 이름·코드·KO→JA 배지**를 보지 않는다.
4. `fromLang` / `toLang` 은 **번역 파이프라인 내부** 전용이다.

수동 전환은 **설정 탭 프로필**(국가·통역 언어)에서만 허용한다.

## SSOT 모듈

| 용도 | API | 파일 |
|------|-----|------|
| UI 표시 언어 | `getUserDisplayLang()` = `getUiLang()` | `src/features/i18n/userLanguagePolicy.ts` |
| UI 문자열 사전 | `getDisplayUiText()` | `src/features/i18n/displayLanguage.ts` |
| 기능 화면(오프라인 4언어) | `getFeatureUiText()` | `src/features/i18n/featureUiCatalog.ts` |
| 발화(TTS) 출력 언어 | `resolveUserOutputLang(preferred_language)` | `src/features/language/languageCatalog.ts` |
| 관계자 표면 | `isOperatorSurfaceVisible()` | `src/features/operator/operatorAccess.ts` |
| 전역 패치 | `Text` · `TextInput.placeholder` · `Alert` · `ToastAndroid` | `App.tsx` + `uiI18n.ts` |

## 유저 화면 표기 (VoIP · 채팅 · 일반통화)

| 항목 | 규칙 |
|------|------|
| **이름/닉네임** | 항상 **국기 + 이름** (`formatFlagPrefixedName`) |
| **국기 출처** | `country_code` 우선, 없으면 `preferred_language` → 대표 국가 |
| **언어쌍** | **모든 설치 사용자** 화면에 `BidirectionalLanguagePairBadge` (예: `English ⇄ 日本語`) |

### 언어쌍 표시 위치 (전역)

| 화면 | 위치 |
|------|------|
| VoIP 로비 | 통화 레일 상단 |
| VoIP 통화 중 | 헤더 + 실시간 채팅 섹션 |
| 채팅방 | AI 번역 칩 아래 |
| 일반통화(PSTN) | 여행 예약 · 일반통화 패널 |
| 설정 → 관계자 로그 | pipeline 메타와 함께 |

SSOT: `src/features/i18n/userDisplayIdentity.ts` · `src/features/i18n/BidirectionalLanguagePairBadge.tsx`

## 금지 (유저 화면)

- `fromLang` / `toLang` 을 **UI 라벨**에 직접 사용
- 원시 언어 코드 (`KO`, `ja`, `preferred_language` uppercase)
- `[통번역 PSTN/TRANSLATE]` 등 **개발 상태 접두어**
- 백엔드/개발 용어 (`백엔드 프로필`, `call_id`, `event_type`, `auto_relay`)
- 채팅방 **언어 선택 바**(⇄ 한국어 English)
- VoIP 레일 **통역 지정 언어** 카드(설정 프로필이 SSOT)

## 허용

| 맥락 | 허용 |
|------|------|
| 설정 프로필 | 국가·통역 언어 **이름**(한국어, English…) — 코드 없음 |
| 번역 파이프라인 | `fromLang` / `toLang` 내부 사용 |
| 관계자 로그 | `fromLang→toLang`, call_id, audit 이벤트 |

## 기능별 적용

| 기능 | 유저 표시 | 발화 |
|------|-----------|------|
| 채팅 | 번역본 우선, 언어 바 없음 | `viewer_translation` → `getUserDisplayLang()` |
| 대면통역 | 「나 / 상대」 라벨만 | 상대에게 들리는 `targetLang` TTS |
| VoIP | `getFeatureUiText()`, 감사 로그는 `__DEV__`만 | `resolveVoipTtsLocale` |
| 일반통화(PSTN) | 「번역 중…」「내/상대 말하기」 | 시스템 다이얼러 |
| 공지/푸시/광고 | `userLanguage={getUiLang()}` | 동일 |

## 다운로드·가입 시 언어

| 단계 | 동작 |
|------|------|
| **앱 설치 직후** | `resolveBootstrapUiLang()` — 단말 로케일/국가 → `uiLang` |
| **회원가입** | `signupGuideCatalog` — 한·영·일·중 오프라인 안내 |
| **설정 탭** | `DOWNLOAD_LANGUAGE_OPTIONS` + 프로필 국가·언어 |
| **국가 변경** | `resolveLangFromCountryOrEnglish` → 51 LANGS 자국어 |

## 한국어 플래시 방지 (3단계)

| 단계 | 방법 | 대상 |
|------|------|------|
| 1 | `resolveBootstrapUiLang()` | 전체 첫 프레임 |
| 2 | `featureUiCatalog` / `bundledManuals` / `signupGuideCatalog` (ko·en·ja·zh) | VoIP·채팅·PSTN·가입 |
| 3 | `appUiText` en 폴백 + `translateUiSync` | 나머지 47개 LANG |

## 검증 체크리스트

1. 일본 가입 유저 → 채팅·VoIP·PSTN·홍보 전부 일본어(한국어 플래시 없음)
2. 통화 중 화면에 `KO`, `ja`, `fromLang` 문자열 없음
3. 채팅방에 언어 선택 바 없음
4. 설정 프로필에서만 언어·국가 변경 가능
5. 관계자만 설정 하단「관계자 로그」에서 pipeline·audit 확인
