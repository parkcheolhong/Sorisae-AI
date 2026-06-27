import { useCallback, useMemo, useState, type Dispatch, type SetStateAction } from 'react';
import type { CallInitResponse } from '../../services/voipCallClient';
import { CallMode, DEFAULT_CALL_MODE, getCallModeLabel } from './types';

type InterCallTurn = 'from' | 'to';

type InterCallLogEntry = {
    turn: InterCallTurn;
    text: string;
    translated: string;
};

type InterCallContactOption = {
    id: string;
    name: string;
    phone: string;
    label: string;
};

type VoipParticipantProfile = {
    nickname: string;
    genderLabel: string;
    countryCode: string;
    countryName: string;
    voiceId: string;
    countryFlag: string;
    preferredLanguage?: string;
};

type CallModeAuditEvent = {
    id: number | string;
    event_type: string;
    requested_mode: string | null;
    resolved_mode: string | null;
    call_route?: string | null;
    status?: string | null;
    error_code?: string | null;
    created_at: string;
};

type PendingIncomingVoipCall = CallInitResponse & {
    caller_label?: string;
    caller_voice_id?: string;
};

export type CallModeController = {
    selectedCallMode: CallMode;
    callModeLabel: string;
    isPstnAssistMode: boolean;
    isVoipFullAutoMode: boolean;
    setCallMode: (nextMode: CallMode) => void;
    voipValidationOverride: boolean;
    setVoipValidationOverride: (value: boolean) => void;
    showVoipTester: boolean;
    setShowVoipTester: (value: boolean) => void;
    showFriendFolder: boolean;
    setShowFriendFolder: Dispatch<SetStateAction<boolean>>;
    interCallActive: boolean;
    setInterCallActive: (value: boolean) => void;
    interCallTurn: InterCallTurn;
    setInterCallTurn: (value: InterCallTurn) => void;
    interCallStatus: string;
    setInterCallStatus: (value: string) => void;
    interCallPhone: string;
    setInterCallPhone: (value: string) => void;
    interCallContactPickerVisible: boolean;
    setInterCallContactPickerVisible: (value: boolean) => void;
    interCallContactLoading: boolean;
    setInterCallContactLoading: (value: boolean) => void;
    interCallContactError: string;
    setInterCallContactError: (value: string) => void;
    interCallContactOptions: InterCallContactOption[];
    setInterCallContactOptions: Dispatch<SetStateAction<InterCallContactOption[]>>;
    interCallLog: InterCallLogEntry[];
    setInterCallLog: Dispatch<SetStateAction<InterCallLogEntry[]>>;
    interManualText: string;
    setInterManualText: (value: string) => void;
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

export function useCallModeController(initialMode: CallMode = DEFAULT_CALL_MODE): CallModeController {
    const [selectedCallMode, setSelectedCallMode] = useState<CallMode>(initialMode);
    const [voipValidationOverride, setVoipValidationOverride] = useState(false);
    const [showVoipTester, setShowVoipTester] = useState(false);
    const [showFriendFolder, setShowFriendFolder] = useState(false);
    const [interCallActive, setInterCallActive] = useState(false);
    const [interCallTurn, setInterCallTurn] = useState<InterCallTurn>('from');
    const [interCallStatus, setInterCallStatus] = useState('');
    const [interCallPhone, setInterCallPhone] = useState('');
    const [interCallContactPickerVisible, setInterCallContactPickerVisible] = useState(false);
    const [interCallContactLoading, setInterCallContactLoading] = useState(false);
    const [interCallContactError, setInterCallContactError] = useState('');
    const [interCallContactOptions, setInterCallContactOptions] = useState<InterCallContactOption[]>([]);
    const [interCallLog, setInterCallLog] = useState<InterCallLogEntry[]>([]);
    const [interManualText, setInterManualText] = useState('');
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

    return useMemo(() => ({
        selectedCallMode,
        callModeLabel: getCallModeLabel(selectedCallMode),
        isPstnAssistMode: selectedCallMode === 'pstn_assist',
        isVoipFullAutoMode: selectedCallMode === 'voip_full_auto',
        setCallMode,
        voipValidationOverride,
        setVoipValidationOverride,
        showVoipTester,
        setShowVoipTester,
        showFriendFolder,
        setShowFriendFolder,
        interCallActive,
        setInterCallActive,
        interCallTurn,
        setInterCallTurn,
        interCallStatus,
        setInterCallStatus,
        interCallPhone,
        setInterCallPhone,
        interCallContactPickerVisible,
        setInterCallContactPickerVisible,
        interCallContactLoading,
        setInterCallContactLoading,
        interCallContactError,
        setInterCallContactError,
        interCallContactOptions,
        setInterCallContactOptions,
        interCallLog,
        setInterCallLog,
        interManualText,
        setInterManualText,
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
    }), [
        interCallActive,
        interCallContactError,
        interCallContactLoading,
        interCallContactOptions,
        interCallContactPickerVisible,
        interCallLog,
        interCallPhone,
        interCallStatus,
        interCallTurn,
        interManualText,
        pendingIncomingVoipCall,
        selectedCallMode,
        setCallMode,
        showFriendFolder,
        showVoipTester,
        voipActiveProfile,
        voipAuditCallId,
        voipAuditError,
        voipAuditEvents,
        voipAuditLoading,
        voipCallInitResponse,
        voipIdentity,
        voipValidationOverride,
    ]);
}
