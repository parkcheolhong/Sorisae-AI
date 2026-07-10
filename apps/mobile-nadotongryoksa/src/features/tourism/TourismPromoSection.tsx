import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
    ActivityIndicator,
    Linking,
    Pressable,
    ScrollView,
    Text,
    TextInput,
    View,
} from 'react-native';

import { translateText } from '../../api/translate';
import { getFeatureUiText } from '../i18n/featureUiCatalog';
import { styles } from '../../../App.styles';
import type { SectionRailKey } from '../navigation/sectionRegistry';
import {
    clearTourismPromoCache,
    fetchTourismPromoBoard,
    postUserTourismPromo,
    type TourismPromoBoardItem,
    type TourismPromoBoardPayload,
} from '../../services/worldlincoTourismPromo';

export type TourismPromoSectionProps = {
    apiBaseUrl: string;
    authToken: string | null | undefined;
    onRequireLogin?: () => void;
    railSectionOffsetRef: React.MutableRefObject<Record<SectionRailKey, number>>;
    activeRailSection: SectionRailKey | null;
    scrollToRailSection: (sectionKey: SectionRailKey, animated?: boolean) => void;
    gpsCountryCode: string | null | undefined;
    latitude: string | number | null | undefined;
    longitude: string | number | null | undefined;
    userLanguage: string;
    onCtaPress?: (action: string) => void;
};

const REASON_MESSAGES: Record<string, string> = {
    gps_country_required: 'tourism.gpsRequired',
    empty_board: 'tourism.emptyBoard',
};

function normalizeLang(raw: string): string {
    return String(raw || 'ko').trim().toLowerCase() || 'ko';
}

function TranslatedPromoBoardCard({
    item,
    viewerLang,
    onCtaPress,
}: {
    item: TourismPromoBoardItem;
    viewerLang: string;
    onCtaPress?: (action: string) => void;
}) {
    const sourceLang = normalizeLang(item.language);
    const targetLang = normalizeLang(viewerLang);
    const [title, setTitle] = useState(item.title);
    const [subtitle, setSubtitle] = useState(item.subtitle);
    const [body, setBody] = useState(item.body);
    const [translating, setTranslating] = useState(false);

    useEffect(() => {
        let alive = true;
        setTitle(item.title);
        setSubtitle(item.subtitle);
        setBody(item.body);
        if (!item.title || sourceLang === targetLang || sourceLang.split('-')[0] === targetLang.split('-')[0]) {
            setTranslating(false);
            return () => { alive = false; };
        }
        setTranslating(true);
        const jobs = [
            item.title,
            item.subtitle || item.title,
            item.body || item.title,
        ];
        Promise.all(
            jobs.map((text) =>
                translateText(text, sourceLang, targetLang, 12000)
                    .then((r) => r.translated || text)
                    .catch(() => text),
            ),
        )
            .then(([t, s, b]) => {
                if (!alive) return;
                setTitle(t);
                setSubtitle(s === t ? '' : s);
                setBody(b);
            })
            .finally(() => { if (alive) setTranslating(false); });
        return () => { alive = false; };
    }, [item.title, item.subtitle, item.body, sourceLang, targetLang]);

    const accent = item.accent_color || (item.source === 'user' ? '#E07C1E' : '#1E6FE0');
    const isUserPost = item.source === 'user';

    const handleCta = useCallback(() => {
        const action = String(item.cta_action || '').trim();
        if (action.startsWith('http://') || action.startsWith('https://')) {
            void Linking.openURL(action);
            return;
        }
        onCtaPress?.(action || 'face_interpretation');
    }, [item.cta_action, onCtaPress]);

    return (
        <View style={[styles.tourismPromoCard, { borderColor: accent, marginBottom: 12 }]}>
            <View style={[styles.tourismPromoAccentBar, { backgroundColor: accent }]} />
            {isUserPost && item.author_username ? (
                <Text style={styles.tourismPromoMeta}>👤 {item.author_username}</Text>
            ) : null}
            {item.nearby ? (
                <Text wlLocalized style={[styles.tourismPromoMeta, { color: accent, fontWeight: '800' }]}>{getFeatureUiText('tourism.nearbyBadge')}</Text>
            ) : null}
            {translating ? (
                <Text wlLocalized style={styles.tourismPromoMeta}>🌐 {getFeatureUiText('tourism.translating')}</Text>
            ) : null}
            <Text style={styles.tourismPromoTitle}>{title}</Text>
            {subtitle ? <Text style={styles.tourismPromoSubtitle}>{subtitle}</Text> : null}
            {body ? <Text style={styles.tourismPromoBody}>{body}</Text> : null}
            {typeof item.distance_km === 'number' ? (
                <Text wlLocalized style={styles.tourismPromoMeta}>
                    {item.distance_km.toFixed(1)}km
                    {typeof item.radius_km === 'number' ? ` · ${getFeatureUiText('tourism.radiusKm', { km: item.radius_km.toFixed(1) })}` : ''}
                </Text>
            ) : null}
            {item.cta_label ? (
                <Pressable
                    style={[styles.tourismPromoCta, { backgroundColor: accent }]}
                    onPress={handleCta}
                    accessibilityRole="button"
                    accessibilityLabel="worldlinco-tourism-promo-board-cta"
                >
                    <Text style={styles.tourismPromoCtaText}>{item.cta_label}</Text>
                </Pressable>
            ) : null}
        </View>
    );
}

