import React from 'react';

import {

    ImageBackground,

    ImageSourcePropType,

    Linking,

    Modal,

    Pressable,

    ScrollView,

    Text,

    View,

} from 'react-native';

import { SafeAreaView } from 'react-native-safe-area-context';



import { styles } from '../../../App.styles';

import { SorisaeVoiceWaveOrb } from './SorisaeVoiceWaveOrb';

import type { SorisaeQaEntry } from './types';



type LangLabelFn = (code: string) => string;



type SorisaeCompanionWindowProps = {

    visible: boolean;

    skyBackground: ImageSourcePropType;

    aiDisplayName: string;

    showStatus: boolean;

    statusText: string;

    qaLog: SorisaeQaEntry[];

    /** 창 안 음성 대화 활성(자동 듣기 ON). gpsStatus와 분리해 UI 깜박임 방지. */

    voiceListenActive: boolean;

    /** TTS 발화 중 — 파장만 일시 정지. */

    sorisaeSpeaking: boolean;

    getLangLabel: LangLabelFn;

    onClose: () => void;

    onClearLog: () => void;

    onToggleConversation: () => void;

};



/** 소리새 AI 전용 창 — 대면 통역과 완전 분리된 Q&A UI. */

export function SorisaeCompanionWindow({

    visible,

    skyBackground,

    aiDisplayName,

    showStatus,

    statusText,

    qaLog,

    voiceListenActive,

    sorisaeSpeaking,

    getLangLabel,

    onClose,

    onClearLog,

    onToggleConversation,

}: SorisaeCompanionWindowProps) {

    const waveHint = sorisaeSpeaking
        ? '🐦 답변 재생 중 · 잠시 후 다시 들어요'
        : '🎙️ 음성 대기 중 · 말씀하세요';



    return (

        <Modal

            visible={visible}

            animationType="slide"

            statusBarTranslucent

            onRequestClose={onClose}

        >

            <ImageBackground source={skyBackground} resizeMode="cover" style={styles.skyBg}>

                <SafeAreaView style={styles.sorisaeWindowRoot}>

                    <View style={styles.sorisaeWindowHeader}>

                        <Text style={styles.sorisaeWindowTitle}>🐦 {aiDisplayName}</Text>

                        <Pressable

                            onPress={onClose}

                            accessibilityRole="button"

                            accessibilityLabel="worldlinco-sorisae-window-close"

                            testID="worldlinco-sorisae-window-close"

                            style={styles.sorisaeWindowCloseBtn}

                        >

                            <Text style={styles.sorisaeWindowCloseText}>✕ 닫기</Text>

                        </Pressable>

                    </View>

                    {showStatus ? <Text style={styles.sorisaeWindowStatus}>{statusText}</Text> : null}

                    <ScrollView style={styles.sorisaeWindowScroll} contentContainerStyle={{ paddingBottom: 16 }}>

                        {qaLog.length === 0 ? (

                            <Text style={styles.sorisaeWindowEmpty}>대화 없음</Text>

                        ) : (

                            qaLog.map((qa) => (

                                <View key={qa.id} style={styles.sorisaeQaTurn}>

                                    <View style={styles.sorisaeQaQuestionRow}>

                                        <View style={styles.sorisaeQaBubbleQuestion}>

                                            <Text style={styles.sorisaeQaRoleLabel}>

                                                {`🙋 질문 · ${getLangLabel(qa.questionLang)}`}

                                            </Text>

                                            <Text style={styles.sorisaeQaQuestionText}>{qa.question}</Text>

                                        </View>

                                    </View>

                                    <View style={styles.sorisaeQaAnswerRow}>

                                        <View style={styles.sorisaeQaBubbleAnswer}>

                                            <Text style={styles.sorisaeQaRoleLabelAnswer}>

                                                {`🐦 답변 · ${getLangLabel(qa.answerLang)}`}

                                            </Text>

                                            <Text style={styles.sorisaeQaAnswerText}>{qa.answer}</Text>
                                            {qa.mapContext?.transport_schedule_options?.length ? (
                                                <View style={{ marginTop: 10, gap: 6 }}>
                                                    <Text style={styles.sorisaeQaRoleLabelAnswer}>🕒 시간표 근거</Text>
                                                    {qa.mapContext.transport_schedule_options.slice(0, 3).map((option, index) => (
                                                        <View key={`${qa.id}-schedule-${index}`} style={{ paddingVertical: 4 }}>
                                                            <Text style={styles.sorisaeQaAnswerText}>
                                                                {`${option.route_label || '교통편'} · ${option.origin_stop || '-'} ${option.departure_local || '--:--'} → ${option.destination_stop || '-'} ${option.arrival_local || '--:--'}`}
                                                            </Text>
                                                        </View>
                                                    ))}
                                                </View>
                                            ) : null}
                                            {qa.mapContext?.origin?.map_url || qa.mapContext?.destination?.map_url ? (
                                                <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 10 }}>
                                                    {qa.mapContext?.origin?.map_url ? (
                                                        <Pressable
                                                            onPress={() => {
                                                                const url = String(qa.mapContext?.origin?.map_url || '').trim();
                                                                if (url) {
                                                                    void Linking.openURL(url).catch(() => {});
                                                                }
                                                            }}
                                                            accessibilityRole="button"
                                                            accessibilityLabel="worldlinco-sorisae-origin-map"
                                                            style={styles.inlineGhostBtn}
                                                        >
                                                            <Text style={styles.inlineGhostBtnText}>
                                                                {`출발지 핀${qa.mapContext?.origin?.display_label ? ` · ${qa.mapContext.origin.display_label}` : qa.mapContext?.origin?.name ? ` · ${qa.mapContext.origin.name}` : ''}`}
                                                            </Text>
                                                        </Pressable>
                                                    ) : null}
                                                    {qa.mapContext?.destination?.map_url ? (
                                                        <Pressable
                                                            onPress={() => {
                                                                const url = String(qa.mapContext?.destination?.map_url || '').trim();
                                                                if (url) {
                                                                    void Linking.openURL(url).catch(() => {});
                                                                }
                                                            }}
                                                            accessibilityRole="button"
                                                            accessibilityLabel="worldlinco-sorisae-destination-map"
                                                            style={styles.inlineGhostBtn}
                                                        >
                                                            <Text style={styles.inlineGhostBtnText}>
                                                                {`목적지 핀${qa.mapContext?.destination?.display_label ? ` · ${qa.mapContext.destination.display_label}` : qa.mapContext?.destination?.name ? ` · ${qa.mapContext.destination.name}` : ''}`}
                                                            </Text>
                                                        </Pressable>
                                                    ) : null}
                                                </View>
                                            ) : null}

                                        </View>

                                    </View>

                                </View>

                            ))

                        )}

                    </ScrollView>

                    <View style={styles.sorisaeWindowFooter}>

                        {qaLog.length > 0 ? (

                            <Pressable

                                onPress={onClearLog}

                                accessibilityRole="button"

                                accessibilityLabel="worldlinco-sorisae-window-clear"

                                style={styles.sorisaeWindowClearBtn}

                            >

                                <Text style={styles.sorisaeWindowClearText}>대화 지우기</Text>

                            </Pressable>

                        ) : null}

                        {voiceListenActive ? (

                            <SorisaeVoiceWaveOrb

                                wavePaused={sorisaeSpeaking}

                                hintText={waveHint}

                                onPress={onToggleConversation}

                            />

                        ) : (

                            <Pressable

                                onPress={onToggleConversation}

                                accessibilityRole="button"

                                accessibilityLabel="worldlinco-sorisae-window-mic"

                                testID="worldlinco-sorisae-window-mic"

                                style={styles.sorisaeWindowMicBtn}

                            >

                                <Text style={styles.sorisaeWindowMicText}>{`🎙️ ${aiDisplayName} 대화 시작`}</Text>

                            </Pressable>

                        )}

                    </View>

                </SafeAreaView>

            </ImageBackground>

        </Modal>

    );

}


