import { useMemo, type Dispatch, type SetStateAction } from 'react';
import type { CallInitResponse } from '../../services/voipCallClient';
import { CallMode, DEFAULT_CALL_MODE, getCallModeLabel } from './types';
import {
    useInterCallState,
    type InterCallContactOption,
    type InterCallLogEntry,
    type InterCallTurn,
} from './useInterCallState';
import {
    useVoipState,
    type CallModeAuditEvent,
    type PendingIncomingVoipCall,
    type VoipParticipantProfile,
} from './useVoipState';

// [기능 분리 Phase3] 이 컨트롤러는 이제 두 도메인 훅(useVoipState + useInterCallState)을
// 합성(compose)하는 얇은 어댑터다. 공개 API(CallModeController)와 반환 형태는 기존과
// 100% 동일하게 유지해 App.tsx 소비부를 한 글자도 바꾸지 않는다(Strangler Fig 무위험 분리).
// 향후 VOIP+채팅 모듈과 일반전화+예약 모듈은 각자 자기 도메인 훅만 직접 사용하면 된다.

// 하위 호환을 위해 기존 타입명을 재노출(re-export).
export type {
    InterCallContactOption,
    InterCallLogEntry,
    InterCallTurn,
    CallModeAuditEvent,
    PendingIncomingVoipCall,
    VoipParticipantProfile,
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
    const voip = useVoipState(initialMode);
    const inter = useInterCallState();

    return useMemo(() => ({
        // --- VOIP 도메인 ---
        selectedCallMode: voip.selectedCallMode,
        callModeLabel: getCallModeLabel(voip.selectedCallMode),
        isPstnAssistMode: voip.selectedCallMode === 'pstn_assist',
        isVoipFullAutoMode: voip.selectedCallMode === 'voip_full_auto',
        setCallMode: voip.setCallMode,
        voipValidationOverride: voip.voipValidationOverride,
        setVoipValidationOverride: voip.setVoipValidationOverride,
        showVoipTester: voip.showVoipTester,
        setShowVoipTester: voip.setShowVoipTester,
        showFriendFolder: voip.showFriendFolder,
        setShowFriendFolder: voip.setShowFriendFolder,
        voipCallInitResponse: voip.voipCallInitResponse,
        setVoipCallInitResponse: voip.setVoipCallInitResponse,
        pendingIncomingVoipCall: voip.pendingIncomingVoipCall,
        setPendingIncomingVoipCall: voip.setPendingIncomingVoipCall,
        voipAuditCallId: voip.voipAuditCallId,
        setVoipAuditCallId: voip.setVoipAuditCallId,
        voipAuditEvents: voip.voipAuditEvents,
        setVoipAuditEvents: voip.setVoipAuditEvents,
        voipAuditLoading: voip.voipAuditLoading,
        setVoipAuditLoading: voip.setVoipAuditLoading,
        voipAuditError: voip.voipAuditError,
        setVoipAuditError: voip.setVoipAuditError,
        voipIdentity: voip.voipIdentity,
        setVoipIdentity: voip.setVoipIdentity,
        voipActiveProfile: voip.voipActiveProfile,
        setVoipActiveProfile: voip.setVoipActiveProfile,
        // --- 일반전화(inter-call) 도메인 ---
        interCallActive: inter.interCallActive,
        setInterCallActive: inter.setInterCallActive,
        interCallTurn: inter.interCallTurn,
        setInterCallTurn: inter.setInterCallTurn,
        interCallStatus: inter.interCallStatus,
        setInterCallStatus: inter.setInterCallStatus,
        interCallPhone: inter.interCallPhone,
        setInterCallPhone: inter.setInterCallPhone,
        interCallContactPickerVisible: inter.interCallContactPickerVisible,
        setInterCallContactPickerVisible: inter.setInterCallContactPickerVisible,
        interCallContactLoading: inter.interCallContactLoading,
        setInterCallContactLoading: inter.setInterCallContactLoading,
        interCallContactError: inter.interCallContactError,
        setInterCallContactError: inter.setInterCallContactError,
        interCallContactOptions: inter.interCallContactOptions,
        setInterCallContactOptions: inter.setInterCallContactOptions,
        interCallLog: inter.interCallLog,
        setInterCallLog: inter.setInterCallLog,
        interManualText: inter.interManualText,
        setInterManualText: inter.setInterManualText,
    }), [voip, inter]);
}
