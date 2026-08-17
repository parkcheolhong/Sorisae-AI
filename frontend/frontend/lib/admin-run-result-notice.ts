export function buildAdminRunResultNotice(options: {
    applyError?: string | null;
    applied?: boolean;
    outputDir?: string | null;
    adminFinalPassGuide: string;
}) {
    if (options.applyError) {
        return `실행은 끝났지만 적용 실패가 발생했습니다: ${options.applyError}`;
    }
    if (options.applied) {
        return `오케스트레이션 1차 검증 결과가 ${options.outputDir || '출력 경로 없음'}에 반영되었습니다. ${options.adminFinalPassGuide}`;
    }
    return '오케스트레이션 응답을 수신했습니다. 상세 결과 패널을 확인해 주세요.';
}
