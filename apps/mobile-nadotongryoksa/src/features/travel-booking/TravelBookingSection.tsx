// App.tsx 에서 분리한 여행/예약 섹션(B2 파일럿, 패스스루 — 상태는 App 소유).
import React from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { View, Text, Pressable, ScrollView, TextInput, ActivityIndicator, Linking, Platform } from 'react-native';
import WebView, { type WebViewMessageEvent } from 'react-native-webview';
import { styles } from '../../../App.styles';
import { C } from '../../app/appTheme';
import { CATEGORY_OPTIONS, RADIUS_OPTIONS, API_BASE } from '../../app/appConstants';
import { SUPPORTED_LANGUAGE_COUNT, type LangCode } from '../language/languageCatalog';
import { formatDistance } from './travelBooking';
import { formatAutoRelayDelayLabel } from '../shared/relayTextGuards';
import { BidirectionalLanguagePairBadge } from '../i18n/BidirectionalLanguagePairBadge';
import { getFeatureUiText } from '../i18n/featureUiCatalog';
import { formatFlagPrefixedName, resolveUserCountryFlag } from '../i18n/userDisplayIdentity';
import TravelItineraryPanel from '../travel-itinerary/TravelItineraryPanel';
import type { NearbyPlace, BookingResponse, SearchCategory } from './types';
import type { PurchaseResult, UserInfo } from '../../app/appTypes';
import type { SectionRailKey } from '../navigation/sectionRegistry';
import type { InterCallLogEntry } from '../call-mode/useInterCallState';

export type TravelBookingSectionProps = {
    railSectionOffsetRef: React.MutableRefObject<Record<SectionRailKey, number>>;
    activeRailSection: SectionRailKey | null;
    scrollToRailSection: (sectionKey: SectionRailKey, animated?: boolean) => void;
    handleSearchNearby: () => void;
    setNearbyCategory: Dispatch<SetStateAction<SearchCategory>>;
    lat: string; setLat: Dispatch<SetStateAction<string>>;
    lon: string; setLon: Dispatch<SetStateAction<string>>;
    nearbyCategory: SearchCategory;
    radiusM: number; setRadiusM: Dispatch<SetStateAction<number>>;
    nearbyLoading: boolean;
    toLang: LangCode; fromLang: LangCode;
    gpsRegionHint: string;
    resolveActiveRegionHint: (source: LangCode) => string | undefined;
    gpsCountryCode: string;
    itinerarySeedQuery: string; itinerarySeedNonce: number;
    nearbyError: string;
    selectedBookingPlace: NearbyPlace | null;
    bookingSelectionNotice: string;
    nearbyPlaces: NearbyPlace[];
    nearbyMapHtml: string;
    handleNearbyMapMessage: (event: WebViewMessageEvent) => void;
    selectedNearbyPlace: NearbyPlace | null;
    setSelectedNearbyPlaceId: Dispatch<SetStateAction<string>>;
    selectedBookingPlaceId: string;
    selectBookingPlace: (placeId: string, sourceLabel: '지도' | '목록', focusTravelSection?: boolean) => void;
    getLangLabel: (code: LangCode) => string;
    interCallActive: boolean;
    handleInterCallToggle: () => void;
    interCallPhone: string; setInterCallPhone: (value: string) => void;
    setShowPhoneDialerModal: Dispatch<SetStateAction<boolean>>;
    interCallStatus: string;
    interCallTurn: 'from' | 'to';
    handleToggleInterCallVoiceAssist: () => void;
    voiceInputTargetRef: React.MutableRefObject<'main' | 'inter_call'>;
    isVoiceRecording: boolean; voiceSttLoading: boolean;
    interCallVoiceAssistEnabled: boolean;
    autoRelayDelayMs: number; setAutoRelayDelayMs: Dispatch<SetStateAction<number>>;
    AUTO_RELAY_DELAY_OPTIONS_MS: readonly number[];
    interManualText: string; setInterManualText: (value: string) => void;
    relayInterCallManual: (turn: 'from' | 'to', spokenText: string, options?: { isAutoRelay?: boolean }) => void;
    interCallLog: InterCallLogEntry[];
    token: string;
    userInfo: UserInfo | null;
    renderSectionConnectionCard: (config: { sectionKey: SectionRailKey; title: string; body: string; bullets: string[]; loginSource: string }) => React.ReactNode;
    openDialPad: (phone: string, reason?: string) => void | Promise<void>;
    bookingName: string; setBookingName: Dispatch<SetStateAction<string>>;
    checkinDate: string; setCheckinDate: Dispatch<SetStateAction<string>>;
    checkoutDate: string; setCheckoutDate: Dispatch<SetStateAction<string>>;
    guests: number; setGuests: Dispatch<SetStateAction<number>>;
    roomCount: number; setRoomCount: Dispatch<SetStateAction<number>>;
    bookingNote: string; setBookingNote: Dispatch<SetStateAction<string>>;
    bookingLoading: boolean;
    handleReserveBooking: () => void;
    bookingError: string;
    bookingResult: BookingResponse | null;
    payError: string;
    purchaseResult: PurchaseResult | null;
    payUrl: string;
    handlePayment: () => void;
    payLoading: boolean;
};

