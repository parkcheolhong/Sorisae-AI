// 최근기록(통화내역) 인라인 섹션 — 네이티브 전화앱 '최근기록' 탭과 같은 형태로
// 발신(↗)·수신(↙)·부재중(✕, 빨강) 통화를 최신순으로 보여준다. 행을 누르면 같은 상대에게 다시 건다.
import React, { useCallback } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { CallHistoryEntry } from '../../services/callHistory';

export interface RecentCallsSectionProps {
    entries: CallHistoryEntry[];
    loading?: boolean;
    onRefresh: () => void;
    onCallAgain: (entry: CallHistoryEntry) => void;
    onClear: () => void;
}

function directionGlyph(direction: CallHistoryEntry['direction']): string {
    if (direction === 'missed') {
        return '✕';
    }
    return direction === 'in' ? '↙' : '↗';
}

function kindLabel(entry: CallHistoryEntry): string {
    const dir = entry.direction === 'missed' ? '부재중' : entry.direction === 'in' ? '수신' : '발신';
    const kind = entry.kind === 'voip' ? '통역통화' : '일반전화';
    return `${kind} · ${dir}`;
}

function formatWhen(iso: string): string {
    const t = Date.parse(iso);
    if (!Number.isFinite(t)) {
        return '';
    }
    const now = Date.now();
    const diffMin = Math.floor((now - t) / 60000);
    if (diffMin < 1) {
        return '방금';
    }
    if (diffMin < 60) {
        return `${diffMin}분 전`;
    }
    const d = new Date(t);
    const sameDay = new Date(now).toDateString() === d.toDateString();
    const hh = String(d.getHours()).padStart(2, '0');
    const mm = String(d.getMinutes()).padStart(2, '0');
    if (sameDay) {
        return `${hh}:${mm}`;
    }
    return `${d.getMonth() + 1}월 ${d.getDate()}일 ${hh}:${mm}`;
}

export function RecentCallsSection({ entries, loading, onRefresh, onCallAgain, onClear }: RecentCallsSectionProps) {
    const renderRow = useCallback((entry: CallHistoryEntry) => {
        const missed = entry.direction === 'missed';
        return (
            <Pressable
                key={`recent-${entry.id}`}
                style={styles.row}
                onPress={() => onCallAgain(entry)}
                accessibilityRole="button"
                accessibilityLabel={`${entry.label} 다시 걸기`}
                testID={`recent-call-${entry.id}`}
            >
                <Text style={[styles.glyph, missed ? styles.glyphMissed : styles.glyphOut]}>{directionGlyph(entry.direction)}</Text>
                <View style={styles.rowText}>
                    <Text style={[styles.label, missed && styles.labelMissed]} numberOfLines={1}>{entry.label}</Text>
                    <Text style={styles.meta} numberOfLines={1}>{kindLabel(entry)}{entry.phone ? ` · ${entry.phone}` : ''}</Text>
                </View>
                <Text style={styles.when}>{formatWhen(entry.at)}</Text>
            </Pressable>
        );
    }, [onCallAgain]);

    return (
        <View style={styles.card}>
            <View style={styles.headerRow}>
                <Text style={styles.title}>🕘 최근기록</Text>
                <View style={styles.headerBtns}>
                    <Pressable style={styles.ghostBtn} onPress={onRefresh} testID="recent-calls-refresh">
                        <Text style={styles.ghostBtnText}>{loading ? '새로고침 중...' : '새로고침'}</Text>
                    </Pressable>
                    {entries.length > 0 ? (
                        <Pressable style={styles.ghostBtn} onPress={onClear} testID="recent-calls-clear">
                            <Text style={styles.ghostBtnText}>기록 삭제</Text>
                        </Pressable>
                    ) : null}
                </View>
            </View>
            {entries.length === 0 ? (
                <Text style={styles.empty}>아직 통화 기록이 없습니다. 연락처에서 통역통화·일반전화를 걸면 여기에 쌓입니다.</Text>
            ) : (
                entries.map(renderRow)
            )}
        </View>
    );
}

const styles = StyleSheet.create({
    card: { backgroundColor: '#ffffff', borderRadius: 14, padding: 12, borderWidth: 1, borderColor: '#dce6f2', marginTop: 4 },
    headerRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 },
    title: { color: '#0b2e5e', fontSize: 16, fontWeight: '800' },
    headerBtns: { flexDirection: 'row', gap: 8 },
    ghostBtn: { paddingVertical: 7, paddingHorizontal: 12, borderRadius: 9, borderWidth: 1, borderColor: '#bcd3f0' },
    ghostBtnText: { color: '#1e6fe0', fontSize: 12, fontWeight: '700' },
    row: { flexDirection: 'row', alignItems: 'center', paddingVertical: 11, borderBottomWidth: 1, borderBottomColor: '#e3eaf5', gap: 12 },
    glyph: { fontSize: 16, fontWeight: '800', width: 22, textAlign: 'center' },
    glyphOut: { color: '#19a463' },
    glyphMissed: { color: '#e5484d' },
    rowText: { flex: 1 },
    label: { color: '#1a1f36', fontSize: 15, fontWeight: '700' },
    labelMissed: { color: '#e5484d' },
    meta: { color: '#5f6b80', fontSize: 12, marginTop: 2 },
    when: { color: '#8a93a3', fontSize: 12 },
    empty: { color: '#8a93a3', fontSize: 13, textAlign: 'center', paddingVertical: 22, lineHeight: 19 },
});
