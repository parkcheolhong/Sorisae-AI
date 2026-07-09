/**
 * 앱 가입 친구(VoIP) 목록 — 연락처 모달과 동일한 [통역통화 · 채팅] 액션 패턴.
 */
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

import { getFriends } from '../../api/friends';
import type { Friend } from './types';

export interface VoipFriendsDirectoryModalProps {
    visible: boolean;
    onClose: () => void;
    /** 통화 레일 연락처 탭에 인라인 삽입(모달 오버레이 없음). */
    embedded?: boolean;
    userId: number;
    token: string;
    onVoipCall: (friend: Friend) => void;
    onChat: (friend: Friend) => void;
    onInvite?: (friend: Friend) => void;
}

export function VoipFriendsDirectoryModal({
    visible,
    onClose,
    embedded = false,
    userId,
    token,
    onVoipCall,
    onChat,
    onInvite,
}: VoipFriendsDirectoryModalProps) {
    const [friends, setFriends] = useState<Friend[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [query, setQuery] = useState('');
    const [sectionExpanded, setSectionExpanded] = useState(true);
    const [expandedId, setExpandedId] = useState<number | null>(null);

    const load = useCallback(async () => {
        if (!token.trim()) {
            return;
        }
        setLoading(true);
        setError('');
        try {
            const data = await getFriends(userId, token);
            setFriends(data.friends.filter((f) => f.friendUserId != null));
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : '친구 목록을 불러오지 못했습니다.');
        } finally {
            setLoading(false);
        }
    }, [token, userId]);

    useEffect(() => {
        if (embedded || visible) {
            void load();
        } else {
            setQuery('');
            setExpandedId(null);
        }
    }, [embedded, visible, load]);

    const filtered = useMemo(() => {
        const q = query.trim().toLowerCase();
        if (!q) {
            return friends;
        }
        return friends.filter((f) => {
            const hay = [
                f.friendUsername,
                f.friendEmail,
                f.friendPhone,
                f.friendVoiceId,
            ]
                .filter(Boolean)
                .join(' ')
                .toLowerCase();
            return hay.includes(q);
        });
    }, [friends, query]);

    const renderRow = useCallback(({ item }: { item: Friend }) => {
        const canVoip = Boolean(item.friendUserId || item.friendVoiceId);
        const canChat = Boolean(item.friendUserId);
        const expanded = expandedId === item.id;
        const label = item.friendUsername || item.friendEmail.split('@')[0];
        return (
            <View style={styles.row}>
                <Pressable
                    style={styles.rowHead}
                    onPress={() => setExpandedId((prev) => (prev === item.id ? null : item.id))}
                    accessibilityRole="button"
                    accessibilityLabel={`${label} ${expanded ? '닫기' : '열기'}`}
                >
                    <View style={styles.rowInfo}>
                        <View style={styles.nameRow}>
                            <Text style={styles.flag}>{item.friendCountryFlag || '🌐'}</Text>
                            <Text style={styles.name} numberOfLines={1}>{label}</Text>
                            <Text style={styles.appBadge}>앱 친구</Text>
                        </View>
                        <Text style={styles.meta} numberOfLines={1}>
                            {item.friendPreferredLanguage?.toUpperCase() || '언어 미설정'}
                            {item.friendVoiceId ? ` · ${item.friendVoiceId}` : ''}
                        </Text>
                    </View>
                    <Text style={styles.chevron}>{expanded ? '▾' : '›'}</Text>
                </Pressable>
                {expanded ? (
                    <View style={styles.actions}>
                        <Pressable
                            style={[styles.actionBtn, styles.voipBtn, !canVoip && styles.actionDisabled]}
                            disabled={!canVoip}
                            onPress={() => onVoipCall(item)}
                        >
                            <Text style={styles.actionText}>📡 통역통화</Text>
                        </Pressable>
                        <Pressable
                            style={[styles.actionBtn, styles.chatBtn, !canChat && styles.actionDisabled]}
                            disabled={!canChat}
                            onPress={() => onChat(item)}
                        >
                            <Text style={styles.actionText}>💬 채팅</Text>
                        </Pressable>
                        {onInvite ? (
                            <Pressable
                                style={[styles.actionBtn, styles.inviteBtn]}
                                onPress={() => onInvite(item)}
                            >
                                <Text style={styles.actionText}>💬 초대</Text>
                            </Pressable>
                        ) : null}
                    </View>
                ) : null}
            </View>
        );
    }, [expandedId, onChat, onInvite, onVoipCall]);

    const body = (
        <>
            {embedded ? (
                <Pressable
                    style={styles.sectionHead}
                    onPress={() => setSectionExpanded((prev) => !prev)}
                    accessibilityRole="button"
                    accessibilityLabel={sectionExpanded ? 'VoIP 친구 통역통화 접기' : 'VoIP 친구 통역통화 펼치기'}
                    testID="voip-friends-dir-section-toggle"
                >
                    <View style={styles.sectionHeadText}>
                        <Text style={styles.title}>📡 VoIP 친구 — 통역통화</Text>
                        {!sectionExpanded ? (
                            <Text style={styles.sectionCollapsedMeta}>{filtered.length}명 · 탭하여 펼치기</Text>
                        ) : (
                            <Text style={styles.hint}>앱 가입 친구 보이스톡 · 단말 연락처와 별도</Text>
                        )}
                    </View>
                    <Text style={styles.sectionChevron}>{sectionExpanded ? '▾' : '›'}</Text>
                </Pressable>
            ) : (
                <>
                    <Text style={styles.title}>📡 VoIP 친구 — 통역통화</Text>
                    <Text style={styles.hint}>앱에 가입한 친구에게 보이스톡을 걸 수 있습니다. 단말 연락처와 별도 목록입니다.</Text>
                </>
            )}
            <View style={[embedded && !sectionExpanded && styles.sectionBodyCollapsed]} pointerEvents={embedded && !sectionExpanded ? 'none' : 'auto'}>
            {embedded && sectionExpanded ? (
                <Text style={styles.hint}>앱 가입 친구 보이스톡 · 단말 연락처와 별도</Text>
            ) : null}
            <TextInput
                style={styles.search}
                placeholder="이름 · 이메일 · 보이스 ID 검색"
                placeholderTextColor="#8a93a3"
                value={query}
                onChangeText={setQuery}
            />
            {error ? <Text style={styles.error}>{error}</Text> : null}
            {loading && friends.length === 0 ? (
                <View style={styles.loadingBox}>
                    <ActivityIndicator color="#1e6fe0" />
                    <Text style={styles.loadingText}>친구 목록 불러오는 중...</Text>
                </View>
            ) : (
                <FlatList
                    style={[styles.list, embedded && styles.listEmbedded]}
                    data={filtered}
                    keyExtractor={(item) => `voip-friend-${item.id}`}
                    renderItem={renderRow}
                    keyboardShouldPersistTaps="handled"
                    nestedScrollEnabled
                    initialNumToRender={12}
                    ListEmptyComponent={
                        <Text style={styles.empty}>
                            {query.trim() ? '검색 결과가 없습니다.' : '등록된 VoIP 친구가 없습니다. 채팅 탭에서 친구를 추가해 보세요.'}
                        </Text>
                    }
                />
            )}
            <View style={styles.footer}>
                <Text style={styles.count}>{filtered.length}명</Text>
                <View style={styles.footerBtns}>
                    <Pressable style={styles.ghostBtn} onPress={() => { void load(); }} testID="voip-friends-dir-refresh">
                        <Text style={styles.ghostBtnText}>{loading ? '새로고침 중...' : '다시 불러오기'}</Text>
                    </Pressable>
                    {!embedded ? (
                        <Pressable style={styles.closeBtn} onPress={onClose} testID="voip-friends-dir-close">
                            <Text style={styles.closeBtnText}>닫기</Text>
                        </Pressable>
                    ) : null}
                </View>
            </View>
            </View>
        </>
    );

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
    embeddedCard: { backgroundColor: '#ffffff', borderRadius: 14, padding: 12, borderWidth: 1, borderColor: '#dce6f2', marginTop: 12 },
    sectionHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 },
    sectionHeadText: { flex: 1, paddingRight: 8 },
    sectionChevron: { color: '#8a93a3', fontSize: 18, fontWeight: '700' },
    sectionCollapsedMeta: { color: '#5f6b80', fontSize: 12, marginTop: 2 },
    sectionBodyCollapsed: { height: 0, overflow: 'hidden', opacity: 0 },
    list: { marginTop: 10, flexGrow: 0 },
    listEmbedded: { maxHeight: 280 },
    row: { borderBottomWidth: 1, borderBottomColor: '#e3eaf5' },
    rowHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 12 },
    rowInfo: { flexShrink: 1, flex: 1 },
    nameRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
    flag: { fontSize: 16 },
    name: { color: '#1a1f36', fontSize: 15, fontWeight: '700', flexShrink: 1 },
    appBadge: { color: '#ffffff', backgroundColor: '#2563eb', fontSize: 10, fontWeight: '800', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6, overflow: 'hidden' },
    meta: { color: '#5f6b80', fontSize: 12, marginTop: 2 },
    chevron: { color: '#8a93a3', fontSize: 18, fontWeight: '700', paddingLeft: 8 },
    actions: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, paddingBottom: 12 },
    actionBtn: { flexGrow: 1, flexBasis: '47%', paddingVertical: 11, borderRadius: 9, alignItems: 'center' },
    voipBtn: { backgroundColor: '#2563eb' },
    chatBtn: { backgroundColor: '#7c3aed' },
    inviteBtn: { backgroundColor: '#7c3aed', flexBasis: '100%' },
    actionDisabled: { opacity: 0.45 },
    actionText: { color: '#fff', fontSize: 12, fontWeight: '700' },
    empty: { color: '#8a93a3', fontSize: 13, textAlign: 'center', paddingVertical: 24 },
    footer: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 12 },
    count: { color: '#8a93a3', fontSize: 12 },
    footerBtns: { flexDirection: 'row', gap: 8 },
    ghostBtn: { paddingVertical: 9, paddingHorizontal: 14, borderRadius: 9, borderWidth: 1, borderColor: '#bcd3f0' },
    ghostBtnText: { color: '#1e6fe0', fontSize: 13, fontWeight: '700' },
    closeBtn: { paddingVertical: 9, paddingHorizontal: 18, borderRadius: 9, backgroundColor: '#e8f1ff' },
    closeBtnText: { color: '#1e6fe0', fontSize: 13, fontWeight: '700' },
});
