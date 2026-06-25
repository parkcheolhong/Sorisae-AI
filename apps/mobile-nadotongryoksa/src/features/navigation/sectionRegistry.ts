/**
 * [기능 분리 Phase5.7] 섹션 레일 단일 레지스트리(SSOT) — 자동 넘버링 + 자동 연결.
 *
 * 기존에 5곳에 흩어져 있던 레일 정의(타입 union / SECTION_RAIL_ITEMS / 셀렉터 빌더 /
 * 딥링크 파서 / correlation featureId)를 **한 곳**에서 정의하고 나머지를 전부 파생한다.
 *
 * ▶ 자동 넘버링: 정의 순서가 곧 고유 `numericId`(1부터). 항목 추가/재배치 시 자동 재매핑.
 * ▶ 자동 연결: 항목 1개만 추가하면
 *     - `SectionRailKey` 유니온 타입
 *     - 레일 렌더 아이템(`SECTION_RAIL_ITEMS`)
 *     - 접근성/테스트 셀렉터(`buildSectionRailSelector`)
 *     - 딥링크/문자열 파서(`parseSectionRailKey`, aliases 포함)
 *     - correlation 기능 ID(`featureIdForSection`)
 *   가 전부 자동으로 연결된다(수기 중복 0).
 */
import { FEATURE_IDS, type FeatureId } from '../correlation/correlationId';

// ── 단일 진실원천(SSOT): 이 배열만 편집하면 전 시스템이 자동 반영된다 ──
//   순서 = 자동 넘버링(numericId). aliases 는 딥링크/레거시 문자열 매칭용(key 포함 불필요 — 자동 포함).
const SECTION_RAIL_SOURCE = [
    { key: 'chat', label: '채팅', icon: '💬', featureId: FEATURE_IDS.chatTranslate, aliases: [] },
    { key: 'voip', label: '통화', icon: '📞', featureId: FEATURE_IDS.voipVoiceRelay, aliases: [] },
    { key: 'song-mode', label: '노래', icon: '🎵', featureId: FEATURE_IDS.songTranslate, aliases: ['song'] },
    { key: 'travel-booking', label: '예약', icon: '🧭', featureId: FEATURE_IDS.orchestrate, aliases: ['travel'] },
] as const;

export type SectionRailKey = (typeof SECTION_RAIL_SOURCE)[number]['key'];

export interface SectionRailDef {
    /** 자동 부여되는 섹션 고유 번호(1부터, 정의 순서 기준). */
    readonly numericId: number;
    readonly key: SectionRailKey;
    readonly label: string;
    readonly icon: string;
    /** correlation 백본 기능 ID(로그/딜리버리/발화 전 구간 상관). */
    readonly featureId: FeatureId;
    /** 딥링크/레거시 문자열 별칭(key 는 자동 포함). */
    readonly aliases: readonly string[];
}

/** 레일 전체 정의(자동 넘버링 적용). */
export const SECTION_RAIL_DEFS: readonly SectionRailDef[] = SECTION_RAIL_SOURCE.map((def, index) => ({
    numericId: index + 1,
    key: def.key,
    label: def.label,
    icon: def.icon,
    featureId: def.featureId,
    aliases: def.aliases,
}));

// ── 파생: 조회 인덱스 ──
const BY_KEY: ReadonlyMap<SectionRailKey, SectionRailDef> = new Map(
    SECTION_RAIL_DEFS.map((def) => [def.key, def]),
);

const BY_NUMERIC_ID: ReadonlyMap<number, SectionRailDef> = new Map(
    SECTION_RAIL_DEFS.map((def) => [def.numericId, def]),
);

// key + aliases 를 모두 소문자로 색인(딥링크/레거시 문자열 → key 자동 매핑).
const BY_ALIAS: ReadonlyMap<string, SectionRailKey> = new Map(
    SECTION_RAIL_DEFS.flatMap((def) => [
        [def.key.toLowerCase(), def.key] as [string, SectionRailKey],
        ...def.aliases.map((alias) => [alias.toLowerCase(), def.key] as [string, SectionRailKey]),
    ]),
);

// ── 파생: 기존 소비부 호환 표면 ──

/** 레일 렌더 아이템({key,label,icon}) — 기존 JSX 호환 형태. */
export const SECTION_RAIL_ITEMS: Array<{ key: SectionRailKey; label: string; icon: string }> =
    SECTION_RAIL_DEFS.map(({ key, label, icon }) => ({ key, label, icon }));

/** 섹션 접근성/테스트 셀렉터(testID). */
export function buildSectionRailSelector(section: SectionRailKey): string {
    return `worldlinco-section-rail-${section}-button`;
}

/** 임의 문자열(딥링크/레거시)을 섹션 key 로 파싱(미매칭이면 null). */
export function parseSectionRailKey(value: string | null | undefined): SectionRailKey | null {
    return BY_ALIAS.get(String(value || '').trim().toLowerCase()) ?? null;
}

// ── 신규: 고유 ID 넘버링 자동 매핑 헬퍼 ──

/** 섹션 key → 고유 번호. */
export function sectionNumericId(key: SectionRailKey): number {
    return BY_KEY.get(key)?.numericId ?? 0;
}

/** 고유 번호 → 섹션 정의(미존재 null). */
export function sectionByNumericId(numericId: number): SectionRailDef | null {
    return BY_NUMERIC_ID.get(numericId) ?? null;
}

/** 섹션 key → 정의(미존재 null). */
export function sectionDefByKey(key: SectionRailKey): SectionRailDef | null {
    return BY_KEY.get(key) ?? null;
}

/** 섹션 key → correlation 기능 ID. */
export function featureIdForSection(key: SectionRailKey): FeatureId {
    return BY_KEY.get(key)?.featureId ?? FEATURE_IDS.orchestrate;
}
