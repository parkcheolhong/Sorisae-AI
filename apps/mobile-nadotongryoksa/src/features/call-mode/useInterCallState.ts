// [기능 분리 Phase3] 일반전화(inter-call) 상태 도메인.
// VOIP 상태(useVoipState)와 물리적으로 분리해, 일반전화+예약 기능이 VOIP+채팅 기능과
// 상태를 공유하지 않도록 한다. useCallModeController 가 이 훅을 합성(compose)한다.
import { useState, type Dispatch, type SetStateAction } from 'react';

export type InterCallTurn = 'from' | 'to';

export type InterCallLogEntry = {
    turn: InterCallTurn;
    text: string;
    translated: string;
};

export type InterCallContactOption = {
    id: string;
    name: string;
    phone: string;
    label: string;
};

export type InterCallState = {
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
};

export function useInterCallState(): InterCallState {
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

    return {
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
    };
}
