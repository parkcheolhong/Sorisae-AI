import { Linking, Platform } from 'react-native';
import { useCallback } from 'react';

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
        const targetPhone = chooseFirstAvailable(input);
        if (!targetPhone) {
            return { dialOpened: false, targetPhone: '' };
        }

        const dialOpened = await openDialPad(targetPhone);
        return { dialOpened, targetPhone };
    }, [openDialPad]);

    return {
        openDialPad,
        startPstnAssistDialFlow,
    };
}
