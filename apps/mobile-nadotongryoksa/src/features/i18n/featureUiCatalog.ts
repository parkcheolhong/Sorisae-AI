/**
 * VoIP · 채팅 · PSTN 기능 UI — ko/en/ja/zh 오프라인 정적 카탈로그.
 * 런타임 API 번역 없이 즉시 표시(한국어 플래시 금지).
 */
import { getEffectiveUiLang } from './uiI18n';
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
    // Song / Voice profile
    | 'song.loginRequiredForPurchase' | 'song.purchaseRequired' | 'song.uploadStart'
    | 'song.uploadPlaybackFallback' | 'song.jobProgress' | 'song.timelineReady'
    | 'song.timelineError' | 'song.fileProcessFailed' | 'song.segmentSaved'
    | 'song.segmentSaveError' | 'song.subtitleSaveFailed' | 'song.exportPreviewReady'
    | 'song.exportPreviewError' | 'song.exportFailed' | 'song.voiceSamplePreparing'
    | 'song.voiceProfileReadyEncrypted' | 'song.voiceSampleCanceled'
    | 'song.recordedProfileReady' | 'song.voiceSampleRecording'
    | 'song.voiceSampleRecordingStartFailed' | 'song.voiceProfileDeleted'
    | 'song.voiceProfileDeleteFailed' | 'song.voicePreviewPolicyChecking'
    | 'song.voicePreviewFailed' | 'song.voiceSampleUploadFailed'
    | 'song.voiceRecordingUploadFailed'
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
    | 'pstn.interCallHint' | 'pstn.interToggleEnd' | 'pstn.interToggleStart' | 'pstn.peerLanguageLabel' | 'pstn.peerLanguageHint'
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
    | 'user.listening' | 'user.translating' | 'user.speaking'
    // Navigation tabs
    | 'nav.tabChat' | 'nav.tabVoip' | 'nav.tabPromo' | 'nav.tabTravel' | 'nav.tabSettings'
    | 'nav.tabFaceInterpret' | 'nav.tabChatMode' | 'nav.tabPhraseBook'
    // Home / Travel / VoIP friends / Tourism / Sorisae
    | 'home.translateHome' | 'home.loginSignup' | 'home.logout'
    | 'home.quickVoip' | 'home.quickVoipSub' | 'home.quickChat' | 'home.quickChatSub'
    | 'home.toolsTitle' | 'home.toolsSub'
    | 'travel.hubHero' | 'travel.flight' | 'travel.flightSub' | 'travel.hotel' | 'travel.hotelSub'
    | 'travel.nearby' | 'travel.nearbySub' | 'travel.itinerary' | 'travel.itinerarySub'
    | 'travel.nearbyRecommend' | 'travel.nearbyRecommendSub' | 'travel.searchSectionTitle' | 'travel.searchSectionSub'
    | 'travel.latLabel' | 'travel.lonLabel' | 'travel.categoryLabel' | 'travel.radiusLabel' | 'travel.searchBtn'
    | 'travel.mapPreview' | 'travel.searchResults' | 'travel.viewOnMap' | 'travel.googleMaps' | 'travel.bookingSelect'
    | 'map.openGoogleMaps'
    | 'travel.selectedPlace' | 'travel.selectedPlaceMeta' | 'travel.selectedPlaceDone'
    | 'travel.bookingSection' | 'travel.bookingSectionSub' | 'travel.interCallPlaceholder' | 'travel.openDialpad'
    | 'travel.catAll' | 'travel.catHotel' | 'travel.catAirport' | 'travel.catRestaurant' | 'travel.catAttraction'
    | 'voip.friendsTitle' | 'voip.friendsSubtitle' | 'voip.friendsSearch' | 'voip.friendsEmpty'
    | 'voip.friendsNoSearch' | 'voip.friendsLoadError' | 'voip.appFriendBadge'
    | 'voip.tabContacts' | 'voip.tabRecents' | 'voip.tabKeypad'
    | 'tourism.promoTitle' | 'tourism.promoIntro' | 'tourism.translating'
    | 'tourism.gpsRequired' | 'tourism.emptyBoard' | 'tourism.nearbyBadge' | 'tourism.radiusKm'
    | 'tourism.composeClose' | 'tourism.composeOpen' | 'tourism.postSuccess' | 'tourism.postFailed'
    | 'manual.back'
    | 'travel.bookingCallAirport' | 'travel.bookingCallHotel' | 'travel.bookingSupportCall'
    | 'sorisae.voiceCallArmOn' | 'sorisae.voiceCallArmOff' | 'sorisae.voiceCallArmed'
    | 'sorisae.windowClose' | 'sorisae.windowEmpty' | 'sorisae.questionLabel' | 'sorisae.answerLabel'
    | 'sorisae.clearLog' | 'sorisae.startConversation' | 'sorisae.waveHintSpeaking' | 'sorisae.waveHintListening'
    | 'sorisae.scheduleBasis' | 'sorisae.transportFallback' | 'sorisae.originPin' | 'sorisae.destinationPin'
    | 'sorisae.convEnded' | 'sorisae.convStarted' | 'sorisae.webChatOnly' | 'sorisae.wakeSuccess'
    | 'sorisae.wakeArmedStatus' | 'sorisae.wakeEnded' | 'sorisae.dormant' | 'sorisae.webWakeOnly'
    | 'capture.micWebUnsupportedTitle' | 'capture.micWebUnsupportedBody' | 'capture.recordErrorTitle'
    | 'capture.voiceInputFailed' | 'capture.listeningSorisae' | 'capture.wakeCallWait' | 'capture.preparingAnswer'
    | 'capture.gpsOff' | 'capture.echoIgnored' | 'capture.server502' | 'capture.server503'
    | 'capture.serverError' | 'capture.loginRequired' | 'capture.answerFailed' | 'capture.segmentErrorContinue'
    | 'capture.interCallTranslateFailed' | 'capture.voiceProcessError'
    | 'capture.langPair' | 'capture.continueListening' | 'capture.interCallListening'
    | 'face.webOnlyTitle' | 'face.webOnlyBody' | 'face.peerLangTitle'
    | 'gps.checkingPermission' | 'gps.deniedStatus' | 'gps.permissionBlocked' | 'gps.permissionNeeded'
    | 'gps.permissionTitle' | 'gps.resolving' | 'gps.resolvedStatus' | 'gps.failedStatus'
    | 'gps.failedTitle' | 'gps.failedBody' | 'gps.openSettings' | 'common.ok'
    | 'gps.reasonServicesDisabled' | 'gps.reasonUnavailable' | 'gps.reasonTimeout'
    | 'gps.modeSatellite' | 'gps.modeHybrid' | 'gps.modeWifiFallback' | 'gps.modeAdbMock' | 'gps.modeCached'
    | 'gps.langRecommend' | 'gps.regionSuffix'
    | 'voip.recentsPeerMissing' | 'voip.recentsNotFoundBody' | 'voip.redialNoNumber' | 'voip.redialNoNumberBody'
    | 'pstn.dialPadOpenFailed' | 'pstn.dialPadWebTitle' | 'pstn.dialPadWebBody'
    | 'pstn.contactsWebTitle' | 'pstn.contactsWebBody'
    | 'chat.hubTitle' | 'chat.hubVoipFriends' | 'chat.hubVoipFriendsSub' | 'chat.hubPhoneFind'
    | 'chat.hubPhoneFindSub' | 'chat.hubMapFind' | 'chat.hubMapFindSub' | 'chat.hubGroup'
    | 'chat.hubGroupSub' | 'chat.hubNearbyTitle' | 'chat.hubNearbySub'
    | 'contacts.title' | 'contacts.searchPlaceholder' | 'contacts.loadErrorEmpty' | 'contacts.loadFailed'
    | 'contacts.loading' | 'contacts.noSearch' | 'contacts.noList' | 'contacts.appFriendBadge'
    | 'contacts.actionCall' | 'contacts.actionSms' | 'contacts.actionVoip' | 'contacts.actionChat'
    | 'contacts.actionInvite' | 'contacts.promoShare' | 'contacts.count' | 'contacts.refresh'
    | 'contacts.refreshing' | 'contacts.close' | 'contacts.collapse' | 'contacts.expand'
    | 'contacts.collapseMeta' | 'contacts.rowClose' | 'contacts.rowOpen';

