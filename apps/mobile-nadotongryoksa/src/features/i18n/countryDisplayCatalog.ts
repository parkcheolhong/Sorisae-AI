/**
 * 설정·프로필 국가 표시 — 국기 + 서비스 국가 로케일별 국가명(오프라인).
 */
import { COUNTRY_NAME_MAP, SIGNUP_COUNTRY_OPTIONS } from '../country/countryCatalog';
import { resolveCountryFlag } from '../profile/profileFormatters';
import { resolveBundledCatalogLang, type BundledUiLang } from './bundledUiLangs';

const LOCALIZED: Partial<Record<string, Partial<Record<BundledUiLang, string>>>> = {
    KR: { ko: '대한민국', en: 'South Korea', ja: '大韓民国', zh: '韩国' },
    US: { ko: '미국', en: 'United States', ja: 'アメリカ', zh: '美国' },
    JP: { ko: '일본', en: 'Japan', ja: '日本', zh: '日本' },
    CN: { ko: '중국', en: 'China', ja: '中国', zh: '中国' },
    TW: { ko: '대만', en: 'Taiwan', ja: '台湾', zh: '台湾' },
    HK: { ko: '홍콩', en: 'Hong Kong', ja: '香港', zh: '香港' },
    VN: { ko: '베트남', en: 'Vietnam', ja: 'ベトナム', zh: '越南' },
    TH: { ko: '태국', en: 'Thailand', ja: 'タイ', zh: '泰国' },
    PH: { ko: '필리핀', en: 'Philippines', ja: 'フィリピン', zh: '菲律宾' },
    ID: { ko: '인도네시아', en: 'Indonesia', ja: 'インドネシア', zh: '印度尼西亚' },
    MY: { ko: '말레이시아', en: 'Malaysia', ja: 'マレーシア', zh: '马来西亚' },
    SG: { ko: '싱가포르', en: 'Singapore', ja: 'シンガポール', zh: '新加坡' },
    FR: { ko: '프랑스', en: 'France', ja: 'フランス', zh: '法国' },
    DE: { ko: '독일', en: 'Germany', ja: 'ドイツ', zh: '德国' },
    GB: { ko: '영국', en: 'United Kingdom', ja: 'イギリス', zh: '英国' },
    CA: { ko: '캐나다', en: 'Canada', ja: 'カナダ', zh: '加拿大' },
    AU: { ko: '호주', en: 'Australia', ja: 'オーストラリア', zh: '澳大利亚' },
    NZ: { ko: '뉴질랜드', en: 'New Zealand', ja: 'ニュージーランド', zh: '新西兰' },
    IE: { ko: '아일랜드', en: 'Ireland', ja: 'アイルランド', zh: '爱尔兰' },
    IT: { ko: '이탈리아', en: 'Italy', ja: 'イタリア', zh: '意大利' },
    ES: { ko: '스페인', en: 'Spain', ja: 'スペイン', zh: '西班牙' },
    MX: { ko: '멕시코', en: 'Mexico', ja: 'メキシコ', zh: '墨西哥' },
    AR: { ko: '아르헨티나', en: 'Argentina', ja: 'アルゼンチン', zh: '阿根廷' },
    CL: { ko: '칠레', en: 'Chile', ja: 'チリ', zh: '智利' },
    CO: { ko: '콜롬비아', en: 'Colombia', ja: 'コロンビア', zh: '哥伦比亚' },
    PE: { ko: '페루', en: 'Peru', ja: 'ペルー', zh: '秘鲁' },
    PT: { ko: '포르투갈', en: 'Portugal', ja: 'ポルトガル', zh: '葡萄牙' },
    BR: { ko: '브라질', en: 'Brazil', ja: 'ブラジル', zh: '巴西' },
    RU: { ko: '러시아', en: 'Russia', ja: 'ロシア', zh: '俄罗斯' },
    SA: { ko: '사우디아라비아', en: 'Saudi Arabia', ja: 'サウジアラビア', zh: '沙特阿拉伯' },
    AE: { ko: '아랍에미리트', en: 'United Arab Emirates', ja: 'アラブ首長国連邦', zh: '阿联酋' },
    EG: { ko: '이집트', en: 'Egypt', ja: 'エジプト', zh: '埃及' },
    QA: { ko: '카타르', en: 'Qatar', ja: 'カタール', zh: '卡塔尔' },
    KW: { ko: '쿠웨이트', en: 'Kuwait', ja: 'クウェート', zh: '科威特' },
    IN: { ko: '인도', en: 'India', ja: 'インド', zh: '印度' },
    PK: { ko: '파키스탄', en: 'Pakistan', ja: 'パキスタン', zh: '巴基斯坦' },
    BD: { ko: '방글라데시', en: 'Bangladesh', ja: 'バングラデシュ', zh: '孟加拉国' },
    TR: { ko: '튀르키예', en: 'Türkiye', ja: 'トルコ', zh: '土耳其' },
    NL: { ko: '네덜란드', en: 'Netherlands', ja: 'オランダ', zh: '荷兰' },
    PL: { ko: '폴란드', en: 'Poland', ja: 'ポーランド', zh: '波兰' },
    UA: { ko: '우크라이나', en: 'Ukraine', ja: 'ウクライナ', zh: '乌克兰' },
    SE: { ko: '스웨덴', en: 'Sweden', ja: 'スウェーデン', zh: '瑞典' },
    NO: { ko: '노르웨이', en: 'Norway', ja: 'ノルウェー', zh: '挪威' },
    DK: { ko: '덴마크', en: 'Denmark', ja: 'デンマーク', zh: '丹麦' },
    FI: { ko: '핀란드', en: 'Finland', ja: 'フィンランド', zh: '芬兰' },
    CZ: { ko: '체코', en: 'Czechia', ja: 'チェコ', zh: '捷克' },
    RO: { ko: '루마니아', en: 'Romania', ja: 'ルーマニア', zh: '罗马尼亚' },
    HU: { ko: '헝가리', en: 'Hungary', ja: 'ハンガリー', zh: '匈牙利' },
    GR: { ko: '그리스', en: 'Greece', ja: 'ギリシャ', zh: '希腊' },
    IL: { ko: '이스라엘', en: 'Israel', ja: 'イスラエル', zh: '以色列' },
};

/** 서비스 국가 로케일(displayLang)에 맞는 국가명. */
export function getCountryDisplayName(countryCode: string, displayLang?: string): string {
    const cc = String(countryCode || '').trim().toUpperCase();
    if (!cc) {
        return '';
    }
    const catalogLang = resolveBundledCatalogLang(displayLang);
    const row = LOCALIZED[cc];
    if (row?.[catalogLang]) {
        return row[catalogLang]!;
    }
    if (row?.ko) {
        return row.ko;
    }
    const fromSignup = SIGNUP_COUNTRY_OPTIONS.find((item) => item.code === cc)?.label;
    if (fromSignup) {
        return fromSignup;
    }
    return COUNTRY_NAME_MAP[cc] ?? cc;
}

/** 🇰🇷 대한민국 형식 — 설정·프로필 공통. */
export function formatCountryDisplay(countryCode: string, displayLang?: string): string {
    const cc = String(countryCode || '').trim().toUpperCase();
    if (!cc) {
        return '';
    }
    const flag = resolveCountryFlag(cc);
    const name = getCountryDisplayName(cc, displayLang);
    return `${flag} ${name}`.trim();
}
