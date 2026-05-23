import type { AdminDashboardSelfRunStatusLike } from '@/lib/admin-self-run-control';
import type { CompactOverviewCard } from '@/lib/admin-dashboard-ui-types';

export type AdminSelfRunDisplayMeta = {
    label: string;
    tone: CompactOverviewCard['tone'];
    detail: string;
    healthPenalty: number;
    actionable: boolean;
};

export type SelfRunFailureInsightLike = {
    severity: 'warning' | 'critical';
    category: 'python_compile_fail' | 'import_error' | 'dependency' | 'timeout' | 'output_shortage' | 'unknown';
    title: string;
    reason: string;
    automatedActions: string[];
    priorityFixPaths: string[];
    guideHref: string;
};

export function parseSelfRunDate(value?: string | null) {
    if (!value) return null;
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function getSelfRunDisplayMeta(status: AdminDashboardSelfRunStatusLike | null): AdminSelfRunDisplayMeta {
    if (!status) {
        return {
            label: '대기 중',
            tone: 'slate',
            detail: '최근 self-run 기록 없음',
            healthPenalty: 0,
            actionable: false,
        };
    }

    if (status.status === 'running') {
        return {
            label: '자가 실행 활성',
            tone: 'emerald',
            detail: typeof status.running_seconds === 'number' ? `${status.running_seconds}초 경과` : (status.runtime_diagnostic || '자가 실행 진행 중'),
            healthPenalty: 0,
            actionable: false,
        };
    }
    if (status.status === 'pending_approval') {
        return {
            label: '승인 대기',
            tone: 'emerald',
            detail: status.runtime_diagnostic || '게이트 통과 · 승인 대기 중',
            healthPenalty: 0,
            actionable: false,
        };
    }
    if (status.status === 'no_changes') {
        return {
            label: '재검증 완료',
            tone: 'emerald',
            detail: 'clone 재검증 완료 · 반영할 diff 없음',
            healthPenalty: 0,
            actionable: false,
        };
    }
    if (status.status === 'applied_to_source') {
        return {
            label: '원본 반영 완료',
            tone: 'emerald',
            detail: '재검증 후 원본 반영 완료',
            healthPenalty: 0,
            actionable: false,
        };
    }
    if (status.status !== 'failed') {
        return {
            label: '대기 중',
            tone: 'slate',
            detail: status.runtime_diagnostic || '최근 self-run 기록 없음',
            healthPenalty: 0,
            actionable: false,
        };
    }

    const finishedAt = parseSelfRunDate(status.finished_at) || parseSelfRunDate(status.started_at);
    const ageHours = finishedAt ? Math.max(0, (Date.now() - finishedAt.getTime()) / 3600000) : null;
    if (ageHours !== null && ageHours >= 6) {
        return {
            label: '보관된 실패',
            tone: 'slate',
            detail: `오래된 실패 기록(${ageHours.toFixed(1)}시간 전)는 즉시 장애 대신 참고용으로만 유지됩니다.`,
            healthPenalty: 0,
            actionable: false,
        };
    }
    if (ageHours !== null && ageHours >= 1) {
        return {
            label: '주의',
            tone: 'amber',
            detail: status.runtime_diagnostic || `최근 self-run 실패 흔적(${ageHours.toFixed(1)}시간 전)이 남아 있습니다.`,
            healthPenalty: 8,
            actionable: true,
        };
    }
    return {
        label: '실행 실패',
        tone: 'orange',
        detail: status.runtime_diagnostic || '최신 self-run 실패 원인 확인 필요',
        healthPenalty: 20,
        actionable: true,
    };
}

export function classifySelfRunFailure(
    status: AdminDashboardSelfRunStatusLike | null,
    cards: Array<{ summary: string; detail?: string | null }>,
): SelfRunFailureInsightLike | null {
    if (!status || status.status !== 'failed') return null;
    const displayMeta = getSelfRunDisplayMeta(status);
    if (!displayMeta.actionable) return null;
    const diagnostic = `${status.runtime_diagnostic || ''} ${cards.map((card) => `${card.summary} ${card.detail || ''}`).join(' ')}`.toLowerCase();
    if (diagnostic.includes('py_compile') || diagnostic.includes('compile-fail') || diagnostic.includes('syntaxerror')) {
        return {
            severity: 'critical',
            category: 'python_compile_fail',
            title: 'Python 컴파일 실패',
            reason: '구문 오류 또는 잘못된 코드 조각 때문에 self-run 산출물이 바로 실행되지 못했습니다.',
            automatedActions: ['LLM 제어 패널 자동 개방', '최신 실패 카드 우선 표시', '로그 패널 자동 확장'],
            priorityFixPaths: [status.source_path || 'workspace/app/main.py', 'root_cause_docs/root_cause_analysis.md', status.worker_log_path || 'analysis_docs/code_analysis.json'].filter(Boolean),
            guideHref: '/admin/llm',
        };
    }
    if (diagnostic.includes('modulenotfounderror') || diagnostic.includes('importerror')) {
        return {
            severity: 'critical',
            category: 'import_error',
            title: '모듈 import 실패',
            reason: '엔트리 파일과 모듈 경로가 맞지 않거나 패키지 초기화가 누락되었습니다.',
            automatedActions: ['서비스/엔트리 점검 카드 강조', '로그 패널 자동 확장', 'LLM 개선 제어 이동 유도'],
            priorityFixPaths: [status.source_path || 'workspace/app/__init__.py', 'workspace/app/main.py', status.worker_log_path || 'root_cause_docs/root_cause_analysis.md'].filter(Boolean),
            guideHref: '/admin/llm',
        };
    }
    if (diagnostic.includes('pip') || diagnostic.includes('dependency') || diagnostic.includes('requirements')) {
        return {
            severity: 'warning',
            category: 'dependency',
            title: '의존성 누락',
            reason: 'requirements 또는 런타임 패키지 구성이 self-run 출력물과 일치하지 않습니다.',
            automatedActions: ['전역 설정 패널 자동 개방', '로그 패널 자동 확장', '재진단 새로고침'],
            priorityFixPaths: ['requirements.txt', 'pyproject.toml', status.worker_log_path || 'analysis_docs/code_analysis.json'].filter(Boolean),
            guideHref: '/admin/llm',
        };
    }
    if (diagnostic.includes('timeout') || diagnostic.includes('timed out')) {
        return {
            severity: 'warning',
            category: 'timeout',
            title: '실행 시간 초과',
            reason: '생성 시간, 검증 시간, 또는 외부 프로세스 응답 시간이 기준을 넘었습니다.',
            automatedActions: ['헬스체크 카드 우선 표시', '로그 패널 자동 확장', '새로고침 재진단'],
            priorityFixPaths: [status.worker_log_path || 'analysis_docs/code_analysis.json', status.source_path || 'workspace/app/main.py', 'root_cause_docs/root_cause_analysis.md'].filter(Boolean),
            guideHref: '/admin/llm',
        };
    }
    if (diagnostic.includes('min_files') || diagnostic.includes('min_dirs') || diagnostic.includes('output shortage') || diagnostic.includes('산출물')) {
        return {
            severity: 'warning',
            category: 'output_shortage',
            title: '산출물 기준 미달',
            reason: '파일 수, 디렉터리 수, 또는 결과물 구조가 self-run 최소 기준에 도달하지 못했습니다.',
            automatedActions: ['기능군 경고 카드 우선 표시', 'LLM 개선 제어 이동 유도', '재진단 새로고침'],
            priorityFixPaths: [status.source_path || 'workspace/app/main.py', 'analysis_docs/code_analysis.json', 'root_cause_docs/root_cause_analysis.md'].filter(Boolean),
            guideHref: '/admin/llm',
        };
    }
    return {
        severity: 'warning',
        category: 'unknown',
        title: '원인 미분류 self-run 실패',
        reason: '현재 수집된 진단 문자열만으로 분류되지 않는 실패입니다. 최신 로그와 root cause 문서를 함께 확인해야 합니다.',
        automatedActions: ['로그 패널 자동 확장', '문제 카드 우선 표시', '상세 제어 이동 유도'],
        priorityFixPaths: [status.worker_log_path || 'root_cause_docs/root_cause_analysis.md', status.source_path || 'workspace/app/main.py'].filter(Boolean),
        guideHref: '/admin/llm',
    };
}

export function assertAdminSelfRunAnalysisContract() {
    const sample = getSelfRunDisplayMeta(null);
    if (!sample.label || typeof sample.actionable !== 'boolean') {
        throw new Error('admin self-run analysis contract 누락: display meta 핵심 필드 필요');
    }
}
