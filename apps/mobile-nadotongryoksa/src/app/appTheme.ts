// ─────────────────────────────────────────────
// 색상 팔레트 (WorldLinco 라이트/하늘색 테마)  — App.tsx 에서 분리
// ─────────────────────────────────────────────
export const C = {
    bg: '#e3f0ff', // 소리새 하늘색(루트 배경 폴백). 실제 배경은 SKY_BG 그라데이션.
    surface: '#ffffff', // 라이트: 흰 카드
    border: '#dce6f2',
    accent: '#1e6fe0',
    green: '#19c37d',
    text: '#1a1f36', // 라이트: 진한 본문
    sub: '#5f6b80',
    badge: '#e8f1ff',
};

export const SECTION_TAB_COLORS: Record<string, string> = {
    'chat': '#1E6FE0',
    'voip': '#0B2E5E',
    'song-mode': '#7C5CFC',
    'tourism-promo': '#E07C1E',
    'travel-booking': '#19C37D',
};
