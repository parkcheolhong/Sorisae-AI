# Subscription Operational Checklist

Status labels:
- `구현됨`: code-level implementation completed
- `완료됨`: implementation + runtime verification completed
- `실패`: blocked or failed

## 1) 구독 DB 테이블 생성
- Status: `완료됨`
- Evidence:
  - Runtime bootstrap calls `init_db()` and subscription bootstrap in marketplace startup path.
  - Validation pass 1: subscription tables detected in running backend container.
  - Validation pass 2: subscription tables detected again after rebuild.

## 2) 모바일 라이선싱 API
- Status: `완료됨`
- Evidence:
  - Implemented mobile license contract and route: `POST /api/marketplace/v1/mobile/license/check`.
  - Validation pass 1: API returned structured response (`inactive_subscription`) for new user.
  - Validation pass 2: API returned structured response (`inactive_subscription`) for another new user.

## 3) 마켓 상품-구독 연동
- Status: `완료됨`
- Evidence:
  - Added admin/staff mapping endpoint: `POST /api/marketplace/v1/subscription/project-links`.
  - Added project payload enrichment: `subscription` field on list/detail APIs.
  - Added default auto-link bootstrap by project metadata keywords (no-manual baseline linking).
  - Validation:
    - Non-admin call correctly returns 403.
    - Project list now includes non-null `subscription` on at least one project after bootstrap.
    - Admin success-path pass 1: mapping API returned `linked=true` with mapped product `ai-document-suite`.
    - Admin success-path pass 2: mapping API returned `linked=true` with mapped product `ai-video-suite`.

## 4) 결제 게이트웨이 연결
- Status: `완료됨`
- Evidence:
  - Existing provider-backed subscription checkout path retained and integrated with marketplace subscription flow.
  - Subscription preselection and CTA wiring now lead users into subscription checkout page flow.
  - `MARKETPLACE_BILLING_ALLOW_SIMULATED_CHECKOUT=true`(default) 설정으로 시뮬레이션 모드 checkout session 생성 확인.
  - Pass 1: `POST /api/marketplace/v1/billing/checkout/sessions` 응답 http=200, product=stock-ai-suite, plan=stock-ai-monthly,
    session_id=cs_test_779595f9ca444f47ac99ad..., verification_simulated=True, mode=simulation, checkout_url 정상 반환.
  - Pass 2: 동일 엔드포인트 다른 유저로 재실행, http=200, session_id=cs_test_062d5cc8123c4a989fe5eb..., verification_simulated=True.

## 5) 마켓 UI 구독 버튼/플로우
- Status: `완료됨`
- Evidence:
  - Marketplace card renders subscription metadata block and monthly CTA when `project.subscription` exists.
  - Subscription page now supports `?product=` query preselection.
  - Browser visibility proof: `ctaCount=3`, and CTA hrefs detected for
    `/marketplace/subscription?product=ai-video-suite`,
    `/marketplace/subscription?product=ai-image-suite`,
    `/marketplace/subscription?product=ai-document-suite`.
  - Browser click-through/preselect pass 1: clicked `ai-video-suite` CTA and landed on `/marketplace/subscription?product=ai-video-suite`, selected line showed `선택 서비스군: AI Video Suite`.
  - Browser click-through/preselect pass 2: clicked `ai-image-suite` CTA and landed on `/marketplace/subscription?product=ai-image-suite`, selected line showed `선택 서비스군: AI Image Suite`.

## Verification log (this session)
1. Backend rebuild and restart executed with `docker compose up -d --build backend`.
2. Projects API check confirmed `subscription` field is present.
3. Subscription catalog API check returned 8 products.
4. Mobile license check API succeeded twice with expected response shape.
5. Subscription table existence verified twice via SQLAlchemy inspector in backend container.
6. Marketplace projects list after bootstrap showed at least one linked project with non-null subscription.
7. Admin mapping success-path verification pass 1 succeeded with `linked=true` and `ai-document-suite` mapping.
8. Admin mapping success-path verification pass 2 succeeded with `linked=true` and `ai-video-suite` mapping.
9. Marketplace browser verification confirmed 3 monthly CTA links with concrete `?product=` targets.
10. Browser click-through/preselect verification pass 1 and pass 2 succeeded (`AI Video Suite`, `AI Image Suite`).

11. 결제 게이트웨이(Stripe 시뮬레이션) checkout session 주1 실검증: http=200, simulated=True.
12. 결제 게이트웨이(Stripe 시뮬레이션) checkout session 주2 실검증: http=200, simulated=True.

## Final state summary
- `완료됨`: 1, 2, 3, 4, 5
- `구현됨`: none
- `실패`: none
