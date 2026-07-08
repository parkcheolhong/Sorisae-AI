export type NetworkTransportKind = 'wifi' | 'cellular' | 'ethernet' | 'none' | 'unknown';

export type CellularGeneration = '2g' | '3g' | '4g' | '5g';

export type NetworkDiagnosticsSnapshot = {
    transport: NetworkTransportKind;
    cellularGeneration: CellularGeneration | null;
    isConnected: boolean;
    isInternetReachable: boolean | null;
    carrier: string | null;
    ssid: string | null;
    label: string;
    isAccurateVoipTestReady: boolean;
    /** 사용자-facing 연결 안내 (베타에서도 안심 톤) */
    statusMessage: string;
    /** QA/필드 테스트용 힌트 — UI 기본 숨김 */
    fieldTestHint: string | null;
    /** 실제 문제(오프라인 등)만 경고 */
    warningMessage: string | null;
};

type NetInfoLikeState = {
    type?: string | null;
    isConnected?: boolean | null;
    isInternetReachable?: boolean | null;
    details?: {
        cellularGeneration?: string | null;
        carrier?: string | null;
        ssid?: string | null;
    } | null;
};

const CELLULAR_GENERATIONS = new Set<CellularGeneration>(['2g', '3g', '4g', '5g']);

function normalizeTransport(type: string | null | undefined): NetworkTransportKind {
    switch (String(type || '').toLowerCase()) {
        case 'wifi':
            return 'wifi';
        case 'cellular':
            return 'cellular';
        case 'ethernet':
            return 'ethernet';
        case 'none':
            return 'none';
        default:
            return 'unknown';
    }
}

function normalizeCellularGeneration(value: string | null | undefined): CellularGeneration | null {
    const normalized = String(value || '').toLowerCase();
    return CELLULAR_GENERATIONS.has(normalized as CellularGeneration)
        ? normalized as CellularGeneration
        : null;
}

export function formatNetworkTransportLabel(snapshot: Pick<NetworkDiagnosticsSnapshot, 'transport' | 'cellularGeneration'>): string {
    if (snapshot.transport === 'cellular') {
        if (snapshot.cellularGeneration === '5g') {
            return 'LTE/5G (셀룰러)';
        }
        if (snapshot.cellularGeneration === '4g') {
            return 'LTE (4G 셀룰러)';
        }
        if (snapshot.cellularGeneration) {
            return `${snapshot.cellularGeneration.toUpperCase()} (셀룰러)`;
        }
        return '셀룰러 데이터';
    }
    if (snapshot.transport === 'wifi') {
        return 'WiFi';
    }
    if (snapshot.transport === 'ethernet') {
        return '유선 Ethernet';
    }
    if (snapshot.transport === 'none') {
        return '연결 없음';
    }
    return '알 수 없음';
}

export function buildNetworkDiagnosticsSnapshot(state: NetInfoLikeState | null): NetworkDiagnosticsSnapshot {
    const transport = normalizeTransport(state?.type);
    const cellularGeneration = transport === 'cellular'
        ? normalizeCellularGeneration(state?.details?.cellularGeneration)
        : null;
    const isConnected = Boolean(state?.isConnected);
    const isInternetReachable = typeof state?.isInternetReachable === 'boolean'
        ? state.isInternetReachable
        : null;
    const carrier = transport === 'cellular'
        ? String(state?.details?.carrier || '').trim() || null
        : null;
    const ssid = transport === 'wifi'
        ? String(state?.details?.ssid || '').trim() || null
        : null;
    const label = formatNetworkTransportLabel({ transport, cellularGeneration });

    let warningMessage: string | null = null;
    let statusMessage: string;
    let fieldTestHint: string | null = null;

    if (!isConnected || isInternetReachable === false) {
        warningMessage = '인터넷 연결이 없습니다. WiFi 또는 모바일 데이터를 켠 뒤 다시 시도해 주세요.';
        statusMessage = '연결 없음';
    } else if (transport === 'cellular') {
        statusMessage = 'LTE/5G(셀룰러) 연결됨 — VoIP·채팅 이용 가능';
        fieldTestHint = '실전 통신 QA: WiFi↔LTE 조합도 함께 확인하면 NAT·전환 이슈를 잡을 수 있습니다.';
    } else if (transport === 'wifi') {
        statusMessage = 'WiFi 연결됨 — VoIP·채팅 이용 가능';
        fieldTestHint = '실전 통신 QA: LTE/5G 데이터 경로도 함께 확인해 주세요.';
    } else if (transport === 'ethernet') {
        statusMessage = '유선 네트워크 연결됨 — VoIP·채팅 이용 가능';
    } else {
        statusMessage = '네트워크 연결됨 — VoIP·채팅 이용 가능';
    }

    return {
        transport,
        cellularGeneration,
        isConnected,
        isInternetReachable,
        carrier,
        ssid,
        label,
        isAccurateVoipTestReady: isConnected && transport === 'cellular',
        statusMessage,
        fieldTestHint,
        warningMessage,
    };
}

export function toClientNetworkContext(snapshot: NetworkDiagnosticsSnapshot): Record<string, string | boolean | null> {
    return {
        transport: snapshot.transport,
        cellular_generation: snapshot.cellularGeneration,
        label: snapshot.label,
        is_connected: snapshot.isConnected,
        is_internet_reachable: snapshot.isInternetReachable,
        carrier: snapshot.carrier,
        ssid: snapshot.ssid,
        is_accurate_voip_test_ready: snapshot.isAccurateVoipTestReady,
    };
}
