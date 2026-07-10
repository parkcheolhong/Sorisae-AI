import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { View, Text, Pressable, Linking } from 'react-native';

import { styles } from '../../../App.styles';
import {
    fetchTourismPromo,
    type TourismPromoPayload,
} from '../../services/worldlincoTourismPromo';

export type CountryTourismPromoCardProps = {
    apiBaseUrl: string;
    /** GPS 역지오코딩 국가 코드(프로필 국가 사용 안 함) */
    gpsCountryCode: string | null | undefined;
    latitude: string | number | null | undefined;
    longitude: string | number | null | undefined;
    /** 앱 프로그램(사용자) 언어 코드 */
    userLanguage: string;
    onCtaPress?: (action: string) => void;
};

export default function CountryTourismPromoCard({
    apiBaseUrl,
    gpsCountryCode,
    latitude,
    longitude,
    userLanguage,
    onCtaPress,
}: CountryTourismPromoCardProps) {
    const [promo, setPromo] = useState<TourismPromoPayload | null>(null);

    const queryReady = useMemo(() => {
        const country = String(gpsCountryCode || '').trim().toUpperCase();
        const lat = latitude === null || latitude === undefined || latitude === ''
            ? null
            : Number.parseFloat(String(latitude));
        const lon = longitude === null || longitude === undefined || longitude === ''
            ? null
            : Number.parseFloat(String(longitude));
        return /^[A-Z]{2}$/.test(country) && Number.isFinite(lat) && Number.isFinite(lon);
    }, [gpsCountryCode, latitude, longitude]);

    useEffect(() => {
        let alive = true;
        if (!queryReady) {
            setPromo(null);
            return () => {
                alive = false;
            };
        }
        void fetchTourismPromo(apiBaseUrl, {
            countryCode: gpsCountryCode,
            latitude,
            longitude,
            language: userLanguage,
        })
            .then((payload) => {
                if (alive) {
                    setPromo(payload);
                }
            })
            .catch(() => {
                if (alive) {
                    setPromo(null);
                }
            });
        return () => {
            alive = false;
        };
    }, [apiBaseUrl, gpsCountryCode, latitude, longitude, queryReady, userLanguage]);

    const handleCta = useCallback(() => {
        if (!promo) {
            return;
        }
        const action = String(promo.cta_action || '').trim();
        if (action.startsWith('http://') || action.startsWith('https://')) {
            void Linking.openURL(action);
            return;
        }
        onCtaPress?.(action || 'face_interpretation');
    }, [onCtaPress, promo]);

    if (!queryReady || !promo) {
        return null;
    }

    const accent = promo.accent_color || '#1E6FE0';

    return (
        <View style={[styles.tourismPromoCard, { borderColor: accent }]}>
            <View style={[styles.tourismPromoAccentBar, { backgroundColor: accent }]} />
            <Text style={styles.tourismPromoTitle}>{promo.title}</Text>
            {promo.subtitle ? <Text style={styles.tourismPromoSubtitle}>{promo.subtitle}</Text> : null}
            {promo.body ? <Text style={styles.tourismPromoBody}>{promo.body}</Text> : null}
            {typeof promo.distance_km === 'number' ? (
                <Text style={styles.tourismPromoMeta}>
                    GPS {promo.country_code} · {promo.distance_km.toFixed(1)}km
                    {typeof promo.radius_km === 'number' ? ` / ${promo.radius_km}km` : ''}
                </Text>
            ) : null}
            {promo.cta_label ? (
                <Pressable
                    style={[styles.tourismPromoCta, { backgroundColor: accent }]}
                    onPress={handleCta}
                    accessibilityRole="button"
                    accessibilityLabel="worldlinco-tourism-promo-cta"
                    testID="worldlinco-tourism-promo-cta"
                >
                    <Text style={styles.tourismPromoCtaText}>{promo.cta_label}</Text>
                </Pressable>
            ) : null}
        </View>
    );
}
