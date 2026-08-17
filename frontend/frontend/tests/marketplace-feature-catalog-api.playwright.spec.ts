import { expect, test } from '@playwright/test';

const API_BASE_URL = process.env.PLAYWRIGHT_MARKETPLACE_API_URL ?? 'http://127.0.0.1:8000';

test('feature catalog API returns six enabled product groups', async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/api/marketplace/feature-catalog`);
    expect(response.ok()).toBeTruthy();

    const payload = (await response.json()) as Array<{ feature_id: string; status: string }>;
    const ids = payload.map((item) => item.feature_id).sort();

    expect(ids).toEqual([
        'ai-document',
        'ai-image',
        'ai-music',
        'ai-powerpoint',
        'ai-sheet',
        'ai-video',
    ]);

    for (const feature of payload) {
        expect(feature.status).toBe('enabled');
    }
});
