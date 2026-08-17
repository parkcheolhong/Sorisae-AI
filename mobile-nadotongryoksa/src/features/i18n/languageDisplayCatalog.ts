/**
 * 통역 언어(51개) 표기 — 사용자 서비스 국가 로케일 기준 오프라인 라벨.
 */
import { LANGS, type LangCode } from '../language/languageCatalog';
import { resolveBundledCatalogLang, type BundledUiLang } from './bundledUiLangs';

type LabelRow = Partial<Record<BundledUiLang, string>>;

const ROWS: Partial<Record<LangCode, LabelRow>> = {
    ko: { ko: '한국어', en: 'Korean', ja: '韓国語', zh: '韩语' },
    en: { ko: '영어', en: 'English', ja: '英語', zh: '英语' },
    zh: { ko: '중국어(简体)', en: 'Chinese (Simplified)', ja: '中国語(簡体)', zh: '中文(简体)' },
    'zh-tw': { ko: '중국어(번체·대만)', en: 'Chinese (Traditional)', ja: '中国語(繁体)', zh: '中文(繁体)' },
    'zh-hk': { ko: '중국어(粵語·홍콩)', en: 'Cantonese (Hong Kong)', ja: '広東語(香港)', zh: '粤语(香港)' },
    ja: { ko: '일본어', en: 'Japanese', ja: '日本語', zh: '日语' },
    es: { ko: '스페인어', en: 'Spanish', ja: 'スペイン語', zh: '西班牙语' },
    fr: { ko: '프랑스어', en: 'French', ja: 'フランス語', zh: '法语' },
    de: { ko: '독일어', en: 'German', ja: 'ドイツ語', zh: '德语' },
    pt: { ko: '포르투갈어', en: 'Portuguese', ja: 'ポルトガル語', zh: '葡萄牙语' },
    ru: { ko: '러시아어', en: 'Russian', ja: 'ロシア語', zh: '俄语' },
    ar: { ko: '아랍어', en: 'Arabic', ja: 'アラビア語', zh: '阿拉伯语' },
    hi: { ko: '힌디어', en: 'Hindi', ja: 'ヒンディー語', zh: '印地语' },
    it: { ko: '이탈리아어', en: 'Italian', ja: 'イタリア語', zh: '意大利语' },
    tr: { ko: '튀르키예어', en: 'Turkish', ja: 'トルコ語', zh: '土耳其语' },
    vi: { ko: '베트남어', en: 'Vietnamese', ja: 'ベトナム語', zh: '越南语' },
    th: { ko: '태국어', en: 'Thai', ja: 'タイ語', zh: '泰语' },
    id: { ko: '인도네시아어', en: 'Indonesian', ja: 'インドネシア語', zh: '印尼语' },
    ms: { ko: '말레이어', en: 'Malay', ja: 'マレー語', zh: '马来语' },
    nl: { ko: '네덜란드어', en: 'Dutch', ja: 'オランダ語', zh: '荷兰语' },
    pl: { ko: '폴란드어', en: 'Polish', ja: 'ポーランド語', zh: '波兰语' },
    uk: { ko: '우크라이나어', en: 'Ukrainian', ja: 'ウクライナ語', zh: '乌克兰语' },
    sv: { ko: '스웨덴어', en: 'Swedish', ja: 'スウェーデン語', zh: '瑞典语' },
    no: { ko: '노르웨이어', en: 'Norwegian', ja: 'ノルウェー語', zh: '挪威语' },
    da: { ko: '덴마크어', en: 'Danish', ja: 'デンマーク語', zh: '丹麦语' },
    fi: { ko: '핀란드어', en: 'Finnish', ja: 'フィンランド語', zh: '芬兰语' },
    cs: { ko: '체코어', en: 'Czech', ja: 'チェコ語', zh: '捷克语' },
    ro: { ko: '루마니아어', en: 'Romanian', ja: 'ルーマニア語', zh: '罗马尼亚语' },
    hu: { ko: '헝가리어', en: 'Hungarian', ja: 'ハンガリー語', zh: '匈牙利语' },
    el: { ko: '그리스어', en: 'Greek', ja: 'ギリシャ語', zh: '希腊语' },
    he: { ko: '히브리어', en: 'Hebrew', ja: 'ヘブライ語', zh: '希伯来语' },
    fil: { ko: '필리핀어', en: 'Filipino', ja: 'フィリピン語', zh: '菲律宾语' },
};

/** 서비스 국가 로케일 기준 언어명 — settings·프로필 공통. */
export function getLanguageDisplayLabel(langCode: string, displayLang?: string): string {
    const code = String(langCode || '').trim().toLowerCase() as LangCode;
    const catalogLang = resolveBundledCatalogLang(displayLang);
    const row = ROWS[code];
    if (row?.[catalogLang]) {
        return row[catalogLang]!;
    }
    if (catalogLang === 'ko' && row?.ko) {
        return row.ko;
    }
    return LANGS.find((item) => item.code === code)?.label ?? code;
}

/** tier-1 앱 표시 언어 칩 — 서비스 국가 로케일 기준. */
const CHIP_LABELS: Record<BundledUiLang, Record<BundledUiLang, string>> = {
    ko: { ko: '한국어', en: '영어', ja: '일본어', zh: '중국어(简体)' },
    en: { ko: 'Korean', en: 'English', ja: 'Japanese', zh: 'Chinese (Simplified)' },
    ja: { ko: '韓国語', en: '英語', ja: '日本語', zh: '中国語(簡体)' },
    zh: { ko: '韩语', en: '英语', ja: '日语', zh: '中文(简体)' },
};

export function getDownloadLangChipLabel(code: BundledUiLang, displayLang?: string): string {
    const catalogLang = resolveBundledCatalogLang(displayLang);
    return CHIP_LABELS[catalogLang]?.[code] ?? code;
}
