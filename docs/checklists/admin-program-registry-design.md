# 관리자 대시보드 프로그램 레지스트리 설계안

## 문서 목적

- 이 문서는 관리자 대시보드를 개별 프로그램을 병렬 관리하는 운영 허브로 확장하기 위한 설계 기준을 정리한다.
- 이 문서는 기존 관리자 레일 구조를 크게 바꾸지 않고, 중앙에 프로그램 레지스트리와 프로그램별 작업공간을 추가하는 최소 변경안을 제시한다.
- 이 문서는 로컬 개발 편의보다 운영 반영 일치와 증거 기반 완료를 우선한다.

## 결론

- 레일 분리 자체가 복잡한 것이 아니라, 레일을 프로그램별로 쪼개려 할 때 복잡해진다.
- 따라서 기존 좌/우 레일은 유지하고, 중앙 영역에 프로그램 레지스트리와 상세 작업공간을 추가하는 구조가 가장 안전하다.
- 전역 운영 패널과 프로그램별 운영 패널을 분리하면 UI/UX 변경 폭은 작고, 운영 확장성은 높다.

## 우선 규칙

- 운영 기준 SSOT가 로컬 기준보다 우선한다.
- 선언하지 않은 표면은 수정하지 않은 것으로 간주한다.
- 코드 수정만으로 완료 처리하지 않는다.
- 운영 서버에서 실제 확인되지 않으면 완료로 닫지 않는다.
- 전역 설정과 프로그램별 설정을 섞지 않는다.

## 현재 구조 기준 해석

- [frontend/frontend/app/admin/page.tsx](../../frontend/frontend/app/admin/page.tsx) 는 관리자 대시보드의 최상위 조립 지점이다.
- [frontend/frontend/app/admin/admin-dashboard-sections-config.tsx](../../frontend/frontend/app/admin/admin-dashboard-sections-config.tsx) 는 현재 카드/섹션 조립 지점이다.
- [frontend/frontend/app/admin/admin-page-types.ts](../../frontend/frontend/app/admin/admin-page-types.ts) 는 관리자 섹션과 패널 props 계약의 SSOT에 가깝다.
- [frontend/frontend/lib/admin-system-settings-service.ts](../../frontend/frontend/lib/admin-system-settings-service.ts) 는 전역 운영 설정의 SSOT 성격을 가진다.

## 권장 UI/UX 구조

### 1. 상단: 프로그램 레지스트리

- 목적: 사용자가 현재 어떤 프로그램을 관리 중인지 먼저 인지하게 한다.
- 형태: 가로 카드형 레지스트리 또는 2열/3열 카드 보드.
- 카드 내용:
  - program_name: 사용자 표시명
  - program_key: 내부 식별자
  - program_type: APK / Web / Service / Console
  - primary_domain: 운영 기본 도메인
  - admin_domain: 관리자 전용 도메인
  - api_base_url: 연결 API 기준 주소
  - latest_version: 현재 버전 또는 빌드 번호
  - build_status: queued / building / passed / failed
  - deploy_status: pending / deployed / rollback / blocked
  - verification_status: not_run / running / passed / failed
  - owner_team: 담당 팀 또는 담당자
  - target_platform: Android / Web / Hybrid / Backend
  - latest_release_channel: dev / staging / production
  - operator_notes: 운영 메모 한 줄
- 카드 클릭 시 해당 프로그램의 상세 작업공간으로 전환한다.

### 2. 중앙: 프로그램 상세 작업공간

- 목적: 선택된 프로그램 하나의 설정, 빌드, 배포, 검증, 오류를 집중 관리한다.
- 포함 항목:
  - program summary header: 선택된 프로그램명, 버전, 도메인, 책임자
  - configuration panel: 프로그램 전용 설정과 환경값
  - build panel: 현재 빌드 상태, 마지막 빌드 결과, 빌드 재실행
  - deploy panel: 배포 대상, 배포 결과, 롤백 버튼
  - verify panel: 운영 검증 링크, 최근 검증 결과, 실검증 체크
  - artifacts panel: APK/ZIP/로그/리포트 경로
  - docs panel: 해당 프로그램의 운영 문서 링크
  - failure panel: 최근 실패 로그와 원인 분류
- 이 영역은 프로그램에 따라 내용이 바뀌며, 전역 공통 패널과 분리한다.

### 3. 좌측 레일: 전역 운영 도구

- 목적: 인증, 정책, 공통 시스템 설정, 공통 로그, 공통 상태를 관리한다.
- 유지 항목 예시:
  - ADMIN CONTROL HUB
  - 관리자 자동 건강상태 / 자가진단
  - self auto-connect graph
  - 전역 설정
  - 공통 로그
- 레일은 그대로 유지하고, 프로그램별 진입점만 추가한다.

### 4. 우측 레일: 빠른 전환 및 실행

- 목적: 자주 여는 화면, 최근 프로그램, 최근 검증, 운영 바로가기를 둔다.
- 유지 항목 예시:
  - 빠른 이동
  - 운영 중인 프로그램 목록
  - 최근 배포/검증
  - 문제 프로그램 고정 핀

### 5. 실제 섹션 순서

아래 순서로 배치하면 기존 레일 구조를 거의 유지하면서도 프로그램 병렬 관리가 가능하다.

1. 운영자 세션 / 핵심 지표 사이에 `프로그램 레지스트리` 카드 보드 추가
2. `선택된 프로그램 요약` 카드 추가
3. `build/deploy/verify` 상태 패널 추가
4. `전역 .env 설정 패널` 유지
5. `전역 건강상태 / 자가진단` 유지
6. `self auto-connect graph` 유지
7. `관리자 수동 오케스트레이션` 유지
8. `카테고리 / 주문 / 구독 / 비용` 같은 기존 운영 패널은 하단에 유지
9. 우측 레일은 `빠른 이동` + `최근 프로그램` + `최근 검증` + `문제 프로그램 핀`만 정리

### 6. 현재 코드에 붙이는 최소 침투 지점

- [frontend/frontend/app/admin/page.tsx](../../frontend/frontend/app/admin/page.tsx)
  - 현재 `adminSidebar` 위 또는 아래에 `program registry` 블록을 추가한다.
  - 선택 상태 `selectedProgramKey` 를 추가하고, 선택된 프로그램에 따라 중앙 상세 패널이 바뀌게 한다.
- [frontend/frontend/app/admin/admin-dashboard-sections-config.tsx](../../frontend/frontend/app/admin/admin-dashboard-sections-config.tsx)
  - 기존 `admin-control` 아래에 `program-registry` 섹션을 추가한다.
  - 선택 프로그램이 있을 때만 렌더되는 `program-detail` 섹션을 별도로 둔다.
- [frontend/frontend/app/admin/admin-page-types.ts](../../frontend/frontend/app/admin/admin-page-types.ts)
  - `AdminProgramRegistryItem`, `AdminProgramRegistryDetail`, `AdminProgramRegistrySectionProps` 타입을 추가한다.

### 7. `admin/page.tsx` 컴포넌트 배치 초안

아래 순서로 두면 기존 레일 구조를 유지하면서 프로그램 병렬 관리층만 추가할 수 있다.

