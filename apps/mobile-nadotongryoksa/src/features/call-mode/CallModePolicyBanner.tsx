import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

export function CallModePolicyBanner() {
    return (
        <View style={styles.banner}>
            <View style={styles.pstnRow}>
                <Text style={styles.pstnIcon}>⚠️</Text>
                <Text style={styles.pstnText}>
                    일반통화(PSTN) 모드는 기존 이동통신 요금이 발생할 수 있습니다.
                </Text>
            </View>
            <View style={styles.voipRow}>
                <Text style={styles.voipIcon}>💡</Text>
                <View style={styles.voipTextWrap}>
                    <Text style={styles.voipText}>인터넷 연결 시 </Text>
                    <View style={styles.voipBadge}>
                        <Text style={styles.voipBadgeText}>VoIP 완전자동</Text>
                    </View>
                    <Text style={styles.voipText}> 모드를 권장합니다.</Text>
                </View>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    banner: {
        backgroundColor: '#18182a',
        borderRadius: 8,
        borderWidth: 1,
        borderColor: '#2e2e44',
        padding: 10,
        gap: 6,
        marginVertical: 4,
    },
    pstnRow: {
        flexDirection: 'row',
        alignItems: 'flex-start',
        gap: 6,
    },
    pstnIcon: {
        fontSize: 13,
        marginTop: 1,
    },
    pstnText: {
        flex: 1,
        fontSize: 12,
        color: '#c08040',
        lineHeight: 18,
    },
    voipRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
    },
    voipIcon: {
        fontSize: 13,
    },
    voipTextWrap: {
        flex: 1,
        flexDirection: 'row',
        alignItems: 'center',
        flexWrap: 'wrap',
    },
    voipText: {
        fontSize: 12,
        color: '#8090b0',
    },
    voipBadge: {
        backgroundColor: '#2a3060',
        borderRadius: 5,
        paddingHorizontal: 5,
        paddingVertical: 1,
        marginHorizontal: 2,
    },
    voipBadgeText: {
        fontSize: 11,
        color: '#80a8ff',
        fontWeight: '600',
    },
});
