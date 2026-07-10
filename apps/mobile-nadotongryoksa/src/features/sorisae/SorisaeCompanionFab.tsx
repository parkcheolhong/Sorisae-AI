import React from 'react';
import { Animated, PanResponderInstance, Text } from 'react-native';

import { styles } from '../../../App.styles';

type SorisaeCompanionFabProps = {
    sorisaeBtnPos: Animated.ValueXY;
    sorisaePanResponder: PanResponderInstance;
};

/** 소리새 AI 플로팅 심볼 — 드래그 이동, 탭 시 전용 창 진입. */
export function SorisaeCompanionFab({
    sorisaeBtnPos,
    sorisaePanResponder,
}: SorisaeCompanionFabProps) {
    return (
        <Animated.View
            {...sorisaePanResponder.panHandlers}
            accessible
            accessibilityRole="button"
            accessibilityLabel="worldlinco-sorisae-fab"
            testID="worldlinco-sorisae-fab"
            style={[
                styles.sorisaeFab,
                { transform: sorisaeBtnPos.getTranslateTransform() },
            ]}
        >
            <Text style={styles.sorisaeFabIcon}>🐦</Text>
        </Animated.View>
    );
}
