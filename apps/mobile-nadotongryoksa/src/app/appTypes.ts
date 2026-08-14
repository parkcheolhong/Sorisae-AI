// App.tsx 에서 분리한 최상위 도메인 타입 모음(타입 전용 모듈).
import type { SectionRailKey } from '../features/navigation/sectionRegistry';
import type { HybridGpsMode } from '../utils/hybridGps';
import type { LangCode } from '../features/language/languageCatalog';

export type VoipParticipantProfile = {
    nickname: string;
    genderLabel: string;
    countryCode: string;
    countryName: string;
    voiceId: string;
    countryFlag: string;
    preferredLanguage?: string;
};

export type DevicePhoneContact = {
    id: string;
    name: string;
    phone: string;
    label: string;
};

export type PurchaseResult = {
    id: number;
    project_id: number;
    buyer_id: number;
    amount: number;
    status: string;
    payment_method: string;
};

export type StoredActiveVoipSession = {
    callId: string;
    railSection?: SectionRailKey | null;
    acceptedParticipantRole?: 'caller' | 'callee' | null;
    acceptedAt?: string | null;
};

export type CallModeAuditEvent = {
    id: number | string;
    event_type: string;
    requested_mode: string | null;
    resolved_mode: string | null;
    call_route?: string | null;
    call_id?: string | null;
    status?: string | null;
    error_code?: string | null;
    auto_relay_requested?: boolean | null;
    auto_relay_applied?: boolean | null;
    created_at: string;
};

export type UserInfo = {
    id: number;
    email: string;
    username?: string;
    preferred_language?: string;
    country_code?: string | null;
};

export type SignupPayload = {
    username: string;
    email: string;
    password: string;
    preferred_language: string;
    country_code?: string | null;
    full_name?: string;
    phone_number?: string;
    verificationChannel?: 'email' | 'phone';
    member_type: 'individual';
    referral_code?: string;
    sales_agent_code?: string;
};

export type UserProfileUpdatePayload = {
    preferred_language: string;
    country_code?: string | null;
};

export type AuthModalMode = 'login' | 'signup';

export type AppEntryDeepLinkTarget =
    | { type: 'rail'; section: SectionRailKey }
    | { type: 'chat'; roomId: string }
    | { type: 'invite'; referralCode: string }
    | { type: 'sales'; salesAgentCode: string }
    | {
        type: 'auth';
        provider?: string;
        accessToken: string;
        refreshToken?: string;
        idToken?: string;
        expiresInSec?: number;
        email?: string;
        userId?: number;
        username?: string;
        displayName?: string;
    }
    | { type: 'voip'; action: 'open' | 'validation' | 'demo' | 'incoming'; callId?: string; calleeVoiceId?: string; forceRetry?: boolean; preferredLanguage?: string; calleePreferredLanguage?: string };

export type SignupRequestCodeResponse = {
    signupSessionToken: string;
    verificationChannel: string;
    maskedTarget: string;
    expiresAt: string;
    devOtpHint?: string;
};

export type SignupSelectionModal = 'language' | 'country' | null;

export type HybridGpsResult = {
    latitude: number;
    longitude: number;
    accuracy: number | null;
    mode: HybridGpsMode;
    qualityScore: number;
    source: 'gps_high' | 'gps_balanced' | 'gps_low' | 'last_known' | 'adb_override' | 'persisted_last_success';
    servicesEnabled: boolean;
    overrideCountryCode?: string;
    overrideRegionHint?: string;
};

export type SongSubtitleEntry = {
    id: string;
    original: string;
    translated: string;
    source: LangCode;
    target: LangCode;
    repeatCount: number;
    detectedBy: 'voice' | 'script' | 'manual' | 'seed';
};

export type SongFileJobStatus = {
    job_id: string;
    status: 'queued' | 'processing' | 'completed' | 'failed';
    stage: string;
    progress: number;
    message: string;
    source_language: string;
    target_language: string;
    segment_count: number;
    quality_score: number;
    error_message?: string | null;
};

export type SongFileTimelineSegment = {
    id: string;
    index: number;
    start_ms: number;
    end_ms: number;
    original: string;
    translated: string;
    source_language: string;
    target_language: string;
    confidence: number;
    detected_by: 'voice' | 'script' | 'manual' | 'seed';
    edited_by_user?: boolean;
    quality_flags?: string[];
};

export type SongFileTimeline = {
    job_id: string;
    source_language: string;
    target_language: string;
    duration_ms: number;
    segment_count: number;
    quality_score: number;
    segments: SongFileTimelineSegment[];
};

export type VoiceLicenseMode = 'self_created' | 'licensed' | 'public_domain' | 'private_preview_unverified' | 'policy_approved_distribution';

export type VoiceOutputScope = 'private_preview' | 'user_saved_preview' | 'policy_review_export' | 'policy_approved_export';

export type VoiceConsentResponse = {
    consent_id: string;
    user_id: string;
    consent_version: string;
    allow_private_preview: boolean;
    allow_export_for_licensed_audio: boolean;
    status: 'active' | 'revoked';
    created_at: string;
};

export type VoiceProfileResponse = {
    voice_profile_id: string;
    profile_label: string;
    sample_duration_ms: number;
    sample_quality_score: number;
    encrypted: boolean;
    status: 'active' | 'revoked' | 'deleted';
};

export type VoicePreviewResponse = {
    preview_id: string;
    gate_status: 'allowed' | 'review_required' | 'blocked';
    policy_allowed: boolean;
    effective_output_scope: VoiceOutputScope;
    message: string;
    segment_count: number;
    duration_ms: number;
    preview_text: string;
    preview_audio_base64?: string | null;
    preview_audio_format?: string | null;
    preview_audio_available?: boolean;
};
