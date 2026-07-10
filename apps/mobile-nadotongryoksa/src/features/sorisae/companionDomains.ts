/**
 * [기능 분리 Phase5.8] 소리새 AI 진화형 멀티도메인 레지스트리(SSOT) + 인텐트 분류기.
 *
 * 기존 소리새 AI 는 "관광 특화" 단일 페르소나였다. 이를 **여러 도메인을 인지하고 함께하는
 * 친구**로 확장한다. 도메인 정의를 한 곳(SSOT 배열)에 모으고, 자동 넘버링(numericId)과
 * 키워드 기반 분류기를 파생한다(sectionRegistry 와 동일한 자동 넘버링·자동 연결 패턴).
 *
 * 순수 모듈(부수효과 0) — 분류기는 결정적이며 어느 언어 입력이든 안전하게 동작한다.
 * 각 도메인의 `personaHint` 는 백엔드 친구 페르소나 시스템 프롬프트에 1줄로 주입되어
 * 답변 톤/초점을 그 도메인에 맞춘다(여행은 여러 강점 중 하나일 뿐, 정체성 전체가 아님).
 */

export type CompanionDomainKey =
    | 'companion'
    | 'travel'
    | 'knowledge'
    | 'life-assist'
    | 'wellbeing'
    | 'language-tutor';

interface CompanionDomainSource {
    readonly key: CompanionDomainKey;
    readonly label: string;
    readonly description: string;
    /** 분류 키워드(소문자 비교, 한·영 혼용). companion 은 폴백 기본값이라 비워둔다. */
    readonly keywords: readonly string[];
    /** 친구 페르소나에 1줄로 주입되는 도메인 초점 힌트. */
    readonly personaHint: string;
}

// ── 단일 진실원천(SSOT): 이 배열만 편집하면 타입·넘버링·분류기·힌트가 자동 연결된다 ──
//   순서 = 자동 넘버링(numericId). companion(일상 친구)이 1번이자 기본 폴백.
const COMPANION_DOMAIN_SOURCE = [
    {
        key: 'companion',
        label: '일상 친구',
        description: '잡담·근황·농담·반응 등 특정 정보검색이 아닌 자연스러운 친구 대화',
        keywords: [],
        personaHint:
            'Be a warm everyday friend first: chat naturally, react, joke, remember what they told you, and keep them company.',
    },
    {
        key: 'travel',
        label: '여행·관광',
        description: '장소 찾기·일정·길찾기·맛집·명소·여행 안전/문화',
        keywords: [
            '여행', '관광', '명소', '맛집', '일정', '코스', '동선', '길찾기', '가볼만', '가 볼 만',
            '호텔', '숙소', '카페', '식당', '약국', '관광지', '투어', '근처', '주변',
            'travel', 'trip', 'tour', 'hotel', 'restaurant', 'cafe', 'itinerary', 'sightsee',
            'nearby', 'directions', 'pharmacy', 'attraction',
        ],
        personaHint:
            'You also have strong travel/local-guide expertise — finding places, directions, safety, customs, and food culture for any country.',
    },
    {
        key: 'knowledge',
        label: '지식·시사·상식',
        description: '사실·역사·과학·방법(how-to)·설명 + 최신 정보·주식/시세·뉴스·날씨·환율 등 다각적 질문',
        // 주의: 'how'/'what'/'어떻게' 같은 초범용 단어는 language-tutor 와 충돌하므로 제외하고
        // 지식·시사에 특이적인 토큰만 둔다(분류 정밀도).
        keywords: [
            '왜', '무엇', '뭐야', '뜻', '의미', '설명', '방법', '차이', '역사', '과학',
            '최신', '뉴스', '주식', '시세', '주가', '환율', '날씨', '경제', '코인', '금리', '상식',
            'why', 'explain', 'meaning', 'difference', 'history', 'science',
            'what is', 'how to', 'latest', 'news', 'stock', 'price', 'weather',
            'exchange rate', 'crypto', 'today',
        ],
        personaHint:
            'When asked a factual/how-to/news/market question, answer clearly and briefly — but only state numbers, prices, or live facts you can verify; if you lack verified data, say so honestly and point to an authoritative source.',
    },
    {
        key: 'life-assist',
        label: '생활 비서',
        description: '리마인더·할일·일정·습관·루틴 등 생활 보조',
        keywords: [
            '리마인더', '알림', '기억해', '잊지마', '할일', '해야', '일정 잡', '예약', '루틴', '습관',
            '매일', '내일', '오늘', '주말', '챙겨',
            'remind', 'reminder', 'todo', 'task', 'schedule', 'routine', 'habit', 'every day',
            'tomorrow', 'don\'t forget',
        ],
        personaHint:
            'Help organize their day like a caring personal assistant: reminders, tasks, routines and habits, gently and proactively.',
    },
    {
        key: 'wellbeing',
        label: '감정 지지',
        description: '기분·고민·위로·격려 등 정서적 동반',
        keywords: [
            '힘들', '외로', '우울', '슬프', '지쳐', '불안', '걱정', '스트레스', '위로', '괜찮을까',
            '행복', '기뻐', '신나', '고마워', '보고싶',
            'lonely', 'sad', 'tired', 'anxious', 'worried', 'stress', 'depressed', 'comfort',
            'happy', 'thank you', 'miss you',
        ],
        personaHint:
            'If they share feelings, respond with genuine empathy and warmth first — listen, validate, and gently encourage; never lecture.',
    },
    {
        key: 'language-tutor',
        label: '언어쌍 교습',
        description: '50개국 언어를 지정 언어↔물어본 언어 쌍으로 표현·발음·뉘앙스를 알려주는 센스',
        keywords: [
            '뭐라고', '뭐라구', '어떻게 말', '어떻게 해', '번역', '가르쳐', '배우', '발음', '회화',
            '이라고 해', '라고 해', '으로 해', '단어', '표현',
            'how do you say', 'how to say', 'translate', 'teach me', 'pronounce', 'in english',
            'in japanese', 'say in', 'word for',
        ],
        personaHint:
            'When they want to learn a phrase, teach it as a language PAIR (their language ↔ the asked language): give the exact phrase, simple pronunciation, and one short usage/nuance tip — never make up a word you are unsure of.',
    },
] as const satisfies readonly CompanionDomainSource[];

