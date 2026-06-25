/**
 * [기능 분리 Phase5.1a] 여행 대면 통역(face-interpretation) 전용 타이밍 상수 SSOT.
 *
 * App.tsx 모놀리스에서 인라인으로 정의돼 있던 대면통역 캡처/재생/에코가드 타이밍을
 * 기능 모듈로 분리한다. 모두 부수효과 없는 순수 상수이므로 안전 추출(디바이스 동작 불변).
 */

/** 여행 대면 통역 — TTS 후 다음 마이크 재개 지연(ms). */
export const FACE_CONVERSATION_RESTART_MS = 250;

/** 여행 대면 통역 — TTS 재생 길이 상한(ms). 초과 시 다음 캡처로 진행. */
export const FACE_CONVERSATION_PLAYBACK_CAP_MS = 10000;

/** 여행 대면 통역 — 마이크 권한 획득 재시도 간격(ms). */
export const FACE_CONVERSATION_PERMISSION_RETRY_MS = 800;

/**
 * 여행 대면 통역 — TTS 재생물이 마이크로 되돌아와 재번역되는 핑퐁 에코를 차단하는 보호창(ms).
 * STT 왕복이 10초 이상 걸릴 수 있어, 에코가 가드창을 지나 도착하지 않도록 넉넉히 잡는다.
 */
export const FACE_CONVERSATION_ECHO_GUARD_MS = 25000;

/** 에코 비교 대상으로 보관할 최근 발화 개수. */
export const FACE_CONVERSATION_SPOKEN_HISTORY = 5;

/**
 * 여행 대면 통역 — TTS 재생 완료 후 잔향이 가라앉을 때까지 듣기를 막는 drain 지연(ms).
 * 이 시간 동안 반이중 게이트(faceSpeakingRef)를 유지해 스피커 잔향을 다시 잡지 않도록 한다.
 */
export const FACE_CONVERSATION_PLAYBACK_DRAIN_MS = 2500;

/**
 * 여행 대면 통역 — 방금 발화한 '출력 언어'로 입력이 되돌아올 때 자기 TTS 에코로 보고 무시하는 창(ms).
 * 재생 종료 직후 마이크가 잡는 잔향(역번역 루프)을 끊는 용도. 실제 상대 화자 응답을 너무 오래
 * 막지 않도록 짧게 잡는다(반이중 게이트 drain 직후의 첫 캡처 잔향만 차단).
 */
export const FACE_OUTPUT_ECHO_GUARD_MS = 5000;
