export type VoiceRelayChunkMeta = {
    seqId: number;
    utteranceId: string;
    chunkIndex: number;
    isFinal: boolean;
    detectedLang?: string;
    // V.2 ID 백본 — 캡처 시점 고유 상관 ID(기능 ID 자동 매핑→셀프 서빙→전송(딜리버리)→음성 발화 자동 연결).
    correlationId?: string;
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
    // V.2 ID 백본 — 이 발화 아이템이 어느 상관 ID에서 왔는지 자가 식별.
    correlationId?: string;
};