export interface CompanionDomain extends CompanionDomainSource {
    /** 자동 부여되는 도메인 고유 번호(1부터, 정의 순서 기준). */
    readonly numericId: number;
}

/** 멀티도메인 전체 정의(자동 넘버링 적용). */
export const COMPANION_DOMAINS: readonly CompanionDomain[] = COMPANION_DOMAIN_SOURCE.map(
    (def, index) => ({ ...def, numericId: index + 1 }),
);

export const DEFAULT_COMPANION_DOMAIN: CompanionDomainKey = 'companion';

const BY_KEY: ReadonlyMap<CompanionDomainKey, CompanionDomain> = new Map(
    COMPANION_DOMAINS.map((d) => [d.key, d]),
);

const BY_NUMERIC_ID: ReadonlyMap<number, CompanionDomain> = new Map(
    COMPANION_DOMAINS.map((d) => [d.numericId, d]),
);

export interface CompanionDomainScore {
    key: CompanionDomainKey;
    score: number;
}

/**
 * 발화 텍스트에 대해 도메인별 키워드 매칭 점수를 매긴다(내림차순).
 * companion 은 키워드가 없어 항상 점수 0(폴백 기준선).
 */
export function scoreCompanionDomains(text: string): CompanionDomainScore[] {
    const low = String(text || '').toLowerCase();
    return COMPANION_DOMAINS.map((d) => {
        let score = 0;
        for (const kw of d.keywords) {
            if (kw && low.includes(kw.toLowerCase())) score += 1;
        }
        return { key: d.key, score };
    }).sort((a, b) => b.score - a.score);
}

/**
 * 발화의 주 도메인을 결정한다. 매칭이 전혀 없으면 기본값(companion).
 * 동점이면 정의 순서가 빠른(numericId 작은) 도메인을 택한다(결정적).
 */
export function classifyCompanionDomain(text: string): CompanionDomainKey {
    const ranked = scoreCompanionDomains(text);
    const top = ranked[0];
    if (!top || top.score <= 0) return DEFAULT_COMPANION_DOMAIN;
    // 동점 tie-break: numericId 오름차순.
    const topScore = top.score;
    const tied = ranked.filter((r) => r.score === topScore);
    if (tied.length === 1) return top.key;
    tied.sort((a, b) => domainNumericId(a.key) - domainNumericId(b.key));
    return tied[0].key;
}

/** 도메인 key → 고유 번호. */
export function domainNumericId(key: CompanionDomainKey): number {
    return BY_KEY.get(key)?.numericId ?? 0;
}

/** 고유 번호 → 도메인 정의(미존재 null). */
export function domainByNumericId(numericId: number): CompanionDomain | null {
    return BY_NUMERIC_ID.get(numericId) ?? null;
}

/** 도메인 key → 정의(미존재 null). */
export function domainByKey(key: CompanionDomainKey): CompanionDomain | null {
    return BY_KEY.get(key) ?? null;
}

/** 도메인 key → 페르소나 1줄 힌트(미존재 시 기본 companion 힌트). */
export function personaHintForDomain(key: CompanionDomainKey): string {
    return (BY_KEY.get(key) ?? BY_KEY.get(DEFAULT_COMPANION_DOMAIN))?.personaHint ?? '';
}
