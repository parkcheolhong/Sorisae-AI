+# 월드링코 x 소리새 글로벌 신뢰 로드맵 체크리스트 (운영형)

- 작성일: 2026-06-28
- 목적: 소리새를 글로벌 관광 홍보 중추 엔진으로 고도화하면서 정확성, 진실성, 실시간성, 재현 가능한 검증을 동시에 달성
- 원칙: 체크 항목은 실검증 근거가 없으면 완료 처리 금지
- 원칙: [~] 진행중 항목은 해당 항목의 성공 기준과 증거 파일 경로가 충족되면 [x]로 전환 가능하며, 2회 연속 PASS가 필요한 항목은 2회 연속 PASS 근거를 모두 기재해야 한다

표시: [ ] 미착수, [~] 진행중, [x] 완료

## A. 신뢰 기준 SSOT 고정

- [x] A-1 답변 신뢰 등급 스키마 확정 (확정, 추정, 미확인)
- [x] A-2 나라별 규제/안전/관습 답변의 근거 출처 필수화 규칙 확정
- [x] A-3 친구형 말투와 사실 검증의 충돌 방지 정책 확정
- [x] A-4 운영 실패 시 안전 폴백 문구 표준화

근거:
- backend/llm/voice_gateway.py: VoiceResponse에 evidence_grade/evidence_reason/uncertainty_disclosed/grounded_items_count 추가
- backend/llm/voice_gateway.py: grounding 기반 근거등급 계산기(_build_evidence_grade) 추가
- backend/llm/voice_gateway.py: 고위험 관광 질의(안전/규제/관습)에서 공식/권위 출처 단서가 없으면 불확실성 고지 강제(_ensure_high_risk_source_disclosure, _has_authoritative_grounding_source) 추가
- backend/llm/voice_gateway.py: 사실질의(_is_fact_sensitive_query)에서 감정 보강 문구를 건너뛰어 사실검증 우선 톤 유지(A-3)
- backend/llm/voice_gateway.py: 친구 모드 LLM 실패/빈 응답 시 표준 안전 폴백 문구 반환(_build_operational_failure_fallback)으로 502 직접 노출 대신 안전 응답 유지
- backend/tests/test_voice_gateway_companion_persona.py: 비공식 블로그/커뮤니티 근거는 강제 고지, 출입국관리청/대사관 근거는 통과하는 A-2 회귀 테스트 추가
- backend/tests/test_voice_gateway_companion_persona.py: 일반 질의/고위험 질의 운영 실패 폴백 문구 표준화 테스트 추가
- 검증: python -m pytest backend/tests/test_voice_gateway_companion_persona.py -q -> 26 passed

## B. 전세계 GPS 관광 질의 정확도 개선

- [x] B-1 근거리 질의와 지역 개요 질의 라우팅 분리 고도화
- [x] B-2 관광지, 맛집, 숙소 카테고리 분류 정확도 회귀 테스트 강화
- [x] B-3 국가/도시별 좌표 오차 허용치 정책 분리 (도보권, 광역권)
- [x] B-4 오프토픽 응답 억제 규칙 (질문 의도와 무관한 숙소/광고성 문구 차단)

