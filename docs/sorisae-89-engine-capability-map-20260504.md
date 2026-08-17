<!-- FILE-ID: FILE-DOCS-SORISAE-89-ENGINE-CAPABILITY-MAP-20260504 -->
<!-- SECTION-ID: SECTION-SORISAE-89-ENGINE-CAPABILITY-MAP -->
<!-- FEATURE-ID: FEATURE-SORISAE-ENGINE-GROUP-DOCUMENTATION -->
<!-- CHUNK-ID: CHUNK-SORISAE-ENGINE-GROUP-DOCUMENTATION-001 -->

# Sorisae 89 Engine Capability Map

## Scope

- Source of truth: `backend/services/shinsegye/engine_hub.py` `SORISAE_ENGINE_REGISTRY`
- Registry size: `89`
- Structure: `10` functional groups (`A` to `J`)
- Verified facts already closed before this document:
  - Full registry import validation in backend container: `TOTAL_KEYS 89`, `FAILED_IMPORTS 0`
  - Authenticated HTTP validation passed for `/api/marketplace/sorisae/engines`
  - Authenticated HTTP validation passed for `/api/marketplace/sorisae/dispatch` with `security` engine

## Checklist

- [x] Registry source re-read from `engine_hub.py`
- [x] `89` engine keys counted by group
- [x] Functional grouping synchronized to a real document
- [ ] Backend-only restart and post-restart representative engine verification

## Group Summary

| Group | Domain | Count | Primary outcome |
| --- | --- | ---: | --- |
| A | Core intelligence and consciousness | 15 | High-level reasoning, orchestration, ethics, quantum-style decisioning |
| B | Voice and language | 14 | Speech, translation, multilingual dialogue, interpreter flows |
| C | Music and creative generation | 13 | Composition, animation, movie planning, game generation |
| D | Emotion, therapy, dream | 3 | Emotional support, dream interpretation, ethical guidance |
| E | Future prediction and investment | 4 | Forecasting, stock analysis, investment advisory |
| F | IoT and smart systems | 8 | Smart home, IoT control, satellite, smart car |
| G | Security and cyber investigation | 12 | Security hardening, forensics, cyber monitoring |
| H | Business and commerce | 4 | Marketing, commerce dashboards, bidding workflows |
| I | Development and performance | 7 | Plugins, virtual dev team, analysis, caching, dashboard |
| J | Compatibility aliases | 9 | Backward-compatible public keys for existing integrations |

## Group A. Core Intelligence and Consciousness

Usage map: Use this group when the request is strategic, multi-step, high-level, or needs routing hints rather than a narrow single-domain tool.

| Engine key | Slot file | Focus |
| --- | --- | --- |
| `decision` | `slot040_sorisae_ai_decision_engine.py` | Prompt analysis and routing |
| `divine` | `slot100_sorisae_divine_intelligence_105.py` | Maximal reasoning tier |
| `transcendent` | `slot110_sorisae_transcendent_102.py` | Transcendent composite reasoning |
| `master` | `slot106_sorisae_master_system.py` | Master controller |
| `master_hybrid` | `slot097_sorisae_master_hybrid_system.py` | Hybrid master orchestration |
| `integrated` | `slot119_sorisae_integrated_hybrid_system.py` | Fully integrated hybrid core |
| `dual_brain` | `slot051_sorisae_dual_brain_comparison.py` | Comparative multi-brain reasoning |
| `consciousness` | `slot037_sorisae_enhanced_consciousness.py` | Enhanced consciousness layer |
| `consciousness_engine` | `slot069_consciousness_engine.py` | Core consciousness engine |
| `ethics` | `slot038_sorisae_ethical_consciousness_engine.py` | Ethical decision engine |
| `ethics_simple` | `slot047_sorisae_ethical_consciousness_simple.py` | Lightweight ethical reasoning |
| `quantum` | `slot118_sorisae_nextgen_features.py` | Quantum, multiverse, DNA-personalized features |
| `spacetime` | `slot061_spatiotemporal_learning_system_new.py` | New spatiotemporal learning |
| `spatiotemporal` | `slot036_spatiotemporal_learning_system.py` | Legacy spatiotemporal learning |
| `core_features` | `slot088_sorisae_core_new_features_20251019_182012.py` | Extended core feature pack |

## Group B. Voice and Language

Usage map: Use this group for voice I/O, speech response, multilingual support, translation, and interpreter-style interaction.