```tsx
export default function AdminDashboardPage() {
  // 전역 상태
  const apiBaseUrl = resolveApiBaseUrl();
  const [selectedProgramKey, setSelectedProgramKey] = React.useState<string>('marketplace');

  // 전역 운영 데이터
  const { systemSettings, dashboardAnalysis, ... } = useAdminPageState();
  const adminSystemSettingsAssembly = buildAdminPageSystemSettingsAssembly(...);

  // 프로그램 레지스트리
  const programRegistry = useAdminProgramRegistry(apiBaseUrl);
  const selectedProgram = React.useMemo(
    () => programRegistry.items.find((item) => item.program_key === selectedProgramKey) || null,
    [programRegistry.items, selectedProgramKey],
  );

  const programRegistryBoard = buildAdminProgramRegistryBoard({
    programRegistry,
    selectedProgramKey,
    onSelectProgramKey: setSelectedProgramKey,
    onRefreshRegistry: programRegistry.reload,
  });

  const programDetailAssembly = buildAdminProgramDetailAssembly({
    program: selectedProgram,
    apiBaseUrl,
    onRefreshProgram: programRegistry.reloadOne,
    onRunProgramCheck: programRegistry.runCheck,
    onRollbackProgram: programRegistry.rollback,
    onOpenArtifacts: programRegistry.openArtifacts,
  });

  const boardSections = buildAdminDashboardSectionsConfig({ ... });

  return (
    <WorkspaceChrome ...>
      <div className="admin-dark-shell">
        <section className="admin-program-registry-strip">
          <AdminProgramRegistryStrip
            items={programRegistry.items}
            selectedProgramKey={selectedProgramKey}
            onSelectProgramKey={setSelectedProgramKey}
            onRefresh={programRegistry.reload}
          />
        </section>

        <section className="admin-program-detail-stage">
          <AdminProgramSummaryCard program={selectedProgram} />
          <AdminProgramDetailPanel {...programDetailAssembly} />
        </section>

        <section className="admin-global-ops-stage">
          <AdminManagementSection title="🧭 전역 .env 설정 패널" ...>
            <AdminSystemSettingsPanel {...adminSystemSettingsAssemblyWithGuard} />
          </AdminManagementSection>
          {boardSections.map((section) => (
            <AdminManagementSection key={section.id} ...>
              {section.body}
            </AdminManagementSection>
          ))}
        </section>
      </div>
    </WorkspaceChrome>
  );
}
```

#### 렌더 순서 원칙

- `adminSidebar` 는 전역 상태 요약으로 유지한다.
- 프로그램 레지스트리 스트립은 `adminSidebar` 바로 아래 첫 작업 영역에 둔다.
- 선택 프로그램 요약 카드와 상세 패널은 `boardSections` 보다 먼저 렌더링한다.
- 전역 패널은 기존 순서를 유지한다.
- 프로그램 상세 패널은 하나만 렌더한다.
- 우측 레일은 변화 없이 유지한다.

#### 화면 흐름 초안

1. 로그인 상태와 핵심 지표를 먼저 본다.
2. 프로그램 카드를 하나 선택한다.
3. 선택한 프로그램의 요약과 상세 작업공간이 중앙에 열린다.
4. 전역 설정과 운영 패널은 그 아래에서 유지된다.
5. 레일에서 빠르게 다른 프로그램이나 전역 패널로 전환한다.

### 8. `admin/page.tsx`에 들어갈 실제 컴포넌트 이름과 props

아래 이름은 현재 코드베이스의 `Admin*` 명명 규칙과 맞춘 제안안이다.

#### A. 프로그램 레지스트리 스트립

- 컴포넌트명: `AdminProgramRegistryStrip`
- 역할: 화면 상단에서 프로그램 목록을 카드 형태로 보여주고, 선택 상태를 바꾼다.
- props:
  - `items: AdminProgramRegistryItem[]`
  - `selectedProgramKey: string`
  - `onSelectProgramKey: (programKey: string) => void`
  - `onRefresh: () => void | Promise<void>`
  - `loading?: boolean`
  - `error?: string | null`

#### B. 선택 프로그램 요약 카드

- 컴포넌트명: `AdminProgramSummaryCard`
- 역할: 선택된 프로그램의 핵심 정보를 짧게 요약한다.
- props:
  - `program: AdminProgramRegistryDetail | null`
  - `selected: boolean`
  - `onOpenDocs: () => void`
  - `onOpenArtifacts: () => void`
  - `onOpenDeployments: () => void`

#### C. 프로그램 상세 작업공간

- 컴포넌트명: `AdminProgramDetailPanel`
- 역할: 선택된 프로그램의 build/deploy/verify/operate 패널을 한 화면에 담는다.
- props:
  - `program: AdminProgramRegistryDetail | null`
  - `apiBaseUrl: string`
  - `onRefreshProgram: (programKey: string) => void | Promise<void>`
  - `onRunProgramCheck: (programKey: string) => void | Promise<void>`
  - `onRollbackProgram: (programKey: string) => void | Promise<void>`
  - `onApproveProgram: (programKey: string) => void | Promise<void>`
  - `onOpenArtifacts: (programKey: string) => void | Promise<void>`
  - `onOpenDocs: (programKey: string) => void | Promise<void>`
  - `busy?: boolean`
  - `error?: string | null`

#### D. 프로그램 상태 바

- 컴포넌트명: `AdminProgramStatusBar`
- 역할: build / deploy / verify / operate 상태를 한 줄로 보여준다.
- props:
  - `buildStatus: string`
  - `deployStatus: string`
  - `verificationStatus: string`
  - `latestVersion?: string | null`
  - `latestBuildId?: string | null`
  - `latestReleaseChannel?: string | null`

#### E. 프로그램 산출물 패널

- 컴포넌트명: `AdminProgramArtifactPanel`
- 역할: APK, ZIP, 로그, 리포트 경로를 노출한다.
- props:
  - `artifacts: Array<{ label: string; href: string; kind: 'apk' | 'zip' | 'log' | 'report' }>`
  - `onOpenArtifact: (href: string) => void`

#### F. 프로그램 검증 패널

- 컴포넌트명: `AdminProgramVerificationPanel`
- 역할: 운영 실검증 결과와 최근 체크를 보여준다.
- props:
  - `checks: Array<{ id: string; title: string; status: 'passed' | 'failed' | 'running' | 'manual'; detail?: string }>`
  - `onRunCheck: () => void | Promise<void>`
  - `loading?: boolean`
  - `error?: string | null`

#### G. 프로그램 레지스트리 보드 조립 함수

- 함수명: `buildAdminProgramRegistryBoard`
- 역할: 프로그램 카드 목록과 선택 상태를 묶어 스트립에 넘긴다.
- 입력 props:
  - `programRegistry: AdminProgramRegistryState`
  - `selectedProgramKey: string`
  - `onSelectProgramKey: (programKey: string) => void`
  - `onRefreshRegistry: () => void | Promise<void>`

#### H. 프로그램 상세 조립 함수

- 함수명: `buildAdminProgramDetailAssembly`
- 역할: 선택된 프로그램에 맞는 상세 패널 props를 생성한다.
- 입력 props:
  - `program: AdminProgramRegistryDetail | null`
  - `apiBaseUrl: string`
  - `onRefreshProgram: (programKey: string) => void | Promise<void>`
  - `onRunProgramCheck: (programKey: string) => void | Promise<void>`
  - `onRollbackProgram: (programKey: string) => void | Promise<void>`
  - `onApproveProgram: (programKey: string) => void | Promise<void>`
  - `onOpenArtifacts: (programKey: string) => void | Promise<void>`
  - `onOpenDocs: (programKey: string) => void | Promise<void>`

### 9. `admin/page.tsx`에 들어가는 상태 변수 초안

- `selectedProgramKey`
- `programRegistryLoading`
- `programRegistryError`
- `programRegistryItems`
- `programRegistryUpdatedAt`
- `programDetailBusyId`
- `programDetailError`
- `programDetailActionMessage`
- `programDetailChecks`
- `programDetailArtifacts`

### 10. 최소 구현 우선순위

1. `AdminProgramRegistryStrip`
2. `AdminProgramSummaryCard`
3. `AdminProgramDetailPanel`
4. `AdminProgramStatusBar`
5. `AdminProgramArtifactPanel`
6. `AdminProgramVerificationPanel`

이 순서로 구현하면 화면이 먼저 살아나고, 이후 API와 검증이 뒤에서 붙는다.

### 11. `admin-page-types.ts`에 들어갈 타입 초안

아래 타입은 `admin/page.tsx`와 `admin-dashboard-sections-config.tsx`가 공유할 최소 계약이다.

