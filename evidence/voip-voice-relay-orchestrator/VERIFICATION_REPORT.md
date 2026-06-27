# VoIP Voice Relay Orchestrator — Verification Report



> **Updated:** 2026-06-16 (build **69** / `1.0.44`)  

> **Master spec:** `TECHNICAL_REPORT_VOIP_ORCHESTRATOR.md`  

> **Launch status:** `evidence/worldlinco-v1-launch/BUILD69_LAUNCH_STATUS.md`  

> **Architecture:** `docs/VOIP_VOICE_RELAY_ORCHESTRATOR_ARCHITECTURE.md`



---



## APK (current)



| Item | Value |

|------|-------|

| versionName | **1.0.44** |

| versionCode | **69** |

| package | `com.parkcheolhong.worldlinco` |

| Caller (Tab) | `R83W70QY11H` — voice `nado-000226` |

| Callee (S10) | `172.30.1.19:5555` — voice `nado-000001` |

| Marketplace | `uploads/marketplace_local/apk/nadotongryoksa-v1.apk` (~64 MB) |

| Live URL | `https://metanova1004.com/api/marketplace/latest.apk` |



---



## PART E-3 (v1.0 launch DoD)



| Gate | Result | Evidence |

|------|--------|----------|

| E-3-1 WiFi 2대 connected (8/10 DoD) | **PASS** cumulative 8/10 + build66 **5/5** | `e3_verify_20260615-212949` |

| E-3-2 repetition echo | **PASS** | `e3-2_echo_20260615-232900` · repetition **0** |

| E-3-3 beta copy | **PASS** | marketplace + `BETA_LAUNCH_GUIDE.md` |

| E-3-6 50-lang alignment | **PASS** | `50lang_audit_20260615-235805` |

| E-3-7 ko↔ja API | **PASS** | same audit run |

| **E-3-8 ko↔ja VoIP (1차)** | **PASS** | `ko_ja_smoke_20260616-005906` · build 69 |
| **E-3-8 strict ja→ko** | **PASS** | `ko_ja_smoke_20260616-023813` · build **73** · `call-0f44540d27f6` |

| E-3-4 beta users ×10 | **OPEN** (0/10) | `E3-4_beta_users.csv` |

| E-3-5 v1.0.45 APK + tag | **pending** | build **73** APK published |



### E-3-8 detail — build 73 strict PASS (2026-06-16)

| Check | Result |
|-------|--------|
| call_id | `call-0f44540d27f6` |
| S10 `detected_lang` | **ja** |
| S10 transcript | `こんにちは、よろしくお願いします。` |
| S10 relay | **`target_lang=ko`** · `안녕하세요, 잘 부탁드립니다.` |
| Tab `VOIP_VOICE_RELAY_PLAYBACK` | **yes** · `target_lang=ko` |
| Backend accept | **`display_language=ko`** |
| repetition | **0** |

### E-3-8 detail — build 69 (1차, superseded for lang pairing)

| Check | Result |
|-------|--------|
| call_id | `call-71a7256e4490` |
| S10 `detected_lang` | **ja** |
| Tab `VOIP_VOICE_RELAY_PLAYBACK` | **yes** |
| Caveat (fixed in 73) | Tab TTS English (`target_lang=en`) |



---



## Scripts



| Script | Purpose |

|--------|---------|

| `scripts/worldlinco_e3_launch_verify.ps1` | E-3-1 batch |

| `scripts/voip_manual_call_setup.ps1` | Call setup · `-SetupOnly` · `-SetPreferredLanguage` |

| `scripts/worldlinco_ko_ja_voip_smoke.ps1` | **E-3-8** ko↔ja smoke |

| `scripts/worldlinco_50lang_alignment_audit.ps1` | E-3-6/7 |

| `scripts/publish_worldlinco_apk.ps1` | Release build + marketplace |



```powershell

pwsh -File scripts\worldlinco_ko_ja_voip_smoke.ps1 -MonitorSec 70 -StableSec 8

```



---



## Open items



- [ ] E-3-4 ten real-user beta sessions

- [ ] E-3-5 git tag `v1.0.44`

- [ ] ja→ko Tab TTS target_lang pairing

- [ ] cap phase automated summary.json PASS stabilization

- [ ] streaming STT / full-duplex (Phase 2~3)


