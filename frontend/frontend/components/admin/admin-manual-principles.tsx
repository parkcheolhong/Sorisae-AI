'use client';

export default function AdminManualPrinciples() {
    return (
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
                <h2 className="text-lg font-semibold text-gray-900">관리자 수동 오케스트레이션 운영 원칙</h2>
                <p className="mt-1 text-sm text-gray-600">관리자 오케스트레이터는 개별 개발 시스템의 구조 성립, 기술 정보 분석, 장기 작업 관리용이며 고객 오케스트레이터와 동일한 기능 축을 수동형으로 확인합니다. 고객 오케스트레이터와 분리된 상태로 수동 진행만 담당합니다.</p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-xs text-gray-600">고객 시스템과 관리자 시스템은 서로 독립 운영</div>
        </div>
    );
}
