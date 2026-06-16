'use client';

import type { AdminIdentityProviderSettings, AdminSystemSettingsResponse } from '@/lib/admin-system-settings-service';
import type { AdminSystemSettingStatusSection } from '@/lib/admin-system-settings-service';

type GeneratorRoleOption = {
    id: string;
    label: string;
    generator: string;
    runtime_role: string;
    options: string[];
    defaultModel: string;
};

export interface AdminSystemSettingsPanelProps {
    systemSettings: AdminSystemSettingsResponse | null;
    systemSettingsDisconnected: boolean;
    systemSettingsLoading: boolean;
    systemSettingsSaving: boolean;
    systemAutomaticApplying: boolean;
    systemSettingsMessage: string;
    identityProviderSettings: AdminIdentityProviderSettings | null;
    generatorRoleOptions: GeneratorRoleOption[];
    optimizedRuntimeRouteDraft: Record<string, string>;
    statusSections: AdminSystemSettingStatusSection[];
    generatorEnvKeyMap: Record<string, string[]>;
    runtimeRouteEnvMap: Record<string, string>;
    systemSettingsOpen: Record<string, boolean>;
    systemSettingsDraft: Record<string, string>;
    postgresPasswordNext: string;
    postgresPasswordConfirm: string;
    postgresPasswordSaving: boolean;
    postgresPasswordMessage: string;
    adminPasswordCurrent: string;
    adminPasswordNext: string;
    adminPasswordConfirm: string;
    adminPasswordChanging: boolean;
    adminPasswordMessage: string;
    onApplyGlobalAutomaticMode: () => void;
    onLoadSystemSettings: () => void;
    onSaveSystemSettings: () => void;
    onApplyGeneratorModelOverride: (profileId: string, modelName: string) => void;
    onToggleSystemSettingsSection: (sectionId: string) => void;
    onUpdateSystemSettingValue: (key: string, value: string) => void;
    onPostgresPasswordNextChange: (value: string) => void;
    onPostgresPasswordConfirmChange: (value: string) => void;
    onUpdatePostgresRuntimePassword: () => void;
    onAdminPasswordCurrentChange: (value: string) => void;
    onAdminPasswordNextChange: (value: string) => void;
    onAdminPasswordConfirmChange: (value: string) => void;
    onChangeAdminPassword: () => void;
}

