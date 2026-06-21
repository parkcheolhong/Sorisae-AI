/**
 * 콘텐츠(사진·동영상) 저작권 게이트 — 표시 레이어용(백엔드 media_license.py 미러).
 * default-deny: 라이선스 미상/저작권보유 → 차단. NC → 차단(상업 플랫폼).
 * 허용: PD/CC0, CC-BY 계열(NC 미포함), 자체보유/상업. CC-BY·ND·상업은 출처표기 필수.
 */

export type MediaInput = {
    url?: string;
    src?: string;
    license?: string | null;
    license_id?: string | null;
    author?: string | null;
    creator?: string | null;
    source?: string | null;
    provider?: string | null;
    license_url?: string | null;
    title?: string | null;
    type?: string | null;
};

export type MediaDecision = {
    allowed: boolean;
    url?: string;
    type: string;
    title?: string | null;
    licenseLabel: string | null;
    licenseUrl: string | null;
    requiresAttribution: boolean;
    attribution: string | null;
    reason: string;
};

const PUBLIC_DOMAIN = new Set([
    'cc0', 'cc0-1.0', 'cc-0', 'pd', 'pdm', 'publicdomain', 'public-domain', 'public domain',
    'no rights reserved', 'wtfpl',
]);
const OWNED = new Set(['owned', 'own', 'self', 'proprietary', 'commercial', 'licensed', 'purchased', 'stock-licensed']);
const DENY = new Set(['all rights reserved', 'arr', 'copyright', '©', 'unknown', 'none', '', 'n/a', 'tba']);

const norm = (v?: string | null) => String(v ?? '').trim().toLowerCase().replace(/\s+/g, ' ');

function ccFlags(licenseNorm: string): string[] | null {
    if (!licenseNorm.includes('cc') && !licenseNorm.startsWith('by')) return null;
    const flags = licenseNorm.split(/[\s\-_/]+/).filter((t) => ['by', 'sa', 'nc', 'nd'].includes(t));
    return flags.length ? flags : null;
}
const ccLabel = (flags: string[]) => 'CC ' + flags.map((f) => f.toUpperCase()).join('-');
const ccUrl = (flags: string[], version = '4.0') => `https://creativecommons.org/licenses/${flags.join('-')}/${version}/`;
const versionFrom = (s: string) => (s.match(/(\d\.\d)/)?.[1] ?? '4.0');

function buildAttribution(author: string, label: string, source: string, required: boolean): string | null {
    if (!author && !source) return required ? null : label;
    let bits = [author, label].filter(Boolean).join(' / ');
    if (source) bits = bits ? `${bits} (via ${source})` : `via ${source}`;
    return bits || null;
}

export function evaluateMedia(item: MediaInput): MediaDecision {
    const licenseRaw = item.license ?? item.license_id ?? null;
    const ln = norm(licenseRaw);
    const url = item.url ?? item.src;
    const author = (item.author ?? item.creator ?? '').trim();
    const source = (item.source ?? item.provider ?? '').trim();
    const type = norm(item.type) || 'image';
    const base = { url, type, title: item.title ?? null };

    if (!url) return { ...base, allowed: false, reason: 'missing url', licenseLabel: null, licenseUrl: null, requiresAttribution: false, attribution: null };
    if (DENY.has(ln)) return { ...base, allowed: false, reason: 'unknown or all-rights-reserved', licenseLabel: null, licenseUrl: null, requiresAttribution: false, attribution: null };

    if (PUBLIC_DOMAIN.has(ln)) {
        const label = ln.includes('cc0') || ln === 'cc-0' ? 'CC0' : 'Public Domain';
        return { ...base, allowed: true, reason: 'public domain / cc0', licenseLabel: label, licenseUrl: item.license_url ?? null, requiresAttribution: false, attribution: buildAttribution(author, label, source, false) };
    }
    if (OWNED.has(ln)) {
        const req = Boolean(author || source);
        return { ...base, allowed: true, reason: 'owned / commercial', licenseLabel: 'Licensed (commercial)', licenseUrl: item.license_url ?? null, requiresAttribution: req, attribution: buildAttribution(author, 'Licensed', source, req) };
    }
    const flags = ccFlags(ln);
    if (flags) {
        if (flags.includes('nc')) return { ...base, allowed: false, reason: 'NonCommercial (NC) not allowed', licenseLabel: ccLabel(flags), licenseUrl: null, requiresAttribution: false, attribution: null };
        if (!flags.includes('by')) return { ...base, allowed: false, reason: 'ambiguous CC without BY', licenseLabel: null, licenseUrl: null, requiresAttribution: false, attribution: null };
        if (!author && !source) return { ...base, allowed: false, reason: 'CC-BY requires attribution', licenseLabel: ccLabel(flags), licenseUrl: ccUrl(flags, versionFrom(ln)), requiresAttribution: true, attribution: null };
        const label = ccLabel(flags);
        return { ...base, allowed: true, reason: 'cc-by family (non-NC)', licenseLabel: label, licenseUrl: item.license_url ?? ccUrl(flags, versionFrom(ln)), requiresAttribution: true, attribution: buildAttribution(author, label, source, true) };
    }
    return { ...base, allowed: false, reason: `unrecognized license: ${String(licenseRaw)}`, licenseLabel: null, licenseUrl: null, requiresAttribution: false, attribution: null };
}

export function filterMedia(items: MediaInput[] | undefined | null): MediaDecision[] {
    if (!Array.isArray(items)) return [];
    return items.map(evaluateMedia).filter((d) => d.allowed);
}
