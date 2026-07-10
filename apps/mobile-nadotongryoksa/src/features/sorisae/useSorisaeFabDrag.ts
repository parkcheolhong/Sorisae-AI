import React, { useRef } from 'react';
import {
    Animated,
    Dimensions,
    PanResponder,
    PanResponderInstance,
    Platform,
} from 'react-native';

type UseSorisaeFabDragResult = {
    sorisaeBtnPos: Animated.ValueXY;
    sorisaePanResponder: PanResponderInstance;
    openSorisaeWindow: () => void;
};

/** 플로팅 소리새 FAB 드래그 + 탭으로 창 열기. */
export function useSorisaeFabDrag(
    onOpenWindow: () => void,
): UseSorisaeFabDragResult {
    const sorisaeBtnPos = useRef(new Animated.ValueXY({
        x: Dimensions.get('window').width - 74,
        y: Math.round(Dimensions.get('window').height * 0.32),
    })).current;
    const sorisaeDragMovedRef = useRef(false);
    const openSorisaeWindow = () => {
        onOpenWindow();
    };
    const sorisaePanResponder = useRef(
        PanResponder.create({
            onStartShouldSetPanResponder: () => true,
            onMoveShouldSetPanResponder: (_e, g) => Math.abs(g.dx) > 4 || Math.abs(g.dy) > 4,
            onPanResponderGrant: () => {
                sorisaeDragMovedRef.current = false;
                sorisaeBtnPos.extractOffset();
            },
            onPanResponderMove: (e, g) => {
                if (Math.abs(g.dx) > 4 || Math.abs(g.dy) > 4) {
                    sorisaeDragMovedRef.current = true;
                }
                Animated.event(
                    [null, { dx: sorisaeBtnPos.x, dy: sorisaeBtnPos.y }],
                    { useNativeDriver: false },
                )(e, g);
            },
            onPanResponderRelease: () => {
                sorisaeBtnPos.flattenOffset();
                if (!sorisaeDragMovedRef.current) {
                    openSorisaeWindow();
                }
            },
        }),
    ).current;

    return { sorisaeBtnPos, sorisaePanResponder, openSorisaeWindow };
}

export function sorisaeFabVisible(params: {
    platform: typeof Platform.OS;
    userInfo: unknown;
    showLogin: boolean;
    sorisaeWindowOpen: boolean;
    sorisaeFabEnabled: boolean;
}): boolean {
    return params.platform !== 'web'
        && !!params.userInfo
        && !params.showLogin
        && !params.sorisaeWindowOpen
        && params.sorisaeFabEnabled;
}
