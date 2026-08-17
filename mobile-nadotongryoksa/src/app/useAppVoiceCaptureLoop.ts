/**
 * App.tsx → useVoiceCaptureLoop SSOT 브리지.
 */
import { useCallback, useEffect, useMemo } from 'react';

import { playFaceTranslationOutput, stopFaceVoicePlayback } from './appFaceVoicePlayback';
import { useVoiceCaptureLoop } from '../features/sorisae/useVoiceCaptureLoop';
import type { VoiceCaptureLoopDeps } from '../features/sorisae/voiceCaptureLoopTypes';
import { reportFaceVoiceAutoTuningMetric } from '../services/worldlincoTuningConfig';

export type AppVoiceCaptureLoopContext = Omit<
    VoiceCaptureLoopDeps,
    | 'playFaceTranslationOutput'
    | 'stopFacePlayback'
    | 'stopSorisaePlayback'
    | 'reportFaceVoiceAutoTuningMetric'
    | 'reportConversationEchoGuardMetric'
>;

export function useAppVoiceCaptureLoop(ctx: AppVoiceCaptureLoopContext) {
    const stopFacePlayback = useCallback(async () => {
        await stopFaceVoicePlayback(ctx.faceVoicePlaybackSoundRef);
        ctx.faceSpeakingRef.current = false;
    }, [ctx.faceSpeakingRef, ctx.faceVoicePlaybackSoundRef]);

    const stopSorisaePlayback = useCallback(async () => {
        await stopFaceVoicePlayback(ctx.sorisaeVoicePlaybackSoundRef);
        ctx.sorisaeSpeakingRef.current = false;
    }, [ctx.sorisaeSpeakingRef, ctx.sorisaeVoicePlaybackSoundRef]);

    const reportConversationEchoGuardMetric = useCallback(() => {
        // telemetry reserved
    }, []);

    const deps: VoiceCaptureLoopDeps = useMemo(() => ({
        ...ctx,
        playFaceTranslationOutput,
        stopFacePlayback,
        stopSorisaePlayback,
        reportFaceVoiceAutoTuningMetric,
        reportConversationEchoGuardMetric,
    }), [ctx, reportConversationEchoGuardMetric, stopFacePlayback, stopSorisaePlayback]);

    const { startVoiceInput, stopVoiceInput } = useVoiceCaptureLoop(deps);

    useEffect(() => {
        ctx.stopVoiceInputRef.current = stopVoiceInput;
    }, [ctx.stopVoiceInputRef, stopVoiceInput]);

    return { startVoiceInput, stopVoiceInput };
}
