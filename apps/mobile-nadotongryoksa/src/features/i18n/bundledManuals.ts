/**
 * 기능 설명서 — overview 등 ko/en/ja/zh 오프라인 정본(한국어 선표시 금지).
 */
import type { FeatureManual } from '../settings/featureManuals';
import { isBundledUiLang, resolveBundledCatalogLang, type BundledUiLang } from './bundledUiLangs';

export type BundledManualContent = {
    title: string;
    summary: string;
    sections: Array<{ heading: string; lines: string[] }>;
};

const OVERVIEW: Record<BundledUiLang, BundledManualContent> = {
    ko: {
        title: '앱 소개',
        summary: 'WorldLinco 기능 한눈에.',
        sections: [
            {
                heading: 'WorldLinco 란?',
                lines: [
                    'WorldLinco 는 언어 장벽 없이 사람과 사람을 잇는 실시간 통·번역 플랫폼입니다.',
                    '대면 통역, VoIP 통역, 일반전화 통역 보조, 번역 채팅, 노래 가사 번역, 여행 예약까지 한 앱에서 제공합니다.',
                    'AI 동반자 "소리새"가 음성으로 대화하고 도와줍니다.',
                ],
            },
            {
                heading: '처음이라면',
                lines: [
                    '설정에서 내 국가·언어를 먼저 지정하면 통역/번역 기본 언어가 맞춰집니다.',
                    '기능 화면에는 긴 설명을 두지 않습니다. 궁금한 점은 설정 → 사용 설명서에서 확인하세요.',
                ],
            },
        ],
    },
    en: {
        title: 'App overview',
        summary: 'WorldLinco at a glance.',
        sections: [
            {
                heading: 'What is WorldLinco?',
                lines: [
                    'WorldLinco connects people in real time across language barriers.',
                    'Face interpretation, VoIP, PSTN assist, translation chat, song lyrics, and travel booking — all in one app.',
                    'AI companion "Sorisae" helps by voice.',
                ],
            },
            {
                heading: 'First time?',
                lines: [
                    'Set your country and language in Settings first — interpretation defaults follow your profile.',
                    'Feature screens stay minimal. See Settings → User guides for details.',
                ],
            },
        ],
    },
    ja: {
        title: 'アプリ紹介',
        summary: 'WorldLinco の機能概要。',
        sections: [
            {
                heading: 'WorldLinco とは？',
                lines: [
                    '言語の壁なく人と人をつなぐリアルタイム通・翻訳プラットフォームです。',
                    '対面通訳、VoIP、一般電話補助、翻訳チャット、歌詞翻訳、旅行予約まで一つのアプリで。',
                    'AIコンパニオン「ソリセ」が音声でサポートします。',
                ],
            },
            {
                heading: 'はじめての方',
                lines: [
                    '設定で国・言語を先に指定すると通訳/翻訳の基本言語が合わせられます。',
                    '機能画面は簡潔です。詳しくは設定 → 使用説明書をご覧ください。',
                ],
            },
        ],
    },
    zh: {
        title: '应用介绍',
        summary: 'WorldLinco 功能一览。',
        sections: [
            {
                heading: '什么是 WorldLinco？',
                lines: [
                    '打破语言障碍、实时连接人与人的通译翻译平台。',
                    '面对面谈、VoIP、普通电话辅助、翻译聊天、歌词翻译、旅行预约，尽在一个应用。',
                    'AI 伙伴「소리새」用语音为您提供帮助。',
                ],
            },
            {
                heading: '初次使用',
                lines: [
                    '请先在设置中指定国家与语言，传译/翻译默认语言将自动匹配。',
                    '功能界面保持简洁。详情请见 设置 → 使用说明。',
                ],
            },
        ],
    },
};

