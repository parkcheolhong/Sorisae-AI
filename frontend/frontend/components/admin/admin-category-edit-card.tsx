'use client';

interface AdminCategoryEditCardProps {
    categoryId: number;
    editingCategoryName: string;
    editingCategoryDescription: string;
    categoryUpdatingId: number | null;
    onUpdateCategory: (categoryId: number) => void;
    onCancelEditCategory: () => void;
    onEditingCategoryNameChange: (value: string) => void;
    onEditingCategoryDescriptionChange: (value: string) => void;
}

export default function AdminCategoryEditCard({
    categoryId,
    editingCategoryName,
    editingCategoryDescription,
    categoryUpdatingId,
    onUpdateCategory,
    onCancelEditCategory,
    onEditingCategoryNameChange,
    onEditingCategoryDescriptionChange,
}: AdminCategoryEditCardProps) {
    return (
        <div className="space-y-3">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <input value={editingCategoryName} onChange={(event) => onEditingCategoryNameChange(event.target.value)} placeholder="카테고리명" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" title="카테고리명 수정" />
                <input value={editingCategoryDescription} onChange={(event) => onEditingCategoryDescriptionChange(event.target.value)} placeholder="설명 (선택)" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" title="카테고리 설명 수정" />
            </div>
            <div className="flex items-center gap-2">
                <button type="button" onClick={() => onUpdateCategory(categoryId)} disabled={categoryUpdatingId === categoryId} className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:bg-blue-300">{categoryUpdatingId === categoryId ? '저장 중...' : '저장'}</button>
                <button type="button" onClick={onCancelEditCategory} className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50">취소</button>
            </div>
        </div>
    );
}
