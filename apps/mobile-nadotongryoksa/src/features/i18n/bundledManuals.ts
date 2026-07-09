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

const BY_ID: Partial<Record<string, Record<BundledUiLang, BundledManualContent>>> = {
    overview: OVERVIEW,
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
