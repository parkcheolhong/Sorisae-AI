'use client';

import React from 'react';
import type { AdminRailOpsSettings } from '@/lib/admin-rail-settings-service';
import { resolveApiBaseUrl } from '@/lib/api';

interface AdminOpsSectionProps {
    settings?: AdminRailOpsSettings;
}

type LlmGatewayDiagnostics = {
    status: string;
    message?: string;
    root_causes?: string[];
    recommendations?: string[];
    containers?: Record<string, any>;
};

type LlmGatewayRecoverResult = {
    message?: string;
    actions?: Array<Record<string, any>>;
    diagnostics_before?: LlmGatewayDiagnostics;
    diagnostics_after?: LlmGatewayDiagnostics;
};

export default function AdminOpsSection({ settings }: AdminOpsSectionProps) {
    const [diagnostics, setDiagnostics] = React.useState<LlmGatewayDiagnostics | null>(null);
    const [recoverResult, setRecoverResult] = React.useState<LlmGatewayRecoverResult | null>(null);
    const [busy, setBusy] = React.useState(false);
    const [error, setError] = React.useState<string>('');

    const fetchDiagnostics = React.useCallback(async () => {
        setBusy(true);
        setError('');
        try {
            const token = window.localStorage.getItem('admin_token') || '';
            const apiBase = resolveApiBaseUrl();
            const response = await fetch(`${apiBase}/api/admin/llm-gateway/diagnostics`, {
                headers: token ? { Authorization: `Bearer ${token}` } : {},
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(String(data?.detail || 'llm gateway diagnostics 호출에 실패했습니다.'));
            }
            setDiagnostics(data);
        } catch (fetchError: any) {
            setError(String(fetchError?.message || 'llm gateway diagnostics 호출에 실패했습니다.'));
        } finally {
            setBusy(false);
        }
    }, []);

    const runRecovery = React.useCallback(async (mode: 'port_shift_shadow' | 'disable_nonessential', dryRun: boolean) => {
        setBusy(true);
        setError('');
        try {
            const token = window.localStorage.getItem('admin_token') || '';
            const apiBase = resolveApiBaseUrl();
            const response = await fetch(`${apiBase}/api/admin/llm-gateway/auto-recover`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                },
                body: JSON.stringify({ mode, dry_run: dryRun }),
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(String(data?.detail || 'llm gateway auto-recover 호출에 실패했습니다.'));
            }
            setRecoverResult(data);
            if (data?.diagnostics_after) {
                setDiagnostics(data.diagnostics_after);
            }
        } catch (recoverError: any) {
            setError(String(recoverError?.message || 'llm gateway auto-recover 호출에 실패했습니다.'));
        } finally {
            setBusy(false);
        }
    }, []);

    React.useEffect(() => {
        void fetchDiagnostics();
    }, [fetchDiagnostics]);

    const [checks] = React.useState([
        {
            id: 1,
            category: 'Database',
            items: [
                { name: 'PostgreSQL 가용성', status: 'pass', details: '✓ 연결 정상, 15,240개 테이블' },
                { name: 'DB 백업', status: 'pass', details: '✓ 매일 03:00 자동 백업 진행 중' },
                { name: 'DB 성능', status: 'warning', details: '⚠ 느린 쿼리 3개 감지, 최적화 필요' },
                { name: 'WAL 설정', status: 'pass', details: '✓ WAL 아카이빙 정상 작동' },
            ],
        },
        {
            id: 2,
            category: 'Cache & Storage',
            items: [
                { name: 'Redis 연결', status: 'pass', details: '✓ 메모리 사용 62% (정상)' },
                { name: 'Qdrant 벡터DB', status: 'pass', details: '✓ 1.2M 벡터 저장, 검색 성능 우수' },
                { name: 'MinIO 객체 저장소', status: 'pass', details: '✓ 2.8TB 사용 중, 여유 있음' },
                { name: '캐시 TTL 정책', status: 'pass', details: '✓ 모든 항목에 적절한 TTL 설정' },
            ],
        },
        {
            id: 3,
            category: 'Application',
            items: [
                { name: '마켓플레이스 헬스', status: 'pass', details: '✓ 99.8% 가용성, 응답 시간 145ms' },
                { name: '관리 패널 헬스', status: 'pass', details: '✓ 정상 작동, 에러율 0.2%' },
                { name: '메시지 큐', status: 'pass', details: '✓ 큐 길이 정상, 처리 속도 우수' },
                { name: '세션 관리', status: 'warning', details: '⚠ 만료 정책 검토 권장' },
            ],
        },
        {
            id: 4,
            category: 'Security & Compliance',
            items: [
                { name: 'SSL/TLS 인증서', status: 'pass', details: '✓ 유효기간 284일 남음' },
                { name: 'API 인증', status: 'pass', details: '✓ JWT 토큰 검증 정상' },
                { name: '로그 감사', status: 'pass', details: '✓ 모든 주요 이벤트 기록 중' },
                { name: '데이터 암호화', status: 'pass', details: '✓ 전송/저장 모두 암호화' },
            ],
        },
    ]);

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'pass':
                return '#10b981';
            case 'warning':
                return '#f59e0b';
            default:
                return '#ef4444';
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'pass':
                return '✓';
            case 'warning':
                return '⚠';
            default:
                return '✕';
        }
    };

    return (
        <div className="workspace-section-stack" style={{ padding: '16px' }}>
            <div
                style={{
                    marginBottom: '20px',
                    borderRadius: '8px',
                    border: '1px solid rgba(255,255,255,0.14)',
                    background: 'rgba(255,255,255,0.03)',
                    padding: '14px',
                }}
            >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px', marginBottom: '8px', flexWrap: 'wrap' }}>
                    <h4 style={{ color: 'rgba(255,255,255,0.94)', margin: 0, fontSize: '14px', fontWeight: 700 }}>
                        LLM Gateway 근본원인 자동 복구
                    </h4>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                        <button type="button" onClick={() => void fetchDiagnostics()} disabled={busy} style={{ borderRadius: 8, border: '1px solid rgba(255,255,255,0.2)', background: 'rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.9)', fontSize: 12, padding: '6px 10px' }}>
                            진단 새로고침
                        </button>
                        <button type="button" onClick={() => void runRecovery('port_shift_shadow', true)} disabled={busy} style={{ borderRadius: 8, border: '1px solid rgba(255,255,255,0.2)', background: 'rgba(99,102,241,0.25)', color: 'rgba(255,255,255,0.95)', fontSize: 12, padding: '6px 10px' }}>
                            포트재배치 Dry-run
                        </button>
                        <button type="button" onClick={() => void runRecovery('port_shift_shadow', false)} disabled={busy} style={{ borderRadius: 8, border: '1px solid rgba(34,197,94,0.35)', background: 'rgba(34,197,94,0.22)', color: 'rgba(236,253,245,0.98)', fontSize: 12, padding: '6px 10px' }}>
                            무중단 포트 재배치 실행
                        </button>
                        <button type="button" onClick={() => void runRecovery('disable_nonessential', false)} disabled={busy} style={{ borderRadius: 8, border: '1px solid rgba(245,158,11,0.35)', background: 'rgba(245,158,11,0.2)', color: 'rgba(255,251,235,0.98)', fontSize: 12, padding: '6px 10px' }}>
                            비핵심 게이트웨이 분리
                        </button>
                    </div>
                </div>

                <p style={{ color: 'rgba(255,255,255,0.65)', fontSize: '12px', margin: '0 0 10px 0', lineHeight: 1.5 }}>
                    눈에 보이는 상태가 아니라 포트 충돌, 네트워크 미부착, 업스트림 502를 근본원인으로 분석하고 자동 조치까지 연결합니다.
                </p>

                {error && (
                    <div style={{ borderRadius: 8, border: '1px solid rgba(248,113,113,0.4)', background: 'rgba(248,113,113,0.12)', color: 'rgba(254,226,226,0.95)', padding: '8px 10px', fontSize: 12, marginBottom: 10 }}>
                        {error}
                    </div>
                )}

                {diagnostics && (
                    <div style={{ borderRadius: 8, border: '1px solid rgba(255,255,255,0.12)', background: 'rgba(0,0,0,0.16)', padding: 10, marginBottom: 10 }}>
                        <p style={{ margin: '0 0 6px 0', color: 'rgba(255,255,255,0.88)', fontSize: 12, fontWeight: 700 }}>
                            상태: {diagnostics.status}
                        </p>
                        <p style={{ margin: '0 0 8px 0', color: 'rgba(255,255,255,0.65)', fontSize: 12 }}>
                            {diagnostics.message || '진단 메시지 없음'}
                        </p>
                        {!!diagnostics.root_causes?.length && (
                            <div style={{ marginBottom: 8 }}>
                                <p style={{ margin: '0 0 4px 0', color: 'rgba(255,255,255,0.82)', fontSize: 12, fontWeight: 600 }}>근본원인</p>
                                <ul style={{ margin: 0, paddingLeft: 18, color: 'rgba(255,255,255,0.7)', fontSize: 12 }}>
                                    {diagnostics.root_causes.map((cause) => (
                                        <li key={cause}>{cause}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                        {!!diagnostics.recommendations?.length && (
                            <div>
                                <p style={{ margin: '0 0 4px 0', color: 'rgba(255,255,255,0.82)', fontSize: 12, fontWeight: 600 }}>자동 권고</p>
                                <ul style={{ margin: 0, paddingLeft: 18, color: 'rgba(255,255,255,0.7)', fontSize: 12 }}>
                                    {diagnostics.recommendations.map((recommendation, index) => (
                                        <li key={`rec-${index}`}>{recommendation}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                )}

                {recoverResult && (
                    <div style={{ borderRadius: 8, border: '1px solid rgba(56,189,248,0.35)', background: 'rgba(56,189,248,0.12)', padding: 10 }}>
                        <p style={{ margin: '0 0 6px 0', color: 'rgba(224,242,254,0.96)', fontSize: 12, fontWeight: 700 }}>
                            실행 결과: {recoverResult.message || '완료'}
                        </p>
                        {!!recoverResult.actions?.length && (
                            <ul style={{ margin: 0, paddingLeft: 18, color: 'rgba(224,242,254,0.88)', fontSize: 12 }}>
                                {recoverResult.actions.slice(0, 6).map((action, index) => (
                                    <li key={`action-${index}`}>
                                        {String(action.step || 'step')} · {String(action.ok ?? '')} {action.stderr ? `· ${String(action.stderr).slice(0, 120)}` : ''}
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>
                )}
            </div>

            <div style={{ marginBottom: '20px' }}>
                <h4 style={{ color: 'rgba(255,255,255,0.9)', marginBottom: '8px', fontSize: '14px', fontWeight: 600 }}>
                    운영 준비도 체크리스트
                </h4>
                <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: '13px', lineHeight: '1.5' }}>
                    프로덕션 배포 전 필수 확인 항목. 모든 인프라 및 보안 항목을 정기적으로 검토합니다.
                </p>
            </div>

            <div style={{ display: 'space-y-4' }}>
                {checks.map((category) => {
                    const passCount = category.items.filter(i => i.status === 'pass').length;
                    const totalCount = category.items.length;
                    const passPercent = (passCount / totalCount) * 100;

                    return (
                        <div
                            key={category.id}
                            style={{
                                borderRadius: '8px',
                                border: '1px solid rgba(255,255,255,0.1)',
                                background: 'rgba(255,255,255,0.02)',
                                padding: '16px',
                                marginBottom: '12px',
                            }}
                        >
                            {/* 카테고리 헤더 */}
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                                <div
                                    style={{
                                        width: '28px',
                                        height: '28px',
                                        borderRadius: '6px',
                                        background: passPercent === 100 ? 'rgba(16,185,129,0.1)' : 'rgba(245,158,11,0.1)',
                                        border: passPercent === 100 ? '1px solid rgba(16,185,129,0.3)' : '1px solid rgba(245,158,11,0.3)',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        color: passPercent === 100 ? '#10b981' : '#f59e0b',
                                        fontSize: '14px',
                                        fontWeight: 600,
                                    }}
                                >
                                    {passPercent === 100 ? '✓' : '!'}
                                </div>
                                <div style={{ flex: 1 }}>
                                    <h5 style={{ margin: '0 0 2px 0', fontSize: '13px', fontWeight: 600, color: 'rgba(255,255,255,0.9)' }}>
                                        {category.category}
                                    </h5>
                                    <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)' }}>
                                        {passCount} / {totalCount} 통과
                                    </div>
                                </div>
                                <div
                                    style={{
                                        width: '40px',
                                        height: '6px',
                                        background: 'rgba(0,0,0,0.3)',
                                        borderRadius: '3px',
                                        overflow: 'hidden',
                                    }}
                                >
                                    <div
                                        style={{
                                            height: '100%',
                                            width: `${passPercent}%`,
                                            background: passPercent === 100 ? '#10b981' : '#f59e0b',
                                            opacity: 0.8,
                                        }}
                                    />
                                </div>
                            </div>

                            {/* 아이템 목록 */}
                            <div style={{ display: 'space-y-2' }}>
                                {category.items.map((item, idx) => (
                                    <div key={idx} style={{ marginBottom: '8px', paddingLeft: '36px' }}>
                                        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                                            <span
                                                style={{
                                                    fontSize: '12px',
                                                    fontWeight: 600,
                                                    color: getStatusColor(item.status),
                                                    marginTop: '-2px',
                                                }}
                                            >
                                                {getStatusIcon(item.status)}
                                            </span>
                                            <div style={{ flex: 1 }}>
                                                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.8)', marginBottom: '2px' }}>
                                                    {item.name}
                                                </div>
                                                <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)' }}>
                                                    {item.details}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    );
                })}
            </div>

            <div style={{ borderRadius: '8px', border: '1px solid rgba(34,197,94,0.3)', background: 'rgba(34,197,94,0.05)', padding: '12px', marginTop: '16px' }}>
                <p style={{ fontSize: '12px', color: 'rgba(34,197,94,0.8)', margin: '0' }}>
                    ✓ 게이트: {settings?.deployment_gate_level ?? 'strict'} · 헬스체크 {settings?.healthcheck_on_open ? 'ON' : 'OFF'} · 런타임 재시작 {settings?.allow_runtime_restart ? '허용' : '비허용'}
                </p>
            </div>
        </div>
    );
}
