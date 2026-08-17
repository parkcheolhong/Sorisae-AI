'use client';

import { type FormEvent, useMemo, useState } from 'react';
import {
    createAdminTravelPartner,
    loadAdminTravelPartners,
    testAdminTravelConnector,
    testAdminTravelPartnerWebhook,
    updateAdminTravelPartnerConnection,
    updateAdminTravelRoutingPolicy,
    type AdminTravelConnectorTestResponse,
    type AdminTravelWebhookTestResponse,
    type AdminTravelPartner,
    type AdminTravelRoutingPolicy,
    type TravelPartnerCategory,
} from '../../lib/admin-travel-partner-service';
import { getAdminToken } from '../../lib/admin-session';

type RoadmapPhase = {
    phase: string;
    goal: string;
    status: 'ready' | 'in-progress' | 'pending';
    apis: string[];
};

const ROADMAP_PHASES: RoadmapPhase[] = [
    {
        phase: 'Phase 1',
        goal: '제휴 링크형 수익화 + 관리자 등록/라우팅',
        status: 'in-progress',
        apis: [
            'POST /api/admin/travel-partners',
            'GET /api/admin/travel-partners',
            'PUT /api/admin/travel-routing-policy',
            'POST /api/affiliate/click',
        ],
    },
    {
        phase: 'Phase 2',
        goal: '호텔/투어 예약 API 직접 연동',
        status: 'pending',
        apis: [
            'POST /api/admin/travel-connectors/{connectorId}/test',
            'GET /api/travel/search/hotels',
            'GET /api/travel/search/tours',
            'POST /api/travel/booking/initiate',
            'POST /api/travel/booking/webhook/{partner}',
        ],
    },
    {
        phase: 'Phase 3',
        goal: '이동 파트너 다중 라우팅 + fallback',
        status: 'pending',
        apis: [
            'GET /api/travel/search/transport',
            'POST /api/travel/transport/deeplink',
            'PUT /api/admin/travel-routing-city-policy',
            'GET /api/admin/travel-routing-health',
        ],
    },
    {
        phase: 'Phase 4',
        goal: '정산/수익 리포팅 자동화',
        status: 'pending',
        apis: [
            'GET /api/admin/revenue/ledger',
            'GET /api/admin/revenue/settlements',
            'GET /api/admin/revenue/by-partner',
            'POST /api/admin/revenue/reconcile',
        ],
    },
];

const STATUS_STYLE: Record<RoadmapPhase['status'], { label: string; color: string }> = {
    ready: { label: '준비됨', color: '#86efac' },
    'in-progress': { label: '진행중', color: '#7dd3fc' },
    pending: { label: '대기', color: '#fbbf24' },
};

