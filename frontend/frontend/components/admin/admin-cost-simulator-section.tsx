'use client';

import type { AdminCostSimulatorResponse } from '@/lib/admin-runtime-types';

type CostSimulatorForm = {
    monthly_orders: number;
    cuts_per_order: number;
    preview_runs_per_order: number;
    approved_external_cuts_per_order: number;
    candidates_per_cut: number;
    retry_rate: number;
    external_image_unit_cost: number;
    external_video_unit_cost: number;
    external_video_ratio: number;
    local_preview_unit_cost: number;
    local_stitch_unit_cost: number;
    storage_unit_cost: number;
    premium_ratio: number;
    currency: string;
};

interface AdminCostSimulatorSectionProps {
    form: CostSimulatorForm;
    loading: boolean;
    error: string;
    result: AdminCostSimulatorResponse | null;
    onFieldChange: (key: keyof CostSimulatorForm, value: string) => void;
    onRun: () => void;
}

export default function AdminCostSimulatorSection({
    form,
    loading,
    error,
    result,
    onFieldChange,
    onRun,
}: AdminCostSimulatorSectionProps) {
    return (
        <>
            <h2 className="mb-3 text-lg font-semibold text-gray-900">💸 비용 시뮬레이터</h2>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                {[
                    ['monthly_orders', '월 주문 수'],
                    ['cuts_per_order', '주문당 컷 수'],
                    ['preview_runs_per_order', '주문당 로컬 preview 횟수'],
                    ['approved_external_cuts_per_order', '승인 외부 컷 수'],
                    ['candidates_per_cut', '컷당 후보 수'],
                    ['retry_rate', '재시도 비율'],
                    ['external_image_unit_cost', '외부 이미지 단가'],
                    ['external_video_unit_cost', '외부 비디오 단가'],
                    ['external_video_ratio', '외부 비디오 사용 비율'],
                    ['local_preview_unit_cost', '로컬 preview 단가'],
                    ['local_stitch_unit_cost', '로컬 stitch 단가'],
                    ['storage_unit_cost', '저장/전송 단가'],
                    ['premium_ratio', '프리미엄 주문 비율'],
                ].map(([key, label]) => (
                    <label key={key} className="block text-xs font-medium text-gray-700">
                        {label}
                        <input
                            type="number"
                            step="0.01"
                            value={String(form[key as keyof CostSimulatorForm])}
                            onChange={(event) => onFieldChange(key as keyof CostSimulatorForm, event.target.value)}
                            className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                        />
                    </label>
                ))}
                <label className="block text-xs font-medium text-gray-700">
                    통화
                    <input
                        value={form.currency}
                        onChange={(event) => onFieldChange('currency', event.target.value)}
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    />
                </label>
            </div>
            <div className="mt-4 flex items-center gap-2">
                <button
                    type="button"
                    onClick={onRun}
                    disabled={loading}
                    className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                >
                    {loading ? '계산 중...' : '비용 계산 실행'}
                </button>
                {error && <span className="text-xs text-red-600">{error}</span>}
            </div>
            {result && (
                <div className="mt-4 space-y-4">
                    <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
                        {result.scenarios.map((scenario) => (
                            <div key={scenario.key} className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                                <p className="text-sm font-semibold text-gray-900">{scenario.label}</p>
                                <p className="mt-2 text-xs text-gray-600">{scenario.summary}</p>
                                <div className="mt-3 space-y-1 text-xs text-gray-700">
                                    <p>월 외부 호출량: {scenario.monthly_external_calls.toLocaleString('ko-KR')}</p>
                                    <p>월 로컬 실행량: {scenario.monthly_local_runs.toLocaleString('ko-KR')}</p>
                                    <p>월 총비용: {scenario.monthly_cost.toLocaleString('ko-KR')} {form.currency}</p>
                                    <p>주문당 비용: {scenario.cost_per_order.toLocaleString('ko-KR')} {form.currency}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                    <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900">
                        <p className="font-semibold">권장 아키텍처: {result.recommended_architecture.mode}</p>
                        <p className="mt-2">{result.recommended_architecture.reason}</p>
                        <p className="mt-2 text-xs">pipeline: {result.recommended_architecture.pipeline.join(' → ')}</p>
                        <p className="mt-1 text-xs">external model interface: {result.recommended_architecture.external_model_interface_contract}</p>
                    </div>
                    <div className="rounded-lg border border-gray-200 bg-white p-4">
                        <p className="text-sm font-semibold text-gray-900">실제 비용 계산식</p>
                        <pre className="mt-3 overflow-x-auto whitespace-pre-wrap text-xs text-gray-700">{result.formula_markdown}</pre>
                    </div>
                </div>
            )}
        </>
    );
}
