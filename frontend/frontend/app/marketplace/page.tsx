'use client';

import * as React from 'react';
import Link from 'next/link';
import FeatureLauncherGrid from '@/components/marketplace/feature-launcher-grid';
import FeatureOrchestratorPopup from '@/components/marketplace/feature-orchestrator-popup';
import { buildMarketplaceWorkspaceRailItems } from '@/components/marketplace/marketplace-rails';
import { resolveApiBaseUrl } from '@/lib/api';
import { useFeatureOrchestrator } from '@/hooks/use-feature-orchestrator';
import WorkspaceChrome from '@/components/ui/workspace-chrome';

const CUSTOMER_TOKEN_KEY = 'customer_token';

type CategoryItem = {
    id: number;
    name: string;
    description?: string | null;
};

type ProjectTag = {
    id: number;
    name: string;
};

type ProjectSubscriptionInfo = {
    product_code: string;
    product_name: string;
    product_description?: string | null;
    plan_code?: string | null;
    plan_name?: string | null;
    currency?: string | null;
    amount_minor?: number | null;
    provider?: string | null;
};

type ProjectItem = {
    id: number;
    title: string;
    description?: string | null;
    price: number;
    category_id: number;
    downloads: number;
    rating: number;
    demo_url?: string | null;
    github_url?: string | null;
    image_url?: string | null;
    is_active: boolean;
    category?: CategoryItem | null;
    tags?: ProjectTag[];
    subscription?: ProjectSubscriptionInfo | null;
};

type ProjectListResponse = {
    projects: ProjectItem[];
    total: number;
    skip: number;
    limit: number;
};

type OverviewStats = {
    projects: number;
    users: number;
    purchases: number;
    reviews: number;
};

type RevenueStats = {
    total_revenue: number;
    total_purchases: number;
    average_purchase_amount: number;
};

type TopProject = {
    id: number;
    title: string;
    downloads: number;
    rating: number;
    price: number;
};

type CustomerMe = {
    email: string;
    username: string;
    full_name?: string | null;
    member_type?: string;
    business_name?: string | null;
    business_registration_number?: string | null;
    representative_name?: string | null;
};

type CustomerMemberType = 'individual' | 'sole_proprietor' | 'corporation';

const MEMBER_TYPE_LABELS: Record<CustomerMemberType, string> = {
    individual: '개인',
    sole_proprietor: '개인사업자',
    corporation: '법인사업자',
};

function formatCurrency(value: number) {
    return new Intl.NumberFormat('ko-KR', { style: 'currency', currency: 'KRW', maximumFractionDigits: 0 }).format(Number(value || 0));
}

