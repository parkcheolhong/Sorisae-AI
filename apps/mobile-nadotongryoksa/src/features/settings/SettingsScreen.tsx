/**
 * 설정 화면(APP_DESIGN 2-6) — 전역 ON/OFF 토글 + 기능별 사용 설명서(아코디언).
 *
 * 사용자가 여기서 한 번 켜두면 각 화면이 그 값을 기본값으로 읽어, 매번 수동으로 마이크를 누르는
 * 번거로움을 없앤다. 표시되는 토글은 모두 실제 배선된 것만 둔다.
 *  - 채팅 자동 듣기 → globalSettings.autoListen
 *  - 수신 메시지 자동 읽어주기 → companionChatReadAloud 저장소
 *  - 플로팅 소리새 버튼 → globalSettings.sorisaeFab
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Linking, Platform, Pressable, ScrollView, StyleSheet, Switch, Text, TextInput, View } from 'react-native';
import * as DocumentPicker from 'expo-document-picker';
import * as Location from 'expo-location';
import * as IntentLauncher from 'expo-intent-launcher';

import type { OnDeviceKwsProvider } from '../../native/onDeviceKws';

import { setGlobalSetting, useGlobalSettings } from './globalSettings';
import { FEATURE_MANUALS, type FeatureManual } from './featureManuals';
import { ManualViewer } from './ManualViewer';
import { ReferralInvitePanel } from './ReferralInvitePanel';
import { checkPermissionStatus, usePermissionCheck, type PermissionType } from '../../hooks/usePermissionCheck';
import { openVoipNotificationSettings, type IncomingAlertSoundMode } from '../../native/voipIncomingAlert';
import { COUNTRY_NAME_MAP, SIGNUP_COUNTRY_OPTIONS } from '../country/countryCatalog';
import { LANGS } from '../language/languageCatalog';
import {
    getCurrentVoipAudioRoute,
    isVoipAudioNativeAvailable,
    subscribeVoipAudioRouteChanges,
    type VoipAudioRouteSnapshot,
} from '../../native/voipAudio';
import { translateText } from '../../api/translate';
import { resolveLanguageLabel } from '../profile/profileFormatters';
import {
    loadChatReadAloudEnabled,
    saveChatReadAloudEnabled,
} from '../sorisae/companionChatReadAloud';
import { getBundledManual } from '../i18n/bundledManuals';
import { DOWNLOAD_LANGUAGE_OPTIONS, getSignupGuideText } from '../i18n/signupGuideCatalog';
import { OperatorLogSection, type OperatorLogSnapshot } from '../operator/OperatorLogSection';
import { handleOperatorUnlockTap, loadOperatorSurfaceUnlock, setOperatorSurfaceUnlock } from '../operator/operatorAccess';

type ManualPreviewText = {
    title: string;
    summary: string;
};

const manualPreviewCache = new Map<string, ManualPreviewText>();

interface Props {
    onClose: () => void;
    /** 레거시: 프로필 인라인 UI가 없을 때만 사용 */
    onOpenProfile?: () => void;
    appVersion: string;
    buildNumber: string | number;
    /** 사용자가 지정한 언어(번역 대상). 기본 'ko'. */
    userLang?: string;
    /** 로그인 사용자 프로필(인라인 편집) */
    userEmail?: string;
    userCountryCode?: string;
    userPreferredLanguage?: string;
    onChangeCountry?: (code: string) => void;
    onChangeLanguage?: (code: string) => void;
    profileSaving?: boolean;
    profileError?: string;
    profileSuccess?: string;
    /** VoIP/채팅 수신 알림 울림 방식 */
    incomingAlertSoundMode?: IncomingAlertSoundMode;
    onIncomingAlertSoundModeChange?: (mode: IncomingAlertSoundMode) => void;
    onOpenPasswordChange?: () => void;
    kwsProvider?: OnDeviceKwsProvider;
    kwsModelPath?: string;
    kwsPorcupineAccessKey?: string;
    kwsPorcupineKeywordPaths?: string[];
    onSaveKws?: (params: {
        provider: OnDeviceKwsProvider;
        modelPath: string;
        porcupineAccessKey: string;
        porcupineKeywordPaths: string[];
    }) => Promise<void>;
    /** 노래 번역 설명서 상단 옵션 패널 */
    songManualPanel?: React.ReactNode;
    /** 설정 탭을 열 때 바로 이 설명서로 이동 */
    initialManualId?: string | null;
    onInitialManualConsumed?: () => void;
    /** 추천 QR 패널용 로그인 토큰 */
    authToken?: string | null;
    /** 관계자 로그 스냅샷(언어 코드·감사 이벤트 — 사용자 화면 비노출) */
    operatorLogSnapshot?: OperatorLogSnapshot;
}

interface ToggleRowProps {
    icon: string;
    label: string;
    desc: string;
    value: boolean;
    onValueChange: (v: boolean) => void;
    testID?: string;
}

function ToggleRow({ icon, label, desc, value, onValueChange, testID }: ToggleRowProps) {
    return (
        <View style={styles.toggleRow}>
            <Text style={styles.toggleIcon}>{icon}</Text>
            <View style={styles.toggleTextWrap}>
                <Text style={styles.toggleLabel}>{label}</Text>
                <Text style={styles.toggleDesc}>{desc}</Text>
            </View>
            <Switch
                value={value}
                onValueChange={onValueChange}
                trackColor={{ false: '#cfd8e6', true: '#9ec8ff' }}
                thumbColor={value ? '#1E6FE0' : '#f4f4f5'}
                accessibilityLabel={testID}
                testID={testID}
            />
        </View>
    );
}

interface SectionCardProps {
    title: string;
    accent: string;
    children: React.ReactNode;
}

function SectionCard({ title, accent, children }: SectionCardProps) {
    return (
        <View style={styles.groupCard}>
            <Text style={[styles.groupTitle, { color: accent }]}>{title}</Text>
            {children}
        </View>
    );
}

