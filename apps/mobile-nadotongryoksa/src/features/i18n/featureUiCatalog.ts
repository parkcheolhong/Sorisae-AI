/**
 * VoIP · 채팅 · PSTN 기능 UI — ko/en/ja/zh 오프라인 정적 카탈로그.
 * 런타임 API 번역 없이 즉시 표시(한국어 플래시 금지).
 */
import { getUiLang } from './uiI18n';
import { resolveBundledCatalogLang, type BundledUiLang } from './bundledUiLangs';

export type FeatureUiKey =
    // VoIP
    | 'voip.remoteParty' | 'voip.me' | 'voip.micListening' | 'voip.micListeningVad'
    | 'voip.chatTranslatePending' | 'voip.chatTranslateFailed' | 'voip.chatAutoTranslate'
    | 'voip.chatEmpty' | 'voip.chatPlaceholder' | 'voip.chatSend'
    | 'voip.connectionInCall' | 'voip.connectionWaitingAudio' | 'voip.connectionFailed'
    | 'voip.connectionDisconnected' | 'voip.connecting'
    | 'voip.voiceRelayStart' | 'voip.voiceRelayStop'
    | 'voip.voiceRelayListening' | 'voip.voiceRelayRecording' | 'voip.voiceRelayTranslating'
    | 'voip.voiceRelayPlayback' | 'voip.voiceRelayWaiting' | 'voip.voiceRelayReady' | 'voip.voiceRelayOff'
    | 'voip.audioPathChecking' | 'voip.audioPathConnecting'
    | 'voip.muteOn' | 'voip.muteOff' | 'voip.speakerOn' | 'voip.speakerOff'
    | 'voip.voiceRelayEmpty' | 'voip.voiceRelayRelayNotConnected' | 'voip.voiceRelayFailed'
    | 'voip.voiceRelayWebUnsupported' | 'voip.voiceRelayMicPermission' | 'voip.voiceRelayStartFailed'
    | 'voip.connectionFailedMsg' | 'voip.connectionDisconnectedMsg'
    | 'voip.chatChannelNotReady' | 'voip.webrtcDisabledDuringRelay'
    | 'voip.recordTooShort' | 'voip.voiceDetectedTranslating' | 'voip.peerRelayReceiving'
    | 'voip.relayDeliveryLabel' | 'voip.recentTranslation' | 'voip.bilingualChatTitle' | 'voip.bilingualChatHint'
    | 'voip.relayServerReady' | 'voip.regionHint' | 'voip.regionHintNone' | 'voip.permissionOpen' | 'voip.goBack'
    | 'voip.deliveredPreview' | 'voip.receivedPreview' | 'voip.sileroVadRecording' | 'voip.voiceRelayHint'
    | 'voip.metaNickname' | 'voip.metaGender' | 'voip.metaCountry' | 'voip.waitingPeerAudio'
    // Chat
    | 'chat.me' | 'chat.peer' | 'chat.emptyRoom' | 'chat.inputPlaceholder' | 'chat.transcribing'
    | 'chat.inviteOpen' | 'chat.inviteClose' | 'chat.settingsOpen' | 'chat.settingsClose'
    | 'chat.inviteSaving' | 'chat.inviteSubmit' | 'chat.settingsSaving' | 'chat.settingsLoading'
    | 'chat.loadRoomFailed' | 'chat.sendFailed' | 'chat.inviteFailed' | 'chat.settingsFailed'
    | 'chat.memberLimitFailed' | 'chat.directSubtitle' | 'chat.directSubtitleAuto'
    | 'chat.groupInviteAllowed' | 'chat.groupInviteOwnerOnly' | 'chat.groupFullNoInvite'
    | 'chat.groupInviteAllowedFull' | 'chat.currentPrefix' | 'chat.online' | 'chat.snsInvite'
    | 'chat.settingsTitle' | 'chat.memberLimitChange' | 'chat.memberLimitMeta' | 'chat.memberLimitFixed'
    | 'chat.memberLimitSaving' | 'chat.memberLimitSave' | 'chat.memberLimitStatus'
    | 'chat.invitePolicy' | 'chat.membersCanInvite' | 'chat.membersCanInviteMeta'
    | 'chat.invitePanelTitle' | 'chat.inviteEmpty' | 'chat.aiChip' | 'chat.memberInviteCard'
    | 'chat.worldlincoNotice' | 'chat.myTranslationFailed' | 'chat.loadFriendsFailed'
    | 'chat.memberLimitTooSmall' | 'chat.deliveryPartial' | 'chat.deliveryFailed' | 'chat.deliveryPending' | 'chat.deliveryDone'
    | 'chat.groupSubtitle' | 'chat.am' | 'chat.pm' | 'chat.langAuto'
    | 'chat.peerLangAutoTranslate' | 'chat.peerLangAutoDetect'
    | 'chat.ocrTitle' | 'chat.extractLabel' | 'chat.translationLabel'
    | 'chat.songTitle' | 'chat.songMemo' | 'chat.songLyrics'
    | 'chat.shareTitle' | 'chat.shareOriginal' | 'chat.shareTranslated'
    // PSTN
    | 'pstn.manualModeFallback' | 'pstn.contactPicked' | 'pstn.chatOpened' | 'pstn.callOutgoing'
    | 'pstn.dialFailed' | 'pstn.dialPadOpened' | 'pstn.contactsCancelled' | 'pstn.speakerAssistStopped'
    | 'pstn.speakerAssistReady' | 'pstn.autoModeStart' | 'pstn.dialPadHint'
    | 'pstn.translationError' | 'pstn.speechError' | 'pstn.browserTtsUnavailable'
    | 'pstn.contactInviteSent' | 'pstn.contactNotRegistered' | 'pstn.chatStartFailedTitle' | 'pstn.chatStartFailedBody'
    | 'pstn.contactChooserPrompt' | 'pstn.contactChatInvite' | 'pstn.contactInterCall' | 'pstn.cancel'
    | 'pstn.friendChatStartFailedBody'
    | 'pstn.callWaiting' | 'pstn.voiceAssistStop' | 'pstn.voiceAssistPreparing' | 'pstn.voiceAssistStart'
    | 'pstn.speakerAssistHint' | 'pstn.autoRelayInterval' | 'pstn.manualInputPlaceholder' | 'pstn.sendNow'
    | 'pstn.interCallHint' | 'pstn.interToggleEnd' | 'pstn.interToggleStart'
    // Home / Face
    | 'home.greeting' | 'home.greetingSub' | 'home.faceTitle' | 'home.faceSub' | 'home.faceCtaOn' | 'home.faceCtaOff'
    | 'face.peerPlaceholder' | 'face.mePlaceholder' | 'face.tapListening' | 'face.tapToSpeak'
    // Chat list
    | 'chat.list.title' | 'chat.list.summaryTitle' | 'chat.list.summaryMetric' | 'chat.list.noPreview'
    | 'chat.list.noRecentTime' | 'chat.list.noRecentChat' | 'chat.list.openVault' | 'chat.list.opening'
    | 'chat.list.closeGroup' | 'chat.list.createGroup' | 'chat.list.refreshing' | 'chat.list.refresh'
    | 'chat.list.groupTitle' | 'chat.list.groupHint' | 'chat.list.groupPlaceholder' | 'chat.list.capacityTitle'
    | 'chat.list.capacityMeta' | 'chat.list.memberInviteTitle' | 'chat.list.memberInviteMeta'
    | 'chat.list.noFriendsForGroup' | 'chat.list.creatingGroup' | 'chat.list.openGroup'
    | 'chat.list.friendsTitle' | 'chat.list.noFriends' | 'chat.list.voipCall' | 'chat.list.chatBtn'
    | 'chat.list.recentRooms' | 'chat.list.noRooms' | 'chat.list.noMessages' | 'chat.list.langUnset'
    | 'chat.list.alertGroupInvite' | 'chat.list.alertAnnouncement' | 'chat.list.alertTranslation'
    | 'chat.list.alertNewMessage' | 'chat.list.directRoom' | 'chat.list.groupRoomMeta'
    | 'chat.list.loadFailed' | 'chat.list.vaultFailed' | 'chat.list.friendRoomFailed' | 'chat.list.groupFailed'
    | 'chat.list.groupNameRequired' | 'chat.list.groupMemberRequired' | 'chat.list.groupOverCapacity'
    | 'chat.list.groupCapacityLimit' | 'chat.list.fixedMembers'
    // User-facing (no language codes)
    | 'user.meSide' | 'user.peerSide' | 'user.bidirectionalMode'
    | 'user.mySpeechInput' | 'user.peerSpeechInput'
    | 'user.listening' | 'user.translating' | 'user.speaking';