```ts
export type AdminProgramRegistryStatus = 'queued' | 'building' | 'passed' | 'failed' | 'pending' | 'deployed' | 'rollback' | 'blocked' | 'not_run' | 'running' | 'manual';

export type AdminProgramRegistryItem = {
  program_id: string;
  program_key: string;
  program_name: string;
  program_type: 'apk' | 'web' | 'service' | 'console';
  primary_domain: string;
  admin_domain?: string | null;
  api_base_url: string;
  target_platform: 'android' | 'web' | 'backend' | 'hybrid';
  build_status: AdminProgramRegistryStatus;
  deploy_status: AdminProgramRegistryStatus;
  verification_status: AdminProgramRegistryStatus;
  latest_version?: string | null;
  latest_build_id?: string | null;
  latest_release_channel?: 'dev' | 'staging' | 'production' | null;
  owner_team?: string | null;
  operator_notes?: string | null;
  docs_links?: Array<{ label: string; href: string }>;
};

export type AdminProgramRegistryArtifact = {
  label: string;
  href: string;
  kind: 'apk' | 'zip' | 'log' | 'report' | 'manifest' | 'doc';
};

export type AdminProgramRegistryCheck = {
  id: string;
  title: string;
  status: 'passed' | 'failed' | 'running' | 'manual';
  detail?: string | null;
  checked_at?: string | null;
};

export type AdminProgramRegistryDetail = AdminProgramRegistryItem & {
  summary?: string | null;
  build_message?: string | null;
  deploy_message?: string | null;
  verify_message?: string | null;
  artifacts: AdminProgramRegistryArtifact[];
  checks: AdminProgramRegistryCheck[];
  related_docs: Array<{ label: string; href: string }>;
};

export type AdminProgramRegistryState = {
  items: AdminProgramRegistryItem[];
  selectedProgramKey: string;
  updatedAt?: string | null;
  loading: boolean;
  error?: string | null;
};

export type AdminProgramRegistrySectionProps = {
  registry: AdminProgramRegistryState;
  onSelectProgramKey: (programKey: string) => void;
  onRefreshRegistry: () => void | Promise<void>;
};

export type AdminProgramSummaryCardProps = {
  program: AdminProgramRegistryDetail | null;
  selected: boolean;
  onOpenDocs: () => void;
  onOpenArtifacts: () => void;
  onOpenDeployments: () => void;
};

export type AdminProgramDetailPanelProps = {
  program: AdminProgramRegistryDetail | null;
  apiBaseUrl: string;
  onRefreshProgram: (programKey: string) => void | Promise<void>;
  onRunProgramCheck: (programKey: string) => void | Promise<void>;
  onRollbackProgram: (programKey: string) => void | Promise<void>;
  onApproveProgram: (programKey: string) => void | Promise<void>;
  onOpenArtifacts: (programKey: string) => void | Promise<void>;
  onOpenDocs: (programKey: string) => void | Promise<void>;
  busy?: boolean;
  error?: string | null;
};

export type AdminProgramStatusBarProps = {
  buildStatus: AdminProgramRegistryStatus;
  deployStatus: AdminProgramRegistryStatus;
  verificationStatus: AdminProgramRegistryStatus;
  latestVersion?: string | null;
  latestBuildId?: string | null;
  latestReleaseChannel?: string | null;
};

export type AdminProgramArtifactPanelProps = {
  artifacts: AdminProgramRegistryArtifact[];
  onOpenArtifact: (href: string) => void;
};

export type AdminProgramVerificationPanelProps = {
  checks: AdminProgramRegistryCheck[];
  onRunCheck: () => void | Promise<void>;
  loading?: boolean;
  error?: string | null;
};
```

#### 타입 설계 원칙

- 공통 상태 문자열은 하나의 union 으로 통일한다.
- `detail` 은 화면용 확장 타입이고, 목록에는 `AdminProgramRegistryItem` 만 쓴다.
- `props` 는 섹션 단위로 쪼개서 `page.tsx` 의 state 폭발을 막는다.
- 전역 설정 타입과 프로그램 레지스트리 타입을 섞지 않는다.

#### `admin-page-types.ts`에 추가할 최소 순서

1. `AdminProgramRegistryStatus`
2. `AdminProgramRegistryItem`
3. `AdminProgramRegistryArtifact`
4. `AdminProgramRegistryCheck`
5. `AdminProgramRegistryDetail`
6. `AdminProgramRegistryState`
7. `AdminProgramRegistrySectionProps`
8. `AdminProgramSummaryCardProps`
9. `AdminProgramDetailPanelProps`
10. `AdminProgramStatusBarProps`
11. `AdminProgramArtifactPanelProps`
12. `AdminProgramVerificationPanelProps`

이 순서대로 넣으면 목록 → 상세 → 검증 → 산출물 순으로 자연스럽게 연결된다.

### 12. 백엔드 API DTO 초안

아래 DTO는 `backend/admin_router.py` 에 추가할 프로그램 레지스트리 계층의 최소 계약이다.

```py
class AdminProgramRegistrySummaryResponse(BaseModel):
    program_id: str
    program_key: str
    program_name: str
    program_type: str
    primary_domain: str
    admin_domain: str | None = None
    api_base_url: str
    target_platform: str
    build_status: str
    deploy_status: str
    verification_status: str
    latest_version: str | None = None
    latest_build_id: str | None = None
    latest_release_channel: str | None = None
    owner_team: str | None = None
    operator_notes: str | None = None
    docs_links: list[dict[str, str]] = Field(default_factory=list)


class AdminProgramRegistryArtifactResponse(BaseModel):
    label: str
    href: str
    kind: str


class AdminProgramRegistryCheckResponse(BaseModel):
    id: str
    title: str
    status: str
    detail: str | None = None
    checked_at: str | None = None


class AdminProgramRegistryDetailResponse(AdminProgramRegistrySummaryResponse):
    summary: str | None = None
    build_message: str | None = None
    deploy_message: str | None = None
    verify_message: str | None = None
    artifacts: list[AdminProgramRegistryArtifactResponse] = Field(default_factory=list)
    checks: list[AdminProgramRegistryCheckResponse] = Field(default_factory=list)
    related_docs: list[dict[str, str]] = Field(default_factory=list)


class AdminProgramRegistryStateResponse(BaseModel):
    items: list[AdminProgramRegistrySummaryResponse] = Field(default_factory=list)
    selected_program_key: str
    updated_at: str | None = None
    loading: bool = False
    error: str | None = None


class AdminProgramRegistryStatusUpdateRequest(BaseModel):
    build_status: str | None = None
    deploy_status: str | None = None
    verification_status: str | None = None
    latest_version: str | None = None
    latest_build_id: str | None = None
    latest_release_channel: str | None = None
    operator_notes: str | None = None


class AdminProgramRegistryCheckRunRequest(BaseModel):
    program_key: str
    check_scope: str = 'operational'
    force: bool = False


class AdminProgramRegistryRollbackRequest(BaseModel):
    program_key: str
    reason: str | None = None


class AdminProgramRegistryApproveRequest(BaseModel):
    program_key: str
    approved_by: str | None = None
    note: str | None = None
```

#### 백엔드 라우트 매핑 초안

- `GET /api/admin/program-registry`
  - `AdminProgramRegistryStateResponse`
- `GET /api/admin/program-registry/{program_id}`
  - `AdminProgramRegistryDetailResponse`
- `PUT /api/admin/program-registry/{program_id}`
  - `AdminProgramRegistryStatusUpdateRequest`
- `PATCH /api/admin/program-registry/{program_id}/status`
  - `AdminProgramRegistryStatusUpdateRequest`
- `GET /api/admin/program-registry/{program_id}/builds`
  - `list[dict[str, Any]]` 또는 별도 `AdminProgramBuildResponse`
- `GET /api/admin/program-registry/{program_id}/deployments`
  - `list[dict[str, Any]]` 또는 별도 `AdminProgramDeploymentResponse`
- `GET /api/admin/program-registry/{program_id}/checks`
  - `list[AdminProgramRegistryCheckResponse]`
