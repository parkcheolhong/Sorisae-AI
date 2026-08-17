// App.tsx 에서 분리한 노래 모드 섹션(B2 순서 2, 패스스루 — 상태는 App 소유).

import React from 'react';

import type { Dispatch, SetStateAction } from 'react';

import { View, Text, Pressable, ScrollView, TextInput } from 'react-native';

import { styles } from '../../../App.styles';

import { VOICE_LICENSE_OPTIONS, VOICE_OUTPUT_SCOPE_OPTIONS } from '../../app/appConstants';

import { resolveSongFileTargetLang, normalizeSongFileLang } from './songLang';

import { formatSongFileTime } from './songText';

import type { LangCode } from '../language/languageCatalog';

import type { SectionRailKey } from '../navigation/sectionRegistry';

import type {

    SongSubtitleEntry,

    SongFileJobStatus,

    SongFileTimelineSegment,

    VoiceConsentResponse,

    VoiceProfileResponse,

    VoicePreviewResponse,

    VoiceLicenseMode,

    VoiceOutputScope,

} from '../../app/appTypes';



export type SongModeSectionProps = {

    /** 설정 → 노래 설명서 상단에 임베드할 때 true (하단 레일 미사용) */
    embeddedInManual?: boolean;

    railSectionOffsetRef?: React.MutableRefObject<Record<SectionRailKey, number>>;

    activeRailSection?: SectionRailKey | null;

    scrollToRailSection?: (sectionKey: SectionRailKey, animated?: boolean) => void;

    songModeEnabled: boolean;

    setSongModeEnabled: Dispatch<SetStateAction<boolean>>;

    hasSongPass: boolean;

    handlePickSongFile: () => void;

    songFileLoading: boolean;

    setSongSubtitles: Dispatch<SetStateAction<SongSubtitleEntry[]>>;

    setSongFileSegments: Dispatch<SetStateAction<SongFileTimelineSegment[]>>;

    setSongFileJob: Dispatch<SetStateAction<SongFileJobStatus | null>>;

    setSongFileExportPreview: Dispatch<SetStateAction<string>>;

    getLangLabel: (code: LangCode) => string;

    toLang: LangCode;

    fromLang: LangCode;

    songModeStatus: string;

    songFileJob: SongFileJobStatus | null;

    songFileName: string;

    songFileSegments: SongFileTimelineSegment[];

    handleToggleSongFilePlayback: () => void;

    songFilePlaying: boolean;

    chatShareLoading: boolean;

    handleShareSongToChat: () => void;

    songFilePlaybackMs: number;

    activeSongFileSegment: SongFileTimelineSegment | null;

    voiceConsent: VoiceConsentResponse | null;

    voiceProfileLoading: boolean;

    handleToggleVoiceSampleRecording: () => void;

    voiceProfileRecording: boolean;

    handlePickVoiceSample: () => void;

    voiceProfile: VoiceProfileResponse | null;

    handleDeleteVoiceProfile: () => void;

    voiceLicenseMode: VoiceLicenseMode;

    setVoiceLicenseMode: Dispatch<SetStateAction<VoiceLicenseMode>>;

    voiceOutputScope: VoiceOutputScope;

    setVoiceOutputScope: Dispatch<SetStateAction<VoiceOutputScope>>;

    voiceRightsAcknowledged: boolean;

    setVoiceRightsAcknowledged: Dispatch<SetStateAction<boolean>>;

    handleCreateVoicePreview: () => void;

    voicePreview: VoicePreviewResponse | null;

    handleSpeakVoicePreview: () => void;

    voiceProfileStatus: string;

    handleExportSongFileTimeline: (format: 'srt' | 'vtt' | 'lrc' | 'json') => void;

    handleSongFileSegmentTextChange: (segmentId: string, translated: string) => void;

    handleSaveSongFileSegment: (segment: SongFileTimelineSegment) => void;

    songFileExportPreview: string;

    songSubtitles: SongSubtitleEntry[];

};



