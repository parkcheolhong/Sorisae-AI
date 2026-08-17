import { useCallback, useMemo, useRef } from 'react';

import {
    useCompanionArmableEffect,
    useCompanionDormantWatchdogEffect,
    type CompanionArmEffectsDeps,
} from './useCompanionArmEffects';
import {
    createSorisaeRuntimeAdapter,
    type SorisaeRuntimeAdapter,
    type SorisaeStartVoiceInputOptions,
    type SorisaeStopVoiceInputOptions,
} from './runtimeAdapter';
import {
    activateFeatureExclusive,
    deactivateFeatureExclusive,
} from '../isolation/fourFeatureRuntime';
import { useSorisaeVoicePipeline, type SorisaeVoicePipelineDeps } from './useSorisaeVoicePipeline';

type SorisaeVoicePipelineFacadeDeps = Omit<SorisaeVoicePipelineDeps, 'runtimeAdapter'> & {
    stopPlayback: SorisaeRuntimeAdapter['stopPlayback'];
};

type SorisaeVoiceCaptureControls = {
    startVoiceInput: (opts?: SorisaeStartVoiceInputOptions) => void;
    stopVoiceInput: (opts?: SorisaeStopVoiceInputOptions) => Promise<void>;
};

export type SorisaePluginFacadeDeps = SorisaeVoicePipelineFacadeDeps;

type SorisaePipelineResult = ReturnType<typeof useSorisaeVoicePipeline>;

export type SorisaePluginFacade = SorisaePipelineResult & {
    bindVoiceCaptureControls: (controls: SorisaeVoiceCaptureControls) => void;
    stopVoiceInputBridgeRef: React.MutableRefObject<((options?: { suppressAutoRestart?: boolean; discardSegment?: boolean }) => Promise<void>) | null>;
};

type SorisaeCompanionLifecycleFacadeDeps = Omit<CompanionArmEffectsDeps,
    | 'companionVoiceCallArmedRef'
    | 'companionVoiceCallRef'
    | 'companionKwsActiveRef'
    | 'setCompanionVoiceCallArmedState'
    | 'setCompanionVoiceCallArmed'
> & {
    plugin: Pick<SorisaePluginFacade,
        | 'companionVoiceCallArmedRef'
        | 'companionVoiceCallRef'
        | 'companionKwsActiveRef'
        | 'setCompanionVoiceCallArmedState'
        | 'setCompanionVoiceCallArmed'
    >;
};

export function useSorisaePluginFacade(deps: SorisaePluginFacadeDeps): SorisaePluginFacade {
    const startVoiceInputBridgeRef = useRef<(opts?: SorisaeStartVoiceInputOptions) => void>(() => { });
    const stopVoiceInputBridgeRef = useRef<((options?: { suppressAutoRestart?: boolean; discardSegment?: boolean }) => Promise<void>) | null>(null);

    const bindVoiceCaptureControls = useCallback((controls: SorisaeVoiceCaptureControls) => {
        startVoiceInputBridgeRef.current = (opts) => {
            void (async () => {
                const activation = await activateFeatureExclusive('sorisae-ai', 'sorisae_voice_start', 'system');
                if (!activation.ok) {
                    console.warn('[SORISAE_EXCLUSIVE_BLOCKED]', JSON.stringify(activation));
                    return;
                }
                controls.startVoiceInput(opts ?? {});
            })();
        };
        stopVoiceInputBridgeRef.current = async (opts) => {
            try {
                await controls.stopVoiceInput(opts ?? {});
            } finally {
                deactivateFeatureExclusive('sorisae-ai', 'sorisae_voice_stop', 'system');
            }
        };
    }, []);

    const runtimeAdapter = useMemo(() => createSorisaeRuntimeAdapter({
        startVoiceInput: (opts) => {
            startVoiceInputBridgeRef.current(opts ?? {});
        },
        stopVoiceInput: (opts) => stopVoiceInputBridgeRef.current?.(opts) ?? Promise.resolve(),
        stopPlayback: deps.stopPlayback,
    }), [deps.stopPlayback]);

    const pipeline = useSorisaeVoicePipeline({
        ...deps,
        runtimeAdapter,
    });

    return {
        ...pipeline,
        bindVoiceCaptureControls,
        stopVoiceInputBridgeRef,
    };
}

export function useSorisaeCompanionLifecycleFacade(deps: SorisaeCompanionLifecycleFacadeDeps): void {
    const { plugin, ...rest } = deps;

    const effectDeps: CompanionArmEffectsDeps = {
        ...rest,
        companionVoiceCallArmedRef: plugin.companionVoiceCallArmedRef,
        companionVoiceCallRef: plugin.companionVoiceCallRef,
        companionKwsActiveRef: plugin.companionKwsActiveRef,
        setCompanionVoiceCallArmedState: plugin.setCompanionVoiceCallArmedState,
        setCompanionVoiceCallArmed: plugin.setCompanionVoiceCallArmed,
    };

    useCompanionArmableEffect(effectDeps);
    useCompanionDormantWatchdogEffect(effectDeps);
}
