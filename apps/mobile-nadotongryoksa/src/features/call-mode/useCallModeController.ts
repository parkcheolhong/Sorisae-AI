import { useCallback, useMemo, useState } from 'react';
import { CallMode, DEFAULT_CALL_MODE, getCallModeLabel } from './types';

type CallModeController = {
    selectedCallMode: CallMode;
    callModeLabel: string;
    isPstnAssistMode: boolean;
    isVoipFullAutoMode: boolean;
    setCallMode: (nextMode: CallMode) => void;
};

export function useCallModeController(initialMode: CallMode = DEFAULT_CALL_MODE): CallModeController {
    const [selectedCallMode, setSelectedCallMode] = useState<CallMode>(initialMode);

    const setCallMode = useCallback((nextMode: CallMode) => {
        setSelectedCallMode(nextMode);
    }, []);

    return useMemo(() => ({
        selectedCallMode,
        callModeLabel: getCallModeLabel(selectedCallMode),
        isPstnAssistMode: selectedCallMode === 'pstn_assist',
        isVoipFullAutoMode: selectedCallMode === 'voip_full_auto',
        setCallMode,
    }), [selectedCallMode, setCallMode]);
}
