import type { FourFeatureId } from './fourFeatureContracts';

export type FeatureEntrypointMap = {
    featureId: FourFeatureId;
    filePath: string;
    startSymbol: string;
    stopSymbol: string;
    notes: string;
};

// This map is a code-level split plan snapshot based on current runtime wiring.
// It is intentionally static and side-effect free.
export const FOUR_FEATURE_ENTRYPOINTS: FeatureEntrypointMap[] = [
    {
        featureId: 'face-translate',
        filePath: 'apps/mobile-nadotongryoksa/App.tsx',
        startSymbol: 'handleToggleFaceConversation',
        stopSymbol: 'handleToggleFaceConversation',
        notes: 'Face translate voice loop toggles via one handler in App runtime.',
    },
    {
        featureId: 'voip-call',
        filePath: 'apps/mobile-nadotongryoksa/src/features/voip-auto/useVoipAutoController.ts',
        startSymbol: 'initiateVoipCall',
        stopSymbol: 'requestEndVoipCall',
        notes: 'VoIP call lifecycle spans controller + API client stop endpoint.',
    },
    {
        featureId: 'pstn-assist',
        filePath: 'apps/mobile-nadotongryoksa/src/features/pstn-assist/usePstnAssistController.ts',
        startSymbol: 'startPstnAssistDialFlow',
        stopSymbol: 'openDialPad',
        notes: 'PSTN assist starts dial flow and returns control to system dialer.',
    },
    {
        featureId: 'sorisae-ai',
        filePath: 'apps/mobile-nadotongryoksa/src/features/sorisae/sorisaePluginFacade.ts',
        startSymbol: 'useSorisaePluginFacade',
        stopSymbol: 'useSorisaeCompanionLifecycleFacade',
        notes: 'Sorisae runtime + companion lifecycle orchestration are facade-owned.',
    },
];