const FACE: Record<BundledUiLang, BundledManualContent> = {
    ko: {
        title: '대면 통역',
        summary: '마주 보고 실시간 번역.',
        sections: [
            {
                heading: '대면 통역 시작',
                lines: [
                    '홈의 대면 통역 카드를 열면 양쪽 언어가 나뉜 전용 화면이 열립니다.',
                    '가운데 마이크를 켜면 내 말이 상대 언어로 번역되어 반대편 화면에 표시됩니다.',
                    '상대가 말한 내용은 다시 내 언어로 번역되어 아래쪽에 반영됩니다.',
                ],
            },
        ],
    },
    en: {
        title: 'Face-to-face interpretation',
        summary: 'Real-time translation face to face.',
        sections: [
            {
                heading: 'Getting started',
                lines: [
                    'Open the face-to-face card on Home for a split-language screen.',
                    'Turn on the center mic — your speech appears translated for the other person.',
                    'Their speech is translated back into your language below.',
                ],
            },
        ],
    },
    ja: {
        title: '対面通訳',
        summary: '向かい合ってリアルタイム翻訳。',
        sections: [
            {
                heading: 'はじめ方',
                lines: [
                    'ホームの対面通訳カードで専用画面を開きます。',
                    '中央マイクをONにすると自分の発話が相手の言語で表示されます。',
                    '相手の発話は自分の言語に翻訳され下に表示されます。',
                ],
            },
        ],
    },
    zh: {
        title: '面对面传译',
        summary: '面对面实时翻译。',
        sections: [
            {
                heading: '开始使用',
                lines: [
                    '在首页打开面对面传译卡片，进入双语分屏界面。',
                    '开启中央麦克风后，您的话会翻译成对方语言显示在对面。',
                    '对方的话会翻译回您的语言显示在下方。',
                ],
            },
        ],
    },
};

const CHAT: Record<BundledUiLang, BundledManualContent> = {
    ko: {
        title: '번역 채팅',
        summary: '1:1·그룹 자동 번역 채팅.',
        sections: [
            {
                heading: '대화 시작하기',
                lines: [
                    '채팅 탭에서 VoIP 친구 찾기·전화번호로 찾기·단체채팅·지도로 찾기를 선택합니다.',
                    '번역 보관함은 나만 보는 개인 방으로, 번역 결과와 운영 공지가 쌓입니다.',
                    '내가 보낸 글과 상대 글이 서로의 언어로 자동 번역되어 표시됩니다.',
                ],
            },
        ],
    },
    en: {
        title: 'Translation chat',
        summary: '1:1 and group auto-translation chat.',
        sections: [
            {
                heading: 'Start a chat',
                lines: [
                    'In Chat, pick VoIP find, phone find, group chat, or map find.',
                    'The translation vault is your private room for results and notices.',
                    'Messages you send and receive are auto-translated for each side.',
                ],
            },
        ],
    },
    ja: {
        title: '翻訳チャット',
        summary: '1対1・グループ自動翻訳チャット。',
        sections: [
            {
                heading: '会話を始める',
                lines: [
                    'チャットタブでVoIP検索・電話番号・グループ・地図検索を選びます。',
                    '翻訳保管庫は自分だけの個人ルームです。',
                    '送受信メッセージはそれぞれの言語に自動翻訳されます。',
                ],
            },
        ],
    },
    zh: {
        title: '翻译聊天',
        summary: '一对一与群组自动翻译聊天。',
        sections: [
            {
                heading: '开始对话',
                lines: [
                    '在聊天页选择 VoIP 查找、电话查找、群聊或地图查找。',
                    '翻译保管库是您私人的结果与公告房间。',
                    '收发消息会自动翻译成各自的语言。',
                ],
            },
        ],
    },
};

