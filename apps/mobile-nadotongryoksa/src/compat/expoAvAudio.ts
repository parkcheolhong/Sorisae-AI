import { PermissionStatus } from 'expo';
import {
    AudioModule,
    AudioQuality,
    createAudioPlayer,
    getRecordingPermissionsAsync,
    requestRecordingPermissionsAsync,
    setAudioModeAsync as setExpoAudioModeAsync,
    type RecordingOptions as ExpoRecordingOptions,
} from 'expo-audio';

type AudioPlayer = ReturnType<typeof createAudioPlayer>;
type AudioRecorder = InstanceType<typeof AudioModule.AudioRecorder>;

type LegacyAudioMode = {
    allowsRecordingIOS?: boolean;
    playsInSilentModeIOS?: boolean;
    shouldDuckAndroid?: boolean;
    playThroughEarpieceAndroid?: boolean;
    staysActiveInBackground?: boolean;
};

type LegacyRecordingOptions = {
    isMeteringEnabled?: boolean;
    keepAudioActiveHint?: boolean;
    android?: {
        extension?: string;
        outputFormat?: number | string;
        audioEncoder?: number | string;
        sampleRate?: number;
        numberOfChannels?: number;
        bitRate?: number;
    };
    ios?: {
        extension?: string;
        outputFormat?: number | string;
        audioQuality?: number;
        sampleRate?: number;
        numberOfChannels?: number;
        bitRate?: number;
        linearPCMBitDepth?: number;
        linearPCMIsBigEndian?: boolean;
        linearPCMIsFloat?: boolean;
    };
    web?: {
        mimeType?: string;
        bitsPerSecond?: number;
    };
};

const ANDROID_OUTPUT_FORMAT: Record<number, ExpoRecordingOptions['android']['outputFormat']> = {
    0: 'default',
    1: '3gp',
    2: 'mpeg4',
    3: 'amrnb',
    4: 'amrwb',
    6: 'aac_adts',
};

const ANDROID_AUDIO_ENCODER: Record<number, ExpoRecordingOptions['android']['audioEncoder']> = {
    0: 'default',
    1: 'amr_nb',
    2: 'amr_wb',
    3: 'aac',
    4: 'he_aac',
    5: 'aac_eld',
};

function mapAndroidOutputFormat(value?: number | string): ExpoRecordingOptions['android']['outputFormat'] {
    if (typeof value === 'string') {
        return value as ExpoRecordingOptions['android']['outputFormat'];
    }
    if (typeof value === 'number') {
        return ANDROID_OUTPUT_FORMAT[value] ?? 'mpeg4';
    }
    return 'mpeg4';
}

function mapAndroidAudioEncoder(value?: number | string): ExpoRecordingOptions['android']['audioEncoder'] {
    if (typeof value === 'string') {
        return value as ExpoRecordingOptions['android']['audioEncoder'];
    }
    if (typeof value === 'number') {
        return ANDROID_AUDIO_ENCODER[value] ?? 'aac';
    }
    return 'aac';
}

function mapRecordingOptions(options: LegacyRecordingOptions): ExpoRecordingOptions {
    const android = options.android ?? {};
    const ios = options.ios ?? {};
    const extension = android.extension ?? ios.extension ?? '.m4a';
    return {
        extension,
        sampleRate: android.sampleRate ?? ios.sampleRate ?? 44_100,
        numberOfChannels: android.numberOfChannels ?? ios.numberOfChannels ?? 1,
        bitRate: android.bitRate ?? ios.bitRate ?? 64_000,
        isMeteringEnabled: options.isMeteringEnabled ?? false,
        android: {
            extension: android.extension ?? extension,
            sampleRate: android.sampleRate,
            outputFormat: mapAndroidOutputFormat(android.outputFormat),
            audioEncoder: mapAndroidAudioEncoder(android.audioEncoder),
        },
        ios: {
            extension: ios.extension ?? extension,
            sampleRate: ios.sampleRate,
            audioQuality: (ios.audioQuality ?? AudioQuality.MEDIUM) as AudioQuality,
            linearPCMBitDepth: ios.linearPCMBitDepth,
            linearPCMIsBigEndian: ios.linearPCMIsBigEndian,
            linearPCMIsFloat: ios.linearPCMIsFloat,
        },
        web: options.web,
    };
}

function mapAudioMode(mode: LegacyAudioMode) {
    return {
        allowsRecording: mode.allowsRecordingIOS ?? false,
        playsInSilentMode: mode.playsInSilentModeIOS ?? true,
        shouldPlayInBackground: mode.staysActiveInBackground ?? false,
        shouldRouteThroughEarpiece: mode.playThroughEarpieceAndroid ?? false,
        interruptionMode: mode.shouldDuckAndroid ? 'duckOthers' as const : 'doNotMix' as const,
    };
}

