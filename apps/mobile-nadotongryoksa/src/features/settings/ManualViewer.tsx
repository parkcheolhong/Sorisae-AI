/**
 * 사용 설명서 뷰어 — 한국어 기본문을 사용자가 지정한 언어(userLang)로 자동 번역해 보여준다.
 *
 * - userLang === 'ko' 이면 원문 그대로.
 * - 그 외 언어는 translateText(ko → userLang)로 줄 단위 번역(언어별 메모리 캐시).
 * - 번역 동안에는 한국어 원문을 먼저 보여주고(빈 화면 방지), 끝나면 번역으로 교체한다.
 */
import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { translateText } from '../../api/translate';
import { resolveLanguageLabel } from '../profile/profileFormatters';
import type { FeatureManual } from './featureManuals';

interface TranslatedSection {
    heading: string;
    lines: string[];
}
interface TranslatedManual {
    title: string;
    summary: string;
    sections: TranslatedSection[];
}

// 언어별 번역 캐시(앱 실행 동안 유지) — 같은 설명서를 다시 열면 즉시 표시.
const manualCache = new Map<string, TranslatedManual>();

function buildKoBase(m: FeatureManual): TranslatedManual {
    return {
        title: m.titleKo,
        summary: m.summaryKo,
        sections: m.sections.map((s) => ({ heading: s.headingKo, lines: s.linesKo })),
    };
}

// 과도한 동시 요청을 피하려 5개씩 끊어 번역. 실패한 줄은 원문 유지.
async function translateChunked(items: string[], to: string, size = 5): Promise<string[]> {
    const out: string[] = [];
    for (let i = 0; i < items.length; i += size) {
        const chunk = items.slice(i, i + size);
        // eslint-disable-next-line no-await-in-loop
        const translated = await Promise.all(
            chunk.map((text) =>
                translateText(text, 'ko', to, 10000)
                    .then((r) => r.translated || text)
                    .catch(() => text),
            ),
        );
        out.push(...translated);
    }
    return out;
}

async function translateManual(m: FeatureManual, to: string): Promise<TranslatedManual> {
    const jobs: string[] = [m.titleKo, m.summaryKo];
    m.sections.forEach((s) => {
        jobs.push(s.headingKo);
        s.linesKo.forEach((l) => jobs.push(l));
    });
    const out = await translateChunked(jobs, to);
    let i = 0;
    const title = out[i++];
    const summary = out[i++];
    const sections = m.sections.map((s) => {
        const heading = out[i++];
        const lines = s.linesKo.map(() => out[i++]);
        return { heading, lines };
    });
    return { title, summary, sections };
}

interface Props {
    manual: FeatureManual;
    userLang: string;
    onBack: () => void;
}

export function ManualViewer({ manual, userLang, onBack }: Props) {
    const lang = (userLang || 'ko').toLowerCase();
    const [data, setData] = useState<TranslatedManual>(() => buildKoBase(manual));
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        let alive = true;
        if (lang === 'ko') {
            setData(buildKoBase(manual));
            setLoading(false);
            return () => { alive = false; };
        }
        const key = `${manual.id}:${lang}`;
        const cached = manualCache.get(key);
        if (cached) {
            setData(cached);
            setLoading(false);
            return () => { alive = false; };
        }
        // 번역 중에는 한국어 원문을 먼저 보여준다.
        setData(buildKoBase(manual));
        setLoading(true);
        translateManual(manual, lang)
            .then((t) => {
                if (!alive) return;
                manualCache.set(key, t);
                setData(t);
            })
            .catch(() => { /* 실패 시 원문 유지 */ })
            .finally(() => { if (alive) setLoading(false); });
        return () => { alive = false; };
    }, [manual, lang]);

    return (
        <View style={styles.root}>
            <View style={styles.header}>
                <Pressable
                    onPress={onBack}
                    style={styles.backBtn}
                    accessibilityRole="button"
                    accessibilityLabel="worldlinco-manual-back"
                    testID="worldlinco-manual-back"
                >
                    <Text style={styles.backBtnText}>‹ 뒤로</Text>
                </Pressable>
                {loading ? <ActivityIndicator size="small" color="#1E6FE0" /> : null}
            </View>

            <ScrollView style={{ flex: 1 }} contentContainerStyle={styles.scrollContent}>
                <Text style={styles.title}>{manual.icon} {data.title}</Text>
                <Text style={styles.summary}>{data.summary}</Text>
                {lang !== 'ko' ? (
                    <Text style={styles.langNote}>🌐 {resolveLanguageLabel(lang)}{loading ? ' · 번역 중…' : ' · 자동 번역됨'}</Text>
                ) : null}

                {data.sections.map((section, si) => (
                    <View key={`sec-${si}`} style={styles.sectionCard}>
                        <Text style={styles.sectionHeading}>{section.heading}</Text>
                        {section.lines.map((line, li) => (
                            <View key={`line-${si}-${li}`} style={styles.lineRow}>
                                <Text style={styles.bullet}>•</Text>
                                <Text style={styles.lineText}>{line}</Text>
                            </View>
                        ))}
                    </View>
                ))}
            </ScrollView>
        </View>
    );
}

const styles = StyleSheet.create({
    root: { flex: 1, paddingHorizontal: 14 },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingTop: 8,
        paddingBottom: 6,
    },
    backBtn: {
        paddingVertical: 6,
        paddingHorizontal: 12,
        borderRadius: 18,
        backgroundColor: 'rgba(255,255,255,0.85)',
        borderWidth: 1,
        borderColor: '#d4def0',
    },
    backBtnText: { fontSize: 15, fontWeight: '800', color: '#1E6FE0' },
    scrollContent: { paddingBottom: 40 },
    title: { fontSize: 23, fontWeight: '900', color: '#10243f', marginTop: 4 },
    summary: { fontSize: 14.5, color: '#3a4a63', lineHeight: 21, marginTop: 6 },
    langNote: { fontSize: 12.5, color: '#1E6FE0', fontWeight: '700', marginTop: 8 },
    sectionCard: {
        backgroundColor: 'rgba(255,255,255,0.94)',
        borderRadius: 16,
        padding: 14,
        marginTop: 12,
        borderWidth: 1,
        borderColor: '#e1e9f5',
    },
    sectionHeading: { fontSize: 16, fontWeight: '900', color: '#16263f', marginBottom: 8 },
    lineRow: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 7 },
    bullet: { fontSize: 15, color: '#1E6FE0', width: 16, lineHeight: 21 },
    lineText: { flex: 1, fontSize: 14.5, color: '#33455f', lineHeight: 21 },
});