- `POST /api/admin/program-registry/{program_id}/checks/run`
  - `AdminProgramRegistryCheckRunRequest`
- `GET /api/admin/program-registry/{program_id}/artifacts`
  - `list[AdminProgramRegistryArtifactResponse]`
- `GET /api/admin/program-registry/{program_id}/docs`
  - `list[dict[str, str]]`
- `POST /api/admin/program-registry/{program_id}/approve`
  - `AdminProgramRegistryApproveRequest`
- `POST /api/admin/program-registry/{program_id}/rollback`
  - `AdminProgramRegistryRollbackRequest`

#### `admin_router.py` 함수명 초안

기존 `admin_router.py`의 `get_admin_*`, `update_admin_*`, `list_admin_*`, `approve_admin_*`, `post_admin_*` 패턴을 그대로 따른다.

- `list_admin_program_registry`
  - `GET /api/admin/program-registry`
  - 역할: 프로그램 목록/요약 상태 반환
- `get_admin_program_registry`
  - `GET /api/admin/program-registry/{program_id}`
  - 역할: 선택 프로그램 상세 반환
- `update_admin_program_registry`
  - `PUT /api/admin/program-registry/{program_id}`
  - 역할: 프로그램 메타/상태 갱신
- `update_admin_program_registry_status`
  - `PATCH /api/admin/program-registry/{program_id}/status`
  - 역할: build/deploy/verify 상태만 부분 갱신
- `list_admin_program_registry_builds`
  - `GET /api/admin/program-registry/{program_id}/builds`
  - 역할: 빌드 히스토리 반환
- `list_admin_program_registry_deployments`
  - `GET /api/admin/program-registry/{program_id}/deployments`
  - 역할: 배포 히스토리 반환
- `list_admin_program_registry_checks`
  - `GET /api/admin/program-registry/{program_id}/checks`
  - 역할: 검증/실검증 결과 반환
- `post_admin_program_registry_check_run`
  - `POST /api/admin/program-registry/{program_id}/checks/run`
  - 역할: 운영 검증 실행 요청
- `list_admin_program_registry_artifacts`
  - `GET /api/admin/program-registry/{program_id}/artifacts`
  - 역할: APK/ZIP/로그/리포트 산출물 반환
- `list_admin_program_registry_docs`
  - `GET /api/admin/program-registry/{program_id}/docs`
  - 역할: 운영 문서 링크 반환
- `approve_admin_program_registry`
  - `POST /api/admin/program-registry/{program_id}/approve`
  - 역할: 운영 반영 승인
- `rollback_admin_program_registry`
  - `POST /api/admin/program-registry/{program_id}/rollback`
  - 역할: 최근 배포 롤백 요청

#### 함수명 설계 원칙

- 목록은 `list_admin_*`
- 단건 조회는 `get_admin_*`
- 전체 갱신은 `update_admin_*`
- 부분 상태 갱신은 `update_admin_*_status`
- 실행형 요청은 `post_admin_*`
- 승인형 요청은 `approve_admin_*`
- 롤백형 요청은 `rollback_admin_*`

#### 선택 기준

- `program_id` 를 경로 변수로 쓰고, `program_key` 는 본문/내부 조회 키로 둔다.
- 목록 응답은 `summary` 중심, 상세 응답은 `detail` 중심으로 나눈다.
- 현재 `admin_router.py` 에 이미 존재하는 `get_admin_system_settings`, `update_admin_system_settings`, `list_admin_projects`, `update_admin_user` 같은 이름 패턴과 같은 수준의 명확성을 유지한다.

#### `admin_router.py` 실제 함수 시그니처 초안

아래 시그니처는 현재 `admin_router.py` 의 `admin: User = Depends(require_admin)`, `db: Session = Depends(get_db)` 패턴과 맞춘다.

```py
@router.get("/program-registry")
def list_admin_program_registry(
  admin: User = Depends(require_admin),
  db: Session = Depends(get_db),
) -> AdminProgramRegistryStateResponse:
  ...


@router.get("/program-registry/{program_id}")
def get_admin_program_registry(
  program_id: str,
  admin: User = Depends(require_admin),
  db: Session = Depends(get_db),
) -> AdminProgramRegistryDetailResponse:
  ...


@router.put("/program-registry/{program_id}")
def update_admin_program_registry(
  program_id: str,
  payload: AdminProgramRegistryStatusUpdateRequest,
  admin: User = Depends(require_admin),
  db: Session = Depends(get_db),
) -> AdminProgramRegistryDetailResponse:
  ...


@router.patch("/program-registry/{program_id}/status")
def update_admin_program_registry_status(
  program_id: str,
  payload: AdminProgramRegistryStatusUpdateRequest,
  admin: User = Depends(require_admin),
  db: Session = Depends(get_db),
) -> AdminProgramRegistrySummaryResponse:
  ...


@router.get("/program-registry/{program_id}/builds")
def list_admin_program_registry_builds(
  program_id: str,
  admin: User = Depends(require_admin),
  db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
  ...


@router.get("/program-registry/{program_id}/deployments")
def list_admin_program_registry_deployments(
  program_id: str,
  admin: User = Depends(require_admin),
  db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
  ...


@router.get("/program-registry/{program_id}/checks")
def list_admin_program_registry_checks(
  program_id: str,
  admin: User = Depends(require_admin),
  db: Session = Depends(get_db),
) -> list[AdminProgramRegistryCheckResponse]:
  ...


@router.post("/program-registry/{program_id}/checks/run")
def post_admin_program_registry_check_run(
  program_id: str,
  payload: AdminProgramRegistryCheckRunRequest,
  admin: User = Depends(require_admin),
  db: Session = Depends(get_db),
) -> dict[str, Any]:
  ...


@router.get("/program-registry/{program_id}/artifacts")
def list_admin_program_registry_artifacts(
  program_id: str,
  admin: User = Depends(require_admin),
  db: Session = Depends(get_db),
) -> list[AdminProgramRegistryArtifactResponse]:
  ...


@router.get("/program-registry/{program_id}/docs")
def list_admin_program_registry_docs(
  program_id: str,
  admin: User = Depends(require_admin),
  db: Session = Depends(get_db),
) -> list[dict[str, str]]:
  ...


@router.post("/program-registry/{program_id}/approve")
def approve_admin_program_registry(
  program_id: str,
  payload: AdminProgramRegistryApproveRequest,
  admin: User = Depends(require_admin),
  db: Session = Depends(get_db),
) -> AdminProgramRegistryDetailResponse:
  ...


@router.post("/program-registry/{program_id}/rollback")
def rollback_admin_program_registry(
  program_id: str,
  payload: AdminProgramRegistryRollbackRequest,
  admin: User = Depends(require_admin),
  db: Session = Depends(get_db),
) -> AdminProgramRegistryDetailResponse:
  ...
```

#### `backend/admin_router.py` 모델명 정리

- `AdminProgramRegistrySummaryResponse`
- `AdminProgramRegistryArtifactResponse`
- `AdminProgramRegistryCheckResponse`
- `AdminProgramRegistryDetailResponse`
- `AdminProgramRegistryStateResponse`
- `AdminProgramRegistryStatusUpdateRequest`
- `AdminProgramRegistryCheckRunRequest`
- `AdminProgramRegistryRollbackRequest`
- `AdminProgramRegistryApproveRequest`

#### `admin_router.py` 내부 helper 함수 이름 초안

기존 `admin_router.py`의 `_build_*`, `_load_*`, `_save_*`, `_serialize_*` 패턴과 동일하게 맞춘다.

- `_build_admin_program_registry_summary_item(program: Any) -> Dict[str, Any]`
  - 목록용 summary 1건 직렬화
- `_build_admin_program_registry_state_payload(db: Session) -> Dict[str, Any]`
  - 목록 응답 본문 조립
- `_build_admin_program_registry_detail_payload(db: Session, program_id: str) -> Dict[str, Any]`
  - 상세 응답 본문 조립
- `_load_admin_program_registry_rows(db: Session) -> List[Any]`
  - 프로그램 원본 row 조회