export default function TourismPromoSection({
    apiBaseUrl,
    authToken,
    onRequireLogin,
    railSectionOffsetRef,
    activeRailSection,
    scrollToRailSection,
    gpsCountryCode,
    latitude,
    longitude,
    userLanguage,
    onCtaPress,
}: TourismPromoSectionProps) {
    const [board, setBoard] = useState<TourismPromoBoardPayload | null>(null);
    const [loading, setLoading] = useState(false);
    const [composeOpen, setComposeOpen] = useState(false);
    const [posting, setPosting] = useState(false);
    const [postStatus, setPostStatus] = useState('');
    const [draftTitle, setDraftTitle] = useState('');
    const [draftSubtitle, setDraftSubtitle] = useState('');
    const [draftBody, setDraftBody] = useState('');

    const countryReady = useMemo(() => {
        const country = String(gpsCountryCode || '').trim().toUpperCase();
        return /^[A-Z]{2}$/.test(country);
    }, [gpsCountryCode]);

    const reloadBoard = useCallback(async () => {
        if (!countryReady) {
            setBoard(null);
            return;
        }
        setLoading(true);
        try {
            const payload = await fetchTourismPromoBoard(apiBaseUrl, {
                countryCode: gpsCountryCode,
                latitude,
                longitude,
                language: userLanguage,
            });
            setBoard(payload);
        } catch {
            setBoard(null);
        } finally {
            setLoading(false);
        }
    }, [apiBaseUrl, countryReady, gpsCountryCode, latitude, longitude, userLanguage]);

    useEffect(() => {
        let alive = true;
        if (!countryReady) {
            setBoard(null);
            setLoading(false);
            return () => { alive = false; };
        }
        setLoading(true);
        void fetchTourismPromoBoard(apiBaseUrl, {
            countryCode: gpsCountryCode,
            latitude,
            longitude,
            language: userLanguage,
        })
            .then((payload) => { if (alive) setBoard(payload); })
            .catch(() => { if (alive) setBoard(null); })
            .finally(() => { if (alive) setLoading(false); });
        return () => { alive = false; };
    }, [apiBaseUrl, countryReady, gpsCountryCode, latitude, longitude, userLanguage]);

    const emptyMessage = useMemo(() => {
        if (!countryReady) {
            return getFeatureUiText(REASON_MESSAGES.gps_country_required as 'tourism.gpsRequired');
        }
        if (board?.reason === 'empty_board' || (board?.enabled && !board.items.length)) {
            return getFeatureUiText(REASON_MESSAGES.empty_board as 'tourism.emptyBoard');
        }
        if (board?.reason) {
            const key = REASON_MESSAGES[board.reason];
            return key ? getFeatureUiText(key as 'tourism.gpsRequired' | 'tourism.emptyBoard') : getFeatureUiText('tourism.emptyBoard');
        }
        return null;
    }, [board, countryReady]);

    const items = board?.enabled ? board.items : [];

    const handlePost = useCallback(async () => {
        if (!authToken) {
            onRequireLogin?.();
            return;
        }
        if (!countryReady) {
            setPostStatus('GPS 국가 확인 후 홍보할 수 있습니다.');
            return;
        }
        const title = draftTitle.trim();
        const body = draftBody.trim();
        if (!title || !body) {
            setPostStatus('제목과 내용을 입력해 주세요.');
            return;
        }
        setPosting(true);
        setPostStatus('');
        try {
            const lat = latitude === null || latitude === undefined || latitude === ''
                ? null
                : Number.parseFloat(String(latitude));
            const lon = longitude === null || longitude === undefined || longitude === ''
                ? null
                : Number.parseFloat(String(longitude));
            await postUserTourismPromo(apiBaseUrl, authToken, {
                title,
                subtitle: draftSubtitle.trim(),
                body,
                countryCode: gpsCountryCode!,
                latitude: Number.isFinite(lat) ? lat : null,
                longitude: Number.isFinite(lon) ? lon : null,
                language: userLanguage,
            });
            setDraftTitle('');
            setDraftSubtitle('');
            setDraftBody('');
            setComposeOpen(false);
            setPostStatus(getFeatureUiText('tourism.postSuccess'));
            clearTourismPromoCache();
            await reloadBoard();
        } catch (error) {
            const message = error instanceof Error ? error.message : 'failed';
            setPostStatus(getFeatureUiText('tourism.postFailed', { message }));
        } finally {
            setPosting(false);
        }
    }, [
        apiBaseUrl,
        authToken,
        countryReady,
        draftBody,
        draftSubtitle,
        draftTitle,
        gpsCountryCode,
        latitude,
        longitude,
        onRequireLogin,
        reloadBoard,
        userLanguage,
    ]);

    return (
        <View
            onLayout={(event) => {
                railSectionOffsetRef.current['tourism-promo'] = event.nativeEvent.layout.y;
                if (activeRailSection === 'tourism-promo') {
                    scrollToRailSection('tourism-promo');
                }
            }}
            style={[styles.sectionCard, activeRailSection === 'tourism-promo' && styles.sectionCardActive]}
        >
            <Text wlLocalized style={styles.songFileTimelineTitle}>{getFeatureUiText('tourism.promoTitle')}</Text>
            <Text wlLocalized style={styles.songSubtitleMeta}>
                {getFeatureUiText('tourism.promoIntro')}
            </Text>

            <Pressable
                style={[styles.inlineGhostBtn, { marginTop: 10, alignSelf: 'flex-start' }]}
                onPress={() => {
                    if (!authToken) {
                        onRequireLogin?.();
                        return;
                    }
                    setComposeOpen((v) => !v);
                }}
                accessibilityRole="button"
                accessibilityLabel="worldlinco-tourism-promo-compose"
                testID="worldlinco-tourism-promo-compose"
            >
                <Text wlLocalized style={styles.inlineGhostBtnText}>
                    {composeOpen ? getFeatureUiText('tourism.composeClose') : getFeatureUiText('tourism.composeOpen')}
                </Text>
            </Pressable>

            {composeOpen ? (
                <View style={[styles.voicePreviewPanel, { marginTop: 10 }]}>
                    <TextInput
                        style={styles.songFileSegmentInput}
                        placeholder="예: ○○ 게스트하우스, ○○ 식당 (필수)"
                        value={draftTitle}
                        onChangeText={setDraftTitle}
                        maxLength={120}
                    />
                    <TextInput
                        style={[styles.songFileSegmentInput, { marginTop: 8 }]}
                        placeholder="예: 할인, 조식 포함, 추천 메뉴 (선택)"
                        value={draftSubtitle}
                        onChangeText={setDraftSubtitle}
                        maxLength={160}
                    />
                    <TextInput
                        style={[styles.songFileSegmentInput, { marginTop: 8, minHeight: 88 }]}
                        placeholder="위치·가격·영업시간·추천 이유 등 (필수)"
                        value={draftBody}
                        onChangeText={setDraftBody}
                        multiline
                        maxLength={800}
                    />
                    <Pressable
                        style={[styles.tourismPromoCta, { backgroundColor: '#E07C1E', marginTop: 10 }]}
                        onPress={() => { void handlePost(); }}
                        disabled={posting}
                    >
                        <Text style={styles.tourismPromoCtaText}>
                            {posting ? '등록 중…' : '홍보 게시하기'}
                        </Text>
                    </Pressable>
                </View>
            ) : null}

            {postStatus ? <Text style={styles.songModeStatusText}>{postStatus}</Text> : null}

            {loading ? (
                <View style={{ paddingVertical: 24, alignItems: 'center' }}>
                    <ActivityIndicator size="small" color="#1E6FE0" />
                    <Text style={styles.songSubtitleMeta}>게시판 불러오는 중…</Text>
                </View>
            ) : null}

            {!loading && emptyMessage && items.length === 0 ? (
                <Text style={styles.songSubtitlePlaceholder}>{emptyMessage}</Text>
            ) : null}

            {!loading && items.length > 0 ? (
                <ScrollView style={{ marginTop: 8 }} nestedScrollEnabled>
                    {items.map((item) => (
                        <TranslatedPromoBoardCard
                            key={String(item.post_id || item.spot_id || item.title)}
                            item={item}
                            viewerLang={userLanguage}
                            onCtaPress={onCtaPress}
                        />
                    ))}
                </ScrollView>
            ) : null}
        </View>
    );
}
