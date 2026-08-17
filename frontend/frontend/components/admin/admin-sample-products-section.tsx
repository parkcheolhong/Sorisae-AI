'use client';

import type { CategoryItem } from '@/lib/admin-category-service';
import type { SampleTemplate } from '@/lib/admin-sample-product-service';

type CategoryStatSummary = {
    total: number;
    today: number;
};

export interface AdminSampleProductsSectionProps {
    categories: CategoryItem[];
    selectedCategoryId: number;
    onSelectedCategoryIdChange: (value: number) => void;
    selectedCategoryStat: CategoryStatSummary;
    selectedCategoryDelta: number;
    sampleBatchCount: number;
    onSampleBatchCountChange: (value: number) => void;
    sampleCleanupPattern: string;
    onSampleCleanupPatternChange: (value: string) => void;
    sampleTemplates: SampleTemplate[];
    sampleCreating: string | null;
    sampleResult: string;
    onCreateBatchSamples: () => void;
    onRunSampleCleanup: (dryRun: boolean) => void;
    onCreateSampleProduct: (template: SampleTemplate) => void;
}

export default function AdminSampleProductsSection({
    categories,
    selectedCategoryId,
    onSelectedCategoryIdChange,
    selectedCategoryStat,
    selectedCategoryDelta,
    sampleBatchCount,
    onSampleBatchCountChange,
    sampleCleanupPattern,
    onSampleCleanupPatternChange,
    sampleTemplates,
    sampleCreating,
    sampleResult,
    onCreateBatchSamples,
    onRunSampleCleanup,
    onCreateSampleProduct,
}: AdminSampleProductsSectionProps) {
    return (
        <>
            <div className="mb-3 flex items-start justify-between gap-2">
                <div>
                    <h3 className="text-sm font-semibold text-gray-900">🎯 원터치 샘플 생성</h3>
                    <p className="mt-1 text-xs text-gray-500">테스트/디자인 검증용 상품을 즉시 생성합니다.</p>
                </div>
            </div>
            <div className="space-y-2">
                <div className="rounded-lg border border-dashed border-violet-300 bg-violet-50 p-3">
                    <p className="mb-2 text-xs font-semibold text-violet-700">샘플 생성 카테고리</p>
                    <select
                        value={selectedCategoryId}
                        onChange={(event) => onSelectedCategoryIdChange(Number(event.target.value))}
                        className="w-full rounded-md border border-violet-300 px-2 py-2 text-xs"
                        title="샘플 생성 카테고리 선택"
                        disabled={sampleCreating !== null || categories.length === 0}
                    >
                        {categories.length === 0 ? (
                            <option value={0}>카테고리 없음</option>
                        ) : (
                            categories.map((category) => (
                                <option key={category.id} value={category.id}>
                                    #{category.id} {category.name}
                                </option>
                            ))
                        )}
                    </select>
                    <p className="mt-2 text-[11px] text-violet-600">단건/대량 샘플 생성 시 선택된 카테고리로 등록됩니다.</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                        <span className="rounded-full border border-violet-200 bg-white px-2 py-0.5 text-[11px] text-violet-700">
                            전체 📦 {selectedCategoryStat.total}개
                        </span>
                        <span className="rounded-full border border-violet-200 bg-white px-2 py-0.5 text-[11px] text-violet-700">
                            오늘 {selectedCategoryStat.today > 0 ? '📈' : '➖'} {selectedCategoryStat.today}개
                        </span>
                        {selectedCategoryDelta !== 0 && (
                            <span
                                className={`rounded-full border px-2 py-0.5 text-[11px] ${selectedCategoryDelta > 0
                                    ? 'border-green-200 bg-green-50 text-green-700'
                                    : 'border-red-200 bg-red-50 text-red-700'
                                    }`}
                            >
                                전일 대비 {selectedCategoryDelta > 0 ? '▲' : '▼'} {selectedCategoryDelta > 0 ? '+' : ''}{selectedCategoryDelta}개
                            </span>
                        )}
                    </div>
                </div>

                <div className="rounded-lg border border-dashed border-blue-300 bg-blue-50 p-3">
                    <p className="mb-2 text-xs font-semibold text-blue-700">대량 샘플 생성</p>
                    <div className="mb-2 flex items-center gap-2">
                        <input
                            type="number"
                            min={1}
                            max={60}
                            value={sampleBatchCount}
                            onChange={(event) => onSampleBatchCountChange(Number(event.target.value))}
                            className="w-20 rounded-md border border-blue-300 px-2 py-1 text-xs"
                            title="샘플 생성 수량"
                            disabled={sampleCreating !== null}
                        />
                        <span className="text-xs text-blue-600">개 생성</span>
                    </div>
                    <button
                        type="button"
                        onClick={onCreateBatchSamples}
                        className="w-full rounded-lg bg-blue-600 py-2 text-xs font-semibold text-white hover:bg-blue-700 disabled:bg-blue-300"
                        disabled={sampleCreating !== null}
                    >
                        원터치 일괄 생성 실행
                    </button>
                </div>

                <div className="rounded-lg border border-dashed border-amber-300 bg-amber-50 p-3">
                    <p className="mb-2 text-xs font-semibold text-amber-700">중복 샘플 정리</p>
                    <input
                        value={sampleCleanupPattern}
                        onChange={(event) => onSampleCleanupPatternChange(event.target.value)}
                        className="mb-2 w-full rounded-md border border-amber-300 px-2 py-1 text-xs"
                        title="정리 패턴"
                        placeholder="[샘플"
                        disabled={sampleCreating !== null}
                    />
                    <div className="grid grid-cols-2 gap-2">
                        <button
                            type="button"
                            onClick={() => onRunSampleCleanup(true)}
                            className="rounded-lg border border-amber-300 bg-white py-2 text-xs font-semibold text-amber-700 hover:bg-amber-100 disabled:bg-amber-100"
                            disabled={sampleCreating !== null}
                        >
                            매칭 미리보기
                        </button>
                        <button
                            type="button"
                            onClick={() => onRunSampleCleanup(false)}
                            className="rounded-lg bg-amber-600 py-2 text-xs font-semibold text-white hover:bg-amber-700 disabled:bg-amber-300"
                            disabled={sampleCreating !== null}
                        >
                            매칭 일괄 정리
                        </button>
                    </div>
                </div>
                {sampleTemplates.map((template) => (
                    <button
                        key={template.key}
                        type="button"
                        onClick={() => onCreateSampleProduct(template)}
                        className="w-full rounded-lg border border-gray-300 bg-gray-50 px-3 py-2 text-left hover:bg-gray-100"
                        disabled={sampleCreating !== null}
                    >
                        <p className="text-sm font-medium text-gray-900">{template.title}</p>
                        <p className="mt-1 text-xs text-gray-500">₩{template.price.toLocaleString('ko-KR')}</p>
                    </button>
                ))}
            </div>
            <p className="mt-3 text-[11px] text-gray-400">현재 관리자 화면에서 직접 실행되는 생성 기능입니다.</p>
            {sampleCreating && <p className="mt-2 text-xs text-blue-600">생성 중...</p>}
            {sampleResult && <p className="mt-2 text-xs text-gray-700">{sampleResult}</p>}
        </>
    );
}