const VOIP: Record<BundledUiLang, BundledManualContent> = {
    ko: {
        title: '통화 통역',
        summary: 'VoIP·일반전화 실시간 통역.',
        sections: [
            {
                heading: 'VoIP 통역 통화',
                lines: [
                    '통화 탭에서 연락처·최근기록·키패드로 상대를 선택해 통화를 시작합니다.',
                    '말하면 내 언어가 상대 언어로, 상대 말은 내 언어로 자동 통역되어 들립니다.',
                ],
            },
            {
                heading: '일반전화(PSTN) 통역 보조',
                lines: [
                    '키패드에서 전화번호로 바로 겁니다. +국가번호로 시작해야 합니다.',
                    '스피커폰으로 상대 음성을 들리게 한 뒤 통역 보조를 켜면 구간별 번역이 재생됩니다.',
                ],
            },
        ],
    },
    en: {
        title: 'Call interpretation',
        summary: 'VoIP and PSTN real-time interpretation.',
        sections: [
            {
                heading: 'VoIP interpret call',
                lines: [
                    'In Calls, pick a contact, recent entry, or keypad number to start.',
                    'Your speech is interpreted to the peer language and vice versa.',
                ],
            },
            {
                heading: 'PSTN assist',
                lines: [
                    'Dial from the keypad with a +country code number.',
                    'Use speakerphone and turn on assist for segment-by-segment translation playback.',
                ],
            },
        ],
    },
    ja: {
        title: '通話通訳',
        summary: 'VoIP・一般電話のリアルタイム通訳。',
        sections: [
            {
                heading: 'VoIP通訳通話',
                lines: [
                    '通話タブで連絡先・履歴・キーパッドから相手を選んで開始します。',
                    '自分の言語は相手の言語に、相手の言語は自分の言語に自動通訳されます。',
                ],
            },
            {
                heading: '一般電話(PSTN)補助',
                lines: [
                    'キーパッドから+国番号で発信します。',
                    'スピーカーで相手の声を聞かせ、補助をONにすると区間ごとに翻訳再生されます。',
                ],
            },
        ],
    },
    zh: {
        title: '通话传译',
        summary: 'VoIP 与普通电话实时传译。',
        sections: [
            {
                heading: 'VoIP 传译通话',
                lines: [
                    '在通话页通过联系人、最近记录或拨号盘选择对方并开始。',
                    '您的话会传译成对方语言，对方的话会传译成您的语言。',
                ],
            },
            {
                heading: '普通电话(PSTN)辅助',
                lines: [
                    '在拨号盘用带 + 国家代码的号码拨打。',
                    '开扬声器听到对方声音后开启辅助，将分段播放翻译。',
                ],
            },
        ],
    },
};

const MAP: Record<BundledUiLang, BundledManualContent> = {
    ko: {
        title: '지도로 친구 찾기',
        summary: '주변 사용자를 지도에서 찾기.',
        sections: [
            {
                heading: '주변 친구 찾기',
                lines: [
                    '채팅 탭의 "지도로 찾기"를 엽니다.',
                    '위치 권한을 허용하면 주변 앱 사용자가 거리순으로 표시됩니다.',
                ],
            },
        ],
    },
    en: {
        title: 'Find friends on map',
        summary: 'Discover nearby users on the map.',
        sections: [
            {
                heading: 'Nearby discovery',
                lines: [
                    'Open "Map find" from the Chat tab.',
                    'Allow location to see nearby app users sorted by distance.',
                ],
            },
        ],
    },
    ja: {
        title: '地図で友達を探す',
        summary: '周辺ユーザーを地図で検索。',
        sections: [
            {
                heading: '周辺検索',
                lines: [
                    'チャットタブの「地図で探す」を開きます。',
                    '位置情報を許可すると近くのユーザーを距離順に表示します。',
                ],
            },
        ],
    },
    zh: {
        title: '地图找好友',
        summary: '在地图上查找附近用户。',
        sections: [
            {
                heading: '附近查找',
                lines: [
                    '在聊天页打开「地图查找」。',
                    '允许定位后按距离显示附近的应用用户。',
                ],
            },
        ],
    },
};

const BY_ID: Partial<Record<string, Record<BundledUiLang, BundledManualContent>>> = {
    overview: OVERVIEW,
    face: FACE,
    chat: CHAT,
    voip: VOIP,
    map: MAP,
};

export function getBundledManual(manualId: string, lang: string): BundledManualContent | null {
    const catalogLang = resolveBundledCatalogLang(lang);
    const pack = BY_ID[manualId];
    return pack?.[catalogLang] ?? pack?.en ?? null;
}

export function hasBundledManual(manualId: string, lang: string): boolean {
    return isBundledUiLang(lang) && !!getBundledManual(manualId, lang);
}

export function bundledManualFromFeature(manual: FeatureManual, lang: string): BundledManualContent | null {
    return getBundledManual(manual.id, lang);
}
