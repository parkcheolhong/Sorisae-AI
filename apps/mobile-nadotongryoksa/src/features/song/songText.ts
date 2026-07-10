// [기능 분리 Phase5] 노래 번역 기능 — 순수 텍스트 헬퍼(자족적, App 상태 비의존).
// App.tsx 모놀리스에서 추출한 첫 단계. 가사 정규화/판별/시간 포맷은 부작용이 없어 안전하게 분리된다.
// (언어 코드 정규화처럼 여러 기능이 공유하는 헬퍼는 별도 공용 모듈로 분리 예정 — 여기엔 두지 않는다.)

/** 가사 라인 정규화 — 대괄호/괄호 주석, 음표 기호, 슬래시 구분을 제거하고 공백을 정리한다. */
export function normalizeLyricLine(text: string): string {
    return text
        .replace(/\[[^\]]*\]/g, ' ')
        .replace(/\([^\)]*\)/g, ' ')
        .replace(/[♪♫♬]/g, ' ')
        .replace(/\s*\/\s*/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
}

/** 가사로 볼 만한 라인인지(너무 짧거나 숫자만이면 제외, 실제 문자 스크립트 포함 시 인정). */
export function isLikelyLyricLine(text: string): boolean {
    const value = normalizeLyricLine(text);
    if (value.length < 2) return false;
    if (/^\d+$/.test(value)) return false;
    return /[A-Za-z\uac00-\ud7a3\u3040-\u30ff\u4e00-\u9fff\u0600-\u06ff\u0900-\u097f\u0400-\u04ff\u0e00-\u0e7f]/.test(value);
}

/** 직전 가사 구간과 사실상 동일(반복)한지 — 중복 자막 억제용. */
export function isRepeatedLyricSegment(current: string, previous: string): boolean {
    const a = normalizeLyricLine(current).toLowerCase();
    const b = normalizeLyricLine(previous).toLowerCase();
    if (!a || !b) return false;
    return a === b || a.includes(b) || b.includes(a);
}

/** ms → `m:ss` 자막 타임코드 포맷. */
export function formatSongFileTime(ms: number): string {
    const totalSeconds = Math.max(0, Math.floor(ms / 1000));
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}
