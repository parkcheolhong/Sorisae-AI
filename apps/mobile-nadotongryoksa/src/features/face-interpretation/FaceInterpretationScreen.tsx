import React from 'react';
import {
    ImageBackground,
    Modal,
    Pressable,
    Text,
    View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

type FeatureUiTextGetter = (key: string, vars?: Record<string, string | number>) => string;

type FaceInterpretationScreenProps = {
    visible: boolean;
    skyBg: any;
    styles: any;
    insetsBottom: number;
    currentFromLabel: string;
    currentToLabel: string;
    homeToFlag: string;
    peerLangManual: boolean;
    resultText: string;
    inputText: string;
    autoVoiceModeEnabled: boolean;
    getFeatureUiText: FeatureUiTextGetter;
    peerLanguageHintText?: string;
    captureBlockMessage?: string | null;
    onOpenPeerLangPicker: () => void;
    onToggleFaceConversation: () => void;
    onRequestClose: () => void;
    onOpenChat: () => void;
    onOpenPhraseBook: () => void;
    onOpenSettings: () => void;
};

export function FaceInterpretationScreen(props: FaceInterpretationScreenProps): React.JSX.Element {
    return (
        <Modal
            visible={props.visible}
            animationType="slide"
            statusBarTranslucent
            onRequestClose={props.onRequestClose}
        >
            <ImageBackground source={props.skyBg} resizeMode="cover" style={props.styles.skyBg}>
                <SafeAreaView style={props.styles.faceScreenRoot} edges={['top', 'left', 'right']}>
                    <View style={props.styles.faceScreenHeader}>
                        <Text style={props.styles.faceScreenLogo}>🎙️ WorldLinco</Text>
                        <Pressable
                            style={props.styles.faceScreenLangPill}
                            onPress={props.onOpenPeerLangPicker}
                            accessibilityRole="button"
                            accessibilityLabel="worldlinco-face-screen-lang"
                            testID="worldlinco-face-screen-lang"
                        >
                            <Text style={props.styles.faceScreenLangPillText}>{props.currentFromLabel} ⇄ {props.currentToLabel}</Text>
                        </Pressable>
                        <Pressable
                            onPress={props.onRequestClose}
                            style={props.styles.faceScreenClose}
                            accessibilityRole="button"
                            accessibilityLabel="worldlinco-face-screen-close"
                            testID="worldlinco-face-screen-close"
                        >
                            <Text style={props.styles.faceScreenCloseText}>✕</Text>
                        </Pressable>
                    </View>

                    <View style={props.styles.faceScreenBody}>
                        <View style={props.styles.facePeerHalf}>
                            <View style={props.styles.faceRotated}>
                                <Pressable
                                    onPress={props.onOpenPeerLangPicker}
                                    accessibilityRole="button"
                                    accessibilityLabel="worldlinco-face-peer-lang"
                                    testID="worldlinco-face-peer-lang"
                                >
                                    <Text style={props.styles.facePeerLangLabel}>{props.homeToFlag} {props.currentToLabel} ▾</Text>
                                    <Text style={props.styles.langAutoChipHint}>
                                        {props.peerLangManual
                                            ? '수동 선택 · GPS 자동 변경 안 함'
                                            : (props.peerLanguageHintText ?? 'GPS 우선 · 필요 시 수동')}
                                    </Text>
                                </Pressable>
                                <Text wlLocalized style={props.styles.facePeerText}>
                                    {props.resultText || props.getFeatureUiText('face.peerPlaceholder')}
                                </Text>
                            </View>
                        </View>

                        <View style={props.styles.faceMeHalf}>
                            <View style={props.styles.faceTapHint}>
                                <Text wlLocalized style={props.styles.faceTapHintText}>
                                    {props.autoVoiceModeEnabled ? props.getFeatureUiText('face.tapListening') : props.getFeatureUiText('face.tapToSpeak')}
                                </Text>
                            </View>
                            <Text wlLocalized style={props.styles.faceMeText}>
                                {props.inputText || props.getFeatureUiText('face.mePlaceholder')}
                            </Text>
                            <Text style={props.styles.faceMeLangLabel}>{props.currentFromLabel}</Text>
                        </View>

                        <View style={props.styles.faceMicWrap} pointerEvents="box-none">
                            <Pressable
                                onPress={props.onToggleFaceConversation}
                                style={[props.styles.faceMicBtn, props.autoVoiceModeEnabled && props.styles.faceMicBtnActive]}
                                accessibilityRole="button"
                                accessibilityLabel="worldlinco-face-screen-mic"
                                testID="worldlinco-face-screen-mic"
                            >
                                <Text style={props.styles.faceMicIconBig}>🎙️</Text>
                            </Pressable>
                            {props.captureBlockMessage ? (
                                <Text style={props.styles.faceVadHintText}>{props.captureBlockMessage}</Text>
                            ) : null}
                        </View>
                    </View>

                    <View style={[props.styles.faceTabBar, { paddingBottom: 8 + props.insetsBottom }]}>
                        <View style={props.styles.faceTabItem}>
                            <Text style={props.styles.faceTabIcon}>🧑‍🤝‍🧑</Text>
                            <Text style={props.styles.faceTabLabelActive}>{props.getFeatureUiText('nav.tabFaceInterpret')}</Text>
                        </View>
                        <Pressable style={props.styles.faceTabItem} onPress={props.onOpenChat}>
                            <Text style={props.styles.faceTabIcon}>💬</Text>
                            <Text style={props.styles.faceTabLabel}>{props.getFeatureUiText('nav.tabChatMode')}</Text>
                        </Pressable>
                        <Pressable style={props.styles.faceTabItem} onPress={props.onOpenPhraseBook}>
                            <Text style={props.styles.faceTabIcon}>📖</Text>
                            <Text style={props.styles.faceTabLabel}>{props.getFeatureUiText('nav.tabPhraseBook')}</Text>
                        </Pressable>
                        <Pressable style={props.styles.faceTabItem} onPress={props.onOpenSettings}>
                            <Text style={props.styles.faceTabIcon}>⚙️</Text>
                            <Text style={props.styles.faceTabLabel}>{props.getFeatureUiText('nav.tabSettings')}</Text>
                        </Pressable>
                    </View>
                </SafeAreaView>
            </ImageBackground>
        </Modal>
    );
}
