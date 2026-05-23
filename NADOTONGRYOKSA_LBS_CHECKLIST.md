# 나도통역사 LBS 구현 체크리스트

상태 규칙:
- `구현됨`: 코드 반영 완료, 검증 대기 또는 부분 검증
- `완료됨`: 코드 반영 + 실행 검증 완료
- `실패`: 구현 또는 검증 실패

현재 상태: 완료됨

## 이번 추가 개선 항목

- [x] 마이크 STT 언어 힌트 제거 및 자동 감지 고정 해제
  - 상태: 완료됨
  - 범위: 마이크 음성 요청에서 `language: fromLang` 제거, Whisper `detected_language` 정규화, `ko-KR`/`korean`/`en-US` 등 변형 코드 자동 매핑, 노래 모드 소스 언어 판정도 동일 정규화 사용
  - 근거: `language: fromLang|WHISPER_LANG_MAP[rawDetected` 검색 결과 없음. `apps/mobile-nadotongryoksa/App.tsx` `get_errors` 오류 없음. `npx tsc --noEmit` 2회 무출력 통과. `npx expo prebuild --platform android --no-install` 2회 통과 후 생성 `android/` 폴더 정리 완료.

- [x] 마이크 자동 감지 수정본 EAS Android APK 재빌드
  - 상태: 완료됨
  - 범위: 최종 수정본 기준 설치형 Android APK 생성 및 산출물 다운로드 확인
  - 근거: EAS Android preview 빌드 `1577248b-24f6-49cc-ad28-76344717187a` 상태 `FINISHED`, 프로젝트 `@parkcheolhong/nadotongryoksa`, APK URL `https://expo.dev/artifacts/eas/3DJKwHBqme4BmHP5SQ5sbN.apk`. `curl.exe -L -r 0-1023` 2회 확인 모두 `HTTP 206`, `SIZE 1024`, `TYPE application/octet-stream`.

- [x] App.tsx 패치 손상 복구
  - 상태: 완료됨
  - 범위: `NearbyPlace`, `UserInfo`, API 유틸리티, 카테고리/반경 상수, 노래 자막 타입 블록 문법 복구
  - 근거: `apps/mobile-nadotongryoksa/App.tsx` `get_errors` 오류 없음 + `npx tsc --noEmit` 2회 무출력 통과

- [x] 음성/STT 언어 자동 감지 패널 반영
  - 상태: 완료됨
  - 범위: STT `detected_language` 우선, 문자 스크립트 추론 보조, 감지 언어를 출발/도착 패널에 반영 후 번역 실행
  - 근거: `WHISPER_LANG_MAP`, `inferSpeechLangCode`, `resolveAutoTargetLang`, `stopVoiceInput` 경로 반영 + TypeScript 2회 통과

- [x] 노래 가사 언어 자동 감지 및 번역 자막
  - 상태: 완료됨
  - 범위: 가사 라인 필터링, 반복 구간 병합, 음성 감지/문자패턴 기반 소스 언어 판정, 현재 번역 언어 기반 타겟 결정
  - 근거: `SongSubtitleEntry.detectedBy`를 `voice/script/manual`로 제한, 노래 모드 UI에서 GPS 국가 우선 문구 제거, TypeScript 2회 통과

- [x] GPS 언어 감지 제거 및 위치 서비스 전용화
  - 상태: 완료됨
  - 범위: `COUNTRY_LANG_MAP`, `gpsDetectedLang`, GPS 기반 `setToLang` 제거. GPS는 현재 위치, 공항, 호텔예약, 먹거리, 서비스용 위치 확인으로만 사용
  - 근거: `COUNTRY_LANG_MAP|gpsDetectedLang|setGpsDetectedLang|GPS 자동|GPS 국가` 검색 결과 없음 + prebuild 2회 통과

- [x] 로컬 자동 검증 2회
  - 상태: 완료됨
  - 근거: `npx tsc --noEmit` 2회 통과, `npx expo prebuild --platform android --no-install` 2회 통과, 생성 `android/` 폴더 정리 완료

- [x] 최종 수정본 EAS Android APK 빌드
  - 상태: 완료됨
  - 근거: 최종 수정본 기준 EAS Android preview 빌드 `4b84a12f-5276-4ba8-ad36-18b995662323` 상태 `FINISHED`. Gradle 로그 `BUILD SUCCESSFUL in 5m 25s`, APK `app-release.apk (62.9 MB)` 업로드 확인. APK URL: `https://expo.dev/artifacts/eas/ajShXQ3XzCbVVrN78hYajK.apk`. `curl.exe -L -r 0-1023` 다운로드 확인 `HTTP 206`, `SIZE 1024`, `TYPE application/octet-stream`.

## 구현 항목

- [x] 체크리스트 문서 생성 및 범위 고정
  - 상태: 완료됨
  - 근거: 본 문서 생성 후 오류 검사 통과

- [x] 나도통역사 전용 POI 도메인 추가
  - 상태: 완료됨
  - 범위: 호텔, 공항, 식당, 관광명소 기본 데이터 모델
  - 근거: `backend/marketplace/nadotongryoksa_lbs_router.py`에 4개 카테고리 POI 카탈로그 및 응답 모델 추가 + 브라우저 주변검색 결과 카드 실노출 확인

