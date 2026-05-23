import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { getFriends, addFriend, removeFriend } from '../../api/friends';
import type { Friend } from './types';

interface Props {
  userId: number;
  token: string;
}

export function FriendFolderScreen({ userId, token }: Props) {
  const [friends, setFriends] = useState<Friend[]>([]);
  const [loading, setLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [addLoading, setAddLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getFriends(userId, token);
      setFriends(data.friends);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '친구 목록을 불러올 수 없습니다.');
    } finally {
      setLoading(false);
    }
  }, [userId, token]);

  useEffect(() => { void load(); }, [load]);

  const handleAdd = useCallback(async () => {
    const trimmed = email.trim();
    if (!trimmed) return;
    setAddLoading(true);
    setError(null);
    try {
      await addFriend({ targetEmail: trimmed, phoneNumber: phone.trim() || undefined }, token);
      setEmail('');
      setPhone('');
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '친구 추가에 실패했습니다.');
    } finally {
      setAddLoading(false);
    }
  }, [email, token, load]);

  const handleRemove = useCallback((friend: Friend) => {
    Alert.alert(
      '친구 삭제',
      `${friend.friendUsername || friend.friendEmail}을(를) 친구 목록에서 삭제할까요?`,
      [
        { text: '취소', style: 'cancel' },
        {
          text: '삭제',
          style: 'destructive',
          onPress: async () => {
            try {
              await removeFriend(friend.id, token);
              await load();
            } catch (e: unknown) {
              Alert.alert('오류', e instanceof Error ? e.message : '삭제 실패');
            }
          },
        },
      ],
    );
  }, [token, load]);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>👥 내 친구 목록</Text>

      <View style={styles.addRow}>
        <TextInput
          style={styles.input}
          placeholder="친구 이메일 입력"
          placeholderTextColor="#888"
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          autoCapitalize="none"
          editable={!addLoading}
        />
      </View>
      <View style={styles.addRow}>
        <TextInput
          style={styles.input}
          placeholder="연락처 번호 (선택)"
          placeholderTextColor="#888"
          value={phone}
          onChangeText={setPhone}
          keyboardType="phone-pad"
          editable={!addLoading}
        />
        <Pressable
          style={[styles.addBtn, addLoading && styles.addBtnDisabled]}
          onPress={() => { void handleAdd(); }}
          disabled={addLoading}
        >
          <Text style={styles.addBtnText}>{addLoading ? '추가 중...' : '+ 추가'}</Text>
        </Pressable>
      </View>

      {error ? <Text style={styles.errorText}>{error}</Text> : null}

      {loading ? (
        <ActivityIndicator color="#6ee7b7" style={styles.loader} />
      ) : friends.length === 0 ? (
        <Text style={styles.emptyText}>친구가 없습니다. 이메일로 추가해보세요.</Text>
      ) : (
        <FlatList
          data={friends}
          keyExtractor={(item) => String(item.id)}
          renderItem={({ item }) => (
            <View style={styles.friendRow}>
              <View style={styles.friendInfo}>
                <Text style={styles.friendName}>{item.friendUsername || item.friendEmail.split('@')[0]}</Text>
                <Text style={styles.friendEmail}>{item.friendEmail}</Text>
                {item.friendPhone ? (
                  <Text style={styles.friendPhone}>📞 {item.friendPhone}</Text>
                ) : null}
              </View>
              <Pressable style={styles.removeBtn} onPress={() => handleRemove(item)}>
                <Text style={styles.removeBtnText}>삭제</Text>
              </Pressable>
            </View>
          )}
          contentContainerStyle={styles.list}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0b0f16',
    padding: 20,
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#e2e8f0',
    marginBottom: 16,
  },
  addRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 12,
  },
  input: {
    flex: 1,
    backgroundColor: '#1e2533',
    color: '#e2e8f0',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    fontSize: 14,
    borderWidth: 1,
    borderColor: '#334155',
  },
  addBtn: {
    backgroundColor: '#6ee7b7',
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 8,
    justifyContent: 'center',
  },
  addBtnDisabled: {
    opacity: 0.5,
  },
  addBtnText: {
    color: '#0b0f16',
    fontWeight: 'bold',
    fontSize: 13,
  },
  errorText: {
    color: '#f87171',
    fontSize: 13,
    marginBottom: 8,
  },
  loader: {
    marginTop: 24,
  },
  emptyText: {
    color: '#64748b',
    textAlign: 'center',
    marginTop: 32,
    fontSize: 14,
  },
  list: {
    paddingBottom: 16,
  },
  friendRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1e2533',
    borderRadius: 10,
    padding: 12,
    marginBottom: 8,
  },
  friendInfo: {
    flex: 1,
  },
  friendName: {
    color: '#e2e8f0',
    fontWeight: '600',
    fontSize: 14,
  },
  friendEmail: {
    color: '#94a3b8',
    fontSize: 12,
    marginTop: 2,
  },
  friendPhone: {
    color: '#6ee7b7',
    fontSize: 12,
    marginTop: 2,
  },
  removeBtn: {
    backgroundColor: '#3f1f1f',
    borderRadius: 6,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  removeBtnText: {
    color: '#f87171',
    fontSize: 12,
    fontWeight: '600',
  },
});
