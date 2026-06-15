/** Minimum PCM / proxy RMS (dBFS) to attempt relay STT on meter-dead Android devices. */
export const VOICE_RELAY_FILE_SPEECH_RMS_DB = -58;

function decodeBase64ToBytes(base64: string): Uint8Array | null {
    const trimmed = String(base64 || '').trim();
    if (!trimmed) {
        return null;
    }
    try {
        if (typeof globalThis.atob === 'function') {
            const binary = globalThis.atob(trimmed);
            const bytes = new Uint8Array(binary.length);
            for (let index = 0; index < binary.length; index += 1) {
                bytes[index] = binary.charCodeAt(index);
            }
            return bytes;
        }
    } catch {
        return null;
    }
    return null;
}

function pcm16SamplesFromWav(bytes: Uint8Array): Int16Array | null {
    if (bytes.length < 44 || bytes[0] !== 0x52 || bytes[1] !== 0x49 || bytes[2] !== 0x46 || bytes[3] !== 0x46) {
        return null;
    }

    let offset = 12;
    while (offset + 8 <= bytes.length) {
        const chunkId = String.fromCharCode(bytes[offset], bytes[offset + 1], bytes[offset + 2], bytes[offset + 3]);
        const chunkSize = bytes[offset + 4]
            | (bytes[offset + 5] << 8)
            | (bytes[offset + 6] << 16)
            | (bytes[offset + 7] << 24);
        if (chunkId === 'data') {
            const dataStart = offset + 8;
            const dataEnd = Math.min(bytes.length, dataStart + chunkSize);
            const sampleCount = Math.floor((dataEnd - dataStart) / 2);
            if (sampleCount <= 0) {
                return null;
            }
            const samples = new Int16Array(sampleCount);
            for (let index = 0; index < sampleCount; index += 1) {
                const byteIndex = dataStart + index * 2;
                samples[index] = bytes[byteIndex] | (bytes[byteIndex + 1] << 8);
            }
            return samples;
        }
        offset += 8 + Math.max(0, chunkSize);
    }
    return null;
}

export function estimatePcm16MonoRmsDb(samples: Int16Array): number {
    if (samples.length === 0) {
        return -160;
    }
    let sumSquares = 0;
    for (let index = 0; index < samples.length; index += 1) {
        const sample = samples[index];
        sumSquares += sample * sample;
    }
    const rms = Math.sqrt(sumSquares / samples.length);
    if (rms <= 0) {
        return -160;
    }
    return 20 * Math.log10(rms / 32768);
}

/** AAC/m4a proxy: byte deviation in payload — useful when Expo metering is dead. */
export function estimateCompressedAudioProxyRmsDb(base64: string): number | null {
    const bytes = decodeBase64ToBytes(base64);
    if (!bytes || bytes.length < 256) {
        return null;
    }
    const start = Math.min(bytes.length - 1, Math.floor(bytes.length * 0.08));
    let sumSquares = 0;
    let count = 0;
    for (let index = start; index < bytes.length; index += 1) {
        const centered = bytes[index] - 128;
        sumSquares += centered * centered;
        count += 1;
    }
    if (count === 0) {
        return null;
    }
    const rms = Math.sqrt(sumSquares / count);
    if (rms <= 0) {
        return -160;
    }
    return 20 * Math.log10(rms / 128);
}

export function estimateRecordingRmsDb(base64: string): number | null {
    const bytes = decodeBase64ToBytes(base64);
    if (!bytes) {
        return null;
    }
    const pcm = pcm16SamplesFromWav(bytes);
    if (pcm) {
        return estimatePcm16MonoRmsDb(pcm);
    }
    return estimateCompressedAudioProxyRmsDb(base64);
}

export function mapFileRmsToPseudoMeterDb(rmsDb: number | null): number {
    if (rmsDb === null) {
        return -160;
    }
    return rmsDb >= VOICE_RELAY_FILE_SPEECH_RMS_DB ? -40 : -160;
}

export function shouldSkipSilentVoiceRelayStt(params: {
    peakMeterDb: number;
    hasSpeech: boolean;
    meterUnavailable: boolean;
    audioBase64: string;
}): { skip: boolean; reason?: string; estimatedRmsDb: number | null } {
    const bytes = decodeBase64ToBytes(params.audioBase64);
    const pcm = bytes ? pcm16SamplesFromWav(bytes) : null;
    const pcmRmsDb = pcm ? estimatePcm16MonoRmsDb(pcm) : null;
    const estimatedRmsDb = estimateRecordingRmsDb(params.audioBase64);
    const peakSilent = params.peakMeterDb <= -159;
    const silenceCapture = params.meterUnavailable && peakSilent && !params.hasSpeech;

    // Dead Android metering: ignore AAC byte-proxy RMS; only WAV PCM can override silence skip.
    if (silenceCapture) {
        if (pcmRmsDb !== null && pcmRmsDb >= VOICE_RELAY_FILE_SPEECH_RMS_DB) {
            return { skip: false, estimatedRmsDb: pcmRmsDb };
        }
        return { skip: true, reason: 'silent_capture_no_meter', estimatedRmsDb: pcmRmsDb ?? estimatedRmsDb };
    }

    if (pcmRmsDb !== null && pcmRmsDb >= VOICE_RELAY_FILE_SPEECH_RMS_DB) {
        return { skip: false, estimatedRmsDb: pcmRmsDb };
    }

    if (estimatedRmsDb !== null && estimatedRmsDb >= VOICE_RELAY_FILE_SPEECH_RMS_DB) {
        return { skip: false, estimatedRmsDb };
    }

    if (estimatedRmsDb !== null && estimatedRmsDb < VOICE_RELAY_FILE_SPEECH_RMS_DB) {
        return { skip: true, reason: 'silent_file_rms', estimatedRmsDb };
    }

    return { skip: false, estimatedRmsDb };
}
