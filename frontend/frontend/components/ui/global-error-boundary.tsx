'use client';

import * as React from 'react';

/**
 * P1-5: 전역 에러 경계 (Error Boundary)
 * 
 * 런타임 에러 발생 시 전체 화면 크래시 대신
 * 사용자에게 복구 가능한 에러 화면을 보여줍니다.
 */

type ErrorBoundaryState = {
    hasError: boolean;
    error: Error | null;
};

export default class GlobalErrorBoundary extends React.Component<
    { children: React.ReactNode },
    ErrorBoundaryState
> {
    constructor(props: { children: React.ReactNode }) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error: Error): ErrorBoundaryState {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        console.error('[GlobalErrorBoundary]', error, errorInfo);
    }

    render() {
        if (this.state.hasError) {
            return (
                <div style={{
                    minHeight: '100vh',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: 'linear-gradient(135deg, #0d1117 0%, #161b22 100%)',
                    color: 'white',
                    fontFamily: "'Inter', 'Pretendard', -apple-system, sans-serif",
                    padding: '40px',
                }}>
                    <div style={{
                        background: 'rgba(255,255,255,0.05)',
                        border: '1px solid rgba(255,255,255,0.1)',
                        borderRadius: '24px',
                        padding: '48px',
                        maxWidth: '520px',
                        textAlign: 'center',
                    }}>
                        <div style={{ fontSize: '48px', marginBottom: '16px' }}>⚠️</div>
                        <h2 style={{ fontSize: '22px', fontWeight: 600, marginBottom: '12px' }}>
                            예기치 않은 오류가 발생했습니다
                        </h2>
                        <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: '14px', lineHeight: '1.6', marginBottom: '24px' }}>
                            일시적인 문제일 수 있습니다. 아래 버튼을 클릭하여 다시 시도해 주세요.
                        </p>
                        {this.state.error && (
                            <pre style={{
                                background: 'rgba(255,0,0,0.08)',
                                border: '1px solid rgba(255,0,0,0.2)',
                                borderRadius: '12px',
                                padding: '12px',
                                fontSize: '11px',
                                color: '#ff6b6b',
                                textAlign: 'left',
                                overflow: 'auto',
                                maxHeight: '120px',
                                marginBottom: '24px',
                            }}>
                                {this.state.error.message}
                            </pre>
                        )}
                        <button
                            type="button"
                            onClick={() => {
                                this.setState({ hasError: false, error: null });
                                window.location.reload();
                            }}
                            style={{
                                background: 'linear-gradient(135deg, #58c9ff 0%, #7c5cff 100%)',
                                color: 'white',
                                border: 'none',
                                borderRadius: '12px',
                                padding: '12px 32px',
                                fontSize: '14px',
                                fontWeight: 600,
                                cursor: 'pointer',
                                transition: 'opacity 0.2s',
                            }}
                        >
                            🔄 새로고침
                        </button>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}
