import React from 'react';
import { ActivityIndicator, Pressable, Text, TextInput, View } from 'react-native';
import { BidirectionalLanguagePairBadge } from '../i18n/BidirectionalLanguagePairBadge';
import { getDisplayUiText } from '../i18n/displayLanguage';
import { getFeatureUiText } from '../i18n/featureUiCatalog';
import type { LangCode } from '../language/languageCatalog';
import { IS_WEB } from '../../app/appConstants';
import { styles } from '../../../App.styles';

type HomeWorkspaceSectionProps = {
    visible: boolean;
    fromLang: LangCode;
    toLang: LangCode;
    homeFromFlag: string;
    currentFromLabel: string;
    homeToFlag: string;
    currentToLabel: string;
    autoVoiceModeEnabled: boolean;
    homeToolsExpanded: boolean;
    gpsLangLoading: boolean;
    gpsStatus: string;
    inputText: string;
    resultText: string;
    ocrLoading: boolean;
    ocrImageName: string;
    ocrError: string;
    ocrExtractedText: string;
    ocrTranslatedText: string;
    offline: boolean;
    onOpenFaceScreen: () => void;
    onToggleFaceConversation: () => void;
    onToggleHomeTools: () => void;
    onPressVoip: () => void;
    onPressChat: () => void;
    onChangeInputText: (value: string) => void;
    onSpeak: (text: string, language: LangCode) => void;
    onPickImageOcr: () => void;
};

