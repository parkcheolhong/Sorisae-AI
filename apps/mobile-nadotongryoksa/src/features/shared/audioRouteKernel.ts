import { disableVoipAudio, enableVoipAudio, setVoipSpeakerphone } from '../../native/voipAudio';

export async function enableConversationCaptureAudio(): Promise<void> {
    // Keep earpiece-oriented capture path for better near-field speech pickup.
    await enableVoipAudio(false, false);
}

export async function enableConversationPlaybackAudio(): Promise<void> {
    // Playback path should be audible and consistent across devices.
    await enableVoipAudio(true, true);
    await setVoipSpeakerphone(true);
}

export async function disableConversationAudio(): Promise<void> {
    await disableVoipAudio();
}
