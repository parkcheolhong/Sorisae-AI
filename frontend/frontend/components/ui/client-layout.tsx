/**
 * P1-5: 클라이언트 레이아웃 래퍼
 * 
 * Error Boundary는 클라이언트 컴포넌트여야 하므로,
 * 서버 컴포넌트인 RootLayout에서 이 래퍼를 통해 감싸줍니다.
 */
'use client';

import GlobalErrorBoundary from '@/components/ui/global-error-boundary';

export default function ClientLayout({ children }: { children: React.ReactNode }) {
    return <GlobalErrorBoundary>{children}</GlobalErrorBoundary>;
}
