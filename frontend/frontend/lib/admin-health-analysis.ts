export type HealthSeverity = 'ok' | 'warning' | 'critical';
export type HealthDiagnosticMetricValue = string | number | boolean | null;
export type HealthDiagnosticMetricMap = Record<string, HealthDiagnosticMetricValue>;

export interface HealthGpuDevice {
    name: string;
    memory_total_mb?: number;
    memory_used_mb?: number;
    utilization_gpu?: number;
    memory_usage_percent?: number;
}

export interface HealthResourceDiagnostic {
    available?: boolean;
    state?: HealthSeverity | string;
    note?: string;
    connection_id?: string;
    queue_name?: string;
    queue_depth?: number | null;
    worker_id?: string;
    started?: boolean;
    heartbeat_age_sec?: number | null;
    last_order_id?: number | null;
    total_mb?: number;
    used_mb?: number;
    available_mb?: number;
    usage_percent?: number;
    cpu_count?: number;
    load_1m?: number | null;
    device_count?: number;
    peak_memory_usage_percent?: number;
    peak_utilization_percent?: number;
    devices?: HealthGpuDevice[];
    error?: string | null;
}

export interface HealthAlertItem {
    id: string;
    severity: 'warning' | 'critical';
    title: string;
    message: string;
    action: string;
    source_path?: string;
    diagnostic_detail?: string;
    root_cause?: string;
    metrics?: HealthDiagnosticMetricMap;
}

export interface HealthDiagnostics {
    generated_at?: string;
    resources?: {
        memory?: HealthResourceDiagnostic;
        cpu?: HealthResourceDiagnostic;
        gpu?: HealthResourceDiagnostic;
        redis_queue?: HealthResourceDiagnostic;
        ad_worker?: HealthResourceDiagnostic;
    };
    alerts?: HealthAlertItem[];
}

export interface HealthStatus {
    status: string;
    version?: string;
    modules?: Record<string, string>;
    diagnostics?: HealthDiagnostics;
}

export function parseHealthDiagnosticMetrics(detail?: string): HealthDiagnosticMetricMap {
    const metrics: HealthDiagnosticMetricMap = {};
    if (!detail) {
        return metrics;
    }

    detail.split(/\s+/).forEach((token) => {
        const separatorIndex = token.indexOf('=');
        if (separatorIndex <= 0) {
            return;
        }

        const key = token.slice(0, separatorIndex).trim();
        const rawValue = token.slice(separatorIndex + 1).trim();
        if (!key) {
            return;
        }

        if (rawValue === 'None' || rawValue === 'null' || rawValue === '') {
            metrics[key] = null;
            return;
        }
        if (rawValue === 'True' || rawValue === 'true') {
            metrics[key] = true;
            return;
        }
        if (rawValue === 'False' || rawValue === 'false') {
            metrics[key] = false;
            return;
        }

        const numericValue = Number(rawValue);
        metrics[key] = Number.isFinite(numericValue) ? numericValue : rawValue;
    });

    return metrics;
}

export function getHealthAlertMetrics(alert: HealthAlertItem): HealthDiagnosticMetricMap {
    return alert.metrics && Object.keys(alert.metrics).length > 0
        ? alert.metrics
        : parseHealthDiagnosticMetrics(alert.diagnostic_detail);
}

export function formatHealthMetricLabel(key: string): string {
    const labels: Record<string, string> = {
        usage_percent: '사용률',
        available_mb: '여유 메모리',
        total_mb: '전체 메모리',
        load_1m: '1분 load',
        cpu_count: 'CPU 코어',
        available: 'GPU 감지',
        peak_utilization_percent: 'GPU 사용률',
        peak_memory_usage_percent: 'VRAM 점유율',
        device_count: 'GPU 대수',
        connection_id: '연결 ID',
        queue_name: '큐 이름',
        queue_depth: '큐 적체량',
        worker_id: '워커 ID',
        heartbeat_age_sec: 'Heartbeat 지연',
        last_order_id: '최근 주문 ID',
        error: '오류',
    };
    return labels[key] || key.replace(/_/g, ' ');
}

export function formatHealthMetricValue(key: string, value: HealthDiagnosticMetricValue): string {
    if (value == null) {
        return '-';
    }
    if (typeof value === 'boolean') {
        return value ? '예' : '아니오';
    }
    if (typeof value === 'number') {
        if (key.endsWith('_percent')) {
            return `${value}%`;
        }
        if (key.endsWith('_mb')) {
            return `${value} MB`;
        }
        if (key.endsWith('_sec')) {
            return `${value}초`;
        }
        return `${value}`;
    }
    return value;
}

export function getHealthAlertRootCause(alert: HealthAlertItem): string {
    if (alert.root_cause?.trim()) {
        return alert.root_cause;
    }

    const metrics = getHealthAlertMetrics(alert);
    if (alert.id === 'gpu') {
        const peakVram = typeof metrics.peak_memory_usage_percent === 'number' ? metrics.peak_memory_usage_percent : null;
        const peakUtil = typeof metrics.peak_utilization_percent === 'number' ? metrics.peak_utilization_percent : null;
        if (peakVram != null && peakVram >= 90 && peakUtil != null && peakUtil < 15) {
            return 'VRAM은 높지만 실제 연산률은 낮습니다. 로드된 모델이나 캐시가 메모리에 상주한 상태일 가능성이 큽니다.';
        }
        return 'GPU 연산 또는 VRAM 점유가 높아 대형 모델 동시 실행이나 오프로딩 설정 영향이 의심됩니다.';
    }
    if (alert.id === 'cpu') {
        return '코어 수 대비 부하가 높거나 CPU 상태 수집이 불완전합니다. 동시 작업과 백그라운드 연산을 먼저 확인해야 합니다.';
    }
    if (alert.id === 'memory') {
        return '가용 메모리가 줄어드는 구간입니다. 캐시, 워커 수, 대용량 프로세스가 메모리를 점유하고 있을 가능성이 큽니다.';
    }
    if (alert.id === 'redis_queue') {
        return '큐 연결 또는 적체 문제로 작업 전달이 지연되고 있습니다.';
    }
    if (alert.id === 'ad_worker') {
        return 'worker heartbeat 또는 주문 소비 흐름이 멈춘 상태일 수 있습니다.';
    }
    return alert.message;
}

export function assertAdminHealthAnalysisContract() {
    const parsed = parseHealthDiagnosticMetrics('usage_percent=90 available=True');
    if (parsed.usage_percent !== 90 || parsed.available !== true) {
        throw new Error('admin health analysis contract 누락: metric parser 핵심 변환 필요');
    }
}
