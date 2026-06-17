import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { NetworkDiagnosticsSnapshot } from '../utils/networkDiagnostics';

interface Props {
    snapshot: NetworkDiagnosticsSnapshot;
}

export function NetworkTestBanner({ snapshot }: Props) {
    const statusTone = snapshot.isAccurateVoipTestReady
        ? styles.readyBanner
        : snapshot.isConnected
            ? styles.warningBanner
            : styles.errorBanner;

    return (
        <View style={[styles.banner, statusTone]}>
            <Text style={styles.title}>📶 네트워크 테스트 상태</Text>
            <Text style={styles.line}>
                현재 경로: <Text style={styles.emphasis}>{snapshot.label}</Text>
                {snapshot.carrier ? ` · ${snapshot.carrier}` : null}
                {snapshot.ssid ? ` · ${snapshot.ssid}` : null}
            </Text>
            {snapshot.isAccurateVoipTestReady ? (
                <Text style={styles.readyText}>
                    셀룰러 데이터 연결됨 — LTE/5G 기준 실전 통신 테스트가 가능합니다.
                </Text>
            ) : snapshot.warningMessage ? (
                <Text style={styles.warningText}>{snapshot.warningMessage}</Text>
            ) : null}
            <Text style={styles.matrixHint}>
                권장 매트릭스: WiFi↔WiFi · WiFi↔LTE · LTE↔LTE (각 2회 이상)
            </Text>
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
    warningBanner: {
        backgroundColor: '#241f14',
        borderColor: '#6b552f',
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
    emphasis: {
        color: '#ffffff',
        fontWeight: '700',
    },
    readyText: {
        fontSize: 12,
        color: '#8fd6a8',
        lineHeight: 18,
    },
    warningText: {
        fontSize: 12,
        color: '#e0b56a',
        lineHeight: 18,
    },
    matrixHint: {
        fontSize: 11,
        color: '#8a96ad',
        lineHeight: 16,
    },
});
