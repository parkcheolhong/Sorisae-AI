'use client';

import AdminAdOrderRow from '@/components/admin/admin-ad-order-row';
import type { AdminAdOrderActionsProps, AdminAdOrderReviewProps } from '@/components/admin/admin-ad-orders-table-types';
import type { AdminAdVideoOrderItem } from '@/lib/admin-dashboard-types';

interface AdminAdOrdersTableBlockProps {
    orders: AdminAdVideoOrderItem[];
    actionTemplateLabels: Record<string, string>;
    review: AdminAdOrderReviewProps;
    actions: AdminAdOrderActionsProps;
}

export default function AdminAdOrdersTableBlock({ orders, actionTemplateLabels, review, actions }: AdminAdOrdersTableBlockProps) {
    if (orders.length === 0) {
        return <div className="text-sm text-gray-500">광고 영상 주문 데이터가 없습니다.</div>;
    }

    return (
        <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
                <thead><tr className="border-b bg-gray-50 text-left"><th className="px-3 py-2">주문ID</th><th className="px-3 py-2">사용자</th><th className="px-3 py-2">제목</th><th className="px-3 py-2">엔진</th><th className="px-3 py-2">4D 상태</th><th className="px-3 py-2">상태</th><th className="px-3 py-2">진행률</th><th className="px-3 py-2">생성일</th><th className="px-3 py-2">액션</th></tr></thead>
                <tbody>
                    {orders.map((order) => (
                        <AdminAdOrderRow
                            key={order.id}
                            order={order}
                            actionTemplateLabels={actionTemplateLabels}
                            review={review}
                            actions={actions}
                        />
                    ))}
                </tbody>
            </table>
        </div>
    );
}
