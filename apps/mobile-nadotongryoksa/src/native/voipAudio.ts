import { NativeModules, Platform } from 'react-native';

/**
 * VoIP 통화용 네이티브 오디오 라우팅 브리지.
 *
 * 표준 통화 오디오 스택 근거(docs/worldlinco-v2/MOBILE_CALL_TRANSLATION_ARCHITECTURE.md):
 *  - 통화 동안 AudioManager.MODE_IN_COMMUNICATION 을 강제해 OEM(삼성) 하드웨어 AEC/NS 를 활성화한다.
 *  - 수신측 발화는 단말 내장 스피커로 라우팅한다.
 *  - 통신 모드 음량(STREAM_VOICE_CALL)을 최대로 올려 "음량 작음" 회귀를 차단한다.
 *
 * expo-av 의 setAudioModeAsync 가 Android AudioManager 모드를 건드릴 수 있으므로,
 * expo-av 호출 *이후* 에 enableVoipAudio() 를 재적용해 통신 모드를 유지한다.
 */
type VoipAudioEnableResult = {
    mode: string;
    speakerphone: boolean;
    aec_supported: boolean;
    ns_supported: boolean;
    agc_supported: boolean;
};

type VoipAudioNativeModule = {
    enableVoipAudio: (speakerphone: boolean, maximizeVolume: boolean) => Promise<VoipAudioEnableResult>;
    disableVoipAudio: () => Promise<boolean>;
    setSpeakerphone: (speakerphone: boolean) => Promise<boolean>;
};

const nativeModule = NativeModules.VoipAudio as VoipAudioNativeModule | undefined;

export function isVoipAudioNativeAvailable(): boolean {
    return Platform.OS === 'android' && Boolean(nativeModule?.enableVoipAudio);
}

export async function enableVoipAudio(
    speakerphone: boolean,
    maximizeVolume = true,
): Promise<VoipAudioEnableResult | null> {
    if (!isVoipAudioNativeAvailable()) {
        return null;
    }
    try {
        return await nativeModule!.enableVoipAudio(speakerphone, maximizeVolume);
    } catch {
        return null;
    }
}

export async function disableVoipAudio(): Promise<void> {
    if (!isVoipAudioNativeAvailable()) {
        return;
    }
    try {
        await nativeModule!.disableVoipAudio();
    } catch {
        // no-op
    }
}

export async function setVoipSpeakerphone(speakerphone: boolean): Promise<void> {
    if (!isVoipAudioNativeAvailable()) {
        return;
    }
    try {
        await nativeModule!.setSpeakerphone(speakerphone);
    } catch {
        // no-op
    }
}

/**
 * G10(A-1) — 통화 렌더 경로 TTS 재생 브리지.
 *
 * 통역 TTS 를 네이티브 `AudioTrack`(`USAGE_VOICE_COMMUNICATION`/STREAM_VOICE_CALL)로 재생해
 * 캡처측 HW AEC 참조 루프에 합류시킨다(설계도 §4 / VOIP_AEC_CAPTURE_PLAN.md §3.1·§4).
 * expo-av(USAGE_MEDIA) 와 달리 AEC 가 자기 TTS 를 소거할 수 있어 굶김/자가에코를 근본 차단한다.
 * 네이티브 미가용/실패 시 호출측이 expo-av 경로로 폴백(무회귀).
 */
type VoipTtsPlayResult = {
    played: boolean;
    reason: string;
    sample_rate?: number;
    channels?: number;
};

type VoipTtsPlayerNativeModule = {
    playFile: (path: string) => Promise<VoipTtsPlayResult>;
    stop: () => Promise<boolean>;
};

const ttsPlayerNativeModule = NativeModules.VoipTtsPlayer as VoipTtsPlayerNativeModule | undefined;

export function isVoipTtsPlayerNativeAvailable(): boolean {
    return Platform.OS === 'android' && typeof ttsPlayerNativeModule?.playFile === 'function';
}

/**
 * 통화 렌더 경로로 오디오 파일을 재생하고 재생 완료까지 대기한다.
 * @param path file:// 접두사 없는 로컬 파일 경로
 * @returns true=네이티브 재생 완료, false=재생 불가(폴백 필요)
 */
export async function playVoiceCallTts(path: string): Promise<boolean> {
    if (!isVoipTtsPlayerNativeAvailable()) {
        return false;
    }
    try {
        const result = await ttsPlayerNativeModule!.playFile(path);
        return Boolean(result?.played);
    } catch {
        return false;
    }
}

export async function stopVoiceCallTts(): Promise<void> {
    if (!isVoipTtsPlayerNativeAvailable()) {
        return;
    }
    try {
        await ttsPlayerNativeModule!.stop();
    } catch {
        // no-op
    }
}
