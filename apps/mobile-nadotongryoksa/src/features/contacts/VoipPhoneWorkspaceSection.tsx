// build 312 SSOT — 통화 탭 전화앱식 3탭(연락처 · 최근기록 · 키패드).
import React from 'react';
import { Pressable, Text, View } from 'react-native';

import { styles } from '../../../App.styles';
import { getFeatureUiText } from '../i18n/featureUiCatalog';

export type VoipWorkspaceTab = 'contacts' | 'recents' | 'keypad';

export interface VoipPhoneWorkspaceSectionProps {
    activeTab: VoipWorkspaceTab;
    onTabChange: (tab: VoipWorkspaceTab) => void;
    recentMissedCount?: number;
    contactsPane: React.ReactNode;
    recentsPane: React.ReactNode;
    keypadPane: React.ReactNode;
}

const TABS: { key: VoipWorkspaceTab; labelKey: 'voip.tabContacts' | 'voip.tabRecents' | 'voip.tabKeypad'; emoji: string; testID: string }[] = [
    { key: 'contacts', labelKey: 'voip.tabContacts', emoji: '📇', testID: 'worldlinco-voip-tab-contacts' },
    { key: 'recents', labelKey: 'voip.tabRecents', emoji: '🕘', testID: 'worldlinco-voip-tab-recents' },
    { key: 'keypad', labelKey: 'voip.tabKeypad', emoji: '⌨️', testID: 'worldlinco-voip-tab-keypad' },
];

export function VoipPhoneWorkspaceSection({
    activeTab,
    onTabChange,
    recentMissedCount = 0,
    contactsPane,
    recentsPane,
    keypadPane,
}: VoipPhoneWorkspaceSectionProps) {
    return (
        <View>
            <View style={styles.voipTabRow}>
                {TABS.map((tab) => {
                    const active = activeTab === tab.key;
                    const label = getFeatureUiText(tab.labelKey);
                    return (
                        <Pressable
                            key={tab.key}
                            style={[styles.voipTab, active && styles.voipTabActive]}
                            onPress={() => onTabChange(tab.key)}
                            accessibilityRole="button"
                            accessibilityLabel={label}
                            testID={tab.testID}
                        >
                            <Text style={[styles.voipTabText, active && styles.voipTabTextActive]}>
                                {tab.emoji} {label}
                            </Text>
                            {tab.key === 'recents' && recentMissedCount > 0 ? (
                                <View style={styles.voipTabBadge}>
                                    <Text style={styles.voipTabBadgeText}>{recentMissedCount > 9 ? '9+' : recentMissedCount}</Text>
                                </View>
                            ) : null}
                        </Pressable>
                    );
                })}
            </View>
            {activeTab === 'contacts' ? contactsPane : null}
            {activeTab === 'recents' ? recentsPane : null}
            {activeTab === 'keypad' ? keypadPane : null}
        </View>
    );
}