| Engine key | Slot file | Focus |
| --- | --- | --- |
| `voice_movie` | `slot001_sorisae_voice_movie_server.py` | Voice plus movie workflow |
| `voice_processor` | `slot004_sorisae_voice_processor.py` | Core speech processing |
| `voice_tuner` | `slot005_voice_tuner.py` | Voice tuning |
| `voice_reactive` | `slot006_sorisae_voice_reactive.py` | Reactive voice behavior |
| `voice_calling` | `slot007_voice_calling_system.py` | Voice calling system |
| `voice_hybrid` | `slot012_hybrid_voice_processor.py` | Hybrid voice processor |
| `voice_command` | `slot020_voice_command_processor.py` | Voice command control |
| `voice_fallback` | `slot024_voice_response_fallback.py` | Fallback response path |
| `interpreter` | `slot015_sorisae_interpreter.py` | Interpreter workflow |
| `hybrid_interpreter` | `slot008_hybrid_interpreter_system.py` | Hybrid interpreter |
| `multilingual` | `slot013_multilingual_system.py` | Multilingual runtime |
| `multilingual_support` | `slot023_sorisae_multilingual_support.py` | Broader multilingual support |
| `translator` | `slot003_hybrid_conversation_translator.py` | Translation engine |
| `southeast_asia` | `slot016_sorisae_southeast_asia_translator.py` | Regional translation specialization |

## Group C. Music and Creative Generation

Usage map: Use this group for composition, story-world creation, animation, movie planning, games, and monetizable creative output.

| Engine key | Slot file | Focus |
| --- | --- | --- |
| `music` | `slot011_ai_music_composer.py` | Music composition |
| `music_chat` | `slot017_music_chat_system.py` | Music-oriented chat |
| `music_chat_web` | `slot009_music_chat_web.py` | Web music chat |
| `music_chat_friend` | `slot019_music_chat_friend_system.py` | Music companion system |
| `emotion_music` | `slot028_emotion_based_music_generator.py` | Emotion-based music generation |
| `animation_theme` | `slot029_animation_studio_theme_song_demo.py` | Animation theme song generation |
| `animation` | `slot091_sorisae_animation_studio_ultra.py` | Animation studio |
| `movie` | `slot103_sorisae_movie_web_server.py` | Movie workflow |
| `game` | `slot081_realtime_game_generator.py` | Real-time game generation |
| `game_concept` | `slot082_sorisae_game_concept_design.py` | Game concept design |
| `game_economy` | `slot074_sorisae_game_economy_system.py` | Game economy system |
| `earning_game` | `slot083_sorisae_earning_game.py` | Revenue-oriented game system |
| `vr` | `slot073_sorisae_fantasy_vr_infinite_universe_game.py` | VR universe game |

## Group D. Emotion, Therapy, Dream

Usage map: Use this group for wellness, affect analysis, dream interpretation, and softer human-facing guidance flows.

| Engine key | Slot file | Focus |
| --- | --- | --- |
| `emotion_therapy` | `slot093_emotion_color_therapist.py` | Emotion-color therapy |
| `dream` | `slot010_dream_interpreter.py` | Dream interpretation |
| `ethical_gps` | `slot092_ethical_gps_system.py` | Ethical life guidance |

## Group E. Future Prediction and Investment

Usage map: Use this group for forecasting, trend prediction, stock-oriented analysis, and investment advice.

| Engine key | Slot file | Focus |
| --- | --- | --- |
| `future_prediction` | `slot104_future_prediction_engine.py` | Future prediction engine |
| `stock` | `slot045_sorisae_dual_brain_stock_system.py` | Stock system |
| `stock_prediction` | `slot076_stock_prediction_200_percent.py` | Aggressive stock prediction |
| `investment` | `slot075_sorisae_investment_advisor_200.py` | Investment advisor |

## Group F. IoT and Smart Systems

Usage map: Use this group for device discovery, home automation, connected infrastructure, vehicle control, and satellite-backed network ideas.

| Engine key | Slot file | Focus |
| --- | --- | --- |
| `iot` | `slot043_sorisae_iot_integration.py` | IoT integration |
| `iot_core` | `slot055_sorisae_iot_integration.py` | IoT core |
| `iot_voice` | `slot014_sorisae_iot_voice_control.py` | Voice-controlled IoT |
| `iot_discovery` | `slot056_sorisae_iot_auto_discovery.py` | IoT auto discovery |
| `hybrid_iot` | `slot042_hybrid_iot_controller.py` | Hybrid IoT controller |
| `smarthome` | `slot044_sorisae_iot_smarthome.py` | Smart home assistant |
| `smart_car` | `slot114_sorisae_smart_car_control.py` | Smart car control |
| `satellite` | `slot115_sorisae_satellite_wifi_system.py` | Satellite Wi-Fi system |

## Group G. Security and Cyber Investigation

