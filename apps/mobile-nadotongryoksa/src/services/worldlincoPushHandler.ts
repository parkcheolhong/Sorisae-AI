import { AppState, NativeModules, Platform, Vibration } from 'react-native';

import { showChatMessageLocalNotification } from './chatIncomingNotifications';
import * as voipIncomingAlert from '../native/voipIncomingAlert';
import * as voipIncomingNotifications from './voipIncomingNotifications';
import { emitVoipCallEnded } from './voipCallSignals';
import { parseChatMessageFcmData } from './worldlincoPushBridge';
import { parseIncomingCallFcmData } from './voipIncomingPushBridge';
import { getVoIPToneService } from './voipToneService';
import {
    announceServerVoice,
    buildAnnouncement,
    getStoredPreferredLanguage,
    ttsLocaleForLang,
} from '../utils/voiceAnnounce';

const CHAT_ALERT_BURST_COUNT = 3;
const CHAT_ALERT_BURST_GAP_MS = 900;

function pulseVibration(times: number): void {
    if (Platform.OS === 'web') {
        return;
    }
    for (let index = 0; index < times; index += 1) {
        setTimeout(() => {
            try {
                Vibration.vibrate(500);
            } catch {
                // no-op
            }
        }, index * CHAT_ALERT_BURST_GAP_MS);
    }
}

function isAppActive(): boolean {
    return Platform.OS === 'web' || AppState.currentState === 'active';
}

function playMessageToneBurst(times: number): void {
    for (let index = 0; index < times; index += 1) {
        setTimeout(() => {
            try {
                getVoIPToneService().playMessageTone();
            } catch {
                // no-op
            }
        }, index * CHAT_ALERT_BURST_GAP_MS);
    }
}

export async function handleWorldlincoPushData(
    data: Record<string, unknown>,
    source: 'foreground' | 'background' | 'notification_open',
): Promise<void> {
    const isVoipIncomingAlertNativeAvailable =
        voipIncomingAlert.isVoipIncomingAlertNativeAvailable ??
        (voipIncomingAlert as { default?: typeof voipIncomingAlert }).default?.isVoipIncomingAlertNativeAvailable;
    // 발신자가 통화를 종료/취소함 → 콜리 단말의 착신 벨(네이티브 풀스크린 알림)을 즉시 멈춘다.
    // (백그라운드/잠금화면에서도 setBackgroundMessageHandler 가 이 핸들러를 실행한다.)
    const pushType = String(data?.type ?? '');
    if (pushType === 'voip_call_cancelled' || pushType === 'call_cancelled' || pushType === 'voip_call_ended') {
        console.log('[VOIP_CANCEL_PUSH]', JSON.stringify({
            source,
            call_id: String(data?.call_id ?? ''),
            native: isVoipIncomingAlertNativeAvailable?.() ?? false,
        }));
        const dismissIncomingNotification =
            voipIncomingNotifications.dismissIncomingVoipLocalNotification ??
            (voipIncomingNotifications as { default?: typeof voipIncomingNotifications }).default?.dismissIncomingVoipLocalNotification;
        const nativeStopIncomingAlert = NativeModules.VoipIncomingAlert?.stopIncomingAlert;
        if (typeof nativeStopIncomingAlert === 'function') {
            await nativeStopIncomingAlert();
        } else {
            const stopIncomingAlert =
                voipIncomingAlert.stopNativeIncomingVoipAlert ??
                (voipIncomingAlert as { default?: typeof voipIncomingAlert }).default?.stopNativeIncomingVoipAlert;
            await stopIncomingAlert?.();
        }
        await dismissIncomingNotification?.();
        try {
            getVoIPToneService().stopAll();
        } catch {
            // no-op
        }
        if (Platform.OS !== 'web') {
            try {
                Vibration.cancel();
            } catch {
                // no-op
            }
        }
        emitVoipCallEnded(String(data?.call_id ?? ''));
        return;
    }

    const incomingCall = parseIncomingCallFcmData(data);
    if (incomingCall?.call_id) {
        const startNativeIncomingVoipAlert =
            voipIncomingAlert.startNativeIncomingVoipAlert ??
            (voipIncomingAlert as { default?: typeof voipIncomingAlert }).default?.startNativeIncomingVoipAlert;
        if (isVoipIncomingAlertNativeAvailable?.()) {
            await startNativeIncomingVoipAlert?.(
                incomingCall.call_id,
                incomingCall.caller_label ?? incomingCall.caller_voice_id ?? '친구',
            );
        }
        const showIncomingVoipLocalNotification =
            voipIncomingNotifications.showIncomingVoipLocalNotification ??
            (voipIncomingNotifications as { default?: typeof voipIncomingNotifications }).default?.showIncomingVoipLocalNotification;
        await showIncomingVoipLocalNotification?.(data);
        return;
    }

    const chatMessage = parseChatMessageFcmData(data);
    if (!chatMessage) {
        return;
    }

    const senderLabel = chatMessage.sender_label ?? '친구';
    const active = isAppActive();
    // 수신자 지정 언어로 안내 문구 구성(50개국어). 활성=서버 뉴럴 TTS, 백그라운드=네이티브 지정언어 단말 TTS.
    const prefLang = await getStoredPreferredLanguage();
    const announceText = await buildAnnouncement('chatNew', prefLang, senderLabel);
    console.log('[CHAT_PUSH]', JSON.stringify({
        event: 'handle',
        source,
        native: isVoipIncomingAlertNativeAvailable?.() ?? false,
        active,
        lang: prefLang,
        sender: senderLabel.slice(0, 24),
    }));
    const startNativeChatIncomingAlert =
        voipIncomingAlert.startNativeChatIncomingAlert ??
        (voipIncomingAlert as { default?: typeof voipIncomingAlert }).default?.startNativeChatIncomingAlert;
    if (isVoipIncomingAlertNativeAvailable?.()) {
        // 활성 시 JS가 서버 뉴럴 TTS로 발화하므로 네이티브는 발화하지 않음(skipSpeak). 백그라운드는 네이티브가 지정언어로 발화.
        await startNativeChatIncomingAlert?.(chatMessage.room_id, senderLabel, {
            announceText,
            localeTag: ttsLocaleForLang(prefLang),
            skipSpeak: active,
        });
        if (active) {
            announceServerVoice(announceText, prefLang).catch(() => { /* no-op */ });
        }
    } else {
        playMessageToneBurst(CHAT_ALERT_BURST_COUNT);
        pulseVibration(CHAT_ALERT_BURST_COUNT);
        // 비-네이티브(웹/구형) 환경: 활성 상태에서 서버 뉴럴 TTS(폴백 단말 TTS)로 안내.
        if (active) {
            announceServerVoice(announceText, prefLang).catch(() => { /* no-op */ });
        }
    }
    await showChatMessageLocalNotification({
        ...data,
        alert_phrase: chatMessage.alert_phrase ?? '친구야~',
    });
}
