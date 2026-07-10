import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { NetworkDiagnosticsSnapshot } from '../utils/networkDiagnostics';
import {
    activeColorScheme,
    fontSize,
    fontWeight,
    getColors,
    lineHeight,
    radius,
    spacing,
    type Colors,
    type ColorScheme,
} from '../theme/theme';

interface Props {
    snapshot: NetworkDiagnosticsSnapshot;
    /** QA/필드 테스트 힌트 — 기본 false (베타 사용자에게 불편한 경고 숨김) */
    showFieldTestHints?: boolean;
}

export function NetworkTestBanner({ snapshot, showFieldTestHints = false }: Props) {
    const statusTone = snapshot.warningMessage
        ? styles.errorBanner
        : snapshot.transport === 'cellular'
            ? styles.readyBanner
            : styles.infoBanner;

    return (
        <View style={[styles.banner, statusTone]}>
            <Text style={styles.title}>📶 연결 상태</Text>
            <Text style={styles.line}>
                {snapshot.statusMessage}
                {snapshot.carrier ? ` · ${snapshot.carrier}` : null}
                {snapshot.ssid ? ` · ${snapshot.ssid}` : null}
            </Text>
            {snapshot.warningMessage ? (
                <Text style={styles.warningText}>{snapshot.warningMessage}</Text>
            ) : null}
            {showFieldTestHints && snapshot.fieldTestHint ? (
                <Text style={styles.matrixHint}>{snapshot.fieldTestHint}</Text>
            ) : null}
        </View>
    );
}

/**
 * 디자인 토큰 기반 스타일(인라인 hex → theme 토큰 치환).
 * - 상태색(성공/정보/경고 배경·테두리)은 기존 사용값과 **동일**(darkColors.status 에 원값 채택).
 * - 텍스트 그레이·간격·라운드는 디자인 시스템 토큰(canonical 그레이 + 8pt 스케일)으로 **정규화**
 *   (예: #e8edf8→text, padding 10→md(12), radius 8→md(10)) — 시각적으로 거의 동일한 미세 정렬.
 * - 라이트 전환 시 `getColors('light')` 로 자동 대응.
 */
function makeStyles(c: Colors) {
    return StyleSheet.create({
        banner: {
            borderRadius: radius.md,
            borderWidth: 1,
            padding: spacing.md,
            gap: spacing.sm,
            marginVertical: spacing.xs,
        },
        readyBanner: {
            backgroundColor: c.status.successBg,
            borderColor: c.status.successBorder,
        },
        infoBanner: {
            backgroundColor: c.status.infoBg,
            borderColor: c.status.infoBorder,
        },
        errorBanner: {
            backgroundColor: c.status.dangerBg,
            borderColor: c.status.dangerBorder,
        },
        title: {
            fontSize: fontSize.caption + 1,
            fontWeight: fontWeight.bold,
            color: c.text,
        },
        line: {
            fontSize: fontSize.caption,
            color: c.textBody,
            lineHeight: lineHeight.caption + 2,
        },
        warningText: {
            fontSize: fontSize.caption,
            color: c.status.dangerText,
            lineHeight: lineHeight.caption + 2,
        },
        matrixHint: {
            fontSize: fontSize.caption - 1,
            color: c.textMuted,
            lineHeight: lineHeight.caption,
        },
    });
}

const stylesByScheme: Record<ColorScheme, ReturnType<typeof makeStyles>> = {
    light: makeStyles(getColors('light')),
    dark: makeStyles(getColors('dark')),
};

const styles = stylesByScheme[activeColorScheme];
