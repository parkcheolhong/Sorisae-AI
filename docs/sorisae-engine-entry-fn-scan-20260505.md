# Sorisae Engine Entry Function Auto-Scan Report
> Generated: 2026-05-05 | Scanned: 121 slot files in `backend/services/shinsegye/engines120/`

## 핵심 발견

| 항목 | 수치 |
|------|------|
| 전체 슬롯 파일 | 121 |
| `main` 함수 보유 | **75개 (62%)** |
| 파싱 오류 | 6개 |
| 빈 슬롯 (함수 없음) | 9개 |
| 기타 진입 함수 보유 | 31개 |

**문제 원인**: 기존 기본 후보 `["run", "execute", "start", "process", "handle"]`에 `main`이 없어서 전체 62% 슬롯이 `module_only` 폴백으로 처리됨.

**조치**: `engine_hub.py _DEFAULT_ADAPTER_ENTRY_CANDIDATES`에 `"main"` 을 1순위로 추가.

---

## 기본 후보 (업데이트됨)

```python
_DEFAULT_ADAPTER_ENTRY_CANDIDATES: tuple[str, ...] = (
    "main",            # 75/121 슬롯
    "run",
    "execute",
    "start",
    "process",
    "handle",
    "run_dashboard",
    "start_server",
    "demo_ethical_gps_system",
)
```

---

## 전체 슬롯별 함수명 표