Usage map: Use this group for hardening, security posture, monitoring, investigation, forensics, and global cyber analysis.

| Engine key | Slot file | Focus |
| --- | --- | --- |
| `security` | `slot049_advanced_security_system.py` | Advanced security system |
| `hybrid_security` | `slot039_hybrid_cyber_security_system.py` | Hybrid security system |
| `biometric` | `slot063_biometric_security_system.py` | Biometric security |
| `security_key` | `slot066_security_key_manager.py` | Security key management |
| `detective` | `slot050_cyber_detective_ai.py` | Cyber detective |
| `detective_dashboard` | `slot041_cyber_detective_dashboard.py` | Detective dashboard |
| `visual_monitor` | `slot046_cyber_detective_visual_monitoring.py` | Visual monitoring |
| `cyber_future_tech` | `slot052_cyber_detective_future_tech.py` | Future investigation tech |
| `cyber_investigator` | `slot054_sorisae_cyber_investigator.py` | Cyber investigation |
| `global_cyber_monitor` | `slot057_cyber_detective_global_server_analysis.py` | Global server analysis |
| `gps_investigation` | `slot059_cyber_detective_gps_radius.py` | GPS investigation |
| `cyber_realtime` | `slot062_cyber_realtime_monitor.py` | Real-time cyber monitoring |

## Group H. Business and Commerce

Usage map: Use this group for commerce workflows, marketing automation, shopping assistance, and bidding-style business analysis.

| Engine key | Slot file | Focus |
| --- | --- | --- |
| `marketing` | `slot109_autonomous_marketing_system.py` | Autonomous marketing |
| `shopping` | `slot120_shopping_mall_dashboard.py` | Shopping mall dashboard |
| `shopping_tutor` | `slot095_integrated_shopping_tutor_designer.py` | Shopping, tutor, designer workflow |
| `civil_engineering` | `slot108_sorisae_civil_engineering_bidding.py` | Civil engineering bidding |

## Group I. Development and Performance

Usage map: Use this group for software-building assistance, plugin generation, project analysis, folder organization, caching, dashboards, and runtime performance.

| Engine key | Slot file | Focus |
| --- | --- | --- |
| `plugin` | `slot111_smart_plugin_generator.py` | Plugin generation |
| `virtual_team` | `slot098_virtual_dev_team.py` | Virtual development team |
| `analyzer` | `slot113_comprehensive_project_analyzer.py` | Project analyzer |
| `project_organizer` | `slot101_organize_projects_into_folders.py` | Project organizer |
| `caching` | `slot105_next_gen_caching_system.py` | Next-gen caching |
| `async_performance` | `slot116_async_performance_system.py` | Async performance |
| `integrated_dashboard` | `slot089_sorisae_integrated_dashboard.py` | Integrated dashboard |

## Group J. Compatibility Aliases

Usage map: These keys preserve older integrations and alternate public names. They should not be counted as separate capability domains.

| Alias key | Slot file | Canonical relation |
| --- | --- | --- |
| `movie_server` | `slot103_sorisae_movie_web_server.py` | Alias of `movie` |
| `movie_web` | `slot103_sorisae_movie_web_server.py` | Alias of `movie` |
| `calling` | `slot007_voice_calling_system.py` | Alias of `voice_calling` |
| `hybrid_voice` | `slot012_hybrid_voice_processor.py` | Alias of `voice_hybrid` |
| `music_friend` | `slot019_music_chat_friend_system.py` | Alias of `music_chat_friend` |
| `iot_voice_control` | `slot014_sorisae_iot_voice_control.py` | Alias of `iot_voice` |
| `stock_200` | `slot076_stock_prediction_200_percent.py` | Alias of `stock_prediction` |
| `security_key_manager` | `slot066_security_key_manager.py` | Alias of `security_key` |
| `realtime_monitor` | `slot062_cyber_realtime_monitor.py` | Alias of `cyber_realtime` |

## Recommended Dispatch Coverage

Representative engines to keep using for smoke validation after backend restart:

| Group | Recommended engine | Reason |
| --- | --- | --- |
| A | `decision` | Lightweight core reasoning smoke test |
| B | `multilingual` | Covers `googletrans`, TTS, multilingual runtime |
| F | `smarthome` | Covers `paho-mqtt` and IoT simulation path |
| G | `security` | Already validated over authenticated HTTP dispatch |

## Runtime Notes

- `googletrans`, `paho-mqtt`, `pygame`, and `PyAudio` were added to runtime requirements.
- `build-essential`, `espeak-ng`, `alsa-utils`, and `portaudio19-dev` were added to backend image build for voice/audio runtime closure.
- A backend-only restart is still the remaining executable verification step for the newly rebuilt image.
