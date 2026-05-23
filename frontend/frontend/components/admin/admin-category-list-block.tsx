'use client';

import AdminCategoryListItem from '@/components/admin/admin-category-list-item';
import type { AdminProjectItem, CategoryItem, CategoryStat } from '@/lib/admin-category-service';

interface AdminCategoryListBlockProps {
    visibleCategories: CategoryItem[];
    sortedVisibleCategories: CategoryItem[];
    categoryStats: Record<number, CategoryStat>;
    categoryRecentProjects: Record<number, AdminProjectItem[]>;
    categoryUpdatingId: number | null;
    categoryDeletingId: number | null;
    editingCategoryId: number | null;
    editingCategoryName: string;
    editingCategoryDescription: string;
    onUpdateCategory: (categoryId: number) => void;
    onCancelEditCategory: () => void;
    onBeginEditCategory: (category: CategoryItem) => void;
    onDeleteCategory: (category: CategoryItem) => void;
    onEditingCategoryNameChange: (value: string) => void;
    onEditingCategoryDescriptionChange: (value: string) => void;
}

export default function AdminCategoryListBlock(props: AdminCategoryListBlockProps) {
    if (props.visibleCategories.length === 0) {
        return <p className="text-xs text-gray-500">등록된 카테고리가 없습니다.</p>;
    }

    return (
        <div className="space-y-3">
            {props.sortedVisibleCategories.map((category) => {
                return (
                    <AdminCategoryListItem
                        key={category.id}
                        category={category}
                        categoryStats={props.categoryStats}
                        categoryRecentProjects={props.categoryRecentProjects}
                        categoryUpdatingId={props.categoryUpdatingId}
                        categoryDeletingId={props.categoryDeletingId}
                        editingCategoryId={props.editingCategoryId}
                        editingCategoryName={props.editingCategoryName}
                        editingCategoryDescription={props.editingCategoryDescription}
                        onUpdateCategory={props.onUpdateCategory}
                        onCancelEditCategory={props.onCancelEditCategory}
                        onBeginEditCategory={props.onBeginEditCategory}
                        onDeleteCategory={props.onDeleteCategory}
                        onEditingCategoryNameChange={props.onEditingCategoryNameChange}
                        onEditingCategoryDescriptionChange={props.onEditingCategoryDescriptionChange}
                    />
                );
            })}
        </div>
    );
}
