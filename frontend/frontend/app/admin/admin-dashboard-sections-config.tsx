import * as React from 'react';
import AdminAdOrdersSection from '@/components/admin/admin-ad-orders-section';
import AdminAutoConnectGraphPanel from '@/components/admin/admin-auto-connect-graph-panel';
import AdminCategoryManagementSection from '@/components/admin/admin-category-management-section';
import AdminDashboardOverview from '@/components/admin/admin-dashboard-overview';
import AdminCostSimulatorSection from '@/components/admin/admin-cost-simulator-section';
import AdminLlmControlSummary from '@/components/admin/admin-llm-control-summary';
import AdminManualOrchestratorSection from '@/components/admin/admin-manual-orchestrator-section';
import AdminQuickLinksSection from '@/components/admin/admin-quick-links-section';
import AdminSampleProductsSection from '@/components/admin/admin-sample-products-section';
import AdminSubscriptionMonitorSection from '@/components/admin/admin-subscription-monitor-section';
import type {
    AdminBoardSection,
    AdminDashboardSectionsConfigParams,
} from '@/app/admin/admin-page-types';

export function buildAdminDashboardSectionsConfig(params: AdminDashboardSectionsConfigParams): AdminBoardSection[] {
    const {
        adminControlHubOpen,
        setAdminControlHubOpen,
        systemSettings,
        dashboardAnalysis,
        setSystemSettingsPanelOpen,
        loadSystemSettings,
        applyGlobalAutomaticMode,
        healthOverviewOpen,
        setHealthOverviewOpen,
        adminDashboardOverviewAssembly,
        autoConnectGraphPanelOpen,
        setAutoConnectGraphPanelOpen,
        adminAutoConnectGraphAssembly,
        customerOrchestratorPanelOpen,
        setCustomerOrchestratorPanelOpen,
        adminManualOrchestratorAssembly,
        adOrdersPanelOpen,
        setAdOrdersPanelOpen,
        adminAdOrdersAssembly,
        categoryPanelOpen,
        setCategoryPanelOpen,
        visibleCategories,
        sortedVisibleCategories,
        categoryStats,
        categoryRecentProjects,
        categoryMessage,
        categoryUpdatingId,
        categoryDeletingId,
        loadCategories,
        updateCategory,
        cancelEditCategory,
        beginEditCategory,
        deleteCategory,
        categoryName,
        categoryDescription,
        categoryCreating,
        hideEmptyCategories,
        categorySortBy,
        setCategoryName,
        setCategoryDescription,
        createCategory,
        setHideEmptyCategories,
        setCategorySortBy,
        editingCategoryId,
        editingCategoryName,
        editingCategoryDescription,
        setEditingCategoryName,
        setEditingCategoryDescription,
        subscriptionMonitorPanelOpen,
        setSubscriptionMonitorPanelOpen,
        apiBaseUrl,
        costSimulatorPanelOpen,
        setCostSimulatorPanelOpen,
        costSimulatorForm,
        costSimulatorLoading,
        costSimulatorError,
        costSimulatorResult,
        updateCostSimulatorField,
        runCostSimulation,
        quickLinksPanelOpen,
        setQuickLinksPanelOpen,
        llmControlPanelOpen,
        setLlmControlPanelOpen,
        llmPanelHeight,
        samplePanelOpen,
        setSamplePanelOpen,
        adminSampleProductsAssembly,
        liveLogsPanelOpen,
        setLiveLogsPanelOpen,
        liveLogs,
        topProjectsPanelOpen,
        setTopProjectsPanelOpen,
        filteredTopProjects,
        formatCurrency,
    } = params;

    return [
        {
            id: 'admin-control',
            title: '🧩 ADMIN CONTROL HUB',
            usage: '전역 운영 지표 요약 및 퀵 액션',
            description: '앱 건강상태와 최근 설정 정보를 한눈에 모니터링합니다.',
            open: adminControlHubOpen,
            onToggle: () => setAdminControlHubOpen((prev) => !prev),
            body: (
                <div className="workspace-admin-command">
                    <textarea
                        className="workspace-admin-command-textarea"
                        readOnly
                        value={[
                            '운영자 명령 허브',
                            `- 관리자 도메인: ${systemSettings?.summary.admin_domain || '-'}`,
                            `- API 기준 주소: ${systemSettings?.summary.local_api_base_url || '-'}`,
                            `- 저장 루트: ${systemSettings?.summary.marketplace_host_root || '-'}`,
                            `- 현재 LLM 프로필: ${systemSettings?.summary.selected_profile || '-'}`,
                            `- 최근 self-run: ${dashboardAnalysis.normalizedDashboardSelfRunStatus?.status || '-'}`,
                        ].join('\n')}
                    />
                    <div className="workspace-admin-command-actions">
                        <button type="button" onClick={() => setSystemSettingsPanelOpen(true)} className="workspace-primary-button">전역 설정 열기</button>
                        <button type="button" onClick={loadSystemSettings} className="workspace-secondary-button">설정 새로고침</button>
                        <button type="button" onClick={applyGlobalAutomaticMode} className="workspace-ghost-button">전역 자동 전환</button>
                    </div>
                </div>
            ),
            toggleTestId: 'admin-control-hub',
            windowSize: 'wide',
        },
        {
            id: 'health',
            title: '🩺 관리자 자동 건강상태 / 자가진단',
            usage: '전체 시스템 건강 상태 모니터링 및 자가 치유',
            description: '각 컴포넌트의 상태를 점검하고 복구 동작을 진행합니다.',
            open: healthOverviewOpen,
            onToggle: () => setHealthOverviewOpen((prev) => !prev),
            body: <AdminDashboardOverview {...adminDashboardOverviewAssembly} />,
            toggleTestId: 'admin-health-overview-section',
            windowSize: 'full',
        },
        {
            id: 'autoconnect',
            title: '🕸️ self auto-connect graph',
            usage: '버튼/패널/대화/실행 공통 추적키 확인',
            description: '관리자 대시보드와 관리자 LLM의 active connection 흐름을 추적합니다.',
            open: autoConnectGraphPanelOpen,
            onToggle: () => setAutoConnectGraphPanelOpen((prev) => !prev),
            body: <AdminAutoConnectGraphPanel {...adminAutoConnectGraphAssembly} />,
            windowSize: 'wide',
        },
        {
            id: 'manual',
            title: '관리자 수동 오케스트레이션',
            usage: '관리자 전용 수동 분석·구조 설계',
            description: '장기 분석, 기술 정보 유입, 구조 수립을 단계별로 수동 관리합니다.',
            open: customerOrchestratorPanelOpen,
            onToggle: () => setCustomerOrchestratorPanelOpen((prev) => !prev),
            body: <AdminManualOrchestratorSection {...adminManualOrchestratorAssembly} />,
            windowSize: 'full',
        },
        {
            id: 'ad-orders',
            title: '🎬 광고 영상 주문 모니터링',
            usage: '광고 주문 상태와 재시도/다운로드 운영 관리',
            description: '주문 모니터링과 액션을 별도 보드 카드로 바로 수행합니다.',
            open: adOrdersPanelOpen,
            onToggle: () => setAdOrdersPanelOpen((prev) => !prev),
            body: (
                <AdminAdOrdersSection
                    summary={adminAdOrdersAssembly.summary}
                    review={adminAdOrdersAssembly.review}
                    actions={adminAdOrdersAssembly.actions}
                />
            ),
            toggleTestId: 'admin-storyboard-section-toggle',
            windowSize: 'full',
        },
        {
            id: 'category',
            title: '🗂️ 마켓플레이스 카테고리 관리',
            usage: '카테고리 등록과 운영 분류 체계 정리',
            description: '상품 분류 체계를 정리하는 관리자용 카드입니다.',
            open: categoryPanelOpen,
            onToggle: () => setCategoryPanelOpen((prev) => !prev),
            body: (
                <AdminCategoryManagementSection
                    list={{
                        visibleCategories,
                        sortedVisibleCategories,
                        categoryStats,
                        categoryRecentProjects,
                        categoryMessage,
                        categoryUpdatingId,
                        categoryDeletingId,
                        onLoadCategories: loadCategories,
                        onUpdateCategory: (categoryId: number) => void updateCategory(categoryId),
                        onCancelEditCategory: cancelEditCategory,
                        onBeginEditCategory: beginEditCategory,
                        onDeleteCategory: (category) => void deleteCategory(category),
                    }}
                    filter={{
                        categoryName,
                        categoryDescription,
                        categoryCreating,
                        hideEmptyCategories,
                        categorySortBy,
                        onCategoryNameChange: setCategoryName,
                        onCategoryDescriptionChange: setCategoryDescription,
                        onCreateCategory: () => void createCategory(),
                        onHideEmptyCategoriesChange: setHideEmptyCategories,
                        onCategorySortByChange: setCategorySortBy,
                    }}
                    editing={{
                        editingCategoryId,
                        editingCategoryName,
                        editingCategoryDescription,
                        onEditingCategoryNameChange: setEditingCategoryName,
                        onEditingCategoryDescriptionChange: setEditingCategoryDescription,
                    }}
                />
            ),
            windowSize: 'wide',
        },
        {
            id: 'subscription-monitor',
            title: '💳 구독 결제 운영 모니터링',
            usage: '실패 결제/환불/상태 변경 이력/웹훅 실패 모니터링',
            description: '구독 과금 운영 이슈를 관리자 화면에서 바로 확인하고 재점검합니다.',
            open: subscriptionMonitorPanelOpen,
            onToggle: () => setSubscriptionMonitorPanelOpen((prev) => !prev),
            body: <AdminSubscriptionMonitorSection apiBaseUrl={apiBaseUrl} />,
            windowSize: 'full',
        },
        {
            id: 'cost',
            title: '💸 비용 시뮬레이터',
            usage: '로컬+외부 하이브리드 비용 모델 계산',
            description: '컷당 비용과 권장 아키텍처를 즉시 계산합니다.',
            open: costSimulatorPanelOpen,
            onToggle: () => setCostSimulatorPanelOpen((prev) => !prev),
            body: (
                <AdminCostSimulatorSection
                    form={costSimulatorForm}
                    loading={costSimulatorLoading}
                    error={costSimulatorError || ''}
                    result={costSimulatorResult}
                    onFieldChange={updateCostSimulatorField}
                    onRun={runCostSimulation}
                />
            ),
            windowSize: 'wide',
        },
        {
            id: 'quick',
            title: '⚡ 빠른 이동',
            usage: '운영자가 자주 여는 핵심 화면과 API 바로가기',
            description: '핵심 운영 경로를 작은 카드로 정리합니다.',
            open: quickLinksPanelOpen,
            onToggle: () => setQuickLinksPanelOpen((prev) => !prev),
            body: <AdminQuickLinksSection apiBaseUrl={apiBaseUrl} />,
            windowSize: 'default',
        },
        {
            id: 'llm',
            title: '🤖 LLM 통합 제어 패널',
            usage: 'LLM runtime, 역할별 모델, 실행 정책 관리',
            description: '핵심 LLM 운영값을 집결 관리합니다.',
            open: llmControlPanelOpen,
            onToggle: () => setLlmControlPanelOpen((prev) => !prev),
            body: <AdminLlmControlSummary llmPanelHeight={llmPanelHeight} />,
            windowSize: 'full',
        },
        {
            id: 'sample',
            title: '🎯 원터치 샘플 생성',
            usage: '테스트/디자인 검증용 샘플 상품 생성과 정리',
            description: '샘플 생성과 정리를 별도 카드로 분리합니다.',
            open: samplePanelOpen,
            onToggle: () => setSamplePanelOpen((prev) => !prev),
            body: <AdminSampleProductsSection {...adminSampleProductsAssembly} />,
            windowSize: 'wide',
        },
        {
            id: 'live-logs',
            title: '📡 운영 라이브 로그',
            usage: '실시간 이벤트 스트림 확인',
            description: '운영 이벤트를 스트림 형태로 제공합니다.',
            open: liveLogsPanelOpen,
            onToggle: () => setLiveLogsPanelOpen((prev) => !prev),
            body: (
                <div style={{ padding: '0 20px', paddingBottom: '20px' }}>
                    {liveLogs.length === 0 ? (
                        <p className="workspace-card-copy">아직 기록된 실시간 이벤트가 없습니다.</p>
                    ) : (
                        <ul className="workspace-list">
                            {liveLogs.map((log) => (
                                <li key={log.id} className="workspace-list-item">
                                    <div>
                                        <strong>{log.message}</strong>
                                        <span>{log.connection_id || '-'} · {log.panel_id || '-'} · {log.action || '-'}</span>
                                    </div>
                                    <span>{log.createdAt}</span>
                                </li>
                            ))}
                        </ul>
                    )}
                </div>
            ),
            toggleTestId: 'admin-live-logs-section',
            windowSize: 'wide',
        },
        {
            id: 'top-projects',
            title: '🏆 상위 프로젝트',
            usage: '다운로드 기준 상위 항목 확인',
            description: '인기 프로젝트 지표를 요약해 제공합니다.',
            open: topProjectsPanelOpen,
            onToggle: () => setTopProjectsPanelOpen((prev) => !prev),
            body: (
                <div style={{ padding: '0 20px', paddingBottom: '20px' }}>
                    {filteredTopProjects.length === 0 ? (
                        <p className="workspace-card-copy">아직 집계된 상위 프로젝트가 없습니다.</p>
                    ) : (
                        <div className="workspace-list mt-4">
                            {filteredTopProjects.map((project) => (
                                <div key={project.id} className="workspace-list-item">
                                    <div>
                                        <strong>{project.title}</strong>
                                        <span>다운로드 {project.downloads} · 평점 {project.rating?.toFixed?.(1) ?? project.rating}</span>
                                    </div>
                                    <strong>{formatCurrency(project.price)}</strong>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            ),
            toggleTestId: 'admin-top-projects-section',
            windowSize: 'wide',
        },
    ];
}
