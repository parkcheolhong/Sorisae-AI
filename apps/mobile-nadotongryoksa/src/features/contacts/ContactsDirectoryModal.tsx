// 단말 전화번호부 디렉터리 모달.
// - 사용자 휴대폰에 저장된 연락처 전체를 불러와(loadDeviceContacts) 검색 가능한 목록으로 보여준다.
// - 각 연락처에서 [📞 일반전화 통역 / 📡 VoIP / 💬 채팅] 3개 채널로 바로 연결한다.
// - VoIP/채팅은 번호가 앱 친구(가입자)와 일치할 때 활성화되고, 미가입이면 채팅은 SNS 초대로 폴백한다.
// - 일반전화 통역은 가입 여부와 무관하게 단말 전화앱 다이얼+자동 통역으로 항상 가능하다.
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
    ActivityIndicator,
    FlatList,
    Linking,
    Modal,
    Pressable,
    StyleSheet,
    Text,
    TextInput,
    View,
} from 'react-native';

import { loadDeviceContacts, type DeviceContact } from '../../services/deviceContacts';
import { buildFriendPhoneIndex, matchFriendByPhones } from './contactFriendMatch';
import { shareAppPromotion } from '../sns-share/snsShare';
import type { Friend } from '../friends/types';

export interface ContactsDirectoryModalProps {
    visible: boolean;
    onClose: () => void;
    // [인라인] true면 모달 오버레이 없이 섹션 안에 바로 렌더한다(통화 섹션 임베드용).
    embedded?: boolean;
    // 설치/홍보 링크 생성을 위한 API base(미지정 시 링크 생략).
    apiBase?: string | null;
    // 홍보 공유 카피에 표시할 추천인 이름(선택).
    inviterName?: string | null;
    // 친구(가입자) 목록 로더. 미로그인/실패 시 빈 배열을 반환하면 된다.
    loadFriends: () => Promise<Friend[]>;
    // 📞 일반전화 통역: 단말 전화앱으로 발신 + 자동 통역 보조 시작.
    onRegularCall: (contact: DeviceContact) => void;
    // 📡 VoIP: 앱 친구일 때만 호출된다.
    onVoipCall: (contact: DeviceContact, friend: Friend) => void;
    // 💬 채팅: 친구면 friend 전달(채팅방), 미가입이면 null(SNS 초대).
    onChat: (contact: DeviceContact, friend: Friend | null) => void;
}

function digitsOnly(value: string): string {
    return value.replace(/\D/g, '');
}