export default function AdminTravelPartnerIntegrationPanel() {
    const [partners, setPartners] = useState<AdminTravelPartner[]>([]);
    const [routingPolicy, setRoutingPolicy] = useState<AdminTravelRoutingPolicy | null>(null);
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [partnerForm, setPartnerForm] = useState({
        partner_id: '',
        name: '',
        category: 'hotel' as TravelPartnerCategory,
        integration_type: 'affiliate',
        regions_supported: 'KR,JP',
        commission_model: '',
        base_url: '',
    });
    const [policyForm, setPolicyForm] = useState({
        version: 'v1',
        default_hotel_partner_id: '',
        default_tour_partner_id: '',
        default_transport_partner_id: '',
    });
    const [connectorForm, setConnectorForm] = useState({
        connector_id: '',
        test_url: '',
        timeout_ms: 3000,
    });
    const [connectionForm, setConnectionForm] = useState({
        partner_id: '',
        base_url: '',
        connector_test_url: '',
        booking_api_url: '',
        webhook_url: '',
    });
    const [webhookTestForm, setWebhookTestForm] = useState({
        event_type: 'admin_webhook_probe',
        sample_data_text: '{\n  "booking_ref": "sample-booking-001",\n  "status": "confirmed",\n  "amount": 120000,\n  "currency": "KRW"\n}',
    });
    const [connectorTestResult, setConnectorTestResult] = useState<AdminTravelConnectorTestResponse | null>(null);
    const [webhookTestResult, setWebhookTestResult] = useState<AdminTravelWebhookTestResponse | null>(null);

    const apiBaseUrl = useMemo(() => {
        const fromEnv = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE || '';
        if (fromEnv) {
            return fromEnv.replace(/\/$/, '');
        }
        if (typeof window !== 'undefined') {
            return window.location.origin;
        }
        return '';
    }, []);

    async function withAdminToken<T>(handler: (token: string) => Promise<T>) {
        const token = getAdminToken();
        if (!token) {
            throw new Error('관리자 토큰이 없습니다. 다시 로그인 후 시도하세요.');
        }
        return handler(token);
    }

    async function handleLoad() {
        setLoading(true);
        setError(null);
        setMessage(null);
        try {
            const data = await withAdminToken((token) =>
                loadAdminTravelPartners({ apiBaseUrl, token })
            );
            setPartners(data.partners || []);
            setRoutingPolicy(data.routing_policy || null);
            setConnectorForm((prev) => ({
                ...prev,
                connector_id: prev.connector_id || data.partners?.[0]?.partner_id || '',
            }));
            const selectedPartner = (data.partners || []).find((item) => item.partner_id === connectionForm.partner_id)
                || data.partners?.[0]
                || null;
            if (selectedPartner) {
                setConnectionForm({
                    partner_id: selectedPartner.partner_id,
                    base_url: String(selectedPartner.base_url || ''),
                    connector_test_url: String(selectedPartner.metadata?.connector_test_url || ''),
                    booking_api_url: String(selectedPartner.metadata?.booking_api_url || ''),
                    webhook_url: String(selectedPartner.metadata?.webhook_url || ''),
                });
            }
            setPolicyForm({
                version: data.routing_policy?.version || 'v1',
                default_hotel_partner_id: data.routing_policy?.default_hotel_partner_id || '',
                default_tour_partner_id: data.routing_policy?.default_tour_partner_id || '',
                default_transport_partner_id: data.routing_policy?.default_transport_partner_id || '',
            });
            setMessage('여행 파트너 설정을 불러왔습니다.');
        } catch (loadError: any) {
            if (String(loadError?.message || '').includes('__ADMIN_TRAVEL_PARTNER_UNAUTHORIZED__')) {
                setError('권한이 만료되었습니다. 관리자 로그인 후 다시 시도하세요.');
            } else {
                setError(String(loadError?.message || '여행 파트너 설정 조회 실패'));
            }
        } finally {
            setLoading(false);
        }
    }

    async function handleCreatePartner(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setSaving(true);
        setError(null);
        setMessage(null);
        try {
            const payload = {
                partner_id: partnerForm.partner_id.trim() || undefined,
                name: partnerForm.name.trim(),
                category: partnerForm.category,
                integration_type: partnerForm.integration_type.trim() || 'affiliate',
                regions_supported: partnerForm.regions_supported
                    .split(',')
                    .map((value) => value.trim())
                    .filter(Boolean),
                commission_model: partnerForm.commission_model.trim() || undefined,
                base_url: partnerForm.base_url.trim() || undefined,
            };
            const created = await withAdminToken((token) =>
                createAdminTravelPartner({ apiBaseUrl, token, payload })
            );
            setPartners(created.partners || []);
            setRoutingPolicy(created.routing_policy || null);
            setConnectorForm((prev) => ({
                ...prev,
                connector_id: prev.connector_id || created.partner.partner_id,
            }));
            setPartnerForm((prev) => ({ ...prev, partner_id: '', name: '', commission_model: '', base_url: '' }));
            setMessage(`파트너를 등록했습니다: ${created.partner.name}`);
        } catch (createError: any) {
            if (String(createError?.message || '').includes('__ADMIN_TRAVEL_PARTNER_UNAUTHORIZED__')) {
                setError('권한이 만료되었습니다. 관리자 로그인 후 다시 시도하세요.');
            } else {
                setError(String(createError?.message || '여행 파트너 등록 실패'));
            }
        } finally {
            setSaving(false);
        }
    }

    async function handleTestConnector(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setSaving(true);
        setError(null);
        setMessage(null);
        setConnectorTestResult(null);
        try {
            const connectorId = connectorForm.connector_id.trim();
            if (!connectorId) {
                throw new Error('테스트할 connector_id를 선택하세요.');
            }
            const result = await withAdminToken((token) =>
                testAdminTravelConnector({
                    apiBaseUrl,
                    token,
                    connectorId,
                    payload: {
                        test_url: connectorForm.test_url.trim() || undefined,
                        timeout_ms: Number(connectorForm.timeout_ms) || 3000,
                    },
                })
            );
            setConnectorTestResult(result);
            setMessage(
                result.reachable
                    ? `커넥터 연결 테스트 성공 (${result.status_code ?? 'n/a'}, ${result.response_time_ms}ms)`
                    : `커넥터 연결 실패 (${result.status_code ?? 'n/a'})`
            );
        } catch (testError: any) {
            if (String(testError?.message || '').includes('__ADMIN_TRAVEL_PARTNER_UNAUTHORIZED__')) {
                setError('권한이 만료되었습니다. 관리자 로그인 후 다시 시도하세요.');
            } else {
                setError(String(testError?.message || '여행 커넥터 연결 테스트 실패'));
            }
        } finally {
            setSaving(false);
        }
    }

    async function handleSaveConnectionUrls(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setSaving(true);
        setError(null);
        setMessage(null);
        try {
            const partnerId = connectionForm.partner_id.trim();
            if (!partnerId) {
                throw new Error('URL을 저장할 partner_id를 선택하세요.');
            }
            const saved = await withAdminToken((token) =>
                updateAdminTravelPartnerConnection({
                    apiBaseUrl,
                    token,
                    partnerId,
                    payload: {
                        base_url: connectionForm.base_url.trim(),
                        connector_test_url: connectionForm.connector_test_url.trim(),
                        booking_api_url: connectionForm.booking_api_url.trim(),
                        webhook_url: connectionForm.webhook_url.trim(),
                    },
                })
            );
            setPartners(saved.partners || []);
            setRoutingPolicy(saved.routing_policy || null);
            setMessage(`API URL 연동을 저장했습니다: ${partnerId}`);
        } catch (saveError: any) {
            if (String(saveError?.message || '').includes('__ADMIN_TRAVEL_PARTNER_UNAUTHORIZED__')) {
                setError('권한이 만료되었습니다. 관리자 로그인 후 다시 시도하세요.');
            } else {
                setError(String(saveError?.message || '여행 파트너 API URL 연동 저장 실패'));
            }
        } finally {
            setSaving(false);
        }
    }

    async function handleTestWebhook(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setSaving(true);
        setError(null);
        setMessage(null);
        setWebhookTestResult(null);
        try {
            const partnerId = connectionForm.partner_id.trim();
            if (!partnerId) {
                throw new Error('Webhook 테스트를 수행할 partner_id를 선택하세요.');
            }

            let sampleData: Record<string, unknown> | undefined;
            const sampleDataText = webhookTestForm.sample_data_text.trim();
            if (sampleDataText) {
                let parsedPayload: unknown = null;
                try {
                    parsedPayload = JSON.parse(sampleDataText);
                } catch {
                    throw new Error('샘플 데이터 JSON 형식이 올바르지 않습니다. JSON 문법을 확인하세요.');
                }
                if (!parsedPayload || typeof parsedPayload !== 'object' || Array.isArray(parsedPayload)) {
                    throw new Error('샘플 데이터는 JSON 객체 형식이어야 합니다.');
                }
                sampleData = parsedPayload as Record<string, unknown>;
            }

            const result = await withAdminToken((token) =>
                testAdminTravelPartnerWebhook({
                    apiBaseUrl,
                    token,
                    partnerId,
                    payload: {
                        webhook_url: connectionForm.webhook_url.trim() || undefined,
                        timeout_ms: 3000,
                        event_type: webhookTestForm.event_type.trim() || 'admin_webhook_probe',
                        sample_data: sampleData,
                    },
                })
            );
            setWebhookTestResult(result);
            setMessage(
                result.reachable
                    ? `Webhook 테스트 발송 성공 (${result.status_code ?? 'n/a'}, ${result.response_time_ms}ms)`
                    : `Webhook 테스트 발송 실패 (${result.status_code ?? 'n/a'})`
            );
        } catch (testError: any) {
            if (String(testError?.message || '').includes('__ADMIN_TRAVEL_PARTNER_UNAUTHORIZED__')) {
                setError('권한이 만료되었습니다. 관리자 로그인 후 다시 시도하세요.');
            } else {
                setError(String(testError?.message || '여행 Webhook 테스트 발송 실패'));
            }
        } finally {
            setSaving(false);
        }
    }

    async function handleSavePolicy(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setSaving(true);
        setError(null);
        setMessage(null);
        try {
            const saved = await withAdminToken((token) =>
                updateAdminTravelRoutingPolicy({
                    apiBaseUrl,
                    token,
                    payload: {
                        version: policyForm.version,
                        default_hotel_partner_id: policyForm.default_hotel_partner_id || null,
                        default_tour_partner_id: policyForm.default_tour_partner_id || null,
                        default_transport_partner_id: policyForm.default_transport_partner_id || null,
                        rules: routingPolicy?.rules || [],
                    },
                })
            );
            setRoutingPolicy(saved.routing_policy);
            setPartners(saved.partners || []);
            setMessage('라우팅 정책을 저장했습니다.');
        } catch (saveError: any) {
            if (String(saveError?.message || '').includes('__ADMIN_TRAVEL_PARTNER_UNAUTHORIZED__')) {
                setError('권한이 만료되었습니다. 관리자 로그인 후 다시 시도하세요.');
            } else {
                setError(String(saveError?.message || '여행 라우팅 정책 저장 실패'));
            }
        } finally {
            setSaving(false);
        }
    }

    return (
        <div className="workspace-section-stack" data-testid="admin-travel-partner-integration-panel">
            <div className="workspace-sidebar-card">
                <p className="workspace-card-kicker">Travel Partner Integration Hub</p>
                <p style={{ margin: '4px 0 0', fontSize: 13, color: 'rgba(255,255,255,0.74)' }}>
                    관리자 대시보드에서 호텔/이동/투어 파트너를 연결하고, 국가/도시 라우팅과 수익 퍼널을 운영하기 위한 착수 패널입니다.
                </p>
            </div>

            <div className="workspace-sidebar-card">
                <p className="workspace-card-kicker">카테고리 우선순위</p>
                <ul style={{ margin: '8px 0 0', paddingLeft: 18, color: 'rgba(255,255,255,0.82)', fontSize: 13 }}>
                    <li>1순위: 호텔 (고단가 예약, 수익 기여도 최대)</li>
                    <li>2순위: 투어/액티비티 (대화형 추천과 적합)</li>
                    <li>3순위: 이동 (지역별 파트너 fallback 중심)</li>
                </ul>
            </div>

            <div className="workspace-sidebar-card">
                <p className="workspace-card-kicker">API 연동 로드맵</p>
                <div style={{ display: 'grid', gap: 10, marginTop: 8 }}>
                    {ROADMAP_PHASES.map((item) => {
                        const status = STATUS_STYLE[item.status];
                        return (
                            <article key={item.phase} style={{ border: '1px solid rgba(148,163,184,0.35)', borderRadius: 10, padding: 12 }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center' }}>
                                    <strong style={{ color: '#e2e8f0', fontSize: 14 }}>{item.phase}</strong>
                                    <span style={{ color: status.color, fontSize: 12, fontWeight: 700 }}>{status.label}</span>
                                </div>
                                <p style={{ margin: '6px 0 8px', color: 'rgba(255,255,255,0.7)', fontSize: 12 }}>{item.goal}</p>
                                <ul style={{ margin: 0, paddingLeft: 18, color: 'rgba(255,255,255,0.85)', fontSize: 12 }}>
                                    {item.apis.map((api) => (
                                        <li key={api}><code>{api}</code></li>
                                    ))}
                                </ul>
                            </article>
                        );
                    })}
                </div>
            </div>

            <div className="workspace-sidebar-card">
                <p className="workspace-card-kicker">착수 결과</p>
                <ul style={{ margin: '8px 0 0', paddingLeft: 18, color: 'rgba(255,255,255,0.82)', fontSize: 13 }}>
                    <li>체크리스트 문서 작성 완료</li>
                    <li>마스터 기술서 작성 완료</li>
                    <li>관리자 대시보드 연동 허브 스켈레톤 패널 반영 완료</li>
                </ul>
            </div>

            <div className="workspace-sidebar-card">
                <p className="workspace-card-kicker">Phase 1 API 운영</p>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
                    <button
                        type="button"
                        className="workspace-btn-secondary"
                        onClick={() => {
                            void handleLoad();
                        }}
                        disabled={loading || saving}
                        data-testid="travel-partner-load-btn"
                    >
                        {loading ? '불러오는 중...' : '설정 불러오기'}
                    </button>
                </div>
                {message ? <p style={{ marginTop: 8, color: '#86efac', fontSize: 12 }}>{message}</p> : null}
                {error ? <p style={{ marginTop: 8, color: '#fca5a5', fontSize: 12 }}>{error}</p> : null}
            </div>

            <div className="workspace-sidebar-card">
                <p className="workspace-card-kicker">파트너 등록 (POST /api/admin/travel-partners)</p>
                <form onSubmit={handleCreatePartner} style={{ display: 'grid', gap: 8, marginTop: 8 }} data-testid="travel-partner-create-form">
                    <input
                        value={partnerForm.partner_id}
                        onChange={(event) => setPartnerForm((prev) => ({ ...prev, partner_id: event.target.value }))}
                        placeholder="partner_id (선택)"
                    />
                    <input
                        value={partnerForm.name}
                        onChange={(event) => setPartnerForm((prev) => ({ ...prev, name: event.target.value }))}
                        placeholder="파트너 이름"
                        required
                    />
                    <select
                        value={partnerForm.category}
                        onChange={(event) => setPartnerForm((prev) => ({ ...prev, category: event.target.value as TravelPartnerCategory }))}
                    >
                        <option value="hotel">hotel</option>
                        <option value="tour">tour</option>
                        <option value="transport">transport</option>
                    </select>
                    <input
                        value={partnerForm.regions_supported}
                        onChange={(event) => setPartnerForm((prev) => ({ ...prev, regions_supported: event.target.value }))}
                        placeholder="지원 지역 (예: KR,JP,SG)"
                    />
                    <input
                        value={partnerForm.commission_model}
                        onChange={(event) => setPartnerForm((prev) => ({ ...prev, commission_model: event.target.value }))}
                        placeholder="커미션 모델"
                    />
                    <input
                        value={partnerForm.base_url}
                        onChange={(event) => setPartnerForm((prev) => ({ ...prev, base_url: event.target.value }))}
                        placeholder="Base URL"
                    />
                    <button type="submit" className="workspace-btn-primary" disabled={saving || loading} data-testid="travel-partner-create-btn">
                        {saving ? '저장 중...' : '파트너 등록'}
                    </button>
                </form>
            </div>

            <div className="workspace-sidebar-card">
                <p className="workspace-card-kicker">라우팅 정책 저장 (PUT /api/admin/travel-routing-policy)</p>
                <form onSubmit={handleSavePolicy} style={{ display: 'grid', gap: 8, marginTop: 8 }} data-testid="travel-routing-policy-form">
                    <input
                        value={policyForm.version}
                        onChange={(event) => setPolicyForm((prev) => ({ ...prev, version: event.target.value }))}
                        placeholder="버전"
                    />
                    <input
                        value={policyForm.default_hotel_partner_id}
                        onChange={(event) => setPolicyForm((prev) => ({ ...prev, default_hotel_partner_id: event.target.value }))}
                        placeholder="기본 호텔 파트너 ID"
                    />
                    <input
                        value={policyForm.default_tour_partner_id}
                        onChange={(event) => setPolicyForm((prev) => ({ ...prev, default_tour_partner_id: event.target.value }))}
                        placeholder="기본 투어 파트너 ID"
                    />
                    <input
                        value={policyForm.default_transport_partner_id}
                        onChange={(event) => setPolicyForm((prev) => ({ ...prev, default_transport_partner_id: event.target.value }))}
                        placeholder="기본 이동 파트너 ID"
                    />
                    <button type="submit" className="workspace-btn-primary" disabled={saving || loading} data-testid="travel-routing-policy-save-btn">
                        {saving ? '저장 중...' : '라우팅 정책 저장'}
                    </button>
                </form>
            </div>

            <div className="workspace-sidebar-card">
                <p className="workspace-card-kicker">커넥터 연결 테스트 (POST /api/admin/travel-connectors/{'{connectorId}'}/test)</p>
                <form onSubmit={handleTestConnector} style={{ display: 'grid', gap: 8, marginTop: 8 }} data-testid="travel-connector-test-form">
                    <select
                        value={connectorForm.connector_id}
                        onChange={(event) => setConnectorForm((prev) => ({ ...prev, connector_id: event.target.value }))}
                        required
                    >
                        <option value="">connector 선택</option>
                        {partners.map((item) => (
                            <option key={item.partner_id} value={item.partner_id}>
                                {item.partner_id} ({item.name})
                            </option>
                        ))}
                    </select>
                    <input
                        value={connectorForm.test_url}
                        onChange={(event) => setConnectorForm((prev) => ({ ...prev, test_url: event.target.value }))}
                        placeholder="테스트 URL (선택, 비우면 base_url 사용)"
                    />
                    <input
                        type="number"
                        min={500}
                        max={15000}
                        value={connectorForm.timeout_ms}
                        onChange={(event) => setConnectorForm((prev) => ({ ...prev, timeout_ms: Number(event.target.value) || 3000 }))}
                        placeholder="Timeout(ms)"
                    />
                    <button type="submit" className="workspace-btn-primary" disabled={saving || loading} data-testid="travel-connector-test-btn">
                        {saving ? '테스트 중...' : '연결 테스트 실행'}
                    </button>
                </form>
                {connectorTestResult ? (
                    <p style={{ marginTop: 8, color: connectorTestResult.reachable ? '#86efac' : '#fca5a5', fontSize: 12 }} data-testid="travel-connector-test-result">
                        {connectorTestResult.reachable ? 'reachable' : 'unreachable'} / status: {String(connectorTestResult.status_code ?? 'n/a')} / {connectorTestResult.response_time_ms}ms
                        {connectorTestResult.error ? ` / error: ${connectorTestResult.error}` : ''}
                    </p>
                ) : null}
            </div>

            <div className="workspace-sidebar-card">
                <p className="workspace-card-kicker">API URL 연동 (PUT /api/admin/travel-partners/{'{partnerId}'}/connection)</p>
                <form onSubmit={handleSaveConnectionUrls} style={{ display: 'grid', gap: 8, marginTop: 8 }} data-testid="travel-partner-connection-form">
                    <select
                        value={connectionForm.partner_id}
                        onChange={(event) => {
                            const partnerId = event.target.value;
                            const selected = partners.find((item) => item.partner_id === partnerId);
                            setConnectionForm({
                                partner_id: partnerId,
                                base_url: String(selected?.base_url || ''),
                                connector_test_url: String(selected?.metadata?.connector_test_url || ''),
                                booking_api_url: String(selected?.metadata?.booking_api_url || ''),
                                webhook_url: String(selected?.metadata?.webhook_url || ''),
                            });
                        }}
                        required
                    >
                        <option value="">URL 연동 대상 partner 선택</option>
                        {partners.map((item) => (
                            <option key={item.partner_id} value={item.partner_id}>
                                {item.partner_id} ({item.name})
                            </option>
                        ))}
                    </select>
                    <input
                        value={connectionForm.base_url}
                        onChange={(event) => setConnectionForm((prev) => ({ ...prev, base_url: event.target.value }))}
                        placeholder="기본 Base URL (https://...)"
                    />
                    <input
                        value={connectionForm.connector_test_url}
                        onChange={(event) => setConnectionForm((prev) => ({ ...prev, connector_test_url: event.target.value }))}
                        placeholder="커넥터 테스트 URL (metadata.connector_test_url)"
                    />
                    <input
                        value={connectionForm.booking_api_url}
                        onChange={(event) => setConnectionForm((prev) => ({ ...prev, booking_api_url: event.target.value }))}
                        placeholder="예약 API URL (metadata.booking_api_url)"
                    />
                    <input
                        value={connectionForm.webhook_url}
                        onChange={(event) => setConnectionForm((prev) => ({ ...prev, webhook_url: event.target.value }))}
                        placeholder="Webhook URL (metadata.webhook_url)"
                    />
                    <button type="submit" className="workspace-btn-primary" disabled={saving || loading} data-testid="travel-partner-connection-save-btn">
                        {saving ? '저장 중...' : '1) API URL 저장'}
                    </button>
                </form>
                <p style={{ marginTop: 8, marginBottom: 0, color: 'rgba(255,255,255,0.66)', fontSize: 11 }}>
                    저장 후 바로 아래 Webhook 테스트를 실행해 연결 상태를 즉시 확인하세요.
                </p>
                <form onSubmit={handleTestWebhook} style={{ display: 'grid', gap: 8, marginTop: 10 }} data-testid="travel-partner-webhook-test-form">
                    <input
                        value={webhookTestForm.event_type}
                        onChange={(event) => setWebhookTestForm((prev) => ({ ...prev, event_type: event.target.value }))}
                        placeholder="Webhook 이벤트 타입 (예: booking_confirmed)"
                    />
                    <textarea
                        value={webhookTestForm.sample_data_text}
                        onChange={(event) => setWebhookTestForm((prev) => ({ ...prev, sample_data_text: event.target.value }))}
                        placeholder="Webhook 샘플 데이터(JSON 객체)"
                        rows={7}
                        style={{ width: '100%' }}
                    />
                    <button type="submit" className="workspace-btn-secondary" disabled={saving || loading} data-testid="travel-partner-webhook-test-btn">
                        {saving ? '테스트 발송 중...' : '2) Webhook 테스트 발송'}
                    </button>
                </form>
                {webhookTestResult ? (
                    <div
                        style={{
                            marginTop: 8,
                            border: `1px solid ${webhookTestResult.reachable ? 'rgba(134,239,172,0.5)' : 'rgba(252,165,165,0.5)'}`,
                            borderRadius: 8,
                            padding: '8px 10px',
                            background: webhookTestResult.reachable ? 'rgba(20,83,45,0.24)' : 'rgba(127,29,29,0.2)',
                            color: webhookTestResult.reachable ? '#86efac' : '#fecaca',
                            fontSize: 12,
                        }}
                        data-testid="travel-partner-webhook-test-result"
                    >
                        <strong>3) 결과 확인:</strong> {webhookTestResult.reachable ? 'reachable' : 'unreachable'} / status: {String(webhookTestResult.status_code ?? 'n/a')} / {webhookTestResult.response_time_ms}ms
                        {webhookTestResult.error ? ` / error: ${webhookTestResult.error}` : ''}
                    </div>
                ) : null}
            </div>

            <div className="workspace-sidebar-card">
                <p className="workspace-card-kicker">등록된 파트너</p>
                {partners.length === 0 ? (
                    <p style={{ margin: '8px 0 0', color: 'rgba(255,255,255,0.7)', fontSize: 12 }}>파트너가 없습니다. 먼저 등록하세요.</p>
                ) : (
                    <ul style={{ margin: '8px 0 0', paddingLeft: 18, color: 'rgba(255,255,255,0.88)', fontSize: 12 }} data-testid="travel-partner-list">
                        {partners.map((item) => (
                            <li key={item.partner_id}>
                                <strong>{item.partner_id}</strong> - {item.name} ({item.category})
                                {item.base_url ? <span> / base: {item.base_url}</span> : null}
                                {item.metadata?.connector_test_url ? <span> / test: {String(item.metadata.connector_test_url)}</span> : null}
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    );
}
