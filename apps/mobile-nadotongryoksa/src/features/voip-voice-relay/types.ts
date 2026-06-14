export type VoiceRelayChunkMeta = {
    seqId: number;
    utteranceId: string;
    chunkIndex: number;
    isFinal: boolean;
    detectedLang?: string;
};

export type VoiceRelayPlaybackItem = {
    seqId: number;
    utteranceId: string;
    chunkIndex: number;
    isFinal: boolean;
    translatedText: string;
    targetLang: string;
    audioUrl?: string;
    audioBase64?: string;
    audioFormat?: string;
};
