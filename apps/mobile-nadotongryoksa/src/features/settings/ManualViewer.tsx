/**
 * 사용 설명서 뷰어 — ko/en/ja/zh 는 오프라인 정본, 그 외는 캐시·API 번역.
 * 비한국어 사용자에게 한국어 원문을 먼저 보여주지 않는다(플래시 금지).
 */
import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { translateText } from '../../api/translate';
import { getBundledManual } from '../i18n/bundledManuals';
import { resolveLanguageLabel } from '../profile/profileFormatters';
import type { FeatureManual } from './featureManuals';
import {
    getCachedManual,
    loadManualI18nCacheForLang,
    setCachedManual,
    type CachedManual,
} from './manualI18nCache';

interface TranslatedSection {
    heading: string;
    lines: string[];
}
interface TranslatedManual {
    title: string;
    summary: string;
    sections: TranslatedSection[];
}

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
    /** 설명서 본문 위에 배치(예: 노래 번역 옵션 패널) */
    topSlot?: React.ReactNode;
}

export function ManualViewer({ manual, userLang, onBack, topSlot }: Props) {
    const lang = (userLang || 'ko').toLowerCase();
    const [data, setData] = useState<TranslatedManual | null>(null);
    const [loading, setLoading] = useState(lang !== 'ko');

    useEffect(() => {
        let alive = true;
        if (lang === 'ko') {
            setData(buildKoBase(manual));
            setLoading(false);
            return () => { alive = false; };
        }
        const bundled = getBundledManual(manual.id, lang);
        if (bundled) {
            setData(bundled);
            setLoading(false);
            return () => { alive = false; };
        }
        setData(null);
        setLoading(true);
        void loadManualI18nCacheForLang(lang).then(() => {
            if (!alive) return;
            const cached = getCachedManual(manual.id, lang);
            if (cached) {
                setData(cached);
                setLoading(false);
                return;
            }
            translateManual(manual, lang)
                .then((t) => {
                    if (!alive) return;
                    setCachedManual(manual.id, lang, t as CachedManual);
                    setData(t);
                })
                .catch(() => {
                    if (!alive) return;
                    const enFallback = getBundledManual(manual.id, 'en');
                    if (enFallback) {
                        setData(enFallback);
                    }
                })
                .finally(() => { if (alive) setLoading(false); });
        });
        return () => { alive = false; };
    }, [manual, lang]);

    const display = data ?? (lang === 'ko' ? buildKoBase(manual) : null);

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
                {display ? (
                    <>
                        <Text style={styles.title}>{manual.icon} {display.title}</Text>
                        <Text style={styles.summary}>{display.summary}</Text>
                        {lang !== 'ko' ? (
                            <Text style={styles.langNote}>🌐 {resolveLanguageLabel(lang)}{loading ? ' · …' : ''}</Text>
                        ) : null}

                        {topSlot ? <View style={styles.topSlotWrap}>{topSlot}</View> : null}

                        {display.sections.map((section, si) => (
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
                    </>
                ) : (
                    <View style={styles.loadingWrap}>
                        <ActivityIndicator size="large" color="#1E6FE0" />
                    </View>
                )}
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
    topSlotWrap: { marginBottom: 14 },
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
    loadingWrap: { paddingVertical: 48, alignItems: 'center' },
});
