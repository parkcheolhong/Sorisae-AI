// 데이터 출처/라이선스 고지 화면.
// 소리새 AI 관광 기능(장소·지도·일정·축제·음식)이 사용하는 오픈데이터의 출처와 라이선스를
// 사용자에게 투명하게 고지한다. OSM(ODbL)·Wikidata(CC0) 등 share-alike/저작자표시 의무 이행.
import React from 'react';
import {
    Linking,
    Modal,
    Pressable,
    ScrollView,
    StyleSheet,
    Text,
    View,
} from 'react-native';

type DataSourcesModalProps = {
    visible: boolean;
    onClose: () => void;
};

const C = {
    panel: '#151b23',
    border: '#21262d',
    text: '#e6edf3',
    sub: '#8b949e',
    accent: '#2a7cff',
    link: '#79c0ff',
    chip: '#0d2236',
};

type SourceItem = {
    title: string;
    license: string;
    usage: string;
    url: string;
};

const SOURCES: SourceItem[] = [
    {
        title: 'OpenStreetMap (지도 타일 · 장소 POI)',
        license: 'ODbL 1.0 (© OpenStreetMap contributors)',
        usage: '지도 배경 타일, 주변 장소·일정의 이름·주소·좌표.',
        url: 'https://www.openstreetmap.org/copyright',
    },
    {
        title: 'Nominatim (OSM 지오코딩/검색)',
        license: 'ODbL 1.0 (© OpenStreetMap contributors)',
        usage: '위치명 → 좌표 변환 및 실시간 장소 검색 보강.',
        url: 'https://nominatim.org/',
    },
    {
        title: 'Wikidata (장소 정보 보강)',
        license: 'CC0 1.0 (퍼블릭 도메인)',
        usage: '관광 명소 분류·설명 등 POI 메타데이터 보강.',
        url: 'https://www.wikidata.org/wiki/Wikidata:Licensing',
    },
    {
        title: '도시 지식그래프 (축제 · 향토 음식)',
        license: '공개 사실 큐레이션 (public knowledge)',
        usage: '도시별 대표 축제·향토 음식 안내. 일반에 널리 알려진 공개 사실만 수록.',
        url: 'https://www.openstreetmap.org/copyright',
    },
];