- `_load_admin_program_registry_row(db: Session, program_id: str) -> Any | None`
  - 단건 row 조회
- `_save_admin_program_registry_row(db: Session, program_id: str, payload: AdminProgramRegistryStatusUpdateRequest) -> Any`
  - status/meta 저장
- `_build_admin_program_registry_builds_payload(db: Session, program_id: str) -> List[Dict[str, Any]]`
  - 빌드 히스토리 조립
- `_build_admin_program_registry_deployments_payload(db: Session, program_id: str) -> List[Dict[str, Any]]`
  - 배포 히스토리 조립
- `_build_admin_program_registry_checks_payload(db: Session, program_id: str) -> List[Dict[str, Any]]`
  - 검증/실검증 기록 조립
- `_build_admin_program_registry_artifacts_payload(db: Session, program_id: str) -> List[Dict[str, Any]]`
  - 산출물 목록 조립
- `_build_admin_program_registry_docs_payload(db: Session, program_id: str) -> List[Dict[str, str]]`
  - 문서 링크 목록 조립
- `_build_admin_program_registry_check_run_payload(db: Session, program_id: str, payload: AdminProgramRegistryCheckRunRequest) -> Dict[str, Any]`
  - 검증 실행 결과 payload 조립
- `_build_admin_program_registry_approve_payload(db: Session, program_id: str, payload: AdminProgramRegistryApproveRequest, admin: User) -> Dict[str, Any]`
  - 승인 결과 payload 조립
- `_build_admin_program_registry_rollback_payload(db: Session, program_id: str, payload: AdminProgramRegistryRollbackRequest, admin: User) -> Dict[str, Any]`
  - 롤백 결과 payload 조립
- `_serialize_admin_program_registry_artifact(item: Any) -> Dict[str, Any]`
  - 산출물 개별 직렬화
- `_serialize_admin_program_registry_check(item: Any) -> Dict[str, Any]`
  - 검증 기록 개별 직렬화

#### helper 함수 설계 원칙

- `_build_*` 는 응답 payload 조립만 책임진다.
- `_load_*` 는 DB/파일에서 읽기만 한다.
- `_save_*` 는 DB/파일 저장만 한다.
- `_serialize_*` 는 ORM/내부 객체를 API 응답 dict 로 바꾼다.
- write API 는 helper에서 실제 검증/저장을 마친 뒤 router 에서 response model 로 반환한다.

#### helper 구현 순서

1. `_load_admin_program_registry_row`
2. `_load_admin_program_registry_rows`
3. `_serialize_admin_program_registry_summary_item`
4. `_build_admin_program_registry_state_payload`
5. `_build_admin_program_registry_detail_payload`
6. `_build_admin_program_registry_checks_payload`
7. `_build_admin_program_registry_artifacts_payload`
8. `_build_admin_program_registry_docs_payload`
9. `_save_admin_program_registry_row`
10. `_build_admin_program_registry_check_run_payload`
11. `_build_admin_program_registry_approve_payload`
12. `_build_admin_program_registry_rollback_payload`

이 순서대로 넣으면 read path 를 먼저 열고, write path 를 나중에 닫을 수 있다.

#### `backend/admin_router.py` 실제 import 목록 초안

아래 import 는 현재 `admin_router.py` 상단의 import 분리 방식과 맞춘다.

```py
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.auth import require_admin
from backend.database import get_db
from backend.models import User
from backend.time_utils import utcnow
```

#### 프로그램 레지스트리 전용 내부 helper import 초안

`admin_router.py` 가 직접 선언하지 않고 다른 서비스 모듈로 분리할 경우의 최소 import 는 아래와 같다.

```py
from backend.admin.program_registry_service import (
    build_admin_program_registry_state_payload,
    build_admin_program_registry_detail_payload,
    build_admin_program_registry_builds_payload,
    build_admin_program_registry_deployments_payload,
    build_admin_program_registry_checks_payload,
    build_admin_program_registry_artifacts_payload,
    build_admin_program_registry_docs_payload,
    build_admin_program_registry_check_run_payload,
    build_admin_program_registry_approve_payload,
    build_admin_program_registry_rollback_payload,
    load_admin_program_registry_rows,
    load_admin_program_registry_row,
    save_admin_program_registry_row,
    serialize_admin_program_registry_summary_item,
    serialize_admin_program_registry_artifact,
    serialize_admin_program_registry_check,
)
```

#### import 설계 원칙

- 공통 프레임워크 import 는 `fastapi`, `pydantic`, `sqlalchemy` 순으로 둔다.
- 공통 인증/DB import 는 `backend.auth`, `backend.database`, `backend.models`, `backend.time_utils` 순으로 둔다.
- 프로그램 레지스트리 전용 로직은 가능하면 별도 service 모듈로 분리한다.
- router 파일은 가능한 얇게 유지하고, payload 조립과 저장은 helper/service 로 넘긴다.
- `Query` 와 `Request` 는 실제 사용이 있을 때만 남기고, 사용하지 않으면 import 하지 않는다.

#### import 정리 우선순위

1. 공통 프레임워크 import
2. 인증 / DB / 모델 import
3. 기존 admin 기능 import
4. 프로그램 레지스트리 전용 service import
5. router 내부 helper 사용 여부 최종 결정

#### `admin_router.py` 실제 코드 스켈레톤 import 블록

아래 블록은 실제 `admin_router.py` 상단에 들어가는 형태를 가장 단순하게 보여준다.

```py
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from backend.auth import require_admin
from backend.database import get_db
from backend.models import User
from backend.admin.program_registry_service import (
    build_admin_program_registry_state_payload,
    build_admin_program_registry_detail_payload,
    build_admin_program_registry_builds_payload,
    build_admin_program_registry_deployments_payload,
    build_admin_program_registry_checks_payload,
    build_admin_program_registry_artifacts_payload,
    build_admin_program_registry_docs_payload,
    build_admin_program_registry_check_run_payload,
    build_admin_program_registry_approve_payload,
    build_admin_program_registry_rollback_payload,
    load_admin_program_registry_row,
    load_admin_program_registry_rows,
    save_admin_program_registry_row,
    serialize_admin_program_registry_summary_item,
    serialize_admin_program_registry_artifact,
    serialize_admin_program_registry_check,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])
```

#### `backend/admin/` 분리 파일명 제안

이 기능은 `admin_router.py`에 너무 많은 helper가 몰리는 구조를 피하고, 아래처럼 분리하는 것이 가장 안전하다.

- `backend/admin/__init__.py`
- `backend/admin/program_registry_service.py`
- `backend/admin/program_registry_models.py`
- `backend/admin/program_registry_types.py`
- `backend/admin/program_registry_validators.py`

추천 조합은 다음 두 가지다.

1. 최소 분리: `program_registry_service.py` + `program_registry_models.py`
2. 엄격 분리: `program_registry_service.py` + `program_registry_types.py` + `program_registry_validators.py`

서비스 파일 후보는 아래와 같은 함수 그룹을 담당한다.

```py
# backend/admin/program_registry_service.py

def load_admin_program_registry_row(...):
    ...

def load_admin_program_registry_rows(...):
    ...

def save_admin_program_registry_row(...):
    ...

def build_admin_program_registry_state_payload(...):
    ...

def build_admin_program_registry_detail_payload(...):
    ...

def build_admin_program_registry_checks_payload(...):
    ...

def build_admin_program_registry_artifacts_payload(...):
    ...

def build_admin_program_registry_docs_payload(...):
    ...

def build_admin_program_registry_check_run_payload(...):
    ...

def build_admin_program_registry_approve_payload(...):
    ...

def build_admin_program_registry_rollback_payload(...):
    ...
```

#### 분리 기준

- `admin_router.py` 는 route 에 대한 계약만 담당한다.
- `program_registry_service.py` 는 실제 DB 조회/저장/조립 로직을 담당한다.
- `program_registry_models.py` 는 DTO 및 상태 enum 정의를 담당한다.
- `program_registry_validators.py` 는 `program_id`, `program_key`, `status` 같은 입력 검증을 담당한다.

