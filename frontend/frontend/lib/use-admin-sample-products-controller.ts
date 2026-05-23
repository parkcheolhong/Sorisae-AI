import { useEffect, useMemo, useState } from 'react';
import {
    cleanupAdminSampleProducts,
    createAdminBatchSamples,
    createAdminSampleProduct,
    sampleTemplates,
    type SampleTemplate,
} from '@/lib/admin-sample-product-service';
import type { CategoryItem, CategoryStat } from '@/lib/admin-category-service';
import type { LiveLogItem } from '@/lib/admin-runtime-types';
import { getAdminToken } from '@/lib/admin-session';

export type UseAdminSampleProductsControllerOptions = {
    apiBaseUrl: string;
    categories: CategoryItem[];
    selectedCategoryId: number;
    setSelectedCategoryId: (value: number) => void;
    categoryStats: Record<number, CategoryStat>;
    handleAdminUnauthorized: (message?: string) => void;
    loadDashboard: (isRefresh?: boolean) => Promise<void>;
    loadCategoryStats: () => Promise<void>;
    pushLiveLog: (level: LiveLogItem['level'], message: string) => void;
    settingsStorageKey: string;
};

export function useAdminSampleProductsController(options: UseAdminSampleProductsControllerOptions) {
    const [sampleCreating, setSampleCreating] = useState<string | null>(null);
    const [sampleResult, setSampleResult] = useState('');
    const [sampleBatchCount, setSampleBatchCount] = useState(12);
    const [sampleCleanupPattern, setSampleCleanupPattern] = useState('[샘플');

    useEffect(() => {
        try {
            const storedSettingsRaw = localStorage.getItem(options.settingsStorageKey);
            if (!storedSettingsRaw) {
                return;
            }
            const settings = JSON.parse(storedSettingsRaw) as {
                batchCount?: number;
                cleanupPattern?: string;
            };
            if (typeof settings.batchCount === 'number') {
                setSampleBatchCount(Math.max(1, Math.min(60, settings.batchCount)));
            }
            if (typeof settings.cleanupPattern === 'string' && settings.cleanupPattern.length > 0) {
                setSampleCleanupPattern(settings.cleanupPattern);
            }
        } catch {
        }
    }, [options.settingsStorageKey]);

    useEffect(() => {
        try {
            localStorage.setItem(
                options.settingsStorageKey,
                JSON.stringify({
                    batchCount: sampleBatchCount,
                    cleanupPattern: sampleCleanupPattern,
                }),
            );
        } catch {
        }
    }, [options.settingsStorageKey, sampleBatchCount, sampleCleanupPattern]);

    const selectedCategoryStat = useMemo(
        () => options.categoryStats[options.selectedCategoryId] ?? { total: 0, today: 0, yesterday: 0, downloads: 0, revenue: 0, ratingSum: 0, ratingCount: 0, averageRating: 0, activeCount: 0, inactiveCount: 0 },
        [options.categoryStats, options.selectedCategoryId],
    );
    const selectedCategoryDelta = selectedCategoryStat.today - selectedCategoryStat.yesterday;

    async function refreshAfterMutation() {
        await options.loadDashboard(true);
        await options.loadCategoryStats();
    }

    async function createSampleProduct(template: SampleTemplate) {
        const token = getAdminToken();
        if (!token) {
            setSampleResult('관리자 토큰이 없습니다. 다시 로그인해주세요.');
            return;
        }

        setSampleCreating(template.key);
        setSampleResult('');
        try {
            const data = await createAdminSampleProduct({
                apiBaseUrl: options.apiBaseUrl,
                token,
                template,
                selectedCategoryId: options.selectedCategoryId,
            });
            setSampleResult(`생성 완료: ${template.title} (ID: ${data?.id ?? '-'})`);
            options.pushLiveLog('success', `샘플 상품 생성 완료: ${template.title}`);
            await refreshAfterMutation();
        } catch (error: any) {
            if (error?.message === '__ADMIN_SAMPLE_UNAUTHORIZED__') {
                options.handleAdminUnauthorized('관리자 로그인이 필요합니다. 다시 로그인하세요.');
                return;
            }
            const message = error?.message || '샘플 상품 생성 중 오류가 발생했습니다.';
            setSampleResult(message);
            options.pushLiveLog('warning', `샘플 상품 생성 실패: ${message}`);
        } finally {
            setSampleCreating(null);
        }
    }

    async function createBatchSamples() {
        const token = getAdminToken();
        if (!token) {
            setSampleResult('관리자 토큰이 없습니다. 다시 로그인해주세요.');
            return;
        }

        const targetCount = Math.max(1, Math.min(60, Number(sampleBatchCount) || 1));
        setSampleCreating('batch');
        setSampleResult('');
        try {
            const result = await createAdminBatchSamples({
                apiBaseUrl: options.apiBaseUrl,
                token,
                selectedCategoryId: options.selectedCategoryId,
                targetCount,
                templates: sampleTemplates,
            });
            setSampleResult(`일괄 생성 완료: ${result.successCount}/${result.targetCount}개 성공`);
            options.pushLiveLog('success', `샘플 상품 일괄 생성: ${result.successCount}/${result.targetCount}`);
            await refreshAfterMutation();
        } catch (error: any) {
            if (error?.message === '__ADMIN_SAMPLE_UNAUTHORIZED__') {
                options.handleAdminUnauthorized('관리자 로그인이 필요합니다. 다시 로그인하세요.');
                return;
            }
            const message = error?.message || '샘플 상품 일괄 생성 중 오류가 발생했습니다.';
            setSampleResult(message);
            options.pushLiveLog('warning', `샘플 상품 일괄 생성 실패: ${message}`);
        } finally {
            setSampleCreating(null);
        }
    }

    async function runSampleCleanup(dryRun: boolean) {
        const token = getAdminToken();
        if (!token) {
            setSampleResult('관리자 토큰이 없습니다. 다시 로그인해주세요.');
            return;
        }

        setSampleCreating(dryRun ? 'cleanup-preview' : 'cleanup-exec');
        try {
            const data = await cleanupAdminSampleProducts({
                apiBaseUrl: options.apiBaseUrl,
                token,
                pattern: sampleCleanupPattern,
                dryRun,
            });
            const message = dryRun
                ? `미리보기: ${data.matched}개 매칭됨`
                : `정리 완료: ${data.matched}개 비활성화`;
            setSampleResult(message);
            options.pushLiveLog('info', `${message} (pattern=${sampleCleanupPattern})`);
            await refreshAfterMutation();
        } catch (error: any) {
            if (error?.message === '__ADMIN_SAMPLE_UNAUTHORIZED__') {
                options.handleAdminUnauthorized('관리자 로그인이 필요합니다. 다시 로그인하세요.');
                return;
            }
            const message = error?.message || '샘플 정리 중 오류가 발생했습니다.';
            setSampleResult(message);
            options.pushLiveLog('warning', message);
        } finally {
            setSampleCreating(null);
        }
    }

    return {
        sampleTemplates,
        sampleCreating,
        sampleResult,
        sampleBatchCount,
        setSampleBatchCount,
        sampleCleanupPattern,
        setSampleCleanupPattern,
        selectedCategoryStat,
        selectedCategoryDelta,
        createSampleProduct,
        createBatchSamples,
        runSampleCleanup,
        categories: options.categories,
        selectedCategoryId: options.selectedCategoryId,
        setSelectedCategoryId: options.setSelectedCategoryId,
    };
}

export function assertAdminSampleProductsControllerContract() {
    if (!Array.isArray(sampleTemplates) || sampleTemplates.length < 3) {
        throw new Error('admin sample products controller contract 누락: 샘플 템플릿 3종 필요');
    }
}