type CatalogRow = Record<BundledUiLang, string>;

const ROWS: Record<FeatureUiKey, CatalogRow> = {
    'voip.remoteParty': { ko: '상대', en: 'Peer', ja: '相手', zh: '对方' },
    'voip.me': { ko: '나', en: 'Me', ja: '自分', zh: '我' },
    'voip.micListening': { ko: '마이크 듣는 중 · 말이 끝나면 자동 번역', en: 'Listening · auto-translate when you finish', ja: '聞いています · 話し終わると自動翻訳', zh: '正在聆听 · 说完后自动翻译' },
    'voip.micListeningVad': { ko: '마이크 듣는 중 · 음성 감지 후 자동 번역', en: 'Listening · auto-translate after voice detected', ja: '聞いています · 音声検出後に自動翻訳', zh: '正在聆听 · 检测到语音后自动翻译' },
    'voip.chatTranslatePending': { ko: '번역 중...', en: 'Translating...', ja: '翻訳中...', zh: '翻译中...' },
    'voip.chatTranslateFailed': { ko: '번역을 불러오지 못했습니다. 원문을 표시합니다.', en: 'Could not load translation. Showing original.', ja: '翻訳を読み込めませんでした。原文を表示します。', zh: '无法加载翻译。显示原文。' },
    'voip.chatAutoTranslate': { ko: '자동 번역', en: 'Auto translation', ja: '自動翻訳', zh: '自动翻译' },
    'voip.chatEmpty': { ko: '아직 통역/채팅이 없습니다. 통화 연결 후 3초 이상 말하면 번역이 여기에 표시됩니다.', en: 'No interpretation or chat yet. Speak for 3+ seconds after connecting.', ja: 'まだ通訳・チャットがありません。接続後3秒以上話すとここに表示されます。', zh: '尚无传译或聊天。连接后说话超过3秒将显示在此。' },
    'voip.chatPlaceholder': { ko: '메시지를 입력하세요', en: 'Type a message', ja: 'メッセージを入力', zh: '输入消息' },
    'voip.chatSend': { ko: '전송', en: 'Send', ja: '送信', zh: '发送' },
    'voip.connectionInCall': { ko: '통화 중', en: 'On call', ja: '通話中', zh: '通话中' },
    'voip.connectionWaitingAudio': { ko: '음성 연결 대기', en: 'Waiting for audio', ja: '音声接続待ち', zh: '等待语音连接' },
    'voip.connectionFailed': { ko: '연결 실패', en: 'Connection failed', ja: '接続失敗', zh: '连接失败' },
    'voip.connectionDisconnected': { ko: '연결 끊김', en: 'Disconnected', ja: '切断', zh: '已断开' },
    'voip.connecting': { ko: '연결 중...', en: 'Connecting...', ja: '接続中...', zh: '连接中...' },
    'voip.voiceRelayStart': { ko: '시작', en: 'Start', ja: '開始', zh: '开始' },
    'voip.voiceRelayStop': { ko: '중지', en: 'Stop', ja: '停止', zh: '停止' },
    'voip.voiceRelayListening': { ko: '지금 음성을 듣고 있습니다.', en: 'Listening for your voice.', ja: '音声を聞いています。', zh: '正在聆听您的语音。' },
    'voip.voiceRelayRecording': { ko: '파일 RMS로 음성 감지 · 녹음 중입니다.', en: 'Detecting voice · recording.', ja: '音声検出 · 録音中です。', zh: '正在检测语音 · 录音中。' },
    'voip.voiceRelayTranslating': { ko: '통역 및 전송 중입니다.', en: 'Translating and sending.', ja: '通訳・送信中です。', zh: '正在传译并发送。' },
    'voip.voiceRelayPlayback': { ko: '상대 통역 재생/수신 중 — 곧 마이크가 재개됩니다.', en: 'Playing peer translation — mic resumes soon.', ja: '相手の通訳再生中 — まもなくマイク再開。', zh: '正在播放对方传译 — 麦克风即将恢复。' },
    'voip.voiceRelayWaiting': { ko: '다음 음성 구간을 대기 중입니다.', en: 'Waiting for next speech segment.', ja: '次の音声区間を待機中。', zh: '等待下一段语音。' },
    'voip.voiceRelayReady': { ko: '상대 음성 경로가 열리면 시작 준비 상태로 대기합니다.', en: 'Ready when peer audio path opens.', ja: '相手の音声経路が開くと開始準備完了。', zh: '对方语音通路就绪后即可开始。' },
    'voip.voiceRelayOff': { ko: '실시간 음성 통역이 꺼져 있습니다.', en: 'Live voice interpretation is off.', ja: 'リアルタイム音声通訳はオフです。', zh: '实时语音传译已关闭。' },
    'voip.audioPathChecking': { ko: '상대 음성 경로 확인 중...', en: 'Checking peer audio path...', ja: '相手の音声経路を確認中...', zh: '正在检查对方语音通路...' },
    'voip.audioPathConnecting': { ko: '음성 경로 연결 중...', en: 'Connecting audio path...', ja: '音声経路を接続中...', zh: '正在连接语音通路...' },
    'voip.muteOn': { ko: '음소거 중', en: 'Muted', ja: 'ミュート中', zh: '已静音' },
    'voip.muteOff': { ko: '음성', en: 'Mic', ja: '音声', zh: '语音' },
    'voip.speakerOn': { ko: '스피커', en: 'Speaker', ja: 'スピーカー', zh: '扬声器' },
    'voip.speakerOff': { ko: '수화기', en: 'Earpiece', ja: '受話器', zh: '听筒' },
    'voip.voiceRelayEmpty': { ko: '음성 통역 결과가 비어 있습니다. 다시 시도해 주세요.', en: 'Voice interpretation result is empty. Please try again.', ja: '音声通訳結果が空です。もう一度お試しください。', zh: '语音传译结果为空。请重试。' },
    'voip.voiceRelayRelayNotConnected': { ko: '음성 통역 relay 채널이 아직 연결되지 않았습니다.', en: 'Voice relay channel is not connected yet.', ja: '音声通訳リレーチャネルがまだ接続されていません。', zh: '语音传译中继通道尚未连接。' },
    'voip.voiceRelayFailed': { ko: '실시간 음성 통역 처리에 실패했습니다.', en: 'Live voice interpretation failed.', ja: 'リアルタイム音声通訳に失敗しました。', zh: '实时语音传译处理失败。' },
    'voip.voiceRelayWebUnsupported': { ko: '웹에서는 통화 중 실시간 음성 통역 녹음을 지원하지 않습니다.', en: 'Live voice interpretation recording is not supported on web during calls.', ja: 'Webでは通話中のリアルタイム音声通訳録音に対応していません。', zh: 'Web 端不支持通话中的实时语音传译录音。' },
    'voip.voiceRelayMicPermission': { ko: '마이크 권한이 없어 실시간 음성 통역을 시작할 수 없습니다.', en: 'Microphone permission required for live voice interpretation.', ja: 'マイク権限がないためリアルタイム音声通訳を開始できません。', zh: '无麦克风权限，无法开始实时语音传译。' },
    'voip.voiceRelayStartFailed': { ko: '실시간 음성 통역 녹음을 시작하지 못했습니다.', en: 'Could not start live voice interpretation recording.', ja: 'リアルタイム音声通訳の録音を開始できませんでした。', zh: '无法开始实时语音传译录音。' },
    'voip.connectionFailedMsg': { ko: '통화 연결에 실패했습니다. 네트워크 또는 서버 상태를 확인해주세요.', en: 'Call connection failed. Check network or server.', ja: '通話接続に失敗しました。ネットワークまたはサーバーを確認してください。', zh: '通话连接失败。请检查网络或服务器。' },
    'voip.connectionDisconnectedMsg': { ko: '통화 연결이 끊어졌습니다.', en: 'Call disconnected.', ja: '通話が切断されました。', zh: '通话已断开。' },
    'voip.chatChannelNotReady': { ko: '채팅 채널이 아직 연결되지 않았습니다. 잠시 후 다시 시도하세요.', en: 'Chat channel not ready. Try again shortly.', ja: 'チャットチャネルがまだ接続されていません。しばらくして再試行してください。', zh: '聊天通道尚未连接。请稍后重试。' },
    'voip.webrtcDisabledDuringRelay': { ko: '실시간 음성 통역 중에는 WebRTC 원음 경로가 꺼져 있습니다. 통역을 중지하면 일반 음성 버튼을 사용할 수 있습니다.', en: 'WebRTC raw audio is off during live interpretation. Stop interpretation to use normal voice.', ja: 'リアルタイム通訳中はWebRTC原音経路がオフです。通訳を停止すると通常音声が使えます。', zh: '实时传译期间 WebRTC 原音通路已关闭。停止传译后可使用普通语音。' },
    'voip.recordTooShort': { ko: '녹음 {ms}ms — 조금 더 길게 말해 주세요.', en: 'Recording {ms}ms — please speak a bit longer.', ja: '録音{ms}ms — もう少し長く話してください。', zh: '录音{ms}ms — 请再说长一点。' },
    'voip.voiceDetectedTranslating': { ko: '음성 감지됨 · 번역 처리 중… (3~7초)', en: 'Voice detected · translating… (3–7s)', ja: '音声検出 · 翻訳処理中…（3〜7秒）', zh: '检测到语音 · 翻译处理中…（3~7秒）' },
    'voip.peerRelayReceiving': { ko: '상대 통역 수신 중 — 잠시 후 마이크가 다시 켜집니다.', en: 'Receiving peer translation — mic resumes shortly.', ja: '相手の通訳受信中 — まもなくマイク再開。', zh: '正在接收对方传译 — 麦克风即将恢复。' },
    'voip.relayDeliveryLabel': { ko: '속기·통역 전달', en: 'Steno · interpretation relay', ja: '速記・通訳配信', zh: '速记·传译传递' },
    'voip.recentTranslation': { ko: '최근 통역', en: 'Recent interpretation', ja: '最近の通訳', zh: '最近传译' },
    'voip.bilingualChatTitle': { ko: '실시간 쌍언어 채팅', en: 'Live bilingual chat', ja: 'リアルタイム二言語チャット', zh: '实时双语聊天' },
    'voip.bilingualChatHint': { ko: '음성 통역 결과가 원문과 번역문 쌍으로 여기에 표시됩니다.', en: 'Voice interpretation appears here as original + translation pairs.', ja: '音声通訳結果が原文と翻訳のペアでここに表示されます。', zh: '语音传译结果以原文与译文对照显示于此。' },
    'voip.relayServerReady': { ko: '서버 relay 경로가 준비됐습니다. 연결 직후 자동 통역 시작을 대기 중입니다.', en: 'Server relay ready. Waiting to start auto interpretation after connect.', ja: 'サーバーリレー準備完了。接続後の自動通訳開始を待機中。', zh: '服务器中继已就绪。等待连接后自动开始传译。' },
    'voip.regionHint': { ko: '현재 지역 힌트: {hint}', en: 'Region hint: {hint}', ja: '地域ヒント: {hint}', zh: '当前地区提示: {hint}' },
    'voip.regionHintNone': { ko: '없음', en: 'none', ja: 'なし', zh: '无' },
    'voip.permissionOpen': { ko: '권한 설정 열기', en: 'Open permissions', ja: '権限設定を開く', zh: '打开权限设置' },
    'voip.goBack': { ko: '돌아가기', en: 'Go back', ja: '戻る', zh: '返回' },
    'voip.deliveredPreview': { ko: '전달됨 · {from} → {to}', en: 'Delivered · {from} → {to}', ja: '配信済 · {from} → {to}', zh: '已传递 · {from} → {to}' },
    'voip.receivedPreview': { ko: '수신 · {text}', en: 'Received · {text}', ja: '受信 · {text}', zh: '接收 · {text}' },
    'voip.sileroVadRecording': { ko: 'Silero VAD로 음성 끝 감지 · 녹음 중입니다.', en: 'Silero VAD end-of-speech · recording.', ja: 'Silero VADで音声終了検出 · 録音中。', zh: 'Silero VAD 检测语音结束 · 录音中。' },
    'voip.voiceRelayHint': { ko: '음성 통역 ON 시 결과는 위 「실시간 쌍언어 채팅」에 원문·번역문으로 표시됩니다.', en: 'When voice interpretation is ON, results appear above in Live bilingual chat.', ja: '音声通訳ON時、上のリアルタイム二言語チャットに原文・翻訳が表示されます。', zh: '开启语音传译后，结果将显示在上方实时双语聊天中。' },
    'voip.metaNickname': { ko: '닉네임', en: 'Nickname', ja: 'ニックネーム', zh: '昵称' },
    'voip.metaGender': { ko: '성별', en: 'Gender', ja: '性別', zh: '性别' },
    'voip.metaCountry': { ko: '국가', en: 'Country', ja: '国', zh: '国家' },
    'voip.waitingPeerAudio': { ko: '상대 음성 수신 대기 중', en: 'Waiting for peer audio', ja: '相手の音声受信待ち', zh: '等待对方语音' },

    'chat.me': { ko: '나', en: 'Me', ja: '自分', zh: '我' },
    'chat.peer': { ko: '상대', en: 'Peer', ja: '相手', zh: '对方' },
    'chat.emptyRoom': { ko: '아직 메시지가 없습니다. 첫 메시지를 내면 이 방이 번역/채팅 히스토리의 시작점이 됩니다.', en: 'No messages yet. Send the first message to start this room.', ja: 'まだメッセージがありません。最初のメッセージでこのルームが始まります。', zh: '尚无消息。发送第一条消息即可开始此聊天室。' },
    'chat.inputPlaceholder': { ko: '메시지를 입력하세요', en: 'Type a message', ja: 'メッセージを入力', zh: '输入消息' },
    'chat.transcribing': { ko: '⏳ 인식 중…', en: '⏳ Recognizing…', ja: '⏳ 認識中…', zh: '⏳ 识别中…' },
    'chat.inviteOpen': { ko: '멤버 초대', en: 'Invite members', ja: 'メンバー招待', zh: '邀请成员' },
    'chat.inviteClose': { ko: '초대 닫기', en: 'Close invite', ja: '招待を閉じる', zh: '关闭邀请' },
    'chat.settingsOpen': { ko: '방 설정', en: 'Room settings', ja: 'ルーム設定', zh: '房间设置' },
    'chat.settingsClose': { ko: '설정 닫기', en: 'Close settings', ja: '設定を閉じる', zh: '关闭设置' },
    'chat.inviteSaving': { ko: '초대 중...', en: 'Inviting...', ja: '招待中...', zh: '邀请中...' },
    'chat.inviteSubmit': { ko: '선택 멤버 초대', en: 'Invite selected', ja: '選択メンバーを招待', zh: '邀请所选成员' },
    'chat.settingsSaving': { ko: '설정 저장 중...', en: 'Saving settings...', ja: '設定を保存中...', zh: '正在保存设置...' },
    'chat.settingsLoading': { ko: '현재 설정 불러오는 중...', en: 'Loading settings...', ja: '設定を読み込み中...', zh: '正在加载设置...' },
    'chat.loadRoomFailed': { ko: '대화방을 불러오지 못했습니다.', en: 'Could not load chat room.', ja: 'チャットルームを読み込めませんでした。', zh: '无法加载聊天室。' },
    'chat.sendFailed': { ko: '메시지를 전송하지 못했습니다.', en: 'Could not send message.', ja: 'メッセージを送信できませんでした。', zh: '无法发送消息。' },
    'chat.inviteFailed': { ko: '멤버를 초대하지 못했습니다.', en: 'Could not invite members.', ja: 'メンバーを招待できませんでした。', zh: '无法邀请成员。' },
    'chat.settingsFailed': { ko: '방 설정을 저장하지 못했습니다.', en: 'Could not save room settings.', ja: 'ルーム設定を保存できませんでした。', zh: '无法保存房间设置。' },
    'chat.memberLimitFailed': { ko: '방 정원을 저장하지 못했습니다.', en: 'Could not save member limit.', ja: '定員を保存できませんでした。', zh: '无法保存人数上限。' },
    'chat.directSubtitle': { ko: '1:1 대화', en: '1:1 chat', ja: '1対1チャット', zh: '一对一聊天' },
    'chat.directSubtitleAuto': { ko: '1:1 대화 · 상대 언어로 자동 번역', en: '1:1 chat · auto-translate to peer language', ja: '1対1 · 相手の言語に自動翻訳', zh: '一对一 · 自动译为对方语言' },
    'chat.groupInviteAllowed': { ko: '멤버 초대 허용', en: 'Members can invite', ja: 'メンバー招待を許可', zh: '允许成员邀请' },
    'chat.groupInviteOwnerOnly': { ko: 'owner만 초대', en: 'Owner only can invite', ja: 'オーナーのみ招待', zh: '仅所有者可邀请' },
    'chat.groupFullNoInvite': { ko: '정원 만석으로 추가 초대 불가', en: 'Room full — cannot invite more', ja: '定員満杯のため追加招待不可', zh: '已满员，无法继续邀请' },
    'chat.groupInviteAllowedFull': { ko: '정책은 멤버 초대 허용이지만 정원 만석으로 추가 초대 불가', en: 'Invites allowed but room is full', ja: '招待は許可されていますが定員満杯です', zh: '允许邀请但已满员' },
    'chat.currentPrefix': { ko: '현재: ', en: 'Current: ', ja: '現在: ', zh: '当前: ' },
    'chat.online': { ko: '● 온라인', en: '● Online', ja: '● オンライン', zh: '● 在线' },
    'chat.snsInvite': { ko: '📨 SNS 초대', en: '📨 SNS invite', ja: '📨 SNS招待', zh: '📨 SNS邀请' },
    'chat.settingsTitle': { ko: '방 설정', en: 'Room settings', ja: 'ルーム設定', zh: '房间设置' },
    'chat.memberLimitChange': { ko: '정원 변경', en: 'Member limit', ja: '定員変更', zh: '人数上限' },
    'chat.memberLimitMeta': { ko: '생성자 입장 후에도 3명, 5명, 10명 고정방으로 바꿀 수 있습니다. 현재 활성 멤버 수보다 작게는 저장되지 않습니다.', en: 'Change to fixed rooms of 3, 5, or 10 members. Cannot go below active member count.', ja: '作成後も3・5・10名の固定ルームに変更できます。アクティブ人数より小さくは保存できません。', zh: '创建后仍可改为3、5、10人固定房间。不能低于当前活跃成员数。' },
    'chat.memberLimitFixed': { ko: '{count}명 고정', en: '{count} members', ja: '{count}名固定', zh: '固定{count}人' },
    'chat.memberLimitSaving': { ko: '정원 저장 중...', en: 'Saving limit...', ja: '定員を保存中...', zh: '正在保存人数...' },
    'chat.memberLimitSave': { ko: '정원 {count}명으로 저장', en: 'Save limit {count}', ja: '定員{count}名で保存', zh: '保存为{count}人' },
    'chat.memberLimitStatus': { ko: '현재: 정원 {limit}명 · 활성 멤버 {active}명', en: 'Limit {limit} · active {active}', ja: '定員{limit}名 · アクティブ{active}名', zh: '上限{limit}人 · 活跃{active}人' },
    'chat.invitePolicy': { ko: '초대 정책', en: 'Invite policy', ja: '招待ポリシー', zh: '邀请策略' },
    'chat.membersCanInvite': { ko: '멤버도 초대 가능', en: 'Members can invite', ja: 'メンバーも招待可', zh: '成员可邀请' },
    'chat.membersCanInviteMeta': { ko: '끄면 owner만 초대할 수 있고, 켜면 현재 멤버도 새 친구를 초대할 수 있습니다.', en: 'Off: owner only. On: members can invite friends.', ja: 'オフ: オーナーのみ。オン: メンバーも招待可。', zh: '关：仅所有者。开：成员也可邀请。' },
    'chat.invitePanelTitle': { ko: '초대할 친구 선택', en: 'Select friends to invite', ja: '招待する友達を選択', zh: '选择要邀请的好友' },
    'chat.inviteEmpty': { ko: '추가로 초대할 수 있는 친구가 없습니다.', en: 'No more friends to invite.', ja: '追加で招待できる友達がいません。', zh: '没有可继续邀请的好友。' },
    'chat.aiChip': { ko: '✨ WorldLinco AI 실시간 번역', en: '✨ WorldLinco AI live translation', ja: '✨ WorldLinco AIリアルタイム翻訳', zh: '✨ WorldLinco AI 实时翻译' },
    'chat.memberInviteCard': { ko: '멤버 초대', en: 'Member invite', ja: 'メンバー招待', zh: '成员邀请' },
    'chat.worldlincoNotice': { ko: '📣 WorldLinco 안내', en: '📣 WorldLinco notice', ja: '📣 WorldLincoお知らせ', zh: '📣 WorldLinco 通知' },
    'chat.myTranslationFailed': { ko: '내 번역 생성 실패', en: 'Your translation failed', ja: '自分の翻訳生成失敗', zh: '您的翻译生成失败' },
    'chat.loadFriendsFailed': { ko: '초대 가능한 친구를 불러오지 못했습니다.', en: 'Could not load friends to invite.', ja: '招待可能な友達を読み込めませんでした。', zh: '无法加载可邀请的好友。' },
    'chat.memberLimitTooSmall': { ko: '현재 활성 멤버가 {count}명이라 정원을 {limit}명으로 줄일 수 없습니다.', en: 'Cannot reduce limit to {limit} with {count} active members.', ja: 'アクティブ{count}名のため定員を{limit}名に下げられません。', zh: '当前活跃{count}人，无法将上限改为{limit}人。' },
    'chat.deliveryPartial': { ko: '배달 {done}/{total} · 실패 {failed}', en: 'Delivered {done}/{total} · failed {failed}', ja: '配信 {done}/{total} · 失敗 {failed}', zh: '送达 {done}/{total} · 失败 {failed}' },
    'chat.deliveryFailed': { ko: '배달 실패 {failed}/{total}', en: 'Delivery failed {failed}/{total}', ja: '配信失敗 {failed}/{total}', zh: '送达失败 {failed}/{total}' },
    'chat.deliveryPending': { ko: '배달 중 {pending}/{total}', en: 'Delivering {pending}/{total}', ja: '配信中 {pending}/{total}', zh: '送达中 {pending}/{total}' },
    'chat.deliveryDone': { ko: '배달 완료 {done}/{total}', en: 'Delivered {done}/{total}', ja: '配信完了 {done}/{total}', zh: '送达完成 {done}/{total}' },
    'chat.groupSubtitle': { ko: '{members}명 / 정원 {limit}명 · {mode} · {invite}', en: '{members}/{limit} · {mode} · {invite}', ja: '{members}名/定員{limit}名 · {mode} · {invite}', zh: '{members}人/上限{limit}人 · {mode} · {invite}' },
    'chat.am': { ko: '오전', en: 'AM', ja: '午前', zh: '上午' },
    'chat.pm': { ko: '오후', en: 'PM', ja: '午後', zh: '下午' },
    'chat.langAuto': { ko: '자동', en: 'Auto', ja: '自動', zh: '自动' },
    'chat.peerLangAutoTranslate': { ko: '상대 언어로 자동 번역', en: 'Auto-translate to peer language', ja: '相手の言語に自動翻訳', zh: '自动译为对方语言' },
    'chat.peerLangAutoDetect': { ko: '상대 언어 자동 감지', en: 'Auto-detect peer language', ja: '相手の言語を自動検出', zh: '自动检测对方语言' },
    'chat.ocrTitle': { ko: 'OCR 결과', en: 'OCR result', ja: 'OCR結果', zh: 'OCR 结果' },
    'chat.extractLabel': { ko: '추출 텍스트', en: 'Extracted text', ja: '抽出テキスト', zh: '提取文本' },
    'chat.translationLabel': { ko: '번역 텍스트', en: 'Translated text', ja: '翻訳テキスト', zh: '翻译文本' },
    'chat.songTitle': { ko: '노래 번역', en: 'Song translation', ja: '歌詞翻訳', zh: '歌曲翻译' },
    'chat.songMemo': { ko: '원문/작업 메모', en: 'Original / notes', ja: '原文/メモ', zh: '原文/备注' },
    'chat.songLyrics': { ko: '번역 가사', en: 'Translated lyrics', ja: '翻訳歌詞', zh: '翻译歌词' },
    'chat.shareTitle': { ko: '번역 공유', en: 'Translation share', ja: '翻訳共有', zh: '翻译分享' },
    'chat.shareOriginal': { ko: '원문', en: 'Original', ja: '原文', zh: '原文' },
    'chat.shareTranslated': { ko: '번역문', en: 'Translation', ja: '翻訳文', zh: '译文' },

    'pstn.manualModeFallback': { ko: '이 환경은 음성 인식을 지원하지 않아 수동 통역 모드로 전환됩니다.', en: 'Speech recognition is not supported here. Switching to manual interpretation.', ja: 'この環境は音声認識に非対応のため手動通訳モードに切り替えます。', zh: '此环境不支持语音识别，将切换为手动传译模式。' },
    'pstn.contactPicked': { ko: '{name} 번호를 단말 전화번호 저장소에서 선택했습니다. 통역 통화 시작을 누르면 시스템 전화앱으로 이어집니다.', en: 'Selected {name} from contacts. Tap start to open the phone app.', ja: '連絡先から{name}を選択しました。通訳通話開始で電話アプリに接続します。', zh: '已从通讯录选择{name}。点击开始传译通话将打开系统电话。' },
    'pstn.chatOpened': { ko: '{name}님과의 채팅방을 열었습니다.', en: 'Opened chat with {name}.', ja: '{name}さんとのチャットを開きました。', zh: '已打开与{name}的聊天。' },
    'pstn.callOutgoing': { ko: '{name}님께 일반전화 통역 발신 — 통화 중 자동 통역이 전달됩니다.', en: 'Outgoing PSTN call to {name} — auto interpretation during call.', ja: '{name}さんへ一般電話通訳発信 — 通話中に自動通訳されます。', zh: '向{name}发起普通电话传译 — 通话中将自动传译。' },
    'pstn.dialFailed': { ko: '전화앱을 열지 못했습니다. 번호를 확인해 주세요.', en: 'Could not open phone app. Check the number.', ja: '電話アプリを開けませんでした。番号を確認してください。', zh: '无法打开电话应用。请检查号码。' },
    'pstn.dialPadOpened': { ko: '다이얼패드 번호로 시스템 전화앱을 열었습니다. 통화 후 수동 통역 모드를 사용하세요.', en: 'Opened phone app with dial pad number. Use manual interpretation after connecting.', ja: 'ダイヤル番号で電話アプリを開きました。通話後は手動通訳をご利用ください。', zh: '已用拨号盘号码打开电话应用。接通后请使用手动传译。' },
    'pstn.contactsCancelled': { ko: '단말 전화번호 저장소 열기를 취소했습니다.', en: 'Cancelled opening contacts.', ja: '連絡先の表示をキャンセルしました。', zh: '已取消打开通讯录。' },
    'pstn.speakerAssistStopped': { ko: '스피커폰 통역 보조를 종료했습니다. 필요하면 텍스트 입력으로 이어가세요.', en: 'Speakerphone interpretation assist stopped. Continue with text if needed.', ja: 'スピーカーフォン通訳補助を終了しました。必要ならテキスト入力をご利用ください。', zh: '已结束扬声器传译辅助。如需可继续用文字输入。' },
    'pstn.speakerAssistReady': { ko: '스피커폰 통역 보조 준비 중 ({delay} 간격)', en: 'Speakerphone assist ready ({delay} interval)', ja: 'スピーカー通訳補助準備中（{delay}間隔）', zh: '扬声器传译辅助准备中（间隔{delay}）' },
    'pstn.autoModeStart': { ko: '{count}개국어 자동 전달 모드 시작', en: 'Auto relay mode started ({count} languages)', ja: '{count}言語自動中継モード開始', zh: '已启动{count}种语言自动中继模式' },
    'pstn.dialPadHint': { ko: '전화번호를 입력하거나 호텔을 선택하면 다이얼패드를 열 수 있습니다.', en: 'Enter a number or pick a hotel to open the dial pad.', ja: '番号を入力するかホテルを選択するとダイヤルを開けます。', zh: '输入号码或选择酒店即可打开拨号盘。' },
    'pstn.translationError': { ko: '통역 통화 처리 중 오류가 발생했습니다.', en: 'Error during interpretation call.', ja: '通訳通話の処理中にエラーが発生しました。', zh: '传译通话处理出错。' },
    'pstn.speechError': { ko: '음성 인식 오류. 다시 시도하세요.', en: 'Speech recognition error. Try again.', ja: '音声認識エラー。再試行してください。', zh: '语音识别错误。请重试。' },
    'pstn.browserTtsUnavailable': { ko: '브라우저 TTS를 사용할 수 없습니다.', en: 'Browser TTS is unavailable.', ja: 'ブラウザTTSを使用できません。', zh: '无法使用浏览器 TTS。' },
    'pstn.contactInviteSent': { ko: '📨 {name}님에게 채팅 초대를 보냈습니다.', en: '📨 Chat invite sent to {name}.', ja: '📨 {name}さんにチャット招待を送信しました。', zh: '📨 已向{name}发送聊天邀请。' },
    'pstn.contactNotRegistered': { ko: '📨 {name}님은 아직 미가입입니다. 초대 공유를 취소했습니다.', en: '📨 {name} is not registered yet. Invite share cancelled.', ja: '📨 {name}さんは未登録です。招待共有をキャンセルしました。', zh: '📨 {name}尚未注册。已取消邀请分享。' },
    'pstn.chatStartFailedTitle': { ko: '채팅 시작 실패', en: 'Could not start chat', ja: 'チャット開始失敗', zh: '无法开始聊天' },
    'pstn.chatStartFailedBody': { ko: '연락처로 채팅을 시작하지 못했습니다.', en: 'Could not start chat from contact.', ja: '連絡先からチャットを開始できませんでした。', zh: '无法从联系人开始聊天。' },
    'pstn.contactChooserPrompt': { ko: '무엇을 할까요?', en: 'What would you like to do?', ja: '何をしますか？', zh: '要做什么？' },
    'pstn.contactChatInvite': { ko: '💬 채팅/초대', en: '💬 Chat / invite', ja: '💬 チャット/招待', zh: '💬 聊天/邀请' },
    'pstn.contactInterCall': { ko: '📞 일반통화', en: '📞 Phone call', ja: '📞 一般通話', zh: '📞 普通电话' },
    'pstn.cancel': { ko: '취소', en: 'Cancel', ja: 'キャンセル', zh: '取消' },
    'pstn.friendChatStartFailedBody': { ko: '친구 채팅을 시작하지 못했습니다.', en: 'Could not start friend chat.', ja: '友達チャットを開始できませんでした。', zh: '无法开始好友聊天。' },
    'pstn.callWaiting': { ko: '통화 대기 중...', en: 'Waiting for call...', ja: '通話待機中...', zh: '等待通话...' },
    'pstn.voiceAssistStop': { ko: '⏹️ 스피커폰 통역 보조 중지', en: '⏹️ Stop speakerphone assist', ja: '⏹️ スピーカー通訳補助を停止', zh: '⏹️ 停止扬声器传译辅助' },
    'pstn.voiceAssistPreparing': { ko: '⏳ 스피커폰 통역 보조 준비 중', en: '⏳ Preparing speakerphone assist', ja: '⏳ スピーカー通訳補助を準備中', zh: '⏳ 正在准备扬声器传译辅助' },
    'pstn.voiceAssistStart': { ko: '🎙️ 스피커폰 통역 보조 시작', en: '🎙️ Start speakerphone assist', ja: '🎙️ スピーカー通訳補助を開始', zh: '🎙️ 开始扬声器传译辅助' },
    'pstn.speakerAssistHint': { ko: '스피커폰으로 상대 음성을 들리게 한 뒤 이 보조를 켜면 주변 음성을 구간별로 받아 번역 후 TTS로 재송출합니다.', en: 'Enable speakerphone, then turn on assist to capture speech in segments, translate, and replay via TTS.', ja: 'スピーカーで相手の音声を聞かせた後、この補助をONにすると周囲の音声を区間ごとに翻訳してTTSで再生します。', zh: '打开扬声器听到对方声音后，开启此辅助将分段采集周围语音、翻译并通过 TTS 播放。' },
    'pstn.autoRelayInterval': { ko: '자동 전송 간격: {delay}', en: 'Auto-send interval: {delay}', ja: '自動送信間隔: {delay}', zh: '自动发送间隔: {delay}' },
    'pstn.manualInputPlaceholder': { ko: '들린 내용을 입력하세요', en: 'Type what you heard', ja: '聞き取った内容を入力', zh: '输入听到的内容' },
    'pstn.sendNow': { ko: '즉시 전송', en: 'Send now', ja: '今すぐ送信', zh: '立即发送' },
    'pstn.interCallHint': { ko: '일반통화는 여행 예약 섹션에서 관리하며, 통화가 열리면 {count}개국어 자동 전달 보조가 시작됩니다. 단말 전화번호 저장소에서 선택한 번호 또는 직접 입력한 번호를 시스템 전화앱으로 넘겨 통역을 이어갑니다.', en: 'Regular calls are managed in Travel Booking. When a call starts, auto-relay assist begins in {count} languages. Pick a number from contacts or enter one to hand off to the phone app.', ja: '一般通話は旅行予約セクションで管理します。通話が始まると{count}言語の自動配信補助が開始されます。', zh: '普通通话在旅行预订区管理。通话开始后启动 {count} 种语言的自动传递辅助。' },
    'pstn.interToggleEnd': { ko: '📵 일반 통화 종료', en: '📵 End regular call', ja: '📵 一般通話を終了', zh: '📵 结束普通通话' },
    'pstn.interToggleStart': { ko: '📞 일반 통화 + 자동 전달 시작', en: '📞 Regular call + auto relay', ja: '📞 一般通話＋自動配信開始', zh: '📞 普通通话 + 自动传递' },
    'home.greeting': { ko: '안녕하세요! 👋', en: 'Hello! 👋', ja: 'こんにちは! 👋', zh: '你好! 👋' },
    'home.greetingSub': { ko: '오늘도 좋은 하루 보내세요.', en: 'Have a great day.', ja: '今日も良い一日を。', zh: '祝您今天愉快。' },
    'home.faceTitle': { ko: '대면 통역', en: 'Face-to-face', ja: '対面通訳', zh: '面对面传译' },
    'home.faceSub': { ko: 'Face-to-face Interpretation', en: 'Face-to-face Interpretation', ja: 'Face-to-face Interpretation', zh: 'Face-to-face Interpretation' },
    'home.faceCtaOn': { ko: '대화 통역 ON · 탭하여 끄기', en: 'Interpretation ON · tap to stop', ja: '通訳ON · タップで停止', zh: '传译开启 · 点击停止' },
    'home.faceCtaOff': { ko: '탭하여 시작', en: 'Tap to start', ja: 'タップして開始', zh: '点击开始' },
    'face.peerPlaceholder': { ko: '상대에게 보여줄 번역이 여기에 표시됩니다.', en: 'Translation for your partner appears here.', ja: '相手に見せる翻訳がここに表示されます。', zh: '给对方看的翻译将显示在此。' },
    'face.mePlaceholder': { ko: '내가 말한 내용이 여기에 표시됩니다.', en: 'What you said appears here.', ja: 'あなたの発話がここに表示されます。', zh: '您说的话将显示在此。' },
    'face.tapListening': { ko: '👆 듣는 중 · 말이 끝나면 자동 번역', en: '👆 Listening · auto-translate when you finish', ja: '👆 聞いています · 話し終わると自動翻訳', zh: '👆 正在聆听 · 说完后自动翻译' },
    'face.tapToSpeak': { ko: '👆 말하려면 탭하세요', en: '👆 Tap to speak', ja: '👆 タップして話す', zh: '👆 点击说话' },
    'chat.list.title': { ko: '채팅', en: 'Chat', ja: 'チャット', zh: '聊天' },
    'chat.list.summaryTitle': { ko: '채팅 알림 요약', en: 'Chat alerts', ja: 'チャット通知', zh: '聊天提醒' },
    'chat.list.summaryMetric': { ko: '{rooms}개 방 · {unread}개 미확인', en: '{rooms} rooms · {unread} unread', ja: '{rooms}室 · 未読{unread}', zh: '{rooms} 个房间 · {unread} 条未读' },
    'chat.list.noPreview': { ko: '최근 메시지 미리보기가 없습니다.', en: 'No recent message preview.', ja: '最近のメッセージプレビューがありません。', zh: '暂无最近消息预览。' },
    'chat.list.noRecentTime': { ko: '최근 수신 시각 없음', en: 'No recent time', ja: '最近の受信時刻なし', zh: '无最近接收时间' },
    'chat.list.noRecentChat': { ko: '최근 대화가 없습니다.', en: 'No recent chats.', ja: '最近の会話がありません。', zh: '暂无最近对话。' },
    'chat.list.openVault': { ko: '번역 보관함 열기', en: 'Open translation vault', ja: '翻訳保管庫を開く', zh: '打开翻译保管库' },
    'chat.list.opening': { ko: '여는 중...', en: 'Opening...', ja: '開いています...', zh: '正在打开...' },
    'chat.list.closeGroup': { ko: '그룹방 닫기', en: 'Close group composer', ja: 'グループ作成を閉じる', zh: '关闭群组创建' },
    'chat.list.createGroup': { ko: '그룹방 만들기', en: 'Create group', ja: 'グループを作成', zh: '创建群组' },
    'chat.list.refreshing': { ko: '새로고침 중...', en: 'Refreshing...', ja: '更新中...', zh: '正在刷新...' },
    'chat.list.refresh': { ko: '새로고침', en: 'Refresh', ja: '更新', zh: '刷新' },
    'chat.list.groupTitle': { ko: '그룹방 만들기', en: 'Create group room', ja: 'グループルームを作成', zh: '创建群组房间' },
    'chat.list.groupHint': { ko: '친구를 골라 번역 채팅방을 바로 열 수 있습니다.', en: 'Pick friends to open a translation chat room.', ja: '友達を選んで翻訳チャットルームを開けます。', zh: '选择好友即可打开翻译聊天室。' },
    'chat.list.groupPlaceholder': { ko: '예: 일본 여행 통역방', en: 'e.g. Japan trip room', ja: '例: 日本旅行通訳ルーム', zh: '例：日本旅行传译室' },
    'chat.list.capacityTitle': { ko: '방 정원 선택', en: 'Room capacity', ja: '定員を選択', zh: '选择房间容量' },
    'chat.list.capacityMeta': { ko: '방장 포함 기준으로 3명, 5명, 10명 고정방을 만들 수 있습니다. 현재 {count}명 입장 예정', en: 'Fixed rooms for 3, 5, or 10 including host. {count} joining now.', ja: 'ホスト含め3/5/10名の固定ルーム。現在{count}名参加予定。', zh: '含群主固定 3/5/10 人房间。当前预计 {count} 人加入。' },
    'chat.list.memberInviteTitle': { ko: '멤버도 초대 가능', en: 'Members can invite', ja: 'メンバーも招待可', zh: '成员可邀请' },
    'chat.list.memberInviteMeta': { ko: '끄면 owner만 초대할 수 있고, 켜면 기존 멤버도 새 친구를 초대할 수 있습니다.', en: 'Off: owner only. On: members can invite friends.', ja: 'OFF: オーナーのみ。ON: メンバーも招待可。', zh: '关：仅群主。开：成员也可邀请。' },
    'chat.list.noFriendsForGroup': { ko: '먼저 친구를 추가해야 그룹방을 만들 수 있습니다.', en: 'Add friends first to create a group.', ja: 'まず友達を追加してください。', zh: '请先添加好友再创建群组。' },
    'chat.list.creatingGroup': { ko: '그룹방 생성 중...', en: 'Creating group...', ja: 'グループ作成中...', zh: '正在创建群组...' },
    'chat.list.openGroup': { ko: '선택 멤버로 그룹방 열기', en: 'Open group with selected', ja: '選択メンバーでグループを開く', zh: '用所选成员打开群组' },
    'chat.list.friendsTitle': { ko: '친구 — 눌러서 바로 연결', en: 'Friends — tap to connect', ja: '友達 — タップで接続', zh: '好友 — 点击即连' },
    'chat.list.noFriends': { ko: '아직 등록된 친구가 없습니다. VoIP 친구 찾기 · 전화번호로 찾기 · 지도로 찾기로 친구를 추가하세요.', en: 'No friends yet. Add via VoIP find, phone, or map.', ja: '友達がいません。VoIP・電話番号・地図から追加してください。', zh: '暂无好友。请通过 VoIP、电话或地图添加。' },
    'chat.list.voipCall': { ko: '📡 통역통화', en: '📡 Interpret call', ja: '📡 通訳通話', zh: '📡 传译通话' },
    'chat.list.chatBtn': { ko: '💬 채팅', en: '💬 Chat', ja: '💬 チャット', zh: '💬 聊天' },
    'chat.list.recentRooms': { ko: '최근 대화방', en: 'Recent rooms', ja: '最近のルーム', zh: '最近房间' },
    'chat.list.noRooms': { ko: '아직 생성된 채팅방이 없습니다. 번역 보관함 또는 친구 채팅부터 시작하세요.', en: 'No chat rooms yet. Start from vault or a friend.', ja: 'チャットルームがありません。保管庫または友達から始めてください。', zh: '暂无聊天室。从保管库或好友聊天开始。' },
    'chat.list.noMessages': { ko: '메시지가 아직 없습니다.', en: 'No messages yet.', ja: 'まだメッセージがありません。', zh: '暂无消息。' },
    'chat.list.langUnset': { ko: '미설정', en: 'Not set', ja: '未設定', zh: '未设置' },
    'chat.list.alertGroupInvite': { ko: '그룹 초대', en: 'Group invite', ja: 'グループ招待', zh: '群组邀请' },
    'chat.list.alertAnnouncement': { ko: '공지 도착', en: 'Announcement', ja: 'お知らせ', zh: '公告到达' },
    'chat.list.alertTranslation': { ko: '번역 결과 도착', en: 'Translation arrived', ja: '翻訳結果', zh: '翻译结果到达' },
    'chat.list.alertNewMessage': { ko: '새 메시지', en: 'New message', ja: '新着', zh: '新消息' },
    'chat.list.directRoom': { ko: '1:1 대화', en: '1:1 chat', ja: '1対1', zh: '一对一' },
    'chat.list.groupRoomMeta': { ko: '{count}명 참여 · 정원 {limit}명 고정', en: '{count} members · cap {limit}', ja: '{count}名参加 · 定員{limit}', zh: '{count} 人参与 · 上限 {limit}' },
    'chat.list.loadFailed': { ko: '채팅방 목록을 불러오지 못했습니다.', en: 'Could not load chat rooms.', ja: 'チャット一覧を読み込めませんでした。', zh: '无法加载聊天室列表。' },
    'chat.list.vaultFailed': { ko: '번역 보관함을 열지 못했습니다.', en: 'Could not open translation vault.', ja: '翻訳保管庫を開けませんでした。', zh: '无法打开翻译保管库。' },
    'chat.list.friendRoomFailed': { ko: '친구 채팅방을 열지 못했습니다.', en: 'Could not open friend chat.', ja: '友達チャットを開けませんでした。', zh: '无法打开好友聊天。' },
    'chat.list.groupFailed': { ko: '그룹방을 만들지 못했습니다.', en: 'Could not create group.', ja: 'グループを作成できませんでした。', zh: '无法创建群组。' },
    'chat.list.groupNameRequired': { ko: '그룹방 이름을 입력해야 합니다.', en: 'Enter a group name.', ja: 'グループ名を入力してください。', zh: '请输入群组名称。' },
    'chat.list.groupMemberRequired': { ko: '초대할 친구를 한 명 이상 선택해야 합니다.', en: 'Select at least one friend.', ja: '友達を1人以上選択してください。', zh: '请至少选择一位好友。' },
    'chat.list.groupOverCapacity': { ko: '현재 선택 인원은 정원 {limit}명을 초과합니다.', en: 'Selected members exceed cap of {limit}.', ja: '選択人数が定員{limit}を超えています。', zh: '所选人数超过上限 {limit}。' },
    'chat.list.groupCapacityLimit': { ko: '정원 {limit}명 방은 방장을 포함해 최대 {limit}명까지만 입장할 수 있습니다.', en: 'Rooms capped at {limit} including host.', ja: '定員{limit}名（ホスト含む）までです。', zh: '含群主最多 {limit} 人。' },
    'chat.list.fixedMembers': { ko: '{n}명 고정', en: '{n} fixed', ja: '{n}名固定', zh: '固定 {n} 人' },

    'user.meSide': { ko: '나', en: 'Me', ja: '自分', zh: '我' },
    'user.peerSide': { ko: '상대', en: 'Peer', ja: '相手', zh: '对方' },
    'user.bidirectionalMode': { ko: '자동 양방향 통역', en: 'Auto bidirectional interpretation', ja: '自動双方向通訳', zh: '自动双向传译' },
    'user.mySpeechInput': { ko: '내 말하기 입력 대기', en: 'Waiting for your speech', ja: '自分の発話入力待ち', zh: '等待您说话' },
    'user.peerSpeechInput': { ko: '상대 말하기 입력 대기', en: 'Waiting for peer speech', ja: '相手の発話入力待ち', zh: '等待对方说话' },
    'user.listening': { ko: '듣는 중…', en: 'Listening…', ja: '聞いています…', zh: '正在聆听…' },
    'user.translating': { ko: '번역 중…', en: 'Translating…', ja: '翻訳中…', zh: '翻译中…' },
    'user.speaking': { ko: '전달 중…', en: 'Speaking…', ja: '再生中…', zh: '正在播放…' },
};

function applyVars(template: string, vars?: Record<string, string | number>): string {
    if (!vars) return template;
    return Object.entries(vars).reduce(
        (out, [key, value]) => out.replace(new RegExp(`\\{${key}\\}`, 'g'), String(value)),
        template,
    );
}

/** 기능 화면 UI 문자열 — 동기·오프라인(ko/en/ja/zh), 그 외 en 즉시 폴백. */
export function getFeatureUiText(
    key: FeatureUiKey,
    vars?: Record<string, string | number>,
    lang?: string,
): string {
    const catalogLang = resolveBundledCatalogLang(lang ?? getUiLang());
    const row = ROWS[key];
    const template = row?.[catalogLang] ?? row?.en ?? key;
    return applyVars(template, vars);
}

export function getAllFeatureUiKeys(): FeatureUiKey[] {
    return Object.keys(ROWS) as FeatureUiKey[];
}