export function DataSourcesModal({ visible, onClose }: DataSourcesModalProps) {
    const open = (url: string) => {
        void Linking.openURL(url);
    };

    return (
        <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
            <View style={styles.overlay}>
                <View
                    style={styles.panel}
                    accessibilityLabel="worldlinco-data-sources-modal"
                    testID="worldlinco-data-sources-modal"
                >
                    <Text style={styles.title}>데이터 출처 · 라이선스</Text>
                    <Text style={styles.intro}>
                        소리새 AI 관광 기능은 상업·음성(TTS)·저장·학습이 허용된 오픈데이터만 사용합니다.
                        Google·Kakao·TripAdvisor 등 제약이 있는 콘텐츠는 적재·학습에 포함하지 않습니다.
                    </Text>

                    <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollBody}>
                        {SOURCES.map((s, idx) => (
                            <View key={idx} style={styles.card}>
                                <Text style={styles.cardTitle}>{s.title}</Text>
                                <View style={styles.licenseChip}>
                                    <Text style={styles.licenseText}>{s.license}</Text>
                                </View>
                                <Text style={styles.usage}>{s.usage}</Text>
                                <Pressable
                                    onPress={() => open(s.url)}
                                    accessibilityLabel={`worldlinco-data-source-link-${idx}`}
                                    testID={`worldlinco-data-source-link-${idx}`}
                                >
                                    <Text style={styles.link}>{s.url}</Text>
                                </Pressable>
                            </View>
                        ))}

                        <Text style={styles.note}>
                            ODbL는 share-alike(동일조건변경허락) 라이선스입니다. 본 앱은 파생 데이터베이스를
                            외부에 배포하지 않으며, 향후 데이터셋을 공개할 경우 ODbL 조건을 준수합니다.
                        </Text>

                        <View style={styles.privacyCard}>
                            <Text style={styles.privacyTitle}>개인정보 처리 (요약)</Text>
                            <Text style={styles.privacyItem}>• 위치·검색어는 추천 처리에만 사용하며 서버에 저장하지 않습니다(요청 범위 처리).</Text>
                            <Text style={styles.privacyItem}>• 운영 로그에는 정밀 좌표·발화 원문을 남기지 않습니다(좌표는 거칠게, 발화는 길이·지문만).</Text>
                            <Text style={styles.privacyItem}>• 정밀 위치(좌표)는 사용자가 동의한 경우에만 전송되며, 동의는 일정 패널에서 언제든 변경할 수 있습니다.</Text>
                            <Text style={styles.privacyItem}>• 외부 실시간 API 응답은 약관이 정한 기한 내에서만 캐시합니다(Google 위경도 ≤ 30일).</Text>
                        </View>

                        <View style={styles.privacyCard}>
                            <Text style={styles.privacyTitle}>사진·동영상 저작권 (요약)</Text>
                            <Text style={styles.privacyItem}>• 현재 화면은 지도·텍스트만 표시하며 사진·동영상을 직접 게시하지 않습니다.</Text>
                            <Text style={styles.privacyItem}>• 향후 이미지 도입 시 CC0/퍼블릭도메인·CC-BY(상업허용)·자체보유 자료만 노출합니다.</Text>
                            <Text style={styles.privacyItem}>• 라이선스를 알 수 없거나 비상업(NC) 조건이면 표시하지 않습니다(차단).</Text>
                            <Text style={styles.privacyItem}>• CC-BY 등 표기 의무가 있는 자료는 저작자·라이선스 출처를 함께 표시합니다.</Text>
                        </View>
                    </ScrollView>

                    <Pressable style={styles.closeBtn} onPress={onClose} testID="worldlinco-data-sources-close">
                        <Text style={styles.closeBtnText}>닫기</Text>
                    </Pressable>
                </View>
            </View>
        </Modal>
    );
}

const styles = StyleSheet.create({
    overlay: {
        flex: 1,
        backgroundColor: 'rgba(0,0,0,0.72)',
        justifyContent: 'center',
        padding: 20,
    },
    panel: {
        backgroundColor: C.panel,
        borderRadius: 16,
        borderWidth: 1,
        borderColor: C.border,
        padding: 20,
        maxHeight: '86%',
        gap: 10,
    },
    title: { color: C.text, fontSize: 18, fontWeight: '800' },
    intro: { color: C.sub, fontSize: 13, lineHeight: 19 },
    scroll: { marginTop: 4 },
    scrollBody: { gap: 12, paddingBottom: 4 },
    card: {
        backgroundColor: '#0b1622',
        borderRadius: 12,
        borderWidth: 1,
        borderColor: C.border,
        padding: 12,
        gap: 6,
    },
    cardTitle: { color: C.text, fontSize: 14, fontWeight: '700' },
    licenseChip: {
        alignSelf: 'flex-start',
        backgroundColor: C.chip,
        borderRadius: 999,
        paddingHorizontal: 10,
        paddingVertical: 4,
    },
    licenseText: { color: C.link, fontSize: 11, fontWeight: '700' },
    usage: { color: C.sub, fontSize: 12, lineHeight: 17 },
    link: { color: C.link, fontSize: 12, textDecorationLine: 'underline' },
    note: { color: C.sub, fontSize: 12, lineHeight: 18, marginTop: 2 },
    privacyCard: {
        backgroundColor: '#0b1622',
        borderRadius: 12,
        borderWidth: 1,
        borderColor: C.border,
        padding: 12,
        gap: 6,
        marginTop: 2,
    },
    privacyTitle: { color: C.text, fontSize: 14, fontWeight: '700' },
    privacyItem: { color: C.sub, fontSize: 12, lineHeight: 17 },
    closeBtn: { alignSelf: 'flex-end', paddingVertical: 6 },
    closeBtnText: { color: C.sub, fontWeight: '700' },
});