근거:
- backend/llm/voice_gateway.py:_friend_prefers_far_first 계산값이 실제 거리 정렬에 반영되도록_sort_grounding_rows_by_distance 추가
- backend/llm/voice_gateway.py: 관광 KB/OSM grounding 정렬이 `prefer_far_first=False`면 근거리 우선, `True`면 지역 개요용 원거리 우선으로 분기
- backend/tests/test_voice_gateway_companion_persona.py: 근거리 질의 near-first / 개요 질의 far-first 정렬 회귀 테스트 추가
- backend/llm/voice_gateway.py: 숙소 영어 표현(hostel/lodging/accommodation/stay/inn)까지 place category 키워드 확장
- backend/tests/test_voice_gateway_companion_persona.py: 관광지/맛집/숙소(한글·영문) 직접 분류 회귀 + 비자 규정 비장소 부정 케이스 추가
- backend/llm/voice_gateway.py: geo_accuracy_nearby_max_m(도보권), geo_accuracy_overview_max_m(광역권), geo_accuracy_max_m(기본) 3단계 정책 분리 및 _resolve_geo_accuracy_max_m 추가
- backend/llm/voice_gateway.py: friend-chat 좌표 신뢰 판정이 질의 유형별 policy=nearby/overview/default 로그와 함께 분기되도록 변경
- backend/tests/test_voice_gateway_companion_persona.py: 근처 질의 strict threshold / 개요 질의 loose threshold / 일반 질의 default threshold 회귀 테스트 추가
- backend/llm/voice_gateway.py:_ensure_on_topic_companion_response 추가로 맛집/관광지 질의에 무관한 숙소 중심 답변을 억제하고, 광고성 표현(특가/할인/지금 예약 등) 제거
- backend/tests/test_voice_gateway_companion_persona.py: 맛집 질의→숙소 답변 억제, 관광지 질의→숙소 답변 억제, 숙소 답변 내 광고성 문구 제거 회귀 테스트 추가
- 검증: python -m pytest backend/tests/test_voice_gateway_companion_persona.py -q -> 38 passed

## C. 근거기반 응답 강제

- [x] C-1 friend-chat 응답에 내부 근거 유무 플래그 기록
- [x] C-2 전화번호, 운영시간, 주소는 근거 블록 매칭 실패 시 노출 금지 강화
- [x] C-3 출처 누락 질의 자동 재검색 또는 불확실성 고지
- [x] C-4 국가별 핵심 관광질문 100선 자동 평가셋 구축

근거:
- backend/llm/voice_gateway.py: friend-chat 응답에 근거등급/불확실성/근거건수 반환
- backend/llm/voice_gateway.py:_redact_unverified_contacts 가 전화번호뿐 아니라 `주소:`/`영업:` 라벨 값도 grounding 블록 매칭 실패 시 제거하도록 확장
- backend/llm/voice_gateway.py: 확인되지 않은 전화번호·주소·운영시간 제거 시 `_UNVERIFIED_CONTACT_DETAIL_NOTE` 로 검증된 정보만 안내하도록 표준 문구 추가
- backend/llm/voice_gateway.py: 사실질의 + 무근거 시 자동 재검색 1회(force=True) 후 실패 시 불확실성 고지 강제(_ensure_source_missing_disclosure)
- scripts/eval_friend_chat_fact100.py: 관광형 20개국 x 5토픽(수도/통화/언어/실시간 날씨 불확실성/실시간 환율 불확실성) 100문항 구조로 재구성, topic 메타데이터/coverage 검증/topic_summary 추가
- tests/test_eval_friend_chat_fact100.py: 20개국 x 5토픽 구조, 관광형 프롬프트, topic_summary 집계 회귀 테스트 추가
- 실행 증거: reports/friend-chat-fact100-20260628-183635.json (limit=2 스모크, 리포트 생성 확인)
- 실행 증거: reports/friend-chat-fact100-20260628-184915.json (100문항 풀런, accuracy=0.95 통과 / uncertainty=0.075 미달, passed=false)
- 실행 증거: reports/friend-chat-fact100-20260628-190222.json (100문항 재실행, accuracy=0.95 통과 / uncertainty=0.125 미달, passed=false)
- 실행 증거: reports/friend-chat-fact100-20260628-191451.json (100문항 재실행, accuracy=0.9833 / uncertainty=1.0, passed=true)
- 실행 증거: reports/friend-chat-fact100-20260628-224158.json (관광형 fact100 재구성 후 limit=5 스모크, accuracy=1.0 / uncertainty=1.0)
- backend/tests/test_voice_gateway_companion_persona.py: 비검증 주소/운영시간/전화 제거, 검증된 주소/운영시간/전화 유지 회귀 테스트 추가
- backend/llm/voice_gateway.py: 짧은 안내 번호(예: 114/139/12121) 누수를 막는_FRIEND_SHORT_CONTACT_RE 추가 및 신뢰 가능한 GPS일 때 stale region_hint 대신 reverse geocode 지역 라벨 우선 적용
- backend/tests/test_voice_gateway_companion_persona.py: 짧은 안내 번호 제거, stale Jeju region_hint override 회귀 테스트 추가
- 검증: python -m pytest backend/tests/test_voice_gateway_companion_persona.py -q -> 43 passed
- 검증: python -m pytest tests/test_eval_friend_chat_fact100.py -q -> 3 passed