export default function AdminSystemSettingsPanel({
    systemSettings,
    systemSettingsDisconnected,
    systemSettingsLoading,
    systemSettingsSaving,
    systemAutomaticApplying,
    systemSettingsMessage,
    identityProviderSettings,
    generatorRoleOptions,
    optimizedRuntimeRouteDraft,
    statusSections,
    generatorEnvKeyMap,
    runtimeRouteEnvMap,
    systemSettingsOpen,
    systemSettingsDraft,
    postgresPasswordNext,
    postgresPasswordConfirm,
    postgresPasswordSaving,
    postgresPasswordMessage,
    adminPasswordCurrent,
    adminPasswordNext,
    adminPasswordConfirm,
    adminPasswordChanging,
    adminPasswordMessage,
    onApplyGlobalAutomaticMode,
    onLoadSystemSettings,
    onSaveSystemSettings,
    onApplyGeneratorModelOverride,
    onToggleSystemSettingsSection,
    onUpdateSystemSettingValue,
    onPostgresPasswordNextChange,
    onPostgresPasswordConfirmChange,
    onUpdatePostgresRuntimePassword,
    onAdminPasswordCurrentChange,
    onAdminPasswordNextChange,
    onAdminPasswordConfirmChange,
    onChangeAdminPassword,
}: AdminSystemSettingsPanelProps) {
    return (
        <>
            <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div>
                    <div className="flex flex-wrap items-center gap-2">
                        <h2 className="text-lg font-semibold text-gray-900">🧭 전역 .env 설정 패널</h2>
                        <span className="rounded-full border border-blue-200 bg-blue-50 px-2 py-1 text-[11px] font-semibold text-blue-700">
                            메인 /admin 통합 제어
                        </span>
                        <span className={`rounded-full border px-2 py-1 text-[11px] font-semibold ${systemSettings
                            ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                            : systemSettingsDisconnected
                                ? 'border-amber-200 bg-amber-50 text-amber-700'
                                : 'border-gray-200 bg-gray-100 text-gray-600'
                            }`}>
                            {systemSettings
                                ? '연동 완료'
                                : systemSettingsDisconnected
                                    ? '미연동 상태'
                                    : '연동 확인 중'}
                        </span>
                    </div>
                    <p className="mt-1 text-sm text-gray-500">
                        프로그램 전반 운영값을 관리자 대시보드에서 직접 읽고 저장합니다. 각 섹션은 접이식이며, 사용 용도를 함께 표시합니다.
                    </p>
                </div>
                <div className="flex gap-2">
                    <button
                        type="button"
                        onClick={onApplyGlobalAutomaticMode}
                        className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:bg-blue-300"
                        disabled={systemSettingsLoading || systemSettingsSaving || systemAutomaticApplying}
                    >
                        {systemAutomaticApplying ? '전환 중...' : '전역 자동 전환'}
                    </button>
                    <button
                        type="button"
                        onClick={onLoadSystemSettings}
                        className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm hover:bg-gray-100"
                        disabled={systemSettingsLoading || systemSettingsSaving || systemAutomaticApplying}
                    >
                        {systemSettingsLoading ? '조회 중...' : '설정 새로고침'}
                    </button>
                    <button
                        type="button"
                        onClick={onSaveSystemSettings}
                        className="rounded-lg bg-emerald-600 px-4 py-2 text-sm text-white hover:bg-emerald-700 disabled:bg-emerald-300"
                        disabled={systemSettingsLoading || systemSettingsSaving || systemAutomaticApplying || !systemSettings}
                    >
                        {systemSettingsSaving ? '저장 중...' : '.env 저장'}
                    </button>
                </div>
            </div>

            {systemSettings && (
                <div className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
                    <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                        <p className="text-xs text-gray-500">관리자 도메인</p>
                        <p className="mt-1 break-all text-sm font-semibold text-gray-900">{systemSettings.summary.admin_domain || '-'}</p>
                    </div>
                    <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                        <p className="text-xs text-gray-500">API 기준 주소</p>
                        <p className="mt-1 break-all text-sm font-semibold text-gray-900">{systemSettings.summary.local_api_base_url || '-'}</p>
                    </div>
                    <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                        <p className="text-xs text-gray-500">저장 루트</p>
                        <p className="mt-1 break-all text-sm font-semibold text-gray-900">{systemSettings.summary.marketplace_host_root || '-'}</p>
                    </div>
                    <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                        <p className="text-xs text-gray-500">현재 LLM 프로필</p>
                        <p className="mt-1 break-all text-sm font-semibold text-gray-900">{systemSettings.summary.selected_profile || '-'}</p>
                    </div>
                </div>
            )}

            {systemSettings && (
                <div className="mb-4 grid grid-cols-1 gap-4 xl:grid-cols-[1.15fr_0.85fr]">
                    <div className="rounded-xl border border-[#35548a] bg-[#1b2b44] p-4 text-[#dbeafe]">
                        <div className="flex items-center justify-between gap-3">
                            <div>
                                <h3 className="text-sm font-semibold text-[#f8fbff]">역할별 코드 생성기 설정</h3>
                                <p className="mt-1 text-xs text-[#c7ddff]">이미지처럼 생성기 역할을 관리자 설정 박스 안에서 바로 확인하도록 붙입니다.</p>
                            </div>
                            <span className="rounded-full border border-[#4b6ea8] bg-[#172334] px-2 py-1 text-[11px] font-semibold text-[#9ecbff]">
                                strategy {systemSettings.summary.code_generation_strategy || '-'}
                            </span>
                        </div>
                        <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                            {generatorRoleOptions.map((profile) => (
                                <div key={profile.id} className="rounded-lg border border-[#314766] bg-[#161d27] px-3 py-3 text-xs text-[#dbeafe]">
                                    <div className="flex items-center justify-between gap-2">
                                        <p className="font-semibold text-[#f8fbff]">{profile.label}</p>
                                        <span className="rounded-full border border-[#36527d] bg-[#20314b] px-2 py-1 text-[10px] font-semibold text-[#8fc2ff]">{profile.generator}</span>
                                    </div>
                                    <p className="mt-2 text-[#d0e3ff]">role: {profile.runtime_role}</p>
                                    <p className="mt-1 break-all text-[11px] text-[#8fc2ff]">profile id: {profile.id}</p>
                                    <label className="mt-3 block">
                                        <span className="mb-2 block text-[11px] font-semibold text-[#f8fbff]">생성기 모델 선택</span>
                                        <select
                                            value={profile.defaultModel || ''}
                                            onChange={(event) => onApplyGeneratorModelOverride(profile.id, event.target.value)}
                                            className="w-full rounded-lg border border-[#36527d] bg-[#223248] px-3 py-2 text-[11px] text-[#f8fbff]"
                                            title={`${profile.label} 생성기 모델 선택`}
                                        >
                                            {profile.options.map((modelName) => (
                                                <option key={`${profile.id}-${modelName}`} value={modelName}>{modelName}</option>
                                            ))}
                                        </select>
                                        <p className="mt-2 text-[11px] text-[#9ecbff]">
                                            연결 설정: {(generatorEnvKeyMap[profile.id] || []).join(', ') || '공통 기본값'}
                                        </p>
                                    </label>
                                </div>
                            ))}
                        </div>
                    </div>
                    <div className="rounded-xl border border-[#314766] bg-[#161d27] p-4 text-[#dbeafe]">
                        <div className="flex items-center justify-between gap-3">
                            <div>
                                <h3 className="text-sm font-semibold text-[#f8fbff]">설치된 LLM 모델 목록</h3>
                                <p className="mt-1 text-xs text-[#c7d2e0]">두번째 이미지의 16개 모델 영역에 맞춰 관리자 설정 박스 안에서도 생성기와 함께 보이도록 노출합니다.</p>
                            </div>
                            <span className="rounded-full border border-[#314766] bg-[#0f1724] px-2 py-1 text-[11px] font-semibold text-[#9fb7d7]">
                                {systemSettings.summary.available_model_count || 0}개
                            </span>
                        </div>
                        <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                            <div className="rounded-lg border border-[#314766] bg-[#0f1724] px-3 py-3 text-xs text-[#dbeafe]">
                                <p className="text-[#9fb7d7]">기본 모델</p>
                                <p className="mt-1 break-all font-semibold text-[#f8fbff]">{systemSettings.summary.default_model || '-'}</p>
                            </div>
                            <div className="rounded-lg border border-[#314766] bg-[#0f1724] px-3 py-3 text-xs text-[#dbeafe]">
                                <p className="text-[#9fb7d7]">챗봇 모델</p>
                                <p className="mt-1 break-all font-semibold text-[#f8fbff]">{systemSettings.summary.chat_model || '-'}</p>
                            </div>
                            <div className="rounded-lg border border-[#314766] bg-[#0f1724] px-3 py-3 text-xs text-[#dbeafe]">
                                <p className="text-[#9fb7d7]">음성 모델</p>
                                <p className="mt-1 break-all font-semibold text-[#f8fbff]">{systemSettings.summary.voice_chat_model || '-'}</p>
                            </div>
                            <div className="rounded-lg border border-[#314766] bg-[#0f1724] px-3 py-3 text-xs text-[#dbeafe]">
                                <p className="text-[#9fb7d7]">추론 모델</p>
                                <p className="mt-1 break-all font-semibold text-[#f8fbff]">{systemSettings.summary.reasoning_model || '-'}</p>
                            </div>
                            <div className="rounded-lg border border-[#314766] bg-[#0f1724] px-3 py-3 text-xs text-[#dbeafe] md:col-span-2">
                                <p className="text-[#9fb7d7]">코딩 모델</p>
                                <p className="mt-1 break-all font-semibold text-[#f8fbff]">{systemSettings.summary.coding_model || '-'}</p>
                            </div>
                        </div>
                        <div className="mt-3 rounded-lg border border-[#314766] bg-[#0f1724] px-3 py-3 text-xs text-[#dbeafe]">
                            <p className="font-semibold text-[#f8fbff]">설치 모델 전체 목록</p>
                            <div className="mt-2 flex flex-wrap gap-2">
                                {(systemSettings.summary.available_models || []).map((modelName) => (
                                    <span key={modelName} className="rounded-full border border-[#49617d] bg-[#edf3fb] px-2 py-1 text-[11px] font-semibold text-[#334155]">
                                        {modelName}
                                    </span>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {systemSettings && (
                <div className="mb-4 rounded-lg border border-dashed border-gray-300 bg-gray-50 p-3 text-xs text-gray-500 space-y-1">
                    <p>ENV 경로: {systemSettings.env_path}</p>
                    <p>런타임 모델 경로: {systemSettings.runtime_config_path}</p>
                    <p>실시간 역할별 LLM 제어와 세부 runtime 조정은 이 관리자 대시보드 하단 내장 패널에서 계속 관리합니다.</p>
                    <p>기본 최적화 기준: selected_profile={systemSettings.summary.selected_profile || 'rtx5090_32gb'} · code_generation_strategy={systemSettings.summary.code_generation_strategy || 'auto_generator'} · min_files=27 · min_dirs=3</p>
                </div>
            )}

            {systemSettingsMessage && (
                <div className={`mb-4 whitespace-pre-line rounded-lg px-4 py-3 text-sm ${systemSettingsDisconnected
                    ? 'border border-amber-200 bg-amber-50 text-amber-800'
                    : 'border border-blue-200 bg-blue-50 text-blue-800'
                    }`}>
                    {systemSettingsMessage}
                </div>
            )}

            <div className="mb-4 rounded-lg border border-violet-200 bg-violet-50 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h3 className="text-sm font-semibold text-violet-900">🔑 관리자 계정 비밀번호 변경</h3>
                        <p className="mt-1 text-xs text-violet-800">
                            Admin 로그인에 쓰는 계정 비밀번호입니다. PostgreSQL DB 비밀번호와는 별개입니다.
                            현재 비밀번호를 모르면 로그인 화면의 복구 페이지 또는 `scripts/reset_fixed_admin_password.py`를 사용하세요.
                        </p>
                    </div>
                </div>
                <form
                    className="mt-3"
                    onSubmit={(event) => {
                        event.preventDefault();
                        onChangeAdminPassword();
                    }}
                >
                    <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                        <label className="block">
                            <span className="mb-2 block text-xs font-semibold text-violet-900">현재 비밀번호</span>
                            <input
                                type="password"
                                value={adminPasswordCurrent}
                                onChange={(event) => onAdminPasswordCurrentChange(event.target.value)}
                                className="w-full rounded-lg border border-violet-300 bg-white px-3 py-2 text-sm"
                                autoComplete="current-password"
                            />
                        </label>
                        <label className="block">
                            <span className="mb-2 block text-xs font-semibold text-violet-900">새 비밀번호</span>
                            <input
                                type="password"
                                value={adminPasswordNext}
                                onChange={(event) => onAdminPasswordNextChange(event.target.value)}
                                className="w-full rounded-lg border border-violet-300 bg-white px-3 py-2 text-sm"
                                autoComplete="new-password"
                            />
                        </label>
                        <label className="block">
                            <span className="mb-2 block text-xs font-semibold text-violet-900">새 비밀번호 확인</span>
                            <input
                                type="password"
                                value={adminPasswordConfirm}
                                onChange={(event) => onAdminPasswordConfirmChange(event.target.value)}
                                className="w-full rounded-lg border border-violet-300 bg-white px-3 py-2 text-sm"
                                autoComplete="new-password"
                            />
                        </label>
                    </div>
                    <div className="mt-3 flex flex-wrap items-center gap-3">
                        <button
                            type="submit"
                            disabled={
                                adminPasswordChanging
                                || !adminPasswordCurrent
                                || !adminPasswordNext
                                || !adminPasswordConfirm
                            }
                            className={`rounded-lg px-4 py-2 text-sm font-semibold text-white ${adminPasswordChanging || !adminPasswordCurrent || !adminPasswordNext || !adminPasswordConfirm ? 'bg-violet-300' : 'bg-violet-600 hover:bg-violet-700'}`}
                        >
                            {adminPasswordChanging ? '변경 중...' : '관리자 비밀번호 변경'}
                        </button>
                        {adminPasswordMessage && (
                            <p className={`whitespace-pre-line text-sm ${adminPasswordMessage.includes('실패') || adminPasswordMessage.includes('올바르지') ? 'text-red-700' : 'text-violet-900'}`}>
                                {adminPasswordMessage}
                            </p>
                        )}
                    </div>
                </form>
            </div>

            <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h3 className="text-sm font-semibold text-amber-900">🗄️ PostgreSQL 런타임 비밀번호 정렬</h3>
                        <p className="mt-1 text-xs text-amber-800">이 작업은 백엔드가 참조하는 `.env`와 로컬 시크릿 파일의 PostgreSQL 비밀번호를 함께 맞춥니다. Windows PostgreSQL 서버 계정 비밀번호 자체는 관리자 권한 PowerShell 단계에서 별도 적용해야 합니다.</p>
                    </div>
                </div>
                <form
                    className="mt-3"
                    onSubmit={(event) => {
                        event.preventDefault();
                        void onUpdatePostgresRuntimePassword();
                    }}
                >
                    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                        <label className="block">
                            <span className="mb-2 block text-xs font-semibold text-amber-900">새 PostgreSQL 비밀번호</span>
                            <input
                                type="password"
                                value={postgresPasswordNext}
                                onChange={(event) => onPostgresPasswordNextChange(event.target.value)}
                                className="w-full rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm"
                                autoComplete="new-password"
                            />
                        </label>
                        <label className="block">
                            <span className="mb-2 block text-xs font-semibold text-amber-900">새 PostgreSQL 비밀번호 확인</span>
                            <input
                                type="password"
                                value={postgresPasswordConfirm}
                                onChange={(event) => onPostgresPasswordConfirmChange(event.target.value)}
                                className="w-full rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm"
                                autoComplete="new-password"
                            />
                        </label>
                    </div>
                    <div className="mt-3 flex flex-wrap items-center gap-3">
                        <button
                            type="submit"
                            disabled={postgresPasswordSaving || !postgresPasswordNext || !postgresPasswordConfirm}
                            className={`rounded-lg px-4 py-2 text-sm font-semibold text-white ${postgresPasswordSaving || !postgresPasswordNext || !postgresPasswordConfirm ? 'bg-amber-300' : 'bg-amber-600 hover:bg-amber-700'}`}
                        >
                            {postgresPasswordSaving ? '저장 중...' : '런타임 비밀번호 저장'}
                        </button>
                        {postgresPasswordMessage && (
                            <p className={`whitespace-pre-line text-sm ${postgresPasswordMessage.includes('실패') || postgresPasswordMessage.includes('오류') ? 'text-red-700' : 'text-amber-900'}`}>
                                {postgresPasswordMessage}
                            </p>
                        )}
                    </div>
                </form>
            </div>

            {systemSettingsLoading && !systemSettings ? (
                <p className="text-sm text-gray-500">전역 설정을 불러오는 중입니다...</p>
            ) : !systemSettings ? (
                <div className="space-y-4">
                    <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
                        {statusSections.map((section) => (
                            <div key={section.id} className="rounded-xl border border-amber-200 bg-amber-50 p-4">
                                <div className="flex items-center justify-between gap-2">
                                    <h3 className="text-sm font-semibold text-gray-900">{section.title}</h3>
                                    <span className="rounded-full border border-amber-200 bg-white px-2 py-1 text-[11px] font-semibold text-amber-700">
                                        미연동
                                    </span>
                                </div>
                                <p className="mt-2 text-xs text-amber-700">{section.usage}</p>
                                <p className="mt-2 text-xs leading-5 text-gray-600">{section.description}</p>
                            </div>
                        ))}
                    </div>
                    <div className="rounded-lg border border-dashed border-amber-300 bg-white px-4 py-3 text-xs text-gray-600">
                        전역 설정 원본이 연결되면 위 항목들이 자동으로 실제 값 편집 모드로 전환됩니다.
                    </div>
                </div>
            ) : (
                <div className="space-y-3">
                    <div className="rounded-xl border border-[#35548a] bg-[#1b2b44] px-4 py-4 text-sm text-[#dbeafe]">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                            <div>
                                <h3 className="text-sm font-semibold text-[#f8fbff]">프로그램 최적화 기본값</h3>
                                <p className="mt-1 text-xs text-[#c7ddff]">관리자 대시보드 저장 시 모델, 런타임, 파일 수 기준을 프로그램 개발 최적화 기본값으로 함께 맞춥니다.</p>
                            </div>
                            <div className="rounded-lg border border-[#4b6ea8] bg-[#172334] px-3 py-2 text-xs text-[#9ecbff]">
                                selected_profile {systemSettings.summary.selected_profile || 'rtx5090_32gb'} · auto_generator 고정
                            </div>
                        </div>
                        <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                            {Object.entries(optimizedRuntimeRouteDraft).map(([routeKey, modelName]) => (
                                <div key={routeKey} className="rounded-lg border border-[#314766] bg-[#0f1724] px-3 py-3 text-xs text-[#dbeafe]">
                                    <p className="font-semibold text-[#f8fbff]">{routeKey}</p>
                                    <p className="mt-1 break-all text-[#9ecbff]">{modelName || '-'}</p>
                                    <p className="mt-2 text-[11px] text-[#c7d2e0]">env key: {runtimeRouteEnvMap[routeKey] || '-'}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                    {systemSettings.sections.map((section) => {
                        const isOpen = !!systemSettingsOpen[section.id];
                        return (
                            <div key={section.id} className="overflow-hidden rounded-xl border border-gray-200">
                                <button
                                    type="button"
                                    onClick={() => onToggleSystemSettingsSection(section.id)}
                                    className="w-full px-4 py-4 text-left hover:bg-gray-50"
                                >
                                    <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
                                        <div>
                                            <div className="flex flex-wrap items-center gap-2">
                                                <span className="text-base font-semibold text-gray-900">{section.title}</span>
                                                <span className="rounded-full border border-violet-200 bg-violet-50 px-2 py-1 text-[11px] font-semibold text-violet-700">
                                                    사용 용도: {section.usage || '운영값 조정'}
                                                </span>
                                            </div>
                                            <p className="mt-1 text-sm text-gray-500">{section.description}</p>
                                        </div>
                                        <span className="text-xs text-gray-500">{isOpen ? '접기' : '펼치기'}</span>
                                    </div>
                                </button>

                                {isOpen && (
                                    <div className="border-t border-gray-200 px-4 py-4">
                                        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                                            {section.fields.map((field) => (
                                                <label key={field.key} className="block">
                                                    <span className="mb-2 block text-xs font-semibold text-gray-500">{field.label}</span>
                                                    {field.multiline ? (
                                                        <textarea
                                                            rows={3}
                                                            value={systemSettingsDraft[field.key] ?? ''}
                                                            onChange={(event) => onUpdateSystemSettingValue(field.key, event.target.value)}
                                                            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                                                            spellCheck={false}
                                                        />
                                                    ) : (
                                                        <input
                                                            type={field.sensitive ? 'password' : 'text'}
                                                            value={systemSettingsDraft[field.key] ?? ''}
                                                            onChange={(event) => onUpdateSystemSettingValue(field.key, event.target.value)}
                                                            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                                                            spellCheck={false}
                                                        />
                                                    )}
                                                </label>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}

            <div className="mb-4 rounded-xl border border-violet-200 bg-violet-50 px-5 py-4 text-violet-950">
                <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                        <div className="flex flex-wrap items-center gap-2">
                            <h2 className="text-sm font-semibold">PASS / KMC / KCB 상용 운영 게이트</h2>
                            <span className={`rounded-full border px-2 py-1 text-[11px] font-semibold ${identityProviderSettings?.provider_statuses?.some((item) => item.request_mapping_ready && item.complete_mapping_ready) ? 'border-emerald-300 bg-white text-emerald-700' : 'border-amber-300 bg-white text-amber-700'}`}>
                                {identityProviderSettings?.provider_statuses?.some((item) => item.request_mapping_ready && item.complete_mapping_ready) ? '실서버 매핑 확인 가능' : '운영값 보강 필요'}
                            </span>
                        </div>
                        <p className="mt-2 text-sm text-violet-900/80">관리자 대시보드에서 공급사 운영값, callback URL, 실서버 매핑 상태를 직접 확인하고 저장합니다.</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <a href="/terms" target="_blank" rel="noreferrer" className="rounded-lg border border-violet-300 bg-white px-3 py-2 text-xs font-semibold text-violet-800 hover:bg-violet-100">
                            이용약관 공개 페이지
                        </a>
                        <a href="/privacy" target="_blank" rel="noreferrer" className="rounded-lg border border-violet-300 bg-white px-3 py-2 text-xs font-semibold text-violet-800 hover:bg-violet-100">
                            개인정보처리방침 공개 페이지
                        </a>
                    </div>
                </div>
                {identityProviderSettings ? (
                    <div className="mt-4 grid gap-3 lg:grid-cols-3">
                        {identityProviderSettings.provider_statuses.map((status) => {
                            const allReady = status.request_mapping_ready && status.complete_mapping_ready;
                            return (
                                <div key={status.provider} className={`rounded-xl border p-4 ${allReady ? 'border-emerald-200 bg-white text-emerald-900' : 'border-amber-200 bg-white text-amber-900'}`}>
                                    <div className="flex items-center justify-between gap-2">
                                        <h3 className="text-sm font-semibold uppercase">{status.provider}</h3>
                                        <span className={`rounded-full border px-2 py-1 text-[11px] font-semibold ${allReady ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-amber-200 bg-amber-50 text-amber-700'}`}>
                                            {allReady ? 'request/complete 정상' : '설정 보강 필요'}
                                        </span>
                                    </div>
                                    <div className="mt-3 space-y-2 text-xs">
                                        <p className="break-all"><span className="font-semibold">endpoint:</span> {status.endpoint || '-'}</p>
                                        <p className="break-all"><span className="font-semibold">callback:</span> {status.callback_url || '-'}</p>
                                        <p><span className="font-semibold">request mapping:</span> {status.request_mapping_ready ? 'ready' : 'pending'}</p>
                                        <p><span className="font-semibold">complete mapping:</span> {status.complete_mapping_ready ? 'ready' : 'pending'}</p>
                                        <p><span className="font-semibold">환경 키:</span> {Object.values(identityProviderSettings.env_keys).join(', ')}</p>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                ) : (
                    <div className="mt-4 rounded-lg border border-dashed border-violet-300 bg-white px-4 py-3 text-xs text-violet-900/80">
                        identity provider 운영 상태를 아직 불러오지 못했습니다. 아래 전역 .env 설정 패널에서 새로고침 후 다시 확인하세요.
                    </div>
                )}
            </div>
        </>
    );
}
