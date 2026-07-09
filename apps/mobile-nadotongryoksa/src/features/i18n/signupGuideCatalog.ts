/**
 * 회원가입·설정 안내 — ko/en/ja/zh 오프라인 정적 문구(한국어 플래시 없음).
 */
import { getUiLang } from './uiI18n';
import { resolveBundledCatalogLang, type BundledUiLang } from './bundledUiLangs';

export type SignupGuideKey =
    | 'signupLanguageLabel' | 'signupCountryLabel' | 'signupLanguageMeta' | 'signupCountryMeta'
    | 'signupProfileHint' | 'signupGuideTitle' | 'signupGuideLine1' | 'signupGuideLine2' | 'signupGuideLine3'
    | 'downloadLangSection' | 'downloadLangHint';

type Row = Record<BundledUiLang, string>;

const ROWS: Record<SignupGuideKey, Row> = {
    signupLanguageLabel: { ko: '회원 기본 언어', en: 'Your language', ja: '会員の基本言語', zh: '会员默认语言' },
    signupCountryLabel: { ko: '프로필 국가', en: 'Your country', ja: 'プロフィールの国', zh: '个人资料国家' },
    signupLanguageMeta: { ko: '50개 언어 전체에서 선택', en: 'Choose from 50 languages', ja: '50言語から選択', zh: '从50种语言中选择' },
    signupCountryMeta: { ko: '50개국 서비스 프로필에서 선택', en: 'Choose from 50 countries', ja: '50か国から選択', zh: '从50个国家中选择' },
    signupProfileHint: {
        ko: 'VoIP·채팅 통역은 이 프로필의 언어와 국가를 기준으로 상대와 연결됩니다. OTP 단계에서도 변경할 수 있습니다.',
        en: 'VoIP and chat interpretation use this profile language and country. You can change them during OTP verification.',
        ja: 'VoIP・チャット通訳はこのプロフィールの言語と国を基準に相手と接続します。OTP段階でも変更できます。',
        zh: 'VoIP 和聊天传译将以此资料的语言和国家连接对方。OTP 阶段也可更改。',
    },
    signupGuideTitle: { ko: '처음 사용 안내', en: 'Getting started', ja: 'はじめての方へ', zh: '入门指南' },
    signupGuideLine1: {
        ko: '국가를 선택하면 통역·번역 기본 언어가 자동으로 맞춰집니다.',
        en: 'Pick your country and your interpretation language is set automatically.',
        ja: '国を選ぶと通訳・翻訳の基本言語が自動で設定されます。',
        zh: '选择国家后，传译/翻译默认语言将自动匹配。',
    },
    signupGuideLine2: {
        ko: '설정 → 사용 설명서에서 기능별 안내를 내 언어로 볼 수 있습니다.',
        en: 'Open Settings → User guides for feature help in your language.',
        ja: '設定 → 使用説明書で各機能の案内を自分の言語で確認できます。',
        zh: '在设置 → 使用说明中可查看各功能指南（您的语言）。',
    },
    signupGuideLine3: {
        ko: '한·영·일·중 4개 언어는 앱 설치 직후 오프라인으로 바로 표시됩니다.',
        en: 'Korean, English, Japanese, and Chinese show instantly offline after install.',
        ja: '韓国語・英語・日本語・中国語はインストール直後からオフラインで表示されます。',
        zh: '韩·英·日·中四种语言安装后即可离线显示。',
    },
    downloadLangSection: { ko: '앱 표시 언어 (오프라인)', en: 'App display language (offline)', ja: 'アプリ表示言語（オフライン）', zh: '应用显示语言（离线）' },
    downloadLangHint: {
        ko: '한·영·일·중은 번역 없이 즉시 표시됩니다. 그 외 언어는 국가 선택 시 자국어로 맞춰집니다.',
        en: 'KO/EN/JA/ZH display instantly. Other languages follow your country selection.',
        ja: '韓・英・日・中は即時表示。その他の言語は国選択で母国語に合わせます。',
        zh: '韩英日中即时显示。其他语言随国家选择匹配母语。',
    },
};

export function getSignupGuideText(key: SignupGuideKey, lang?: string): string {
    const catalogLang = resolveBundledCatalogLang(lang ?? getUiLang());
    return ROWS[key]?.[catalogLang] ?? ROWS[key]?.en ?? key;
}

export const DOWNLOAD_LANGUAGE_OPTIONS: Array<{ code: BundledUiLang; label: string }> = [
    { code: 'ko', label: '한국어' },
    { code: 'en', label: 'English' },
    { code: 'ja', label: '日本語' },
    { code: 'zh', label: '中文(简体)' },
];
