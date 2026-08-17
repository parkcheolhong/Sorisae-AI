import React, { useCallback, useMemo, useRef, useState } from 'react';
import {
    ActivityIndicator,
    FlatList,
    Modal,
    Pressable,
    StyleSheet,
    Text,
    View,
} from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import type { ComponentRef } from 'react';

import { translateImage, type ImageTranslateResult } from '../../api/translate';

export type CameraTranslateOverlayProps = {
    visible: boolean;
    fromLang: string;
    toLang: string;
    fromLabel: string;
    toLabel: string;
    regionHint?: string;
    onClose: () => void;
    onSwapLanguages: () => void;
    onTranslated: (result: ImageTranslateResult) => void;
};

export function CameraTranslateOverlay({
    visible,
    fromLang,
    toLang,
    fromLabel,
    toLabel,
    regionHint,
    onClose,
    onSwapLanguages,
    onTranslated,
}: CameraTranslateOverlayProps) {
    const cameraRef = useRef<ComponentRef<typeof CameraView>>(null);
    const [permission, requestPermission] = useCameraPermissions();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [preview, setPreview] = useState<{ original: string; translated: string } | null>(null);

    const resultRows = useMemo(() => {
        if (!preview) {
            return [] as Array<{ key: string; kind: 'label' | 'text'; value: string }>;
        }
        return [
            { key: 'original-label', kind: 'label' as const, value: '원문' },
            { key: 'original-text', kind: 'text' as const, value: preview.original },
            { key: 'translated-label', kind: 'label' as const, value: '번역' },
            { key: 'translated-text', kind: 'text' as const, value: preview.translated },
        ];
    }, [preview]);

    const renderResultRow = useCallback(({ item }: {
        item: { key: string; kind: 'label' | 'text'; value: string };
    }) => {
        if (item.kind === 'label') {
            return <Text style={styles.resultLabel}>{item.value}</Text>;
        }
        if (item.key === 'translated-text') {
            return <Text style={styles.resultTranslated}>{item.value}</Text>;
        }
        return <Text style={styles.resultOriginal}>{item.value}</Text>;
    }, []);

    const resetPreview = useCallback(() => {
        setPreview(null);
        setError('');
    }, []);

    const handleClose = useCallback(() => {
        if (loading) {
            return;
        }
        resetPreview();
        onClose();
    }, [loading, onClose, resetPreview]);

    const handleCapture = useCallback(async () => {
        if (loading || !cameraRef.current) {
            return;
        }
        setError('');
        setPreview(null);
        setLoading(true);
        try {
            const photo = await cameraRef.current.takePictureAsync({
                quality: 0.88,
                skipProcessing: false,
                exif: false,
            });
            if (!photo?.uri) {
                throw new Error('사진 촬영에 실패했습니다.');
            }
            const result = await translateImage(
                {
                    uri: photo.uri,
                    name: `camera-hd-${Date.now()}.jpg`,
                    mimeType: 'image/jpeg',
                },
                fromLang,
                toLang,
                regionHint,
                { highDensity: true },
            );
            if (!result.original_text?.trim()) {
                setError('글자를 찾지 못했습니다. 더 가까이·선명하게 다시 촬영해 주세요.');
                return;
            }
            setPreview({
                original: result.original_text,
                translated: result.translated,
            });
            onTranslated(result);
        } catch (captureError: unknown) {
            const message = captureError instanceof Error
                ? captureError.message
                : '카메라 번역에 실패했습니다.';
            setError(message);
        } finally {
            setLoading(false);
        }
    }, [fromLang, loading, onTranslated, regionHint, toLang]);

    if (!visible) {
        return null;
    }

    if (!permission) {
        return (
            <Modal visible animationType="slide" onRequestClose={handleClose}>
                <View style={styles.centered}>
                    <ActivityIndicator color="#58c9ff" />
                </View>
            </Modal>
        );
    }

    if (!permission.granted) {
        return (
            <Modal visible animationType="slide" onRequestClose={handleClose}>
                <View style={styles.centered}>
                    <Text style={styles.permissionTitle}>카메라 권한 필요</Text>
                    <Text style={styles.permissionBody}>메뉴판·표지판 고밀도 OCR 번역을 위해 카메라 접근을 허용해 주세요.</Text>
                    <Pressable style={styles.primaryBtn} onPress={() => { void requestPermission(); }}>
                        <Text style={styles.primaryBtnText}>권한 허용</Text>
                    </Pressable>
                    <Pressable style={styles.ghostBtn} onPress={handleClose}>
                        <Text style={styles.ghostBtnText}>닫기</Text>
                    </Pressable>
                </View>
            </Modal>
        );
    }

    return (
        <Modal visible animationType="slide" onRequestClose={handleClose}>
            <View style={styles.root}>
                <CameraView ref={cameraRef} style={styles.camera} facing="back">
                    <View style={styles.topBar}>
                        <Pressable style={styles.iconBtn} onPress={handleClose} disabled={loading}>
                            <Text style={styles.iconBtnText}>✕</Text>
                        </Pressable>
                        <Text style={styles.title}>고밀도 즉시 번역</Text>
                        <View style={styles.iconBtnPlaceholder} />
                    </View>

                    <View style={styles.langRow}>
                        <Text style={styles.langChip}>{fromLabel}</Text>
                        <Pressable onPress={onSwapLanguages} disabled={loading} style={styles.swapBtn}>
                            <Text style={styles.swapText}>⇄</Text>
                        </Pressable>
                        <Text style={styles.langChip}>{toLabel}</Text>
                    </View>

                    {preview ? (
                        <View style={styles.resultPanel}>
                            <FlatList
                                style={styles.resultScroll}
                                data={resultRows}
                                renderItem={renderResultRow}
                                keyExtractor={(item) => item.key}
                                initialNumToRender={4}
                                maxToRenderPerBatch={4}
                                windowSize={3}
                                removeClippedSubviews
                            />
                            <Pressable style={styles.secondaryBtn} onPress={resetPreview} disabled={loading}>
                                <Text style={styles.secondaryBtnText}>다시 촬영</Text>
                            </Pressable>
                        </View>
                    ) : null}

                    {error ? (
                        <View style={styles.errorBox}>
                            <Text style={styles.errorText}>{error}</Text>
                        </View>
                    ) : null}

                    <View style={styles.bottomBar}>
                        <Pressable
                            style={[styles.shutterOuter, loading && styles.shutterDisabled]}
                            onPress={() => { void handleCapture(); }}
                            disabled={loading}
                            accessibilityRole="button"
                            accessibilityLabel="camera-translate-shutter"
                            testID="camera-translate-shutter"
                        >
                            {loading ? (
                                <ActivityIndicator color="#0b0f16" size="large" />
                            ) : (
                                <View style={styles.shutterInner} />
                            )}
                        </Pressable>
                        <Text style={styles.bottomHint}>
                            {loading ? '고밀도 OCR · 번역 중…' : '탭하여 촬영 · 즉시 번역'}
                        </Text>
                    </View>
                </CameraView>
            </View>
        </Modal>
    );
}