| 슬롯 파일 | 진입 함수 후보 (top-level defs) | 권장 entry_fn |
|-----------|-------------------------------|--------------|
| slot001_sorisae_voice_movie_server | `main` | `main` |
| slot002_sorisae_iot_voice_control | `main` | `main` |
| slot003_hybrid_conversation_translator | `main` | `main` |
| slot004_sorisae_voice_processor | `_play_audio_file`, `test_voice_processor` | `test_voice_processor` |
| slot005_voice_tuner | `main` | `main` |
| slot006_sorisae_voice_reactive | `_play_audio_file`, `test_voice_reactive`, `main` | `main` |
| slot007_voice_calling_system | `test_voice_calling_system` | `test_voice_calling_system` |
| slot008_hybrid_interpreter_system | `main` | `main` |
| slot009_music_chat_web | `setup_music_chat_interface` | `setup_music_chat_interface` |
| slot010_dream_interpreter | *(없음)* | `module_only` |
| slot011_ai_music_composer | *(없음)* | `module_only` |
| slot012_hybrid_voice_processor | `_play_audio_file_hybrid`, `main` | `main` |
| slot013_multilingual_system | `test_multilingual_system` | `test_multilingual_system` |
| slot014_sorisae_iot_voice_control | `main` | `main` |
| slot015_sorisae_interpreter | `main` | `main` |
| slot016_sorisae_southeast_asia_translator | `main` | `main` |
| slot017_music_chat_system | `get_chat_system` | `get_chat_system` |
| slot018_test_voice_reactive | `run_tests` | `run_tests` |
| slot019_music_chat_friend_system | `get_friend_system`, `demo_friend_system` | `get_friend_system` |
| slot020_voice_command_processor | `main` | `main` |
| slot021_test_animation_voice_integration | `main` + 8개 유틸 | `main` |
| slot022_demo_animation_voice_integration | `main` + 7개 데모 | `main` |
| slot023_sorisae_multilingual_support | `main` | `main` |
| slot024_voice_response_fallback | `get_fallback_response` | `get_fallback_response` |
| slot025_test_socket_voice_fixes | `run_tests` | `run_tests` |
| slot026_test_voice_double_utterance_fix | `main` | `main` |
| slot027_test_integration_voice_error_handling | `main` + 5개 시뮬레이터 | `main` |
| slot028_emotion_based_music_generator | `main` | `main` |
| slot029_animation_studio_theme_song_demo | `animation_studio_theme_song_demo`, `main` | `main` |
| slot030_enhanced_voice_exit | `process_voice_command`, `test_voice_exit`, 외 | `process_voice_command` |
| slot031_ai_speech_tts | `speak`, `test_voice` | `speak` |
| slot032_start_music_chat_server | `start_server` | `start_server` |
| slot033_run_interpreter | `main` | `main` |
| slot034_run_music_composer | `main` | `main` |
| slot035_run_voice_processing | `main` | `main` |
| slot036_spatiotemporal_learning_system | `test_spatiotemporal_learning` | `test_spatiotemporal_learning` |
| slot037_sorisae_enhanced_consciousness | `test_enhanced_consciousness` | `test_enhanced_consciousness` |
| slot038_sorisae_ethical_consciousness_engine | `test_ethical_consciousness_engine` | `test_ethical_consciousness_engine` |
| slot039_hybrid_cyber_security_system | `main` | `main` |
| slot040_sorisae_ai_decision_engine | `test_decision_engine` | `test_decision_engine` |
| slot041_cyber_detective_dashboard | `dashboard`, `handle_dashboard_request`, `main`류 | `dashboard` |
| slot042_hybrid_iot_controller | `main` | `main` |
| slot043_sorisae_iot_integration | `test_iot_integration` | `test_iot_integration` |
| slot044_sorisae_iot_smarthome | `test_iot_system` | `test_iot_system` |
| slot045_sorisae_dual_brain_stock_system | `main` | `main` |
| slot046_cyber_detective_visual_monitoring | `main` | `main` |
| slot047_sorisae_ethical_consciousness_simple | `test_ethical_consciousness` | `test_ethical_consciousness` |
| slot048_sorisae_dual_brain_stock_system | `main` | `main` |
| slot049_advanced_security_system | `main` | `main` |
| slot050_cyber_detective_ai | `demo_cyber_detective` | `demo_cyber_detective` |
| slot051_sorisae_dual_brain_comparison | **PARSE_ERROR** (line 205 unterminated string) | `module_only` |
| slot052_cyber_detective_future_tech | `main` | `main` |
| slot053_sorisae_iot_smarthome | `main` | `main` |
| slot054_sorisae_cyber_investigator | `main` | `main` |
| slot055_sorisae_iot_integration | `main` | `main` |
| slot056_sorisae_iot_auto_discovery | `main` | `main` |
| slot057_cyber_detective_global_server_analysis | `main` | `main` |
| slot058_cyber_detective_global_network | `main` | `main` |
| slot059_cyber_detective_gps_radius | `main` | `main` |
| slot060_cyber_detective_detailed_analysis | `main` | `main` |
| slot061_spatiotemporal_learning_system_new | `test_spatiotemporal_system` | `test_spatiotemporal_system` |
| slot062_cyber_realtime_monitor | *(없음)* | `module_only` |
| slot063_biometric_security_system | `demo_biometric_security`, `main` | `main` |
| slot064_cyber_investigation_report | `main` | `main` |
| slot065_cyber_detective_methodology | `main` | `main` |
| slot066_security_key_manager | `main` | `main` |
| slot067_security_demo_20251019_070650 | `main` | `main` |
| slot068_security_demo | `main` | `main` |
| slot069_consciousness_engine | *(없음)* | `module_only` |
| slot070_run_iot_smarthome | `main` | `main` |
| slot071_run_cyber_detective | `main` | `main` |
| slot072_run_security | `main` | `main` |
| slot073_sorisae_fantasy_vr_infinite_universe_game | `main` | `main` |
| slot074_sorisae_game_economy_system | `main` + datetime adapters | `main` |
| slot075_sorisae_investment_advisor_200 | `main` | `main` |
| slot076_stock_prediction_200_percent | `demonstrate_stock_prediction_200_percent` | `demonstrate_stock_prediction_200_percent` |
| slot077_stock_prediction_200_percent | **PARSE_ERROR** (line 449) | `module_only` |
| slot078_game_earning_analysis | **PARSE_ERROR** (line 203) | `module_only` |
| slot079_sorisae_investment_advisor_200 | `main` | `main` |
| slot080_realtime_game_generator_20251019_182012 | `create_game_response` | `create_game_response` |
| slot081_realtime_game_generator | `create_game_response` | `create_game_response` |
| slot082_sorisae_game_concept_design | `main` | `main` |
| slot083_sorisae_earning_game | `main` | `main` |
| slot084_sorisae_vr_launcher | `main`, `run_demo` | `main` |
| slot085_run_investment_advisor | `main` | `main` |
| slot086_run_game_economy | `main` | `main` |
| slot087_run_vr_games | `main` | `main` |
| slot088_sorisae_core_new_features_20251019_182012 | *(없음)* | `module_only` |
| slot089_sorisae_integrated_dashboard | `run_dashboard`, `main`, `index`, 외 다수 | `main` |
| slot090_sorisae_core_controller_exit_fix_20251019_174426 | *(없음)* | `module_only` |
| slot091_sorisae_animation_studio_ultra | `main` | `main` |
| slot092_ethical_gps_system | `demo_ethical_gps_system`, `main` | `main` |
| slot093_emotion_color_therapist | **PARSE_ERROR** (line 813) | `module_only` |
| slot094_sorisae_dashboard_web | `run_dashboard`, `index`, `verify_api_key`, 외 다수 | `run_dashboard` |
| slot095_integrated_shopping_tutor_designer | `main` | `main` |
| slot096_run_all_shinsegye | `main`, `run_sorisae_engine`, `run_intelligent_sorisae_engine` | `main` |
| slot097_sorisae_master_hybrid_system | `main`, `signal_handler` | `main` |
| slot098_virtual_dev_team | *(없음)* | `module_only` |
| slot099_detailed_technical_report | `generate_detailed_technical_report` | `generate_detailed_technical_report` |
| slot100_sorisae_divine_intelligence_105 | `main` | `main` |
| slot101_organize_projects_into_folders | `main` | `main` |
| slot102_app_Sorisay | `_play_audio_file_app` | `_play_audio_file_app` |
| slot103_sorisae_movie_web_server | `main` | `main` |
| slot104_future_prediction_engine | **PARSE_ERROR** (line 497) | `module_only` |
| slot105_next_gen_caching_system | `main` | `main` |
| slot106_sorisae_master_system | `main` | `main` |
| slot107_run_complete_sorisae_system | `main` | `main` |
| slot108_sorisae_civil_engineering_bidding | `main` | `main` |
| slot109_autonomous_marketing_system | `create_autonomous_marketing_response` | `create_autonomous_marketing_response` |
| slot110_sorisae_transcendent_102 | `main` | `main` |
| slot111_smart_plugin_generator | *(없음)* | `module_only` |
| slot112_ethical_gps_system_simple | `demo_ethical_gps_system` | `demo_ethical_gps_system` |
| slot113_comprehensive_project_analyzer | **PARSE_ERROR** (line 339) | `module_only` |
| slot114_sorisae_smart_car_control | `main` | `main` |
| slot115_sorisae_satellite_wifi_system | `main` | `main` |
| slot116_async_performance_system | *(없음)* | `module_only` |
| slot117_analyze_all_shinsegye_projects | `main` | `main` |
| slot118_sorisae_nextgen_features | `main` | `main` |
| slot119_sorisae_integrated_hybrid_system | `main` | `main` |
| slot120_shopping_mall_dashboard | `start_dashboard_server`, `dashboard`, 외 다수 | `start_dashboard_server` |

---

## 파싱 오류 슬롯 (수정 필요)

| 슬롯 | 오류 위치 | 원인 |
|------|-----------|------|
| slot051_sorisae_dual_brain_comparison | line 205 | unterminated string literal |
| slot077_stock_prediction_200_percent | line 449 | unterminated string literal |
| slot078_game_earning_analysis | line 203 | unterminated string literal |
| slot093_emotion_color_therapist | line 813 | unterminated string literal |
| slot104_future_prediction_engine | line 497 | unterminated string literal |
| slot113_comprehensive_project_analyzer | line 339 | unterminated string literal |

---

## 빈 슬롯 (top-level 함수 없음)

slot010, slot011, slot062, slot069, slot088, slot090, slot098, slot111, slot116

이 슬롯들은 클래스 기반 또는 전역 실행 코드만 있음 → `module_only` 처리가 정상.