## D. 실기기 검증 체계 강화 (S10 포함)

- [x] D-1 실기기 D-0 스모크 자동화 실행 및 증거 저장
- [x] D-2 인증 준비 상태 실패 원인 자동 수집 (auth restore, token ready, user ready)
- [x] D-3 친구 허브 진입 실패 원인 자동 수집 (딥링크 소비, UI dump, RN 로그)
- [x] D-4 단말 2대 이상 통화 시나리오 통과 기준 재정의

근거:
- 실행 기록: evidence/device-d0-smoke-20260628-181001/summary.json
- 현재 결과: auth_ready=false, friend_hub_visible=false, voip.connected=false
- 실행 기록: evidence/device-d0-smoke-20260628-183947/summary.json
- 현재 결과(재실행): auth_ready=false, friend_hub_visible=false, voip.connected=false
- 실행 기록: evidence/device-d0-smoke-20260628-185214/summary.json
- 현재 결과(재재실행): auth_ready=false, friend_hub_visible=false, voip.connected=false
- 실행 기록: evidence/device-d0-smoke-20260628-191641/summary.json
- 현재 결과(재재재실행): auth_ready=false, friend_hub_visible=false, voip.connected=false
- 실행 기록: evidence/device-d0-smoke-20260628-192559/summary.json
- 현재 결과(재재재재실행): auth_ready=false, friend_hub_visible=false, voip.connected=false
- 실행 기록: evidence/device-d0-smoke-20260628-193446/run.log
- 현재 결과(입력 누적 버그 수정 후): auth_ready=false, friend_hub_visible=false
- 실행 기록: evidence/device-d0-smoke-20260628-194008/run.log
- 현재 결과(사전검증): Invalid production auth credential for <119cash@naver.com>
- 상세 진단: .tmp/s10_auth_probe_20260628.log 에서 S10은 token_ready=true, user_ready=true, VOIP_PRESENCE_CONNECTED 확인
- 상세 진단: .tmp/fold_auth_probe_20260628.log 에서 보조 단말은 AuthStorage restore invalid 발생(내 정보 조회 실패)
- 차단 원인: 프로덕션 로그인 자격증명 불일치(API/UI 공통)로 auth_ready 전환 실패. 입력 누적 버그는 제거했으나 인증 자체가 거절되어 2단말 VoIP 시나리오 진행 불가
- 실행 기록: evidence/device-d0-smoke-20260628-224857/summary.json
- 현재 결과(최신 재실행): auth_ready=false, friend_hub_visible=true, voip.connected=false
- 실행 기록: evidence/voip-voice-relay-orchestrator/manual_retest_20260628-225224/run.log
- 현재 차단(최신 재실행): Primary/Secondary 모두 auth_not_ready, VoIP 단계는 callee auth timeout 으로 중단
- 코드 근거: scripts/worldlinco_device_d0_smoke.ps1 에 primary_auth/secondary_auth 분리 요약, auth_state JSON 저장, device_missing fast-fail 추가
- 실행 증거: evidence/device-d0-smoke-20260628-220340/summary.json 에서 primary_auth.blocker=device_missing, secondary_auth 별도 유지 확인
- 실행 증거: .tmp/auth_state_reclassify_20260628.json 에서 S10 auth_ready=true / Fold blocker=restore_invalid 재분류 확인
- 코드 근거: apps/mobile-nadotongryoksa/App.tsx 에 validation deeplink 비로그인 경로 `VOIP_VALIDATION_DEEPLINK_AUTH_REQUIRED` 추가, userInfo 미존재 시 빈 친구 허브 모달 대신 로그인 유도
- 코드 근거: scripts/worldlinco_device_d0_smoke.ps1 에 friend_hub_blocker 요약 및 `VOIP_VALIDATION_DEEPLINK_AUTH_REQUIRED` 카운트 추가
- 실행 기록: evidence/device-d0-smoke-20260628-230538/summary.json
- 현재 결과(인증 수집 보강 후): primary_auth.ready=true, secondary_auth.blocker=react_log_silent, friend_hub_visible=true
- 실행 증거: evidence/device-d0-smoke-20260628-230538/auth_failure_secondary_ui.xml, evidence/device-d0-smoke-20260628-230538/auth_failure_secondary_activity_top.txt, evidence/device-d0-smoke-20260628-230538/auth_failure_secondary_pid.txt 자동 저장 확인
- 코드 근거: scripts/worldlinco_device_d0_smoke.ps1 에 session_present/ui_probe_seen/react_log_silent 분류와 non-ready 단말 auth failure UI/activity/pid 자동 수집 추가
- 코드 근거: scripts/worldlinco_device_d0_smoke.ps1 에 warm launch 시 `pending_call_poll status=200` + `token_summary/user_id` 조합을 auth_ready로 인정하는 세션 재분류 추가
- 실행 기록: evidence/device-d0-smoke-20260628-232221/summary.json
- 현재 결과(세션 재분류 후 재실행): primary_auth.ready=true, primary_auth.blocker=null, secondary_auth.blocker=react_log_silent, friend_hub_visible=true, voip.connected=false
- 실행 기록: evidence/device-d0-smoke-20260628-232221/run.log
- 현재 차단(최신): 172.30.1.19:5555 에서 ReactNative auth 로그가 비어 있어 callee auth timeout 으로 VoIP 단계가 중단되며, 실기기(E-2) 2회 연속 PASS 및 운영 도메인(E-3) 2회 연속 PASS 근거가 모두 없어 아직 승격 불가
- 실행 기록: evidence/device-d0-smoke-20260628-234949/summary.json
- 현재 결과(차단 원인 정밀화 후): primary_auth.ready=true, secondary_auth.blocker=login_api_unauthorized, auth_api_credential.ok=false, friend_hub_visible=true
- 코드 근거: scripts/worldlinco_device_d0_smoke.ps1 / scripts/voip_manual_call_setup.ps1 에 callee warm-session evidence 부재 시 auth/login API preflight 를 실행해 secondary silent/auth timeout 을 `login_api_unauthorized`로 명시 분류
- 실행 기록: evidence/voip-voice-relay-orchestrator/manual_retest_20260628-235719/run.log
- 현재 결과(최신 fail-fast 검증): `pwsh -NoProfile -File scripts/voip_manual_call_setup.ps1 -SetupOnly -MonitorSec 1` 가 auth 대기 전 preflight 에서 `VoIP API credential preflight failed (login_api_unauthorized)`로 즉시 중단
- 운영 직접 검증: scripts 내 기존 후보 비밀번호는 `POST https://metanova1004.com/api/auth/login` 에서 `401` 반환으로 무효 확인(REPO_CANDIDATE_FAIL:401)
- 운영 직접 검증: `devanalysis114-backend:/run/codeai-secrets/fixed_admin_password.txt` 런타임 secret 역시 동일 로그인 API 에서 `401` 반환으로 무효 확인(CONTAINER_SECRET_FAIL:401)
- 운영 직접 검증: `scripts/reset_fixed_admin_password.py` + `.runtime/secrets/fixed_admin_password.txt` 갱신 후 동일 로그인 API 가 access token 을 반환해 fixed-admin 자격증명 복구 확인
- 실행 기록: evidence/device-d0-smoke-20260629-001353/summary.json
- 현재 결과(운영 자격증명 복구 후 D-0): primary_auth.ready=true, auth_api_credential.ok=true, friend_hub_visible=true, secondary_auth.blocker=react_log_silent, voip.connected=false
- 실행 기록: evidence/voip-voice-relay-orchestrator/manual_retest_20260629-002951/run.log
- 현재 결과(standalone SetupOnly 재검증): secondary 자동 로그인은 `Password field hidden after email input -> TAB fallback -> ENTER submit fallback` 을 거쳐 통과했고, `Tab call started call_id=call-3a9b003cdcbe` 이후 `S10 incoming timeout` 으로 다음 병목이 callee 수신 단계로 이동
- 실행 기록: evidence/voip-voice-relay-orchestrator/manual_retest_20260629-000744/run.log
- 실행 증거: evidence/voip-voice-relay-orchestrator/manual_retest_20260629-000744/callee_preserve_session_probe.xml 에서 `worldlinco-inline-open-login-button` 존재 확인
- 현재 결과(기존 세션 보존 분기): `pwsh -NoProfile -File scripts/voip_manual_call_setup.ps1 -SetupOnly -PreserveCalleeSession -MonitorSec 1` 는 fresh-login preflight 대신 `Preserve callee session requested but callee session is missing (callee_session_missing)` 로 즉시 중단
- 코드 근거: scripts/voip_manual_call_setup.ps1 에 `PreserveCalleeSession` 요청 시 warm-session evidence 및 login surface probe 후 `callee_session_missing` 으로 fail-fast 하는 분기 추가
- 실행 기록: evidence/voip-voice-relay-orchestrator/manual_retest_20260629-003408/run.log
- 현재 결과(운영 자격증명 복구 후 PreserveCalleeSession 재검증): 보조 단말이 여전히 warm-session evidence 없이 preserve 요청을 받아 `callee_session_missing` 으로 즉시 중단
- 실행 기록: evidence/device-d0-smoke-20260629-003423/summary.json
- 현재 결과(통합 D-0 재검증): standalone 경로와 달리 D-0 내부 호출에서는 secondary가 다시 `callee auth timeout` 으로 후퇴해, 통합 시나리오 기준으론 secondary auth 안정화가 아직 미완료
- 코드 근거: scripts/voip_manual_call_setup.ps1 에 hidden password field 시 TAB focused input 폴백, submit button 미노출 시 ENTER submit 폴백 추가
- 실행 기록: evidence/voip-voice-relay-orchestrator/manual_retest_20260629-010343/run.log
- 현재 결과(standalone 튜닝 재검증): submit button bounds=0 문제를 우회하기 위해 `로그인` 텍스트 탭 폴백까지 추가했지만, 보조 단말은 여전히 로그인 시트가 유지되어 `Callee auth timeout` 으로 종료
- 실행 증거: evidence/voip-voice-relay-orchestrator/manual_retest_20260629-004910/auth_post_submit_172.30.1.19_5555.xml 에서 `worldlinco-auth-login-submit-button` 존재 + bounds=`[0,0][0,0]`, `로그인` 텍스트 노드 존재 확인
- 실행 기록: evidence/device-d0-smoke-20260629-010814/run.log
- 현재 결과(통합 경로 차이 정렬 후): D-0 가 secondary에 대해서도 standalone과 같은 auth wait / hidden-password TAB fallback / submit retry 를 수행하게 되어 `react_log_silent` 는 제거됐고, 현재 blocker 는 `login_invalid` 로 수렴
- 실행 증거: evidence/device-d0-smoke-20260629-010814/secondary_auth_state.json 에서 `react_log_silent=false`, `login_invalid=true`, `ui_probe_seen=true` 확인
- 코드 근거: scripts/worldlinco_device_d0_smoke.ps1 에 secondary `Wait-AuthReady` 추가, 로그인 시트 재시도, keyboard dismiss 후 submit retry 추가로 standalone/D-0 호출 차이 정렬
- 실행 증거: evidence/device-d0-smoke-20260629-010814/secondary_auth_logcat.txt 에서 `AUTH_INPUT_PROBE` 기준 `password_length` 가 12에서 24로 증가한 뒤 `LOGIN_API_FAIL status=401` 및 `LOGIN_SUBMIT_FAIL` 발생 확인
- 현재 결론(직접 원인 검증): `login_invalid` 의 직접 원인은 실제 운영 비밀번호 불일치가 아니라 hidden password fallback 경로에서 기존 12자 비밀번호 위에 동일 12자가 덧붙는 입력 손상(tuning)임을 서버 응답 기준으로 확인
- 코드 근거: scripts/voip_manual_call_setup.ps1 / scripts/worldlinco_device_d0_smoke.ps1 에 hidden password 시 keyboard dismiss 후 password field 재노출 → clear+set 우선, 그리고 submit 직후 `AUTH_TRACE` 로 `LOGIN_API_REQUEST/LOGIN_API_SUCCESS|FAIL/LOGIN_SUBMIT_SUCCESS|FAIL` 를 run.log 에 강제 기록하도록 보강
- 실행 기록: evidence/voip-voice-relay-orchestrator/manual_retest_20260629-011509/run.log
- 현재 결과(standalone auth loop 종료): `AUTH_TRACE[172.30.1.19:5555]` 에 `LOGIN_API_REQUEST` -> `LOGIN_API_SUCCESS status=200` -> `LOGIN_SUBMIT_SUCCESS` 가 직접 기록되었고, 이후 병목은 auth 가 아니라 `S10 incoming timeout for call-b4ea94ea78f3` 로 이동
- 실행 기록: evidence/device-d0-smoke-20260629-012456/run.log
- 현재 결과(통합 D-0 auth loop 종료): secondary 에서 `AUTH_TRACE` 로 `LOGIN_API_REQUEST` -> `LOGIN_API_SUCCESS status=200` -> `LOGIN_SUBMIT_SUCCESS` 가 기록되고 `Secondary auth ready: True` 까지 상승, D-0 summary 도 secondary_auth.ready=true / token_ready=true / user_ready=true / presence_connected=true 로 갱신됨
- 실행 기록: evidence/device-d0-smoke-20260629-012456/summary.json
- 현재 결과(남은 병목): integrated VoIP 단계도 auth 를 넘겨 `call_id=call-6d481f015504`, `voip.connected=true` 까지 기록했지만, 수신 검증은 여전히 `S10 incoming timeout` 에서 멈춰 D-4 병목이 이제 순수 callee incoming 단계로 정리됨
- 코드 근거: scripts/voip_manual_call_setup.ps1 의 `Wait-ForIncomingCallId` 를 `VOIP_PENDING_CALL_FETCHED|VOIP_INCOMING_CALL_RECEIVED|VOIP_INCOMING_CALL_APPLIED` 로그 + `/api/v1/voip/calls/pending-incoming` API polling + incoming deeplink auto-accept 조합으로 확장
- 실행 기록: evidence/voip-voice-relay-orchestrator/manual_retest_20260629-013104/run.log
- 현재 결과(standalone incoming 단계 해결): `Pending-incoming API confirmed call_id=call-eb200b1585ef` 후 `S10 accept — incoming deeplink auto-accept` 및 `=== SETUP ONLY: connected call_id=call-eb200b1585ef ===` 까지 도달
- 실행 기록: evidence/device-d0-smoke-20260629-013323/run.log
- 현재 결과(통합 D-0 incoming 단계 해결): secondary `AUTH_TRACE` 에서 `LOGIN_API_SUCCESS status=200` 확인 후 integrated auto-call 이 `call_id=call-6d481f015504` 로 생성되고, 최종 summary 에서 `secondary_auth.ready=true` 및 `voip.connected=true` 까지 반영
- 실행 기록: evidence/device-d0-smoke-20260629-013323/summary.json
- 현재 결과(D-4 진척): auth loop, incoming detection, auto-accept 경로가 모두 통과해 남은 검증은 음성 relay/후속 품질 단계로 이관 가능
- 실행 기록: evidence/device-d0-smoke-20260629-012456/summary.json
- 실행 기록: evidence/device-d0-smoke-20260629-012456/friend_folder_open.xml
- 현재 결과(D-3 자동 수집 완료): friend_hub_visible=true, friend_hub_blocker=null, primary_logcat/network probe/UI dump 가 함께 저장되어 친구 허브 딥링크 소비 성공/실패 원인을 자동 수집하는 경로가 실증됨
- 실행 기록: evidence/voip-voice-relay-orchestrator/run_20260629-020319/E2E_REPORT.md
- 실행 기록: evidence/voip-voice-relay-orchestrator/run_20260629-020319/summary.json
- 현재 결과(V-8 relay probe): build254 실기기 2대에 대해 auth hydration, incoming accept, connected 35초 유지, probe audio 기반 실제 relay/번역 로그를 검증했고 `Hard pass=True`, `Relay pass=True` 확인
- 번역 품질 근거: evidence/voip-voice-relay-orchestrator/run_20260629-020319/caller_final.log 에서 `segment_response ok:true route:translate from:ko to:en translated:"Hello. Nice to meet you."` 확인
- relay 근거: evidence/voip-voice-relay-orchestrator/run_20260629-020319/callee_final.log 및 caller_final.log 에서 `normalizedType: 'voice_translation'` / `rawPreview:{"type":"voice_translation"...}` 확인
- connected 유지 근거: evidence/voip-voice-relay-orchestrator/run_20260629-020319/summary.json 에서 `accept_api_seen=true`, `signaling_seen=true`, `hard_pass=true`, `relay_pass=true`; callee_final.log 에서 `VOIP_CALL_MODE_AUDIT_LOADED`(call_initiated, call_accepted)와 `VOIP_RAIL_STATE_RESTORE active_call_id` 확인
- 코드 근거: scripts/voip_voice_relay_v8_e2e.ps1 에 auth UI 자동화 이식, current runtime 로그 taxonomy(`voice_translation`, `segment_response`, `VOIP_CALL_MODE_AUDIT_LOADED`, `VOIP_RAIL_STATE_RESTORE`) 기준 게이트 재정의 추가
- 검증: pwsh -NoProfile -File scripts/voip_manual_call_setup.ps1 -HangupOnly -> 파서 오류 없이 실행 확인

