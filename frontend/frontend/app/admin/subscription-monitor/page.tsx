'use client';

import Link from 'next/link';
import Image from 'next/image';
import AdminSubscriptionMonitorSection from '@/components/admin/admin-subscription-monitor-section';
import { resolveApiBaseUrl } from '@/lib/api';

export default function AdminSubscriptionMonitorPage() {
    const apiBaseUrl = resolveApiBaseUrl();
    const entryRailItems = [
        { href: '/admin', label: '관리자 대시보드', note: '메인 운영 허브', icon: '/icons/entry-rail/dashboard.svg' },
        { href: '/admin/subscription-monitor?period_days=7&status=all', label: '최근 7일 모니터링', note: '단기 이슈 점검', icon: '/icons/entry-rail/recent-7days.svg' },
        { href: '/admin/subscription-monitor?period_days=30&status=all', label: '최근 30일 모니터링', note: '기본 운영 뷰', icon: '/icons/entry-rail/recent-30days.svg' },
        { href: '/admin/subscription-monitor?period_days=90&status=all', label: '최근 90일 모니터링', note: '장기 추세 확인', icon: '/icons/entry-rail/recent-90days.svg' },
        { href: '/marketplace/subscription', label: '마켓 구독 페이지', note: '사용자 화면 확인', icon: '/icons/entry-rail/marketplace.svg' },
    ] as const;

    return (
        <div className="admin-dark" style={{ minHeight: '100vh', padding: '24px' }}>
            <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
                <div className="workspace-admin-command-actions" style={{ marginBottom: '12px' }}>
                    <Link href="/admin" className="workspace-secondary-button" style={{ textDecoration: 'none' }}>
                        관리자 대시보드로 돌아가기
                    </Link>
                </div>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '16px', flexWrap: 'wrap' }}>
                    <section className="workspace-panel-card" style={{ paddingTop: '16px', flex: '1 1 760px', minWidth: '0' }}>
                        <h2 className="workspace-card-title" style={{ marginBottom: '8px' }}>💳 구독 결제 운영 모니터링</h2>
                        <p className="workspace-card-copy" style={{ marginBottom: '16px' }}>
                            실패 결제, 환불, 상태 변경 이력, 웹훅 실패를 기간/상태 필터로 확인합니다.
                        </p>
                        <AdminSubscriptionMonitorSection apiBaseUrl={apiBaseUrl} />
                    </section>

                    <aside
                        className="workspace-panel-card"
                        data-testid="admin-subscription-monitor-entry-rail"
                        style={{
                            flex: '0 1 270px',
                            width: '270px',
                            minWidth: '220px',
                            paddingTop: '16px',
                            position: 'sticky',
                            top: '16px',
                        }}
                    >
                        <h3 className="workspace-card-title" style={{ fontSize: '16px', marginBottom: '6px' }}>
                            ⚡ 진입 레일
                        </h3>
                        <p className="workspace-card-copy" style={{ marginBottom: '12px', fontSize: '12px' }}>
                            운영자가 자주 쓰는 구독 점검 경로를 우측에서 바로 이동합니다.
                        </p>
                        <div className="workspace-list">
                            {entryRailItems.map((item) => (
                                <Link
                                    key={item.href}
                                    href={item.href}
                                    className="workspace-list-item"
                                    style={{ textDecoration: 'none', color: 'inherit', display: 'flex', gap: '10px', alignItems: 'flex-start' }}
                                >
                                    <Image 
                                        src={item.icon} 
                                        alt={item.label}
                                        width={20}
                                        height={20}
                                        style={{ marginTop: '2px', minWidth: '20px', flexShrink: 0, opacity: 0.8 }}
                                    />
                                    <div style={{ flex: 1, minWidth: 0 }}>
                                        <strong style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.label}</strong>
                                        <span style={{ display: 'block', fontSize: '11px', opacity: 0.65 }}>{item.note}</span>
                                    </div>
                                </Link>
                            ))}
                        </div>
                    </aside>
                </div>
            </div>
        </div>
    );
}
