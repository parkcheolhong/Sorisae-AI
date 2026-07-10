export type FourFeatureId =
    | 'face-translate'
    | 'voip-call'
    | 'pstn-assist'
    | 'sorisae-ai';

export type SharedResourceKey =
    | 'mic-capture'
    | 'tts-playback'
    | 'voice-session'
    | 'network-stream'
    | 'ui-focus';

export type FeatureLifecycleCommand =
    | 'start'
    | 'stop'
    | 'pause'
    | 'resume'
    | 'quiesce';

export type LifecycleCommandInput = {
    featureId: FourFeatureId;
    command: FeatureLifecycleCommand;
    reason: string;
    source: 'user' | 'system' | 'auto';
    atMs: number;
};

export type FeatureInputSnapshot = {
    authReady: boolean;
    preferredLanguage: string;
    targetLanguage: string;
    networkOnline: boolean;
    activeRailSection: string | null;
};

export type FeatureOutputEvent =
    | {
        type: 'status';
        featureId: FourFeatureId;
        message: string;
        atMs: number;
      }
    | {
        type: 'error';
        featureId: FourFeatureId;
        code: string;
        message: string;
        atMs: number;
      }
    | {
        type: 'resource-claim';
        featureId: FourFeatureId;
        resource: SharedResourceKey;
        atMs: number;
      }
    | {
        type: 'resource-release';
        featureId: FourFeatureId;
        resource: SharedResourceKey;
        atMs: number;
      };

export type ResourceRequirement = {
    resource: SharedResourceKey;
    exclusive: boolean;
};

export type FourFeatureContract = {
    id: FourFeatureId;
    version: 'v1';
    requiredResources: ResourceRequirement[];
};

export const FOUR_FEATURE_CONTRACTS: Record<FourFeatureId, FourFeatureContract> = {
    'face-translate': {
        id: 'face-translate',
        version: 'v1',
        requiredResources: [
            { resource: 'mic-capture', exclusive: true },
            { resource: 'tts-playback', exclusive: true },
            { resource: 'ui-focus', exclusive: false },
        ],
    },
    'voip-call': {
        id: 'voip-call',
        version: 'v1',
        requiredResources: [
            { resource: 'voice-session', exclusive: true },
            { resource: 'network-stream', exclusive: true },
            { resource: 'mic-capture', exclusive: true },
            { resource: 'tts-playback', exclusive: true },
            { resource: 'ui-focus', exclusive: false },
        ],
    },
    'pstn-assist': {
        id: 'pstn-assist',
        version: 'v1',
        requiredResources: [
            { resource: 'mic-capture', exclusive: true },
            { resource: 'tts-playback', exclusive: true },
            { resource: 'ui-focus', exclusive: false },
        ],
    },
    'sorisae-ai': {
        id: 'sorisae-ai',
        version: 'v1',
        requiredResources: [
            { resource: 'mic-capture', exclusive: true },
            { resource: 'tts-playback', exclusive: true },
            { resource: 'ui-focus', exclusive: false },
        ],
    },
};