`admin_router.py` 상단은 스켈레톤 import 와 `APIRouter` 선언만 남기고, all heavy logic 은 service layer 로 넘기는 구조가 가장 안전하다.

#### `admin_router.py` 실제 route 함수 본문 스켈레톤

아래는 실제 `admin_router.py` 안에서 각 route 가 가져야 할 내부 흐름을 가장 근접한 형태로 적은 코드 스켈레톤이다.

```py
@router.get("/program-registry")
def list_admin_program_registry(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminProgramRegistryStateResponse:
    """프로그램 레지스트리 목록 조회"""
    rows = load_admin_program_registry_rows(db=db)
    items = [
        serialize_admin_program_registry_summary_item(row)
        for row in rows
    ]
    payload = build_admin_program_registry_state_payload(
        rows=rows,
        items=items,
    )
    return AdminProgramRegistryStateResponse(**payload)


@router.get("/program-registry/{program_id}")
def get_admin_program_registry(
    program_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminProgramRegistryDetailResponse:
    """단일 프로그램 상세 조회"""
    row = load_admin_program_registry_row(db=db, program_id=program_id)
    if row is None:
        raise HTTPException(status_code=404, detail="program not found")

    payload = build_admin_program_registry_detail_payload(
        db=db,
        program_id=program_id,
        row=row,
    )
    return AdminProgramRegistryDetailResponse(**payload)


@router.patch("/program-registry/{program_id}")
def update_admin_program_registry(
    program_id: str,
    payload: AdminProgramRegistryStatusUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminProgramRegistryDetailResponse:
    """프로그램 기본 메타/상태 업데이트"""
    row = load_admin_program_registry_row(db=db, program_id=program_id)
    if row is None:
        raise HTTPException(status_code=404, detail="program not found")

    updated_row = save_admin_program_registry_row(
        db=db,
        program_id=program_id,
        payload=payload,
        admin=admin,
    )
    detail_payload = build_admin_program_registry_detail_payload(
        db=db,
        program_id=program_id,
        row=updated_row,
    )
    return AdminProgramRegistryDetailResponse(**detail_payload)


@router.patch("/program-registry/{program_id}/status")
def update_admin_program_registry_status(
    program_id: str,
    payload: AdminProgramRegistryStatusUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminProgramRegistryDetailResponse:
    """상태만 변경하는 경량 업데이트"""
    row = load_admin_program_registry_row(db=db, program_id=program_id)
    if row is None:
        raise HTTPException(status_code=404, detail="program not found")

    updated_row = save_admin_program_registry_row(
        db=db,
        program_id=program_id,
        payload=payload,
        admin=admin,
    )
    detail_payload = build_admin_program_registry_detail_payload(
        db=db,
        program_id=program_id,
        row=updated_row,
    )
    return AdminProgramRegistryDetailResponse(**detail_payload)


@router.get("/program-registry/{program_id}/builds")
def list_admin_program_registry_builds(
    program_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[Dict[str, Any]]:
    """빌드 히스토리 조회"""
    row = load_admin_program_registry_row(db=db, program_id=program_id)
    if row is None:
        raise HTTPException(status_code=404, detail="program not found")
    return build_admin_program_registry_builds_payload(db=db, program_id=program_id)


@router.get("/program-registry/{program_id}/deployments")
def list_admin_program_registry_deployments(
    program_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[Dict[str, Any]]:
    """배포 히스토리 조회"""
    row = load_admin_program_registry_row(db=db, program_id=program_id)
    if row is None:
        raise HTTPException(status_code=404, detail="program not found")
    return build_admin_program_registry_deployments_payload(db=db, program_id=program_id)


@router.get("/program-registry/{program_id}/checks")
def list_admin_program_registry_checks(
    program_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[AdminProgramRegistryCheckResponse]:
    """검증 기록 조회"""
    row = load_admin_program_registry_row(db=db, program_id=program_id)
    if row is None:
        raise HTTPException(status_code=404, detail="program not found")

    items = build_admin_program_registry_checks_payload(db=db, program_id=program_id)
    return [AdminProgramRegistryCheckResponse(**item) for item in items]


@router.post("/program-registry/{program_id}/checks/run")
def post_admin_program_registry_check_run(
    program_id: str,
    payload: AdminProgramRegistryCheckRunRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminProgramRegistryDetailResponse:
    """수동 검증 실행"""
    row = load_admin_program_registry_row(db=db, program_id=program_id)
    if row is None:
        raise HTTPException(status_code=404, detail="program not found")

    run_payload = build_admin_program_registry_check_run_payload(
        db=db,
        program_id=program_id,
        payload=payload,
        admin=admin,
    )
    updated_row = save_admin_program_registry_row(
        db=db,
        program_id=program_id,
        payload=AdminProgramRegistryStatusUpdateRequest(
            build_status=run_payload.get("build_status"),
            verification_status=run_payload.get("verification_status"),
        ),
        admin=admin,
    )
    detail_payload = build_admin_program_registry_detail_payload(
        db=db,
        program_id=program_id,
        row=updated_row,
    )
    return AdminProgramRegistryDetailResponse(**detail_payload)


@router.get("/program-registry/{program_id}/artifacts")
def list_admin_program_registry_artifacts(
    program_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[AdminProgramRegistryArtifactResponse]:
    """산출물 목록 조회"""
    row = load_admin_program_registry_row(db=db, program_id=program_id)
    if row is None:
        raise HTTPException(status_code=404, detail="program not found")

    items = build_admin_program_registry_artifacts_payload(db=db, program_id=program_id)
    return [AdminProgramRegistryArtifactResponse(**item) for item in items]


@router.get("/program-registry/{program_id}/docs")
def list_admin_program_registry_docs(
    program_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[dict[str, str]]:
    """문서 링크 조회"""
    row = load_admin_program_registry_row(db=db, program_id=program_id)
    if row is None:
        raise HTTPException(status_code=404, detail="program not found")
    return build_admin_program_registry_docs_payload(db=db, program_id=program_id)


@router.post("/program-registry/{program_id}/approve")
def approve_admin_program_registry(
    program_id: str,
    payload: AdminProgramRegistryApproveRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminProgramRegistryDetailResponse:
    """승인 처리"""
    row = load_admin_program_registry_row(db=db, program_id=program_id)
    if row is None:
        raise HTTPException(status_code=404, detail="program not found")

    approve_payload = build_admin_program_registry_approve_payload(
        db=db,
        program_id=program_id,
        payload=payload,
        admin=admin,
    )
    updated_row = save_admin_program_registry_row(
        db=db,
        program_id=program_id,
        payload=AdminProgramRegistryStatusUpdateRequest(
            deploy_status=approve_payload.get("deploy_status"),
            verification_status=approve_payload.get("verification_status"),
        ),
        admin=admin,
    )
    detail_payload = build_admin_program_registry_detail_payload(
        db=db,
        program_id=program_id,
        row=updated_row,
    )
    return AdminProgramRegistryDetailResponse(**detail_payload)


@router.post("/program-registry/{program_id}/rollback")
def rollback_admin_program_registry(
    program_id: str,
    payload: AdminProgramRegistryRollbackRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminProgramRegistryDetailResponse:
    """롤백 처리"""
    row = load_admin_program_registry_row(db=db, program_id=program_id)
    if row is None:
        raise HTTPException(status_code=404, detail="program not found")

    rollback_payload = build_admin_program_registry_rollback_payload(
        db=db,
        program_id=program_id,
        payload=payload,
        admin=admin,
    )
    updated_row = save_admin_program_registry_row(
        db=db,
        program_id=program_id,
        payload=AdminProgramRegistryStatusUpdateRequest(
            deploy_status=rollback_payload.get("deploy_status"),
            verification_status=rollback_payload.get("verification_status"),
        ),
        admin=admin,
    )
    detail_payload = build_admin_program_registry_detail_payload(
        db=db,
        program_id=program_id,
        row=updated_row,
    )
    return AdminProgramRegistryDetailResponse(**detail_payload)
```