export default function TravelBookingSection(props: TravelBookingSectionProps) {
    const {
        railSectionOffsetRef,
        activeRailSection,
        scrollToRailSection,
        handleSearchNearby,
        setNearbyCategory,
        lat,
        setLat,
        lon,
        setLon,
        nearbyCategory,
        radiusM,
        setRadiusM,
        nearbyLoading,
        toLang,
        fromLang,
        gpsRegionHint,
        resolveActiveRegionHint,
        gpsCountryCode,
        itinerarySeedQuery,
        itinerarySeedNonce,
        nearbyError,
        selectedBookingPlace,
        bookingSelectionNotice,
        nearbyPlaces,
        nearbyMapHtml,
        handleNearbyMapMessage,
        selectedNearbyPlace,
        setSelectedNearbyPlaceId,
        selectedBookingPlaceId,
        selectBookingPlace,
        getLangLabel,
        interCallActive,
        handleInterCallToggle,
        interCallPhone,
        setInterCallPhone,
        setShowPhoneDialerModal,
        interCallStatus,
        interCallTurn,
        handleToggleInterCallVoiceAssist,
        voiceInputTargetRef,
        isVoiceRecording,
        voiceSttLoading,
        interCallVoiceAssistEnabled,
        autoRelayDelayMs,
        setAutoRelayDelayMs,
        AUTO_RELAY_DELAY_OPTIONS_MS,
        interManualText,
        setInterManualText,
        relayInterCallManual,
        interCallLog,
        token,
        userInfo,
        renderSectionConnectionCard,
        openDialPad,
        bookingName,
        setBookingName,
        checkinDate,
        setCheckinDate,
        checkoutDate,
        setCheckoutDate,
        guests,
        setGuests,
        roomCount,
        setRoomCount,
        bookingNote,
        setBookingNote,
        bookingLoading,
        handleReserveBooking,
        bookingError,
        bookingResult,
        payError,
        purchaseResult,
        payUrl,
        handlePayment,
        payLoading,
    } = props;
    return (
        <>

                        {/* 주변 검색 레일 */}
                            <View
                                onLayout={(event) => {
                                    railSectionOffsetRef.current['travel-booking'] = event.nativeEvent.layout.y;
                                    if (activeRailSection === 'travel-booking') {
                                        scrollToRailSection('travel-booking');
                                    }
                                }}
                                style={styles.sectionCard}
                            >
                                <View style={styles.bookingTileGrid}>
                                    <Pressable
                                        style={styles.bookingTile}
                                        onPress={() => setNearbyCategory('airport')}
                                        accessibilityRole="button"
                                        accessibilityLabel="항공권"
                                        testID="worldlinco-booking-action-flight"
                                    >
                                        <View style={[styles.bookingTileIcon, { backgroundColor: '#19C37D' }]}><Text style={styles.bookingTileEmoji}>✈️</Text></View>
                                        <Text style={styles.bookingTileLabel}>항공권</Text>
                                    </Pressable>
                                    <Pressable
                                        style={styles.bookingTile}
                                        onPress={() => setNearbyCategory('hotel')}
                                        accessibilityRole="button"
                                        accessibilityLabel="호텔"
                                        testID="worldlinco-booking-action-hotel"
                                    >
                                        <View style={[styles.bookingTileIcon, { backgroundColor: '#19C37D' }]}><Text style={styles.bookingTileEmoji}>🏨</Text></View>
                                        <Text style={styles.bookingTileLabel}>호텔</Text>
                                    </Pressable>
                                    <Pressable
                                        style={styles.bookingTile}
                                        onPress={() => setNearbyCategory('all')}
                                        accessibilityRole="button"
                                        accessibilityLabel="주변 검색"
                                        testID="worldlinco-booking-action-nearby"
                                    >
                                        <View style={[styles.bookingTileIcon, { backgroundColor: '#19C37D' }]}><Text style={styles.bookingTileEmoji}>📍</Text></View>
                                        <Text style={styles.bookingTileLabel}>주변 검색</Text>
                                    </Pressable>
                                    <Pressable
                                        style={styles.bookingTile}
                                        onPress={() => setNearbyCategory('attraction')}
                                        accessibilityRole="button"
                                        accessibilityLabel="일정"
                                        testID="worldlinco-booking-action-itinerary"
                                    >
                                        <View style={[styles.bookingTileIcon, { backgroundColor: '#19C37D' }]}><Text style={styles.bookingTileEmoji}>📅</Text></View>
                                        <Text style={styles.bookingTileLabel}>일정</Text>
                                    </Pressable>
                                </View>
                                <Pressable
                                    style={styles.bookingNearbyCard}
                                    onPress={handleSearchNearby}
                                    accessibilityRole="button"
                                    accessibilityLabel="주변 추천"
                                    testID="worldlinco-booking-nearby-recommend"
                                >
                                    <View style={styles.bookingNearbyThumb}><Text style={styles.bookingNearbyThumbEmoji}>🗺️</Text></View>
                                    <View style={styles.bookingNearbyBody}>
                                        <Text style={styles.bookingNearbyTitle}>주변 추천</Text>
                                    </View>
                                    <Text style={styles.voipTileChevron}>›</Text>
                                </Pressable>
                                <Text style={[styles.sectionTitle, { color: '#19C37D', marginTop: 18 }]}>📍 주변 검색</Text>

                                <View style={styles.coordRow}>
                                    <View style={styles.coordField}>
                                        <Text style={styles.coordLabel}>위도</Text>
                                        <TextInput
                                            style={styles.compactInput}
                                            value={lat}
                                            onChangeText={setLat}
                                            accessibilityLabel="worldlinco-travel-lat-input"
                                            testID="worldlinco-travel-lat-input"
                                        />
                                    </View>
                                    <View style={styles.coordField}>
                                        <Text style={styles.coordLabel}>경도</Text>
                                        <TextInput
                                            style={styles.compactInput}
                                            value={lon}
                                            onChangeText={setLon}
                                            accessibilityLabel="worldlinco-travel-lon-input"
                                            testID="worldlinco-travel-lon-input"
                                        />
                                    </View>
                                </View>

                                <Text style={styles.label}>카테고리</Text>
                                <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.railRow}>
                                    {CATEGORY_OPTIONS.map((item) => (
                                        <Pressable
                                            key={item.value}
                                            style={[styles.railBtn, nearbyCategory === item.value && styles.railBtnActive]}
                                            onPress={() => setNearbyCategory(item.value)}
                                            accessibilityLabel={`worldlinco-travel-category-${item.value}`}
                                            testID={`worldlinco-travel-category-${item.value}`}
                                        >
                                            <Text style={[styles.railBtnText, nearbyCategory === item.value && styles.railBtnTextActive]}>{item.label}</Text>
                                        </Pressable>
                                    ))}
                                </ScrollView>

                                <Text style={styles.label}>검색 반경</Text>
                                <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.railRow}>
                                    {RADIUS_OPTIONS.map((item) => (
                                        <Pressable
                                            key={item.value}
                                            style={[styles.railBtn, radiusM === item.value && styles.railBtnActive]}
                                            onPress={() => setRadiusM(item.value)}
                                            accessibilityLabel={`worldlinco-travel-radius-${item.value}`}
                                            testID={`worldlinco-travel-radius-${item.value}`}
                                        >
                                            <Text style={[styles.railBtnText, radiusM === item.value && styles.railBtnTextActive]}>{item.label}</Text>
                                        </Pressable>
                                    ))}
                                </ScrollView>

                                <Pressable
                                    style={[styles.translateBtn, nearbyLoading && styles.translateBtnDisabled]}
                                    onPress={handleSearchNearby}
                                    disabled={nearbyLoading}
                                    accessibilityLabel="worldlinco-travel-search-button"
                                    testID="worldlinco-travel-search-button"
                                >
                                    {nearbyLoading ? <ActivityIndicator color="#fff" size="small" /> : <Text style={styles.translateBtnText}>주변 장소 찾기</Text>}
                                </Pressable>

                                <TravelItineraryPanel
                                    latitude={Number.parseFloat(lat)}
                                    longitude={Number.parseFloat(lon)}
                                    language={toLang}
                                    regionHint={gpsRegionHint || resolveActiveRegionHint(fromLang)}
                                    countryCode={gpsCountryCode}
                                    apiBase={API_BASE}
                                    seedQuery={itinerarySeedQuery}
                                    seedNonce={itinerarySeedNonce}
                                />

                                {nearbyError ? <Text style={styles.errorText}>{nearbyError}</Text> : null}

                                {selectedBookingPlace ? (
                                    <View style={styles.bookingSelectionBanner}>
                                        <Text style={styles.bookingSelectionBannerTitle}>선택된 예약 장소</Text>
                                        <Text style={styles.bookingSelectionBannerPlace}>{selectedBookingPlace.name}</Text>
                                        <Text style={styles.bookingSelectionBannerMeta}>
                                            {selectedBookingPlace.category_label} · {formatDistance(selectedBookingPlace.distance_m)} · 아래 예약 카드에 즉시 반영됩니다.
                                        </Text>
                                        <Text style={styles.bookingSelectionBannerStatic}>예약 선택 완료 · 예약 폼에 반영됨</Text>
                                        {bookingSelectionNotice ? (
                                            <Text style={styles.bookingSelectionBannerNotice}>{bookingSelectionNotice}</Text>
                                        ) : null}
                                    </View>
                                ) : null}

                                {nearbyPlaces.length > 0 && (
                                    <View style={styles.nearbyMapWrap} pointerEvents="none">
                                        <View style={styles.nearbyMapHeaderRow}>
                                            <Text style={styles.nearbyMapTitle}>지도 미리보기</Text>
                                            <Text style={styles.nearbyMapSubtitle}>{selectedNearbyPlace?.name || '검색 결과'}</Text>
                                        </View>
                                        {nearbyMapHtml ? (
                                            <WebView
                                                originWhitelist={['*']}
                                                source={{ html: nearbyMapHtml }}
                                                style={styles.nearbyMapWebView}
                                                scrollEnabled={false}
                                                nestedScrollEnabled
                                                onMessage={handleNearbyMapMessage}
                                            />
                                        ) : null}
                                    </View>
                                )}

                                {nearbyPlaces.length > 0 && (
                                    <View style={styles.nearbyListWrap}>
                                        {nearbyPlaces.map((place) => (
                                            <Pressable
                                                key={place.id}
                                                style={[styles.placeItem, selectedNearbyPlace?.id === place.id && styles.placeItemActive]}
                                                onPress={() => setSelectedNearbyPlaceId(place.id)}
                                                accessibilityLabel={`worldlinco-travel-place-${place.id}`}
                                                testID={`worldlinco-travel-place-${place.id}`}
                                            >
                                                <Text style={styles.placeName}>{place.name}</Text>
                                                <Text style={styles.placeMeta}>{place.category_label} · {formatDistance(place.distance_m)} · ★ {Number(place.rating).toFixed(1)}</Text>
                                                <Text style={styles.placeAddr}>{place.address}</Text>
                                                <View style={styles.placeActionRow}>
                                                    <Pressable
                                                        style={[styles.inlineActionBtn, selectedNearbyPlace?.id === place.id && styles.inlineActionBtnActive]}
                                                        onPress={() => setSelectedNearbyPlaceId(place.id)}
                                                    >
                                                        <Text style={[styles.inlineActionBtnText, selectedNearbyPlace?.id === place.id && styles.inlineActionBtnTextActive]}>지도에서 보기</Text>
                                                    </Pressable>
                                                    <Pressable style={styles.inlineActionBtn} onPress={() => {
                                                        setSelectedNearbyPlaceId(place.id);
                                                        Linking.openURL(place.google_maps_url);
                                                    }}>
                                                        <Text style={styles.inlineActionBtnText}>Google 지도</Text>
                                                    </Pressable>
                                                    {place.booking_supported && (place.category === 'hotel' || place.category === 'airport') && (
                                                        <Pressable
                                                            style={[styles.inlineActionBtn, selectedBookingPlaceId === place.id && styles.inlineActionBtnActive]}
                                                            onPress={() => selectBookingPlace(place.id, '목록')}
                                                            accessibilityLabel={`worldlinco-travel-booking-select-${place.id}`}
                                                            testID={`worldlinco-travel-booking-select-${place.id}`}
                                                        >
                                                            <Text style={[styles.inlineActionBtnText, selectedBookingPlaceId === place.id && styles.inlineActionBtnTextActive]}>예약 선택</Text>
                                                        </Pressable>
                                                    )}
                                                </View>
                                            </Pressable>
                                        ))}
                                    </View>
                                )}
                            </View>

                        {/* 여행 예약 레일 */}
                            <View
                                style={[styles.sectionCard, activeRailSection === 'travel-booking' && styles.sectionCardActive]}
                            >
                                <Text style={styles.sectionTitle}>🧳 여행 예약</Text>
                                <View style={styles.sectionCard}>
                                    <Text style={styles.sectionTitle}>☎ 예약 섹션 일반 통화 모드</Text>
                                    <Text style={styles.sectionSub}>{getFeatureUiText('user.bidirectionalMode')}</Text>
                                    <BidirectionalLanguagePairBadge fromLang={fromLang} toLang={toLang} />
                                    <Pressable style={[styles.interToggleBtn, interCallActive && styles.interToggleBtnActive]} onPress={handleInterCallToggle}>
                                        <Text style={[styles.interToggleText, interCallActive && styles.interToggleTextActive]}>
                                            {interCallActive ? getFeatureUiText('pstn.interToggleEnd') : getFeatureUiText('pstn.interToggleStart')}
                                        </Text>
                                    </Pressable>

                                    <TextInput
                                        style={styles.compactInput}
                                        placeholder="통역 통화 전화번호 (예: 01012345678)"
                                        placeholderTextColor={C.sub}
                                        keyboardType="phone-pad"
                                        value={interCallPhone}
                                        onChangeText={setInterCallPhone}
                                    />
                                    <View style={styles.interCallQuickRow}>
                                        <Pressable
                                            style={styles.inlineGhostBtn}
                                            onPress={() => setShowPhoneDialerModal(true)}
                                            accessibilityLabel="다이얼패드 열기"
                                            testID="worldlinco-phone-dialer-open"
                                        >
                                            <Text style={styles.inlineGhostBtnText}>다이얼패드 열기</Text>
                                        </Pressable>
                                        {interCallPhone ? (
                                            <Pressable style={styles.inlineGhostBtn} onPress={() => setInterCallPhone('')}>
                                                <Text style={styles.inlineGhostBtnText}>전화번호 비우기</Text>
                                            </Pressable>
                                        ) : null}
                                    </View>

                                    {interCallActive && (
                                        <View style={styles.interPanel}>
                                            <BidirectionalLanguagePairBadge fromLang={fromLang} toLang={toLang} compact />
                                            <Text style={styles.interStatus}>{interCallStatus || getFeatureUiText('pstn.callWaiting')}</Text>
                                            {Platform.OS !== 'web' && (
                                                <>
                                                    <Text style={styles.sectionSub}>
                                                        {interCallTurn === 'from'
                                                            ? `👤 ${getFeatureUiText('user.mySpeechInput')}`
                                                            : `🤝 ${getFeatureUiText('user.peerSpeechInput')}`}
                                                    </Text>
                                                    <Pressable
                                                        style={styles.inlineActionBtn}
                                                        onPress={() => { void handleToggleInterCallVoiceAssist(); }}
                                                        accessibilityLabel="worldlinco-inter-call-voice-assist-toggle"
                                                        testID="worldlinco-inter-call-voice-assist-toggle"
                                                    >
                                                        <Text style={styles.inlineActionBtnText}>
                                                            {voiceInputTargetRef.current === 'inter_call' && (isVoiceRecording || voiceSttLoading)
                                                                ? getFeatureUiText('pstn.voiceAssistStop')
                                                                : interCallVoiceAssistEnabled
                                                                    ? getFeatureUiText('pstn.voiceAssistPreparing')
                                                                    : getFeatureUiText('pstn.voiceAssistStart')}
                                                        </Text>
                                                    </Pressable>
                                                    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.railRow}>
                                                        {AUTO_RELAY_DELAY_OPTIONS_MS.map((optionMs) => (
                                                            <Pressable
                                                                key={`inter-auto-relay-${optionMs}`}
                                                                style={[styles.railBtn, autoRelayDelayMs === optionMs && styles.railBtnActive]}
                                                                onPress={() => setAutoRelayDelayMs(optionMs)}
                                                            >
                                                                <Text style={[styles.railBtnText, autoRelayDelayMs === optionMs && styles.railBtnTextActive]}>
                                                                    {formatAutoRelayDelayLabel(optionMs)}
                                                                </Text>
                                                            </Pressable>
                                                        ))}
                                                    </ScrollView>
                                                    <TextInput
                                                        style={[styles.compactInput, styles.noteInput]}
                                                        multiline
                                                        placeholder={getFeatureUiText('pstn.manualInputPlaceholder')}
                                                        placeholderTextColor={C.sub}
                                                        value={interManualText}
                                                        onChangeText={setInterManualText}
                                                    />
                                                    <Pressable
                                                        style={styles.inlineActionBtn}
                                                        onPress={() => relayInterCallManual(interCallTurn, interManualText)}
                                                    >
                                                        <Text style={styles.inlineActionBtnText}>{getFeatureUiText('pstn.sendNow')}</Text>
                                                    </Pressable>
                                                </>
                                            )}

                                            {interCallLog.length > 0 && (
                                                <View style={styles.nearbyListWrap}>
                                                    {[...interCallLog].reverse().map((entry, idx) => {
                                                        const userFlag = resolveUserCountryFlag(userInfo?.country_code, userInfo?.preferred_language);
                                                        const peerFlag = resolveUserCountryFlag(null, toLang);
                                                        const userLabel = formatFlagPrefixedName(userFlag, userInfo?.username || userInfo?.email?.split('@')[0] || getFeatureUiText('user.meSide'));
                                                        const peerLabel = formatFlagPrefixedName(peerFlag, getFeatureUiText('user.peerSide'));
                                                        return (
                                                        <View key={`inter-${idx}`} style={styles.placeItem}>
                                                            <Text style={styles.placeMeta}>
                                                                {entry.turn === 'from' ? userLabel : peerLabel}
                                                            </Text>
                                                            <Text style={styles.placeName}>{entry.text}</Text>
                                                            <Text style={styles.successText}>→ {entry.translated}</Text>
                                                        </View>
                                                        );
                                                    })}
                                                </View>
                                            )}
                                        </View>
                                    )}
                                </View>

                                {!token || !userInfo ? renderSectionConnectionCard({
                                    sectionKey: 'travel-booking',
                                    title: '예약 요청은 계정 연결 후 바로 검증됩니다',
                                    body: '주변 결과는 로그인 없이도 둘러볼 수 있지만, 예약 요청과 결제 흐름은 계정 기반으로 저장됩니다. 로그인 후 실제 계정 기준으로 예약 폼과 결과 카드 검증을 진행해 주세요.',
                                    bullets: ['예약 폼 입력과 요청 전송', '예약 결과 카드 및 지원번호 확인', '동일 계정으로 결제 흐름 이어서 검증'],
                                    loginSource: 'travel_booking_section_gate',
                                }) : null}

                                <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.railRow}>
                                    {nearbyPlaces
                                        .filter((place) => (place.category === 'hotel' || place.category === 'airport') && place.booking_supported)
                                        .map((place) => (
                                            <Pressable
                                                key={`booking-rail-${place.id}`}
                                                style={[styles.hotelRailBtn, selectedBookingPlaceId === place.id && styles.hotelRailBtnActive]}
                                                onPress={() => selectBookingPlace(place.id, '목록')}
                                                accessibilityLabel={`worldlinco-travel-booking-rail-${place.id}`}
                                                testID={`worldlinco-travel-booking-rail-${place.id}`}
                                            >
                                                <Text style={styles.hotelRailName}>{place.name}</Text>
                                                <Text style={styles.hotelRailMeta}>{place.category_label} · {place.price_tier} · ★ {Number(place.rating).toFixed(1)}</Text>
                                            </Pressable>
                                        ))}
                                </ScrollView>

                                {selectedBookingPlace ? (
                                    <View
                                        style={styles.selectedHotelBox}
                                        accessibilityLabel="worldlinco-travel-booking-selected-place"
                                        testID="worldlinco-travel-booking-selected-place"
                                    >
                                        <Text style={styles.selectedHotelName}>{selectedBookingPlace.name}</Text>
                                        <Text style={styles.placeAddr}>{selectedBookingPlace.address}</Text>
                                        <Text style={styles.selectedHotelStatic}>예약 선택 완료 · 예약 폼에 반영됨</Text>
                                        {bookingSelectionNotice ? (
                                            <Text style={styles.selectedHotelNotice}>{bookingSelectionNotice}</Text>
                                        ) : null}
                                        {selectedBookingPlace.phone ? (
                                            <Pressable
                                                style={styles.inlineActionBtn}
                                                onPress={() => { void openDialPad(selectedBookingPlace.phone, 'travel_booking_place_call'); }}
                                                accessibilityLabel={selectedBookingPlace.category === 'airport'
                                                    ? 'worldlinco-travel-booking-airport-call-button'
                                                    : 'worldlinco-travel-booking-hotel-call-button'}
                                                testID={selectedBookingPlace.category === 'airport'
                                                    ? 'worldlinco-travel-booking-airport-call-button'
                                                    : 'worldlinco-travel-booking-hotel-call-button'}
                                            >
                                                <Text style={styles.inlineActionBtnText}>
                                                    {getFeatureUiText(
                                                        selectedBookingPlace.category === 'airport'
                                                            ? 'travel.bookingCallAirport'
                                                            : 'travel.bookingCallHotel',
                                                    )}
                                                </Text>
                                            </Pressable>
                                        ) : null}
                                    </View>
                                ) : null}

                                <TextInput
                                    style={styles.compactInput}
                                    placeholder="예약자명"
                                    placeholderTextColor={C.sub}
                                    value={bookingName}
                                    onChangeText={setBookingName}
                                    accessibilityLabel="worldlinco-travel-booking-name-input"
                                    testID="worldlinco-travel-booking-name-input"
                                />
                                <View style={styles.coordRow}>
                                    <View style={styles.coordField}>
                                        <Text style={styles.coordLabel}>체크인(YYYY-MM-DD)</Text>
                                        <TextInput
                                            style={styles.compactInput}
                                            value={checkinDate}
                                            onChangeText={setCheckinDate}
                                            accessibilityLabel="worldlinco-travel-booking-checkin-input"
                                            testID="worldlinco-travel-booking-checkin-input"
                                        />
                                    </View>
                                    <View style={styles.coordField}>
                                        <Text style={styles.coordLabel}>체크아웃(YYYY-MM-DD)</Text>
                                        <TextInput
                                            style={styles.compactInput}
                                            value={checkoutDate}
                                            onChangeText={setCheckoutDate}
                                            accessibilityLabel="worldlinco-travel-booking-checkout-input"
                                            testID="worldlinco-travel-booking-checkout-input"
                                        />
                                    </View>
                                </View>
                                <View style={styles.coordRow}>
                                    <View style={styles.coordField}>
                                        <Text style={styles.coordLabel}>인원</Text>
                                        <TextInput
                                            style={styles.compactInput}
                                            keyboardType="number-pad"
                                            value={String(guests)}
                                            onChangeText={(v) => setGuests(Math.max(1, Number(v) || 1))}
                                            accessibilityLabel="worldlinco-travel-booking-guests-input"
                                            testID="worldlinco-travel-booking-guests-input"
                                        />
                                    </View>
                                    <View style={styles.coordField}>
                                        <Text style={styles.coordLabel}>객실 수</Text>
                                        <TextInput
                                            style={styles.compactInput}
                                            keyboardType="number-pad"
                                            value={String(roomCount)}
                                            onChangeText={(v) => setRoomCount(Math.max(1, Number(v) || 1))}
                                            accessibilityLabel="worldlinco-travel-booking-roomcount-input"
                                            testID="worldlinco-travel-booking-roomcount-input"
                                        />
                                    </View>
                                </View>
                                <TextInput
                                    style={[styles.compactInput, styles.noteInput]}
                                    multiline
                                    placeholder="추가 요청사항 (예: 금연실, 늦은 체크인)"
                                    placeholderTextColor={C.sub}
                                    value={bookingNote}
                                    onChangeText={setBookingNote}
                                    accessibilityLabel="worldlinco-travel-booking-note-input"
                                    testID="worldlinco-travel-booking-note-input"
                                />

                                <Pressable
                                    style={[styles.translateBtn, (bookingLoading || !selectedBookingPlace) && styles.translateBtnDisabled]}
                                    onPress={handleReserveBooking}
                                    disabled={bookingLoading || !selectedBookingPlace}
                                    accessibilityLabel="worldlinco-travel-booking-submit-button"
                                    testID="worldlinco-travel-booking-submit-button"
                                >
                                    {bookingLoading ? <ActivityIndicator color="#fff" size="small" /> : <Text style={styles.translateBtnText}>예약 요청 보내기</Text>}
                                </Pressable>

                                {bookingError ? <Text style={styles.errorText}>{bookingError}</Text> : null}

                                {bookingResult && (
                                    <View
                                        style={styles.successBox}
                                        accessibilityLabel="worldlinco-travel-booking-result"
                                        testID="worldlinco-travel-booking-result"
                                    >
                                        <Text style={styles.successTitle}>예약 확인번호 {bookingResult.confirmation_id}</Text>
                                        <Text style={styles.successText}>{bookingResult.booking_message}</Text>
                                        <Text style={styles.successText}>{bookingResult.translated_message}</Text>
                                        {bookingResult.support_phone ? (
                                            <Pressable
                                                style={styles.inlineActionBtn}
                                                onPress={() => { void openDialPad(bookingResult.support_phone, 'travel_booking_support_call'); }}
                                                accessibilityLabel="worldlinco-travel-booking-support-call-button"
                                                testID="worldlinco-travel-booking-support-call-button"
                                            >
                                                <Text style={styles.inlineActionBtnText}>{getFeatureUiText('travel.bookingSupportCall')}</Text>
                                            </Pressable>
                                        ) : null}
                                    </View>
                                )}
                            </View>

                        {/* 결제 레일 */}
                        {bookingResult && (
                            <View
                                style={styles.sectionCard}
                                accessibilityLabel="worldlinco-travel-payment-card"
                                testID="worldlinco-travel-payment-card"
                            >
                                <Text style={styles.sectionTitle}>💳 결제</Text>
                                <Text style={styles.sectionSub}>
                                    결제 예정 금액: {(Math.max(1, Math.ceil((new Date(checkoutDate).getTime() - new Date(checkinDate).getTime()) / 86400000)) * roomCount * 80000).toLocaleString('ko-KR')}원
                                </Text>
                                {payError ? <Text style={styles.errorText}>{payError}</Text> : null}
                                {purchaseResult ? (
                                    <View
                                        style={styles.successBox}
                                        accessibilityLabel="worldlinco-travel-payment-result"
                                        testID="worldlinco-travel-payment-result"
                                    >
                                        <Text style={styles.successTitle}>구매 ID: {purchaseResult.id} · 상태: {purchaseResult.status}</Text>
                                        {payUrl ? (
                                            <Pressable
                                                style={styles.inlineActionBtn}
                                                onPress={() => Linking.openURL(payUrl)}
                                                accessibilityLabel="worldlinco-travel-payment-open-url-button"
                                                testID="worldlinco-travel-payment-open-url-button"
                                            >
                                                <Text style={styles.inlineActionBtnText}>결제 페이지 열기</Text>
                                            </Pressable>
                                        ) : (
                                            <Text style={styles.sectionSub}>결제 URL을 불러오는 중...</Text>
                                        )}
                                    </View>
                                ) : (
                                    <Pressable
                                        style={[styles.translateBtn, (!token || payLoading) && styles.translateBtnDisabled]}
                                        onPress={handlePayment}
                                        disabled={!token || payLoading}
                                        accessibilityLabel="worldlinco-travel-payment-submit-button"
                                        testID="worldlinco-travel-payment-submit-button"
                                    >
                                        {payLoading ? <ActivityIndicator color="#fff" size="small" /> : <Text style={styles.translateBtnText}>{token ? '결제 진행하기' : '로그인 후 결제'}</Text>}
                                    </Pressable>
                                )}
                            </View>
                        )}

        </>
    );
}