function toPermissionResponse(response: { granted: boolean; status: string }) {
    return {
        granted: response.granted,
        status: response.status,
        expires: 'never' as const,
        canAskAgain: response.status !== PermissionStatus.DENIED,
    };
}

class Sound {
    private readonly player: AudioPlayer;
    private playbackListener: { remove: () => void } | null = null;

    private constructor(player: AudioPlayer) {
        this.player = player;
    }

    static async createAsync(
        source: { uri?: string } | string | number,
        initialStatus?: { shouldPlay?: boolean; isLooping?: boolean; volume?: number },
    ): Promise<{ sound: Sound }> {
        const normalizedSource = typeof source === 'object' && source !== null && 'uri' in source
            ? source.uri ?? null
            : source;
        const player = createAudioPlayer(normalizedSource, { updateInterval: 500 });
        const sound = new Sound(player);
        if (typeof initialStatus?.volume === 'number') {
            player.volume = initialStatus.volume;
        }
        if (initialStatus?.isLooping) {
            player.loop = true;
        }
        if (initialStatus?.shouldPlay) {
            player.play();
        }
        return { sound };
    }

    async playAsync(): Promise<void> {
        this.player.play();
    }

    async pauseAsync(): Promise<void> {
        this.player.pause();
    }

    async stopAsync(): Promise<void> {
        this.player.pause();
        await this.player.seekTo(0);
    }

    async unloadAsync(): Promise<void> {
        this.playbackListener?.remove();
        this.playbackListener = null;
        this.player.remove();
    }

    async getStatusAsync() {
        return {
            isLoaded: this.player.isLoaded,
            isPlaying: this.player.playing,
            didJustFinish: false,
        };
    }

    setOnPlaybackStatusUpdate(
        callback: (status: { isLoaded?: boolean; didJustFinish?: boolean; isPlaying?: boolean }) => void,
    ): void {
        this.playbackListener?.remove();
        this.playbackListener = this.player.addListener('playbackStatusUpdate', (status) => {
            callback({
                isLoaded: status.isLoaded,
                didJustFinish: status.didJustFinish,
                isPlaying: status.playing,
            });
        });
    }

    async setProgressUpdateIntervalAsync(_intervalMs: number): Promise<void> {
        // expo-audio sets update interval at player creation time.
    }
}

class Recording {
    private recorder: AudioRecorder;

    constructor() {
        this.recorder = new AudioModule.AudioRecorder(mapRecordingOptions({
            android: { outputFormat: 2, audioEncoder: 3, extension: '.m4a' },
            ios: { extension: '.m4a', audioQuality: AudioQuality.MEDIUM },
            web: { mimeType: 'audio/webm', bitsPerSecond: 128_000 },
        }));
    }

    static async createAsync(options: LegacyRecordingOptions): Promise<{ recording: Recording }> {
        const recording = new Recording();
        await recording.prepareToRecordAsync(options);
        await recording.startAsync();
        return { recording };
    }

    async prepareToRecordAsync(options: LegacyRecordingOptions): Promise<void> {
        await this.recorder.prepareToRecordAsync(mapRecordingOptions(options));
    }

    async startAsync(): Promise<void> {
        this.recorder.record();
    }

    async stopAndUnloadAsync(): Promise<void> {
        await this.recorder.stop();
    }

    getURI(): string | null {
        return this.recorder.uri;
    }

    async getStatusAsync() {
        const status = this.recorder.getStatus();
        return {
            isRecording: status.isRecording,
            metering: status.metering,
            durationMillis: status.durationMillis,
        };
    }
}

export const Audio = {
    AndroidOutputFormat: {
        DEFAULT: 0,
        THREE_GPP: 1,
        MPEG_4: 2,
        AMR_NB: 3,
        AMR_WB: 4,
        AAC_ADTS: 6,
    },
    AndroidAudioEncoder: {
        DEFAULT: 0,
        AMR_NB: 1,
        AMR_WB: 2,
        AAC: 3,
        HE_AAC: 4,
        AAC_ELD: 5,
    },
    IOSAudioQuality: {
        MIN: AudioQuality.MIN,
        LOW: AudioQuality.LOW,
        MEDIUM: AudioQuality.MEDIUM,
        HIGH: AudioQuality.HIGH,
        MAX: AudioQuality.MAX,
    },
    RecordingOptionsPresets: {
        HIGH_QUALITY: {
            web: { mimeType: 'audio/webm', bitsPerSecond: 128_000 },
        },
    },
    Sound,
    Recording,
    async setAudioModeAsync(mode: LegacyAudioMode): Promise<void> {
        await setExpoAudioModeAsync(mapAudioMode(mode));
    },
    async requestPermissionsAsync() {
        return toPermissionResponse(await requestRecordingPermissionsAsync());
    },
    async getPermissionsAsync() {
        return toPermissionResponse(await getRecordingPermissionsAsync());
    },
};

export type RecordingOptions = LegacyRecordingOptions;