#### route 함수 내부 흐름 원칙

- route 의 시작은 항상 `load_*` 로 현재 row/rows 를 읽는다.
- route 는 404 check 와 입력 검증을 가장 먼저 수행한다.
- write API 는 `save_admin_program_registry_row()` 또는 service-specific `build_*_payload()` 를 통해 의도된 상태를 반영한다.
- `build_*_payload()` 는 payload 자체를 조립하고, route 는 최종 `Response` model 로 감싼다.
- 응답은 항상 `DetailResponse`/`StateResponse` 로 끝난다.
- 상세/검증/승인/롤백 API 는 모두 마지막에 `build_admin_program_registry_detail_payload()` 로 일관되게 마무리한다.

#### 실제 구현 우선순위

1. `list_admin_program_registry`
2. `get_admin_program_registry`
3. `update_admin_program_registry_status`
4. `update_admin_program_registry`
5. `list_admin_program_registry_checks`
6. `list_admin_program_registry_artifacts`
7. `list_admin_program_registry_docs`
8. `post_admin_program_registry_check_run`
9. `approve_admin_program_registry`
10. `rollback_admin_program_registry`
11. `list_admin_program_registry_builds`
12. `list_admin_program_registry_deployments`

이 순서대로 구현하면 목록 → 상세 → 상태 갱신 → 검증/산출물 → 승인/롤백 구조가 자연스럽게 이어진다.

#### 최소 Smoke Test 엔드포인트 호출 시나리오

실제 반영된 route 블록 기준 최소 호출 순서는 아래와 같다.

1. `GET /api/admin/program-registry`
2. `GET /api/admin/program-registry/{program_id}`
3. `GET /api/admin/program-registry/{program_id}/checks`
4. `GET /api/admin/program-registry/{program_id}/artifacts`
5. `GET /api/admin/program-registry/{program_id}/docs`
6. 선택: `PATCH /api/admin/program-registry/{program_id}/status`

실행 스크립트:

- `scripts/run_admin_program_registry_smoke.ps1`

실행 예시:

```powershell
$env:ADMIN_BEARER_TOKEN = "<admin-jwt>"
pwsh -File scripts/run_admin_program_registry_smoke.ps1 -BaseUrl "http://127.0.0.1:8000"

# write endpoint 포함
pwsh -File scripts/run_admin_program_registry_smoke.ps1 -BaseUrl "http://127.0.0.1:8000" -EnableWrite
```

성공 기준:

- read endpoint 호출 5개가 모두 `200`
- `ProgramId` 미지정 시 목록 첫 항목의 `program_id`를 자동 선택
- `-EnableWrite` 사용 시 status patch 호출도 `200`
- 최종 출력이 `SMOKE PASSED`

#### Negative Smoke Test 시나리오 (404/400 검증)

요청한 실패 케이스를 계약으로 고정한다.

1. 없는 `program_id` 조회는 `404`
2. `confirm=false` 롤백 요청은 `400`
3. 잘못된 status 문자열은 `400`

실행 스크립트:

- `scripts/run_admin_program_registry_negative_smoke.ps1`

실행 예시:

```powershell
$env:ADMIN_BEARER_TOKEN = "<admin-jwt>"
pwsh -File scripts/run_admin_program_registry_negative_smoke.ps1 -BaseUrl "http://127.0.0.1:8000"
```

기대 결과:

- 1단계: `GET /api/admin/program-registry/missing-program-id-404` -> `404`
- 2단계: `POST /api/admin/program-registry/{program_id}/rollback` with `confirm=false` -> `400`
- 3단계: `PATCH /api/admin/program-registry/{program_id}/status` with invalid status -> `400`
- 최종 출력이 `NEGATIVE SMOKE PASSED`

#### Auth Negative Smoke Test 시나리오 (401/403 검증)

인증 실패 계약도 아래처럼 고정한다.

1. 인증 헤더 없이 조회하면 `401`
2. non-admin 토큰으로 조회하면 `403`

실행 스크립트:

- `scripts/run_admin_program_registry_auth_negative_smoke.ps1`

실행 예시:

```powershell
pwsh -File scripts/run_admin_program_registry_auth_negative_smoke.ps1 -BaseUrl "http://127.0.0.1:8000"
```

기대 결과:

- 1단계: `GET /api/admin/program-registry` (no auth header) -> `401`
- 2단계: `GET /api/admin/program-registry` (non-admin token) -> `403`
- 최종 출력이 `AUTH NEGATIVE SMOKE PASSED`

#### 통합 계약 Smoke 실행

404/400/400 과 401/403을 한 번에 검증할 때는 아래 스크립트를 사용한다.

- `scripts/run_admin_program_registry_contract_smoke.ps1`

실행 예시:

```powershell
pwsh -File scripts/run_admin_program_registry_contract_smoke.ps1 -BaseUrl "http://127.0.0.1:8000"
```

성공 기준:

- Negative smoke 결과: `NEGATIVE SMOKE PASSED`
- Auth negative smoke 결과: `AUTH NEGATIVE SMOKE PASSED`
- 최종 출력: `PROGRAM REGISTRY CONTRACT SMOKE PASSED`

#### `backend/admin/program_registry_service.py` 실제 함수 시그니처 스켈레톤

아래 파일 단위 스켈레톤은 실제 구현 파일의 시작부를 가장 근접하게 표현한다.

```py
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from backend.models import User
    from backend.admin.program_registry_models import (
        AdminProgramRegistryApproveRequest,
        AdminProgramRegistryCheckRunRequest,
        AdminProgramRegistryRollbackRequest,
        AdminProgramRegistryStatusUpdateRequest,
    )


def load_admin_program_registry_rows(db: Session) -> List[Any]:
    raise NotImplementedError


def load_admin_program_registry_row(db: Session, program_id: str) -> Optional[Any]:
    raise NotImplementedError


def save_admin_program_registry_row(
    *,
    db: Session,
    program_id: str,
    payload: "AdminProgramRegistryStatusUpdateRequest",
    admin: Optional["User"] = None,
) -> Any:
    raise NotImplementedError


def serialize_admin_program_registry_summary_item(row: Any) -> Dict[str, Any]:
    raise NotImplementedError


def serialize_admin_program_registry_artifact(item: Any) -> Dict[str, Any]:
    raise NotImplementedError


def serialize_admin_program_registry_check(item: Any) -> Dict[str, Any]:
    raise NotImplementedError


def build_admin_program_registry_state_payload(
    *,
    db: Session,
    rows: Optional[List[Any]] = None,
    items: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    raise NotImplementedError


def build_admin_program_registry_detail_payload(
    *,
    db: Session,
    program_id: str,
    row: Optional[Any] = None,
) -> Dict[str, Any]:
    raise NotImplementedError


def build_admin_program_registry_builds_payload(
    *,
    db: Session,
    program_id: str,
) -> List[Dict[str, Any]]:
    raise NotImplementedError


def build_admin_program_registry_deployments_payload(
    *,
    db: Session,
    program_id: str,
) -> List[Dict[str, Any]]:
    raise NotImplementedError


def build_admin_program_registry_checks_payload(
    *,
    db: Session,
    program_id: str,
) -> List[Dict[str, Any]]:
    raise NotImplementedError


def build_admin_program_registry_artifacts_payload(
    *,
    db: Session,
    program_id: str,
) -> List[Dict[str, Any]]:
    raise NotImplementedError


def build_admin_program_registry_docs_payload(
    *,
    db: Session,
    program_id: str,
) -> List[Dict[str, str]]:
    raise NotImplementedError


def build_admin_program_registry_check_run_payload(
    *,
    db: Session,
    program_id: str,
    payload: "AdminProgramRegistryCheckRunRequest",
    admin: Optional["User"] = None,
) -> Dict[str, Any]:
    raise NotImplementedError


def build_admin_program_registry_approve_payload(
    *,
    db: Session,
    program_id: str,
    payload: "AdminProgramRegistryApproveRequest",
    admin: Optional["User"] = None,
) -> Dict[str, Any]:
    raise NotImplementedError


def build_admin_program_registry_rollback_payload(
    *,
    db: Session,
    program_id: str,
    payload: "AdminProgramRegistryRollbackRequest",
    admin: Optional["User"] = None,
) -> Dict[str, Any]:
    raise NotImplementedError
```

