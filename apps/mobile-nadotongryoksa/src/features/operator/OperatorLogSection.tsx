import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import type { CallModeAuditEvent } from '../../app/appTypes';
import { getLangLabelText } from '../language/languageCatalog';
import { isOperatorSurfaceVisible } from './operatorAccess';
import { BidirectionalLanguagePairBadge } from '../i18n/BidirectionalLanguagePairBadge';

export interface OperatorLogSnapshot {
    userId?: number | null;
    email?: string | null;
    preferredLanguage?: string | null;
    countryCode?: string | null;
    fromLang?: string | null;
    toLang?: string | null;
    voipAuditEvents?: CallModeAuditEvent[];
    lastTranslationLog?: string | null;
}

interface Props {
    snapshot: OperatorLogSnapshot;
    onLock?: () => void;
}

export function OperatorLogSection({ snapshot, onLock }: Props) {
    if (!isOperatorSurfaceVisible()) {
        return null;
    }

    const events = snapshot.voipAuditEvents ?? [];

    return (
        <View style={styles.root}>
            <Text style={styles.title}>관계자 로그 (운영·개발 전용)</Text>
            <Text style={styles.hint}>
                언어 코드·call_id·감사 이벤트는 실구매 사용자 화면에 노출하지 않습니다.
            </Text>
            {snapshot.fromLang && snapshot.toLang ? (
                <BidirectionalLanguagePairBadge fromLang={snapshot.fromLang} toLang={snapshot.toLang} />
            ) : null}
            <Text style={styles.row}>user_id: {snapshot.userId ?? '—'}</Text>
            <Text style={styles.row}>email: {snapshot.email ?? '—'}</Text>
            <Text style={styles.row}>
                preferred_language: {snapshot.preferredLanguage ?? '—'}
                {snapshot.preferredLanguage ? ` (${getLangLabelText(snapshot.preferredLanguage)})` : ''}
            </Text>
            <Text style={styles.row}>country_code: {snapshot.countryCode ?? '—'}</Text>
            <Text style={styles.row}>
                pipeline fromLang → toLang: {snapshot.fromLang ?? '—'} → {snapshot.toLang ?? '—'}
            </Text>
            {snapshot.lastTranslationLog ? (
                <Text style={styles.row}>last status: {snapshot.lastTranslationLog}</Text>
            ) : null}
            <Text style={styles.subTitle}>VoIP 감사 로그 ({events.length})</Text>
            <ScrollView style={styles.logScroll} nestedScrollEnabled>
                {events.length === 0 ? (
                    <Text style={styles.empty}>감사 이벤트 없음</Text>
                ) : (
                    events.map((event) => (
                        <View key={`${event.id}-${event.created_at}`} style={styles.eventRow}>
                            <Text style={styles.eventType}>{event.event_type}</Text>
                            <Text style={styles.eventMeta}>call_id: {event.call_id}</Text>
                            <Text style={styles.eventMeta}>
                                auto_relay {event.auto_relay_requested ? 'req' : 'no'} /{' '}
                                {event.auto_relay_applied ? 'applied' : 'skip'}
                            </Text>
                        </View>
                    ))
                )}
            </ScrollView>
            {onLock && !__DEV__ ? (
                <Pressable style={styles.lockBtn} onPress={onLock}>
                    <Text style={styles.lockBtnText}>관계자 로그 잠금</Text>
                </Pressable>
            ) : null}
        </View>
    );
}

const styles = StyleSheet.create({
    root: {
        marginTop: 12,
        padding: 12,
        borderRadius: 12,
        borderWidth: 1,
        borderColor: '#f0c9a8',
        backgroundColor: '#fff8f0',
    },
    title: { fontSize: 14, fontWeight: '900', color: '#8a4b12' },
    hint: { fontSize: 11.5, color: '#9a6b3a', marginTop: 4, lineHeight: 16 },
    subTitle: { fontSize: 12.5, fontWeight: '800', color: '#8a4b12', marginTop: 10 },
    row: { fontSize: 11.5, color: '#5c4030', marginTop: 4, fontFamily: 'monospace' },
    logScroll: { maxHeight: 160, marginTop: 6 },
    empty: { fontSize: 11.5, color: '#9a6b3a', fontStyle: 'italic' },
    eventRow: {
        paddingVertical: 6,
        borderBottomWidth: 1,
        borderBottomColor: '#f5e0cc',
    },
    eventType: { fontSize: 11.5, fontWeight: '800', color: '#5c4030' },
    eventMeta: { fontSize: 10.5, color: '#7a5a40', fontFamily: 'monospace' },
    lockBtn: {
        marginTop: 10,
        paddingVertical: 8,
        alignItems: 'center',
        borderRadius: 8,
        borderWidth: 1,
        borderColor: '#e0b88a',
    },
    lockBtnText: { fontSize: 12, fontWeight: '700', color: '#8a4b12' },
});