export function ContactsDirectoryModal({
    visible,
    onClose,
    embedded = false,
    apiBase,
    inviterName,
    loadFriends,
    onRegularCall,
    onVoipCall,
    onChat,
}: ContactsDirectoryModalProps) {
    const [contacts, setContacts] = useState<DeviceContact[]>([]);
    const [friendIndex, setFriendIndex] = useState<Map<string, Friend>>(new Map());
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [query, setQuery] = useState('');
    // [인라인 접기] 통화 탭 임베드 시 섹션 전체 접기/펼치기(목록 스크롤 위치 유지).
    const [sectionExpanded, setSectionExpanded] = useState(true);
    // [네이티브 전화앱식] 연락처를 탭하면 그 행만 펼쳐 [전화·문자·통역통화·채팅] 액션을 노출한다.
    const [expandedId, setExpandedId] = useState<string | null>(null);

    const load = useCallback(async (force: boolean) => {
        setLoading(true);
        setError('');
        try {
            const [list, friends] = await Promise.all([
                loadDeviceContacts(force),
                loadFriends().catch(() => [] as Friend[]),
            ]);
            setContacts(list);
            setFriendIndex(buildFriendPhoneIndex(friends));
            if (list.length === 0) {
                setError('단말에 저장된 연락처를 찾지 못했습니다. 연락처 권한을 허용했는지 확인해 주세요.');
            }
        } catch (e: any) {
            setError(e?.message || '연락처를 불러오지 못했습니다.');
        } finally {
            setLoading(false);
        }
    }, [loadFriends]);

    useEffect(() => {
        if (embedded || visible) {
            void load(false);
        } else {
            setQuery('');
            setExpandedId(null);
        }
    }, [embedded, visible, load]);

    // 💬 문자(SMS) — 단말 메시지 앱을 연다(가입 여부 무관, 모든 연락처 공통).
    const handleSms = useCallback((contact: DeviceContact) => {
        const num = digitsOnly(contact.phone);
        if (!num) {
            return;
        }
        Linking.openURL(`sms:${num}`).catch(() => { /* 메시지 앱 없음/거부 시 무시 */ });
    }, []);

    const filtered = useMemo(() => {
        const q = query.trim().toLowerCase();
        if (!q) {
            return contacts;
        }
        const qDigits = digitsOnly(q);
        return contacts.filter((c) => {
            if (c.name.toLowerCase().includes(q)) {
                return true;
            }
            if (qDigits && digitsOnly(c.phone).includes(qDigits)) {
                return true;
            }
            return qDigits ? c.keys.some((k) => k.includes(qDigits)) : false;
        });
    }, [contacts, query]);

    const renderRow = useCallback(({ item }: { item: DeviceContact }) => {
        const friend = matchFriendByPhones(friendIndex, [item.phone, ...item.keys]);
        const isAppUser = Boolean(friend && friend.friendUserId != null);
        const expanded = expandedId === item.id;
        return (
            <View style={styles.row} testID={`contacts-dir-row-${item.id}`}>
                {/* [네이티브 전화앱식] 행 탭 → 그 연락처만 펼쳐 액션 노출. 다시 탭하면 접힘. */}
                <Pressable
                    style={styles.rowHead}
                    onPress={() => setExpandedId((prev) => (prev === item.id ? null : item.id))}
                    accessibilityRole="button"
                    accessibilityLabel={`${item.name} ${expanded ? '닫기' : '열기'}`}
                    testID={`contacts-dir-head-${item.id}`}
                >
                    <View style={styles.rowInfo}>
                        <View style={styles.nameRow}>
                            <Text style={styles.name} numberOfLines={1}>{item.name}</Text>
                            {isAppUser ? <Text style={styles.appBadge}>앱 친구</Text> : null}
                        </View>
                        <Text style={styles.phone} numberOfLines={1}>{item.phone}</Text>
                    </View>
                    <Text style={styles.rowChevron}>{expanded ? '▾' : '›'}</Text>
                </Pressable>
                {expanded ? (
                    <View style={styles.actions}>
                        {/* 모든 연락처 공통: [📞 전화 · 💬 문자]. 앱 친구면 [📡 통역통화 · 💬 채팅] 추가. */}
                        <Pressable
                            style={[styles.actionBtn, styles.callBtn]}
                            onPress={() => onRegularCall(item)}
                            accessibilityLabel={`${item.name} 전화`}
                            testID={`contacts-dir-call-${item.id}`}
                        >
                            <Text style={styles.actionText}>📞 전화</Text>
                        </Pressable>
                        <Pressable
                            style={[styles.actionBtn, styles.smsBtn]}
                            onPress={() => handleSms(item)}
                            accessibilityLabel={`${item.name} 문자`}
                            testID={`contacts-dir-sms-${item.id}`}
                        >
                            <Text style={styles.actionText}>💬 문자</Text>
                        </Pressable>
                        {isAppUser && friend ? (
                            <Pressable
                                style={[styles.actionBtn, styles.voipBtn]}
                                onPress={() => onVoipCall(item, friend)}
                                accessibilityLabel={`${item.name} 통역통화 VoIP`}
                                testID={`contacts-dir-voip-${item.id}`}
                            >
                                <Text style={styles.actionText}>📡 통역통화</Text>
                            </Pressable>
                        ) : null}
                        <Pressable
                            style={[styles.actionBtn, styles.chatBtn]}
                            onPress={() => onChat(item, friend)}
                            accessibilityLabel={`${item.name} 채팅`}
                            testID={`contacts-dir-chat-${item.id}`}
                        >
                            <Text style={styles.actionText}>{isAppUser ? '💬 채팅' : '💬 초대'}</Text>
                        </Pressable>
                    </View>
                ) : null}
            </View>
        );
    }, [friendIndex, expandedId, handleSms, onRegularCall, onVoipCall, onChat]);

    const body = (
        <>
            {embedded ? (
                <Pressable
                    style={styles.sectionHead}
                    onPress={() => setSectionExpanded((prev) => !prev)}
                    accessibilityRole="button"
                    accessibilityLabel={sectionExpanded ? '연락처에서 바로 연결 접기' : '연락처에서 바로 연결 펼치기'}
                    testID="contacts-dir-section-toggle"
                >
                    <View style={styles.sectionHeadText}>
                        <Text style={styles.title}>📇 연락처에서 바로 연결</Text>
                        {!sectionExpanded ? (
                            <Text style={styles.sectionCollapsedMeta}>{filtered.length}명 · 탭하여 펼치기</Text>
                        ) : null}
                    </View>
                    <Text style={styles.sectionChevron}>{sectionExpanded ? '▾' : '›'}</Text>
                </Pressable>
            ) : (
                <Text style={styles.title}>📇 연락처에서 바로 연결</Text>
            )}
            <View style={[embedded && !sectionExpanded && styles.sectionBodyCollapsed]} pointerEvents={embedded && !sectionExpanded ? 'none' : 'auto'}>
                    <TextInput
                        style={styles.search}
                        placeholder="이름 또는 번호 검색"
                        placeholderTextColor="#8a93a3"
                        value={query}
                        onChangeText={setQuery}
                        testID="contacts-dir-search"
                    />
                    {error ? <Text style={styles.error}>{error}</Text> : null}
                    {loading && contacts.length === 0 ? (
                        <View style={styles.loadingBox}>
                            <ActivityIndicator color="#1e6fe0" />
                            <Text style={styles.loadingText}>연락처를 불러오는 중...</Text>
                        </View>
                    ) : (
                        <FlatList
                            style={[styles.list, embedded && styles.listEmbedded]}
                            data={filtered}
                            keyExtractor={(item) => `contact-dir-${item.id}`}
                            renderItem={renderRow}
                            keyboardShouldPersistTaps="handled"
                            initialNumToRender={20}
                            nestedScrollEnabled
                            ListEmptyComponent={
                                <Text style={styles.empty}>
                                    {query.trim() ? '검색 결과가 없습니다.' : '표시할 연락처가 없습니다.'}
                                </Text>
                            }
                        />
                    )}
                    <Pressable
                        style={styles.promoBtn}
                        onPress={() => { void shareAppPromotion({ apiBase, inviterName }); }}
                        testID="contacts-dir-promote"
                    >
                        <Text style={styles.promoBtnText}>📣 앱 홍보 공유 (카카오톡·라인·SNS·문자)</Text>
                    </Pressable>
                    <View style={styles.footer}>
                        <Text style={styles.count}>{filtered.length}명</Text>
                        <View style={styles.footerBtns}>
                            <Pressable style={styles.ghostBtn} onPress={() => { void load(true); }} testID="contacts-dir-refresh">
                                <Text style={styles.ghostBtnText}>{loading ? '새로고침 중...' : '다시 불러오기'}</Text>
                            </Pressable>
                            {!embedded ? (
                                <Pressable style={styles.closeBtn} onPress={onClose} testID="contacts-dir-close">
                                    <Text style={styles.closeBtnText}>닫기</Text>
                                </Pressable>
                            ) : null}
                        </View>
                    </View>
            </View>
        </>
    );

    // [인라인] 통화 섹션 안에 모달 오버레이 없이 그대로 렌더한다.
    if (embedded) {
        return <View style={styles.embeddedCard}>{body}</View>;
    }

    return (
        <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
            <View style={styles.overlay}>
                <View style={styles.card}>{body}</View>
            </View>
        </Modal>
    );
}

