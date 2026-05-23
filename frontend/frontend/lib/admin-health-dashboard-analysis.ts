import type { HealthDiagnostics } from '@/lib/admin-health-analysis';
import type { SystemResourceCard } from '@/lib/admin-dashboard-ui-types';
import type { AdminAlertItem, LlmStatus } from '@/lib/admin-runtime-types';

export function buildAdminLlmGpuLayersLabel(llmStatus: LlmStatus | null): string {
    if (llmStatus?.gpu_runtime_label) {
        return llmStatus.gpu_runtime_label;
    }
    const rawLayers = llmStatus?.n_gpu_layers;
    if (Number.isFinite(rawLayers)) {
        return `GPU ${rawLayers} layers`;
    }
    if (llmStatus?.acceleration_mode === 'cpu_only') {
        return 'CPU 전용';
    }
    if (llmStatus?.num_gpu === -1) {
        return 'GPU 전체 오프로딩';
    }
    if (Number.isFinite(llmStatus?.num_gpu) && (llmStatus?.num_gpu ?? 0) > 0) {
        return `GPU ${llmStatus?.num_gpu}개 사용`;
    }
    return llmStatus?.loaded
        ? 'GPU 구성 확인 대기'
        : '연결 확인 중';
}

export function buildAdminSystemResourceCards(healthDiagnostics: HealthDiagnostics | undefined): SystemResourceCard[] {
    const memory = healthDiagnostics?.resources?.memory;
    const cpu = healthDiagnostics?.resources?.cpu;
    const gpu = healthDiagnostics?.resources?.gpu;
    const redisQueue = healthDiagnostics?.resources?.redis_queue;
    const adWorker = healthDiagnostics?.resources?.ad_worker;

    return [
        {
            id: 'memory',
            title: '메모리',
            icon: '🧠',
            state: (memory?.state as 'ok' | 'warning' | 'critical') || 'warning',
            value: memory?.available
                ? `${memory.usage_percent ?? 0}% 사용`
                : '미수집',
            detail: memory?.available
                ? `${memory.used_mb ?? 0} / ${memory.total_mb ?? 0} MB`
                : (memory?.note || '메모리 진단 정보 없음'),
            action: memory?.note || '메모리 캐시와 동시 작업 수를 점검하세요.',
            apiPath: '/api/health',
        },
        {
            id: 'cpu',
            title: 'CPU',
            icon: '🧮',
            state: (cpu?.state as 'ok' | 'warning' | 'critical') || 'warning',
            value: cpu?.usage_percent != null
                ? `${cpu.usage_percent}% 부하`
                : '미수집',
            detail: cpu?.usage_percent != null
                ? `load ${cpu.load_1m ?? '-'} / core ${cpu.cpu_count ?? '-'}`
                : (cpu?.note || 'CPU 진단 정보 없음'),
            action: cpu?.note || '워커 수와 CPU fallback 실행 여부를 점검하세요.',
            apiPath: '/api/health',
        },
        {
            id: 'gpu',
            title: 'GPU',
            icon: '🎮',
            state: (gpu?.state as 'ok' | 'warning' | 'critical') || 'warning',
            value: gpu?.available
                ? `util ${gpu.peak_utilization_percent ?? 0}%`
                : '미감지',
            detail: gpu?.available
                ? `VRAM ${gpu.peak_memory_usage_percent ?? 0}% · ${gpu.device_count ?? 0}대`
                : (gpu?.note || 'GPU 진단 정보 없음'),
            action: gpu?.note || 'GPU 드라이버와 모델 프로필을 점검하세요.',
            apiPath: '/api/health',
        },
        {
            id: 'redis_queue',
            title: 'Redis Queue',
            icon: '🧵',
            state: (redisQueue?.state as 'ok' | 'warning' | 'critical') || 'warning',
            value: redisQueue?.available
                ? `depth ${redisQueue.queue_depth ?? 0}`
                : '미연결',
            detail: redisQueue?.connection_id
                ? `${redisQueue.connection_id} / ${redisQueue.queue_name ?? '-'}`
                : (redisQueue?.note || 'Redis queue 진단 정보 없음'),
            action: redisQueue?.note || 'REDIS_URL과 queue 연결 상태를 점검하세요.',
            apiPath: '/api/health',
        },
        {
            id: 'ad_worker',
            title: 'Ad Worker',
            icon: '🛠️',
            state: (adWorker?.state as 'ok' | 'warning' | 'critical') || 'warning',
            value: adWorker?.available
                ? 'heartbeat 정상'
                : '미기동',
            detail: adWorker?.worker_id
                ? `${adWorker.worker_id} / ${adWorker.heartbeat_age_sec ?? '-'}초 / order ${adWorker.last_order_id ?? '-'}`
                : (adWorker?.note || '광고 주문 worker 진단 정보 없음'),
            action: adWorker?.note || 'worker 실행 진입점과 heartbeat를 점검하세요.',
            apiPath: '/api/health',
        },
    ];
}

export function buildAdminOpsAlerts(options: {
    healthDiagnostics: HealthDiagnostics | undefined;
    hasOrchestratorCapabilityError: boolean;
    hasOrchestratorCapabilityWarning: boolean;
}): AdminAlertItem[] {
    const alerts: AdminAlertItem[] = [];

    for (const alert of options.healthDiagnostics?.alerts || []) {
        alerts.push({
            id: `health-${alert.id}`,
            level: alert.severity,
            title: alert.title,
            message: alert.message,
            action: alert.action,
            source: 'system',
            apiPath: '/api/health',
        });
    }

    if (options.hasOrchestratorCapabilityError) {
        alerts.push({
            id: 'orchestrator-error',
            level: 'critical',
            title: '오케스트레이터 오류',
            message: '오케스트레이터 기능군 중 오류 상태가 감지되었습니다.',
            action: '상세 제어에서 최신 self-run 실패 원인과 산출물 미달 기준을 확인하세요.',
            source: 'orchestrator',
            apiPath: '/api/admin/orchestrator/capabilities/summary',
        });
    } else if (options.hasOrchestratorCapabilityWarning) {
        alerts.push({
            id: 'orchestrator-warning',
            level: 'warning',
            title: '오케스트레이터 주의',
            message: '오케스트레이터 기능군 중 주의 상태가 감지되었습니다.',
            action: '상세 제어에서 누락 파일, 변경 디렉터리, 코드량 기준을 재점검하세요.',
            source: 'orchestrator',
            apiPath: '/api/admin/orchestrator/capabilities/summary',
        });
    }

    return alerts.sort((left, right) => {
        const weight = { critical: 2, warning: 1 };
        return weight[right.level] - weight[left.level];
    });
}

export function assertAdminHealthDashboardAnalysisContract() {
    const labels = buildAdminLlmGpuLayersLabel({
        loaded: true,
        model_path: 'sample',
        n_ctx: 1,
        n_batch: 1,
        acceleration_mode: 'cpu_only',
    });
    const cards = buildAdminSystemResourceCards(undefined);
    const alerts = buildAdminOpsAlerts({
        healthDiagnostics: undefined,
        hasOrchestratorCapabilityError: false,
        hasOrchestratorCapabilityWarning: true,
    });
    if (labels !== 'CPU 전용' || cards.length !== 5 || alerts[0]?.id !== 'orchestrator-warning') {
        throw new Error('admin health dashboard analysis contract 누락: health dashboard 해석 기본 규칙 필요');
    }
}
