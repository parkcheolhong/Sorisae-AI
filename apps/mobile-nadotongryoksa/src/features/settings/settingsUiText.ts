/**
 * 설정 탭 UI 문자열 카탈로그 — userLang(프로필 언어) 변경 시 라벨이 동시에 바뀌도록 SSOT.
 * ko/en 직접 제공, 그 외 언어는 en 폴백(getUiText 와 동일 정책).
 */
import { resolveBundledCatalogLang } from '../i18n/bundledUiLangs';
import { SETTINGS_UI_JA, SETTINGS_UI_ZH } from './settingsUiTextJaZh';

export type SettingsUiText = {
    headerTitle: string;
    intro: string;
    sectionAccount: string;
    sectionIncomingAlert: string;
    sectionDevicePrep: string;
    sectionChatVoice: string;
    sectionSorisae: string;
    sectionManuals: string;
    sectionSecurity: string;
    country: string;
    translationLanguage: string;
    profileLanguageLinkedHint: string;
    notSet: string;
    saving: string;
    profileLinkLabel: string;
    profileLinkDesc: string;
    incomingAlertHint: string;
    alertSound: string;
    alertVibrate: string;
    alertSilent: string;
    micPermission: string;
    locationPermission: string;
    gpsService: string;
    notificationPermission: string;
    granted: string;
    required: string;
    requestMic: string;
    requestLocation: string;
    requestNotification: string;
    openGpsSettings: string;
    voipSpeakerDefault: string;
    voipSpeakerOnDesc: string;
    voipSpeakerOffDesc: string;
    voipSpeakerSetOn: string;
    voipSpeakerSetOff: string;
    currentAudioRoute: string;
    audioRouteLive: string;
    refreshDeviceStatus: string;
    refreshDeviceFailed: string;
    openSystemSettings: string;
    openVoipNotification: string;
    openBluetooth: string;
    refreshAudioRoute: string;
    refreshAudioRouteDone: string;
    deviceChecking: string;
    refreshDevice: string;
    speakerOn: string;
    speakerOff: string;
    btConnected: string;
    btDisconnected: string;
    autoListen: string;
    autoListenDesc: string;
    readAloud: string;
    readAloudDesc: string;
    sorisaeFab: string;
    sorisaeFabDesc: string;
    manualsIntroKo: string;
    manualsIntroTranslated: string;
    kwsAdvancedTitle: string;
    kwsSectionHint: string;
    kwsEngineLabel: string;
    kwsProviderVosk: string;
    kwsProviderPorcupine: string;
    kwsModelFolder: string;
    kwsModelPlaceholder: string;
    kwsPickModel: string;
    kwsPicking: string;
    kwsPicovoiceKey: string;
    kwsPicovoicePlaceholder: string;
    kwsKeywordFiles: string;
    kwsPickKeywords: string;
    kwsNoKeywordFiles: string;
    kwsSave: string;
    kwsSaving: string;
    kwsSaved: string;
    kwsSaveFailed: string;
    kwsVoskPathRequired: string;
    kwsPicovoiceKeyRequired: string;
    kwsKeywordRequired: string;
    kwsPpnRequired: string;
    kwsPickPpnFailed: string;
    kwsPpnSelected: string;
    passwordChange: string;
    loginRequiredToChange: string;
    unsupportedLanguage: string;
    countrySavedSuccess: string;
    countrySaveFailed: string;
    languageSavedSuccess: string;
    languageSaveFailed: string;
};

