export function buildAdminHeaderIntroData(options: {
    embeddedMode: boolean;
}) {
    return {
        embeddedMode: options.embeddedMode,
        embeddedTitle: '🤖 관리자 대시보드 내장 LLM 통합 제어',
        embeddedDescription: '메인 /admin 이 공식 단일 제어 화면입니다. 이 임베드 패널에서 runtime, 역할별 모델, 실행 정책, 오케스트레이터 전역 환경값을 한 번에 관리합니다.',
        stickyEyebrow: 'Admin Orchestrator Independent Space',
        stickyDescription: '독립공간 복귀 링크를 헤더에 고정했습니다. 언제든 관리자 대시보드나 고객 오케스트레이터 공간으로 즉시 복귀할 수 있습니다.',
        pageTitle: '🤖 LLM 오케스트레이터',
        pageSubtitle: '멀티 에이전트 파이프라인 (계획 → 코드 → 리뷰)',
        pageDescription: '공식 제어 경로는 관리자 대시보드의 내장 LLM 통합 제어 패널입니다. 이 단독 페이지는 점검·복구·직접 접근이 필요할 때만 사용하는 보조 진입 경로로 유지합니다.',
    };
}
