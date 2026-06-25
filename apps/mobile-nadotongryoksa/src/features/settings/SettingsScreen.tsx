/**
 * 설정 화면(APP_DESIGN 2-6) — 전역 ON/OFF 토글 + 기능별 사용 설명서(아코디언).
 *
 * 사용자가 여기서 한 번 켜두면 각 화면이 그 값을 기본값으로 읽어, 매번 수동으로 마이크를 누르는
 * 번거로움을 없앤다. 표시되는 토글은 모두 실제 배선된 것만 둔다.
 *  - 채팅 자동 듣기 → globalSettings.autoListen (채팅방 진입 시 핸즈프리 자동 시작)
 *  - 수신 메시지 자동 읽어주기 → companionChatReadAloud (채팅방 수신 메시지 음성 낭독)
 *  - 플로팅 소리새 버튼 표시 → globalSettings.sorisaeFab (홈 🐦 버튼 표시)
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Switch, Text, View } from 'react-native';

import { loadChatReadAloudEnabled, saveChatReadAloudEnabled } from '../sorisae/companionChatReadAloud';
import { setGlobalSetting, useGlobalSettings } from './globalSettings';
import { FEATURE_MANUALS, type FeatureManual } from './featureManuals';
import { ManualViewer } from './ManualViewer';

interface Props {
    onClose: () => void;
    onOpenProfile: () => void;
    appVersion: string;
    buildNumber: string | number;
    /** 사용자가 지정한 언어(번역 대상). 기본 'ko'. */
    userLang?: string;
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

interface GroupCardProps {
    title: string;
    accent: string;
    help: string;
    children: React.ReactNode;
    groupKey: string;
}

function GroupCard({ title, accent, help, children, groupKey }: GroupCardProps) {
    const [helpOpen, setHelpOpen] = useState(false);
    return (
        <View style={styles.groupCard}>
            <Text style={[styles.groupTitle, { color: accent }]}>{title}</Text>
            {children}
            <Pressable
                style={styles.helpToggle}
                onPress={() => setHelpOpen((v) => !v)}
                accessibilityRole="button"
                accessibilityLabel={`worldlinco-settings-help-${groupKey}`}
                testID={`worldlinco-settings-help-${groupKey}`}
            >
                <Text style={styles.helpToggleText}>{helpOpen ? '❓ 사용법 닫기 ▲' : '❓ 사용법 보기 ▼'}</Text>
            </Pressable>
            {helpOpen ? (
                <View style={styles.helpBox}>
                    <Text style={styles.helpText}>{help}</Text>
                </View>
            ) : null}
        </View>
    );
}