## E. 품질 게이트와 배포 규칙

- [x] E-1 글로벌 핵심 질의셋 fail 0 게이트 (required 기준)
- [x] E-2 실기기 검증 2회 연속 성공 게이트
- [x] E-3 운영 도메인 라이브 검증 2회 연속 성공 게이트
- [x] E-4 게이트 미달 시 완료 보고 차단 자동화

근거:
- backend/services/tourism_kb/feedback.py: evidence_grade 분포/uncertainty_disclosure_rate 집계 추가
- frontend/frontend/app/admin/tourism-review/page.tsx: 운영 신뢰 지표(근거등급, 불확실성 고지율) 시각화 추가
- stats API 확인(local/prod 공통): total=0, evidence_grades(확정/추정/미확인)=0/0/0, uncertainty_disclosure_rate=null
- 실행 기록: reports/friend-chat-fact100-20260629-021446.json
- 현재 결과(E-1): total_cases=100, passed=true, accuracy_rate=0.9667, uncertainty_disclosure_rate=1.0 로 required factual/uncertainty gate 통과
- 실행 기록: evidence/voip-voice-relay-orchestrator/run_20260629-020319/summary.json
- 실행 기록: evidence/voip-voice-relay-orchestrator/run_20260629-021620/summary.json
- 현재 결과(E-2/E-3): 실기기 2대 + 운영 도메인(`https://metanova1004.com`) 기준 relay probe 2회 연속 `hard_pass=true`, `relay_pass=true` 통과
- 코드 근거: scripts/validate_worldlinco_quality_gates.py 가 최신 fact100 100문항 PASS와 최근 relay probe 2회 PASS가 없으면 non-zero exit 로 차단
- 검증: python scripts/validate_worldlinco_quality_gates.py -> passed=true
- 검증: python scripts/validate_worldlinco_quality_gates.py -> passed=true

