import type { MutableRefObject } from 'react';
import type { AudioSound } from '../../compat/expoAvAudio';

export type SorisaeVoiceInputTarget = 'main' | 'inter_call';

export type SorisaeStartVoiceInputOptions = {
    autoMode?: boolean;
    target?: SorisaeVoiceInputTarget;
};

export type SorisaeStopVoiceInputOptions = {
    suppressAutoRestart?: boolean;
    discardSegment?: boolean;
};

export type SorisaePlaybackSoundRef = MutableRefObject<AudioSound | null>;

export type SorisaeRuntimeAdapter = {
    startVoiceInput: (opts?: SorisaeStartVoiceInputOptions) => void;
    stopVoiceInput: (opts?: SorisaeStopVoiceInputOptions) => Promise<void>;
    stopPlayback: (soundRef: SorisaePlaybackSoundRef) => Promise<void>;
};

export function createSorisaeRuntimeAdapter(adapter: SorisaeRuntimeAdapter): SorisaeRuntimeAdapter {
    return adapter;
}
