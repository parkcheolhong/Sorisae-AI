'use client';

import type { AdminProjectItem, CategoryItem, CategoryStat } from '@/lib/admin-category-service';

interface AdminCategoryDisplayCardProps {
    category: CategoryItem;
    categoryStat: CategoryStat;
    recentProjects: AdminProjectItem[];
    categoryDeletingId: number | null;
    onBeginEditCategory: (category: CategoryItem) => void;
    onDeleteCategory: (category: CategoryItem) => void;
}

export default function AdminCategoryDisplayCard({
    category,
    categoryStat,
    recentProjects,
    categoryDeletingId,
    onBeginEditCategory,
    onDeleteCategory,
}: AdminCategoryDisplayCardProps) {
    const hasLinkedProjects = categoryStat.total > 0;

    return (
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
                <p className="text-sm font-semibold text-gray-900">#{category.id} {category.name}</p>
                <p className="mt-1 text-xs text-gray-500">{category.description || '설명 없음'}</p>
                <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4">
                    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-[11px] text-gray-700"><p className="text-gray-400">연결 프로젝트</p><p className="mt-1 font-semibold text-gray-900">{categoryStat.total}개</p></div>
                    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-[11px] text-gray-700"><p className="text-gray-400">다운로드</p><p className="mt-1 font-semibold text-gray-900">{categoryStat.downloads}회</p></div>
                    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-[11px] text-gray-700"><p className="text-gray-400">매출 추정</p><p className="mt-1 font-semibold text-gray-900">{Math.round(categoryStat.revenue).toLocaleString('ko-KR')}원</p></div>
                    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-[11px] text-gray-700"><p className="text-gray-400">평균 평점</p><p className="mt-1 font-semibold text-gray-900">{categoryStat.averageRating.toFixed(2)}</p><p className="mt-1 text-[10px] text-gray-400">리뷰 {categoryStat.ratingCount}건</p></div>
                </div>
                <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-gray-600">
                    <span className="rounded-full border border-gray-200 bg-white px-2 py-1">오늘 {categoryStat.today}개</span>
                    <span className="rounded-full border border-gray-200 bg-white px-2 py-1">어제 {categoryStat.yesterday}개</span>
                    <span className="rounded-full border border-gray-200 bg-white px-2 py-1">활성 {categoryStat.activeCount}개</span>
                    <span className="rounded-full border border-gray-200 bg-white px-2 py-1">비활성 {categoryStat.inactiveCount}개</span>
                    <span className="rounded-full border border-gray-200 bg-white px-2 py-1">활성 비율 {categoryStat.total > 0 ? Math.round((categoryStat.activeCount / categoryStat.total) * 100) : 0}%</span>
                </div>
                <div className="mt-3 rounded-lg border border-dashed border-gray-200 bg-white p-2">
                    <p className="text-[11px] font-semibold text-gray-500">최근 프로젝트 미리보기</p>
                    {recentProjects.length === 0 ? <p className="mt-2 text-[11px] text-gray-400">최근 등록 프로젝트가 없습니다.</p> : <div className="mt-2 space-y-1">{recentProjects.map((project) => <button key={project.id} type="button" onClick={() => window.open(`/marketplace/${project.id}`, '_blank', 'noopener,noreferrer')} className="block text-left text-[11px] text-blue-600 hover:text-blue-700 hover:underline">• #{project.id} {project.title || '제목 없음'}<span className="ml-2 text-gray-400">{project.created_at ? new Date(project.created_at).toLocaleDateString('ko-KR') : '-'}</span></button>)}</div>}
                </div>
            </div>
            <div className="flex items-center gap-2">
                <button type="button" onClick={() => onBeginEditCategory(category)} className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50">수정</button>
                <button type="button" onClick={() => onDeleteCategory(category)} disabled={categoryDeletingId === category.id || hasLinkedProjects} className="rounded-lg border border-red-300 px-3 py-1.5 text-xs text-red-700 hover:bg-red-50 disabled:opacity-50" title={hasLinkedProjects ? `연결 프로젝트 ${categoryStat.total}개가 있어 삭제할 수 없습니다.` : '카테고리 삭제'}>{categoryDeletingId === category.id ? '삭제 중...' : `삭제${hasLinkedProjects ? ` · 연결 ${categoryStat.total}개` : ''}`}</button>
            </div>
        </div>
    );
}
