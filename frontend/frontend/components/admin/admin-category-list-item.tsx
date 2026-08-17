'use client';

import AdminCategoryDisplayCard from '@/components/admin/admin-category-display-card';
import AdminCategoryEditCard from '@/components/admin/admin-category-edit-card';
import { createEmptyCategoryStat, type AdminProjectItem, type CategoryItem, type CategoryStat } from '@/lib/admin-category-service';

interface AdminCategoryListItemProps {
    category: CategoryItem;
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

export default function AdminCategoryListItem(props: AdminCategoryListItemProps) {
    const isEditing = props.editingCategoryId === props.category.id;
    const categoryStat = props.categoryStats[props.category.id] ?? createEmptyCategoryStat();
    const recentProjects = props.categoryRecentProjects[props.category.id] ?? [];

    return (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
            {isEditing ? (
                <AdminCategoryEditCard
                    categoryId={props.category.id}
                    editingCategoryName={props.editingCategoryName}
                    editingCategoryDescription={props.editingCategoryDescription}
                    categoryUpdatingId={props.categoryUpdatingId}
                    onUpdateCategory={props.onUpdateCategory}
                    onCancelEditCategory={props.onCancelEditCategory}
                    onEditingCategoryNameChange={props.onEditingCategoryNameChange}
                    onEditingCategoryDescriptionChange={props.onEditingCategoryDescriptionChange}
                />
            ) : (
                <AdminCategoryDisplayCard
                    category={props.category}
                    categoryStat={categoryStat}
                    recentProjects={recentProjects}
                    categoryDeletingId={props.categoryDeletingId}
                    onBeginEditCategory={props.onBeginEditCategory}
                    onDeleteCategory={props.onDeleteCategory}
                />
            )}
        </div>
    );
}
