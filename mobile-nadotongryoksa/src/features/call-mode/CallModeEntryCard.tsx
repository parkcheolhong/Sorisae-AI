import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { CallMode } from './types';

interface CallModeEntryCardProps {
    selectedMode: CallMode;
    onSelect: (mode: CallMode) => void;
}

export function CallModeEntryCard({ selectedMode, onSelect }: CallModeEntryCardProps) {
    return (
        <View style={styles.container}>
            <Pressable
                style={[styles.card, selectedMode === 'pstn_assist' && styles.cardSelected]}
                onPress={() => onSelect('pstn_assist')}
                accessibilityRole="radio"
                accessibilityState={{ selected: selectedMode === 'pstn_assist' }}
            >
                <View style={styles.cardHeader}>
                    <Text style={[styles.modeTitle, selectedMode === 'pstn_assist' && styles.modeTitleSelected]}>
                        일반통화 보조 모드
                    </Text>
                    {selectedMode === 'pstn_assist' && (
                        <View style={styles.activeBadge}>
                            <Text style={styles.activeBadgeText}>✓ 선택됨</Text>
                        </View>
                    )}
                </View>
                <Text style={styles.modeDesc}>기존 전화(PSTN)에 실시간 통역을 보조합니다.</Text>
            </Pressable>

            <Pressable
                style={[styles.card, selectedMode === 'voip_full_auto' && styles.cardSelected]}
                onPress={() => onSelect('voip_full_auto')}
                accessibilityRole="radio"
                accessibilityState={{ selected: selectedMode === 'voip_full_auto' }}
            >
                <View style={styles.cardHeader}>
                    <Text style={[styles.modeTitle, selectedMode === 'voip_full_auto' && styles.modeTitleSelected]}>
                        VoIP 완전자동 모드
                    </Text>
                    <View style={styles.recommendBadge}>
                        <Text style={styles.recommendBadgeText}>⭐ 권장</Text>
                    </View>
                    {selectedMode === 'voip_full_auto' && (
                        <View style={styles.activeBadge}>
                            <Text style={styles.activeBadgeText}>✓ 선택됨</Text>
                        </View>
                    )}
                </View>
                <Text style={styles.modeDesc}>앱 내 인터넷 통화로 통역을 완전 자동화합니다.</Text>
            </Pressable>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        gap: 8,
        marginVertical: 4,
    },
    card: {
        borderWidth: 1,
        borderColor: '#dce6f2',
        borderRadius: 10,
        padding: 12,
        backgroundColor: '#ffffff',
    },
    cardSelected: {
        borderColor: '#1e6fe0',
        backgroundColor: '#e3f0ff',
    },
    cardHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: 6,
        marginBottom: 4,
    },
    modeTitle: {
        fontSize: 14,
        fontWeight: '600',
        color: '#3a4356',
    },
    modeTitleSelected: {
        color: '#1e6fe0',
    },
    modeDesc: {
        fontSize: 12,
        color: '#5f6b80',
    },
    activeBadge: {
        backgroundColor: '#1e6fe0',
        borderRadius: 6,
        paddingHorizontal: 6,
        paddingVertical: 2,
    },
    activeBadgeText: {
        fontSize: 11,
        color: '#ffffff',
        fontWeight: '600',
    },
    recommendBadge: {
        backgroundColor: '#fff4d6',
        borderRadius: 6,
        paddingHorizontal: 6,
        paddingVertical: 2,
    },
    recommendBadgeText: {
        fontSize: 11,
        color: '#b45309',
    },
});
