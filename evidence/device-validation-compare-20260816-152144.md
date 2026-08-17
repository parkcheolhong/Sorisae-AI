# Device Validation Bundle Compare

- old_bundle: evidence\device-validation-20260816-150743
- new_bundle: evidence\device-validation-rerun-20260816-151754
- old_probe_passed: False
- new_probe_passed: False

## Probe Check Diff
| check | old_ok | new_ok | changed | old_detail | new_detail |
|---|---:|---:|---:|---|---|
| adb_apk_build | True | True | no | device=R83W70QY11H build=331 min=323 | device=R83W70QY11H build=331 min=323 |
| adb_sorisae_runtime | False | False | no | segment_200=False tight_preupload_loop=False hallucination_422=False | segment_200=False tight_preupload_loop=False hallucination_422=False |
| friend_chat_audio_silent_graceful | True | True | no | status=422 detail=음성이 감지되지 않았습니다. 다시 말씀해 주세요. | status=422 detail=음성이 감지되지 않았습니다. 다시 말씀해 주세요. |
| friend_chat_audio_speech_m4a | True | True | no |  |  |
| friend_chat_model_route | True | True | no | base=http://host.docker.internal:8008/v1 model=Qwen/Qwen2.5-Coder-14B-Instruct-AWQ served=['Qwen/Qwen2.5-Coder-14B-Instruct-AWQ'] | base=http://host.docker.internal:8008/v1 model=Qwen/Qwen2.5-Coder-14B-Instruct-AWQ served=['Qwen/Qwen2.5-Coder-14B-Instruct-AWQ'] |
| friend_chat_text_llm | True | True | no | status=200 response_len=251 | status=200 response_len=113 |
| health | True | True | no | status=200 | status=200 |
| m4a_normalize_ssot | True | True | no | docker normalized_bytes=84042 transcript_len=10 | docker normalized_bytes=84042 transcript_len=10 |
| marketplace_manifest | True | True | no | status=200 build=331 min=323 | status=200 build=331 min=323 |

## Auth E2E (rerun bundle)
```json
{
  "base_url": "http://127.0.0.1:8000",
  "email": "119cash@naver.com",
  "login_1": {
    "status": 200,
    "token_issued": true
  },
  "login_2_duplicate_blocked": {
    "status": 409,
    "detail": "이미 다른 기기 또는 세션에서 로그인 상태가 남아 있습니다. 현재 사용 중인 기기가 없다면 계정 복구(본인확인) 후 세션 해제 뒤 다시 시도해 주세요.",
    "matches_mobile_ux": true
  },
  "logout": {
    "status": 204
  },
  "login_3_after_logout": {
    "status": 200,
    "token_issued": true
  }
}
```

## Runtime Tail (new)
```text
08-16 15:11:08.952 11549 11608 I ReactNativeJS:   hasMediaDevices: true }
08-16 15:11:08.967 11549 11608 W ReactNativeJS: This method is deprecated (as well as all React Native Firebase namespaced API) and will be removed in the next major release as part of move to match Firebase Web modular SDK API. Please see migration guide for more details: https://rnfirebase.io/migrating-to-v22 Please use `getApps()` instead.
08-16 15:11:08.968 11549 11608 W ReactNativeJS: This method is deprecated (as well as all React Native Firebase namespaced API) and will be removed in the next major release as part of move to match Firebase Web modular SDK API. Please see migration guide for more details: https://rnfirebase.io/migrating-to-v22 Please use `initializeApp()` instead.
08-16 15:11:08.970 11549 11608 W ReactNativeJS: This method is deprecated (as well as all React Native Firebase namespaced API) and will be removed in the next major release as part of move to match Firebase Web modular SDK API. Please see migration guide for more details: https://rnfirebase.io/migrating-to-v22 Please use `getApps()` instead.
08-16 15:11:08.970 11549 11608 W ReactNativeJS: This method is deprecated (as well as all React Native Firebase namespaced API) and will be removed in the next major release as part of move to match Firebase Web modular SDK API. Please see migration guide for more details: https://rnfirebase.io/migrating-to-v22 Please use `getApp()` instead.
08-16 15:11:08.997 11549 11608 I ReactNativeJS: Running "main"
08-16 15:11:09.245 11549 11608 I ReactNativeJS: '[UI_PRESS_PROBE]', '{"event":"NETWORK_TRANSPORT_CHANGED","timestamp":"2026-08-16T06:11:09.245Z","token_ready":false,"user_ready":false,"show_login":false,"show_voip_tester":false,"selected_call_mode":"pstn_assist","transport":"unknown","cellular_generation":null,"label":"알 수 없음","is_connected":false,"is_internet_reachable":null,"carrier":null,"ssid":null,"is_accurate_voip_test_ready":false,"previous_label":null}'
08-16 15:11:09.248 11549 11608 I ReactNativeJS: '[WORLDLINGCO_API] base_url', 'https://metanova1004.com'
08-16 15:11:09.253 11549 11608 I ReactNativeJS: [VoIPToneService] AudioContext not available (React Native environment)
08-16 15:11:09.256 11549 11608 I ReactNativeJS: '[FACE_CONVERSATION]', '{"event":"silero_probe","supported":false}'
08-16 15:11:09.267 11549 11608 I ReactNativeJS: '[DEEP_LINK_TRACE]', '{"source":"initial_url","outcome":"empty_url"}'
08-16 15:11:09.352 11549 11608 W ReactNativeJS: This  ...[truncated]
```