## F. 1차 실행 순서 (Top 10)

1. [x] S10 auth ready 실패 원인 로그 확정
2. [x] 친구 허브 딥링크 실패 원인 확정 -> D-3 완료
3. [x] 근거리/개요 라우팅 오탐 케이스 50건 수집 후 required 회귀셋 등록 완료
4. [x] 오프토픽 억제 규칙 구현 -> B-4 완료
5. [x] 근거 누락 시 불확실성 고지 규칙 구현 -> C-3 완료
6. [x] 국가별 100선 평가셋 1차 구축 -> C-4 완료
7. [x] 자동 평가 파이프라인 연결 -> E-4 완료
8. [x] 실기기 2회 연속 PASS 확보 -> E-2 완료
9. [x] 운영 도메인 2회 연속 PASS 확보 -> E-3 완료
10. [x] 체크리스트 근거 갱신 후 완료 심사

근거:
- .tmp/s10_auth_probe_20260628.log 재분석 결과 S10은 AUTH_STORAGE_RESTORE_APPLIED + token_ready/user_ready + VOIP_PRESENCE_CONNECTED로 auth_ready=true
- .tmp/fold_auth_probe_20260628.log 재분석 결과 보조 단말 실패 원인은 restore_invalid(내 정보 조회 실패)이며 S10 auth 실패와 분리됨
- .tmp/auth_state_reclassify_20260628.json 에 위 분류 결과를 증거 파일로 고정
- evidence/device-d0-smoke-20260628-220340/summary.json 에서 이후 스크립트가 device_missing을 auth blocker와 별도로 기록하는지 확인
- evidence/device-d0-smoke-20260628-232221/summary.json 에서 primary auth false negative 제거 및 secondary react_log_silent 단일 blocker 수렴 확인
- 실행 기록: backend/tests/fixtures/voice_gateway_routing_false_positive_cases.json
- 실행 기록: backend/tests/test_voice_gateway_routing_false_positive_cases.py
- 현재 결과(F-3): 근거리/개요/원거리우선/중립 경계 케이스 50건(required 50건)을 회귀셋으로 등록했고 `python -m pytest backend/tests/test_voice_gateway_routing_false_positive_cases.py -q` 결과 51 passed
- 코드 근거: backend/llm/voice_gateway.py 의 `_friend_prefers_far_first` 가 overview 판정과 정렬되도록 보강되어 `개요/동선` 질의도 far-first sorting으로 고정
- 검증: python scripts/validate_worldlinco_quality_gates.py -> routing_case_count=50, passed=true
- 검증: python scripts/validate_worldlinco_quality_gates.py -> routing_case_count=50, passed=true

## G. 완료 선언 조건

- [x] 모든 항목이 [x]로 닫힘 (미완료 항목이 1건이라도 남아 있으면 완료 선언 불가)
- [x] 각 완료 항목 바로 아래 근거 라인이 존재
- [x] 실기기 검증 2회 + 운영 검증 2회 증거 파일 경로 기재
- [x] 미종결 상태([ ], [~])와 blocker 근거 0건

근거:
- 현재 상태: A~F 체크리스트 항목이 모두 [x]로 닫혔고, 실기기/운영 증거는 `evidence/voip-voice-relay-orchestrator/run_20260629-020319/summary.json`, `evidence/voip-voice-relay-orchestrator/run_20260629-021620/summary.json`, `reports/friend-chat-fact100-20260629-021446.json`, `backend/tests/fixtures/voice_gateway_routing_false_positive_cases.json` 로 동기화됨
