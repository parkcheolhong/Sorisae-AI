// [기능 분리 Phase3] VOIP 상태 도메인.
// 일반전화(useInterCallState)와 물리적으로 분리해, VOIP+채팅 기능이 일반전화+예약 기능과
// 상태를 공유하지 않도록 한다. useCallModeController 가 이 훅을 합성(compose)한다.
import { useCallback, useState, type Dispatch, type SetStateAction } from 'react';
import type { CallInitResponse } from '../../services/voipCallClient';
import { CallMode, DEFAULT_CALL_MODE } from './types';

export type VoipParticipantProfile = {
    nickname: string;
    genderLabel: string;
    countryCode: string;
    countryName: string;
    voiceId: string;
    countryFlag: string;
    preferredLanguage?: string;
};

export type CallModeAuditEvent = {
    id: number | string;
    event_type: string;
    requested_mode: string | null;
    resolved_mode: string | null;
    call_route?: string | null;
    status?: string | null;
    error_code?: string | null;
    created_at: string;
};

export type PendingIncomingVoipCall = CallInitResponse & {
    caller_label?: string;
    caller_voice_id?: string;
};

export type VoipState = {
    selectedCallMode: CallMode;
    setCallMode: (nextMode: CallMode) => void;
    voipValidationOverride: boolean;
    setVoipValidationOverride: (value: boolean) => void;
    showVoipTester: boolean;
    setShowVoipTester: (value: boolean) => void;
    showFriendFolder: boolean;
    setShowFriendFolder: Dispatch<SetStateAction<boolean>>;
    voipCallInitResponse: CallInitResponse | null;
    setVoipCallInitResponse: (value: CallInitResponse | null) => void;
    pendingIncomingVoipCall: PendingIncomingVoipCall | null;
    setPendingIncomingVoipCall: (value: PendingIncomingVoipCall | null) => void;
    voipAuditCallId: string;
    setVoipAuditCallId: (value: string) => void;
    voipAuditEvents: CallModeAuditEvent[];
    setVoipAuditEvents: Dispatch<SetStateAction<CallModeAuditEvent[]>>;
    voipAuditLoading: boolean;
    setVoipAuditLoading: (value: boolean) => void;
    voipAuditError: string;
    setVoipAuditError: (value: string) => void;
    voipIdentity: string;
    setVoipIdentity: (value: string) => void;
    voipActiveProfile: VoipParticipantProfile | null;
    setVoipActiveProfile: Dispatch<SetStateAction<VoipParticipantProfile | null>>;
};

export function useVoipState(initialMode: CallMode = DEFAULT_CALL_MODE): VoipState {
    const [selectedCallMode, setSelectedCallMode] = useState<CallMode>(initialMode);
    const [voipValidationOverride, setVoipValidationOverride] = useState(false);
    const [showVoipTester, setShowVoipTester] = useState(false);
    const [showFriendFolder, setShowFriendFolder] = useState(false);
    const [voipCallInitResponse, setVoipCallInitResponse] = useState<CallInitResponse | null>(null);
    const [pendingIncomingVoipCall, setPendingIncomingVoipCall] = useState<PendingIncomingVoipCall | null>(null);
    const [voipAuditCallId, setVoipAuditCallId] = useState('');
    const [voipAuditEvents, setVoipAuditEvents] = useState<CallModeAuditEvent[]>([]);
    const [voipAuditLoading, setVoipAuditLoading] = useState(false);
    const [voipAuditError, setVoipAuditError] = useState('');
    const [voipIdentity, setVoipIdentity] = useState('');
    const [voipActiveProfile, setVoipActiveProfile] = useState<VoipParticipantProfile | null>(null);

    const setCallMode = useCallback((nextMode: CallMode) => {
        setSelectedCallMode(nextMode);
    }, []);

    return {
        selectedCallMode,
        setCallMode,
        voipValidationOverride,
        setVoipValidationOverride,
        showVoipTester,
        setShowVoipTester,
        showFriendFolder,
        setShowFriendFolder,
        voipCallInitResponse,
        setVoipCallInitResponse,
        pendingIncomingVoipCall,
        setPendingIncomingVoipCall,
        voipAuditCallId,
        setVoipAuditCallId,
        voipAuditEvents,
        setVoipAuditEvents,
        voipAuditLoading,
        setVoipAuditLoading,
        voipAuditError,
        setVoipAuditError,
        voipIdentity,
        setVoipIdentity,
        voipActiveProfile,
        setVoipActiveProfile,
    };
}
