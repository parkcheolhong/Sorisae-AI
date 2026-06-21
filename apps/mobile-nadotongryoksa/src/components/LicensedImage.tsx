/**
 * 라이선스 게이트를 통과한 미디어만 렌더하는 이미지 컴포넌트.
 * - evaluateMedia 로 default-deny 검사 → 미허용 시 아무것도 렌더하지 않음(null).
 * - 출처표기 필수(CC-BY 등)면 캡션을 시각적으로 노출(미준수 표시 방지).
 * - 접근성: accessibilityLabel 에 제목/출처 포함.
 */

import React from 'react';
import { Image, Linking, StyleProp, StyleSheet, Text, TouchableOpacity, View, ViewStyle } from 'react-native';
import { evaluateMedia, MediaInput } from '../media/licenseGate';

type Props = {
    media: MediaInput;
    width?: number;
    height?: number;
    style?: StyleProp<ViewStyle>;
};

export default function LicensedImage({ media, width, height = 160, style }: Props) {
    const decision = evaluateMedia(media);
    if (!decision.allowed || !decision.url) {
        if (__DEV__ && media?.url) {
            // 개발 중 차단 사유를 콘솔로만 노출(프로덕션 UI 영향 없음).
            console.warn('[LicensedImage] blocked:', decision.reason, media.url);
        }
        return null;
    }
    if (decision.type === 'video') {
        // 동영상은 별도 플레이어 필요 — 현재는 렌더하지 않음(게이트만 통과 판정).
        return null;
    }

    const caption = decision.attribution;
    const a11y = [decision.title, caption].filter(Boolean).join(', ') || '이미지';

    return (
        <View style={[styles.wrap, style]}>
            <Image
                source={{ uri: decision.url }}
                style={[styles.img, { height, width: width ?? '100%' }]}
                resizeMode="cover"
                accessible
                accessibilityLabel={a11y}
            />
            {decision.requiresAttribution && caption ? (
                decision.licenseUrl ? (
                    <TouchableOpacity onPress={() => decision.licenseUrl && Linking.openURL(decision.licenseUrl)}>
                        <Text style={styles.caption}>{caption}</Text>
                    </TouchableOpacity>
                ) : (
                    <Text style={styles.caption}>{caption}</Text>
                )
            ) : caption ? (
                <Text style={styles.captionMuted}>{caption}</Text>
            ) : null}
        </View>
    );
}

const styles = StyleSheet.create({
    wrap: { borderRadius: 10, overflow: 'hidden', backgroundColor: '#0d1117' },
    img: { width: '100%', borderRadius: 10 },
    caption: { fontSize: 10, color: '#79c0ff', paddingVertical: 3, paddingHorizontal: 4 },
    captionMuted: { fontSize: 10, color: '#8b949e', paddingVertical: 3, paddingHorizontal: 4 },
});
