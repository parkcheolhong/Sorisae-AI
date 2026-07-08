// 단말 전화번호부 디렉터리 모달.
// - 사용자 휴대폰에 저장된 연락처 전체를 불러와(loadDeviceContacts) 검색 가능한 목록으로 보여준다.
// - 각 연락처에서 [📞 일반전화 통역 / 📡 VoIP / 💬 채팅] 3개 채널로 바로 연결한다.
// - VoIP/채팅은 번호가 앱 친구(가입자)와 일치할 때 활성화되고, 미가입이면 채팅은 SNS 초대로 폴백한다.
// - 일반전화 통역은 가입 여부와 무관하게 단말 전화앱 다이얼+자동 통역으로 항상 가능하다.
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
    ActivityIndicator,
    FlatList,
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
        if (visible) {
            void load(false);
        } else {
            setQuery('');
        }
    }, [visible, load]);

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
        return (
            <View style={styles.row} testID={`contacts-dir-row-${item.id}`}>
                <View style={styles.rowInfo}>
                    <View style={styles.nameRow}>
                        <Text style={styles.name} numberOfLines={1}>{item.name}</Text>
                        {isAppUser ? <Text style={styles.appBadge}>앱 친구</Text> : null}
                    </View>
                    <Text style={styles.phone} numberOfLines={1}>{item.phone}</Text>
                </View>
                <View style={styles.actions}>
                    {/* [버그 수정] 라벨 정합: 통역 VoIP 와 일반전화(PSTN)를 명확히 구분한다.
                        과거엔 PSTN 버튼이 '📞 통역통화'로 표기돼, '통역통화 걸기' 의도가 셀룰러 일반전화로 새는
                        문제가 있었다. → '통역통화(VoIP)'를 앱 친구의 주동작으로, PSTN 은 '일반전화'로 명시. */}
                    <Pressable
                        style={[styles.actionBtn, isAppUser ? styles.voipBtn : styles.actionBtnDisabled]}
                        onPress={() => { if (isAppUser && friend) { onVoipCall(item, friend); } }}
                        disabled={!isAppUser}
                        accessibilityLabel={`${item.name} 통역통화 VoIP`}
                        testID={`contacts-dir-voip-${item.id}`}
                    >
                        <Text style={[styles.actionText, !isAppUser && styles.actionTextDisabled]}>📡 통역통화(VoIP)</Text>
                    </Pressable>
                    <Pressable
                        style={[styles.actionBtn, styles.callBtn]}
                        onPress={() => onRegularCall(item)}
                        accessibilityLabel={`${item.name} 일반전화(PSTN)`}
                        testID={`contacts-dir-call-${item.id}`}
                    >
                        <Text style={styles.actionText}>📞 일반전화</Text>
                    </Pressable>
                    <Pressable
                        style={[styles.actionBtn, styles.chatBtn]}
                        onPress={() => onChat(item, friend)}
                        accessibilityLabel={`${item.name} 채팅`}
                        testID={`contacts-dir-chat-${item.id}`}
                    >
                        <Text style={styles.actionText}>{isAppUser ? '💬 채팅' : '💬 초대'}</Text>
                    </Pressable>
                </View>
            </View>
        );
    }, [friendIndex, onRegularCall, onVoipCall, onChat]);

    return (
        <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
            <View style={styles.overlay}>
                <View style={styles.card}>
                    <Text style={styles.title}>📇 연락처 연동</Text>
                    <Text style={styles.hint}>
                        휴대폰에 저장된 연락처에서 통역통화(VoIP) · 일반전화 · 채팅으로 바로 연결합니다.
                        통역통화(VoIP)와 채팅은 상대가 앱 가입자일 때 활성화되고, 미가입이면 일반전화(셀룰러)로 연결하거나 채팅은 초대로 이어집니다.
                    </Text>
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
                            style={styles.list}
                            data={filtered}
                            keyExtractor={(item) => `contact-dir-${item.id}`}
                            renderItem={renderRow}
                            keyboardShouldPersistTaps="handled"
                            initialNumToRender={20}
                            ListEmptyComponent={
                                <Text style={styles.empty}>
                                    {query.trim() ? '검색 결과가 없습니다.' : '표시할 연락처가 없습니다.'}
                                </Text>
                            }
                        />
                    )}
                    <Pressable
                        style={styles.promoBtn}
                        onPress={() => {
                            shareAppPromotion({ apiBase, inviterName }).catch((error) => {
                                console.warn('[CONTACTS_DIR] promo share failed', error);
                            });
                        }}
                        testID="contacts-dir-promote"
                    >
                        <Text style={styles.promoBtnText}>📣 앱 홍보 공유 (카카오톡·라인·SNS·문자)</Text>
                    </Pressable>
                    <View style={styles.footer}>
                        <Text style={styles.count}>{filtered.length}명</Text>
                        <View style={styles.footerBtns}>
                            <Pressable
                                style={styles.ghostBtn}
                                onPress={() => {
                                    load(true).catch((error) => {
                                        console.warn('[CONTACTS_DIR] refresh failed', error);
                                    });
                                }}
                                testID="contacts-dir-refresh"
                            >
                                <Text style={styles.ghostBtnText}>{loading ? '새로고침 중...' : '다시 불러오기'}</Text>
                            </Pressable>
                            <Pressable style={styles.closeBtn} onPress={onClose} testID="contacts-dir-close">
                                <Text style={styles.closeBtnText}>닫기</Text>
                            </Pressable>
                        </View>
                    </View>
                </View>
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
    list: { marginTop: 10, flexGrow: 0 },
    row: { paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#e3eaf5' },
    rowInfo: { marginBottom: 8 },
    nameRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
    name: { color: '#1a1f36', fontSize: 15, fontWeight: '700', flexShrink: 1 },
    appBadge: { color: '#ffffff', backgroundColor: '#1e6fe0', fontSize: 10, fontWeight: '800', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6, overflow: 'hidden' },
    phone: { color: '#5f6b80', fontSize: 12, marginTop: 2 },
    actions: { flexDirection: 'row', gap: 8 },
    actionBtn: { flex: 1, paddingVertical: 9, borderRadius: 9, alignItems: 'center', justifyContent: 'center' },
    callBtn: { backgroundColor: '#19a463' },
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
