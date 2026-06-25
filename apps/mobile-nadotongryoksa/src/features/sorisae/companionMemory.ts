/**
 * [기능 분리 Phase5.8] 소리새 AI 진화형 기억/페르소나 모델 — 순수 reducer(부수효과 0).
 *
 * "성격·습관·모든 것을 인지하고 함께하는 친구"의 핵심: 세션을 넘는 경량 기억.
 *  - 무엇을 기억하나: 호칭, 선호 말투(반말/존댓말), 주 사용 언어, 관심 주제 빈도,
 *    도메인 사용 빈도(=습관), 사용자가 직접 말한 기억할 사실, 첫/마지막 대화 시각, 누적 턴.
 *  - 어디에 저장하나: **온디바이스만**(companionPersonaStore 가 AsyncStorage 영속화).
 *    서버에는 압축된 "페르소나 브리프" 문자열만 요청 시 주입한다(원문/PII 서버 영속화 0).
 *  - 어떻게 진화하나: 매 대화 턴마다 observeTurn 으로 누적 → buildPersonaBrief 로 압축.
 *
 * 모든 함수는 순수·결정적. 입력 persona 를 변형하지 않고 새 객체를 반환한다(immutability).
 */
import { classifyCompanionDomain, domainByKey, type CompanionDomainKey } from './companionDomains';

export const COMPANION_PERSONA_VERSION = 1;

export type CompanionTone = 'casual' | 'polite' | 'unknown';

export interface CompanionPersona {
    version: number;
    /** 사용자가 불러달라는 호칭(자동 추출하지 않고 명시 설정 시에만). */
    preferredName: string | null;
    /** 말투 선호 누적 카운트 — resolveTone 으로 해석. */
    casualCount: number;
    politeCount: number;
    /** 주 사용 언어(마지막 관측). */
    language: string | null;
    /** 관심 주제 토큰 → 누적 빈도. */
    interests: Record<string, number>;
    /** 도메인 key → 사용 빈도(=대화 습관). */
    domainCounts: Record<string, number>;
    /** 사용자가 직접 말한 기억할 사실(짧은 스니펫, 중복제거·캡). */
    notableFacts: string[];
    /** 누적 대화 턴 수. */
    turns: number;
    firstSeenAt: string | null;
    lastSeenAt: string | null;
}

const MAX_INTERESTS = 40;
const MAX_FACTS = 8;
const FACT_MAX_LEN = 60;
/** 브리프를 주입하기 시작하는 최소 누적 턴(초반 노이즈 방지). */
export const PERSONA_BRIEF_MIN_TURNS = 3;

export function createEmptyPersona(): CompanionPersona {
    return {
        version: COMPANION_PERSONA_VERSION,
        preferredName: null,
        casualCount: 0,
        politeCount: 0,
        language: null,
        interests: {},
        domainCounts: {},
        notableFacts: [],
        turns: 0,
        firstSeenAt: null,
        lastSeenAt: null,
    };
}

// ── 토큰화/불용어(관심 주제 추출용, 한·영 공통, 결정적) ──
const STOPWORDS = new Set([
    '그리고', '그래서', '그런데', '하지만', '그냥', '진짜', '정말', '너무', '조금', '많이',
    '오늘', '내일', '지금', '여기', '저기', '거기', '우리', '너희', '그것', '이것', '저것',
    '있어', '없어', '같아', '해줘', '알려줘', '뭐야', '어디', '어떻게', '그게', '근데',
    'the', 'and', 'but', 'for', 'you', 'are', 'was', 'this', 'that', 'with', 'have',
    'just', 'really', 'very', 'today', 'tomorrow', 'now', 'here', 'there', 'what', 'how',
    'about', 'please', 'okay', 'yeah', 'like',
]);

/**
 * 관심 주제 후보 토큰 추출(결정적). 공백/구두점으로 분할 후
 * 한글/CJK 는 2자 이상, 라틴은 4자 이상 + 불용어 제거.
 */