const styles = StyleSheet.create({
    root: {
        flex: 1,
        backgroundColor: '#000',
    },
    camera: {
        flex: 1,
        justifyContent: 'space-between',
    },
    centered: {
        flex: 1,
        backgroundColor: '#0b0f16',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
        gap: 16,
    },
    permissionTitle: {
        color: '#fff',
        fontSize: 20,
        fontWeight: '700',
    },
    permissionBody: {
        color: '#b8c4d9',
        fontSize: 14,
        textAlign: 'center',
        lineHeight: 22,
    },
    primaryBtn: {
        backgroundColor: '#58c9ff',
        paddingHorizontal: 24,
        paddingVertical: 12,
        borderRadius: 12,
    },
    primaryBtnText: {
        color: '#0b0f16',
        fontWeight: '700',
        fontSize: 16,
    },
    ghostBtn: {
        padding: 12,
    },
    ghostBtnText: {
        color: '#8ea0bd',
        fontSize: 15,
    },
    topBar: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingTop: 52,
        paddingHorizontal: 16,
    },
    title: {
        color: '#fff',
        fontSize: 16,
        fontWeight: '700',
    },
    iconBtn: {
        width: 40,
        height: 40,
        borderRadius: 20,
        backgroundColor: 'rgba(0,0,0,0.45)',
        alignItems: 'center',
        justifyContent: 'center',
    },
    iconBtnPlaceholder: {
        width: 40,
        height: 40,
    },
    iconBtnText: {
        color: '#fff',
        fontSize: 18,
        fontWeight: '700',
    },
    langRow: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 12,
        marginTop: 8,
    },
    langChip: {
        color: '#fff',
        backgroundColor: 'rgba(0,0,0,0.55)',
        paddingHorizontal: 14,
        paddingVertical: 8,
        borderRadius: 999,
        fontSize: 14,
        fontWeight: '600',
        overflow: 'hidden',
    },
    swapBtn: {
        width: 36,
        height: 36,
        borderRadius: 18,
        backgroundColor: 'rgba(88,201,255,0.25)',
        alignItems: 'center',
        justifyContent: 'center',
    },
    swapText: {
        color: '#58c9ff',
        fontSize: 16,
        fontWeight: '700',
    },
    guideBox: {
        alignSelf: 'center',
        marginTop: 12,
        paddingHorizontal: 16,
        paddingVertical: 10,
        borderRadius: 12,
        backgroundColor: 'rgba(0,0,0,0.45)',
        maxWidth: '88%',
    },
    guideText: {
        color: '#dce6f5',
        fontSize: 13,
        textAlign: 'center',
        lineHeight: 20,
    },
    resultPanel: {
        marginHorizontal: 16,
        marginTop: 12,
        maxHeight: 220,
        backgroundColor: 'rgba(11,15,22,0.88)',
        borderRadius: 16,
        padding: 14,
        borderWidth: 1,
        borderColor: 'rgba(88,201,255,0.35)',
    },
    resultScroll: {
        maxHeight: 160,
    },
    resultLabel: {
        color: '#8ea0bd',
        fontSize: 12,
        marginBottom: 4,
        marginTop: 6,
    },
    resultOriginal: {
        color: '#fff',
        fontSize: 14,
        lineHeight: 21,
    },
    resultTranslated: {
        color: '#58c9ff',
        fontSize: 15,
        fontWeight: '600',
        lineHeight: 22,
        marginBottom: 8,
    },
    secondaryBtn: {
        alignSelf: 'flex-end',
        paddingVertical: 6,
        paddingHorizontal: 10,
    },
    secondaryBtnText: {
        color: '#58c9ff',
        fontSize: 13,
        fontWeight: '600',
    },
    errorBox: {
        marginHorizontal: 16,
        marginTop: 8,
        padding: 12,
        borderRadius: 12,
        backgroundColor: 'rgba(255,77,79,0.18)',
    },
    errorText: {
        color: '#ffb4b4',
        fontSize: 13,
        lineHeight: 20,
    },
    bottomBar: {
        alignItems: 'center',
        paddingBottom: 36,
        gap: 10,
    },
    shutterOuter: {
        width: 78,
        height: 78,
        borderRadius: 39,
        borderWidth: 4,
        borderColor: '#fff',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'rgba(255,255,255,0.12)',
    },
    shutterDisabled: {
        opacity: 0.7,
    },
    shutterInner: {
        width: 58,
        height: 58,
        borderRadius: 29,
        backgroundColor: '#fff',
    },
    bottomHint: {
        color: '#fff',
        fontSize: 13,
        backgroundColor: 'rgba(0,0,0,0.45)',
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderRadius: 999,
        overflow: 'hidden',
    },
});