type CatalogRow = Record<BundledUiLang, string>;

const ROWS: Record<FeatureUiKey, CatalogRow> = {
    'voip.remoteParty': { ko: '상대', en: 'Peer', ja: '相手', zh: '对方' },
    'voip.me': { ko: '나', en: 'Me', ja: '自分', zh: '我' },
    'voip.micListening': { ko: '마이크 듣는 중 · 말이 끝나면 자동 번역', en: 'Listening · auto-translate when you finish', ja: '聞いています · 話し終わると自動翻訳', zh: '正在聆听 · 说完后自动翻译' },
    'voip.micListeningVad': { ko: '마이크 듣는 중 · 음성 감지 후 자동 번역', en: 'Listening · auto-translate after voice detected', ja: '聞いています · 音声検出後に自動翻訳', zh: '正在聆听 · 检测到语音后自动翻译' },
    'voip.chatTranslatePending': { ko: '번역 중...', en: 'Translating...', ja: '翻訳中...', zh: '翻译中...' },
    'voip.chatTranslateFailed': { ko: '번역을 불러오지 못했습니다. 원문을 표시합니다.', en: 'Could not load translation. Showing original.', ja: '翻訳を読み込めませんでした。原文を表示します。', zh: '无法加载翻译。显示原文。' },
    'voip.chatAutoTranslate': { ko: '자동 번역', en: 'Auto translation', ja: '自動翻訳', zh: '自动翻译' },
    'voip.chatEmpty': { ko: '아직 통역/채팅이 없습니다.', en: 'No interpretation or chat yet.', ja: 'まだ通訳・チャットがありません。', zh: '尚无传译或聊天。' },
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

    'song.loginRequiredForPurchase': { ko: '🎵 노래 번역 결제는 로그인 후 사용할 수 있습니다.', en: '🎵 Song translation purchase is available after login.', ja: '🎵 歌詞翻訳の購入はログイン後に利用できます。', zh: '🎵 登录后可使用歌曲翻译购买。' },
    'song.purchaseRequired': { ko: '🎵 노래 번역은 건당 결제 후 사용할 수 있습니다.', en: '🎵 Song translation is available per-track after purchase.', ja: '🎵 歌詞翻訳は1曲ごとの購入後に利用できます。', zh: '🎵 歌曲翻译需按曲购买后使用。' },
    'song.uploadStart': { ko: '🎵 노래 파일을 업로드하고 백엔드 자막 작업을 시작합니다.', en: '🎵 Uploading song file and starting subtitle processing.', ja: '🎵 楽曲ファイルをアップロードし、字幕処理を開始します。', zh: '🎵 正在上传歌曲文件并开始字幕处理。' },
    'song.uploadPlaybackFallback': { ko: '🎵 파일 업로드는 계속 진행합니다. 이 기기에서 미리 재생할 수 없는 형식일 수 있습니다.', en: '🎵 Upload continues. This device may not preview this format.', ja: '🎵 アップロードは継続します。この端末ではプレビュー再生できない形式の可能性があります。', zh: '🎵 上传继续进行。此设备可能无法预览该格式。' },
    'song.jobProgress': { ko: '🎵 {message} ({progress}%)', en: '🎵 {message} ({progress}%)', ja: '🎵 {message} ({progress}%)', zh: '🎵 {message}（{progress}%）' },
    'song.timelineReady': { ko: '🎵 파일 자막 준비: {from} → {to} · {count}개 구간 · 품질 {quality}%', en: '🎵 Subtitles ready: {from} → {to} · {count} segments · quality {quality}%', ja: '🎵 字幕準備完了: {from} → {to} · {count}区間 · 品質 {quality}%', zh: '🎵 字幕已就绪：{from} → {to} · {count} 段 · 质量 {quality}%' },
    'song.timelineError': { ko: '🎵 파일 자막 오류: {message}', en: '🎵 Subtitle error: {message}', ja: '🎵 字幕エラー: {message}', zh: '🎵 字幕错误：{message}' },
    'song.fileProcessFailed': { ko: '노래 파일 처리에 실패했습니다.', en: 'Song file processing failed.', ja: '楽曲ファイルの処理に失敗しました。', zh: '歌曲文件处理失败。' },
    'song.segmentSaved': { ko: '🎵 {time} 구간 번역을 저장했습니다.', en: '🎵 Saved translation for segment {time}.', ja: '🎵 {time} 区間の翻訳を保存しました。', zh: '🎵 已保存 {time} 段翻译。' },
    'song.segmentSaveError': { ko: '🎵 자막 편집 오류: {message}', en: '🎵 Subtitle edit error: {message}', ja: '🎵 字幕編集エラー: {message}', zh: '🎵 字幕编辑错误：{message}' },
    'song.subtitleSaveFailed': { ko: '자막 편집 저장 실패', en: 'Failed to save subtitle edit', ja: '字幕編集の保存に失敗しました', zh: '字幕编辑保存失败' },
    'song.exportPreviewReady': { ko: '🎵 {format} 자막 내보내기 미리보기를 생성했습니다.', en: '🎵 Generated {format} subtitle export preview.', ja: '🎵 {format} 字幕エクスポートのプレビューを生成しました。', zh: '🎵 已生成 {format} 字幕导出预览。' },
    'song.exportPreviewError': { ko: '🎵 자막 내보내기 오류: {message}', en: '🎵 Subtitle export error: {message}', ja: '🎵 字幕エクスポートエラー: {message}', zh: '🎵 字幕导出错误：{message}' },
    'song.exportFailed': { ko: '자막 내보내기 실패', en: 'Subtitle export failed', ja: '字幕エクスポートに失敗しました', zh: '字幕导出失败' },
    'song.voiceSamplePreparing': { ko: '내 목소리 사용 동의를 확인하고 샘플 파일을 준비합니다.', en: 'Checking consent and preparing voice sample file.', ja: '同意を確認し、音声サンプルを準備します。', zh: '正在确认同意并准备语音样本文件。' },
    'song.voiceProfileReadyEncrypted': { ko: '목소리 프로필 준비됨 · 품질 {quality}% · 암호화 저장', en: 'Voice profile ready · quality {quality}% · encrypted', ja: '音声プロファイル準備完了 · 品質 {quality}% · 暗号化保存', zh: '语音档案已就绪 · 质量 {quality}% · 已加密保存' },
    'song.voiceSampleCanceled': { ko: '샘플 선택이 취소되었습니다.', en: 'Sample selection was canceled.', ja: 'サンプル選択がキャンセルされました。', zh: '已取消样本选择。' },
    'song.recordedProfileReady': { ko: '녹음 샘플 프로필 준비됨 · 품질 {quality}%', en: 'Recorded sample profile ready · quality {quality}%', ja: '録音サンプルのプロファイル準備完了 · 品質 {quality}%', zh: '录音样本档案已就绪 · 质量 {quality}%' },
    'song.voiceSampleRecording': { ko: '목소리 샘플 녹음 중입니다. 20초 이상 또렷하게 읽어 주세요.', en: 'Recording voice sample. Please read clearly for 20+ seconds.', ja: '音声サンプルを録音中です。20秒以上はっきり読んでください。', zh: '正在录制语音样本。请清晰朗读 20 秒以上。' },
    'song.voiceSampleRecordingStartFailed': { ko: '목소리 샘플 녹음을 시작할 수 없습니다.', en: 'Could not start voice sample recording.', ja: '音声サンプル録音を開始できませんでした。', zh: '无法开始语音样本录制。' },
    'song.voiceProfileDeleted': { ko: '목소리 프로필과 서버 샘플이 삭제되었습니다.', en: 'Voice profile and server sample were deleted.', ja: '音声プロファイルとサーバーサンプルを削除しました。', zh: '语音档案和服务器样本已删除。' },
    'song.voiceProfileDeleteFailed': { ko: '목소리 프로필 삭제 실패', en: 'Failed to delete voice profile', ja: '音声プロファイルの削除に失敗しました', zh: '语音档案删除失败' },
    'song.voicePreviewPolicyChecking': { ko: '번역가사 voice preview 정책 게이트를 확인합니다.', en: 'Checking policy gates for translated-lyrics voice preview.', ja: '翻訳歌詞の音声プレビューに対するポリシーゲートを確認します。', zh: '正在检查翻译歌词语音预览的策略门槛。' },
    'song.voicePreviewFailed': { ko: '번역가사 voice preview 실패', en: 'Translated-lyrics voice preview failed', ja: '翻訳歌詞の音声プレビューに失敗しました', zh: '翻译歌词语音预览失败' },
    'song.voiceSampleUploadFailed': { ko: '목소리 샘플 업로드 실패', en: 'Voice sample upload failed', ja: '音声サンプルのアップロードに失敗しました', zh: '语音样本上传失败' },
    'song.voiceRecordingUploadFailed': { ko: '목소리 녹음 업로드 실패', en: 'Voice recording upload failed', ja: '音声録音のアップロードに失敗しました', zh: '语音录音上传失败' },

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
    'pstn.peerLanguageLabel': { ko: '상대 언어 (GPS/수동)', en: 'Partner language (GPS/manual)', ja: '相手の言語 (GPS/手動)', zh: '对方语言 (GPS/手动)' },
    'pstn.peerLanguageHint': { ko: 'GPS 우선 · ▾ 탭으로 수동 선택 · 내 언어는 설정 탭', en: 'GPS first · tap ▾ to pick manually · my language in Settings', ja: 'GPS優先 · ▾で手動選択 · 自分の言語は設定タブ', zh: 'GPS 优先 · 点 ▾ 手动选择 · 我的语言在设置页' },
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
    'nav.tabChat': { ko: '채팅', en: 'Chat', ja: 'チャット', zh: '聊天' },
    'nav.tabVoip': { ko: '통화', en: 'Calls', ja: '通話', zh: '通话' },
    'nav.tabPromo': { ko: '홍보', en: 'Promo', ja: 'プロモ', zh: '推广' },
    'nav.tabTravel': { ko: '예약', en: 'Travel', ja: '予約', zh: '预订' },
    'nav.tabSettings': { ko: '설정', en: 'Settings', ja: '設定', zh: '设置' },
    'nav.tabFaceInterpret': { ko: '대면 통역', en: 'Face-to-face', ja: '対面通訳', zh: '面对面传译' },
    'nav.tabChatMode': { ko: '대화 모드', en: 'Chat mode', ja: '会話モード', zh: '对话模式' },
    'nav.tabPhraseBook': { ko: '문장 모음', en: 'Phrases', ja: 'フレーズ集', zh: '常用句' },
    'home.translateHome': { ko: '번역 홈', en: 'Translate home', ja: '翻訳ホーム', zh: '翻译首页' },
    'home.loginSignup': { ko: '로그인 / 회원가입', en: 'Log in / Sign up', ja: 'ログイン / 会員登録', zh: '登录 / 注册' },
    'home.logout': { ko: '로그아웃', en: 'Log out', ja: 'ログアウト', zh: '登出' },
    'home.quickVoip': { ko: '통화하기', en: 'Call', ja: '通話する', zh: '通话' },
    'home.quickVoipSub': { ko: 'AI 통역 통화', en: 'AI interpret call', ja: 'AI通訳通話', zh: 'AI 传译通话' },
    'home.quickChat': { ko: '채팅하기', en: 'Chat', ja: 'チャットする', zh: '聊天' },
    'home.quickChatSub': { ko: '실시간 번역 채팅', en: 'Live translation chat', ja: 'リアルタイム翻訳チャット', zh: '实时翻译聊天' },
    'home.toolsTitle': { ko: '정밀 번역 도구', en: 'Precision translate tools', ja: '精密翻訳ツール', zh: '精准翻译工具' },
    'home.toolsSub': { ko: '직접 입력·OCR 번역', en: 'Direct input + OCR', ja: '直接入力・OCR翻訳', zh: '直接输入 + OCR 翻译' },
    'travel.hubHero': { ko: '여행을 한 곳에서 예약하세요', en: 'Book your travel in one place', ja: '旅行をまとめて予約', zh: '一站式预订旅行' },
    'travel.flight': { ko: '항공권', en: 'Flights', ja: '航空券', zh: '机票' },
    'travel.flightSub': { ko: '비행기 예약', en: 'Flight booking', ja: 'フライト予約', zh: '航班预订' },
    'travel.hotel': { ko: '호텔', en: 'Hotels', ja: 'ホテル', zh: '酒店' },
    'travel.hotelSub': { ko: '숙소 예약', en: 'Stay booking', ja: '宿泊予約', zh: '住宿预订' },
    'travel.nearby': { ko: '주변 검색', en: 'Nearby search', ja: '周辺検索', zh: '周边搜索' },
    'travel.nearbySub': { ko: '맛집·관광', en: 'Food & sights', ja: 'グルメ・観光', zh: '美食·景点' },
    'travel.itinerary': { ko: '일정', en: 'Itinerary', ja: '日程', zh: '行程' },
    'travel.itinerarySub': { ko: '여행 타임라인', en: 'Travel timeline', ja: '旅行タイムライン', zh: '旅行时间线' },
    'travel.nearbyRecommend': { ko: '주변 추천', en: 'Nearby picks', ja: '周辺おすすめ', zh: '周边推荐' },
    'travel.nearbyRecommendSub': { ko: '현재 위치 기준 추천', en: 'Recommendations near you', ja: '現在地ベースのおすすめ', zh: '基于当前位置推荐' },
    'travel.searchSectionTitle': { ko: '📍 주변 검색', en: '📍 Nearby search', ja: '📍 周辺検索', zh: '📍 周边搜索' },
    'travel.searchSectionSub': { ko: '조건 선택 후 바로 검색', en: 'Set filters and search', ja: '条件を選んで検索', zh: '选择条件后搜索' },
    'travel.latLabel': { ko: '위도', en: 'Latitude', ja: '緯度', zh: '纬度' },
    'travel.lonLabel': { ko: '경도', en: 'Longitude', ja: '経度', zh: '经度' },
    'travel.categoryLabel': { ko: '카테고리', en: 'Category', ja: 'カテゴリ', zh: '类别' },
    'travel.radiusLabel': { ko: '검색 반경', en: 'Search radius', ja: '検索半径', zh: '搜索半径' },
    'travel.searchBtn': { ko: '주변 장소 찾기', en: 'Find nearby places', ja: '周辺を検索', zh: '查找周边地点' },
    'travel.mapPreview': { ko: '지도 미리보기', en: 'Map preview', ja: '地図プレビュー', zh: '地图预览' },
    'travel.searchResults': { ko: '검색 결과', en: 'Search results', ja: '検索結果', zh: '搜索结果' },
    'travel.viewOnMap': { ko: '지도에서 보기', en: 'View on map', ja: '地図で見る', zh: '在地图中查看' },
    'travel.googleMaps': { ko: 'Google 지도', en: 'Google Maps', ja: 'Googleマップ', zh: 'Google 地图' },
    'map.openGoogleMaps': { ko: 'Google 지도', en: 'Google Maps', ja: 'Googleマップ', zh: 'Google 地图' },
    'travel.bookingSelect': { ko: '예약 선택', en: 'Select for booking', ja: '予約に選択', zh: '选择预订' },
    'travel.selectedPlace': { ko: '선택된 예약 장소', en: 'Selected booking place', ja: '選択した予約場所', zh: '已选预订地点' },
    'travel.selectedPlaceMeta': { ko: '{category} · {distance} · 예약 폼 반영됨', en: '{category} · {distance} · Applied to booking form', ja: '{category} · {distance} · 予約フォームに反映', zh: '{category} · {distance} · 已同步到预订表单' },
    'travel.selectedPlaceDone': { ko: '예약 선택 완료 · 예약 폼에 반영됨', en: 'Booking place selected · form updated', ja: '予約選択完了 · フォームに反映', zh: '预订地点已选 · 表单已更新' },
    'travel.bookingSection': { ko: '🧳 여행 예약', en: '🧳 Travel booking', ja: '🧳 旅行予約', zh: '🧳 旅行预订' },
    'travel.bookingSectionSub': { ko: '예약 대상 선택 후 요청', en: 'Select and request booking', ja: '対象を選んで予約リクエスト', zh: '选择后发起预订请求' },
    'travel.interCallPlaceholder': { ko: '통역 통화 전화번호 (예: 01012345678)', en: 'Interpret call number (e.g. 01012345678)', ja: '通訳通話番号（例: 01012345678）', zh: '传译通话号码（例：01012345678）' },
    'travel.openDialpad': { ko: '다이얼패드 열기', en: 'Open dial pad', ja: 'ダイヤルパッドを開く', zh: '打开拨号盘' },
    'travel.catAll': { ko: '전체', en: 'All', ja: 'すべて', zh: '全部' },
    'travel.catHotel': { ko: '호텔', en: 'Hotels', ja: 'ホテル', zh: '酒店' },
    'travel.catAirport': { ko: '공항', en: 'Airports', ja: '空港', zh: '机场' },
    'travel.catRestaurant': { ko: '식당', en: 'Restaurants', ja: 'レストラン', zh: '餐厅' },
    'travel.catAttraction': { ko: '관광명소', en: 'Attractions', ja: '観光名所', zh: '景点' },
    'voip.friendsTitle': { ko: '📡 VoIP 친구 — 통역통화', en: '📡 VoIP friends — interpretation call', ja: '📡 VoIP友達 — 通訳通話', zh: '📡 VoIP 好友 — 传译通话' },
    'voip.friendsSubtitle': { ko: '앱 친구 통역통화', en: 'Interpret calls with app friends', ja: 'アプリ友達との通訳通話', zh: '与应用好友进行传译通话' },
    'voip.friendsSearch': { ko: '이름 · 이메일 · 보이스 ID 검색', en: 'Search name · email · voice ID', ja: '名前 · メール · ボイスID検索', zh: '搜索姓名 · 邮箱 · 语音 ID' },
    'voip.friendsEmpty': { ko: '등록된 VoIP 친구가 없습니다. 채팅 탭에서 친구를 추가해 보세요.', en: 'No VoIP friends yet. Add friends from the Chat tab.', ja: 'VoIP友達がいません。チャットタブから追加してください。', zh: '暂无 VoIP 好友。请在聊天标签页添加好友。' },
    'voip.friendsNoSearch': { ko: '검색 결과가 없습니다.', en: 'No search results.', ja: '検索結果がありません。', zh: '没有搜索结果。' },
    'voip.friendsLoadError': { ko: '친구 목록을 불러오지 못했습니다.', en: 'Could not load friends list.', ja: '友達リストを読み込めませんでした。', zh: '无法加载好友列表。' },
    'voip.appFriendBadge': { ko: '앱 친구', en: 'App friend', ja: 'アプリ友達', zh: '应用好友' },
    'tourism.promoTitle': { ko: '📣 근처 숙박·음식점 홍보', en: '📣 Nearby stays & dining promos', ja: '📣 近くの宿泊・飲食プロモ', zh: '📣 附近住宿·餐饮推广' },
    'tourism.promoIntro': { ko: '근처 숙박·맛집 홍보', en: 'Nearby stay and dining promos', ja: '近くの宿泊・グルメプロモ', zh: '附近住宿·美食推广' },
    'tourism.translating': { ko: '번역 중...', en: 'Translating...', ja: '翻訳中...', zh: '翻译中...' },
    'tourism.gpsRequired': { ko: 'GPS를 켜면 근처 홍보를 볼 수 있습니다.', en: 'Turn on GPS to view nearby promos.', ja: 'GPSをオンにすると近くのプロモを表示できます。', zh: '开启 GPS 后可查看附近推广。' },
    'tourism.emptyBoard': { ko: '근처 홍보가 아직 없습니다.', en: 'No nearby promos yet.', ja: '近くのプロモはまだありません。', zh: '暂无附近推广。' },
    'tourism.nearbyBadge': { ko: '📍 근처', en: '📍 Nearby', ja: '📍 近く', zh: '📍 附近' },
    'tourism.radiusKm': { ko: '반경 {km}km', en: 'within {km} km', ja: '半径{km}km', zh: '半径 {km} km' },
    'tourism.composeClose': { ko: '작성 닫기', en: 'Close composer', ja: '作成を閉じる', zh: '关闭编辑' },
    'tourism.composeOpen': { ko: '＋ 숙박·맛집 홍보 올리기', en: '＋ Post stay or dining promo', ja: '＋ 宿泊・グルメを投稿', zh: '＋ 发布住宿·美食推广' },
    'tourism.postSuccess': { ko: '홍보가 등록되었습니다.', en: 'Promo posted.', ja: 'プロモを登録しました。', zh: '推广已发布。' },
    'tourism.postFailed': { ko: '홍보 등록 오류: {message}', en: 'Post failed: {message}', ja: '投稿エラー: {message}', zh: '发布失败：{message}' },
    'manual.back': { ko: '‹ 뒤로', en: '‹ Back', ja: '‹ 戻る', zh: '‹ 返回' },
    'sorisae.voiceCallArmOn': { ko: '📞 소리새AI 음성무한대기(심볼) 켜기', en: '📞 Turn on voice-call wake', ja: '📞 音声呼び出し待機をオン', zh: '📞 开启语音呼叫等待' },
    'sorisae.voiceCallArmOff': { ko: '🔕 소리새AI 음성무한대기(심볼) 끄기', en: '🔔 Say "{name}" to wake · turn off', ja: '🔔 「{name}」で起動 · 待機オフ', zh: '🔔 呼叫「{name}」唤醒 · 关闭等待' },
    'sorisae.voiceCallArmed': { ko: '🔔 소리새AI 음성무한대기(심볼) 동작 중', en: '🔔 Voice-call wake on · say "{name}" or "Sorisae"', ja: '🔔 音声呼び出し待機中 · 「{name}」または「ソリセ」', zh: '🔔 语音呼叫等待中 · 呼叫「{name}」或「索里塞」' },
    'voip.tabContacts': { ko: '연락처', en: 'Contacts', ja: '連絡先', zh: '联系人' },
    'voip.tabRecents': { ko: '최근기록', en: 'Recents', ja: '履歴', zh: '最近' },
    'voip.tabKeypad': { ko: '키패드', en: 'Keypad', ja: 'キーパッド', zh: '拨号盘' },
    'travel.bookingCallAirport': { ko: '📞 공항 예약센터 전화 예약', en: '📞 Call airport booking center', ja: '📞 空港予約センターに電話', zh: '📞 致电机场预订中心' },
    'travel.bookingCallHotel': { ko: '📞 호텔 전화 예약', en: '📞 Call hotel to book', ja: '📞 ホテルに電話予約', zh: '📞 致电酒店预订' },
    'travel.bookingSupportCall': { ko: '📞 예약센터 통화', en: '📞 Call booking support', ja: '📞 予約センターに通話', zh: '📞 致电预订中心' },
    'sorisae.windowClose': { ko: '✕ 닫기', en: '✕ Close', ja: '✕ 閉じる', zh: '✕ 关闭' },
    'sorisae.windowEmpty': { ko: '대화 없음', en: 'No conversation yet', ja: '会話なし', zh: '暂无对话' },
    'sorisae.questionLabel': { ko: '🙋 질문 · {lang}', en: '🙋 Question · {lang}', ja: '🙋 質問 · {lang}', zh: '🙋 提问 · {lang}' },
    'sorisae.answerLabel': { ko: '🐦 답변 · {lang}', en: '🐦 Answer · {lang}', ja: '🐦 回答 · {lang}', zh: '🐦 回答 · {lang}' },
    'sorisae.clearLog': { ko: '대화 지우기', en: 'Clear conversation', ja: '会話を消去', zh: '清除对话' },
    'sorisae.startConversation': { ko: '🐦 {name} 대화 시작', en: '🐦 Start chat with {name}', ja: '🐦 {name}と会話開始', zh: '🐦 与{name}开始对话' },
    'sorisae.waveHintSpeaking': { ko: '🐦 답변 재생 중 · 잠시 후 다시 들어요', en: '🐦 Playing answer · listening resumes soon', ja: '🐦 回答再生中 · まもなく再開', zh: '🐦 正在播放回答 · 稍后继续聆听' },
    'sorisae.waveHintListening': { ko: '🎙️ 음성 대기 중 · 말씀하세요', en: '🎙️ Listening · speak now', ja: '🎙️ 音声待機中 · 話してください', zh: '🎙️ 等待语音 · 请说话' },
    'sorisae.scheduleBasis': { ko: '🕒 시간표 근거', en: '🕒 Schedule basis', ja: '🕒 時刻表の根拠', zh: '🕒 时刻表依据' },
    'sorisae.transportFallback': { ko: '교통편', en: 'Transit', ja: '交通', zh: '交通' },
    'sorisae.originPin': { ko: '출발지 핀', en: 'Origin pin', ja: '出発地ピン', zh: '出发地标记' },
    'sorisae.destinationPin': { ko: '목적지 핀', en: 'Destination pin', ja: '目的地ピン', zh: '目的地标记' },
    'sorisae.convEnded': { ko: '🐦 {name} 대화를 종료했습니다.', en: '🐦 Ended chat with {name}.', ja: '🐦 {name}との会話を終了しました。', zh: '🐦 已结束与{name}的对话。' },
    'sorisae.convStarted': { ko: '🐦 {name} 대화 시작 · 말이 끝나면 자동으로 답해요', en: '🐦 Chat with {name} started · auto-reply when you finish', ja: '🐦 {name}と会話開始 · 話し終わると自動応答', zh: '🐦 与{name}开始对话 · 说完后自动回复' },
    'sorisae.webChatOnly': { ko: '{name} 음성 대화는 모바일 앱에서 사용할 수 있습니다.', en: 'Voice chat with {name} is available in the mobile app.', ja: '{name}との音声会話はモバイルアプリで利用できます。', zh: '与{name}的语音对话请在移动应用中使用。' },
    'sorisae.wakeSuccess': { ko: '🐦 {name} 깨어났어요! 말씀하세요 · 3분 무응답이면 잠들어요', en: '🐦 {name} is awake! Speak now · sleeps after 3 min idle', ja: '🐦 {name}が起きました！話してください · 3分無応答でスリープ', zh: '🐦 {name}已唤醒！请说话 · 3分钟无响应将休眠' },
    'sorisae.wakeArmedStatus': { ko: '🔔 소리새AI 음성무한대기(심볼) 동작 중', en: '🔔 Voice-call wake on · say "{name}" or "Sorisae"', ja: '🔔 音声呼び出し待機中 · 「{name}」または「ソリセ」', zh: '🔔 语音呼叫等待中 · 呼叫「{name}」或「索里塞」' },
    'sorisae.wakeEnded': { ko: '🐦 소리새AI 음성무한대기(심볼)를 종료했습니다.', en: '🐦 Voice-call wake for {name} turned off.', ja: '🐦 {name}の音声呼び出し待機を終了しました。', zh: '🐦 已关闭{name}的语音呼叫等待。' },
    'sorisae.dormant': { ko: '😴 {name}가 3분 무응답으로 잠들었어요 · 다시 부르면 깨어나요', en: '😴 {name} slept after 3 min idle · call again to wake', ja: '😴 {name}が3分無応答でスリープ · 再度呼ぶと起動', zh: '😴 {name}因3分钟无响应已休眠 · 再次呼叫可唤醒' },
    'sorisae.webWakeOnly': { ko: '{name} 음성 호출은 모바일 앱에서 사용할 수 있습니다.', en: 'Voice-call wake for {name} is available in the mobile app.', ja: '{name}の音声呼び出しはモバイルアプリで利用できます。', zh: '{name}的语音呼叫请在移动应用中使用。' },
    'capture.micWebUnsupportedTitle': { ko: '마이크 지원 불가', en: 'Microphone not supported', ja: 'マイク非対応', zh: '不支持麦克风' },
    'capture.micWebUnsupportedBody': { ko: '현재 브라우저는 음성 인식을 지원하지 않습니다. Chrome 또는 Edge 최신 버전을 사용해 주세요.', en: 'This browser does not support speech recognition. Use the latest Chrome or Edge.', ja: 'このブラウザは音声認識に非対応です。最新のChromeまたはEdgeをご利用ください。', zh: '当前浏览器不支持语音识别。请使用最新版 Chrome 或 Edge。' },
    'capture.recordErrorTitle': { ko: '녹음 오류', en: 'Recording error', ja: '録音エラー', zh: '录音错误' },
    'capture.voiceInputFailed': { ko: '🎤 음성 입력 실패: {detail}', en: '🎤 Voice input failed: {detail}', ja: '🎤 音声入力失敗: {detail}', zh: '🎤 语音输入失败: {detail}' },
    'capture.listeningSorisae': { ko: '🎙️ 듣는 중 · 말씀하세요', en: '🎙️ Listening · speak now', ja: '🎙️ 聞いています · 話してください', zh: '🎙️ 正在聆听 · 请说话' },
    'capture.wakeCallWait': { ko: '🔔 소리새AI 음성무한대기(심볼) 감지 중', en: '🔔 Wake-call waiting · call a bit longer', ja: '🔔 呼び出し待機 · もう少し長く呼んでください', zh: '🔔 等待呼叫 · 请再呼叫长一点' },
    'capture.preparingAnswer': { ko: '🔄 답변 준비 중...', en: '🔄 Preparing answer...', ja: '🔄 回答準備中...', zh: '🔄 正在准备回答...' },
    'capture.gpsOff': { ko: '⚠️ GPS OFF · 일반 대화는 계속 · 위치 질문은 부정확할 수 있음', en: '⚠️ GPS off · chat continues · location answers may be inaccurate', ja: '⚠️ GPSオフ · 会話は継続 · 位置の質問は不正確な場合あり', zh: '⚠️ GPS 关闭 · 对话继续 · 位置相关问题可能不准确' },
    'capture.echoIgnored': { ko: '🔇 발화 중 입력(에코) 무시 · 발화가 끝나면 다시 들어요', en: '🔇 Ignoring echo while speaking · listening resumes after', ja: '🔇 発話中のエコー無視 · 終了後に再開', zh: '🔇 发言时忽略回声 · 结束后继续聆听' },
    'capture.server502': { ko: '⚠️ AI 서버 재시작 중(502) · 8초 후 다시 들어요', en: '⚠️ AI server restarting (502) · listening again in 8s', ja: '⚠️ AIサーバー再起動中(502) · 8秒後に再開', zh: '⚠️ AI 服务器重启中(502) · 8秒后恢复聆听' },
    'capture.server503': { ko: '⚠️ AI 서버 준비 중(503) · 잠시 후 다시 말씀해 주세요', en: '⚠️ AI server preparing (503) · please try again shortly', ja: '⚠️ AIサーバー準備中(503) · しばらくして再試行', zh: '⚠️ AI 服务器准备中(503) · 请稍后再试' },
    'capture.serverError': { ko: '⚠️ AI 서버 응답 실패 ({status}) · 잠시 후 다시 말씀해 주세요', en: '⚠️ AI server error ({status}) · please try again shortly', ja: '⚠️ AIサーバーエラー({status}) · しばらくして再試行', zh: '⚠️ AI 服务器错误({status}) · 请稍后再试' },
    'capture.loginRequired': { ko: '⚠️ 로그인이 필요합니다 · 다시 로그인해 주세요', en: '⚠️ Login required · please sign in again', ja: '⚠️ ログインが必要です · 再ログインしてください', zh: '⚠️ 需要登录 · 请重新登录' },
    'capture.answerFailed': { ko: '⚠️ 답변 실패 ({status}) · 다시 말씀해 주세요', en: '⚠️ Answer failed ({status}) · please try again', ja: '⚠️ 回答失敗({status}) · もう一度話してください', zh: '⚠️ 回答失败({status}) · 请再说一次' },
    'capture.segmentErrorContinue': { ko: '🎙️ 이번 구간 오류 · 계속 듣는 중...', en: '🎙️ Segment error · still listening...', ja: '🎙️ 区間エラー · 聞き続けています...', zh: '🎙️ 本段出错 · 继续聆听...' },
    'capture.langPair': { ko: '🎯 {from} → {to}', en: '🎯 {from} → {to}', ja: '🎯 {from} → {to}', zh: '🎯 {from} → {to}' },
    'capture.continueListening': { ko: '🎙️ {message} · 계속 듣는 중...', en: '🎙️ {message} · still listening...', ja: '🎙️ {message} · 聞き続けています...', zh: '🎙️ {message} · 继续聆听...' },
    'capture.interCallListening': { ko: '🎙️ 스피커폰 통역 보조 수신 중... {delay} 후 자동 처리합니다.', en: '🎙️ Speakerphone assist listening... auto relay in {delay}.', ja: '🎙️ スピーカー通訳補助受信中... {delay}後に自動処理。', zh: '🎙️ 扬声器传译辅助接收中... {delay}后自动处理。' },
    'capture.interCallTranslateFailed': { ko: '번역에 실패했습니다. 다시 말씀해 주세요.', en: 'Translation failed. Please try again.', ja: '翻訳に失敗しました。もう一度話してください。', zh: '翻译失败。请再说一次。' },
    'capture.voiceProcessError': { ko: '음성 처리 오류', en: 'Voice processing error', ja: '音声処理エラー', zh: '语音处理错误' },
    'face.webOnlyTitle': { ko: '대면 통역', en: 'Face-to-face interpretation', ja: '対面通訳', zh: '面对面传译' },
    'face.webOnlyBody': { ko: '자동 대화 통역은 모바일 앱에서 사용할 수 있습니다.', en: 'Auto conversation interpretation is available in the mobile app.', ja: '自動会話通訳はモバイルアプリで利用できます。', zh: '自动对话传译请在移动应用中使用。' },
    'face.peerLangTitle': { ko: '상대 언어 필요', en: 'Partner language required', ja: '相手の言語が必要', zh: '需要对方语言' },
    'gps.checkingPermission': { ko: '위치 권한 확인 중...', en: 'Checking location permission...', ja: '位置権限を確認中...', zh: '正在检查位置权限...' },
    'gps.deniedStatus': { ko: '위치 권한 미허용 · {message}', en: 'Location denied · {message}', ja: '位置権限未許可 · {message}', zh: '位置权限未允许 · {message}' },
    'gps.permissionBlocked': { ko: '위치 권한이 차단되어 있습니다. Android 설정에서 {appName} 위치 권한을 허용해 주세요.', en: 'Location is blocked. Allow location for {appName} in Android settings.', ja: '位置がブロックされています。Android設定で{appName}の位置を許可してください。', zh: '位置权限已被阻止。请在 Android 设置中允许 {appName} 的位置权限。' },
    'gps.permissionNeeded': { ko: '현재 위치 확인과 주변 서비스 검색을 위해 위치 권한이 필요합니다.', en: 'Location permission is required for position and nearby services.', ja: '現在地と周辺検索には位置権限が必要です。', zh: '需要位置权限以确认当前位置和周边服务。' },
    'gps.permissionTitle': { ko: '위치 권한 필요', en: 'Location permission required', ja: '位置権限が必要', zh: '需要位置权限' },
    'gps.resolving': { ko: 'GPS/Wi-Fi/기지국 위치 확인 중...', en: 'Resolving GPS/Wi-Fi/cell location...', ja: 'GPS/Wi-Fi/基地局の位置を確認中...', zh: '正在确认 GPS/Wi-Fi/基站位置...' },
    'gps.resolvedStatus': { ko: '{mode} · 품질 {score}점 · 정확도 {acc} · 좌표 {lat}, {lng} · 국가 {country}{lang}{region}', en: '{mode} · quality {score} · accuracy {acc} · {lat}, {lng} · {country}{lang}{region}', ja: '{mode} · 品質{score} · 精度{acc} · {lat}, {lng} · {country}{lang}{region}', zh: '{mode} · 质量{score} · 精度{acc} · {lat}, {lng} · {country}{lang}{region}' },
    'gps.failedStatus': { ko: '위치 확인 실패 · {reason}', en: 'Location failed · {reason}', ja: '位置確認失敗 · {reason}', zh: '位置确认失败 · {reason}' },
    'gps.failedTitle': { ko: '위치 확인 실패', en: 'Location failed', ja: '位置確認失敗', zh: '位置确认失败' },
    'gps.failedBody': { ko: '{reason}\n\nAndroid 위치 서비스와 앱 위치 권한을 확인한 뒤 다시 눌러 주세요.', en: '{reason}\n\nCheck Android location services and app permission, then try again.', ja: '{reason}\n\nAndroidの位置サービスとアプリ権限を確認して再試行してください。', zh: '{reason}\n\n请检查 Android 位置服务和应用位置权限后重试。' },
    'gps.openSettings': { ko: '설정 열기', en: 'Open settings', ja: '設定を開く', zh: '打开设置' },
    'common.ok': { ko: '확인', en: 'OK', ja: 'OK', zh: '确定' },
    'gps.reasonServicesDisabled': { ko: '단말 위치 서비스가 꺼져 있고 저장된 마지막 위치도 없습니다.', en: 'Device location is off and no last known position is stored.', ja: '端末の位置サービスがオフで、最後の位置もありません。', zh: '设备位置服务已关闭且无上次位置记录。' },
    'gps.reasonUnavailable': { ko: 'GPS/Wi-Fi/기지국 제공자에서 현재 위치와 마지막 위치를 모두 받지 못했습니다.', en: 'Could not get current or last position from GPS/Wi-Fi/cell.', ja: 'GPS/Wi-Fi/基地局から現在地と最終位置を取得できませんでした。', zh: '无法从 GPS/Wi-Fi/基站获取当前或上次位置。' },
    'gps.reasonTimeout': { ko: '위치 제공자 응답 시간이 초과되었거나 단말 위치 제공자가 응답하지 않았습니다.', en: 'Location provider timed out or did not respond.', ja: '位置プロバイダがタイムアウトまたは応答しませんでした。', zh: '位置提供方超时或未响应。' },
    'gps.modeSatellite': { ko: 'Satellite GPS', en: 'Satellite GPS', ja: 'Satellite GPS', zh: 'Satellite GPS' },
    'gps.modeHybrid': { ko: 'Hybrid GPS/Wi-Fi', en: 'Hybrid GPS/Wi-Fi', ja: 'Hybrid GPS/Wi-Fi', zh: 'Hybrid GPS/Wi-Fi' },
    'gps.modeWifiFallback': { ko: 'WF Fallback', en: 'WF Fallback', ja: 'WF Fallback', zh: 'WF Fallback' },
    'gps.modeAdbMock': { ko: 'ADB Mock GPS', en: 'ADB Mock GPS', ja: 'ADB Mock GPS', zh: 'ADB Mock GPS' },
    'gps.modeCached': { ko: 'Cached Wi-Fi/Cell', en: 'Cached Wi-Fi/Cell', ja: 'Cached Wi-Fi/Cell', zh: 'Cached Wi-Fi/Cell' },
    'gps.langRecommend': { ko: ' · 추천 {lang}', en: ' · suggest {lang}', ja: ' · 推奨 {lang}', zh: ' · 推荐 {lang}' },
    'gps.regionSuffix': { ko: ' · 지역 {region}', en: ' · region {region}', ja: ' · 地域 {region}', zh: ' · 地区 {region}' },
    'voip.recentsPeerMissing': { ko: '통역통화', en: 'Interpretation call', ja: '通訳通話', zh: '传译通话' },
    'voip.recentsNotFoundBody': { ko: '최근 기록의 상대를 찾지 못했습니다.', en: 'Could not find the peer from recents.', ja: '履歴の相手が見つかりませんでした。', zh: '未找到最近记录中的对方。' },
    'voip.redialNoNumber': { ko: '일반전화', en: 'Regular call', ja: '一般電話', zh: '普通电话' },
    'voip.redialNoNumberBody': { ko: '저장된 번호가 없어 다시 걸 수 없습니다.', en: 'No saved number to redial.', ja: '保存された番号がなく再発信できません。', zh: '没有保存的号码，无法重拨。' },
    'pstn.dialPadOpenFailed': { ko: '다이얼패드에서 선택한 번호로 전화앱을 열지 못했습니다.', en: 'Could not open the phone app with the dial pad number.', ja: 'ダイヤル番号で電話アプリを開けませんでした。', zh: '无法用拨号盘号码打开电话应用。' },
    'pstn.dialPadWebTitle': { ko: '다이얼패드', en: 'Dial pad', ja: 'ダイヤル', zh: '拨号盘' },
    'pstn.dialPadWebBody': { ko: '웹에서는 시스템 전화앱 연동을 사용할 수 없습니다.', en: 'System phone app is not available on web.', ja: 'Webではシステム電話アプリ連携は使えません。', zh: 'Web 端无法使用系统电话应用。' },
    'pstn.contactsWebTitle': { ko: '전화번호 저장소 열기', en: 'Open contacts', ja: '連絡先を開く', zh: '打开通讯录' },
    'pstn.contactsWebBody': { ko: '웹에서는 단말 전화번호 저장소를 직접 열 수 없습니다. 모바일 앱에서 사용하세요.', en: 'Device contacts cannot be opened on web. Use the mobile app.', ja: 'Webでは端末の連絡先を開けません。モバイルアプリをご利用ください。', zh: 'Web 端无法打开设备通讯录。请使用移动应用。' },
    'chat.hubTitle': { ko: '💬 채팅 + 친구 허브', en: '💬 Chat + friends hub', ja: '💬 チャット＋友達ハブ', zh: '💬 聊天 + 好友中心' },
    'chat.hubVoipFriends': { ko: 'VoIP 친구 찾기', en: 'Find VoIP friends', ja: 'VoIP友達を探す', zh: '查找 VoIP 好友' },
    'chat.hubVoipFriendsSub': { ko: '앱 가입 친구', en: 'App members', ja: 'アプリ登録友達', zh: '已注册应用的好友' },
    'chat.hubPhoneFind': { ko: '전화번호로 찾기', en: 'Find by phone', ja: '電話番号で探す', zh: '按电话号码查找' },
    'chat.hubPhoneFindSub': { ko: '번호로 친구 추가', en: 'Add friend by number', ja: '番号で友達追加', zh: '通过号码添加好友' },
    'chat.hubMapFind': { ko: '지도로 찾기', en: 'Find on map', ja: '地図で探す', zh: '在地图上查找' },
    'chat.hubMapFindSub': { ko: '주변 친구 탐색', en: 'Nearby friends', ja: '近くの友達を探索', zh: '探索附近好友' },
    'chat.hubGroup': { ko: '단체채팅', en: 'Group chat', ja: 'グループチャット', zh: '群聊' },
    'chat.hubGroupSub': { ko: '그룹 만들기', en: 'Create a group', ja: 'グループを作成', zh: '创建群组' },
    'chat.hubNearbyTitle': { ko: '🗺️ 주변 친구 찾기', en: '🗺️ Find nearby friends', ja: '🗺️ 近くの友達を探す', zh: '🗺️ 查找附近好友' },
    'chat.hubNearbySub': { ko: '근처 친구 탐색/수락', en: 'Find and accept nearby friends', ja: '近くの友達を探索・承認', zh: '探索并接受附近好友' },
    'contacts.title': { ko: '📇 연락처에서 바로 연결', en: '📇 Connect from contacts', ja: '📇 連絡先から接続', zh: '📇 从通讯录直接连接' },
    'contacts.searchPlaceholder': { ko: '이름 또는 번호 검색', en: 'Search name or number', ja: '名前または番号を検索', zh: '搜索姓名或号码' },
    'contacts.loadErrorEmpty': { ko: '단말에 저장된 연락처를 찾지 못했습니다. 연락처 권한을 허용했는지 확인해 주세요.', en: 'No contacts on device. Check contacts permission.', ja: '端末に連絡先がありません。連絡先権限を確認してください。', zh: '未找到设备通讯录。请确认已允许通讯录权限。' },
    'contacts.loadFailed': { ko: '연락처를 불러오지 못했습니다.', en: 'Could not load contacts.', ja: '連絡先を読み込めませんでした。', zh: '无法加载通讯录。' },
    'contacts.loading': { ko: '연락처를 불러오는 중...', en: 'Loading contacts...', ja: '連絡先を読み込み中...', zh: '正在加载通讯录...' },
    'contacts.noSearch': { ko: '검색 결과가 없습니다.', en: 'No search results.', ja: '検索結果がありません。', zh: '无搜索结果。' },
    'contacts.noList': { ko: '표시할 연락처가 없습니다.', en: 'No contacts to show.', ja: '表示する連絡先がありません。', zh: '没有可显示的联系人。' },
    'contacts.appFriendBadge': { ko: '앱 친구', en: 'App friend', ja: 'アプリ友達', zh: '应用好友' },
    'contacts.actionCall': { ko: '📞 전화', en: '📞 Call', ja: '📞 電話', zh: '📞 电话' },
    'contacts.actionSms': { ko: '💬 문자', en: '💬 SMS', ja: '💬 SMS', zh: '💬 短信' },
    'contacts.actionVoip': { ko: '📡 통역통화', en: '📡 Interpret call', ja: '📡 通訳通話', zh: '📡 传译通话' },
    'contacts.actionChat': { ko: '💬 채팅', en: '💬 Chat', ja: '💬 チャット', zh: '💬 聊天' },
    'contacts.actionInvite': { ko: '💬 초대', en: '💬 Invite', ja: '💬 招待', zh: '💬 邀请' },
    'contacts.promoShare': { ko: '📣 앱 홍보 공유 (카카오톡·라인·SNS·문자)', en: '📣 Share app promo (Kakao·LINE·SNS·SMS)', ja: '📣 アプリ宣伝を共有（カカオ・LINE・SNS・SMS）', zh: '📣 分享应用推广（Kakao·LINE·SNS·短信）' },
    'contacts.count': { ko: '{count}명', en: '{count}', ja: '{count}人', zh: '{count}人' },
    'contacts.refresh': { ko: '다시 불러오기', en: 'Reload', ja: '再読み込み', zh: '重新加载' },
    'contacts.refreshing': { ko: '새로고침 중...', en: 'Refreshing...', ja: '更新中...', zh: '正在刷新...' },
    'contacts.close': { ko: '닫기', en: 'Close', ja: '閉じる', zh: '关闭' },
    'contacts.collapse': { ko: '연락처에서 바로 연결 접기', en: 'Collapse contacts connect', ja: '連絡先接続を折りたたむ', zh: '收起通讯录连接' },
    'contacts.expand': { ko: '연락처에서 바로 연결 펼치기', en: 'Expand contacts connect', ja: '連絡先接続を展開', zh: '展开通讯录连接' },
    'contacts.collapseMeta': { ko: '{count}명 · 탭하여 펼치기', en: '{count} · tap to expand', ja: '{count}人 · タップで展開', zh: '{count}人 · 点击展开' },
    'contacts.rowClose': { ko: '닫기', en: 'Close', ja: '閉じる', zh: '关闭' },
    'contacts.rowOpen': { ko: '열기', en: 'Open', ja: '開く', zh: '打开' },
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
    const catalogLang = resolveBundledCatalogLang(lang ?? getEffectiveUiLang());
    const row = ROWS[key];
    const template = row?.[catalogLang] ?? row?.en ?? key;
    return applyVars(template, vars);
}

export function getAllFeatureUiKeys(): FeatureUiKey[] {
    return Object.keys(ROWS) as FeatureUiKey[];
}

const TRAVEL_CATEGORY_KEYS = {
    all: 'travel.catAll',
    hotel: 'travel.catHotel',
    airport: 'travel.catAirport',
    restaurant: 'travel.catRestaurant',
    attraction: 'travel.catAttraction',
} as const satisfies Record<string, FeatureUiKey>;

export type TravelCategoryValue = keyof typeof TRAVEL_CATEGORY_KEYS;

export function getTravelCategoryLabel(value: TravelCategoryValue, lang?: string): string {
    const key = TRAVEL_CATEGORY_KEYS[value];
    return key ? getFeatureUiText(key, undefined, lang) : value;
}
