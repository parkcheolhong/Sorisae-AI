# Phase 7.6 — 오디오 격리 실기기 검증 (2026-07-09)

**빌드:** 1.0.241 / **317**  
**단말:** R83W70QY11H (SM-T225N)  
**EAS:** https://expo.dev/accounts/parkcheolhong/projects/nadotongryoksa/builds/29f2974f-5f10-48ca-b183-96aadaedc76d  
**APK:** https://expo.dev/artifacts/eas/WqG9MkyZrW0OBxjJD6kWJ3SUSnRJQZmcBF8SHjkaZhg.apk

## 자동 프리플라이트 (완료)

| 검사 | 결과 |
|------|------|
| adb install 317 | Success |
| 앱 cold start 크래시 | 없음 (`boot-317.log`) |
| APK 번들 Phase7 태그 | `VOIP_SESSION_GUARD`, `quiesce_voip`, `quiesce_pstn` 포함 |
| 로컬 marketplace API | `build_number=317` |
| 운영 marketplace API | `build_number=317` |

## 수동 시나리오 (테스터 조작 필요)

스크립트: `scripts/run_phase7_audio_isolation_device_smoke.ps1`

| ID | 시나리오 | 기대 로그 |
|----|----------|-----------|
| 7.6-A | 대면 ON → VoIP 친구 발신 | `quiesce_voip`, `VOICE_LEASE revoke` |
| 7.6-B | 대면 ON → PSTN 발신 | `quiesce_pstn` |
| 7.6-C | PSTN 종료 → 대면/VoIP 재시작 | lease `release`, pstn deactivate |
| 7.6-D | 수신 VoIP 수락 | `quiesce_voip` before accept |

## 증적 파일

- `boot-317.log` — cold start logcat
