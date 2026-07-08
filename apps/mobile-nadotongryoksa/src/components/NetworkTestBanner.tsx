import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { NetworkDiagnosticsSnapshot } from '../utils/networkDiagnostics';

interface Props {
    snapshot: NetworkDiagnosticsSnapshot;
    /** QA/필드 테스트 힌트 — 기본 false (베타 사용자에게 불편한 경고 숨김) */
    showFieldTestHints?: boolean;
}

export function NetworkTestBanner({ snapshot, showFieldTestHints = false }: Props) {
    const statusTone = snapshot.warningMessage
        ? styles.errorBanner
        : snapshot.transport === 'cellular'
            ? styles.readyBanner
            : styles.infoBanner;

    return (
        <View style={[styles.banner, statusTone]}>
            <Text style={styles.title}>📶 연결 상태</Text>
            <Text style={styles.line}>
                {snapshot.statusMessage}
                {snapshot.carrier ? ` · ${snapshot.carrier}` : null}
                {snapshot.ssid ? ` · ${snapshot.ssid}` : null}
            </Text>
            {snapshot.warningMessage ? (
                <Text style={styles.warningText}>{snapshot.warningMessage}</Text>
            ) : null}
            {showFieldTestHints && snapshot.fieldTestHint ? (
                <Text style={styles.matrixHint}>{snapshot.fieldTestHint}</Text>
            ) : null}
        </View>
    );
}

const styles = StyleSheet.create({
    banner: {
        borderRadius: 8,
        borderWidth: 1,
        padding: 10,
        gap: 6,
        marginVertical: 4,
    },
    readyBanner: {
        backgroundColor: '#14261a',
        borderColor: '#2f6b45',
    },
    infoBanner: {
        backgroundColor: '#151c28',
        borderColor: '#2e3f58',
    },
    errorBanner: {
        backgroundColor: '#241418',
        borderColor: '#6b2f3d',
    },
    title: {
        fontSize: 13,
        fontWeight: '700',
        color: '#e8edf8',
    },
    line: {
        fontSize: 12,
        color: '#b8c4dc',
        lineHeight: 18,
    },
    warningText: {
        fontSize: 12,
        color: '#f0a0a8',
        lineHeight: 18,
    },
    matrixHint: {
        fontSize: 11,
        color: '#8a96ad',
        lineHeight: 16,
    },
});
