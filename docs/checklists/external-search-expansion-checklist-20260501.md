# External Search Expansion Checklist

## Scope

- backend/api/external_search_router.py
- backend/main.py
- frontend/frontend/components/ui/AdminExternalSearchPanel.tsx
- frontend/frontend/app/admin/llm/page.tsx

## Checklist

- [x] Google Maps place_id 기반 상세 리뷰 모드를 place_id 해석 + 상세 리뷰 조회 흐름으로 강화한다.
- [x] Bing 뉴스 외 Bing 이미지/비디오 엔드포인트를 추가한다.
- [x] 관리자 LLM 패널에서 뉴스/지도리뷰/유튜브/트렌드/쇼핑 5개 API를 즉시 호출할 수 있는 UI를 연결한다.
- [x] 변경 파일 정적 오류를 0건으로 맞춘다.
- [x] 백엔드 런타임 실검증 2회를 통과한다.
- [x] 관리자 패널 API 호출 실검증 2회를 통과한다.

## Verification Log

- 2026-05-01 pass 1: `http://127.0.0.1:8000`에서 로그인 후 `news`, `maps-reviews`, `shopping` 실응답 확인. `news` 2건, `maps-reviews` 2건, `shopping` 2건. Bing `images/videos`는 `MISSING_API_KEY` 표준 오류 스키마 반환 확인.
- 2026-05-01 pass 2: `maps-reviews` 검색 결과에서 `place_id=ChIJobb671mhfDURrcE4SebLfyw` 추출 후 상세 호출 재검증. `google_maps_reviews`로 3건 반환, `source=스타벅스 강남R점`, `extra.place_id/data_id/address/category/response_from_owner` 확인.
- 2026-05-01 frontend pass 1: `http://127.0.0.1:3005/admin` iframe 내 `외부 검색 즉시 호출` 패널 노출 확인 후 `news` 호출 성공. 메타 `endpoint=news`, `provider=serpapi`, `engine=google_news`, `items=5` 확인.
- 2026-05-01 frontend pass 2: 같은 패널에서 `maps-reviews` 호출 성공. 메타 `endpoint=maps-reviews`, `engine=google_maps`, `items=5` 및 카드별 `place_id/data_id` 렌더링 확인.
- 2026-05-01 Bing key block: 워크스페이스 `.env` 및 컨테이너 환경에서 `BING_SEARCH_API_KEY`가 빈 값으로 확인됨. 실제 Bing 이미지/비디오 데이터 응답 검증은 키 주입 후 재실행 필요.