const KO: SettingsUiText = {
    headerTitle: '⚙️ 설정',
    intro: '핵심 설정만 빠르게 관리합니다.',
    sectionAccount: '👤 계정 · 프로필',
    sectionIncomingAlert: '🔔 수신 알림',
    sectionDevicePrep: '📱 기기 준비',
    sectionChatVoice: '🎧 채팅 · 음성',
    sectionSorisae: '🐦 소리새 AI',
    sectionManuals: '📖 사용 설명서',
    sectionSecurity: '🔒 보안',
    country: '국가',
    translationLanguage: '통역/번역 언어',
    profileLanguageLinkedHint: '국가 변경 시 자동 연동 · 채팅·VoIP·일반전화 기본',
    notSet: '미설정',
    saving: '저장 중...',
    profileLinkLabel: '프로필 · 국가 · 언어',
    profileLinkDesc: '통역/번역 기본 언어 변경',
    incomingAlertHint: '수신 알림 방식',
    alertSound: '🔊 소리',
    alertVibrate: '📳 진동',
    alertSilent: '🔕 무음',
    micPermission: '마이크 권한',
    locationPermission: '위치 권한',
    gpsService: 'GPS 서비스',
    notificationPermission: '알림 권한',
    granted: '허용됨',
    required: '필요',
    requestMic: '🎙️ 마이크 권한 요청',
    requestLocation: '📍 위치 권한 요청',
    requestNotification: '🔔 알림 권한 요청',
    openGpsSettings: '🛰️ GPS 설정 열기 (ON/OFF)',
    voipSpeakerDefault: '통화 기본 출력: 스피커',
    voipSpeakerOnDesc: '현재 기본값: 스피커 ON',
    voipSpeakerOffDesc: '현재 기본값: 이어피스/이어폰 우선',
    voipSpeakerSetOn: '통화 기본 출력이 스피커로 설정되었습니다.',
    voipSpeakerSetOff: '통화 기본 출력이 이어피스/이어폰 우선으로 설정되었습니다.',
    currentAudioRoute: '현재 오디오 경로',
    audioRouteLive: '실시간 상태: 스피커 {speaker} · BT {bt}',
    refreshDeviceStatus: '기기 권한 상태를 새로고침했습니다.',
    refreshDeviceFailed: '기기 권한 상태 확인에 실패했습니다.',
    openSystemSettings: '⚙️ 시스템 설정 열기',
    openVoipNotification: '📞 VoIP 알림 설정 열기',
    openBluetooth: '🎧 블루투스 설정 열기 (이어폰 연결)',
    refreshAudioRoute: '🔈 오디오 경로 새로고침',
    refreshAudioRouteDone: '오디오 경로 상태를 새로고침했습니다.',
    deviceChecking: '점검 중...',
    refreshDevice: '🔄 상태 새로고침',
    speakerOn: 'ON',
    speakerOff: 'OFF',
    btConnected: '연결됨',
    btDisconnected: '미연결',
    autoListen: '채팅 자동 듣기',
    autoListenDesc: '입장 시 자동 대기',
    readAloud: '수신 메시지 자동 읽어주기',
    readAloudDesc: '상대 메시지 읽어주기',
    sorisaeFab: '플로팅 소리새 버튼',
    sorisaeFabDesc: '홈 버튼 표시',
    manualsIntroKo: '기능 안내',
    manualsIntroTranslated: '기능 안내 · {lang}',
    kwsAdvancedTitle: '🧠 고급 · 소리새AI 음성무한대기(심볼)',
    kwsSectionHint: '호출어 감지 고급 설정',
    kwsEngineLabel: '감지 엔진',
    kwsProviderVosk: '일반 음성 (Vosk)',
    kwsProviderPorcupine: '호출어 전용 (Porcupine)',
    kwsModelFolder: '음성 모델 폴더',
    kwsModelPlaceholder: '예: /sdcard/Download/vosk-model-small-ko',
    kwsPickModel: '📂 음성 모델 파일 선택',
    kwsPicking: '선택 중...',
    kwsPicovoiceKey: 'Picovoice 인증 키',
    kwsPicovoicePlaceholder: 'Picovoice에서 발급받은 키',
    kwsKeywordFiles: '호출어 파일 (여러 개 선택 가능)',
    kwsPickKeywords: '📂 호출어 파일 선택',
    kwsNoKeywordFiles: '선택된 호출어 파일이 없습니다.',
    kwsSave: '호출어 감지 설정 저장',
    kwsSaving: '저장 중...',
    kwsSaved: '호출어 감지 설정이 저장되었습니다.',
    kwsSaveFailed: '호출어 감지 설정 저장에 실패했습니다.',
    kwsVoskPathRequired: '일반 음성(Vosk) 사용 시 모델 폴더 경로를 입력해 주세요.',
    kwsPicovoiceKeyRequired: 'Picovoice 인증 키를 입력해 주세요.',
    kwsKeywordRequired: '호출어 파일을 1개 이상 선택해 주세요.',
    kwsPpnRequired: '호출어 파일(.ppn)을 선택해 주세요.',
    kwsPickPpnFailed: '호출어 파일 선택에 실패했습니다.',
    kwsPpnSelected: '{count}개 호출어 파일을 선택했습니다.',
    passwordChange: '비밀번호 변경',
    loginRequiredToChange: '로그인 후 변경할 수 있습니다.',
    unsupportedLanguage: '지원하지 않는 언어입니다.',
    countrySavedSuccess: '국가가 저장되었습니다.',
    countrySaveFailed: '국가 저장에 실패했습니다.',
    languageSavedSuccess: '통역/번역 언어가 저장되었습니다.',
    languageSaveFailed: '언어 저장에 실패했습니다.',
};

