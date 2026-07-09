/**
 * 소리새 companion arm/disarm + dormant 마이크 워치독.
 */
import { useEffect } from 'react';
import type { MutableRefObject, RefObject } from 'react';
import { Platform } from 'react-native';

import type { CompanionVoiceCallState } from './companionVoiceCall';

export type CompanionArmEffectsDeps = {
    userInfo: unknown;
    showLogin: boolean;
    sorisaeWindowOpen: boolean;
    /** false면 로그인 후 자동 dormant arm 안 함(홈 호명 비사용). */
    companionAutoArmEnabled: boolean;
    /** 소리새 dormant 마이크를 멈춰야 하는 화면 단위 상태. */
    companionArmSuspended: boolean;
    companionVoiceCallArmedRef: RefObject<boolean>;
    companionVoiceCallRef: RefObject<CompanionVoiceCallState>;
    companionKwsActiveRef: RefObject<boolean>;
    sorisaeWindowOpenRef: RefObject<boolean>;
    companionDormantRecoverBlockedUntilRef: RefObject<number>;
    recordingRef: RefObject<unknown>;
    voiceInputStartInFlightRef: RefObject<boolean>;
    voiceInputStopInFlightRef: RefObject<boolean>;
    autoVoiceModeEnabledRef: RefObject<boolean>;
    voiceInputTargetRef: MutableRefObject<string>;
    setCompanionVoiceCallArmedState: (armed: boolean) => Promise<void>;
    setCompanionVoiceCallArmed: (armed: boolean) => void;
    setAutoVoiceModeEnabled: (v: boolean) => void;
    startVoiceInput: (opts?: { autoMode?: boolean }) => void;
};

/** 로그인·홈 대기 시 companion arm, 화면 단위 suspended 상태일 때만 disarm. */
function isCompanionMicBlocked(deps: CompanionArmEffectsDeps): boolean {
    return deps.companionArmSuspended;
}

/** 로그인·홈 대기 시 companion arm, suspended 상태면 disarm. */
export function useCompanionArmableEffect(deps: CompanionArmEffectsDeps): void {
    const {
        userInfo,
        showLogin,
        sorisaeWindowOpen,
        companionAutoArmEnabled,
        companionArmSuspended,
        companionVoiceCallArmedRef,
        setCompanionVoiceCallArmedState,
    } = deps;

    useEffect(() => {
        if (Platform.OS === 'web') return;
        const micBlocked = isCompanionMicBlocked(deps);
        const armable = companionAutoArmEnabled
            && !!userInfo
            && !showLogin
            && !sorisaeWindowOpen
            && !micBlocked;
        console.log('[COMPANION_VOICE_CALL]', JSON.stringify({
            event: 'armable_eval',
            armable,
            auto_arm: companionAutoArmEnabled,
            has_user: !!userInfo,
            show_login: !!showLogin,
            sorisae_window_open: !!sorisaeWindowOpen,
            companion_arm_suspended: companionArmSuspended,
            armed: companionVoiceCallArmedRef.current,
        }));
        if (armable && !companionVoiceCallArmedRef.current) {
            void setCompanionVoiceCallArmedState(true);
        } else if (companionVoiceCallArmedRef.current && (!armable || micBlocked)) {
            void setCompanionVoiceCallArmedState(false);
        }
    }, [
        userInfo,
        showLogin,
        sorisaeWindowOpen,
        companionAutoArmEnabled,
        companionArmSuspended,
        setCompanionVoiceCallArmedState,
    ]);
}

/** dormant 대기 중 마이크 루프 자동 복구(백오프 존중). auto-arm 꺼져 있으면 no-op. */
export function useCompanionDormantWatchdogEffect(deps: CompanionArmEffectsDeps): void {
    useEffect(() => {
        if (Platform.OS === 'web' || !deps.companionAutoArmEnabled) return undefined;
        const timer = setInterval(() => {
            const now = Date.now();
            const dormantPhase = deps.companionVoiceCallRef.current?.phase === 'dormant';
            const micBlocked = isCompanionMicBlocked(deps);
            const shouldRecover = !deps.sorisaeWindowOpenRef.current
                && deps.companionVoiceCallArmedRef.current
                && dormantPhase
                && !deps.companionKwsActiveRef.current
                && !micBlocked
                && now >= deps.companionDormantRecoverBlockedUntilRef.current
                && !deps.recordingRef.current
                && !deps.voiceInputStartInFlightRef.current
                && !deps.voiceInputStopInFlightRef.current;
            if (!shouldRecover) {
                console.log('[COMPANION_VOICE_CALL]', JSON.stringify({
                    event: 'dormant_watchdog_skip',
                    armed: deps.companionVoiceCallArmedRef.current,
                    kws_active: deps.companionKwsActiveRef.current,
                    sorisae_window_open: deps.sorisaeWindowOpenRef.current,
                    companion_arm_suspended: deps.companionArmSuspended,
                    phase: deps.companionVoiceCallRef.current?.phase,
                    recording: !!deps.recordingRef.current,
                    start_inflight: deps.voiceInputStartInFlightRef.current,
                    stop_inflight: deps.voiceInputStopInFlightRef.current,
                    auto_voice: deps.autoVoiceModeEnabledRef.current,
                    blocked_until_ms: deps.companionDormantRecoverBlockedUntilRef.current,
                }));
                return;
            }
            deps.voiceInputTargetRef.current = 'main';
            if (!deps.autoVoiceModeEnabledRef.current) {
                deps.autoVoiceModeEnabledRef.current = true;
                deps.setAutoVoiceModeEnabled(true);
            }
            if (!deps.companionVoiceCallArmedRef.current) {
                deps.companionVoiceCallArmedRef.current = true;
                deps.setCompanionVoiceCallArmed(true);
            }
            console.log('[COMPANION_VOICE_CALL]', JSON.stringify({ event: 'dormant_watchdog_recover' }));
            void deps.startVoiceInput({ autoMode: true });
        }, 2500);
        return () => clearInterval(timer);
    }, [
        deps.startVoiceInput,
        deps.companionArmSuspended,
        deps.companionAutoArmEnabled,
    ]);
}
