import {
    COMPANION_VOICE_CALL_IDLE_MS,
    armCompanionVoiceCall,
    companionVoiceCallRemainingMs,
    createCompanionVoiceCallState,
    disarmCompanionVoiceCall,
    matchCompanionWakeWord,
    markCompanionVoiceCallActivity,
    onCompanionVoiceCallTranscript,
    resolveWakeCandidates,
    shouldCompanionVoiceCallSleep,
    sleepCompanionVoiceCall,
    wakeCompanionVoiceCall,
} from '../features/sorisae/companionVoiceCall';

describe('companionVoiceCall wake-word matching', () => {
    it('matches the configured AI name core (case/space/punct insensitive)', () => {
        expect(matchCompanionWakeWord('루나야 들려?', '루나')).toBe(true);
        expect(matchCompanionWakeWord('헤이 루나!', '루나 AI')).toBe(true);
        expect(matchCompanionWakeWord('LUNA, hello', 'Luna')).toBe(true);
    });

    it('always matches the default "소리새" alias even with a custom name', () => {
        expect(matchCompanionWakeWord('소리새 일어나', '루나')).toBe(true);
        expect(matchCompanionWakeWord('소리새!', null)).toBe(true);
    });

    it('does not match unrelated speech', () => {
        expect(matchCompanionWakeWord('오늘 날씨 어때', '루나')).toBe(false);
        expect(matchCompanionWakeWord('', '루나')).toBe(false);
    });

    it('drops too-short candidates to avoid false positives', () => {
        // 한 글자 이름은 정규화 길이 미달로 후보에서 제외(기본 소리새만 후보).
        const candidates = resolveWakeCandidates('A');
        expect(candidates).not.toContain('a');
        expect(candidates).toContain('소리새');
    });

    it('supports extra aliases', () => {
        expect(matchCompanionWakeWord('자기야 나 왔어', '루나', ['자기야'])).toBe(true);
    });
});

describe('companionVoiceCall state machine', () => {
    it('arms from off to dormant and disarms back to off', () => {
        let s = createCompanionVoiceCallState();
        expect(s.phase).toBe('off');
        s = armCompanionVoiceCall(s);
        expect(s.phase).toBe('dormant');
        s = disarmCompanionVoiceCall(s);
        expect(s.phase).toBe('off');
    });

    it('wakes on wake-word transcript while dormant', () => {
        let s = armCompanionVoiceCall(createCompanionVoiceCallState());
        const r = onCompanionVoiceCallTranscript(s, '소리새야', 1_000, '루나');
        expect(r.event).toBe('wake');
        expect(r.state.phase).toBe('awake');
        expect(r.state.lastActivityMs).toBe(1_000);
    });

    it('ignores non-wake transcript while dormant', () => {
        const s = armCompanionVoiceCall(createCompanionVoiceCallState());
        const r = onCompanionVoiceCallTranscript(s, '밥 먹었어?', 1_000, '루나');
        expect(r.event).toBe('ignored');
        expect(r.state.phase).toBe('dormant');
    });

    it('marks activity (resets idle) on any transcript while awake', () => {
        let s = wakeCompanionVoiceCall(armCompanionVoiceCall(createCompanionVoiceCallState()), 1_000);
        const r = onCompanionVoiceCallTranscript(s, '내일 일정 알려줘', 5_000, '루나');
        expect(r.event).toBe('activity');
        expect(r.state.lastActivityMs).toBe(5_000);
    });

    it('does not mark activity when not awake', () => {
        const dormant = armCompanionVoiceCall(createCompanionVoiceCallState());
        expect(markCompanionVoiceCallActivity(dormant, 9_000)).toBe(dormant);
    });
});

describe('companionVoiceCall 3-minute auto-sleep', () => {
    it('uses 180000ms (3 minutes) as the idle threshold', () => {
        expect(COMPANION_VOICE_CALL_IDLE_MS).toBe(180_000);
    });

    it('sleeps only after the idle threshold elapses while awake', () => {
        const s = wakeCompanionVoiceCall(createCompanionVoiceCallState('dormant'), 0);
        expect(shouldCompanionVoiceCallSleep(s, COMPANION_VOICE_CALL_IDLE_MS - 1)).toBe(false);
        expect(shouldCompanionVoiceCallSleep(s, COMPANION_VOICE_CALL_IDLE_MS)).toBe(true);
    });

    it('never sleeps while dormant or off', () => {
        expect(shouldCompanionVoiceCallSleep(createCompanionVoiceCallState('dormant'), 10_000_000)).toBe(false);
        expect(shouldCompanionVoiceCallSleep(createCompanionVoiceCallState('off'), 10_000_000)).toBe(false);
    });

    it('returns to dormant (re-callable) after sleeping', () => {
        let s = wakeCompanionVoiceCall(createCompanionVoiceCallState('dormant'), 0);
        s = sleepCompanionVoiceCall(s);
        expect(s.phase).toBe('dormant');
        // 다시 부르면 깨어난다.
        const r = onCompanionVoiceCallTranscript(s, '소리새', 200_000, '루나');
        expect(r.event).toBe('wake');
    });

    it('reports remaining countdown ms while awake', () => {
        const s = wakeCompanionVoiceCall(createCompanionVoiceCallState('dormant'), 1_000);
        expect(companionVoiceCallRemainingMs(s, 1_000)).toBe(COMPANION_VOICE_CALL_IDLE_MS);
        expect(companionVoiceCallRemainingMs(s, 1_000 + 60_000)).toBe(COMPANION_VOICE_CALL_IDLE_MS - 60_000);
        expect(companionVoiceCallRemainingMs(createCompanionVoiceCallState('dormant'), 0)).toBeNull();
    });
});