export function SettingsScreen({ onClose, onOpenProfile, appVersion, buildNumber, userLang = 'ko' }: Props) {
    const settings = useGlobalSettings();
    const [readAloud, setReadAloud] = useState(false);
    const [activeManual, setActiveManual] = useState<FeatureManual | null>(null);

    useEffect(() => {
        let alive = true;
        loadChatReadAloudEnabled()
            .then((enabled) => {
                if (alive) setReadAloud(enabled);
            })
            .catch(() => {});
        return () => {
            alive = false;
        };
    }, []);

    const handleAutoListen = useCallback((v: boolean) => {
        void setGlobalSetting('autoListen', v);
    }, []);

    const handleReadAloud = useCallback((v: boolean) => {
        setReadAloud(v);
        void saveChatReadAloudEnabled(v);
    }, []);

    const handleSorisaeFab = useCallback((v: boolean) => {
        void setGlobalSetting('sorisaeFab', v);
    }, []);

    // 설명서를 열었으면 뷰어를 전체로 보여준다(지정 언어 자동 번역).
    if (activeManual) {
        return (
            <ManualViewer
                manual={activeManual}
                userLang={userLang}
                onBack={() => setActiveManual(null)}
            />
        );
    }

    return (
        <View style={styles.root}>
            <View style={styles.header}>
                <Text style={styles.headerTitle}>⚙️ 설정</Text>
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
            <Text style={styles.intro}>
                자주 쓰는 기능을 여기서 한 번만 켜두면, 화면마다 매번 누를 필요 없이 자동으로 동작합니다.
            </Text>

            <ScrollView style={{ flex: 1 }} contentContainerStyle={styles.scrollContent}>
                <GroupCard
                    groupKey="voice"
                    title="🎧 음성 · 핸즈프리"
                    accent="#1E6FE0"
                    help={'· 채팅 자동 듣기: 채팅방에 들어가면 마이크가 자동으로 대기합니다. 말을 하면 인식해 입력칸에 채우고, 말이 끝나면(무음 약 1초) 자동으로 멈췄다가 다시 듣습니다. 매번 마이크 버튼을 누르지 않아도 됩니다.\n· 수신 메시지 자동 읽어주기: 상대가 보낸 메시지를 음성으로 읽어줍니다(URL/기호는 제외).'}
                >
                    <ToggleRow
                        icon="🎙️"
                        label="채팅 자동 듣기(핸즈프리)"
                        desc="채팅방 진입 시 마이크 자동 대기"
                        value={settings.autoListen}
                        onValueChange={handleAutoListen}
                        testID="worldlinco-settings-toggle-autolisten"
                    />
                    <View style={styles.divider} />
                    <ToggleRow
                        icon="🔊"
                        label="수신 메시지 자동 읽어주기"
                        desc="상대 메시지를 음성으로 낭독"
                        value={readAloud}
                        onValueChange={handleReadAloud}
                        testID="worldlinco-settings-toggle-readaloud"
                    />
                </GroupCard>

                <GroupCard
                    groupKey="sorisae"
                    title="🐦 소리새 AI"
                    accent="#7A3FF2"
                    help={'· 플로팅 소리새 버튼: 홈 화면에 떠 있는 파랑새(🐦) 버튼입니다. 끄면 화면에서 숨겨지고, 소리새 대화는 다른 진입점에서 계속 사용할 수 있습니다.'}
                >
                    <ToggleRow
                        icon="🐦"
                        label="플로팅 소리새 버튼 표시"
                        desc="홈 화면의 떠다니는 소리새 버튼"
                        value={settings.sorisaeFab}
                        onValueChange={handleSorisaeFab}
                        testID="worldlinco-settings-toggle-sorisaefab"
                    />
                </GroupCard>

                <GroupCard
                    groupKey="account"
                    title="👤 계정 · 프로필"
                    accent="#0B7A4B"
                    help={'· 내 국가·언어를 바꾸면 통역/번역의 기본 언어가 함께 바뀝니다.'}
                >
                    <Pressable
                        style={styles.linkRow}
                        onPress={onOpenProfile}
                        accessibilityRole="button"
                        accessibilityLabel="worldlinco-settings-open-profile"
                        testID="worldlinco-settings-open-profile"
                    >
                        <Text style={styles.linkRowIcon}>🌐</Text>
                        <View style={styles.toggleTextWrap}>
                            <Text style={styles.toggleLabel}>프로필 · 국가 · 언어 설정</Text>
                            <Text style={styles.toggleDesc}>통역/번역 기본 언어 변경</Text>
                        </View>
                        <Text style={styles.linkChevron}>›</Text>
                    </Pressable>
                </GroupCard>

                <View style={styles.groupCard}>
                    <Text style={[styles.groupTitle, { color: '#0B6FB0' }]}>📖 사용 설명서</Text>
                    <Text style={styles.guideIntro}>기능별 사용법을 지정한 언어로 자동 번역해 보여드립니다.</Text>
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
                                    <Text style={styles.toggleLabel}>{m.titleKo}</Text>
                                    <Text style={styles.toggleDesc}>{m.summaryKo}</Text>
                                </View>
                                <Text style={styles.linkChevron}>›</Text>
                            </Pressable>
                        </View>
                    ))}
                </View>

                <View style={styles.appInfo}>
                    <Text style={styles.appInfoText}>WorldLinco · v{appVersion} · build {String(buildNumber)}</Text>
                </View>
            </ScrollView>
        </View>
    );
}

const styles = StyleSheet.create({
    root: { flex: 1, paddingHorizontal: 14 },
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
});
