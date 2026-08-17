'use client';

/**
 * P1-6: 탭 전환 시 로딩 스켈레톤
 * 
 * 어드민/마켓플레이스 탭 전환 시 빈 화면 대신
 * 프리미엄 느낌의 펄스 애니메이션 스켈레톤을 보여줍니다.
 */

export default function ViewSkeleton({ lines = 5 }: { lines?: number }) {
    return (
        <div style={{
            maxWidth: '800px',
            margin: '0 auto',
            padding: '40px 20px',
            animation: 'fadeIn 0.3s ease-in',
        }}>
            {/* 타이틀 스켈레톤 */}
            <div style={{
                width: '45%',
                height: '28px',
                borderRadius: '8px',
                background: 'linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.04) 75%)',
                backgroundSize: '200% 100%',
                animation: 'skeletonPulse 1.5s ease-in-out infinite',
                marginBottom: '12px',
            }} />
            {/* 서브타이틀 스켈레톤 */}
            <div style={{
                width: '65%',
                height: '16px',
                borderRadius: '6px',
                background: 'linear-gradient(90deg, rgba(255,255,255,0.03) 25%, rgba(255,255,255,0.06) 50%, rgba(255,255,255,0.03) 75%)',
                backgroundSize: '200% 100%',
                animation: 'skeletonPulse 1.5s ease-in-out infinite 0.1s',
                marginBottom: '32px',
            }} />

            {/* 카드 스켈레톤 */}
            <div style={{
                background: 'rgba(255,255,255,0.02)',
                border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: '16px',
                padding: '24px',
            }}>
                {Array.from({ length: lines }).map((_, i) => (
                    <div key={i} style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '12px',
                        marginBottom: i < lines - 1 ? '16px' : '0',
                    }}>
                        {/* 아이콘 자리 */}
                        <div style={{
                            width: '36px',
                            height: '36px',
                            borderRadius: '10px',
                            flexShrink: 0,
                            background: 'linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.04) 75%)',
                            backgroundSize: '200% 100%',
                            animation: `skeletonPulse 1.5s ease-in-out infinite ${i * 0.08}s`,
                        }} />
                        {/* 텍스트 라인 */}
                        <div style={{ flex: 1 }}>
                            <div style={{
                                width: `${60 + Math.random() * 30}%`,
                                height: '14px',
                                borderRadius: '4px',
                                background: 'linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.04) 75%)',
                                backgroundSize: '200% 100%',
                                animation: `skeletonPulse 1.5s ease-in-out infinite ${i * 0.08}s`,
                                marginBottom: '6px',
                            }} />
                            <div style={{
                                width: `${30 + Math.random() * 20}%`,
                                height: '10px',
                                borderRadius: '4px',
                                background: 'linear-gradient(90deg, rgba(255,255,255,0.02) 25%, rgba(255,255,255,0.05) 50%, rgba(255,255,255,0.02) 75%)',
                                backgroundSize: '200% 100%',
                                animation: `skeletonPulse 1.5s ease-in-out infinite ${i * 0.08 + 0.05}s`,
                            }} />
                        </div>
                    </div>
                ))}
            </div>

            <style>{`
                @keyframes skeletonPulse {
                    0% { background-position: 200% 0; }
                    100% { background-position: -200% 0; }
                }
                @keyframes fadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
            `}</style>
        </div>
    );
}