export default function SongModeSection({

    embeddedInManual = false,

    railSectionOffsetRef,

    activeRailSection,

    scrollToRailSection,

    songModeEnabled,

    setSongModeEnabled,

    hasSongPass,

    handlePickSongFile,

    songFileLoading,

    setSongSubtitles,

    setSongFileSegments,

    setSongFileJob,

    setSongFileExportPreview,

    getLangLabel,

    toLang,

    fromLang,

    songModeStatus,

    songFileJob,

    songFileName,

    songFileSegments,

    handleToggleSongFilePlayback,

    songFilePlaying,

    chatShareLoading,

    handleShareSongToChat,

    songFilePlaybackMs,

    activeSongFileSegment,

    voiceConsent,

    voiceProfileLoading,

    handleToggleVoiceSampleRecording,

    voiceProfileRecording,

    handlePickVoiceSample,

    voiceProfile,

    handleDeleteVoiceProfile,

    voiceLicenseMode,

    setVoiceLicenseMode,

    voiceOutputScope,

    setVoiceOutputScope,

    voiceRightsAcknowledged,

    setVoiceRightsAcknowledged,

    handleCreateVoicePreview,

    voicePreview,

    handleSpeakVoicePreview,

    voiceProfileStatus,

    handleExportSongFileTimeline,

    handleSongFileSegmentTextChange,

    handleSaveSongFileSegment,

    songFileExportPreview,

    songSubtitles,

}: SongModeSectionProps) {

    const voiceSettingsPanel = (
                        <View style={styles.voicePreviewPanel}>
                            <Text style={styles.songFileTimelineTitle}>🎵 노래 설정</Text>
                            <Text style={styles.songSubtitleMeta}>필요한 분만 켜서 사용하세요. 자세한 설명은 아래 안내를 참고하세요.</Text>

                            <View style={styles.voicePreviewHeaderRow}>
                                <Text style={styles.songModeMetaText}>내 목소리 번역가사 preview</Text>
                                <Text style={styles.songSubtitleMeta}>{voiceConsent ? '동의 확인됨' : '동의 대기'}</Text>
                            </View>

                            <Text style={styles.songSubtitleMeta}>
                                기본은 개인 preview이며, 권리 확인과 정책 승인 후 공유/export 경로가 열립니다.
                            </Text>

                            <View style={styles.songModeActionRow}>
                                <Pressable style={[styles.inlineGhostBtn, voiceProfileLoading && styles.inlineGhostBtnDisabled]} onPress={handleToggleVoiceSampleRecording} disabled={voiceProfileLoading}>
                                    <Text style={styles.inlineGhostBtnText}>{voiceProfileRecording ? '샘플 녹음 종료' : '샘플 녹음'}</Text>
                                </Pressable>
                                <Pressable style={[styles.inlineGhostBtn, voiceProfileLoading && styles.inlineGhostBtnDisabled]} onPress={handlePickVoiceSample} disabled={voiceProfileLoading || voiceProfileRecording}>
                                    <Text style={styles.inlineGhostBtnText}>{voiceProfileLoading ? '처리 중' : '샘플 파일 업로드'}</Text>
                                </Pressable>
                                {voiceProfile ? (
                                    <Pressable style={styles.inlineGhostBtn} onPress={handleDeleteVoiceProfile}>
                                        <Text style={styles.inlineGhostBtnText}>프로필 삭제</Text>
                                    </Pressable>
                                ) : null}
                            </View>

                            {voiceProfile ? (
                                <Text style={styles.songModeMetaText}>
                                    프로필: {voiceProfile.profile_label} · 품질 {(voiceProfile.sample_quality_score * 100).toFixed(0)}% · {voiceProfile.encrypted ? '암호화 저장' : '저장 대기'}
                                </Text>
                            ) : null}

                            <Text style={styles.songModeMetaText}>권리 모드</Text>
                            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.railRow}>
                                {VOICE_LICENSE_OPTIONS.map((option) => (
                                    <Pressable
                                        key={`voice-license-${option.value}`}
                                        style={[styles.railBtn, voiceLicenseMode === option.value && styles.railBtnActive]}
                                        onPress={() => setVoiceLicenseMode(option.value)}
                                    >
                                        <Text style={[styles.railBtnText, voiceLicenseMode === option.value && styles.railBtnTextActive]}>{option.label}</Text>
                                    </Pressable>
                                ))}
                            </ScrollView>

                            <Text style={styles.songModeMetaText}>출력 범위</Text>
                            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.railRow}>
                                {VOICE_OUTPUT_SCOPE_OPTIONS.map((option) => (
                                    <Pressable
                                        key={`voice-scope-${option.value}`}
                                        style={[styles.railBtn, voiceOutputScope === option.value && styles.railBtnActive]}
                                        onPress={() => setVoiceOutputScope(option.value)}
                                    >
                                        <Text style={[styles.railBtnText, voiceOutputScope === option.value && styles.railBtnTextActive]}>{option.label}</Text>
                                    </Pressable>
                                ))}
                            </ScrollView>

                            <Pressable style={styles.voiceAckRow} onPress={() => setVoiceRightsAcknowledged((value) => !value)}>
                                <Text style={styles.voiceAckMark}>{voiceRightsAcknowledged ? '✓' : ''}</Text>
                                <Text style={styles.voiceAckText}>권리 보유/허가 여부와 사용자 책임 고지를 확인했습니다.</Text>
                            </Pressable>

                            <View style={styles.songModeActionRow}>
                                <Pressable style={[styles.inlineActionBtn, (!voiceProfile || !songFileJob || songFileJob.status !== 'completed' || voiceProfileLoading) && styles.inlineGhostBtnDisabled]} onPress={handleCreateVoicePreview} disabled={!voiceProfile || !songFileJob || songFileJob.status !== 'completed' || voiceProfileLoading}>
                                    <Text style={styles.inlineActionBtnText}>번역가사 preview 생성</Text>
                                </Pressable>
                                {voicePreview?.preview_text ? (
                                    <Pressable style={styles.inlineGhostBtn} onPress={handleSpeakVoicePreview}>
                                        <Text style={styles.inlineGhostBtnText}>preview 듣기</Text>
                                    </Pressable>
                                ) : null}
                            </View>

                            {voiceProfileStatus ? <Text style={styles.songModeStatusText}>{voiceProfileStatus}</Text> : null}

                            {voicePreview ? (
                                <View style={styles.voicePreviewResultBox}>
                                    <Text style={styles.songSubtitleMeta}>{voicePreview.gate_status} · {voicePreview.effective_output_scope} · {voicePreview.segment_count}개 구간</Text>
                                    <Text style={styles.songFileExportPreview}>{voicePreview.preview_text.slice(0, 900)}</Text>
                                </View>
                            ) : null}
                        </View>
    );

    const content = (
        <>
                        {embeddedInManual ? voiceSettingsPanel : null}

                        <View style={styles.actionTileGrid2}>

                            <Pressable

                                style={[styles.gridTile, songModeEnabled && styles.gridTileActive]}

                                onPress={() => setSongModeEnabled((prev) => !prev)}

                                accessibilityRole="button"

                                accessibilityLabel="노래 모드 토글"

                                testID="worldlinco-song-action-toggle"

                            >

                                <View style={[styles.gridTileIcon, { backgroundColor: '#7C5CFC' }]}><Text style={styles.gridTileEmoji}>🎵</Text></View>

                                <Text style={styles.gridTileLabel}>노래 모드 {songModeEnabled ? 'ON' : 'OFF'}</Text>

                            </Pressable>

                            <Pressable

                                style={styles.gridTile}

                                onPress={handlePickSongFile}

                                accessibilityRole="button"

                                accessibilityLabel="노래 파일 선택"

                                testID="worldlinco-song-action-file"

                            >

                                <View style={[styles.gridTileIcon, { backgroundColor: '#7C5CFC' }]}><Text style={styles.gridTileEmoji}>📂</Text></View>

                                <Text style={styles.gridTileLabel}>노래 파일 선택</Text>

                            </Pressable>

                        </View>

                        <View style={styles.songModeActionRow}>

                            <Pressable style={[styles.inlineGhostBtn, (songFileLoading || !hasSongPass) && styles.inlineGhostBtnDisabled]} onPress={handlePickSongFile} disabled={songFileLoading || !hasSongPass}>

                                <Text style={styles.inlineGhostBtnText}>{songFileLoading ? '파일 처리 중' : '노래 파일 선택'}</Text>

                            </Pressable>

                            <Pressable style={styles.inlineGhostBtn} onPress={() => {

                                setSongSubtitles([]);

                                setSongFileSegments([]);

                                setSongFileJob(null);

                                setSongFileExportPreview('');

                            }}>

                                <Text style={styles.inlineGhostBtnText}>자막 초기화</Text>

                            </Pressable>

                        </View>

                        {songModeStatus ? <Text style={styles.songModeStatusText}>{songModeStatus}</Text> : null}

                        {songFileJob ? (

                            <View style={styles.songFileJobBox}>

                                <View style={styles.mediaMetaCard}>

                                    <View style={styles.mediaThumbBox}>

                                        <Text style={styles.mediaThumbEmoji}>🎵</Text>

                                        <Text style={styles.mediaThumbCaption}>{songFileName.split('.').pop()?.slice(0, 4).toUpperCase() || 'SONG'}</Text>

                                    </View>

                                    <View style={styles.mediaMetaBody}>

                                        <Text style={styles.mediaMetaTitle}>{songFileName || '선택한 노래 파일'}</Text>

                                        <View style={styles.mediaBadgeRow}>

                                            <View style={styles.mediaBadge}><Text style={styles.mediaBadgeText}>{songFileSegments.length}구간</Text></View>

                                            <View style={styles.mediaBadge}><Text style={styles.mediaBadgeText}>{getLangLabel(fromLang)}</Text></View>

                                            <View style={styles.mediaBadge}><Text style={styles.mediaBadgeText}>{getLangLabel(resolveSongFileTargetLang(fromLang, toLang))}</Text></View>

                                        </View>

                                        <Text style={styles.songModeMetaText}>{songFileJob.stage} · {songFileJob.message}</Text>

                                    </View>

                                </View>

                                <View style={styles.songFileJobHeader}>

                                    <Text style={styles.songFileNameText}>{songFileName || '선택한 노래 파일'}</Text>

                                    <Text style={styles.songFileProgressText}>{songFileJob.progress}%</Text>

                                </View>

                                <Text style={styles.songSubtitleMeta}>{songFileJob.stage} · {songFileJob.message}</Text>

                                <View style={styles.songFileProgressTrack}>

                                    <View style={[styles.songFileProgressFill, { width: `${Math.max(4, Math.min(100, songFileJob.progress))}%` }]} />

                                </View>

                                <View style={styles.songFileControlRow}>

                                    <Pressable style={styles.inlineGhostBtn} onPress={handleToggleSongFilePlayback}>

                                        <Text style={styles.inlineGhostBtnText}>{songFilePlaying ? '일시정지' : '재생'}</Text>

                                    </Pressable>

                                    <Pressable

                                        style={[styles.inlineActionBtn, chatShareLoading && styles.inlineGhostBtnDisabled]}

                                        onPress={() => { void handleShareSongToChat(); }}

                                        disabled={chatShareLoading}

                                    >

                                        <Text style={styles.inlineActionBtnText}>{chatShareLoading ? '공유 중...' : '💬 노래 번역을 채팅에 보내기'}</Text>

                                    </Pressable>

                                    <Text style={styles.songSubtitleMeta}>현재 {formatSongFileTime(songFilePlaybackMs)} {activeSongFileSegment ? `· ${activeSongFileSegment.index}번 자막` : ''}</Text>

                                </View>

                            </View>

                        ) : null}

                        {songFileSegments.length > 0 ? (

                            <View style={styles.songFileTimelineWrap}>

                                <Text style={styles.songFileTimelineTitle}>파일 번역 자막 편집</Text>

                                <View style={styles.songFileExportRow}>

                                    {(['srt', 'vtt', 'lrc', 'json'] as const).map((format) => (

                                        <Pressable key={format} style={styles.songFileExportBtn} onPress={() => handleExportSongFileTimeline(format)}>

                                            <Text style={styles.songFileExportText}>{format.toUpperCase()}</Text>

                                        </Pressable>

                                    ))}

                                </View>

                                {songFileSegments.map((segment) => {

                                    const active = activeSongFileSegment?.id === segment.id;

                                    const sourceLang = normalizeSongFileLang(segment.source_language, fromLang);

                                    const targetLang = normalizeSongFileLang(segment.target_language, toLang);

                                    return (

                                        <View key={segment.id} style={[styles.songFileSegmentItem, active && styles.songFileSegmentItemActive]}>

                                            <Text style={styles.songSubtitleMeta}>{formatSongFileTime(segment.start_ms)} - {formatSongFileTime(segment.end_ms)} · {getLangLabel(sourceLang)} → {getLangLabel(targetLang)} · {(segment.confidence * 100).toFixed(0)}%</Text>

                                            <Text style={styles.songSubtitleOriginal}>{segment.original}</Text>

                                            <TextInput

                                                style={styles.songFileSegmentInput}

                                                value={segment.translated}

                                                multiline

                                                onChangeText={(text) => handleSongFileSegmentTextChange(segment.id, text)}

                                            />

                                            <View style={styles.songFileSegmentFooter}>

                                                <Text style={styles.songSubtitleMeta}>{segment.edited_by_user ? '사용자 편집됨' : segment.detected_by}</Text>

                                                <Pressable style={styles.songFileSaveBtn} onPress={() => handleSaveSongFileSegment(segment)}>

                                                    <Text style={styles.songFileSaveText}>저장</Text>

                                                </Pressable>

                                            </View>

                                        </View>

                                    );

                                })}

                                {songFileExportPreview ? (

                                    <Text style={styles.songFileExportPreview}>{songFileExportPreview}</Text>

                                ) : null}

                            </View>

                        ) : null}

                        <View style={styles.songSubtitleWrap}>

                            {songSubtitles.length === 0 ? (

                                <Text style={styles.songSubtitlePlaceholder}>노래 모드를 켠 뒤 마이크 버튼으로 가사 한 구간을 캡처하거나 노래 파일을 선택하면 번역 자막이 여기에 누적됩니다.</Text>

                            ) : (

                                songSubtitles.map((entry) => (

                                    <View key={entry.id} style={styles.songSubtitleItem}>

                                        <Text style={styles.songSubtitleOriginal}>

                                            {entry.original}

                                            {entry.repeatCount > 1 ? `  x${entry.repeatCount}` : ''}

                                        </Text>

                                        <Text style={styles.songSubtitleTranslated}>{entry.translated}</Text>

                                        <Text style={styles.songSubtitleMeta}>{getLangLabel(entry.source)} → {getLangLabel(entry.target)} · {entry.detectedBy}</Text>

                                    </View>

                                ))

                            )}

                        </View>
        </>
    );

    if (embeddedInManual) {
        return <View style={{ marginBottom: 12 }}>{content}</View>;
    }

    return (
        <View
            onLayout={(event) => {
                if (railSectionOffsetRef && scrollToRailSection) {
                    railSectionOffsetRef.current['tourism-promo'] = event.nativeEvent.layout.y;
                    if (activeRailSection === 'tourism-promo') {
                        scrollToRailSection('tourism-promo');
                    }
                }
            }}
            style={[styles.sectionCard, activeRailSection === 'tourism-promo' && styles.sectionCardActive]}
        >
            {content}
        </View>
    );
}