#### 함수/모델 설계 원칙

- 목록 조회는 `StateResponse` 를 반환한다.
- 단건 상세 조회는 `DetailResponse` 를 반환한다.
- 상태 갱신은 `StatusUpdateRequest` 를 받는다.
- 실행형 액션은 `CheckRunRequest`, `RollbackRequest`, `ApproveRequest` 를 받는다.
- `program_id` 는 경로 식별자, `program_key` 는 내부 검증 식별자로 유지한다.
- `Request`/`Response` 접미사는 현재 `admin_router.py`의 기존 네이밍과 동일한 수준의 명확성을 유지한다.

#### 백엔드 DTO 설계 원칙

- 요청 DTO와 응답 DTO를 분리한다.
- 목록 응답은 summary, 상세 응답은 detail 로 나눈다.
- 상태 문자열은 프런트 union 과 맞추되, 백엔드에서는 최종적으로 enum 상수로 고정할 수 있게 둔다.
- `program_key` 는 모든 write API 의 필수 식별자로 쓴다.
- `program_id` 는 저장소 내부 식별자로 쓴다.

#### 백엔드 구현 순서

1. `AdminProgramRegistrySummaryResponse`
2. `AdminProgramRegistryDetailResponse`
3. `AdminProgramRegistryStateResponse`
4. `AdminProgramRegistryStatusUpdateRequest`
5. `AdminProgramRegistryCheckRunRequest`
6. `AdminProgramRegistryRollbackRequest`
7. `AdminProgramRegistryApproveRequest`

이 순서로 넣으면 먼저 목록이 열리고, 이후 상세/검증/롤백/승인 흐름이 따라붙는다.

## 프로그램 레지스트리 데이터 모델

### 핵심 필드

- program_id
- program_key
- program_name
- program_type
- primary_domain
- admin_domain
- api_base_url
- target_platform
- build_status
- deploy_status
- verification_status
- latest_version
- latest_build_id
- latest_release_channel
- owner_team
- operator_notes
- docs_links

### 프로그램별 상태 축

- design
- build
- package
- deploy
- verify
- operate

### 권장 프로그램 분류

- marketplace
- admin_dashboard
- regional_console
- apk_delivery
- future_program_slot_a
- future_program_slot_b

## 필요한 API 목록

### 레지스트리 조회

- GET /api/admin/program-registry
  - 프로그램 목록과 요약 상태 조회
- GET /api/admin/program-registry/{program_id}
  - 프로그램 상세 설정과 최근 상태 조회

### 상태 갱신

- PUT /api/admin/program-registry/{program_id}
  - 프로그램 메타정보 수정
- PATCH /api/admin/program-registry/{program_id}/status
  - build/deploy/verify/operate 상태 갱신

### 배포/검증

- GET /api/admin/program-registry/{program_id}/builds
  - 최근 빌드 목록 조회
- GET /api/admin/program-registry/{program_id}/deployments
  - 최근 배포 목록 조회
- GET /api/admin/program-registry/{program_id}/checks
  - 운영 검증 기록 조회
- POST /api/admin/program-registry/{program_id}/checks/run
  - 선택 프로그램의 검증 실행 요청

### 산출물/문서

- GET /api/admin/program-registry/{program_id}/artifacts
  - APK, ZIP, 로그, 리포트 경로 조회
- GET /api/admin/program-registry/{program_id}/docs
  - 해당 프로그램의 운영 문서 링크 조회

### 권한/운영

- POST /api/admin/program-registry/{program_id}/approve
  - 운영 반영 승인
- POST /api/admin/program-registry/{program_id}/rollback
  - 최근 배포 롤백 요청

## 프런트 섹션 배치안

### 현재 관리자 페이지에 추가할 영역

- 상단 배너 또는 첫 카드 영역: 프로그램 레지스트리
- 중앙 보드: 선택 프로그램 상세 카드
- 보조 패널: build/deploy/check history
- 기존 전역 패널: 그대로 유지

### 현재 파일 기준 연결 지점

- [frontend/frontend/app/admin/page.tsx](../../frontend/frontend/app/admin/page.tsx)
  - 프로그램 선택 상태와 현재 선택된 program_key를 추가한다.
  - 프로그램 선택에 따라 중앙 보드의 상세 패널을 바꾼다.
- [frontend/frontend/app/admin/admin-dashboard-sections-config.tsx](../../frontend/frontend/app/admin/admin-dashboard-sections-config.tsx)
  - 기존 전역 섹션 아래에 program-registry 섹션을 추가한다.
  - 프로그램별 상세 패널은 별도 섹션으로 분리한다.
- [frontend/frontend/app/admin/admin-page-types.ts](../../frontend/frontend/app/admin/admin-page-types.ts)
  - 프로그램 카드, 상세 패널, 상태 히스토리용 props 타입을 추가한다.

### 레이아웃 원칙

- 레일은 유지하고 중앙만 확장한다.
- 전역 패널과 프로그램 패널을 섞지 않는다.
- 한 화면에서 모든 프로그램 세부를 동시에 보여주지 않는다.
- 선택된 프로그램만 활성화해서 렌더링한다.

## 구현 순서

1. 프로그램 레지스트리 타입 정의를 추가한다.
2. 목록 조회 API를 먼저 만든다.
3. 관리자 페이지에 프로그램 선택 상태를 붙인다.
4. 프로그램 카드 보드를 추가한다.
5. 프로그램 상세 패널을 연결한다.
6. 배포/검증/산출물 패널을 분리한다.
7. 하드게이트를 추가하고 운영 실검증으로 닫는다.

## 하드게이트 항목

### 1. 레지스트리 SSOT 게이트

- 프로그램명, 도메인, api_base_url, build_status가 파일과 API에서 다르면 실패다.
- 전역 설정과 프로그램 설정이 같은 필드명으로 혼용되면 실패다.
- 카드 표시 순서가 `program_name → program_type → domain → build/deploy/verify → owner` 순서를 벗어나면 실패다.

### 2. 레일 비파괴 게이트

- 기존 좌/우 레일이 사라지거나 의미가 바뀌면 실패다.
- 전역 운영 패널이 프로그램별 패널로 대체되면 실패다.

### 3. 선택형 작업공간 게이트

- 선택하지 않은 프로그램의 상세 패널이 동시에 과도하게 렌더되면 실패다.
- 프로그램 선택이 바뀌었는데 상세 상태가 이전 프로그램에 남아 있으면 실패다.
- 상세 패널은 하나의 program_key만 기준으로 렌더해야 하며, 여러 프로그램 상태를 한 패널에 혼합하면 실패다.

### 4. API 정합성 게이트

- 목록, 상세, 상태 갱신, 검증, 산출물 API의 응답 구조가 섞이면 실패다.
- program_id 기준 라우팅이 흔들리면 실패다.

### 5. 운영 실검증 게이트

- 개발서버 결과만으로 완료하면 실패다.
- 운영 도메인에서 실제 확인이 없으면 실패다.
- 같은 프로그램을 2회 이상 확인하지 않으면 완료로 닫지 않는다.

### 6. 반영 범위 게이트

- 로컬파일, 컨테이너, 개발서버, 운영서버 중 어디까지 반영했는지 문서에 없으면 실패다.
- 선언한 표면 외에 몰래 바꾼 파일이 있으면 실패다.

## 문서화 규칙

- 작업 시작 시 이 설계안을 먼저 읽는다.
- 수정 전후로 체크리스트 템플릿을 함께 채운다.
- 하드게이트 통과 기록이 없으면 완료로 닫지 않는다.
