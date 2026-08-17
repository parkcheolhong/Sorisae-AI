export type AdminDirectivePanelAgentOption = {
    key: string;
    label: string;
    summary: string;
    modelKey: string;
};

export type AdminDirectivePanelFeature = {
    key: string;
    title: string;
    description: string;
    lockedMode: string;
    lockedLogics: string[];
};

export type AdminDirectivePanelConversationMessage = {
    role: string;
    content: string;
    speaker?: string;
    timestamp?: string;
};

export type AdminDirectivePanelMarketplaceOffer = {
    id: string;
    title: string;
    subtitle: string;
    description: string;
    priceLabel: string;
    badge: string;
    tags: string[];
    primaryActionLabel: string;
    secondaryActionLabel: string;
};

export interface AdminDirectivePanelProps {
    chatAgentKey: string;
    voiceAgentKey: string;
    llmConfiguredModels?: Record<string, string> | null;
    orchestratorAgentOptions: AdminDirectivePanelAgentOption[];
    mandatoryRules: string[];
    optionalRules: string[];
    enabledRules: string[];
    onToggleRule: (rule: string) => void;
    routedTextFeatures: AdminDirectivePanelFeature[];
    textFeatureAgents: Record<string, string>;
    onUpdateTextFeatureAgent: (featureKey: string, agentKey: string) => void;
    onSetChatAgentKey: (agentKey: string) => void;
    onSetVoiceAgentKey: (agentKey: string) => void;
    continueInPlace: boolean;
    onSetContinueInPlace: (value: boolean) => void;
    workOutputDir: string;
    onSetWorkOutputDir: (value: string) => void;
    chatFunctionMode: string;
    onSetChatFunctionMode: (value: string) => void;
    conversation: AdminDirectivePanelConversationMessage[];
    examples: string[];
    onApplyExample: (value: string) => void;
    chatInput: string;
    onSetChatInput: (value: string) => void;
    chatLoading: boolean;
    onPushUserMessage: () => Promise<void>;
    loading: boolean;
    canRun: boolean;
    onRun: () => Promise<void>;
    onStartVoiceInput: () => void;
    voiceListening: boolean;
    liveOutputDir: string;
    lastWebResultsCount: number;
    marketplaceOffers: AdminDirectivePanelMarketplaceOffer[];
    onApplyMarketplaceOffer: (offerId: string) => void;
    onOpenMarketplace: () => void;
}