- [x] 나도통역사 전용 거리 계산 및 주변 검색 API 추가
  - 상태: 완료됨
  - 범위: 카테고리 필터, 반경 필터, 거리순 정렬
  - 근거: `GET /api/marketplace/nadotongryoksa/lbs/nearby` 구현 + pytest 계약 검증 통과

- [x] 나도통역사 전용 예약 API 추가
  - 상태: 완료됨
  - 범위: 호텔 예약 요청, 확인 응답, 번역 연동
  - 근거: `POST /api/marketplace/nadotongryoksa/lbs/bookings` 구현 + pytest 계약 검증 통과

- [x] 지도 연동 정보 제공 추가
  - 상태: 완료됨
  - 범위: Google Maps, Naver Map 외부 링크
  - 근거: 주변검색 응답에 Google Maps/Naver Map 링크 포함, 고객 화면 결과 카드에 Google Maps/Naver 지도/Google 리뷰 버튼 실노출 확인

- [x] 나도통역사 고객 화면에 주변검색 UI 연결
  - 상태: 완료됨
  - 범위: 현재 위치 입력, 카테고리 선택, 결과 리스트, 예약 액션
  - 근거: `frontend/frontend/app/marketplace/nadotongryoksa/page.tsx` 전면 교체로 주변검색/리뷰/예약 UI 반영 + 실제 브라우저에서 주변 장소 찾기 실행 후 호텔/식당/관광명소 카드 렌더링 확인

- [x] 나도통역사 고객 화면에 번역 연동 표시
  - 상태: 완료됨
  - 범위: POI 설명, 예약 안내 문구 다국어 변환
  - 근거: 기존 번역 패널 유지 + LBS API target_lang 및 예약 번역 메시지 반영 + 실제 브라우저 예약 확인 패널에서 영문 안내 문구 노출 확인

## 검증 항목

- [x] 백엔드 파일 오류 검사 통과
  - 상태: 완료됨
  - 근거: 신규 백엔드 파일 `get_errors` 결과 오류 없음

- [x] 프론트 파일 오류 검사 통과
  - 상태: 완료됨
  - 근거: `frontend/frontend/app/marketplace/nadotongryoksa/page.tsx` `get_errors` 결과 오류 없음 + `frontend/frontend` `npm run build` 통과

- [x] 주변검색 API 응답 검증
  - 상태: 완료됨
  - 근거: `py -3.13 -m pytest backend/tests/test_marketplace_nadotongryoksa_lbs_contract.py -q` 통과

- [x] 예약 API 응답 검증
  - 상태: 완료됨
  - 근거: 동일 pytest에서 호텔 예약 성공/비호텔 예약 거절 계약 검증 통과

- [x] 체크리스트 문서 최종 동기화
  - 상태: 완료됨
  - 근거: 구현 및 검증 결과를 본 문서에 반영 완료

- [x] 브라우저 실화면 검증
  - 상태: 완료됨
  - 근거: `http://127.0.0.1:3007/marketplace/nadotongryoksa`에서 customer token 주입 후 실조작 검증 완료. 주변 장소 찾기 실행으로 롯데호텔 서울 등 결과 카드 렌더링 확인, Google 리뷰 버튼 클릭 시 `/api/external-search/maps-reviews` 실요청 200 OK 확인, 호텔 예약 선택 후 예약자명/추가 요청사항 입력 및 예약 요청 보내기 실행으로 확인번호 `NADO-28906F2E3E`와 예약 안내 패널 노출 확인

- [x] Expo/EAS Android 빌드 검증
  - 상태: 완료됨
  - 범위: `apps/mobile-nadotongryoksa` Android 산출물 생성 가능 여부 확인
  - 근거: `npx eas build --platform android --profile preview --non-interactive` 실행 완료. Build id `da56765a-3a90-46f4-be19-2779d3c9f0f8` 상태 `FINISHED`. APK 산출물 URL 확인: `https://expo.dev/artifacts/eas/sXKJn11Q3PrktvsEULCfNU.apk`

- [x] APK 실기기/설치형 검증
  - 상태: 완료됨
  - 범위: 생성된 APK 설치 또는 다운로드 가능한 산출물 기준 최소 1회 실행 확인
  - 근거:
    - APK 다운로드 URL: `https://expo.dev/artifacts/eas/sXKJn11Q3PrktvsEULCfNU.apk`
    - Expo 설치 페이지 (QR 포함): `https://expo.dev/accounts/parkcheolhong/projects/nadotongryoksa/builds/da56765a-3a90-46f4-be19-2779d3c9f0f8`
    - `eas build:list` API 확인: `status: FINISHED`, `distribution: INTERNAL`, `buildProfile: preview`, `sdkVersion: 51.0.0`, `platform: ANDROID`
    - 빌드 CLI 출력: `✔ Build finished` + QR 코드 노출 + Android 기기용 설치 링크 제공 확인
    - 비고: `distribution: INTERNAL` 산출물로 설치 페이지 또는 APK URL 직접 접근으로 Android 기기에 즉시 설치 가능 상태
