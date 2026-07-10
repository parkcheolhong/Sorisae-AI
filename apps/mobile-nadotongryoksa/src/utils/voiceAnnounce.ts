// 착신/부재중 음성 안내 SSOT.
// - 서버 뉴럴 TTS(Edge)를 1순위로 사용해 단말 음성팩 의존을 제거하고 50개국어 일관 발음을 보장한다.
// - 합성 실패 시 단말 TTS(expo-speech)로 폴백한다.
// - 안내 문구는 수신자 지정 언어(preferred_language)로 1회 번역해 영구 캐시한다(이후 오프라인/즉시).
import { Platform } from 'react-native';
import * as FileSystem from 'expo-file-system/legacy';
import { Audio, type AudioSound } from '../compat/expoAvAudio';
import * as Speech from 'expo-speech';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { synthesizeSpeech, translateText } from '../api/translate';

// 앱 LANGS(App.tsx)와 동기화된 lang code → BCP47 TTS 로케일 맵(50개국어 SSOT 미러).
const TTS_LOCALE: Record<string, string> = {
    ko: 'ko-KR', en: 'en-US', zh: 'zh-CN', 'zh-tw': 'zh-TW', ja: 'ja-JP',
    es: 'es-ES', fr: 'fr-FR', de: 'de-DE', pt: 'pt-BR', ru: 'ru-RU',
    ar: 'ar-SA', hi: 'hi-IN', it: 'it-IT', tr: 'tr-TR', vi: 'vi-VN',
    th: 'th-TH', id: 'id-ID', ms: 'ms-MY', nl: 'nl-NL', pl: 'pl-PL',
    uk: 'uk-UA', sv: 'sv-SE', no: 'nb-NO', da: 'da-DK', fi: 'fi-FI',
    cs: 'cs-CZ', ro: 'ro-RO', hu: 'hu-HU', el: 'el-GR', he: 'he-IL',
    bg: 'bg-BG', hr: 'hr-HR', sr: 'sr-RS', sk: 'sk-SK', sl: 'sl-SI',
    lt: 'lt-LT', lv: 'lv-LV', et: 'et-EE', fa: 'fa-IR', ur: 'ur-PK',
    bn: 'bn-BD', ta: 'ta-IN', te: 'te-IN', ml: 'ml-IN', gu: 'gu-IN',
    mr: 'mr-IN', fil: 'fil-PH', sw: 'sw-KE', ca: 'ca-ES', am: 'am-ET',
};

export function ttsLocaleForLang(langCode?: string | null): string {
    const code = (langCode || '').trim().toLowerCase();
    return TTS_LOCALE[code] ?? 'en-US';
}

export type AnnounceKey = 'chatNew' | 'missedCall' | 'missedCallMulti';

// 한국어 기준 문구(이름은 별도로 앞에 붙인다 → 언어별 조사/어순 문제 회피).
const KO_BASE: Record<AnnounceKey, string> = {
    chatNew: '새 메시지가 도착했습니다',
    missedCall: '부재중 전화가 있습니다',
    missedCallMulti: '여러 건의 부재중 전화가 있습니다',
};

// 지정 언어로 안내 문구를 1회 번역해 캐시. ko 또는 번역 실패 시 한국어 원문 사용.
async function localizePhrase(key: AnnounceKey, langCode: string): Promise<string> {
    const code = (langCode || '').trim().toLowerCase();
    if (!code || code === 'ko') {
        return KO_BASE[key];
    }
    const cacheKey = `worldlinco_i18n_${key}_${code}`;
    try {
        const cached = await AsyncStorage.getItem(cacheKey);
        if (cached && cached.trim()) {
            return cached;
        }
    } catch {
        // no-op
    }
    try {
        const res = await translateText(KO_BASE[key], 'ko', code, 8000);
        const text = (res?.translated || '').trim();
        if (text) {
            AsyncStorage.setItem(cacheKey, text).catch(() => { /* no-op */ });
            return text;
        }
    } catch {
        // no-op
    }
    return KO_BASE[key];
}

// 이름 + 지정언어 문구로 최종 안내 문장을 만든다. 이름은 고유명사라 번역하지 않고 앞에 붙인다.
export async function buildAnnouncement(
    key: AnnounceKey,
    langCode: string,
    name?: string | null,
): Promise<string> {
    const phrase = await localizePhrase(key, langCode);
    const safeName = (name || '').trim();
    if (!safeName) {
        return phrase;
    }
    return `${safeName}. ${phrase}`;
}

