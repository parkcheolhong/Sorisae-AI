"""One-shot batch i18n wiring for ChatRoom, VoIP, App PSTN."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def apply_repls(path: Path, repls: list[tuple[str, str]], label: str) -> None:
    text = path.read_text(encoding='utf-8')
    for old, new in repls:
        if old not in text:
            print(f'{label} MISSING:', old[:70])
        else:
            text = text.replace(old, new, 1)
    path.write_text(text, encoding='utf-8')
    print(f'{label} done')


chat_repls = [
    (
        "return options?.currentPrefix\n      ? '현재: 정책은 멤버 초대 허용이지만 정원 만석으로 추가 초대 불가'\n      : '정원 만석으로 추가 초대 불가';",
        "return options?.currentPrefix\n      ? getFeatureUiText('chat.currentPrefix') + getFeatureUiText('chat.groupInviteAllowedFull')\n      : getFeatureUiText('chat.groupFullNoInvite');",
    ),
    (
        "return options?.currentPrefix ? '현재: 멤버 초대 허용' : '멤버 초대 허용';",
        "return options?.currentPrefix ? getFeatureUiText('chat.currentPrefix') + getFeatureUiText('chat.groupInviteAllowed') : getFeatureUiText('chat.groupInviteAllowed');",
    ),
    (
        "return options?.currentPrefix ? '현재: owner만 초대' : 'owner만 초대';",
        "return options?.currentPrefix ? getFeatureUiText('chat.currentPrefix') + getFeatureUiText('chat.groupInviteOwnerOnly') : getFeatureUiText('chat.groupInviteOwnerOnly');",
    ),
    (
        "return `${detail.members.length}명 / 정원 ${memberLimit}명 · ${detail.translation_mode} · ${buildGroupInviteStatusLabel(detail, room)}`;",
        "return getFeatureUiText('chat.groupSubtitle', { members: detail.members.length, limit: memberLimit, mode: detail.translation_mode, invite: buildGroupInviteStatusLabel(detail, room) });",
    ),
    (
        "return map[c] ?? { flag: '🌐', label: code ? code.toUpperCase() : '자동' };",
        "return map[c] ?? { flag: '🌐', label: code ? code.toUpperCase() : getFeatureUiText('chat.langAuto') };",
    ),
    (
        "const ampm = h < 12 ? '오전' : '오후';",
        "const ampm = h < 12 ? getFeatureUiText('chat.am') : getFeatureUiText('chat.pm');",
    ),
    (
        "return `배달 ${summary.done_count}/${summary.recipient_count} · 실패 ${summary.failed_count}`;",
        "return getFeatureUiText('chat.deliveryPartial', { done: summary.done_count, total: summary.recipient_count, failed: summary.failed_count });",
    ),
    (
        "return `배달 실패 ${summary.failed_count}/${summary.recipient_count}`;",
        "return getFeatureUiText('chat.deliveryFailed', { failed: summary.failed_count, total: summary.recipient_count });",
    ),
    (
        "return `배달 중 ${summary.pending_count}/${summary.recipient_count}`;",
        "return getFeatureUiText('chat.deliveryPending', { pending: summary.pending_count, total: summary.recipient_count });",
    ),
    (
        "return `배달 완료 ${summary.done_count}/${summary.recipient_count}`;",
        "return getFeatureUiText('chat.deliveryDone', { done: summary.done_count, total: summary.recipient_count });",
    ),
    ("<Text style={styles.systemCardTitle}>멤버 초대</Text>", "<Text style={styles.systemCardTitle}>{getFeatureUiText('chat.memberInviteCard')}</Text>"),
    ("<Text style={styles.systemCardTitle}>📣 WorldLinco 안내</Text>", "<Text style={styles.systemCardTitle}>{getFeatureUiText('chat.worldlincoNotice')}</Text>"),
    ("<Text style={styles.messageStatusError}>내 번역 생성 실패</Text>", "<Text style={styles.messageStatusError}>{getFeatureUiText('chat.myTranslationFailed')}</Text>"),
    ("setError(e instanceof Error ? e.message : '대화방을 불러오지 못했습니다.');", "setError(e instanceof Error ? e.message : getFeatureUiText('chat.loadRoomFailed'));"),
    ("setError(e instanceof Error ? e.message : '초대 가능한 친구를 불러오지 못했습니다.');", "setError(e instanceof Error ? e.message : getFeatureUiText('chat.loadFriendsFailed'));"),
    ("setError(e instanceof Error ? e.message : '메시지를 전송하지 못했습니다.');", "setError(e instanceof Error ? e.message : getFeatureUiText('chat.sendFailed'));"),
    ("setError(e instanceof Error ? e.message : '멤버를 초대하지 못했습니다.');", "setError(e instanceof Error ? e.message : getFeatureUiText('chat.inviteFailed'));"),
    ("setError(e instanceof Error ? e.message : '방 설정을 저장하지 못했습니다.');", "setError(e instanceof Error ? e.message : getFeatureUiText('chat.settingsFailed'));"),
    (
        "setError(`현재 활성 멤버가 ${detail.members.length}명이라 정원을 ${pendingMemberLimit}명으로 줄일 수 없습니다.`);",
        "setError(getFeatureUiText('chat.memberLimitTooSmall', { count: detail.members.length, limit: pendingMemberLimit }));",
    ),
    ("setError(e instanceof Error ? e.message : '방 정원을 저장하지 못했습니다.');", "setError(e instanceof Error ? e.message : getFeatureUiText('chat.memberLimitFailed'));"),
    ("<Text style={styles.headerOnline}>● 온라인</Text>", "<Text style={styles.headerOnline}>{getFeatureUiText('chat.online')}</Text>"),
    ("<Text style={styles.snsInviteButtonText}>📨 SNS 초대</Text>", "<Text style={styles.snsInviteButtonText}>{getFeatureUiText('chat.snsInvite')}</Text>"),
    (
        "<Text style={styles.inviteButtonText}>{inviteOpen ? '초대 닫기' : '멤버 초대'}</Text>",
        "<Text style={styles.inviteButtonText}>{inviteOpen ? getFeatureUiText('chat.inviteClose') : getFeatureUiText('chat.inviteOpen')}</Text>",
    ),
    (
        "<Text style={styles.settingButtonText}>{settingsOpen ? '설정 닫기' : '방 설정'}</Text>",
        "<Text style={styles.settingButtonText}>{settingsOpen ? getFeatureUiText('chat.settingsClose') : getFeatureUiText('chat.settingsOpen')}</Text>",
    ),
    ("<Text style={styles.settingsTitle}>방 설정</Text>", "<Text style={styles.settingsTitle}>{getFeatureUiText('chat.settingsTitle')}</Text>"),
    ("<Text style={styles.settingsLabel}>정원 변경</Text>", "<Text style={styles.settingsLabel}>{getFeatureUiText('chat.memberLimitChange')}</Text>"),
    (
        "<Text style={styles.settingsMeta}>생성자 입장 후에도 3명, 5명, 10명 고정방으로 바꿀 수 있습니다. 현재 활성 멤버 수보다 작게는 저장되지 않습니다.</Text>",
        "<Text style={styles.settingsMeta}>{getFeatureUiText('chat.memberLimitMeta')}</Text>",
    ),
    (
        "<Text style={[styles.limitOptionText, active && styles.limitOptionTextActive]}>{option}명 고정</Text>",
        "<Text style={[styles.limitOptionText, active && styles.limitOptionTextActive]}>{getFeatureUiText('chat.memberLimitFixed', { count: option })}</Text>",
    ),
    (
        "<Text style={styles.settingSaveButtonText}>{settingsSaving ? '정원 저장 중...' : `정원 ${pendingMemberLimit}명으로 저장`}</Text>",
        "<Text style={styles.settingSaveButtonText}>{settingsSaving ? getFeatureUiText('chat.memberLimitSaving') : getFeatureUiText('chat.memberLimitSave', { count: pendingMemberLimit })}</Text>",
    ),
    (
        "<Text style={styles.settingsStatus}>현재: 정원 {detail?.member_limit ?? room.member_limit ?? 10}명 · 활성 멤버 {detail?.members.length ?? room.member_count}명</Text>",
        "<Text style={styles.settingsStatus}>{getFeatureUiText('chat.memberLimitStatus', { limit: detail?.member_limit ?? room.member_limit ?? 10, active: detail?.members.length ?? room.member_count })}</Text>",
    ),
    ("<Text style={styles.settingsLabel}>초대 정책</Text>", "<Text style={styles.settingsLabel}>{getFeatureUiText('chat.invitePolicy')}</Text>"),
    ("<Text style={styles.settingsLabel}>멤버도 초대 가능</Text>", "<Text style={styles.settingsLabel}>{getFeatureUiText('chat.membersCanInvite')}</Text>"),
    (
        "<Text style={styles.settingsMeta}>끄면 owner만 초대할 수 있고, 켜면 현재 멤버도 새 친구를 초대할 수 있습니다.</Text>",
        "<Text style={styles.settingsMeta}>{getFeatureUiText('chat.membersCanInviteMeta')}</Text>",
    ),
    (
        "<Text style={styles.settingsStatus}>{settingsSaving ? '설정 저장 중...' : (detail ? buildGroupInviteStatusLabel(detail, room, { currentPrefix: true }) : '현재 설정 불러오는 중...')}</Text>",
        "<Text style={styles.settingsStatus}>{settingsSaving ? getFeatureUiText('chat.settingsSaving') : (detail ? buildGroupInviteStatusLabel(detail, room, { currentPrefix: true }) : getFeatureUiText('chat.settingsLoading'))}</Text>",
    ),
    ("<Text style={styles.invitePanelTitle}>초대할 친구 선택</Text>", "<Text style={styles.invitePanelTitle}>{getFeatureUiText('chat.invitePanelTitle')}</Text>"),
    ("<Text style={styles.inviteEmptyText}>추가로 초대할 수 있는 친구가 없습니다.</Text>", "<Text style={styles.inviteEmptyText}>{getFeatureUiText('chat.inviteEmpty')}</Text>"),
    (
        "<Text style={styles.sendButtonText}>{inviteLoading ? '초대 중...' : '선택 멤버 초대'}</Text>",
        "<Text style={styles.sendButtonText}>{inviteLoading ? getFeatureUiText('chat.inviteSaving') : getFeatureUiText('chat.inviteSubmit')}</Text>",
    ),
    ("<Text style={styles.aiChipText}>✨ WorldLinco AI 실시간 번역</Text>", "<Text style={styles.aiChipText}>{getFeatureUiText('chat.aiChip')}</Text>"),
    (
        "<Text style={styles.emptyText}>아직 메시지가 없습니다. 첫 메시지를 내면 이 방이 번역/채팅 히스토리의 시작점이 됩니다.</Text>",
        "<Text style={styles.emptyText}>{getFeatureUiText('chat.emptyRoom')}</Text>",
    ),
]

voip_repls = [
    ("setVoiceRelayError('음성 통역 결과가 비어 있습니다. 다시 시도해 주세요.');", "setVoiceRelayError(getFeatureUiText('voip.voiceRelayEmpty'));"),
    ("setVoiceRelayError('음성 통역 relay 채널이 아직 연결되지 않았습니다.');", "setVoiceRelayError(getFeatureUiText('voip.voiceRelayRelayNotConnected'));"),
    ("setVoiceRelayError('웹에서는 통화 중 실시간 음성 통역 녹음을 지원하지 않습니다.');", "setVoiceRelayError(getFeatureUiText('voip.voiceRelayWebUnsupported'));"),
    ("setVoiceRelayError('마이크 권한이 없어 실시간 음성 통역을 시작할 수 없습니다.');", "setVoiceRelayError(getFeatureUiText('voip.voiceRelayMicPermission'));"),
    (
        "setVoiceRelayError('실시간 음성 통역 중에는 WebRTC 원음 경로가 꺼져 있습니다. 통역을 중지하면 일반 음성 버튼을 사용할 수 있습니다.');",
        "setVoiceRelayError(getFeatureUiText('voip.webrtcDisabledDuringRelay'));",
    ),
    ("setChatError('채팅 채널이 아직 연결되지 않았습니다. 잠시 후 다시 시도하세요.');", "setChatError(getFeatureUiText('voip.chatChannelNotReady'));"),
    (
        "const message = err instanceof Error ? err.message : '실시간 음성 통역 처리에 실패했습니다.';",
        "const message = err instanceof Error ? err.message : getFeatureUiText('voip.voiceRelayFailed');",
    ),
    (
        "const message = err instanceof Error ? err.message : '실시간 음성 통역 녹음을 시작하지 못했습니다.';",
        "const message = err instanceof Error ? err.message : getFeatureUiText('voip.voiceRelayStartFailed');",
    ),
    (
        "setVoiceRelayError(`녹음 ${snapshot.segmentDurationMs}ms — 조금 더 길게 말해 주세요.`);",
        "setVoiceRelayError(getFeatureUiText('voip.recordTooShort', { ms: snapshot.segmentDurationMs }));",
    ),
    (
        "? '통화 연결에 실패했습니다. 네트워크 또는 서버 상태를 확인해주세요.'\n                            : '통화 연결이 끊어졌습니다.');",
        "? getFeatureUiText('voip.connectionFailedMsg')\n                            : getFeatureUiText('voip.connectionDisconnectedMsg'));",
    ),
    (
        "? '통화 연결에 실패했습니다. 네트워크 또는 서버 상태를 확인해주세요.'\n                        : '통화 연결이 끊어졌습니다.');",
        "? getFeatureUiText('voip.connectionFailedMsg')\n                        : getFeatureUiText('voip.connectionDisconnectedMsg'));",
    ),
    (
        "setLastRelayDeliveryHint(`전달됨 · ${transcript.slice(0, 40)} → ${translatedText.slice(0, 40)}`);",
        "setLastRelayDeliveryHint(getFeatureUiText('voip.deliveredPreview', { from: transcript.slice(0, 40), to: translatedText.slice(0, 40) }));",
    ),
    (
        "setLastRelayDeliveryHint(`수신 · ${translatedText.slice(0, 48)}`);",
        "setLastRelayDeliveryHint(getFeatureUiText('voip.receivedPreview', { text: translatedText.slice(0, 48) }));",
    ),
    ("<Text style={styles.buttonText}>권한 설정 열기</Text>", "<Text style={styles.buttonText}>{getFeatureUiText('voip.permissionOpen')}</Text>"),
    ("<Text style={styles.buttonText}>돌아가기</Text>", "<Text style={styles.buttonText}>{getFeatureUiText('voip.goBack')}</Text>"),
    ("실시간 쌍언어 채팅", "{getFeatureUiText('voip.bilingualChatTitle')}"),
    ("음성 통역 결과가 원문과 번역문 쌍으로 여기에 표시됩니다.", "{getFeatureUiText('voip.bilingualChatHint')}"),
    (
        "<Text style={styles.chatLiveBannerText}>음성 감지됨 · 번역 처리 중… (3~7초)</Text>",
        "<Text style={styles.chatLiveBannerText}>{getFeatureUiText('voip.voiceDetectedTranslating')}</Text>",
    ),
    (
        "? '마이크 듣는 중 · 말이 끝나면 자동 번역'\n                            : voiceRelayMeterDead\n                                ? '마이크 듣는 중 · 음성 감지 후 자동 번역'\n                                : '마이크 듣는 중 · 말이 끝나면 자동 번역'}",
        "? getFeatureUiText('voip.micListening')\n                            : voiceRelayMeterDead\n                                ? getFeatureUiText('voip.micListeningVad')\n                                : getFeatureUiText('voip.micListening')}",
    ),
    (
        "<Text style={styles.chatLiveBannerText}>상대 통역 수신 중 — 잠시 후 마이크가 다시 켜집니다.</Text>",
        "<Text style={styles.chatLiveBannerText}>{getFeatureUiText('voip.peerRelayReceiving')}</Text>",
    ),
    (
        "<Text style={styles.chatLatestPreviewLabel}>속기·통역 전달</Text>",
        "<Text style={styles.chatLatestPreviewLabel}>{getFeatureUiText('voip.relayDeliveryLabel')}</Text>",
    ),
    ("<Text style={styles.chatLatestPreviewLabel}>최근 통역</Text>", "<Text style={styles.chatLatestPreviewLabel}>{getFeatureUiText('voip.recentTranslation')}</Text>"),
    (
        "const speakerLabel = entry.fromRole === participantRole ? '나' : remoteDisplayName;",
        "const speakerLabel = entry.fromRole === participantRole ? getFeatureUiText('voip.me') : remoteDisplayName;",
    ),
    (
        "<Text style={styles.statusText}>{connectionState === 'connected' ? '상대 음성 경로 확인 중...' : '음성 경로 연결 중...'}</Text>",
        "<Text style={styles.statusText}>{connectionState === 'connected' ? getFeatureUiText('voip.audioPathChecking') : getFeatureUiText('voip.audioPathConnecting')}</Text>",
    ),
]

app_path = ROOT / 'App.tsx'
app_text = app_path.read_text(encoding='utf-8')
app_repls = [
    (
        "setInterCallStatus(\n                shared\n                    ? `📨 ${contact.name}님에게 채팅 초대를 보냈습니다.`\n                    : `📨 ${contact.name}님은 아직 미가입입니다. 초대 공유를 취소했습니다.`,\n            );",
        "setInterCallStatus(\n                shared\n                    ? getFeatureUiText('pstn.contactInviteSent', { name: contact.name })\n                    : getFeatureUiText('pstn.contactNotRegistered', { name: contact.name }),\n            );",
    ),
    (
        "Alert.alert('채팅 시작 실패', error?.message || '연락처로 채팅을 시작하지 못했습니다.');",
        "Alert.alert(getFeatureUiText('pstn.chatStartFailedTitle'), error?.message || getFeatureUiText('pstn.chatStartFailedBody'));",
    ),
    (
        "`${contact.phone}\\n무엇을 할까요?`",
        "`${contact.phone}\\n${getFeatureUiText('pstn.contactChooserPrompt')}`",
    ),
    (
        "{ text: '💬 채팅/초대', onPress: () => { void handleOpenChatFromContact(contact); } }",
        "{ text: getFeatureUiText('pstn.contactChatInvite'), onPress: () => { void handleOpenChatFromContact(contact); } }",
    ),
    (
        "{ text: '📞 일반통화', onPress: () => { handleSelectInterCallContact(contact); } }",
        "{ text: getFeatureUiText('pstn.contactInterCall'), onPress: () => { handleSelectInterCallContact(contact); } }",
    ),
    ("{ text: '취소', style: 'cancel' },", "{ text: getFeatureUiText('pstn.cancel'), style: 'cancel' },"),
    (
        "setInterCallStatus(\n            shared\n                ? `📨 ${contact.name}님에게 채팅 초대를 보냈습니다.`\n                : `📨 ${contact.name}님은 아직 미가입입니다. 초대 공유를 취소했습니다.`,\n        );",
        "setInterCallStatus(\n            shared\n                ? getFeatureUiText('pstn.contactInviteSent', { name: contact.name })\n                : getFeatureUiText('pstn.contactNotRegistered', { name: contact.name }),\n        );",
    ),
    (
        "Alert.alert('채팅 시작 실패', error?.message || '친구 채팅을 시작하지 못했습니다.');",
        "Alert.alert(getFeatureUiText('pstn.chatStartFailedTitle'), error?.message || getFeatureUiText('pstn.friendChatStartFailedBody'));",
    ),
]

if __name__ == '__main__':
    apply_repls(ROOT / 'src/features/chat/screens/ChatRoomScreen.tsx', chat_repls, 'ChatRoomScreen')
    apply_repls(ROOT / 'src/screens/VoIPCallScreen.tsx', voip_repls, 'VoIPCallScreen')
    text = app_path.read_text(encoding='utf-8')
    for old, new in app_repls:
        if old not in text:
            print('App.tsx MISSING:', old[:70])
        else:
            text = text.replace(old, new)
    app_path.write_text(text, encoding='utf-8')
    print('App.tsx done')
