import type { OrchestratorCapabilityDetailSectionItem } from '@/lib/admin-dashboard-types';
import type { LiveLogItem } from '@/lib/admin-runtime-types';
import type { OrchestratorCapabilityActionGuide } from '@/lib/admin-dashboard-ui-types';

export function pickPreferredModel(availableModels: string[], candidates: string[], fallback = '') {
    const availableSet = new Set(availableModels);
    for (const candidate of candidates) {
        if (availableSet.has(candidate)) {
            return candidate;
        }
    }
    return fallback;
}

export function downloadCsvFromRows(filename: string, rows: string[][]) {
    if (typeof window === 'undefined') {
        return;
    }
    const csvText = rows.map((row) => row.map((cell) => {
        const value = String(cell ?? '');
        return /[",\n]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value;
    }).join(',')).join('\n');
    const blob = new Blob([`\uFEFF${csvText}`], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    window.URL.revokeObjectURL(url);
}

export function toFileHref(path: string) {
    const normalized = (path || '').trim();
    if (!normalized) return '#';
    if (/^[a-zA-Z]:\\/.test(normalized)) {
        return `file:///${normalized.replace(/\\/g, '/')}`;
    }
    if (normalized.startsWith('/')) {
        return `file://${normalized}`;
    }
    return `file:///${normalized.replace(/\\/g, '/')}`;
}

export function getSecurityRulePriority(item: OrchestratorCapabilityDetailSectionItem) {
    const haystack = `${item.label} ${item.value} ${item.note || ''}`.toLowerCase();
    let score = 0;
    if (haystack.includes('secret_key')) score += 400;
    if (haystack.includes('auth') || haystack.includes('admin')) score += 320;
    if (haystack.includes('token') || haystack.includes('jwt')) score += 260;
    if (haystack.includes('password') || haystack.includes('credential')) score += 240;
    if (haystack.includes('subprocess') || haystack.includes('eval') || haystack.includes('pickle')) score += 220;
    if (haystack.includes('warning')) score += 40;
    return score;
}

export function normalizeStoredLiveLog(item: LiveLogItem): LiveLogItem | null {
    const message = String(item?.message || '').trim();
    if (!message || message === 'Not Found') {
        return null;
    }
    return {
        ...item,
        message,
    };
}

export function formatCurrency(value: number) {
    return new Intl.NumberFormat('ko-KR', { style: 'currency', currency: 'KRW', maximumFractionDigits: 0 }).format(Number.isFinite(value) ? value : 0);
}

export function getOrchestratorActionGuide(capabilityId: string): OrchestratorCapabilityActionGuide {
    const detailHref = capabilityId
        ? `/admin/llm?capability=${encodeURIComponent(capabilityId)}`
        : '/admin/llm';
    if (capabilityId === 'project-scanner') {
        return {
            title: '실행 근거 다시 수집',
            summary: '전체 프로젝트 기준 self-run 기록과 현재 진단 범위를 다시 맞춥니다.',
            href: detailHref,
        };
    }
    if (capabilityId === 'self-healing-engine') {
        return {
            title: '복구 순서 즉시 실행',
            summary: '최신 failure chain 기준으로 self-healing engine 개선 흐름을 다시 실행합니다.',
            href: detailHref,
        };
    }
    if (capabilityId === 'code-generator') {
        return {
            title: '산출물 기준 보강',
            summary: '파일 수, 폴더 수, 코드량 부족 기준을 넘기도록 code generator 개선 실행으로 이동합니다.',
            href: detailHref,
        };
    }
    return {
        title: '상세 제어 열기',
        summary: '기능군 상세 제어 화면으로 이동해 원인과 개선 경로를 확인합니다.',
        href: detailHref,
    };
}

export function normalizeSystemSettingsMessage(message: string) {
    if (message.includes('.env 파일을 찾을 수 없습니다')) {
        return {
            userMessage: '전역 설정 탭이 아직 연결되지 않았습니다. 기능별 상태만 간단 표시합니다.',
            detailMessage: '.env 원본 파일이 확인되지 않아 읽기/저장이 비활성화된 상태입니다.',
            liveLogLevel: 'info' as const,
            liveLogMessage: '전역 설정 탭 미연동 상태 감지: .env 원본 파일 미확인',
        };
    }

    if (message.includes('upstream timeout') || message.includes('target=')) {
        return {
            userMessage: '전역 설정 프록시가 지연돼 직접 백엔드 경로로 재시도했습니다. 계속 반복되면 실행 중인 프런트 번들을 재기동하세요.',
            detailMessage: message,
            liveLogLevel: 'warning' as const,
            liveLogMessage: `전역 설정 프록시 지연 감지: ${message || 'unknown'}`,
        };
    }

    return {
        userMessage: '전역 설정 탭 연동 상태를 확인하지 못했습니다. 기능별 상태만 간단 표시합니다.',
        detailMessage: message,
        liveLogLevel: 'warning' as const,
        liveLogMessage: `전역 설정 조회 실패: ${message || 'unknown'}`,
    };
}