export default function MarketplacePage() {
    const featureOrchestrator = useFeatureOrchestrator();
    const apiBaseUrl = React.useMemo(() => resolveApiBaseUrl(), []);
    const [categories, setCategories] = React.useState<CategoryItem[]>([]);
    const [projects, setProjects] = React.useState<ProjectItem[]>([]);
    const [shinsegyeProducts, setShinsegyeProducts] = React.useState<ProjectItem[]>([]);
    const [topProjects, setTopProjects] = React.useState<TopProject[]>([]);
    const [overview, setOverview] = React.useState<OverviewStats | null>(null);
    const [revenue, setRevenue] = React.useState<RevenueStats | null>(null);
    const [selectedCategoryId, setSelectedCategoryId] = React.useState(0);
    const [search, setSearch] = React.useState('');
    const [sortBy, setSortBy] = React.useState<'created_at' | 'downloads' | 'rating' | 'price'>('downloads');
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState('');
    const [token, setToken] = React.useState('');
    const [me, setMe] = React.useState<CustomerMe | null>(null);
    const [authMode, setAuthMode] = React.useState<'login' | 'signup'>('login');
    const [email, setEmail] = React.useState('');
    const [username, setUsername] = React.useState('');
    const [fullName, setFullName] = React.useState('');
    const [memberType, setMemberType] = React.useState<CustomerMemberType>('individual');
    const [businessName, setBusinessName] = React.useState('');
    const [businessRegistrationNumber, setBusinessRegistrationNumber] = React.useState('');
    const [representativeName, setRepresentativeName] = React.useState('');
    const [password, setPassword] = React.useState('');
    const [authLoading, setAuthLoading] = React.useState(false);
    const [authMessage, setAuthMessage] = React.useState('');

    const loadMyInfo = React.useCallback(async (targetToken: string) => {
        const response = await fetch(`${apiBaseUrl}/api/auth/me`, {
            headers: { Authorization: `Bearer ${targetToken}` },
            cache: 'no-store',
        });
        if (!response.ok) {
            throw new Error('내 정보를 불러오지 못했습니다.');
        }
        const payload = await response.json();
        setMe(payload);
    }, [apiBaseUrl]);

    const loadMarketplace = React.useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const projectParams = new URLSearchParams({
                skip: '0',
                limit: '24',
                sort_by: sortBy,
                sort_order: 'desc',
            });
            if (selectedCategoryId > 0) {
                projectParams.set('category_id', String(selectedCategoryId));
            }
            if (search.trim()) {
                projectParams.set('search', search.trim());
            }

            const [categoriesResponse, projectsResponse, shinsegyeResponse, overviewResponse, revenueResponse, topProjectsResponse] = await Promise.allSettled([
                fetch(`${apiBaseUrl}/api/marketplace/categories`, { cache: 'no-store' }),
                fetch(`${apiBaseUrl}/api/marketplace/projects?${projectParams.toString()}`, { cache: 'no-store' }),
                fetch(`${apiBaseUrl}/api/marketplace/shinsegye/products`, { cache: 'no-store', headers: token ? { Authorization: `Bearer ${token}` } : {} }),
                fetch(`${apiBaseUrl}/api/marketplace/stats/overview`, { cache: 'no-store' }),
                fetch(`${apiBaseUrl}/api/marketplace/stats/revenue`, { cache: 'no-store' }),
                fetch(`${apiBaseUrl}/api/marketplace/stats/top-projects?limit=6`, { cache: 'no-store' }),
            ]);

            const readPayload = async <T,>(result: PromiseSettledResult<Response>, fallback: T): Promise<T> => {
                if (result.status !== 'fulfilled' || !result.value.ok) {
                    return fallback;
                }
                return result.value.json().catch(() => fallback);
            };

            if (projectsResponse.status !== 'fulfilled' || !projectsResponse.value.ok) {
                throw new Error('마켓플레이스 데이터를 불러오지 못했습니다.');
            }

            const categoriesPayload = await readPayload(categoriesResponse, [] as CategoryItem[]);
            const projectsPayload = await projectsResponse.value.json().catch(() => ({ projects: [], total: 0, skip: 0, limit: 24 }));
            const shinsegyePayload = await readPayload(shinsegyeResponse, { products: [] } as any);
            const overviewPayload = await readPayload(overviewResponse, null as OverviewStats | null);
            const revenuePayload = await readPayload(revenueResponse, null as RevenueStats | null);
            const topProjectsPayload = await readPayload(topProjectsResponse, [] as TopProject[]);

            // shinsegyeProducts를 ProjectItem 형식으로 변환
            const shinsegyeList = Array.isArray((shinsegyePayload as any)?.products)
                ? (shinsegyePayload as any).products.map((p: any) => ({
                    id: p.key ? -Math.abs(p.key.hashCode?.() ?? 0) : 0, // shinsegye는 음수 ID
                    title: p.title || '',
                    description: p.description || '',
                    price: p.price || 0,
                    category_id: p.category_id || 0,
                    downloads: 0,
                    rating: 5,
                    demo_url: `/marketplace/shinsegye/${p.key}`,
                    github_url: p.github_url || null,
                    image_url: p.image_url || null,
                    is_active: true,
                    tags: (p.tags || []).map((name: string) => ({ id: 0, name })),
                  }))
                : [];

            setCategories(Array.isArray(categoriesPayload) ? categoriesPayload : []);
            setProjects(Array.isArray((projectsPayload as ProjectListResponse)?.projects) ? (projectsPayload as ProjectListResponse).projects : []);
            setShinsegyeProducts(shinsegyeList);
            setOverview(overviewPayload);
            setRevenue(revenuePayload);
            setTopProjects(Array.isArray(topProjectsPayload) ? topProjectsPayload : []);
        } catch (loadError: any) {
            setError(loadError?.message || '마켓플레이스 데이터를 불러오지 못했습니다.');
        } finally {
            setLoading(false);
        }
    }, [apiBaseUrl, search, selectedCategoryId, sortBy, token]);

    React.useEffect(() => {
        void loadMarketplace();
    }, [loadMarketplace]);

    React.useEffect(() => {
        if (typeof window === 'undefined') {
            return;
        }
        const savedToken = localStorage.getItem(CUSTOMER_TOKEN_KEY) || '';
        if (!savedToken) {
            return;
        }
        setToken(savedToken);
        loadMyInfo(savedToken).catch(() => {
            localStorage.removeItem(CUSTOMER_TOKEN_KEY);
            setToken('');
            setMe(null);
        });
    }, [loadMyInfo]);

    const handleAuth = React.useCallback(async () => {
        setAuthLoading(true);
        setAuthMessage('');
        try {
            if (authMode === 'signup') {
                const signupResponse = await fetch(`${apiBaseUrl}/api/auth/signup`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        username: username.trim(),
                        email: email.trim(),
                        password,
                        full_name: fullName.trim(),
                        member_type: memberType,
                        business_name: memberType === 'individual' ? null : businessName.trim(),
                        business_registration_number: memberType === 'individual' ? null : businessRegistrationNumber.trim(),
                        representative_name: memberType === 'corporation' ? representativeName.trim() : null,
                    }),
                });
                const signupPayload = await signupResponse.json().catch(() => null);
                if (!signupResponse.ok) {
                    throw new Error(signupPayload?.detail || '회원가입에 실패했습니다.');
                }
            }

            const formData = new URLSearchParams();
            formData.set('username', email.trim());
            formData.set('password', password);

            const loginResponse = await fetch(`${apiBaseUrl}/api/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: formData.toString(),
            });
            const loginPayload = await loginResponse.json().catch(() => null);
            if (!loginResponse.ok || !loginPayload?.access_token) {
                throw new Error(loginPayload?.detail || '로그인에 실패했습니다.');
            }
            if (typeof window !== 'undefined') {
                localStorage.setItem(CUSTOMER_TOKEN_KEY, loginPayload.access_token);
            }
            setToken(loginPayload.access_token);
            await loadMyInfo(loginPayload.access_token);
            setAuthMessage(authMode === 'signup' ? '회원가입과 로그인이 완료되었습니다.' : '로그인되었습니다.');
        } catch (authError: any) {
            setAuthMessage(authError?.message || '인증 처리 중 오류가 발생했습니다.');
        } finally {
            setAuthLoading(false);
        }
    }, [apiBaseUrl, authMode, businessName, businessRegistrationNumber, email, fullName, loadMyInfo, memberType, password, representativeName, username]);

    const handleLogout = React.useCallback(() => {
        if (typeof window !== 'undefined') {
            localStorage.removeItem(CUSTOMER_TOKEN_KEY);
        }
        setToken('');
        setMe(null);
        setAuthMessage('로그아웃되었습니다.');
    }, []);

    const marketplaceSummaryCards = [
        { id: 'projects', label: '진열 가능 상품', value: String(overview?.projects ?? 0), note: '실제 등록 프로젝트 기준' },
        { id: 'purchases', label: '완료 구매', value: String(overview?.purchases ?? 0), note: '결제 완료/반영 건수' },
        { id: 'revenue', label: '평균 구매 금액', value: formatCurrency(revenue?.average_purchase_amount ?? 0), note: `총 매출 ${formatCurrency(revenue?.total_revenue ?? 0)}` },
        { id: 'reviews', label: '리뷰 수', value: String(overview?.reviews ?? 0), note: '공개 상세 리뷰 기준' },
    ];

    const marketplaceSidebar = (
        <div className="workspace-section-stack">
            <div className="workspace-sidebar-card" data-testid="marketplace-auth-panel">
                <p className="workspace-card-kicker">Account</p>
                <h3 className="workspace-card-title">회원가입 / 내정보</h3>
                {!me ? (
                    <form className="workspace-form-stack mt-4" onSubmit={(event) => { event.preventDefault(); void handleAuth(); }}>
                        <div className="workspace-auth-switch text-sm">
                            <button type="button" onClick={() => setAuthMode('login')} className={authMode === 'login' ? 'active' : ''}>로그인</button>
                            <button type="button" onClick={() => setAuthMode('signup')} className={authMode === 'signup' ? 'active' : ''}>회원가입</button>
                        </div>
                        <input id="marketplace-email" name="email" autoComplete={authMode === 'signup' ? 'email' : 'username'} value={email} onChange={(event) => setEmail(event.target.value)} placeholder="이메일" className="workspace-input" />
                        {authMode === 'signup' && (
                            <>
                                <input id="marketplace-username" name="username" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} placeholder="사용자명" className="workspace-input" />
                                <input id="marketplace-fullname" name="fullName" autoComplete="name" value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="이름 / 담당자명" className="workspace-input" />
                                <select id="marketplace-membertype" name="memberType" value={memberType} onChange={(event) => setMemberType(event.target.value as CustomerMemberType)} className="workspace-select" aria-label="회원 유형" title="회원 유형">
                                    <option value="individual">개인</option>
                                    <option value="sole_proprietor">개인사업자</option>
                                    <option value="corporation">법인사업자</option>
                                </select>
                                {memberType !== 'individual' && (
                                    <>
                                        <input id="marketplace-businessname" name="businessName" autoComplete="organization" value={businessName} onChange={(event) => setBusinessName(event.target.value)} placeholder={memberType === 'corporation' ? '법인명' : '상호명'} className="workspace-input" />
                                        <input id="marketplace-businessreg" name="businessRegistrationNumber" autoComplete="off" value={businessRegistrationNumber} onChange={(event) => setBusinessRegistrationNumber(event.target.value)} placeholder="사업자등록번호" className="workspace-input" />
                                    </>
                                )}
                                {memberType === 'corporation' && (
                                    <input id="marketplace-repname" name="representativeName" autoComplete="name" value={representativeName} onChange={(event) => setRepresentativeName(event.target.value)} placeholder="대표자명" className="workspace-input" />
                                )}
                            </>
                        )}
                        <input type="password" autoComplete={authMode === 'signup' ? 'new-password' : 'current-password'} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="비밀번호" className="workspace-input" />
                        <button type="submit" disabled={authLoading} className="workspace-primary-button w-full justify-center text-center">
                            {authLoading ? '처리 중...' : authMode === 'signup' ? '회원가입 후 시작' : '로그인 후 시작'}
                        </button>
                        {authMessage ? <p className="workspace-card-copy">{authMessage}</p> : null}
                    </form>
                ) : (
                    <div className="workspace-list mt-4 text-sm">
                        <div className="workspace-list-item"><strong>이메일</strong><span>{me.email}</span></div>
                        <div className="workspace-list-item"><strong>사용자명</strong><span>{me.username}</span></div>
                        <div className="workspace-list-item"><strong>가입 유형</strong><span>{MEMBER_TYPE_LABELS[(me.member_type as CustomerMemberType) || 'individual']}</span></div>
                        {me.business_name ? <div className="workspace-list-item"><strong>사업자명/법인명</strong><span>{me.business_name}</span></div> : null}
                    </div>
                )}
            </div>

            <div className="workspace-sidebar-card" data-testid="marketplace-top-projects">
                <p className="workspace-card-kicker">Top Projects</p>
                <h3 className="workspace-card-title">다운로드 상위 프로젝트</h3>
                <div className="workspace-list mt-4">
                    {topProjects.slice(0, 6).map((project) => (
                        <div key={`top-${project.id}`} className="workspace-list-item">
                            <div>
                                <strong>{project.title}</strong>
                                <span>다운로드 {project.downloads} · 평점 {Number(project.rating || 0).toFixed(1)}</span>
                            </div>
                            <strong>{formatCurrency(project.price)}</strong>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );

    const marketplaceRails = buildMarketplaceWorkspaceRailItems('market-home');

    return (
        <>
            <WorkspaceChrome
                brand="Marketplace Workspace"
                title="고객 거래 워크스페이스"
                description="좌측/우측 레일을 통해 기능을 분류하고 탭 형태로 제공하는 UI입니다."
                statusLabel={loading ? '데이터 동기화 중' : '운영 API 연결 완료'}
                pageTestId="marketplace-main-page"
                compactHeader
                hideHero
                railItems={marketplaceRails.railItems}
                rightRailItems={marketplaceRails.rightRailItems}
                topActions={
                    <>
                        <Link href="/marketplace/orchestrator" className="workspace-topbar-chip">고객용 오케스트레이터</Link>
                    </>
                }
                sidebar={marketplaceSidebar}
            >
                <div className="workspace-section-stack">
                    <div className="workspace-metric-grid" data-testid="marketplace-stats-cards">
                        {marketplaceSummaryCards.map((card) => (
                            <div key={card.id} className="workspace-metric-card">
                                <p className="workspace-metric-label">{card.label}</p>
                                <p className="workspace-metric-value">{card.value}</p>
                                <p className="workspace-metric-note">{card.note}</p>
                            </div>
                        ))}
                    </div>

                    <section id="office-tools-hub" className="workspace-card" data-testid="marketplace-feature-launcher">
                        <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
                            <div>
                                <p className="workspace-card-kicker">실행형 Feature Orchestrator</p>
                                <h2 className="workspace-card-heading">3개 AI 서비스 통합 진열</h2>
                                <p className="workspace-card-copy">preview → final → 다운로드 흐름을 한곳에서 실행하고 바로 검증할 수 있습니다.</p>
                            </div>
                        </div>
                        <FeatureLauncherGrid
                            catalog={featureOrchestrator.catalog}
                            catalogLoading={featureOrchestrator.catalogLoading}
                            catalogError={featureOrchestrator.catalogError}
                            activeFeatureId={featureOrchestrator.activeFeatureId}
                            onLaunch={featureOrchestrator.openFeature}
                        />
                    </section>

                    {shinsegyeProducts.length > 0 && (
                        <section className="workspace-card">
                            <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
                                <div>
                                    <p className="workspace-card-kicker">신세계 소리새 완제품</p>
                                    <h2 className="workspace-card-heading">7개 통합 패키지</h2>
                                    <p className="workspace-card-copy">통번역, 미디어 스튜디오, 보안/탐정, 게임, 스마트홈, 비즈니스, 개발도구 완제품 번들입니다.</p>
                                </div>
                            </div>
                            {shinsegyeProducts.length > 0 && (
                                <div className="marketplace-projects-grid" data-testid="shinsegye-products">
                                    {shinsegyeProducts.map((project) => (
                                        <article key={`shinsegye-${project.id}`} className="workspace-card">
                                            <p className="workspace-card-kicker" style={{color: '#f0b43f', fontWeight: 700}}>완제품</p>
                                            <h3 className="workspace-card-heading">{project.title}</h3>
                                            <p className="workspace-card-body">{project.description || '설명이 아직 등록되지 않았습니다.'}</p>
                                            {!!project.tags?.length && (
                                                <div className="workspace-chip-row">
                                                    {project.tags.slice(0, 5).map((tag) => (
                                                        <span key={`${project.id}-${tag.id}-${tag.name}`} className="workspace-chip">#{tag.name}</span>
                                                    ))}
                                                </div>
                                            )}
                                            <div className="workspace-project-stats">
                                                <div className="workspace-project-stat">
                                                    <p className="workspace-project-stat-label">가격</p>
                                                    <p className="workspace-project-stat-value text-[#f0b43f]">{formatCurrency(project.price)}</p>
                                                </div>
                                            </div>
                                            <div className="mt-5 flex flex-wrap items-center justify-between gap-2">
                                                <div className="flex flex-wrap gap-2">
                                                    <Link href={`/marketplace/shinsegye/${project.demo_url}`} className="workspace-secondary-button">상세 보기</Link>
                                                    <Link href={`/marketplace/orchestrator?product=${encodeURIComponent(project.title)}&projectId=${project.id}&projectTitle=${encodeURIComponent(project.title)}&projectSummary=${encodeURIComponent(project.description || '')}`} className="workspace-primary-button">패키지 주문</Link>
                                                </div>
                                            </div>
                                        </article>
                                    ))}
                                </div>
                            )}
                        </section>
                    )}

                    <section className="workspace-card">
                        <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
                            <div>
                                <p className="workspace-card-kicker">운영형 프로젝트 목록</p>
                                <h2 className="workspace-card-heading">실제 등록 프로젝트</h2>
                                <p className="workspace-card-copy">DB 프로젝트 기준으로 정렬/검색/카테고리 필터 결과를 바로 보여줍니다. 마켓플레이스 도메인에서는 관리자 화면 링크를 노출하지 않습니다.</p>
                            </div>
                        </div>

                        <div className="grid gap-4 lg:grid-cols-[1fr_220px_220px]" data-testid="marketplace-filters">
                            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="프로젝트 제목/설명 검색" className="workspace-input" />
                            <select value={String(selectedCategoryId)} onChange={(event) => setSelectedCategoryId(Number(event.target.value))} className="workspace-select" aria-label="카테고리 필터" title="카테고리 필터">
                                <option value="0">전체 카테고리</option>
                                {categories.map((category) => (
                                    <option key={category.id} value={category.id}>{category.name}</option>
                                ))}
                            </select>
                            <select value={sortBy} onChange={(event) => setSortBy(event.target.value as typeof sortBy)} className="workspace-select" aria-label="정렬 기준" title="정렬 기준">
                                <option value="downloads">다운로드순</option>
                                <option value="rating">평점순</option>
                                <option value="price">가격순</option>
                                <option value="created_at">최신순</option>
                            </select>
                        </div>
                        <div className="workspace-chip-row mt-4">
                            <span className="workspace-chip workspace-chip-active">상품 {projects.length}개 노출</span>
                            {categories.map((category) => (
                                <button key={category.id} type="button" onClick={() => setSelectedCategoryId(category.id)} className={`workspace-chip ${selectedCategoryId === category.id ? 'workspace-chip-active' : ''}`}>
                                    {category.name}
                                </button>
                            ))}
                            {selectedCategoryId !== 0 && (
                                <button type="button" onClick={() => setSelectedCategoryId(0)} className="workspace-chip">필터 초기화</button>
                            )}
                        </div>

                        {error && <div className="mb-4 rounded-2xl border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div>}
                        {loading ? (
                            <div className="workspace-card-copy px-5 py-8 text-center text-base">마켓플레이스 데이터를 불러오는 중...</div>
                        ) : projects.length === 0 ? (
                            <div className="workspace-card-copy px-5 py-8 text-center text-base">조건에 맞는 프로젝트가 없습니다.</div>
                        ) : (
                            <div className="workspace-market-grid" data-testid="marketplace-project-grid">
                                {projects.map((project) => (
                                    <article key={project.id} className="workspace-project-card">
                                        <div className="flex items-start justify-between gap-3">
                                            <div>
                                                <p className="workspace-card-kicker">{project.category?.name || categories.find((item) => item.id === project.category_id)?.name || `카테고리 ${project.category_id}`}</p>
                                                <h3 className="workspace-card-heading">{project.title}</h3>
                                            </div>
                                            <span className={`workspace-chip ${project.is_active ? 'workspace-chip-active' : ''}`}>{project.is_active ? '운영중' : '비활성'}</span>
                                        </div>
                                        <p className="workspace-card-body">{project.description || '설명이 아직 등록되지 않았습니다.'}</p>
                                        {!!project.tags?.length && (
                                            <div className="workspace-chip-row">
                                                {project.tags.slice(0, 5).map((tag) => (
                                                    <span key={`${project.id}-${tag.id}-${tag.name}`} className="workspace-chip">#{tag.name}</span>
                                                ))}
                                            </div>
                                        )}
                                        <div className="workspace-project-stats">
                                            <div className="workspace-project-stat">
                                                <p className="workspace-project-stat-label">다운로드</p>
                                                <p className="workspace-project-stat-value">{project.downloads || 0}</p>
                                            </div>
                                            <div className="workspace-project-stat">
                                                <p className="workspace-project-stat-label">평점</p>
                                                <p className="workspace-project-stat-value">{Number(project.rating || 0).toFixed(1)}</p>
                                            </div>
                                            <div className="workspace-project-stat">
                                                <p className="workspace-project-stat-label">가격</p>
                                                <p className="workspace-project-stat-value text-[#f0b43f]">{formatCurrency(project.price)}</p>
                                            </div>
                                        </div>
                                        {project.subscription ? (
                                            <div className="workspace-list mt-3 text-sm">
                                                <div className="workspace-list-item">
                                                    <strong>월정액</strong>
                                                    <span>
                                                        {project.subscription.amount_minor != null
                                                            ? `월 ${new Intl.NumberFormat('ko-KR').format(Math.max(0, Number(project.subscription.amount_minor || 0)))} ${project.subscription.currency || 'KRW'}`
                                                            : '요금 준비 중'}
                                                    </span>
                                                </div>
                                                <div className="workspace-list-item">
                                                    <strong>구독 상품</strong>
                                                    <span>{project.subscription.product_name}</span>
                                                </div>
                                            </div>
                                        ) : null}
                                        <div className="mt-5 flex flex-wrap items-center justify-between gap-2">
                                            <div className="flex flex-wrap gap-2">
                                                <Link href={`/marketplace/${project.id}`} className="workspace-secondary-button">상세 보기</Link>
                                                <Link href={`/marketplace/orchestrator?product=code-generator-deployment-kit&projectId=${project.id}&projectTitle=${encodeURIComponent(project.title)}&projectSummary=${encodeURIComponent(project.description || '')}`} className="workspace-primary-button">오케스트레이터 주문</Link>
                                                {project.subscription ? (
                                                    <Link
                                                        href={`/marketplace/subscription?product=${encodeURIComponent(project.subscription.product_code)}`}
                                                        className="workspace-primary-button"
                                                    >
                                                        월 구독 시작
                                                    </Link>
                                                ) : null}
                                            </div>
                                            <div className="flex flex-wrap gap-2">
                                                {project.demo_url && (
                                                  project.demo_url.toLowerCase().endsWith('.apk')
                                                    ? <a href={project.demo_url} download className="workspace-topbar-chip workspace-chip-active" style={{background:'#2a7cff',color:'#fff',fontWeight:700}}>� APK 다운로드</a>
                                                    : <a href={project.demo_url} target="_blank" rel="noreferrer" className="workspace-topbar-chip">데모</a>
                                                )}
                                                {project.github_url && (
                                                  project.github_url.startsWith('/marketplace/')
                                                    ? <a href={project.github_url} className="workspace-topbar-chip" style={{background:'#31c45d22',color:'#31c45d',fontWeight:700,border:'1px solid #31c45d44'}}>🌐 웹에서 바로 사용</a>
                                                    : <a href={project.github_url} target="_blank" rel="noreferrer" className="workspace-topbar-chip">GitHub</a>
                                                )}
                                            </div>
                                        </div>
                                    </article>
                                ))}
                            </div>
                        )}
                    </section>
                </div>
            </WorkspaceChrome>
            <FeatureOrchestratorPopup
                isOpen={featureOrchestrator.isPopupOpen}
                activeFeatureId={featureOrchestrator.activeFeatureId}
                featureMeta={featureOrchestrator.activeFeatureMeta}
                popupMode={featureOrchestrator.activeFeature?.popup_mode}
                title={featureOrchestrator.activeFeature?.title || featureOrchestrator.activeFeatureMeta.popupKicker}
                featureSummary={featureOrchestrator.activeFeature?.summary || featureOrchestrator.activeFeatureMeta.launcherSummary}
                popupState={featureOrchestrator.popupState}
                projectName={featureOrchestrator.projectName}
                setProjectName={featureOrchestrator.setProjectName}
                prompt={featureOrchestrator.prompt}
                setPrompt={featureOrchestrator.setPrompt}
                templateId={featureOrchestrator.templateId}
                setTemplateId={featureOrchestrator.setTemplateId}
                finalEnabled={featureOrchestrator.finalEnabled}
                setFinalEnabled={featureOrchestrator.setFinalEnabled}
                supportsPhotoUpload={featureOrchestrator.activeFeature?.supports_photo_upload || false}
                photoFileName={featureOrchestrator.photoFileName}
                photoPreviewUrl={featureOrchestrator.photoPreviewUrl}
                applyPhotoFile={featureOrchestrator.applyPhotoFile}
                previewArtifact={featureOrchestrator.previewArtifact}
                finalArtifact={featureOrchestrator.finalArtifact}
                qualityReview={featureOrchestrator.qualityReview}
                submitLoading={featureOrchestrator.submitLoading}
                submitFeature={featureOrchestrator.submitFeature}
                closePopup={featureOrchestrator.closePopup}
                errorText={featureOrchestrator.errorText}
                runId={featureOrchestrator.runId}
                eventLog={featureOrchestrator.eventLog}
                streamConnection={featureOrchestrator.streamConnection}
                stageRunStatus={featureOrchestrator.stageRun?.status}
                latestEventAt={featureOrchestrator.latestEventAt}
                elapsedSeconds={featureOrchestrator.elapsedSeconds}
                liveViewArtifact={featureOrchestrator.liveViewArtifact}
                spreadsheetRunSummary={featureOrchestrator.spreadsheetRunSummary}
                spreadsheetDownloadLinks={featureOrchestrator.spreadsheetDownloadLinks}
                progressSnapshot={featureOrchestrator.progressSnapshot}
                progressHistory={featureOrchestrator.progressHistory}
            />
        </>
    );
}
