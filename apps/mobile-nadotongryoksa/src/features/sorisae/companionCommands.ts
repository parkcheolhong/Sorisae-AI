/**
 * [기능 분리 Phase5.9] 소리새 AI 진화형 동반자 — 음성 명령 파서 + 능동 제안(순수 모듈).
 *
 * 후속 요구(온디바이스 SSOT 유지) 구현:
 *  - parseCompanionCommand: "나를 잊어줘"(기억 초기화) / "나를 ~라고 불러줘"(호칭 설정) 같은
 *    온디바이스 메모리 제어 명령을 발화에서 감지(LLM 호출 없이 결정적으로 처리).
 *  - buildProactiveSuggestion: 누적 관심/도메인 습관에 근거해 능동적으로 건넬 한 마디(없으면 null).
 *
 * 순수·결정적. 실제 저장/초기화는 companionPersonaStore 가, 발화 출력은 호출부가 담당한다.
 */
import {
    domainByKey,
    type CompanionDomainKey,
} from './companionDomains';
import { topDomains, topInterests, type CompanionPersona } from './companionMemory';

export type CompanionCommandType = 'reset' | 'set_name' | 'none';

export interface CompanionCommand {
    type: CompanionCommandType;
    /** set_name 일 때 사용자가 원한 호칭. */
    name?: string;
}

const RESET_PATTERNS: readonly RegExp[] = [
    /나(를|에 대해|에 대한 거)?\s*(다)?\s*잊어\s*(줘|버려|버려줘)?/u,
    /(내|나의)?\s*기억\s*(을|를)?\s*(다)?\s*(지워|삭제|초기화)/u,
    /forget\s+(me|everything|all)/iu,
    /reset\s+(my\s+)?(memory|persona|profile)/iu,
];

// "나를 ○○라고 불러줘 / ○○라고 불러 / call me ○○"
const SET_NAME_KO_RE = /(?:나를|날|내\s*이름은|제\s*이름은)?\s*([가-힣A-Za-z0-9]{1,24}?)\s*(?:이라고|라고)\s*불러\s*(?:줘|주세요)?/u;
const SET_NAME_EN_RE = /\bcall\s+me\s+([A-Za-z0-9][A-Za-z0-9 ]{0,23})\b/iu;

function cleanName(name: string): string {
    return String(name || '').replace(/\s+/g, ' ').trim().slice(0, 24);
}

/**
 * 발화에서 온디바이스 메모리 제어 명령을 파싱한다(우선순위: reset > set_name).
 * 명령이 아니면 {type:'none'}.
 */
export function parseCompanionCommand(text: string): CompanionCommand {
    const raw = String(text || '').trim();
    if (!raw) return { type: 'none' };

    if (RESET_PATTERNS.some((re) => re.test(raw))) {
        return { type: 'reset' };
    }

    const ko = raw.match(SET_NAME_KO_RE);
    if (ko && ko[1]) {
        const name = cleanName(ko[1]);
        if (name) return { type: 'set_name', name };
    }
    const en = raw.match(SET_NAME_EN_RE);
    if (en && en[1]) {
        const name = cleanName(en[1]);
        if (name) return { type: 'set_name', name };
    }
    return { type: 'none' };
}

/** 능동 제안을 시작하는 최소 누적 턴(충분히 알게 된 뒤에만 능동적으로 건넨다). */
export const PROACTIVE_SUGGESTION_MIN_TURNS = 6;

const DOMAIN_SUGGESTION: Partial<Record<CompanionDomainKey, string>> = {
    travel: '여행 얘기 자주 했었지 — 다음 갈 곳 같이 계획해볼까?',
    'language-tutor': '요즘 외국어 공부 중이었지 — 오늘 한 문장 같이 익혀볼까?',
    'life-assist': '오늘 챙길 일 있으면 알려줘, 내가 기억해둘게.',
    wellbeing: '요즘 마음은 좀 어때? 편하게 얘기해도 돼.',
};

/**
 * 누적 페르소나(습관/관심)에 근거한 능동 제안 한 마디. 근거가 약하면 null.
 * 1순위: 주 사용 도메인 맞춤 제안 → 2순위: 자주 언급한 관심사 기반.
 */
export function buildProactiveSuggestion(persona: CompanionPersona): string | null {
    if (!persona || persona.turns < PROACTIVE_SUGGESTION_MIN_TURNS) return null;

    const [topDomain] = topDomains(persona, 1);
    if (topDomain && DOMAIN_SUGGESTION[topDomain]) {
        return DOMAIN_SUGGESTION[topDomain] as string;
    }

    const [interest] = topInterests(persona, 1);
    if (interest) {
        const label = topDomain ? domainByKey(topDomain)?.label : null;
        const tail = label ? `(${label}) ` : '';
        return `요즘 ${tail}'${interest}' 얘기 자주 했는데, 더 얘기해볼까?`;
    }
    return null;
}