export function extractInterestTokens(text: string): string[] {
    const raw = String(text || '').toLowerCase();
    const parts = raw.split(/[\s.,!?;:'"`()\[\]{}~\-·…‥。、！？；：「」『』，．（）【】〔〕《》0-9]+/u);
    const out: string[] = [];
    const seen = new Set<string>();
    for (const p of parts) {
        const tok = p.trim();
        if (!tok || STOPWORDS.has(tok)) continue;
        const isLatin = /^[a-z]+$/.test(tok);
        const minLen = isLatin ? 4 : 2;
        if (tok.length < minLen) continue;
        if (seen.has(tok)) continue;
        seen.add(tok);
        out.push(tok);
    }
    return out;
}

// 자기개방(기억할 사실) 신호 — 사용자가 자신에 대해 말한 문장만 보수적으로 포착.
const SELF_DISCLOSURE_RE =
    /(^|\s)(나는|난\s|내\s|제\s|저는|저\s|나\s|좋아하|싫어하|취미|꿈은|목표는)|(\bi\s|\bi'm\s|\bmy\s|\bi am\s|\bi like\b|\bi love\b|\bi hate\b)/i;

function normalizeFact(text: string): string {
    return String(text || '').replace(/\s+/g, ' ').trim().slice(0, FACT_MAX_LEN);
}

export interface ObserveTurnInput {
    transcript: string;
    answer?: string;
    /** 미지정 시 transcript 로 자동 분류. */
    domain?: CompanionDomainKey;
    language?: string | null;
    /** 시각 주입(테스트 결정성). 미지정 시 현재 시각. */
    nowIso?: string;
}

/**
 * 한 대화 턴을 관측해 페르소나를 진화시킨다(순수 — 새 객체 반환).
 * transcript(사용자 발화)에서 말투/관심/사실을 흡수하고 도메인 사용 빈도를 누적한다.
 */
export function observeTurn(persona: CompanionPersona, input: ObserveTurnInput): CompanionPersona {
    const base = persona && persona.version === COMPANION_PERSONA_VERSION ? persona : createEmptyPersona();
    const transcript = String(input.transcript || '').trim();
    if (!transcript) return base;

    const nowIso = input.nowIso || new Date().toISOString();
    const domain = input.domain || classifyCompanionDomain(transcript);

    // 말투 선호: 한국어 반말/존댓말 마커(한글은 \b 가 무의미하므로 종결어미+경계로 판정).
    let casualCount = base.casualCount;
    let politeCount = base.politeCount;
    const politeHit =
        /(습니다|십시오|세요|해요|어요|예요|이에요)/.test(transcript) || /요([\s.!?,~]|$)/.test(transcript);
    const casualHit =
        /[ㅋㅎ]/.test(transcript) || /(야|자|아|해|지|냐|니|네|다|까|줘)([\s.!?,~]|$)/.test(transcript);
    if (politeHit) {
        politeCount += 1;
    } else if (casualHit) {
        casualCount += 1;
    }

    // 관심 주제 빈도 누적(상한 유지).
    const interests: Record<string, number> = { ...base.interests };
    for (const tok of extractInterestTokens(transcript)) {
        interests[tok] = (interests[tok] || 0) + 1;
    }
    const trimmedInterests = trimTopRecord(interests, MAX_INTERESTS);

    // 도메인 사용 빈도(=습관).
    const domainCounts: Record<string, number> = { ...base.domainCounts };
    domainCounts[domain] = (domainCounts[domain] || 0) + 1;

    // 기억할 사실(자기개방 문장만, 중복제거·캡).
    let notableFacts = base.notableFacts;
    if (SELF_DISCLOSURE_RE.test(transcript)) {
        const fact = normalizeFact(transcript);
        if (fact && !notableFacts.some((f) => normalizeFact(f) === fact)) {
            notableFacts = [...notableFacts, fact].slice(-MAX_FACTS);
        }
    }

    return {
        version: COMPANION_PERSONA_VERSION,
        preferredName: base.preferredName,
        casualCount,
        politeCount,
        language: input.language != null && String(input.language).trim() ? String(input.language).trim() : base.language,
        interests: trimmedInterests,
        domainCounts,
        notableFacts,
        turns: base.turns + 1,
        firstSeenAt: base.firstSeenAt || nowIso,
        lastSeenAt: nowIso,
    };
}

/** 사용자가 명시 요청한 호칭 설정(자동 추출 금지 — 오인식 방지). */
export function setPreferredName(persona: CompanionPersona, name: string | null): CompanionPersona {
    const clean = name == null ? null : String(name).replace(/\s+/g, ' ').trim().slice(0, 24) || null;
    return { ...persona, preferredName: clean };
}

/** 누적 말투 카운트로 선호 말투 해석. */
export function resolveTone(persona: CompanionPersona): CompanionTone {
    if (persona.casualCount === 0 && persona.politeCount === 0) return 'unknown';
    if (persona.casualCount > persona.politeCount) return 'casual';
    if (persona.politeCount > persona.casualCount) return 'polite';
    return 'unknown';
}

/** 빈도 상위 N개 토큰을 내림차순으로(동점은 사전순 — 결정적). */
export function topInterests(persona: CompanionPersona, n: number): string[] {
    return Object.entries(persona.interests)
        .sort((a, b) => (b[1] - a[1]) || a[0].localeCompare(b[0]))
        .slice(0, Math.max(0, n))
        .map(([k]) => k);
}

/** 사용 빈도 상위 도메인 key(내림차순, 동점은 정의 순서). */
export function topDomains(persona: CompanionPersona, n: number): CompanionDomainKey[] {
    return Object.entries(persona.domainCounts)
        .filter(([k]) => domainByKey(k as CompanionDomainKey) !== null)
        .sort((a, b) => {
            if (b[1] !== a[1]) return b[1] - a[1];
            const an = domainByKey(a[0] as CompanionDomainKey)?.numericId ?? 99;
            const bn = domainByKey(b[0] as CompanionDomainKey)?.numericId ?? 99;
            return an - bn;
        })
        .slice(0, Math.max(0, n))
        .map(([k]) => k as CompanionDomainKey);
}

function trimTopRecord(record: Record<string, number>, max: number): Record<string, number> {
    const entries = Object.entries(record);
    if (entries.length <= max) return record;
    const kept = entries
        .sort((a, b) => (b[1] - a[1]) || a[0].localeCompare(b[0]))
        .slice(0, max);
    return Object.fromEntries(kept);
}

export interface PersonaBriefOptions {
    maxInterests?: number;
    maxFacts?: number;
    minTurns?: number;
}

/**
 * 백엔드 친구 페르소나에 주입할 **압축 브리프**(영문 1문단). 온디바이스 누적 요약만 담는다.
 * 누적 턴이 minTurns 미만이면 빈 문자열을 반환해 초반 노이즈 주입을 막는다.
 */
export function buildPersonaBrief(persona: CompanionPersona, options: PersonaBriefOptions = {}): string {
    const minTurns = options.minTurns ?? PERSONA_BRIEF_MIN_TURNS;
    if (!persona || persona.turns < minTurns) return '';

    const parts: string[] = [];
    if (persona.preferredName) {
        parts.push(`They like to be called "${persona.preferredName}".`);
    }
    const tone = resolveTone(persona);
    if (tone === 'casual') {
        parts.push('They prefer a casual, friendly tone (반말 환영).');
    } else if (tone === 'polite') {
        parts.push('They prefer a polite tone.');
    }
    const interests = topInterests(persona, options.maxInterests ?? 5);
    if (interests.length) {
        parts.push(`They often bring up: ${interests.join(', ')}.`);
    }
    const domains = topDomains(persona, 2)
        .map((k) => domainByKey(k)?.label)
        .filter((v): v is string => Boolean(v));
    if (domains.length) {
        parts.push(`Frequent conversation areas: ${domains.join(', ')}.`);
    }
    const facts = persona.notableFacts.slice(-(options.maxFacts ?? 3));
    if (facts.length) {
        parts.push(`Things they told you about themselves: ${facts.map((f) => `"${f}"`).join('; ')}.`);
    }
    if (!parts.length) return '';

    const sessions = persona.turns;
    return (
        `[Companion memory — on-device, ${sessions} turns so far] ` +
        parts.join(' ') +
        ' Greet and continue like an old friend who remembers them; weave this in naturally, never recite it back.'
    );
}