export function SettingsScreen({
    onClose,
    onOpenProfile = () => {},
    appVersion,
    buildNumber,
    userLang = 'ko',
    userEmail,
    userCountryCode = '',
    userPreferredLanguage = '',
    onChangeCountry,
    onChangeLanguage,
    profileSaving = false,
    profileError = '',
    profileSuccess = '',
    incomingAlertSoundMode = 'sound',
    onIncomingAlertSoundModeChange,
    onOpenPasswordChange,
    kwsProvider = 'vosk',
    kwsModelPath = '',
    kwsPorcupineAccessKey = '',
    kwsPorcupineKeywordPaths = [],
    onSaveKws = async () => {},
    songManualPanel,
    initialManualId,
    onInitialManualConsumed,
    authToken,
    operatorLogSnapshot,
}: Props) {
    const settings = useGlobalSettings();
    const t = getSettingsText(userLang);
    const { requestPermissions } = usePermissionCheck();
    const [operatorUnlockTick, setOperatorUnlockTick] = useState(0);

    useEffect(() => {
        void loadOperatorSurfaceUnlock().then(() => setOperatorUnlockTick((n) => n + 1));
    }, []);

    const handleVersionTap = useCallback(() => {
        void handleOperatorUnlockTap().then((unlocked) => {
            if (unlocked) {
                setOperatorUnlockTick((n) => n + 1);
            }
        });
    }, []);

    useEffect(() => {
        if (!initialManualId) {
            return;
        }
        const manual = FEATURE_MANUALS.find((m) => m.id === initialManualId) ?? null;
        if (manual) {
            setActiveManual(manual);
        }
        onInitialManualConsumed?.();
    }, [initialManualId, onInitialManualConsumed]);
    const [kwsProviderDraft, setKwsProviderDraft] = useState<OnDeviceKwsProvider>(kwsProvider);
    const [kwsModelPathDraft, setKwsModelPathDraft] = useState(kwsModelPath);
    const [kwsPorcupineAccessKeyDraft, setKwsPorcupineAccessKeyDraft] = useState(kwsPorcupineAccessKey);
    const [kwsPorcupineKeywordPathsDraft, setKwsPorcupineKeywordPathsDraft] = useState<string[]>(kwsPorcupineKeywordPaths);
    const [kwsSaving, setKwsSaving] = useState(false);
    const [kwsPicking, setKwsPicking] = useState(false);
    const [kwsSaveMessage, setKwsSaveMessage] = useState('');
    const [kwsSaveError, setKwsSaveError] = useState('');
    const [deviceReadyLoading, setDeviceReadyLoading] = useState(false);
    const [deviceReadyError, setDeviceReadyError] = useState('');
    const [deviceReadyMessage, setDeviceReadyMessage] = useState('');
    const [micGranted, setMicGranted] = useState(false);
    const [locationGranted, setLocationGranted] = useState(false);
    const [gpsServicesEnabled, setGpsServicesEnabled] = useState(false);
    const [notificationGranted, setNotificationGranted] = useState(true);
    const [audioRoute, setAudioRoute] = useState<VoipAudioRouteSnapshot | null>(null);
    const [manualPreviewTextMap, setManualPreviewTextMap] = useState<Record<string, ManualPreviewText>>({});
    const [readAloudEnabled, setReadAloudEnabled] = useState(false);
    const [kwsAdvancedOpen, setKwsAdvancedOpen] = useState(false);
    const [countryPickerOpen, setCountryPickerOpen] = useState(false);
    const [langPickerOpen, setLangPickerOpen] = useState(false);
    const hasInlineProfile = Boolean(onChangeCountry && onChangeLanguage);

    useEffect(() => {
        setKwsProviderDraft(kwsProvider);
    }, [kwsProvider]);

    useEffect(() => {
        setKwsModelPathDraft(kwsModelPath);
    }, [kwsModelPath]);

    useEffect(() => {
        setKwsPorcupineAccessKeyDraft(kwsPorcupineAccessKey);
    }, [kwsPorcupineAccessKey]);

    useEffect(() => {
        setKwsPorcupineKeywordPathsDraft(kwsPorcupineKeywordPaths);
    }, [kwsPorcupineKeywordPaths]);

    const refreshDeviceReadiness = useCallback(() => {
        setDeviceReadyLoading(true);
        setDeviceReadyError('');
        setDeviceReadyMessage('');
        void Promise.all([
            checkPermissionStatus('RECORD_AUDIO'),
            checkPermissionStatus('ACCESS_FINE_LOCATION'),
            checkPermissionStatus('POST_NOTIFICATIONS'),
            Location.hasServicesEnabledAsync(),
            getCurrentVoipAudioRoute(),
        ])
            .then(([mic, location, notification, gpsEnabled, routeSnapshot]) => {
                setMicGranted(mic);
                setLocationGranted(location);
                setNotificationGranted(notification);
                setGpsServicesEnabled(Boolean(gpsEnabled));
                setAudioRoute(routeSnapshot);
                setDeviceReadyMessage(t.refreshDeviceStatus);
            })
            .catch((error: any) => {
                setDeviceReadyError(error?.message || t.refreshDeviceFailed);
            })
            .finally(() => {
                setDeviceReadyLoading(false);
            });
    }, [t.refreshDeviceFailed, t.refreshDeviceStatus]);

    useEffect(() => {
        refreshDeviceReadiness();
    }, [refreshDeviceReadiness]);

    useEffect(() => {
        void loadChatReadAloudEnabled().then(setReadAloudEnabled);
    }, []);

    useEffect(() => {
        if (!isVoipAudioNativeAvailable()) {
            return undefined;
        }
        const unsubscribe = subscribeVoipAudioRouteChanges((snapshot) => {
            setAudioRoute(snapshot);
        });
        return () => {
            unsubscribe();
        };
    }, []);

    useEffect(() => {
        const lang = String(userLang || 'ko').trim().toLowerCase();
        if (lang === 'ko') {
            setManualPreviewTextMap({});
            return;
        }
        let alive = true;

        const hydrate = async () => {
            const nextMap: Record<string, ManualPreviewText> = {};
            for (const manual of FEATURE_MANUALS) {
                const cacheKey = `${manual.id}:${lang}`;
                const cached = manualPreviewCache.get(cacheKey);
                if (cached) {
                    nextMap[manual.id] = cached;
                    continue;
                }
                const bundled = getBundledManual(manual.id, lang);
                if (bundled) {
                    const translated: ManualPreviewText = { title: bundled.title, summary: bundled.summary };
                    manualPreviewCache.set(cacheKey, translated);
                    nextMap[manual.id] = translated;
                    continue;
                }
                try {
                    const [titleRes, summaryRes] = await Promise.all([
                        translateText(manual.titleKo, 'ko', lang, 8000),
                        translateText(manual.summaryKo, 'ko', lang, 8000),
                    ]);
                    const translated: ManualPreviewText = {
                        title: titleRes.translated || getBundledManual(manual.id, 'en')?.title || manual.titleKo,
                        summary: summaryRes.translated || getBundledManual(manual.id, 'en')?.summary || manual.summaryKo,
                    };
                    manualPreviewCache.set(cacheKey, translated);
                    nextMap[manual.id] = translated;
                } catch {
                    const enFallback = getBundledManual(manual.id, 'en');
                    nextMap[manual.id] = enFallback
                        ? { title: enFallback.title, summary: enFallback.summary }
                        : { title: manual.titleKo, summary: manual.summaryKo };
                }
            }

            if (alive) {
                setManualPreviewTextMap(nextMap);
            }
        };

        void hydrate();
        return () => {
            alive = false;
        };
    }, [userLang]);

    const formatAudioRouteLabel = useCallback((snapshot: VoipAudioRouteSnapshot | null): string => {
        if (!snapshot) {
            return '확인 불가';
        }
        if (snapshot.route === 'bluetooth') {
            return 'BT';
        }
        if (snapshot.route === 'wired') {
            return '이어폰';
        }
        if (snapshot.route === 'speaker') {
            return '스피커';
        }
        if (snapshot.route === 'earpiece') {
            return '이어피스';
        }
        return '확인 불가';
    }, []);

    const requestDevicePermission = useCallback((permission: PermissionType, featureName: string) => {
        setDeviceReadyError('');
        setDeviceReadyMessage('');
        void requestPermissions([permission], featureName, (message) => {
            setDeviceReadyError(message);
        }).then((granted) => {
            if (granted) {
                setDeviceReadyMessage(`${featureName} 권한이 허용되었습니다.`);
            }
            refreshDeviceReadiness();
        });
    }, [refreshDeviceReadiness, requestPermissions]);

    const openSystemPanel = useCallback((androidAction: string) => {
        if (Platform.OS === 'android') {
            void IntentLauncher.startActivityAsync(androidAction).catch(() => {
                void Linking.openSettings();
            });
            return;
        }
        void Linking.openSettings();
    }, []);

    const normalizeFileUriToPath = useCallback((uri?: string | null): string => {
        const raw = String(uri || '').trim();
        if (!raw) {
            return '';
        }
        if (raw.startsWith('file://')) {
            return decodeURIComponent(raw.replace(/^file:\/\//, ''));
        }
        return raw;
    }, []);

    const getParentDirPath = useCallback((path: string): string => {
        const normalized = String(path || '').replace(/\\/g, '/').trim();
        if (!normalized) {
            return '';
        }
        const idx = normalized.lastIndexOf('/');
        if (idx <= 0) {
            return normalized;
        }
        return normalized.slice(0, idx);
    }, []);

    const handlePickVoskModelPath = useCallback(() => {
        setKwsSaveError('');
        setKwsSaveMessage('');
        setKwsPicking(true);
        void DocumentPicker.getDocumentAsync({
            multiple: false,
            copyToCacheDirectory: true,
            type: '*/*',
        })
            .then((result) => {
                if (result.canceled || !result.assets?.length) {
                    return;
                }
                const assetPath = normalizeFileUriToPath(result.assets[0]?.uri);
                const parentDir = getParentDirPath(assetPath);
                if (!parentDir) {
                    setKwsSaveError('모델 파일 경로를 해석하지 못했습니다. 경로를 수동으로 입력해 주세요.');
                    return;
                }
                setKwsModelPathDraft(parentDir);
                setKwsSaveMessage('선택한 파일 기준으로 모델 폴더 경로를 설정했습니다.');
            })
            .catch((error: any) => {
                setKwsSaveError(error?.message || '모델 파일 선택에 실패했습니다.');
            })
            .finally(() => {
                setKwsPicking(false);
            });
    }, [getParentDirPath, normalizeFileUriToPath]);

    const handlePickPorcupineKeywords = useCallback(() => {
        setKwsSaveError('');
        setKwsSaveMessage('');
        setKwsPicking(true);
        void DocumentPicker.getDocumentAsync({
            multiple: true,
            copyToCacheDirectory: true,
            type: '*/*',
        })
            .then((result) => {
                if (result.canceled || !result.assets?.length) {
                    return;
                }
                const nextPaths = result.assets
                    .map((asset) => normalizeFileUriToPath(asset.uri))
                    .filter((path) => path.toLowerCase().endsWith('.ppn'));
                if (nextPaths.length === 0) {
                    setKwsSaveError(t.kwsPpnRequired);
                    return;
                }
                const deduped = Array.from(new Set(nextPaths));
                setKwsPorcupineKeywordPathsDraft(deduped);
                setKwsSaveMessage(formatSettingsText(t.kwsPpnSelected, { count: deduped.length }));
            })
            .catch((error: any) => {
                setKwsSaveError(error?.message || t.kwsPickPpnFailed);
            })
            .finally(() => {
                setKwsPicking(false);
            });
    }, [normalizeFileUriToPath, t.kwsPickPpnFailed, t.kwsPpnRequired, t.kwsPpnSelected]);

    const handleAutoListen = useCallback((v: boolean) => {
        void setGlobalSetting('autoListen', v);
    }, []);

    const handleReadAloud = useCallback((v: boolean) => {
        setReadAloudEnabled(v);
        void saveChatReadAloudEnabled(v);
    }, []);

    const handleSorisaeFab = useCallback((v: boolean) => {
        void setGlobalSetting('sorisaeFab', v);
    }, []);

    const handleSaveKws = useCallback(() => {
        setKwsSaveError('');
        setKwsSaveMessage('');

        if (kwsProviderDraft === 'vosk' && !kwsModelPathDraft.trim()) {
            setKwsSaveError(t.kwsVoskPathRequired);
            return;
        }
        if (kwsProviderDraft === 'porcupine') {
            if (!kwsPorcupineAccessKeyDraft.trim()) {
                setKwsSaveError(t.kwsPicovoiceKeyRequired);
                return;
            }
            if (kwsPorcupineKeywordPathsDraft.length === 0) {
                setKwsSaveError(t.kwsKeywordRequired);
                return;
            }
        }

        setKwsSaving(true);
        void onSaveKws({
            provider: kwsProviderDraft,
            modelPath: kwsModelPathDraft,
            porcupineAccessKey: kwsPorcupineAccessKeyDraft,
            porcupineKeywordPaths: kwsPorcupineKeywordPathsDraft,
        })
            .then(() => {
                setKwsSaveMessage(t.kwsSaved);
            })
            .catch((error: any) => {
                setKwsSaveError(error?.message || t.kwsSaveFailed);
            })
            .finally(() => {
                setKwsSaving(false);
            });
    }, [
        kwsModelPathDraft,
        kwsPorcupineAccessKeyDraft,
        kwsPorcupineKeywordPathsDraft,
        kwsProviderDraft,
        onSaveKws,
        t.kwsKeywordRequired,
        t.kwsPicovoiceKeyRequired,
        t.kwsSaveFailed,
        t.kwsSaved,
        t.kwsVoskPathRequired,
    ]);

    // 설명서를 열었으면 뷰어를 전체로 보여준다(지정 언어 자동 번역).
    if (activeManual) {
        return (
            <ManualViewer
                manual={activeManual}
                userLang={userLang}
                onBack={() => setActiveManual(null)}
                topSlot={activeManual.id === 'song' ? songManualPanel : undefined}
            />
        );
    }

    return (
        <View style={styles.root}>
            <View style={styles.header}>
                <Text style={styles.headerTitle}>{t.headerTitle}</Text>
                <Pressable
                    onPress={onClose}
                    style={styles.closeBtn}
                    accessibilityRole="button"
                    accessibilityLabel="worldlinco-settings-close"
                    testID="worldlinco-settings-close"
                >
                    <Text style={styles.closeBtnText}>✕</Text>
                </Pressable>
            </View>
            <Text style={styles.intro}>{t.intro}</Text>

            <ScrollView style={{ flex: 1 }} contentContainerStyle={styles.scrollContent}>
                <SectionCard title={t.sectionAccount} accent="#0B7A4B">
                    {userEmail ? <Text style={styles.toggleDesc}>{userEmail}</Text> : null}
                    {hasInlineProfile ? (
                        <>
                            <Text style={styles.downloadLangSection}>{getSignupGuideText('downloadLangSection', userLang)}</Text>
                            <Text style={styles.downloadLangHint}>{getSignupGuideText('downloadLangHint', userLang)}</Text>
                            <View style={styles.downloadLangRow}>
                                {DOWNLOAD_LANGUAGE_OPTIONS.map((opt) => {
                                    const active = userLang === opt.code;
                                    return (
                                        <Pressable
                                            key={`dl-lang-${opt.code}`}
                                            style={[styles.downloadLangChip, active && styles.downloadLangChipActive]}
                                            onPress={() => onChangeLanguage?.(opt.code)}
                                            testID={`worldlinco-settings-download-lang-${opt.code}`}
                                        >
                                            <Text style={[styles.downloadLangChipText, active && styles.downloadLangChipTextActive]}>
                                                {opt.label}
                                            </Text>
                                        </Pressable>
                                    );
                                })}
                            </View>
                            <Pressable
                                style={styles.profileRow}
                                onPress={() => { setCountryPickerOpen((v) => !v); setLangPickerOpen(false); }}
                                testID="worldlinco-settings-country-toggle"
                            >
                                <Text style={styles.profileRowLabel}>{t.country}</Text>
                                <Text style={styles.profileRowValue}>
                                    {(SIGNUP_COUNTRY_OPTIONS.find((c) => c.code === userCountryCode)?.label)
                                        || COUNTRY_NAME_MAP[userCountryCode]
                                        || userCountryCode
                                        || t.notSet} ▾
                                </Text>
                            </Pressable>
                            {countryPickerOpen ? (
                                <ScrollView style={styles.profilePickerList} nestedScrollEnabled>
                                    {SIGNUP_COUNTRY_OPTIONS.map((c) => {
                                        const active = c.code === userCountryCode;
                                        return (
                                            <Pressable
                                                key={`settings-country-${c.code}`}
                                                style={[styles.profilePickerOption, active && styles.profilePickerOptionActive]}
                                                onPress={() => {
                                                    setCountryPickerOpen(false);
                                                    onChangeCountry?.(c.code);
                                                }}
                                                testID={`worldlinco-settings-country-${c.code}`}
                                            >
                                                <Text style={[styles.profilePickerOptionText, active && styles.profilePickerOptionTextActive]}>
                                                    {c.label} ({c.code})
                                                </Text>
                                                {active ? <Text style={styles.profilePickerCheck}>✓</Text> : null}
                                            </Pressable>
                                        );
                                    })}
                                </ScrollView>
                            ) : null}
                            <Pressable
                                style={styles.profileRow}
                                onPress={() => { setLangPickerOpen((v) => !v); setCountryPickerOpen(false); }}
                                testID="worldlinco-settings-language-toggle"
                            >
                                <Text style={styles.profileRowLabel}>{t.translationLanguage}</Text>
                                <Text style={styles.profileRowValue}>
                                    {(LANGS.find((l) => l.code === userPreferredLanguage)?.label)
                                        || userPreferredLanguage
                                        || t.notSet} ▾
                                </Text>
                            </Pressable>
                            {langPickerOpen ? (
                                <ScrollView style={styles.profilePickerList} nestedScrollEnabled>
                                    {LANGS.map((l) => {
                                        const active = l.code === userPreferredLanguage;
                                        return (
                                            <Pressable
                                                key={`settings-lang-${l.code}`}
                                                style={[styles.profilePickerOption, active && styles.profilePickerOptionActive]}
                                                onPress={() => {
                                                    setLangPickerOpen(false);
                                                    onChangeLanguage?.(l.code);
                                                }}
                                                testID={`worldlinco-settings-language-${l.code}`}
                                            >
                                                <Text style={[styles.profilePickerOptionText, active && styles.profilePickerOptionTextActive]}>
                                                    {l.label}
                                                </Text>
                                                {active ? <Text style={styles.profilePickerCheck}>✓</Text> : null}
                                            </Pressable>
                                        );
                                    })}
                                </ScrollView>
                            ) : null}
                            {profileSaving ? <Text style={styles.toggleDesc}>{t.saving}</Text> : null}
                            {profileError ? <Text style={styles.kwsSaveError}>{profileError}</Text> : null}
                            {profileSuccess ? <Text style={styles.kwsSaveSuccess}>{profileSuccess}</Text> : null}
                        </>
                    ) : (
                        <Pressable
                            style={styles.linkRow}
                            onPress={onOpenProfile}
                            accessibilityRole="button"
                            accessibilityLabel="worldlinco-settings-open-profile"
                            testID="worldlinco-settings-open-profile"
                        >
                            <Text style={styles.linkRowIcon}>🌐</Text>
                            <View style={styles.toggleTextWrap}>
                                <Text style={styles.toggleLabel}>{t.profileLinkLabel}</Text>
                                <Text style={styles.toggleDesc}>{t.profileLinkDesc}</Text>
                            </View>
                            <Text style={styles.linkChevron}>›</Text>
                        </Pressable>
                    )}
                </SectionCard>

                {onIncomingAlertSoundModeChange ? (
                    <SectionCard title={t.sectionIncomingAlert} accent="#0B6FB0">
                        <Text style={styles.kwsSectionHint}>{t.incomingAlertHint}</Text>
                        <View style={styles.segmentRow}>
                            {([
                                { mode: 'sound' as IncomingAlertSoundMode, label: t.alertSound },
                                { mode: 'vibrate' as IncomingAlertSoundMode, label: t.alertVibrate },
                                { mode: 'silent' as IncomingAlertSoundMode, label: t.alertSilent },
                            ]).map((item) => {
                                const active = incomingAlertSoundMode === item.mode;
                                return (
                                    <Pressable
                                        key={`alert-mode-${item.mode}`}
                                        style={[styles.segment, active && styles.segmentActive]}
                                        onPress={() => onIncomingAlertSoundModeChange(item.mode)}
                                        accessibilityRole="button"
                                        accessibilityLabel={`수신 알림 ${item.label}`}
                                        testID={`worldlinco-settings-alert-${item.mode}`}
                                    >
                                        <Text style={[styles.segmentText, active && styles.segmentTextActive]}>{item.label}</Text>
                                    </Pressable>
                                );
                            })}
                        </View>
                    </SectionCard>
                ) : null}

                <SectionCard title={t.sectionDevicePrep} accent="#0B7A4B">
                    <View style={styles.deviceCheckRow}>
                        <Text style={styles.deviceCheckTitle}>{t.micPermission}</Text>
                        <Text style={[styles.deviceCheckValue, micGranted ? styles.deviceCheckOk : styles.deviceCheckWarn]}>{micGranted ? t.granted : t.required}</Text>
                    </View>
                    <Pressable
                        style={styles.deviceActionBtn}
                        onPress={() => requestDevicePermission('RECORD_AUDIO', '음성 입력')}
                        accessibilityRole="button"
                        accessibilityLabel="worldlinco-settings-request-mic-permission"
                        testID="worldlinco-settings-request-mic-permission"
                    >
                        <Text style={styles.deviceActionBtnText}>{t.requestMic}</Text>
                    </Pressable>

                    <View style={styles.deviceCheckRow}>
                        <Text style={styles.deviceCheckTitle}>{t.locationPermission}</Text>
                        <Text style={[styles.deviceCheckValue, locationGranted ? styles.deviceCheckOk : styles.deviceCheckWarn]}>{locationGranted ? t.granted : t.required}</Text>
                    </View>
                    <Pressable
                        style={styles.deviceActionBtn}
                        onPress={() => requestDevicePermission('ACCESS_FINE_LOCATION', 'GPS 기반 언어 감지')}
                        accessibilityRole="button"
                        accessibilityLabel="worldlinco-settings-request-location-permission"
                        testID="worldlinco-settings-request-location-permission"
                    >
                        <Text style={styles.deviceActionBtnText}>{t.requestLocation}</Text>
                    </Pressable>
                    <View style={styles.deviceCheckRow}>
                        <Text style={styles.deviceCheckTitle}>{t.gpsService}</Text>
                        <Text style={[styles.deviceCheckValue, gpsServicesEnabled ? styles.deviceCheckOk : styles.deviceCheckWarn]}>{gpsServicesEnabled ? t.speakerOn : t.speakerOff}</Text>
                    </View>
                    <Pressable
                        style={styles.deviceActionBtn}
                        onPress={() => openSystemPanel('android.settings.LOCATION_SOURCE_SETTINGS')}
                        accessibilityRole="button"
                        accessibilityLabel="worldlinco-settings-open-location-source-settings"
                        testID="worldlinco-settings-open-location-source-settings"
                    >
                        <Text style={styles.deviceActionBtnText}>{t.openGpsSettings}</Text>
                    </Pressable>

                    <View style={styles.deviceCheckRow}>
                        <Text style={styles.deviceCheckTitle}>{t.notificationPermission}</Text>
                        <Text style={[styles.deviceCheckValue, notificationGranted ? styles.deviceCheckOk : styles.deviceCheckWarn]}>{notificationGranted ? t.granted : t.required}</Text>
                    </View>
                    <Pressable
                        style={styles.deviceActionBtn}
                        onPress={() => requestDevicePermission('POST_NOTIFICATIONS', 'VoIP 수신 알림')}
                        accessibilityRole="button"
                        accessibilityLabel="worldlinco-settings-request-notification-permission"
                        testID="worldlinco-settings-request-notification-permission"
                    >
                        <Text style={styles.deviceActionBtnText}>{t.requestNotification}</Text>
                    </Pressable>

                    <ToggleRow
                        icon="🎧"
                        label={t.voipSpeakerDefault}
                        desc={settings.voipSpeakerDefaultOn ? t.voipSpeakerOnDesc : t.voipSpeakerOffDesc}
                        value={settings.voipSpeakerDefaultOn}
                        onValueChange={(v) => {
                            void setGlobalSetting('voipSpeakerDefaultOn', v);
                            setDeviceReadyMessage(v ? t.voipSpeakerSetOn : t.voipSpeakerSetOff);
                            setDeviceReadyError('');
                        }}
                        testID="worldlinco-settings-toggle-voip-speaker-default"
                    />

                    <View style={styles.deviceCheckRow}>
                        <Text style={styles.deviceCheckTitle}>{t.currentAudioRoute}</Text>
                        <Text style={[styles.deviceCheckValue, audioRoute ? styles.deviceCheckOk : styles.deviceCheckWarn]}>
                            {formatAudioRouteLabel(audioRoute)}
                        </Text>
                    </View>
                    <Text style={styles.toggleDesc}>
                        {formatSettingsText(t.audioRouteLive, {
                            speaker: audioRoute?.speakerphone ? t.speakerOn : t.speakerOff,
                            bt: audioRoute?.bluetoothConnected ? t.btConnected : t.btDisconnected,
                        })}
                    </Text>

                    <Pressable
                        style={styles.deviceActionBtn}
                        onPress={() => openSystemPanel('android.settings.BLUETOOTH_SETTINGS')}
                        accessibilityRole="button"
                        accessibilityLabel="worldlinco-settings-open-bluetooth-settings"
                        testID="worldlinco-settings-open-bluetooth-settings"
                    >
                        <Text style={styles.deviceActionBtnText}>{t.openBluetooth}</Text>
                    </Pressable>
                    <Pressable
                        style={styles.deviceActionBtn}
                        onPress={() => {
                            setDeviceReadyError('');
                            setDeviceReadyMessage('');
                            void getCurrentVoipAudioRoute().then((snapshot) => {
                                setAudioRoute(snapshot);
                                setDeviceReadyMessage(t.refreshAudioRouteDone);
                            });
                        }}
                        accessibilityRole="button"
                        accessibilityLabel="worldlinco-settings-refresh-audio-route"
                        testID="worldlinco-settings-refresh-audio-route"
                    >
                        <Text style={styles.deviceActionBtnText}>{t.refreshAudioRoute}</Text>
                    </Pressable>

                    <View style={styles.deviceActionRow}>
                        <Pressable
                            style={[styles.deviceActionBtn, styles.deviceActionBtnInline]}
                            onPress={refreshDeviceReadiness}
                            accessibilityRole="button"
                            accessibilityLabel="worldlinco-settings-refresh-device-readiness"
                            testID="worldlinco-settings-refresh-device-readiness"
                        >
                            <Text style={styles.deviceActionBtnText}>{deviceReadyLoading ? t.deviceChecking : t.refreshDevice}</Text>
                        </Pressable>
                        <Pressable
                            style={[styles.deviceActionBtn, styles.deviceActionBtnInline]}
                            onPress={() => {
                                void Linking.openSettings();
                            }}
                            accessibilityRole="button"
                            accessibilityLabel="worldlinco-settings-open-system-settings"
                            testID="worldlinco-settings-open-system-settings"
                        >
                            <Text style={styles.deviceActionBtnText}>{t.openSystemSettings}</Text>
                        </Pressable>
                    </View>
                    <Pressable
                        style={styles.deviceActionBtn}
                        onPress={() => {
                            void openVoipNotificationSettings();
                        }}
                        accessibilityRole="button"
                        accessibilityLabel="worldlinco-settings-open-voip-notification-settings"
                        testID="worldlinco-settings-open-voip-notification-settings"
                    >
                        <Text style={styles.deviceActionBtnText}>{t.openVoipNotification}</Text>
                    </Pressable>

                    {deviceReadyError ? <Text style={styles.kwsSaveError}>{deviceReadyError}</Text> : null}
                    {!deviceReadyError && !!deviceReadyMessage ? <Text style={styles.kwsSaveSuccess}>{deviceReadyMessage}</Text> : null}
                </SectionCard>

                <SectionCard title={t.sectionChatVoice} accent="#1E6FE0">
                    <ToggleRow
                        icon="🎙️"
                        label={t.autoListen}
                        desc={t.autoListenDesc}
                        value={settings.autoListen}
                        onValueChange={handleAutoListen}
                        testID="worldlinco-settings-toggle-autolisten"
                    />
                    <ToggleRow
                        icon="🔊"
                        label={t.readAloud}
                        desc={t.readAloudDesc}
                        value={readAloudEnabled}
                        onValueChange={handleReadAloud}
                        testID="worldlinco-settings-toggle-read-aloud"
                    />
                </SectionCard>

                <SectionCard title={t.sectionSorisae} accent="#7A3FF2">
                    <ToggleRow
                        icon="🐦"
                        label={t.sorisaeFab}
                        desc={t.sorisaeFabDesc}
                        value={settings.sorisaeFab}
                        onValueChange={handleSorisaeFab}
                        testID="worldlinco-settings-toggle-sorisaefab"
                    />
                </SectionCard>

                <View style={styles.groupCard}>
                    <ReferralInvitePanel authToken={authToken} />
                </View>

                <View style={styles.groupCard}>
                    <Text style={[styles.groupTitle, { color: '#0B6FB0' }]}>{t.sectionManuals}</Text>
                    <Text style={styles.guideIntro}>
                        {userLang === 'ko'
                            ? t.manualsIntroKo
                            : formatSettingsText(t.manualsIntroTranslated, { lang: resolveLanguageLabel(userLang) })}
                    </Text>
                    {FEATURE_MANUALS.map((m, idx) => (
                        <View key={m.id}>
                            {idx > 0 ? <View style={styles.divider} /> : null}
                            <Pressable
                                style={styles.linkRow}
                                onPress={() => setActiveManual(m)}
                                accessibilityRole="button"
                                accessibilityLabel={`worldlinco-settings-manual-${m.id}`}
                                testID={`worldlinco-settings-manual-${m.id}`}
                            >
                                <Text style={styles.linkRowIcon}>{m.icon}</Text>
                                <View style={styles.toggleTextWrap}>
                                    <Text style={styles.toggleLabel}>{manualPreviewTextMap[m.id]?.title ?? m.titleKo}</Text>
                                    <Text style={styles.toggleDesc}>{manualPreviewTextMap[m.id]?.summary ?? m.summaryKo}</Text>
                                </View>
                                <Text style={styles.linkChevron}>›</Text>
                            </Pressable>
                        </View>
                    ))}
                </View>

                <View style={styles.groupCard}>
                    <Pressable
                        style={styles.helpToggle}
                        onPress={() => setKwsAdvancedOpen((v) => !v)}
                        accessibilityRole="button"
                        accessibilityLabel="worldlinco-settings-kws-advanced-toggle"
                        testID="worldlinco-settings-kws-advanced-toggle"
                    >
                        <Text style={[styles.groupTitle, { color: '#5f6b80' }]}>
                            {t.kwsAdvancedTitle} {kwsAdvancedOpen ? '▲' : '▼'}
                        </Text>
                    </Pressable>
                    {kwsAdvancedOpen ? (
                        <>
                            <Text style={styles.kwsSectionHint}>{t.kwsSectionHint}</Text>
                            <Text style={styles.kwsLabel}>{t.kwsEngineLabel}</Text>
                            <View style={styles.kwsProviderRow}>
                                <Pressable
                                    style={[styles.kwsProviderChip, kwsProviderDraft === 'vosk' && styles.kwsProviderChipActive]}
                                    onPress={() => setKwsProviderDraft('vosk')}
                                    accessibilityRole="button"
                                    accessibilityLabel="worldlinco-settings-kws-provider-vosk"
                                    testID="worldlinco-settings-kws-provider-vosk"
                                >
                                    <Text style={[styles.kwsProviderChipText, kwsProviderDraft === 'vosk' && styles.kwsProviderChipTextActive]}>{t.kwsProviderVosk}</Text>
                                </Pressable>
                                <Pressable
                                    style={[styles.kwsProviderChip, kwsProviderDraft === 'porcupine' && styles.kwsProviderChipActive]}
                                    onPress={() => setKwsProviderDraft('porcupine')}
                                    accessibilityRole="button"
                                    accessibilityLabel="worldlinco-settings-kws-provider-porcupine"
                                    testID="worldlinco-settings-kws-provider-porcupine"
                                >
                                    <Text style={[styles.kwsProviderChipText, kwsProviderDraft === 'porcupine' && styles.kwsProviderChipTextActive]}>{t.kwsProviderPorcupine}</Text>
                                </Pressable>
                            </View>

                            <Text style={styles.kwsLabel}>{t.kwsModelFolder}</Text>
                            <TextInput
                                style={styles.kwsInput}
                                value={kwsModelPathDraft}
                                onChangeText={setKwsModelPathDraft}
                                placeholder={t.kwsModelPlaceholder}
                                placeholderTextColor="#8fa0ba"
                                autoCapitalize="none"
                                autoCorrect={false}
                                accessibilityLabel="worldlinco-settings-kws-model-path"
                                testID="worldlinco-settings-kws-model-path"
                            />
                            <Pressable
                                style={styles.kwsPickBtn}
                                onPress={handlePickVoskModelPath}
                                disabled={kwsPicking}
                                accessibilityRole="button"
                                accessibilityLabel="worldlinco-settings-kws-model-path-pick"
                                testID="worldlinco-settings-kws-model-path-pick"
                            >
                                <Text style={styles.kwsPickBtnText}>{kwsPicking ? t.kwsPicking : t.kwsPickModel}</Text>
                            </Pressable>

                            <Text style={styles.kwsLabel}>{t.kwsPicovoiceKey}</Text>
                            <TextInput
                                style={styles.kwsInput}
                                value={kwsPorcupineAccessKeyDraft}
                                onChangeText={setKwsPorcupineAccessKeyDraft}
                                placeholder={t.kwsPicovoicePlaceholder}
                                placeholderTextColor="#8fa0ba"
                                autoCapitalize="none"
                                autoCorrect={false}
                                accessibilityLabel="worldlinco-settings-kws-porcupine-access-key"
                                testID="worldlinco-settings-kws-porcupine-access-key"
                            />

                            <Text style={styles.kwsLabel}>{t.kwsKeywordFiles}</Text>
                            <Pressable
                                style={styles.kwsPickBtn}
                                onPress={handlePickPorcupineKeywords}
                                disabled={kwsPicking}
                                accessibilityRole="button"
                                accessibilityLabel="worldlinco-settings-kws-porcupine-keyword-paths-pick"
                                testID="worldlinco-settings-kws-porcupine-keyword-paths-pick"
                            >
                                <Text style={styles.kwsPickBtnText}>{kwsPicking ? t.kwsPicking : t.kwsPickKeywords}</Text>
                            </Pressable>
                            {kwsPorcupineKeywordPathsDraft.length > 0 ? (
                                <View style={styles.kwsPathList}>
                                    {kwsPorcupineKeywordPathsDraft.map((path, idx) => (
                                        <Text key={`kws-ppn-${idx}`} style={styles.kwsPathListItem} numberOfLines={2}>{`${idx + 1}. ${path}`}</Text>
                                    ))}
                                </View>
                            ) : (
                                <Text style={styles.kwsHintText}>{t.kwsNoKeywordFiles}</Text>
                            )}

                            {kwsSaveError ? <Text style={styles.kwsSaveError}>{kwsSaveError}</Text> : null}
                            {kwsSaveMessage ? <Text style={styles.kwsSaveSuccess}>{kwsSaveMessage}</Text> : null}

                            <Pressable
                                style={[styles.kwsSaveBtn, kwsSaving && styles.kwsSaveBtnDisabled]}
                                onPress={handleSaveKws}
                                disabled={kwsSaving || kwsPicking}
                                accessibilityRole="button"
                                accessibilityLabel="worldlinco-settings-kws-save"
                                testID="worldlinco-settings-kws-save"
                            >
                                <Text style={styles.kwsSaveBtnText}>{kwsSaving ? t.kwsSaving : t.kwsSave}</Text>
                            </Pressable>
                        </>
                    ) : null}
                </View>

                {onOpenPasswordChange ? (
                    <SectionCard title={t.sectionSecurity} accent="#5f6b80">
                        <Pressable
                            style={styles.deviceActionBtn}
                            onPress={onOpenPasswordChange}
                            testID="worldlinco-settings-password-change"
                        >
                            <Text style={styles.deviceActionBtnText}>{t.passwordChange}</Text>
                        </Pressable>
                    </SectionCard>
                ) : null}

                <View style={styles.appInfo}>
                    <Pressable onPress={handleVersionTap} accessibilityLabel="worldlinco-settings-version">
                        <Text style={styles.appInfoText}>WorldLinco · v{appVersion} · build {String(buildNumber)}</Text>
                    </Pressable>
                </View>

                {operatorLogSnapshot ? (
                    <OperatorLogSection
                        key={`operator-log-${operatorUnlockTick}`}
                        snapshot={operatorLogSnapshot}
                        onLock={() => {
                            void setOperatorSurfaceUnlock(false).then(() => setOperatorUnlockTick((n) => n + 1));
                        }}
                    />
                ) : null}
            </ScrollView>
        </View>
    );
}

const styles = StyleSheet.create({
    root: { flex: 1, paddingHorizontal: 14, backgroundColor: 'rgba(255,255,255,0.96)' },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingTop: 8,
        paddingBottom: 6,
    },
    headerTitle: { fontSize: 24, fontWeight: '900', color: '#10243f' },
    closeBtn: {
        width: 40,
        height: 40,
        borderRadius: 20,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'rgba(255,255,255,0.85)',
        borderWidth: 1,
        borderColor: '#d4def0',
    },
    closeBtnText: { fontSize: 18, fontWeight: '800', color: '#41506b' },
    intro: { fontSize: 14, color: '#3a4a63', lineHeight: 20, marginBottom: 10 },
    scrollContent: { paddingBottom: 40 },
    groupCard: {
        backgroundColor: 'rgba(255,255,255,0.94)',
        borderRadius: 18,
        padding: 16,
        marginBottom: 14,
        borderWidth: 1,
        borderColor: '#e1e9f5',
        shadowColor: '#1b3a6b',
        shadowOpacity: 0.06,
        shadowRadius: 10,
        shadowOffset: { width: 0, height: 4 },
        elevation: 2,
    },
    groupTitle: { fontSize: 17, fontWeight: '900', marginBottom: 10 },
    guideIntro: { fontSize: 13, color: '#6a788f', marginBottom: 8, lineHeight: 18 },
    toggleRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 6 },
    toggleIcon: { fontSize: 22, width: 34, textAlign: 'center' },
    toggleTextWrap: { flex: 1, paddingHorizontal: 8 },
    toggleLabel: { fontSize: 15, fontWeight: '800', color: '#16263f' },
    toggleDesc: { fontSize: 12.5, color: '#6a788f', marginTop: 2 },
    divider: { height: 1, backgroundColor: '#eef2f8', marginVertical: 6 },
    helpToggle: { marginTop: 10, alignSelf: 'flex-start' },
    helpToggleText: { fontSize: 13, fontWeight: '800', color: '#1E6FE0' },
    helpBox: {
        marginTop: 8,
        backgroundColor: '#f3f7ff',
        borderRadius: 12,
        padding: 12,
        borderWidth: 1,
        borderColor: '#dce8fb',
    },
    helpText: { fontSize: 13, color: '#33455f', lineHeight: 20 },
    linkRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 6 },
    linkRowIcon: { fontSize: 22, width: 34, textAlign: 'center' },
    linkChevron: { fontSize: 26, color: '#9aa7bd', fontWeight: '700', paddingHorizontal: 4 },
    appInfo: { alignItems: 'center', paddingVertical: 18 },
    appInfoText: { fontSize: 12.5, color: '#7b889d', fontWeight: '600' },
    kwsLabel: {
        marginTop: 10,
        marginBottom: 6,
        fontSize: 13,
        fontWeight: '800',
        color: '#28466f',
    },
    kwsSectionHint: {
        marginBottom: 8,
        color: '#8fa0ba',
        fontSize: 12.5,
        lineHeight: 18,
    },
    kwsProviderRow: { flexDirection: 'row', gap: 8, marginBottom: 2 },
    kwsProviderChip: {
        borderRadius: 12,
        paddingHorizontal: 14,
        paddingVertical: 8,
        borderWidth: 1,
        borderColor: '#d2ddf0',
        backgroundColor: '#f4f7fd',
    },
    kwsProviderChipActive: {
        borderColor: '#1E6FE0',
        backgroundColor: '#e8f1ff',
    },
    kwsProviderChipText: {
        color: '#4a5f7f',
        fontWeight: '700',
    },
    kwsProviderChipTextActive: {
        color: '#1E6FE0',
    },
    kwsInput: {
        borderWidth: 1,
        borderColor: '#d7e3f6',
        backgroundColor: '#ffffff',
        borderRadius: 10,
        paddingHorizontal: 11,
        paddingVertical: 10,
        color: '#13253f',
        fontSize: 13,
    },
    kwsPickBtn: {
        marginTop: 8,
        borderRadius: 10,
        paddingVertical: 10,
        paddingHorizontal: 10,
        borderWidth: 1,
        borderColor: '#cfe0f8',
        backgroundColor: '#f4f9ff',
        alignItems: 'center',
    },
    kwsPickBtnText: {
        color: '#1E6FE0',
        fontWeight: '800',
        fontSize: 12.5,
    },
    kwsPathList: {
        marginTop: 8,
        borderRadius: 10,
        borderWidth: 1,
        borderColor: '#e1e9f5',
        backgroundColor: '#ffffff',
        paddingVertical: 8,
        paddingHorizontal: 10,
        gap: 6,
    },
    kwsPathListItem: {
        color: '#33455f',
        fontSize: 12,
        lineHeight: 18,
    },
    kwsHintText: {
        marginTop: 8,
        color: '#6a788f',
        fontSize: 12,
    },
    kwsSaveBtn: {
        marginTop: 12,
        borderRadius: 12,
        paddingVertical: 11,
        alignItems: 'center',
        backgroundColor: '#1E6FE0',
    },
    kwsSaveBtnDisabled: { opacity: 0.6 },
    kwsSaveBtnText: { color: '#ffffff', fontWeight: '800', fontSize: 14 },
    kwsSaveError: { marginTop: 8, color: '#b42318', fontSize: 12.5, fontWeight: '700' },
    kwsSaveSuccess: { marginTop: 8, color: '#0B7A4B', fontSize: 12.5, fontWeight: '700' },
    deviceCheckRow: {
        marginTop: 6,
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    deviceCheckTitle: {
        fontSize: 13.5,
        fontWeight: '800',
        color: '#1f3555',
    },
    deviceCheckValue: {
        fontSize: 12.5,
        fontWeight: '800',
    },
    deviceCheckOk: {
        color: '#0B7A4B',
    },
    deviceCheckWarn: {
        color: '#b54708',
    },
    deviceActionRow: {
        flexDirection: 'row',
        gap: 8,
        marginTop: 8,
    },
    deviceActionBtn: {
        marginTop: 8,
        borderRadius: 10,
        paddingVertical: 10,
        paddingHorizontal: 10,
        borderWidth: 1,
        borderColor: '#d5e5f9',
        backgroundColor: '#f7fbff',
        alignItems: 'center',
    },
    deviceActionBtnInline: {
        flex: 1,
    },
    deviceActionBtnText: {
        color: '#1E6FE0',
        fontWeight: '800',
        fontSize: 12.5,
    },
    profileRow: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingVertical: 12,
        paddingHorizontal: 12,
        borderRadius: 10,
        borderWidth: 1,
        borderColor: '#e1e9f5',
        backgroundColor: '#ffffff',
        marginTop: 8,
    },
    profileRowLabel: { fontSize: 13.5, fontWeight: '800', color: '#6a788f' },
    profileRowValue: {
        fontSize: 13.5,
        fontWeight: '800',
        color: '#0b2e5e',
        flexShrink: 1,
        textAlign: 'right',
        marginLeft: 12,
    },
    profilePickerList: {
        maxHeight: 220,
        marginTop: 6,
        borderWidth: 1,
        borderColor: '#e1e9f5',
        borderRadius: 10,
        backgroundColor: '#ffffff',
    },
    profilePickerOption: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingVertical: 10,
        paddingHorizontal: 12,
        borderBottomWidth: 1,
        borderBottomColor: '#eef2f8',
    },
    profilePickerOptionActive: { backgroundColor: '#eef5ff' },
    profilePickerOptionText: { fontSize: 13.5, color: '#33455f', fontWeight: '600' },
    profilePickerOptionTextActive: { color: '#1E6FE0', fontWeight: '800' },
    profilePickerCheck: { color: '#1E6FE0', fontWeight: '900', fontSize: 14 },
    segmentRow: { flexDirection: 'row', gap: 8, marginTop: 4 },
    segment: {
        flex: 1,
        paddingVertical: 11,
        borderRadius: 10,
        borderWidth: 1,
        borderColor: '#dce6f2',
        backgroundColor: '#f4f7fd',
        alignItems: 'center',
    },
    segmentActive: { borderColor: '#1E6FE0', backgroundColor: '#e8f1ff' },
    segmentText: { color: '#33455f', fontSize: 13, fontWeight: '700' },
    segmentTextActive: { color: '#1E6FE0', fontWeight: '900' },
    downloadLangSection: { fontSize: 13.5, fontWeight: '900', color: '#0B7A4B', marginTop: 10 },
    downloadLangHint: { fontSize: 12, color: '#6a788f', lineHeight: 18, marginTop: 4, marginBottom: 6 },
    downloadLangRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 4 },
    downloadLangChip: {
        paddingVertical: 8,
        paddingHorizontal: 12,
        borderRadius: 20,
        borderWidth: 1,
        borderColor: '#dce6f2',
        backgroundColor: '#f4f7fd',
    },
    downloadLangChipActive: { borderColor: '#1E6FE0', backgroundColor: '#e8f1ff' },
    downloadLangChipText: { fontSize: 13, fontWeight: '700', color: '#33455f' },
    downloadLangChipTextActive: { color: '#1E6FE0', fontWeight: '900' },
});