const styles = StyleSheet.create({
    overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'center', alignItems: 'center', padding: 16 },
    card: { width: '100%', maxWidth: 520, maxHeight: '86%', backgroundColor: '#ffffff', borderRadius: 16, padding: 16, borderWidth: 1, borderColor: '#dce6f2' },
    title: { color: '#0b2e5e', fontSize: 17, fontWeight: '800', marginBottom: 6 },
    hint: { color: '#5f6b80', fontSize: 12, lineHeight: 17, marginBottom: 10 },
    search: { backgroundColor: '#f4f9ff', borderWidth: 1, borderColor: '#dce6f2', borderRadius: 10, color: '#1a1f36', paddingHorizontal: 12, paddingVertical: 9, fontSize: 14 },
    error: { color: '#e5484d', fontSize: 12, marginTop: 8 },
    loadingBox: { paddingVertical: 28, alignItems: 'center', gap: 8 },
    loadingText: { color: '#5f6b80', fontSize: 13 },
    embeddedCard: { backgroundColor: '#ffffff', borderRadius: 14, padding: 12, borderWidth: 1, borderColor: '#dce6f2', marginTop: 4 },
    sectionHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 },
    sectionHeadText: { flex: 1, paddingRight: 8 },
    sectionChevron: { color: '#8a93a3', fontSize: 18, fontWeight: '700' },
    sectionCollapsedMeta: { color: '#5f6b80', fontSize: 12, marginTop: 2 },
    sectionBodyCollapsed: { height: 0, overflow: 'hidden', opacity: 0 },
    list: { marginTop: 10, flexGrow: 0 },
    listEmbedded: { maxHeight: 360 },
    row: { borderBottomWidth: 1, borderBottomColor: '#e3eaf5' },
    rowHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 12 },
    rowChevron: { color: '#8a93a3', fontSize: 18, fontWeight: '700', paddingLeft: 8 },
    rowInfo: { flexShrink: 1 },
    nameRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
    name: { color: '#1a1f36', fontSize: 15, fontWeight: '700', flexShrink: 1 },
    appBadge: { color: '#ffffff', backgroundColor: '#1e6fe0', fontSize: 10, fontWeight: '800', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6, overflow: 'hidden' },
    phone: { color: '#5f6b80', fontSize: 12, marginTop: 2 },
    actions: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, paddingBottom: 12 },
    actionBtn: { flexGrow: 1, flexBasis: '47%', paddingVertical: 11, borderRadius: 9, alignItems: 'center', justifyContent: 'center' },
    callBtn: { backgroundColor: '#19a463' },
    smsBtn: { backgroundColor: '#1e6fe0' },
    voipBtn: { backgroundColor: '#2563eb' },
    chatBtn: { backgroundColor: '#7c3aed' },
    actionBtnDisabled: { backgroundColor: '#e3eaf5' },
    actionText: { color: '#fff', fontSize: 12, fontWeight: '700' },
    actionTextDisabled: { color: '#8a93a3' },
    empty: { color: '#8a93a3', fontSize: 13, textAlign: 'center', paddingVertical: 24 },
    promoBtn: { marginTop: 12, paddingVertical: 11, borderRadius: 10, backgroundColor: '#e6f7ef', borderWidth: 1, borderColor: '#19c37d', alignItems: 'center' },
    promoBtnText: { color: '#1f9d57', fontSize: 13, fontWeight: '800' },
    footer: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 12 },
    count: { color: '#8a93a3', fontSize: 12 },
    footerBtns: { flexDirection: 'row', gap: 8 },
    ghostBtn: { paddingVertical: 9, paddingHorizontal: 14, borderRadius: 9, borderWidth: 1, borderColor: '#bcd3f0' },
    ghostBtnText: { color: '#1e6fe0', fontSize: 13, fontWeight: '700' },
    closeBtn: { paddingVertical: 9, paddingHorizontal: 18, borderRadius: 9, backgroundColor: '#e8f1ff' },
    closeBtnText: { color: '#1e6fe0', fontSize: 13, fontWeight: '700' },
});
