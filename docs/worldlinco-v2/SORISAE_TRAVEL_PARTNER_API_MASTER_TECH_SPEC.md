# Sorisae Travel Partner API Master Tech Spec

## 0. 문서 목적
- 소리새 AI가 여행 대화로 사용자 선호를 축적하고, 호텔/이동/투어 파트너 연동으로 수익을 창출하는 운영형 파이프라인을 정의한다.
- 모든 파트너 연결/연동/운영/모니터링을 관리자 대시보드에서 수행할 수 있도록 SSOT를 고정한다.

## 1. 목표
- 대화 축적: 의도/슬롯/피드백을 구조화해 추천 품질을 지속 개선
- 파트너 연동: 호텔/투어/이동 파트너를 지역별 라우팅 정책으로 제어
- 수익화: 추천 퍼널과 커미션 정산까지 추적 가능
- 운영성: 관리자 패널에서 연결 테스트, 장애 탐지, fallback 조정 가능

## 2. 범위
- 포함
  - 대화 데이터 스키마
  - 파트너 연동 우선순위(호텔→투어→이동)
  - 관리자 대시보드 연동 허브
  - 수익 KPI 대시보드
- 제외
  - 결제대행 신규 구축
  - 외부 파트너 계약/법무 체결 절차

## 3. 관리자 대시보드 연동 구조

### 3.1 패널
- 이름: `Partner Integration Hub`
- 위치: `/admin` 우측 런처 레일
- 기능
  - 파트너 카탈로그 관리
  - 커넥터 연결 테스트
  - 국가/도시 라우팅 정책 관리
  - 웹훅 장애 모니터/재처리
  - 수익 퍼널/KPI 요약 확인

### 3.2 운영 흐름
1. 운영자가 파트너 등록
2. 커넥터 인증 설정 및 연결 테스트
3. 국가/도시 라우팅 정책 저장
4. 추천 응답에서 정책 기반 파트너 후보 산출
5. 클릭/예약/완료 이벤트 집계
6. 커미션 및 KPI 반영

## 4. 데이터 모델 (핵심)

### 4.1 대화 축적
- `trip_sessions`
- `conversation_turns`
- `travel_slots`
- `feedback_events`

### 4.2 파트너/수익
- `partner_catalog`
- `partner_connectors`
- `routing_policies`
- `recommendation_events`
- `partner_click_events`
- `booking_events`
- `attribution_ledger`

### 4.3 보안/컴플라이언스
- `consents`
- `privacy_audit_logs`

## 5. 파트너 연동 우선순위

### 5.1 1순위 호텔
- 이유: 고단가 예약으로 수익 기여도 큼
- 단계: 제휴 링크형 → API 직접 연동

### 5.2 2순위 투어/액티비티
- 이유: 여행 대화 맥락과 추천 적합성 높음
- 단계: 도시 큐레이션 링크형 → API 연동형

### 5.3 3순위 이동
- 이유: 지역별 공급 차이/정책 차이 큼
- 단계: 딥링크형 → 지역별 다중 라우팅

## 6. API 로드맵 (관리자 연동 중심)

### Phase 1: 제휴 링크형
- `POST /api/admin/travel-partners`
- `GET /api/admin/travel-partners`
- `PUT /api/admin/travel-routing-policy`
- `POST /api/affiliate/click`

### Phase 2: 예약 API 직접 연동
- `POST /api/admin/travel-connectors/{connectorId}/test`
- `GET /api/travel/search/hotels`
- `GET /api/travel/search/tours`
- `POST /api/travel/booking/initiate`
- `POST /api/travel/booking/webhook/{partner}`

### Phase 3: 이동 라우팅 고도화
- `GET /api/travel/search/transport`
- `POST /api/travel/transport/deeplink`
- `PUT /api/admin/travel-routing-city-policy`
- `GET /api/admin/travel-routing-health`

### Phase 4: 정산/리포팅
- `GET /api/admin/revenue/ledger`
- `GET /api/admin/revenue/settlements`
- `GET /api/admin/revenue/by-partner`
- `POST /api/admin/revenue/reconcile`

## 7. MVP 화면 흐름
1. 사용자 여행 컨텍스트 입력
2. 대화형 질문/응답
3. 추천 보드(호텔/투어/이동)
4. 예약/외부 이동
5. 피드백 수집
6. 추천 품질/수익 이벤트 누적

## 8. KPI 정의

### 8.1 퍼널
- CTR = clicks / impressions
- Booking Start Rate = booking_initiated / clicks
- Confirm Rate = booking_confirmed / booking_initiated
- Completion Rate = booking_completed / booking_confirmed

### 8.2 수익
- GMV
- 총 커미션
- RPS(세션당 수익)
- 파트너별 순수익

### 8.3 운영/품질
- 파트너 API 성공률
- 파트너 API p95
- fallback 비율
- 추천 만족도
- 취소율/환불율

## 9. 보안/정책
- API 키 원문 저장 금지(시크릿 참조 ID만 저장)
- 위치/음성/프로필 동의 목적 분리
- 제휴 추천 카드에 스폰서/제휴 표기
- 웹훅 서명 검증 + idempotency 처리

## 10. 착수 산출물 (2026-06-30)
- 체크리스트 생성: `docs/checklists/sorisae-travel-partner-api-integration-checklist-20260630.md`
- 관리자 UI 스켈레톤: `Partner Integration Hub` 패널/런처 연결

## 11. 관리자 운영 UX 확장 (2026-06-30)

### 11.1 Travel Partner 운영 시퀀스 고정
- 관리자 패널에서 아래 순서를 기본 운영 플로우로 고정한다.
1. `1) API URL 저장`
2. `2) Webhook 테스트 발송`
3. `3) 결과 확인`
- Webhook 테스트는 이벤트 타입과 샘플 JSON 바디를 UI에서 직접 편집해 즉시 재전송 가능해야 한다.
- 결과 카드는 `reachable/unreachable`, `status_code`, `response_time_ms`, `error`를 즉시 표시한다.

### 11.2 Travel Partner API 운영 확장 포인트
- API URL 저장: `PUT /api/admin/travel-partners/{partnerId}/connection`
- Webhook 테스트: `POST /api/admin/travel-partners/{partnerId}/webhook/test`
  - 입력 필드: `webhook_url`, `timeout_ms`, `event_type`, `sample_data`
  - 목적: 저장 직후 연결 생존성/계약 형태를 관리자 화면에서 즉시 검증

### 11.3 레일 운영 액션 센터 상·하단 토글 UX
- 운영자가 긴 카드 그리드를 빠르게 접고/펼칠 수 있도록 액션 센터에 상단/하단 토글을 제공한다.
  - 상단: `위에서 접기 ▲` / `위에서 열기 ▼`
  - 하단: `아래에서 접기 ▲`
- 요구사항: 대시보드 운영 중 패널 이동/확장 시 스크롤 비용을 줄이고, 즉시조치 가시성을 보장한다.
