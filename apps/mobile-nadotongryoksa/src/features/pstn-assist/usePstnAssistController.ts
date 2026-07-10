import { Linking, Platform } from 'react-native';
import { useCallback } from 'react';
import { activateFeatureExclusive, deactivateFeatureExclusive } from '../isolation/fourFeatureRuntime';

type PstnAssistDialInput = {
    interCallPhone?: string;
    bookingSupportPhone?: string;
    selectedBookingPhone?: string;
};

type PstnAssistDialResult = {
    dialOpened: boolean;
    targetPhone: string;
};

type PstnAssistController = {
    openDialPad: (rawPhone?: string) => Promise<boolean>;
    startPstnAssistDialFlow: (input: PstnAssistDialInput) => Promise<PstnAssistDialResult>;
};

function normalizePhone(raw?: string): string {
    if (!raw) return '';
    const trimmed = raw.trim();
    if (!trimmed) return '';
    const cleaned = trimmed.replace(/[^\d+]/g, '');
    if (cleaned.startsWith('+')) {
        return `+${cleaned.slice(1).replace(/\+/g, '')}`;
    }
    return cleaned;
}

function chooseFirstAvailable(input: PstnAssistDialInput): string {
    return normalizePhone(input.interCallPhone)
        || normalizePhone(input.bookingSupportPhone)
        || normalizePhone(input.selectedBookingPhone)
        || '';
}

export function usePstnAssistController(): PstnAssistController {
    const openDialPad = useCallback(async (rawPhone?: string): Promise<boolean> => {
        const targetPhone = normalizePhone(rawPhone);
        if (!targetPhone) {
            return false;
        }

        const telUri = `tel:${targetPhone}`;
        try {
            const canOpen = await Linking.canOpenURL(telUri);
            if (!canOpen) {
                return false;
            }
            await Linking.openURL(telUri);
            return true;
        } catch (error) {
            console.warn('[PSTN_ASSIST_DIAL_FAIL]', {
                platform: Platform.OS,
                telUri,
                error: error instanceof Error ? error.message : String(error),
            });
            return false;
        }
    }, []);

    const startPstnAssistDialFlow = useCallback(async (input: PstnAssistDialInput): Promise<PstnAssistDialResult> => {
        const activation = await activateFeatureExclusive('pstn-assist', 'pstn_dial_flow_start', 'system');
        if (!activation.ok) {
            throw new Error('다른 기능이 활성화되어 PSTN 보조 통화를 시작할 수 없습니다. 현재 기능을 종료한 뒤 다시 시도해 주세요.');
        }
        const targetPhone = chooseFirstAvailable(input);
        if (!targetPhone) {
            deactivateFeatureExclusive('pstn-assist', 'pstn_dial_flow_no_target', 'system');
            return { dialOpened: false, targetPhone: '' };
        }

        const dialOpened = await openDialPad(targetPhone);
        if (!dialOpened) {
            deactivateFeatureExclusive('pstn-assist', 'pstn_dial_flow_open_failed', 'system');
        }
        return { dialOpened, targetPhone };
    }, [openDialPad]);

    return {
        openDialPad,
        startPstnAssistDialFlow,
    };
}
