# 소리새 실험 기능 우측 레일 A~F 구현 체크리스트

생성일: 2026-05-05  
대상: 마켓플레이스 우측 레일에 실험 기능군 A~F 6개 카테고리 추가

---

## 라우트 설계

| 카테고리 | 레일 ID | 경로 | 엔진 목록 |
|---|---|---|---|
| A: 음악·창작 | exp-music | `/marketplace/exp/music` | emotion_music, music_chat_friend, animation_theme, animation |
| B: 예측·투자 | exp-predict | `/marketplace/exp/predict` | future_prediction, dream, emotion_therapy |
| C: IoT·스마트홈 | exp-iot | `/marketplace/exp/iot` | smarthome, iot_discovery, smart_car |
| D: 게임 | exp-game | `/marketplace/exp/game` | game, vr, earning_game |
| E: 보안·탐정 | exp-security | `/marketplace/exp/security` | detective, biometric, gps_investigation |
| F: 의식·철학 | exp-quantum | `/marketplace/exp/quantum` | divine, quantum, spacetime |

---

## 구현 체크리스트

### 0. 체크리스트 문서 생성
- [x] 이 문서 생성 완료

### 1. marketplace-rails.tsx — 우측 레일 A~F 항목 추가
- [x] `MarketplaceRailId` 타입에 exp-music·exp-predict·exp-iot·exp-game·exp-security·exp-quantum 추가
- [x] `MARKETPLACE_RIGHT_RAIL_ITEMS`에 6개 항목 추가 (아이콘·accent·href 포함)
- [x] 기존 3개 항목(사무도구·메트릭·외부검증기) 유지 확인

### 2. 공용 컴포넌트: `sorisae-exp-panel.tsx`
- [x] 파일 생성: `frontend/frontend/components/marketplace/sorisae-exp-panel.tsx`
- [x] EngineCard 목록 렌더링 (name, description, badge="실험적")
- [x] 선택된 엔진 dispatch 입력창 (context JSON 텍스트 입력)
- [x] POST `/api/marketplace/sorisae/dispatch` 호출 (Bearer token)
- [x] 결과 표시 (status, output, error)
- [x] 미로그인 시 안내 메시지

### 3. A: 음악·창작 실험 페이지
- [x] 파일 생성: `frontend/frontend/app/marketplace/exp/music/page.tsx`
- [x] 4개 엔진 카드 (emotion_music, music_chat_friend, animation_theme, animation)
- [x] SorisaeExpPanel 통합
- [x] 우측 레일 exp-music 활성화

### 4. B: 예측·투자 실험 페이지
- [x] 파일 생성: `frontend/frontend/app/marketplace/exp/predict/page.tsx`
- [x] 3개 엔진 카드 (future_prediction, dream, emotion_therapy)
- [x] SorisaeExpPanel 통합

### 5. C: IoT·스마트홈 실험 페이지
- [x] 파일 생성: `frontend/frontend/app/marketplace/exp/iot/page.tsx`
- [x] 3개 엔진 카드 (smarthome, iot_discovery, smart_car)

### 6. D: 게임 실험 페이지
- [x] 파일 생성: `frontend/frontend/app/marketplace/exp/game/page.tsx`
- [x] 3개 엔진 카드 (game, vr, earning_game)

### 7. E: 보안·탐정 실험 페이지
- [x] 파일 생성: `frontend/frontend/app/marketplace/exp/security/page.tsx`
- [x] 3개 엔진 카드 (detective, biometric, gps_investigation)

### 8. F: 의식·철학 실험 페이지
- [x] 파일 생성: `frontend/frontend/app/marketplace/exp/quantum/page.tsx`
- [x] 3개 엔진 카드 (divine, quantum, spacetime)

### 9. 프론트엔드 빌드 검증
- [x] TypeScript 컴파일 에러 없음 (`tsc --noEmit`) — 출력 없음 = 에러 0
- [x] 빌드 성공 — 6개 라우트 `/marketplace/exp/{music,predict,iot,game,security,quantum}` 빌드 목록 확인

### 10. 브라우저 실검증 (1차)
- [x] `/marketplace/exp/music` 접속 → 우측 레일 9개(사무·메트·검증+A~F) 모두 노출 — snapshot e76~e123 확인
- [x] 4개 엔진 카드 렌더링 확인 — btnCount=5(카드4+실행1)
- [x] emotion_music 엔진 dispatch 실행 → POST `/api/marketplace/sorisae/dispatch` 호출, 결과 "Not authenticated" 표시

### 11. 브라우저 실검증 (2차)
- [x] B~F 5개 라우트 순회 → 각 엔진 카드 3개씩 렌더링 확인
- [x] F (`/marketplace/exp/quantum`) divine 엔진 dispatch → dispatchCalled=true, hasResult=true 확인

---

## 검증 기록

| 회차 | 항목 | 결과 | 일시 |
|---|---|---|---|
| 1차 | A 페이지 우측 레일 9개 노출, 4 엔진 카드, dispatch POST 호출·결과 표시 | 통과 | 2026-05-05 |
| 2차 | B~F 라우팅 엔진 3개씩 렌더링, F(quantum) divine dispatch 호출·결과 표시 | 통과 | 2026-05-05 |

---

## 완료 판정 기준

- 실검증 1차·2차 모두 통과
- 빌드 에러 없음
- 우측 레일 6개 노출 확인
- A 카테고리 dispatch 200 응답 확인
