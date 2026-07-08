import type { VoiceRelayPlaybackItem } from './types';

export class VoiceRelayPlaybackQueue {
    private readonly queue: VoiceRelayPlaybackItem[] = [];
    private readonly acceptedKeys = new Set<string>();
    private processing = false;
    private seqCounter = 0;

    constructor(private readonly playItem: (item: VoiceRelayPlaybackItem) => Promise<void>) {}

    nextSeqId(): number {
        this.seqCounter += 1;
        return this.seqCounter;
    }

    enqueue(item: VoiceRelayPlaybackItem): void {
        const itemKey = this.buildDedupKey(item);
        if (this.acceptedKeys.has(itemKey)) {
            return;
        }
        this.acceptedKeys.add(itemKey);
        this.queue.push(item);
        this.queue.sort((left, right) => {
            if (left.seqId !== right.seqId) {
                return left.seqId - right.seqId;
            }
            if (left.utteranceId !== right.utteranceId) {
                return left.utteranceId.localeCompare(right.utteranceId);
            }
            return left.chunkIndex - right.chunkIndex;
        });
        void this.drain();
    }

    clear(): void {
        this.queue.length = 0;
        this.acceptedKeys.clear();
    }

    get pendingCount(): number {
        return this.queue.length;
    }

    private async drain(): Promise<void> {
        if (this.processing) {
            return;
        }

        this.processing = true;
        try {
            while (this.queue.length > 0) {
                const next = this.queue.shift();
                if (!next) {
                    break;
                }
                await this.playItem(next);
            }
        } finally {
            this.processing = false;
            if (this.queue.length > 0) {
                void this.drain();
            }
        }
    }

    private buildDedupKey(item: VoiceRelayPlaybackItem): string {
        const correlation = String(item.correlationId ?? '').trim();
        if (correlation) {
            return `corr:${correlation}`;
        }
        return [
            item.utteranceId,
            item.chunkIndex,
            item.seqId,
            item.targetLang,
            item.translatedText,
            item.isFinal ? '1' : '0',
        ].join('|');
    }
}