export function HomeWorkspaceSection({
    visible,
    fromLang,
    toLang,
    homeFromFlag,
    currentFromLabel,
    homeToFlag,
    currentToLabel,
    autoVoiceModeEnabled,
    homeToolsExpanded,
    gpsLangLoading,
    gpsStatus,
    inputText,
    resultText,
    ocrLoading,
    ocrImageName,
    ocrError,
    ocrExtractedText,
    ocrTranslatedText,
    offline,
    onOpenFaceScreen,
    onToggleFaceConversation,
    onToggleHomeTools,
    onPressVoip,
    onPressChat,
    onChangeInputText,
    onSpeak,
    onPickImageOcr,
}: HomeWorkspaceSectionProps) {
    if (!visible) {
        return null;
    }

    const displayUiText = getDisplayUiText();
    const hasGpsStatus = Boolean(gpsStatus);

    return (
        <>
            <View style={styles.homeGreetingWrap}>
                <Text wlLocalized style={styles.homeGreeting}>{getFeatureUiText('home.greeting')}</Text>
                <BidirectionalLanguagePairBadge fromLang={fromLang} toLang={toLang} />
            </View>

            <Pressable
                style={styles.faceHeroCard}
                onPress={onOpenFaceScreen}
                accessibilityRole="button"
                accessibilityLabel="worldlinco-home-face-hero"
                testID="worldlinco-home-face-hero"
            >
                <Text wlLocalized style={styles.faceHeroTitle}>{getFeatureUiText('home.faceTitle')}</Text>
                <View style={styles.faceHeroFlagRow}>
                    <View style={styles.faceHeroLangCol}>
                        <Text style={styles.faceHeroFlag}>{homeFromFlag}</Text>
                        <Text style={styles.faceHeroLangLabel}>{currentFromLabel}</Text>
                    </View>
                    <Text style={styles.faceHeroSwap}>⇄</Text>
                    <View style={styles.faceHeroLangCol}>
                        <Text style={styles.faceHeroFlag}>{homeToFlag}</Text>
                        <Text style={styles.faceHeroLangLabel}>{currentToLabel}</Text>
                    </View>
                </View>
                <View style={[styles.faceHeroMic, autoVoiceModeEnabled && styles.faceHeroMicActive]}>
                    <Text style={styles.faceHeroMicIcon}>🎙️</Text>
                </View>
                <Text wlLocalized style={styles.faceHeroCta}>
                    {autoVoiceModeEnabled ? getFeatureUiText('home.faceCtaOn') : getFeatureUiText('home.faceCtaOff')}
                </Text>
            </Pressable>

            <View style={styles.homeQuickRow}>
                <Pressable
                    style={styles.homeQuickBtn}
                    onPress={onPressVoip}
                    accessibilityRole="button"
                    accessibilityLabel="worldlinco-home-quick-voip"
                    testID="worldlinco-home-quick-voip"
                >
                    <Text style={styles.homeQuickIcon}>📞</Text>
                    <View style={{ flex: 1 }}>
                        <Text wlLocalized style={styles.homeQuickTitle}>{getFeatureUiText('home.quickVoip')}</Text>
                    </View>
                </Pressable>
                <Pressable
                    style={styles.homeQuickBtn}
                    onPress={onPressChat}
                    accessibilityRole="button"
                    accessibilityLabel="worldlinco-home-quick-chat"
                    testID="worldlinco-home-quick-chat"
                >
                    <Text style={styles.homeQuickIcon}>💬</Text>
                    <View style={{ flex: 1 }}>
                        <Text wlLocalized style={styles.homeQuickTitle}>{getFeatureUiText('home.quickChat')}</Text>
                    </View>
                </Pressable>
            </View>

            <Pressable
                style={styles.homeFavRow}
                onPress={onToggleHomeTools}
                accessibilityRole="button"
                accessibilityLabel="worldlinco-home-tools-toggle"
                testID="worldlinco-home-tools-toggle"
            >
                <Text style={styles.homeFavIcon}>⭐</Text>
                <View style={{ flex: 1 }}>
                    <Text wlLocalized style={styles.homeFavTitle}>{getFeatureUiText('home.toolsTitle')}</Text>
                </View>
                <Text style={styles.homeFavChevron}>{homeToolsExpanded ? '∧' : '〉'}</Text>
            </Pressable>

            {homeToolsExpanded ? (
                <>
                    <View style={styles.translationHub}>
                        {!IS_WEB ? (
                            <Pressable
                                style={[styles.faceConversationToggleBtn, autoVoiceModeEnabled && styles.faceConversationToggleBtnActive]}
                                onPress={onToggleFaceConversation}
                                accessibilityRole="button"
                                accessibilityLabel="worldlinco-face-conversation-toggle"
                                testID="worldlinco-face-conversation-toggle"
                            >
                                <Text style={[styles.faceConversationToggleText, autoVoiceModeEnabled && styles.faceConversationToggleTextActive]}>
                                    {autoVoiceModeEnabled
                                        ? (displayUiText.faceConversationOn ?? '🎙️ 대화 통역 ON')
                                        : (displayUiText.faceConversationOff ?? '대화 통역 OFF')}
                                </Text>
                            </Pressable>
                        ) : null}

                        <View style={styles.labelRow}>
                            <Text style={styles.label}>{displayUiText.profileLanguageLabel ?? '내 언어 (프로필)'}</Text>
                            <Text style={styles.gpsAutoBadge}>{gpsLangLoading ? '📍 위치 확인 중' : '🎙️ 자동 감지'}</Text>
                        </View>
                        {hasGpsStatus ? null : null}
                        <View style={styles.langAutoChip}>
                            <Text style={styles.langAutoChipValue}>{currentFromLabel}</Text>
                            <Text style={styles.langAutoChipHint}>{displayUiText.profileLanguageHint ?? '프로필 저장값'}</Text>
                        </View>

                        <View style={styles.inputBox}>
                            <TextInput
                                style={styles.textInput}
                                multiline
                                placeholder={displayUiText.inputPlaceholder}
                                placeholderTextColor="#8f99a8"
                                showSoftInputOnFocus
                                value={inputText}
                                onChangeText={onChangeInputText}
                            />
                            {inputText.length > 0 ? (
                                <View style={styles.inputBtnRow}>
                                    <Pressable style={styles.speakBtn} onPress={() => onSpeak(inputText, fromLang)}>
                                        <Text style={styles.speakIcon}>🔊</Text>
                                    </Pressable>
                                </View>
                            ) : null}
                        </View>

                        {!IS_WEB && !autoVoiceModeEnabled ? (
                            <View style={styles.autoVoiceModeWrap}>
                                <Text style={styles.autoVoiceModeStatus}>{displayUiText.manualVoiceOnlyNotice}</Text>
                            </View>
                        ) : null}
                    </View>

                    <View>
                        <View style={[styles.inputBox, styles.resultBox]}>
                            <Text style={resultText ? styles.resultText : styles.resultPlaceholder}>
                                {resultText || displayUiText.resultPlaceholder}
                            </Text>
                            {resultText.length > 0 && (
                                <Pressable style={styles.speakBtn} onPress={() => onSpeak(resultText, toLang)}>
                                    <Text style={styles.speakIcon}>🔊</Text>
                                </Pressable>
                            )}
                        </View>
                        <View style={styles.ocrCard}>
                            <Text style={styles.ocrTitle}>{displayUiText.ocrTitle}</Text>
                            <Pressable
                                style={[styles.inlineActionBtn, ocrLoading && styles.inlineGhostBtnDisabled]}
                                onPress={onPickImageOcr}
                                disabled={ocrLoading}
                            >
                                {ocrLoading ? <ActivityIndicator color="#79c0ff" size="small" /> : <Text style={styles.inlineActionBtnText}>{displayUiText.ocrPickImage}</Text>}
                            </Pressable>
                            {ocrImageName ? (
                                <View style={styles.mediaMetaCard}>
                                    <View style={styles.mediaThumbBox}>
                                        <Text style={styles.mediaThumbEmoji}>🖼️</Text>
                                        <Text style={styles.mediaThumbCaption}>IMG</Text>
                                    </View>
                                    <View style={styles.mediaMetaBody}>
                                        <Text style={styles.mediaMetaTitle}>{ocrImageName}</Text>
                                        <View style={styles.mediaBadgeRow}>
                                            <View style={styles.mediaBadge}><Text style={styles.mediaBadgeText}>OCR</Text></View>
                                        </View>
                                        <Text style={styles.songModeMetaText}>{(displayUiText.ocrSelectedFile ?? '선택 파일: {file}').replace('{file}', ocrImageName)}</Text>
                                    </View>
                                </View>
                            ) : null}
                            {ocrError ? <Text style={styles.errorText}>{ocrError}</Text> : null}
                            {ocrExtractedText ? (
                                <View style={styles.ocrPreviewBox}>
                                    <Text style={styles.successTitle}>{displayUiText.ocrExtractedTitle}</Text>
                                    <Text style={styles.successText}>{ocrExtractedText}</Text>
                                </View>
                            ) : null}
                            {ocrTranslatedText ? (
                                <View style={styles.ocrPreviewBox}>
                                    <Text style={styles.successTitle}>{displayUiText.ocrTranslatedTitle}</Text>
                                    <Text style={styles.successText}>{ocrTranslatedText}</Text>
                                </View>
                            ) : null}
                        </View>

                        {offline && (
                            <View style={styles.offlineBanner}>
                                <Text style={styles.offlineText}>{displayUiText.offlineMsg}</Text>
                            </View>
                        )}
                    </View>
                </>
            ) : null}
        </>
    );
}