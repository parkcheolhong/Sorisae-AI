/**
 * 전역 UI 번역 프리페치용 한국어 원문 수집 — 51개 LANGS 공통 SSOT.
 */
import { UI_TEXT } from '../../app/appUiText';
import { SECTION_RAIL_DEFS } from '../navigation/sectionRegistry';
import { getSettingsText } from '../settings/settingsUiText';

function collectRecordStrings(record: Record<string, string>): string[] {
    return Object.values(record).filter((v) => typeof v === 'string' && v.trim().length > 0);
}

/** 앱 UI에 반복 등장하는 한국어 원문(설정·탭·사전) — 언어 변경 시 일괄 프리페치. */
export function collectKoUiStrings(): string[] {
    const seen = new Set<string>();
    const add = (text: string) => {
        const t = String(text || '').trim();
        if (t) seen.add(t);
    };
    collectRecordStrings(UI_TEXT.ko as Record<string, string>).forEach(add);
    collectRecordStrings(getSettingsText() as unknown as Record<string, string>).forEach(add);
    SECTION_RAIL_DEFS.forEach((def) => add(def.label));
    return [...seen];
}