const EN: SettingsUiText = {
    headerTitle: '⚙️ Settings',
    intro: 'Quickly manage core settings.',
    sectionAccount: '👤 Account · Profile',
    sectionIncomingAlert: '🔔 Incoming alerts',
    sectionDevicePrep: '📱 Device readiness',
    sectionChatVoice: '🎧 Chat · Voice',
    sectionSorisae: '🐦 Sorisae AI',
    sectionManuals: '📖 User guides',
    sectionSecurity: '🔒 Security',
    country: 'Country',
    translationLanguage: 'Interpretation / translation language',
    profileLanguageLinkedHint: 'Auto-linked to country · default for chat, VoIP, and phone',
    notSet: 'Not set',
    saving: 'Saving...',
    profileLinkLabel: 'Profile · Country · Language',
    profileLinkDesc: 'Change default translation language',
    incomingAlertHint: 'Incoming alert mode',
    alertSound: '🔊 Sound',
    alertVibrate: '📳 Vibrate',
    alertSilent: '🔕 Silent',
    micPermission: 'Microphone permission',
    locationPermission: 'Location permission',
    gpsService: 'GPS service',
    notificationPermission: 'Notification permission',
    granted: 'Granted',
    required: 'Required',
    requestMic: '🎙️ Request microphone',
    requestLocation: '📍 Request location',
    requestNotification: '🔔 Request notifications',
    openGpsSettings: '🛰️ Open GPS settings (ON/OFF)',
    voipSpeakerDefault: 'Default call output: speaker',
    voipSpeakerOnDesc: 'Current default: speaker ON',
    voipSpeakerOffDesc: 'Current default: earpiece/headset first',
    voipSpeakerSetOn: 'Default call output set to speaker.',
    voipSpeakerSetOff: 'Default call output set to earpiece/headset first.',
    currentAudioRoute: 'Current audio route',
    audioRouteLive: 'Live: speaker {speaker} · BT {bt}',
    refreshDeviceStatus: 'Device permission status refreshed.',
    refreshDeviceFailed: 'Failed to check device permissions.',
    openSystemSettings: '⚙️ Open system settings',
    openVoipNotification: '📞 Open VoIP notification settings',
    openBluetooth: '🎧 Open Bluetooth settings (headset)',
    refreshAudioRoute: '🔈 Refresh audio route',
    refreshAudioRouteDone: 'Audio route status refreshed.',
    deviceChecking: 'Checking...',
    refreshDevice: '🔄 Refresh status',
    speakerOn: 'ON',
    speakerOff: 'OFF',
    btConnected: 'connected',
    btDisconnected: 'not connected',
    autoListen: 'Chat auto-listen',
    autoListenDesc: 'Auto-wait on room entry',
    readAloud: 'Read incoming messages aloud',
    readAloudDesc: 'Read peer messages aloud',
    sorisaeFab: 'Floating Sorisae button',
    sorisaeFabDesc: 'Show home button',
    manualsIntroKo: 'Feature guides',
    manualsIntroTranslated: 'Feature guides · {lang}',
    kwsAdvancedTitle: '🧠 Advanced · Sorisae voice standby symbol',
    kwsSectionHint: 'Advanced wake-word settings',
    kwsEngineLabel: 'Detection engine',
    kwsProviderVosk: 'General speech (Vosk)',
    kwsProviderPorcupine: 'Wake-word only (Porcupine)',
    kwsModelFolder: 'Speech model folder',
    kwsModelPlaceholder: 'e.g. /sdcard/Download/vosk-model-small-en',
    kwsPickModel: '📂 Pick speech model file',
    kwsPicking: 'Selecting...',
    kwsPicovoiceKey: 'Picovoice access key',
    kwsPicovoicePlaceholder: 'Key from Picovoice',
    kwsKeywordFiles: 'Wake-word files (multi-select)',
    kwsPickKeywords: '📂 Pick wake-word files',
    kwsNoKeywordFiles: 'No wake-word files selected.',
    kwsSave: 'Save wake-word settings',
    kwsSaving: 'Saving...',
    kwsSaved: 'Wake-word settings saved.',
    kwsSaveFailed: 'Failed to save wake-word settings.',
    kwsVoskPathRequired: 'Enter a Vosk model folder path.',
    kwsPicovoiceKeyRequired: 'Enter a Picovoice access key.',
    kwsKeywordRequired: 'Select at least one wake-word file.',
    kwsPpnRequired: 'Select a .ppn wake-word file.',
    kwsPickPpnFailed: 'Failed to pick wake-word files.',
    kwsPpnSelected: 'Selected {count} wake-word file(s).',
    passwordChange: 'Change password',
    loginRequiredToChange: 'Sign in to change this.',
    unsupportedLanguage: 'Unsupported language.',
    countrySavedSuccess: 'Country saved.',
    countrySaveFailed: 'Failed to save country.',
    languageSavedSuccess: 'Interpretation language saved.',
    languageSaveFailed: 'Failed to save language.',
};

const CATALOG: Record<string, SettingsUiText> = { ko: KO, en: EN, ja: SETTINGS_UI_JA, zh: SETTINGS_UI_ZH };

/**
 * 설정 탭 라벨 SSOT — ko/en/ja/zh 오프라인 즉시 표시(한국어 플래시 방지).
 */
export function getSettingsText(lang?: string): SettingsUiText {
    const catalogLang = resolveBundledCatalogLang(lang ?? 'ko');
    return CATALOG[catalogLang] ?? CATALOG.en ?? KO;
}

export function formatSettingsText(template: string, vars: Record<string, string | number>): string {
    return Object.entries(vars).reduce(
        (out, [key, value]) => out.replace(new RegExp(`\\{${key}\\}`, 'g'), String(value)),
        template,
    );
}
