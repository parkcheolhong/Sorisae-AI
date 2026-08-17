'use client';

import AdminCategoryListBlock from '@/components/admin/admin-category-list-block';
import type { AdminProjectItem, CategoryItem, CategoryStat } from '@/lib/admin-category-service';

type CategorySortBy = 'name' | 'projects' | 'today' | 'downloads' | 'revenue' | 'rating' | 'active';

interface AdminCategoryManagementSectionProps {
    list: {
        visibleCategories: CategoryItem[];
        sortedVisibleCategories: CategoryItem[];
        categoryStats: Record<number, CategoryStat>;
        categoryRecentProjects: Record<number, AdminProjectItem[]>;
        categoryMessage: string;
        categoryUpdatingId: number | null;
        categoryDeletingId: number | null;
        onLoadCategories: () => void;
        onUpdateCategory: (categoryId: number) => void;
        onCancelEditCategory: () => void;
        onBeginEditCategory: (category: CategoryItem) => void;
        onDeleteCategory: (category: CategoryItem) => void;
    };
    filter: {
        categoryName: string;
        categoryDescription: string;
        categoryCreating: boolean;
        hideEmptyCategories: boolean;
        categorySortBy: CategorySortBy;
        onCategoryNameChange: (value: string) => void;
        onCategoryDescriptionChange: (value: string) => void;
        onCreateCategory: () => void;
        onHideEmptyCategoriesChange: (checked: boolean) => void;
        onCategorySortByChange: (value: CategorySortBy) => void;
    };
    editing: {
        editingCategoryId: number | null;
        editingCategoryName: string;
        editingCategoryDescription: string;
        onEditingCategoryNameChange: (value: string) => void;
        onEditingCategoryDescriptionChange: (value: string) => void;
    };
}

export default function AdminCategoryManagementSection({ list, filter, editing }: AdminCategoryManagementSectionProps) {
    return (
        <>
            <div className="mb-3 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900">🗂️ 마켓플레이스 카테고리 (간단 관리)</h2>
                <button type="button" onClick={list.onLoadCategories} className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50">목록 새로고침</button>
            </div>

            <div className="mb-3 grid grid-cols-1 gap-3 md:grid-cols-3">
                <input value={filter.categoryName} onChange={(event) => filter.onCategoryNameChange(event.target.value)} placeholder="카테고리명" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" title="카테고리명" />
                <input value={filter.categoryDescription} onChange={(event) => filter.onCategoryDescriptionChange(event.target.value)} placeholder="설명 (선택)" className="rounded-lg border border-gray-300 px-3 py-2 text-sm md:col-span-2" title="카테고리 설명" />
            </div>

            <div className="mb-3 flex items-center gap-2">
                <button type="button" onClick={filter.onCreateCategory} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:bg-indigo-300" disabled={filter.categoryCreating}>{filter.categoryCreating ? '생성 중...' : '카테고리 생성'}</button>
                <label className="flex items-center gap-2 text-xs text-gray-600"><input type="checkbox" checked={filter.hideEmptyCategories} onChange={(event) => filter.onHideEmptyCategoriesChange(event.target.checked)} />빈 카테고리 숨기기</label>
                <select value={filter.categorySortBy} onChange={(event) => filter.onCategorySortByChange(event.target.value as CategorySortBy)} className="rounded-lg border border-gray-300 px-2 py-1.5 text-xs text-gray-700" title="카테고리 정렬 기준">
                    <option value="projects">프로젝트 수순</option>
                    <option value="today">오늘 생성순</option>
                    <option value="downloads">다운로드순</option>
                    <option value="revenue">매출순</option>
                    <option value="rating">평점순</option>
                    <option value="active">활성 프로젝트 수순</option>
                    <option value="name">이름순</option>
                </select>
                {list.categoryMessage && <span className="text-xs text-gray-600">{list.categoryMessage}</span>}
            </div>

            <AdminCategoryListBlock
                visibleCategories={list.visibleCategories}
                sortedVisibleCategories={list.sortedVisibleCategories}
                categoryStats={list.categoryStats}
                categoryRecentProjects={list.categoryRecentProjects}
                categoryUpdatingId={list.categoryUpdatingId}
                categoryDeletingId={list.categoryDeletingId}
                editingCategoryId={editing.editingCategoryId}
                editingCategoryName={editing.editingCategoryName}
                editingCategoryDescription={editing.editingCategoryDescription}
                onUpdateCategory={list.onUpdateCategory}
                onCancelEditCategory={list.onCancelEditCategory}
                onBeginEditCategory={list.onBeginEditCategory}
                onDeleteCategory={list.onDeleteCategory}
                onEditingCategoryNameChange={editing.onEditingCategoryNameChange}
                onEditingCategoryDescriptionChange={editing.onEditingCategoryDescriptionChange}
            />
        </>
    );
}
