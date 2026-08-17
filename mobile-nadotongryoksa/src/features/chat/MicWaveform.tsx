// 마이크 ON 상태 파형 표시 — 녹음(듣는 중)일 때 막대가 위아래로 출렁이는 간단한 파형 애니메이션.
// 별도 텍스트 표기 없이 "마이크가 켜져 있고 듣고 있다"를 시각적으로만 전달한다.
import React, { useEffect, useRef } from 'react';
import { Animated, StyleSheet, View } from 'react-native';

export interface MicWaveformProps {
    active: boolean;
    color?: string;
}

const BAR_COUNT = 7;

export function MicWaveform({ active, color = '#e5484d' }: MicWaveformProps) {
    const bars = useRef(Array.from({ length: BAR_COUNT }, () => new Animated.Value(0.35))).current;

    useEffect(() => {
        if (!active) {
            bars.forEach((b) => { b.stopAnimation(); b.setValue(0.35); });
            return;
        }
        const loops = bars.map((b, i) =>
            Animated.loop(
                Animated.sequence([
                    Animated.timing(b, { toValue: 1, duration: 300 + i * 55, useNativeDriver: true }),
                    Animated.timing(b, { toValue: 0.35, duration: 300 + i * 55, useNativeDriver: true }),
                ]),
            ),
        );
        const timers = loops.map((loop, i) => setTimeout(() => loop.start(), i * 70));
        return () => {
            timers.forEach(clearTimeout);
            loops.forEach((loop) => loop.stop());
        };
    }, [active, bars]);

    if (!active) {
        return null;
    }
    return (
        <View style={styles.row} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
            {bars.map((b, i) => (
                <Animated.View
                    key={`wave-${i}`}
                    style={[styles.bar, { backgroundColor: color, transform: [{ scaleY: b }] }]}
                />
            ))}
        </View>
    );
}

const styles = StyleSheet.create({
    row: { flexDirection: 'row', alignItems: 'center', gap: 3, height: 24 },
    bar: { width: 3.5, height: 22, borderRadius: 2 },
});
