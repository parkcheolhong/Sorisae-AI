/**
 * App.tsx → useVoiceCaptureLoop SSOT 브리지.
 */
import { useEffect } from 'react';

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
    const stopFacePlayback = async () => {
        await stopFaceVoicePlayback(ctx.faceVoicePlaybackSoundRef);
        ctx.faceSpeakingRef.current = false;
    };

    const stopSorisaePlayback = async () => {
        await stopFaceVoicePlayback(ctx.sorisaeVoicePlaybackSoundRef);
        ctx.sorisaeSpeakingRef.current = false;
    };

    const deps: VoiceCaptureLoopDeps = {
        ...ctx,
        playFaceTranslationOutput,
        stopFacePlayback,
        stopSorisaePlayback,
        reportFaceVoiceAutoTuningMetric,
        reportConversationEchoGuardMetric: () => { /* telemetry reserved */ },
    };

    const { startVoiceInput, stopVoiceInput } = useVoiceCaptureLoop(deps);

    useEffect(() => {
        ctx.stopVoiceInputRef.current = stopVoiceInput;
    }, [ctx.stopVoiceInputRef, stopVoiceInput]);

    return { startVoiceInput, stopVoiceInput };
}
