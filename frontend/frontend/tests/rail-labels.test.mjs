/**
 * Rail label snapshot test — pure Node.js assertions (no Jest required).
 * Guards against accidental label/shortLabel/activeRailId regressions.
 *
 * Run: node tests/rail-labels.test.mjs
 * Included in: npm test
 */

import assert from 'node:assert/strict';
import fs from 'node:fs';

// ─── Snapshot: Marketplace left rail ────────────────────────────────────────
const LEFT_RAIL = [{
        id: 'market-home',
        label: '마켓 메인',
        shortLabel: '메인'
    },
    {
        id: 'code-generator',
        label: 'AI 엔진 코드',
        shortLabel: '코드'
    },
    {
        id: 'orchestrator',
        label: 'AI 엔진 오케스트레이터',
        shortLabel: '오케'
    },
    {
        id: 'movie-studio',
        label: 'AI 엔진 영상',
        shortLabel: '영상'
    },
];

// ─── Snapshot: Marketplace right rail ───────────────────────────────────────
const RIGHT_RAIL = [{
        id: 'generator',
        label: '음성 엔진',
        shortLabel: '음성'
    },
    {
        id: 'video-worker',
        label: '영상 워커',
        shortLabel: '워커'
    },
    {
        id: 'popular',
        label: '시스템 메트릭',
        shortLabel: '메트'
    },
    {
        id: 'ml-detectors',
        label: '외부 검증기',
        shortLabel: '검증'
    },
];

// ─── Snapshot: Page → activeRailId mapping ───────────────────────────────────
// Rule: leftActive must be a left-rail id; rightActive must be a right-rail id.
const PAGE_RAIL_MAPPING = [{
        route: '/marketplace',
        leftActive: 'market-home',
        rightActive: 'generator'
    },
    {
        route: '/marketplace/code-generator',
        leftActive: 'code-generator',
        rightActive: 'generator'
    },
    {
        route: '/marketplace/orchestrator',
        leftActive: 'orchestrator',
        rightActive: 'generator'
    },
    {
        route: '/marketplace/movie-studio',
        leftActive: 'movie-studio',
        rightActive: 'generator'
    },
    {
        route: '/marketplace/voice',
        leftActive: 'market-home',
        rightActive: 'generator'
    },
    {
        route: '/marketplace/video-worker',
        leftActive: 'market-home',
        rightActive: 'video-worker'
    },
    {
        route: '/marketplace/metrics',
        leftActive: 'market-home',
        rightActive: 'popular'
    },
    {
        route: '/marketplace/ml-detectors',
        leftActive: 'market-home',
        rightActive: 'ml-detectors'
    },
];

// ─── Snapshot: Admin override maps ──────────────────────────────────────────
const ADMIN_LEFT_OVERRIDES = {
    'admin-control-hub': '제어',
    'system-settings': '설정',
    'auto-connect': '연결',
    'health-overview': '건강',
    'ad-orders': '주문',
    category: '카테',
};

const ADMIN_RIGHT_OVERRIDES = {
    'manual-orchestrator': '오케',
    'live-logs': '로그',
    'top-projects': '인기',
    sample: '샘플',
    cost: '비용',
    'quick-links': '빠른',
};

// ─── Assertions ──────────────────────────────────────────────────────────────

// 1. Left rail order
assert.deepStrictEqual(
    LEFT_RAIL.map(i => i.id),
    ['market-home', 'code-generator', 'orchestrator', 'movie-studio'],
    'Left rail IDs order',
);

// 2. Right rail order
assert.deepStrictEqual(
    RIGHT_RAIL.map(i => i.id),
    ['generator', 'video-worker', 'popular', 'ml-detectors'],
    'Right rail IDs order',
);

// 3. No duplicate IDs across left + right
const allRailIds = [...LEFT_RAIL, ...RIGHT_RAIL].map(i => i.id);
assert.equal(new Set(allRailIds).size, allRailIds.length, 'No duplicate rail IDs across left+right');

// 4. shortLabel length ≤ 4 chars
for (const item of [...LEFT_RAIL, ...RIGHT_RAIL]) {
    assert.ok(
        item.shortLabel.length <= 4,
        `shortLabel too long: "${item.id}" → "${item.shortLabel}" (${item.shortLabel.length} chars)`,
    );
}

// 5. No empty labels
for (const item of [...LEFT_RAIL, ...RIGHT_RAIL]) {
    assert.ok(item.label.trim().length > 0, `Empty label for id="${item.id}"`);
    assert.ok(item.shortLabel.trim().length > 0, `Empty shortLabel for id="${item.id}"`);
}

// 6. Page rail mapping — each active ID must belong to the correct rail
const leftRailIds = new Set(LEFT_RAIL.map(i => i.id));
const rightRailIds = new Set(RIGHT_RAIL.map(i => i.id));

for (const mapping of PAGE_RAIL_MAPPING) {
    assert.ok(
        leftRailIds.has(mapping.leftActive),
        `leftActive "${mapping.leftActive}" not in left rail (route: ${mapping.route})`,
    );
    assert.ok(
        rightRailIds.has(mapping.rightActive),
        `rightActive "${mapping.rightActive}" not in right rail (route: ${mapping.route})`,
    );
}

// 7. Admin override key coverage
const expectedLeftIds = Object.keys(ADMIN_LEFT_OVERRIDES).sort();
const expectedRightIds = Object.keys(ADMIN_RIGHT_OVERRIDES).sort();

assert.deepStrictEqual(
    expectedLeftIds,
    ['ad-orders', 'admin-control-hub', 'auto-connect', 'category', 'health-overview', 'system-settings'],
    'Admin left override IDs',
);
assert.deepStrictEqual(
    expectedRightIds,
    ['cost', 'live-logs', 'manual-orchestrator', 'quick-links', 'sample', 'top-projects'],
    'Admin right override IDs',
);

// 8. Admin override shortLabel length ≤ 4 chars
for (const [id, label] of [...Object.entries(ADMIN_LEFT_OVERRIDES), ...Object.entries(ADMIN_RIGHT_OVERRIDES)]) {
    assert.ok(
        label.length <= 4,
        `Admin shortLabel too long: "${id}" → "${label}"`,
    );
}

// 9. Marketplace main page must not expose direct admin links
const marketplaceMainPageSource = fs.readFileSync('app/marketplace/page.tsx', 'utf8');
assert.ok(
    !marketplaceMainPageSource.includes('href="/admin') && !marketplaceMainPageSource.includes("href='/admin"),
    'Marketplace main page should not expose direct /admin links',
);

// 10. Marketplace main page must keep 5-engine legacy section label
assert.ok(
    marketplaceMainPageSource.includes('5가지 AI 엔진 상품'),
    'Marketplace main page should keep 5-engine legacy section label',
);

console.log('✓ rail-labels snapshot: PASS');