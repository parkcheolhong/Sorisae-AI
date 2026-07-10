import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Image, Pressable, Share, StyleSheet, Text, View } from 'react-native';

import { fetchReferralMe, type ReferralMePayload } from '../../services/worldlincoReferral';

type ReferralInvitePanelProps = {
    authToken?: string | null;
};

export function ReferralInvitePanel({ authToken }: ReferralInvitePanelProps) {
    const [payload, setPayload] = useState<ReferralMePayload | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const load = useCallback(async () => {
        if (!authToken) {
            setPayload(null);
            setError('');
            return;
        }
        setLoading(true);
        setError('');
        try {
            const data = await fetchReferralMe(authToken);
            setPayload(data);
        } catch (err) {
            setPayload(null);
            setError(err instanceof Error ? err.message : '추천 정보를 불러오지 못했습니다.');
        } finally {
            setLoading(false);
        }
    }, [authToken]);

    useEffect(() => {
        void load();
    }, [load]);

    const handleShare = useCallback(async () => {
        if (!payload) {
            return;
        }
        try {
            await Share.share({
                title: 'WorldLinco 초대',
                message: `WorldLinco 50개국 실시간 통번역 앱을 추천합니다.\n추천 코드: ${payload.code}\n설치 링크: ${payload.invite_url}`,
                url: payload.invite_url,
            });
        } catch {
            // 사용자가 공유 취소
        }
    }, [payload]);

    if (!authToken) {
        return (
            <View style={styles.wrap}>
                <Text style={styles.title}>🎁 친구 초대 QR</Text>
                <Text style={styles.hint}>로그인 후 나만의 추천 QR·링크를 만들 수 있습니다.</Text>
            </View>
        );
    }

    return (
        <View style={styles.wrap}>
            <Text style={styles.title}>🎁 친구 초대 QR</Text>
            <Text style={styles.hint}>
                QR을 공유하면 친구가 앱을 설치·가입할 때 추천인으로 기록됩니다.
                {payload?.discount_policy?.enabled ? ` 첫 결제 ${payload.discount_policy.percent ?? 3}% 할인이 적용됩니다.` : ''}
            </Text>
            {loading ? (
                <ActivityIndicator color="#1E6FE0" style={styles.loader} />
            ) : null}
            {error ? <Text style={styles.error}>{error}</Text> : null}
            {payload ? (
                <>
                    <View style={styles.qrBox}>
                        <Image
                            source={{ uri: payload.qr_url }}
                            style={styles.qrImage}
                            accessibilityLabel="worldlinco-referral-qr"
                        />
                    </View>
                    <Text style={styles.codeLabel}>추천 코드</Text>
                    <Text style={styles.codeValue} testID="worldlinco-referral-code">{payload.code}</Text>
                    <Text style={styles.stats}>추천 가입 {payload.signup_count}명</Text>
                    <Pressable
                        style={styles.shareBtn}
                        onPress={() => { void handleShare(); }}
                        accessibilityRole="button"
                        accessibilityLabel="worldlinco-referral-share"
                        testID="worldlinco-referral-share"
                    >
                        <Text style={styles.shareBtnText}>링크 공유하기</Text>
                    </Pressable>
                </>
            ) : null}
        </View>
    );
}

const styles = StyleSheet.create({
    wrap: {
        paddingVertical: 4,
    },
    title: {
        fontSize: 16,
        fontWeight: '800',
        color: '#1a1f36',
        marginBottom: 6,
    },
    hint: {
        fontSize: 13,
        lineHeight: 19,
        color: '#5f6b80',
        marginBottom: 10,
    },
    loader: {
        marginVertical: 12,
    },
    error: {
        color: '#c0392b',
        fontSize: 13,
        marginBottom: 8,
    },
    qrBox: {
        alignSelf: 'center',
        backgroundColor: '#fff',
        borderRadius: 16,
        padding: 12,
        borderWidth: 1,
        borderColor: '#dbe7fb',
        marginBottom: 10,
    },
    qrImage: {
        width: 180,
        height: 180,
        resizeMode: 'contain',
    },
    codeLabel: {
        fontSize: 12,
        color: '#5f6b80',
        textAlign: 'center',
    },
    codeValue: {
        fontSize: 18,
        fontWeight: '800',
        color: '#1E6FE0',
        textAlign: 'center',
        letterSpacing: 1,
        marginBottom: 6,
    },
    stats: {
        fontSize: 13,
        color: '#4a5f7f',
        textAlign: 'center',
        marginBottom: 12,
    },
    shareBtn: {
        backgroundColor: '#1E6FE0',
        borderRadius: 12,
        paddingVertical: 12,
        alignItems: 'center',
    },
    shareBtnText: {
        color: '#fff',
        fontWeight: '800',
        fontSize: 15,
    },
});
