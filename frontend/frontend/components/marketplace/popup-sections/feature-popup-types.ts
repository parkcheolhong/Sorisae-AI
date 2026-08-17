import type { FeaturePopupState } from '@/hooks/use-feature-orchestrator';

export interface PopupEventLogItem {
    state: FeaturePopupState;
    at: string;
}

export interface PopupQualityReview {
    passed?: boolean;
    score?: number;
    issues?: string[];
    checks?: Record<string, boolean>;
}