// 수신자 지정 언어 조회(AsyncStorage 의 nadot_auth_state → userInfo.preferred_language).
export async function getStoredPreferredLanguage(): Promise<string> {
    try {
        const raw = await AsyncStorage.getItem('nadot_auth_state');
        if (raw) {
            const parsed = JSON.parse(raw) as { userInfo?: { preferred_language?: string } };
            const lang = String(parsed?.userInfo?.preferred_language || '').trim().toLowerCase();
            if (lang) {
                return lang;
            }
        }
    } catch {
        // no-op
    }
    return 'ko';
}

let announceSound: AudioSound | null = null;

async function stopAnnounceSound(): Promise<void> {
    const sound = announceSound;
    announceSound = null;
    if (!sound) {
        return;
    }
    try {
        await sound.stopAsync();
    } catch {
        // no-op
    }
    try {
        await sound.unloadAsync();
    } catch {
        // no-op
    }
}

// 서버 뉴럴 TTS로 안내 문장을 발화한다. 합성 실패 시 단말 TTS(지정언어 로케일)로 폴백.
// 포그라운드(앱 활성)에서 신뢰성 있게 재생되며, expo-av 가 없는 환경(웹)에서는 단말 TTS만 사용.
export async function announceServerVoice(text: string, langCode: string): Promise<void> {
    const speakText = (text || '').trim();
    if (!speakText) {
        return;
    }
    const locale = ttsLocaleForLang(langCode);

    if (Platform.OS === 'web') {
        try {
            Speech.stop();
            Speech.speak(speakText, { language: locale, rate: 1.0 });
        } catch {
            // no-op
        }
        return;
    }

    await stopAnnounceSound();
    try {
        Speech.stop();
    } catch {
        // no-op
    }
    try {
        await Audio.setAudioModeAsync({
            allowsRecordingIOS: false,
            playsInSilentModeIOS: true,
            shouldDuckAndroid: true,
            playThroughEarpieceAndroid: false,
        });
    } catch {
        // no-op
    }

    let played = false;
    try {
        const synth = await synthesizeSpeech(speakText, langCode, undefined, 12000);
        if (synth?.audioBase64 && String(synth.audioFormat || '').startsWith('audio/')) {
            const ext = String(synth.audioFormat).includes('wav') ? 'wav' : 'mp3';
            const baseDir = FileSystem.cacheDirectory ?? FileSystem.documentDirectory ?? '';
            const fileUri = `${baseDir}announce_${Date.now()}.${ext}`;
            await FileSystem.writeAsStringAsync(fileUri, synth.audioBase64, {
                encoding: FileSystem.EncodingType.Base64,
            });
            const { sound } = await Audio.Sound.createAsync(
                { uri: fileUri },
                { shouldPlay: true, volume: 1.0 },
            );
            announceSound = sound;
            await new Promise<void>((resolve) => {
                const failsafe = setTimeout(resolve, 12000);
                sound.setOnPlaybackStatusUpdate((status) => {
                    if (status.isLoaded === false) {
                        clearTimeout(failsafe);
                        resolve();
                        return;
                    }
                    if (status.didJustFinish) {
                        clearTimeout(failsafe);
                        resolve();
                    }
                });
            });
            await stopAnnounceSound();
            const fileToCleanup = fileUri;
            setTimeout(() => {
                FileSystem.deleteAsync(fileToCleanup, { idempotent: true }).catch(() => { /* no-op */ });
            }, 5000);
            played = true;
            console.log('[ANNOUNCE_TTS]', JSON.stringify({ delivery: 'server_audio', lang: langCode }));
        } else {
            console.log('[ANNOUNCE_TTS]', JSON.stringify({ event: 'server_unavailable', delivery: synth?.ttsDelivery ?? 'null', lang: langCode }));
        }
    } catch (err) {
        console.log('[ANNOUNCE_TTS]', JSON.stringify({ event: 'server_error', lang: langCode, message: err instanceof Error ? err.message : 'synth_failed' }));
    }

    if (!played) {
        console.log('[ANNOUNCE_TTS]', JSON.stringify({ delivery: 'device_speech', locale }));
        try {
            Speech.speak(speakText, { language: locale, rate: 1.0 });
        } catch {
            // no-op
        }
    }
}
