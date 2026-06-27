import type { VoiceRelayPlaybackItem } from './types';

export class VoiceRelayPlaybackQueue {
    private readonly queue: VoiceRelayPlaybackItem[] = [];
    private processing = false;
    private seqCounter = 0;

    constructor(private readonly playItem: (item: VoiceRelayPlaybackItem) => Promise<void>) {}

    nextSeqId(): number {
        this.seqCounter += 1;
        return this.seqCounter;
    }

    enqueue(item: VoiceRelayPlaybackItem): void {
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
}
