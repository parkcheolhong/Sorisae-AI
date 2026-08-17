import React, { memo, useEffect, useRef } from 'react';
import {
    Animated,
    Easing,
    Pressable,
    StyleSheet,
    Text,
    View,
} from 'react-native';

const RING_COUNT = 3;
const RING_DURATION_MS = 2800;
const RING_STAGGER_MS = 933;

type SorisaeVoiceWaveOrbProps = {
    /** TTS 발화 중이면 파장만 멈춤(오rb·UI는 유지). */
    wavePaused: boolean;
    hintText: string;
    onPress: () => void;
};

/**
 * 소리새 창 음성 대기 오rb — 연속 파장(ripple) 상시 흐름.
 * TTS 발화 중에만 wavePaused 로 정지. gpsStatus·STT 로딩과 분리.
 */
function SorisaeVoiceWaveOrbInner({
    wavePaused,
    hintText,
    onPress,
}: SorisaeVoiceWaveOrbProps) {
    const ringProgress = useRef(
        Array.from({ length: RING_COUNT }, () => new Animated.Value(0)),
    ).current;
    const pauseMix = useRef(new Animated.Value(wavePaused ? 1 : 0)).current;
    const loopsRef = useRef<Animated.CompositeAnimation[]>([]);

    useEffect(() => {
        const animation = Animated.timing(pauseMix, {
            toValue: wavePaused ? 1 : 0,
            duration: 220,
            easing: Easing.out(Easing.quad),
            useNativeDriver: true,
        });
        animation.start();
        return () => animation.stop();
    }, [pauseMix, wavePaused]);

    useEffect(() => {
        loopsRef.current.forEach((loop) => loop.stop());
        loopsRef.current = [];

        const loops = ringProgress.map((progress, index) => {
            progress.setValue(0);
            const loop = Animated.loop(
                Animated.sequence([
                    Animated.delay(index * RING_STAGGER_MS),
                    Animated.timing(progress, {
                        toValue: 1,
                        duration: RING_DURATION_MS,
                        easing: Easing.out(Easing.quad),
                        useNativeDriver: true,
                    }),
                ]),
            );
            loop.start();
            return loop;
        });
        loopsRef.current = loops;

        return () => {
            loops.forEach((loop) => loop.stop());
            loopsRef.current = [];
        };
    }, [ringProgress]);

    return (
        <View style={styles.wrap}>
            {ringProgress.map((progress, index) => (
                <Animated.View
                    key={`sorisae-wave-ring-${index}`}
                    pointerEvents="none"
                    style={[
                        styles.ring,
                        {
                            opacity: Animated.multiply(
                                progress.interpolate({
                                    inputRange: [0, 0.1, 0.45, 0.75, 1],
                                    outputRange: [0.06, 0.36, 0.2, 0.08, 0.06],
                                }),
                                pauseMix.interpolate({
                                    inputRange: [0, 1],
                                    outputRange: [1, 0.42],
                                }),
                            ),
                            transform: [{
                                scale: progress.interpolate({
                                    inputRange: [0, 1],
                                    outputRange: [0.94, 1.68],
                                }),
                            }],
                        },
                    ]}
                />
            ))}
            <Pressable
                onPress={onPress}
                accessibilityRole="button"
                accessibilityLabel="worldlinco-sorisae-window-mic"
                testID="worldlinco-sorisae-window-mic"
                style={styles.coreBtn}
            >
                <Text style={styles.coreBird}>🐦</Text>
            </Pressable>
            <Text style={styles.hint}>{hintText}</Text>
        </View>
    );
}

export const SorisaeVoiceWaveOrb = memo(SorisaeVoiceWaveOrbInner);

const styles = StyleSheet.create({
    wrap: {
        flex: 1,
        minHeight: 136,
        alignItems: 'center',
        justifyContent: 'center',
    },
    ring: {
        position: 'absolute',
        width: 112,
        height: 112,
        borderRadius: 56,
        borderWidth: 1.5,
        borderColor: 'rgba(30, 111, 224, 0.28)',
        backgroundColor: 'rgba(70, 163, 255, 0.07)',
    },
    coreBtn: {
        width: 96,
        height: 96,
        borderRadius: 48,
        backgroundColor: '#f8fbff',
        borderWidth: 2.5,
        borderColor: '#69aef5',
        alignItems: 'center',
        justifyContent: 'center',
        shadowColor: '#1e3a66',
        shadowOpacity: 0.14,
        shadowRadius: 10,
        elevation: 4,
    },
    coreBird: { fontSize: 42 },
    hint: {
        marginTop: 10,
        color: '#1f9d57',
        fontSize: 14,
        fontWeight: '900',
        letterSpacing: 0.2,
        textAlign: 'center',
    },
});
