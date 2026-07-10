import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { formatBidirectionalLanguagePair } from './userDisplayIdentity';

interface Props {
    fromLang: string;
    toLang: string;
    compact?: boolean;
}

/** VoIP·채팅·PSTN — 양방향 언어쌍 배지(모든 사용자 화면). */
export function BidirectionalLanguagePairBadge({ fromLang, toLang, compact = false }: Props) {
    if (!fromLang || !toLang) {
        return null;
    }
    return (
        <View style={[styles.wrap, compact && styles.wrapCompact]}>
            <Text style={[styles.badge, compact && styles.badgeCompact]}>
                {formatBidirectionalLanguagePair(fromLang, toLang)}
            </Text>
        </View>
    );
}

const styles = StyleSheet.create({
    wrap: {
        marginTop: 6,
        marginBottom: 4,
        alignSelf: 'flex-start',
    },
    wrapCompact: {
        marginTop: 4,
        marginBottom: 2,
    },
    badge: {
        fontSize: 13,
        fontWeight: '800',
        color: '#0b2e5e',
        backgroundColor: '#e8f1ff',
        borderWidth: 1,
        borderColor: '#9ec8ff',
        borderRadius: 10,
        paddingVertical: 6,
        paddingHorizontal: 12,
        overflow: 'hidden',
    },
    badgeCompact: {
        fontSize: 12,
        paddingVertical: 4,
        paddingHorizontal: 10,
    },
});
