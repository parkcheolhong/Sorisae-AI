// 키패드(다이얼패드) 인라인 섹션 — 네이티브 전화앱의 키패드 탭과 동일한 숫자판.
// 번호를 직접 눌러 입력하고 초록 [전화] 버튼으로 일반전화 통역(PSTN+자동통역)을 건다. 모달 없이 화면 안에서 사용.
import React, { useState, useCallback } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

export interface DialpadSectionProps {
    initialNumber?: string;
    onCall: (phoneNumber: string) => void;
}

const KEYS: { d: string; sub?: string }[] = [
    { d: '1' }, { d: '2', sub: 'ABC' }, { d: '3', sub: 'DEF' },
    { d: '4', sub: 'GHI' }, { d: '5', sub: 'JKL' }, { d: '6', sub: 'MNO' },
    { d: '7', sub: 'PQRS' }, { d: '8', sub: 'TUV' }, { d: '9', sub: 'WXYZ' },
    { d: '*' }, { d: '0', sub: '+' }, { d: '#' },
];

export function DialpadSection({ initialNumber = '', onCall }: DialpadSectionProps) {
    const [number, setNumber] = useState(initialNumber);

    const press = useCallback((d: string) => {
        setNumber((prev) => (prev + d).slice(0, 24));
    }, []);

    const backspace = useCallback(() => {
        setNumber((prev) => prev.slice(0, -1));
    }, []);

    const clearAll = useCallback(() => {
        setNumber('');
    }, []);

    const canCall = number.replace(/\D/g, '').length >= 3;

    return (
        <View style={styles.card}>
            <View style={styles.displayRow}>
                <Text style={styles.display} numberOfLines={1} adjustsFontSizeToFit testID="dialpad-display">
                    {number || '번호 입력'}
                </Text>
            </View>
            <View style={styles.grid}>
                {KEYS.map((k) => (
                    <Pressable
                        key={`dialkey-${k.d}`}
                        style={styles.key}
                        onPress={() => press(k.d)}
                        onLongPress={k.d === '0' ? () => press('+') : undefined}
                        accessibilityRole="button"
                        accessibilityLabel={`다이얼 ${k.d}`}
                        testID={`dialpad-key-${k.d}`}
                    >
                        <Text style={styles.keyDigit}>{k.d}</Text>
                        {k.sub ? <Text style={styles.keySub}>{k.sub}</Text> : null}
                    </Pressable>
                ))}
            </View>
            <View style={styles.actionRow}>
                <View style={styles.sideSlot} />
                <Pressable
                    style={[styles.callBtn, !canCall && styles.callBtnDisabled]}
                    onPress={() => { if (canCall) { onCall(number); } }}
                    disabled={!canCall}
                    accessibilityRole="button"
                    accessibilityLabel="전화 걸기"
                    testID="dialpad-call"
                >
                    <Text style={styles.callBtnText}>📞 전화</Text>
                </Pressable>
                <Pressable
                    style={styles.sideSlot}
                    onPress={backspace}
                    onLongPress={clearAll}
                    disabled={number.length === 0}
                    accessibilityRole="button"
                    accessibilityLabel="지우기"
                    testID="dialpad-backspace"
                >
                    <Text style={[styles.backspace, number.length === 0 && styles.backspaceDisabled]}>⌫</Text>
                </Pressable>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    card: { backgroundColor: '#ffffff', borderRadius: 14, padding: 12, borderWidth: 1, borderColor: '#dce6f2', marginTop: 4 },
    displayRow: { paddingVertical: 14, alignItems: 'center', borderBottomWidth: 1, borderBottomColor: '#eef2f8', marginBottom: 8 },
    display: { fontSize: 30, fontWeight: '700', color: '#0b2e5e', letterSpacing: 1 },
    grid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between' },
    key: { width: '31%', aspectRatio: 1.7, alignItems: 'center', justifyContent: 'center', borderRadius: 12, backgroundColor: '#f4f9ff', marginBottom: 8 },
    keyDigit: { fontSize: 24, fontWeight: '700', color: '#1a1f36' },
    keySub: { fontSize: 9, fontWeight: '700', color: '#8a93a3', letterSpacing: 1, marginTop: 1 },
    actionRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 4 },
    sideSlot: { width: 64, height: 52, alignItems: 'center', justifyContent: 'center' },
    callBtn: { flex: 1, marginHorizontal: 8, backgroundColor: '#19a463', borderRadius: 30, paddingVertical: 14, alignItems: 'center', justifyContent: 'center' },
    callBtnDisabled: { backgroundColor: '#bcd3c7' },
    callBtnText: { color: '#ffffff', fontSize: 17, fontWeight: '800' },
    backspace: { fontSize: 24, color: '#5f6b80' },
    backspaceDisabled: { color: '#cdd6e3' },
    hint: { color: '#8a93a3', fontSize: 11, lineHeight: 16, textAlign: 'center', marginTop: 10 },
});
