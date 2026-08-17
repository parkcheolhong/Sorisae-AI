# Mobile Real Device Validation Checklist (2026-08-13)

## Target
- Device serial: R83W70QY11H
- App package: com.parkcheolhong.worldlinco
- APK path: C:\\codeAI\\apps\\mobile-nadotongryoksa\\android\\app\\build\\outputs\\apk\\debug\\app-debug.apk

## Checklist
- [x] ADB single target connectivity verified
- [x] Fresh APK install/upgrade success on target device
- [x] App process launches without immediate crash
- [x] Runtime permission state 확인 (mic/location/notification)
- [x] Login delay 계측 (실사용 계정 기준)
- [x] Settings toggle 실반영 확인 (터치 전/후)
- [x] Audio route/volume 차단 해제 확인

## Blocking Issue (Real Device)
- 상태: 해제 완료
- 해제된 이슈 1: Firebase `databaseURL` 누락 오류 해소 후 본문/설정 화면 진입 복구
- 해제된 이슈 2: 로그인 지연 실측값 기록(`run18_metrics_summary.txt`, ResultMs=44)
- 해제된 이슈 3: `expo-notifications: Custom sound 'default' not found` 미재현 확인(`run18_logcat_after_sound_fix.txt`, MatchCount=0)

## Evidence Log
- 상태: 완료
- 근거 파일: apps/mobile-nadotongryoksa/evidence/device-validation-20260813/

## Latest Verified Outcome
- Firebase 런타임 복구 확인: 더 이상 `Missing or invalid FirebaseOptions property 'databaseURL'` 재발 로그 없음(최신 Metro 출력 기준).
- 설정 화면 진입 복구 확인: `run14_screen.png`
- 수신 알림 토글 반영 확인: `무음` 화면(`run14_screen.png`) -> `소리` 화면(`run15_after_alert_toggle_sound.png`), 텍스트 `현재 수신 알림: 🔊 소리` 확인.
- 권한 상태 확인: 설정 화면 내 `마이크 권한 허용됨`, `위치 권한 허용됨` 노출 (`run15_after_alert_toggle_sound.png`).
- 로그인 실측 로그 추가: 자동복구 이벤트 시점 기반 지표 파일 `run16_metrics_summary.txt` 생성(Found→Applied 약 41~48ms 샘플).
- run17 실측 갱신: `run17_metrics_summary.txt` 생성, `LOGIN_SUBMIT_PRESS`/`LOGIN_SESSION_APPLIED` 마커 부재로 submit->applied 지연값은 `N/A` 기록.
- 로그인 상태 실확인: `run17_login_confirm_after_minimize_seq.png`에서 `AUTH_DEBUG_STATE: AUTHENTICATED`, `AUTH_DEBUG_USER: 6|burumi69@gmail.com` 확인.
- custom sound 경고 집계: `run17_key_runtime_events.log` 기준 72회 집계.
- run18 수정 검증: `run18_logcat_after_sound_fix.txt`에서 custom sound 경고 패턴 미검출(0회).
- 로그인 지연 수치 확정: `run18_metrics_summary.txt` ResultMs=44.
- run20 릴리스 실기기 검증: 로그인 완료 상태, 음성 호출 대기 ON, 채팅 핵심 레일 진입 확인(`run20_release_validation_summary.txt`).
- run22 직접 오픈 검증: 대면 통역/소리새AI 모두 차단 배너 없이 직접 진입 확인(`run22_face_sorisae_block_check_summary.txt`).

## Verification Runs
- Run 1: 완료
  - adb 연결: run1_adb_devices.txt
  - apk 설치: run1_install.txt
  - 패키지 확인: run1_package_list.txt
  - 앱 실행/PID: run1_launch.txt, run1_pidof.txt
  - 권한/버전: run1_permissions_and_version.txt
  - 화면 캡처: run1_screen_after_launch.png
  - 로그 필터: run1_logcat_filtered.txt
- Run 2: 완료
  - 강제종료 후 콜드스타트 시간: run2_launch_timing.txt
  - 앱 PID: run2_pidof.txt
  - 화면 캡처: run2_screen_after_cold_start.png
  - 화면 XML: run2_window.xml
- Run 3: 완료 (dev 연결 시도)
  - reverse 연결: run3_reverse_8081.txt
  - exp 링크 시도: run3_open_exp_link.txt
  - 화면 캡처: run3_screen_after_exp_link.png
  - 화면 XML: run3_window.xml
- Run 4: 완료 (custom scheme 연결 시도)
  - 화면 캡처: run4_screen_after_custom_scheme.png
  - 화면 XML: run4_window.xml
  - expo 로그: run4_expo_start_tail.log
  - logcat 오류: run4_logcat_firebase_error.txt
- Run 10: 완료 (본문 복구 검증)
  - 화면 캡처: run10_screen.png
  - 화면 XML: run10_window.xml
- Run 14: 완료 (설정 화면 진입)
  - 화면 캡처: run14_screen.png
  - 화면 XML: run14_window.xml
- Run 15: 완료 (설정 토글/권한 상태)
  - 토글 전/후: run14_screen.png, run15_after_alert_toggle_sound.png
  - 권한 상태 화면: run15_after_alert_toggle_sound.png
- Run 16: 완료 (실측 로그 추가)
 	- Metro tail: run16_expo_tail_1200.log
 	- 런타임 핵심 이벤트: run16_key_runtime_events.log
 	- ADB 런타임 포커스 로그: run16_adb_runtime_focus.log
 	- 실측 요약: run16_metrics_summary.txt
- Run 17: 완료 (신규 로그인 계측/경고 집계 증적 보강)
 	- 앱 데이터 초기화: run17_pm_clear.txt
 	- 콜드 런치 타이밍: run17_launch_timing.txt
 	- 로그인 폼 준비 화면: run17_login_form_ready.png
 	- 로그인 후 상태 화면(LogBox 경고 노출): run17_after_login_state.png
 	- 런타임 이벤트 추출: run17_key_runtime_events.log
 	- ADB 로그 덤프: run17_logcat_dump.txt
 	- 실측 요약: run17_metrics_summary.txt
- Run 18: 완료 (경고 수정 검증 + 최종 수치 확정)
 	- 콜드 런치 타이밍: run18_launch_timing.txt
 	- 수정 후 로그 검증: run18_logcat_after_sound_fix.txt
 	- 상태 화면 증적: run18_post_fix_state.png
 	- 최종 요약: run18_metrics_summary.txt
- Run 20: 완료 (릴리스 APK 실기기 플로우 검증)
 	- 로그인 완료 상태: run20_after_login_confirm.png
 	- 음성 호출 대기 ON: run20_voice_wait_toggle.png
 	- 채팅 핵심 레일 진입: run20_chat_rail_entry.png
 	- 입력 지연 개선 증적: run20_login_lag_fix_typed.png, run20_login_gfxinfo_after_fix.txt
 	- 최종 요약: run20_release_validation_summary.txt
- Run 22: 완료 (대면 통역/소리새AI 차단 배너 재검증)
 	- 로그인 후 상태: run22_after_login_confirm.png
 	- 대면 통역 직접 오픈: run22_face_translate_open.png
 	- 소리새AI 직접 오픈: run22_sorisae_open_retry.png
 	- 최종 요약: run22_face_sorisae_block_check_summary.txt
