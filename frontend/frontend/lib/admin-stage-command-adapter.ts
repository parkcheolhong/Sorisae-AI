import type { SelfPrepareMode } from '@/lib/use-admin-self-run';

export interface StageCommandContext {
    stageNote: string;
    substepChecks: Record<string, boolean>;
    revisionNote: string;
}

export interface StageCommandActions {
    run: () => Promise<unknown>;
    runWithTask: (task: string) => Promise<unknown>;
    updateStageStatus: (status: 'passed' | 'failed' | 'manual_correction', payload: {
        stageNote: string;
        manualCorrection: string;
        substepChecks: Record<string, boolean>;
        revisionNote: string;
        onSuccess?: () => void;
    }) => Promise<unknown>;
    verify: () => Promise<unknown>;
    applyIdeaPreset: (value: string) => void;
}

export const DEFAULT_STAGE_IDEA_PRESETS = [
    '운영 장애 원인을 1줄 요약 + 재현 조건 추가',
    '다음 카드에서 검증할 API/로그/권한 체크를 미리 기록',
    '수정 범위를 현재 단계 책임으로 다시 좁히기',
];

// 실행 의도 감지: 아래 키워드를 포함하면 run() 으로 라우팅
export const EXECUTION_INTENT_KEYWORDS = [
    '자가진단', '자가 진단', '진단해줘', '진단해 줘',
    '자가개선', '자가 개선', '개선해줘', '개선해 줘',
    '자가확장', '자가 확장', '확장해줘', '확장해 줘',
    '스크립트 만들어', '스크립트 생성', '스크립트 작성', '스크립트 추가',
    '구현해줘', '구현해 줘', '만들어줘', '만들어 줘',
    '수정해줘', '수정해 줘', '고쳐줘', '고쳐 줘',
    '추가해줘', '추가해 줘', '삭제해줘', '삭제해 줘',
    '작성해줘', '작성해 줘', '생성해줘', '생성해 줘',
    '분석해줘', '분석해 줘', '최적화해줘', '최적화해 줘',
    '리팩터링', '리팩토링',
    '빌드해줘', '빌드해 줘', '테스트해줘', '테스트해 줘',
    '검증해줘', '검증해 줘', '배포해줘', '배포해 줘',
    '연결해줘', '연결해 줘', '연동해줘', '연동해 줘',
    '적용해줘', '적용해 줘', '설치해줘', '설치해 줘',
    '해주세요', '해 주세요', '부탁해', '부탁합니다',
];

export function detectsExecutionIntent(prompt: string): boolean {
    const lower = prompt.toLowerCase().trim();
    return EXECUTION_INTENT_KEYWORDS.some(kw => lower.includes(kw));
}

export async function applyAdminStageCommand(
    input: string,
    context: StageCommandContext,
    actions: StageCommandActions,
) {
    const trimmed = input.trim();
    if (!trimmed) return false;
    const payload = {
        stageNote: context.stageNote,
        manualCorrection: context.stageNote,
        substepChecks: context.substepChecks,
        revisionNote: context.revisionNote,
        onSuccess: () => actions.applyIdeaPreset(''),
    };

    if (trimmed === '/run') {
        await actions.run();
        return true;
    }
    if (trimmed === '/pass') {
        await actions.updateStageStatus('passed', payload);
        return true;
    }
    if (trimmed === '/fix') {
        await actions.updateStageStatus('manual_correction', payload);
        return true;
    }
    if (trimmed === '/fail') {
        await actions.updateStageStatus('failed', payload);
        return true;
    }
    if (trimmed === '/verify') {
        await actions.verify();
        return true;
    }

    // 자가 진단 / 자가 개선 / 자가 확장 슬래시 명령
    if (/^\/(diagnose|자가진단|진단)$/i.test(trimmed)) {
        await actions.runWithTask('자가 진단: 현재 코드베이스 전체를 진단하고 이슈를 분석해줘');
        return true;
    }
    if (/^\/(improve|자가개선|개선)$/i.test(trimmed)) {
        await actions.runWithTask('자가 개선: 진단 결과를 기반으로 코드 품질과 구조를 개선해줘');
        return true;
    }
    if (/^\/(expand|자가확장|확장)$/i.test(trimmed)) {
        await actions.runWithTask('자가 확장: 기존 구조를 분석하고 확장 가능한 기능을 추가해줘');
        return true;
    }
    if (/^\/(analyze|분석)$/i.test(trimmed)) {
        await actions.runWithTask('현재 코드베이스의 전체 구조와 의존성을 분석해줘');
        return true;
    }
    if (/^\/(test|테스트)$/i.test(trimmed)) {
        await actions.verify();
        return true;
    }

    // /script <이름>: 스크립트 생성
    const scriptMatch = trimmed.match(/^\/(script|스크립트)\s+(.+)$/i);
    if (scriptMatch) {
        await actions.runWithTask(`스크립트 생성: ${scriptMatch[2].trim()}`);
        return true;
    }

    // /task <태스크>: 임의 태스크 즉시 실행
    const taskMatch = trimmed.match(/^\/(task|실행)\s+(.+)$/i);
    if (taskMatch) {
        await actions.runWithTask(taskMatch[2].trim());
        return true;
    }

    // /search <쿼리>: 검색 태스크 실행
    const searchMatch = trimmed.match(/^\/(search|검색)\s+(.+)$/i);
    if (searchMatch) {
        await actions.runWithTask(`검색 및 분석: ${searchMatch[2].trim()}`);
        return true;
    }

    const presetMatch = trimmed.match(/^\/preset\s+(\d+)$/i);
    if (presetMatch) {
        const selected = DEFAULT_STAGE_IDEA_PRESETS[Number(presetMatch[1]) - 1];
        if (selected) {
            actions.applyIdeaPreset(selected);
            return true;
        }
    }
    return false;
}

export const applyStageIdeaPresetValue = (currentValue: string, preset: string) => (
    preset ? [currentValue, preset].filter(Boolean).join('\n') : ''
);

export const resolvePresetForGeneratorMode = (presetId: SelfPrepareMode) => presetId;
