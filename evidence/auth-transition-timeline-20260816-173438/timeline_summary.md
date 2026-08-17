# Auth Transition Timeline Summary (2026-08-16 17:34:38)

## Artifacts
- 01_start.txt: app cold start result
- 02_callback_start.txt: passkey callback deep link injection result
- 03_ui_t2.xml: UI dump at ~t+2s after callback injection
- 04_ui_t10.xml: UI dump at ~t+10s after callback injection
- 05_reactnative_logcat.txt: ReactNativeJS log snapshot

## Verified log sequence
1) App started normally
- Start status is ok (cold start)

1) Deep link callback was delivered to running app instance
- "intent has been delivered to currently running top-most instance"

1) Callback parse/dispatch occurred
- DEEP_LINK_TRACE runtime_url contains passkey callback URL
- DEEP_LINK_TRACE_PARSE shows entry_target.type=auth, provider=passkey, auth_mode=passkey_login, access_token_present=true
- DEEP_LINK_TRACE_DISPATCH shows entry_type=auth

1) Auth callback event fired but stayed logged-out state
- UI_PRESS_PROBE SOCIAL_LOGIN_CALLBACK with:
  - token_ready=false
  - user_ready=false
  - show_login=true

1) Callback ended with fail, not success
- UI_PRESS_PROBE SOCIAL_LOGIN_CALLBACK_FAIL with:
  - provider=passkey
  - error="내 정보 조회 실패 (HTTP 401)"
  - auth_mode=passkey_login

## Conclusion from this timeline
- This run did not reach PASSKEY_LOGIN_CALLBACK_SUCCESS or SOCIAL_LOGIN_CALLBACK_SUCCESS.
- Therefore applyAuthenticatedSession() success path (token/user set + show_login false) was not entered in this run.
- Because callback failed at 401, login gate "re-open after success" branch cannot be validated from this timeline.

## Source code checkpoints related to this result
- apps/mobile-nadotongryoksa/App.tsx
  - applyAuthenticatedSession at line ~1496: sets show login false on success path.
  - auth hydration/bootstrap around lines ~3111-3172: can set show login true when no restored session.
  - callback logging around lines ~4014-4066: SOCIAL_LOGIN_CALLBACK, PASSKEY_LOGIN_CALLBACK_SUCCESS, SOCIAL_LOGIN_CALLBACK_SUCCESS, SOCIAL_LOGIN_CALLBACK_FAIL.
- apps/mobile-nadotongryoksa/src/features/sorisae/useSorisaeFabDrag.ts
  - sorisaeFabVisible at line ~57: requires userInfo present and showLogin false.

## Sorisae FAB in this timeline
- Given token_ready=false, user_ready=false, show_login=true at callback event and 401 fail,
  Sorisae FAB visibility condition is not satisfied by design.
- UI XML dumps are captured for this timeline, but this run's auth state itself already blocks FAB condition.

## Next clean-room rerun requirement
To capture "success then gate re-open" branch in one timeline:
1) Use a token that can pass current-user lookup (avoid 401).
2) Capture callbacks and UI_PRESS_PROBE transitions in one fresh logcat window.
3) Verify event order:
   - PASSKEY_LOGIN_CALLBACK_SUCCESS or SOCIAL_LOGIN_CALLBACK_SUCCESS
   - token_ready/user_ready true transition
   - any later show_login true event with cause.
4) Immediately capture UI dump and assert Sorisae FAB condition in same window.
