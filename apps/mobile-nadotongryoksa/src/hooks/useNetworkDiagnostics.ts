import { useEffect, useState } from 'react';
import NetInfo, { type NetInfoState } from '@react-native-community/netinfo';
import {
    buildNetworkDiagnosticsSnapshot,
    type NetInfoLikeState,
    type NetworkDiagnosticsSnapshot,
} from '../utils/networkDiagnostics';

const INITIAL_SNAPSHOT = buildNetworkDiagnosticsSnapshot(null);

export function useNetworkDiagnostics(enabled = true): NetworkDiagnosticsSnapshot {
    const [snapshot, setSnapshot] = useState<NetworkDiagnosticsSnapshot>(INITIAL_SNAPSHOT);

    useEffect(() => {
        if (!enabled) {
            return undefined;
        }

        let active = true;

        const applyState = (state: NetInfoState) => {
            if (!active) {
                return;
            }
            // NetInfoState 의 transport 별 details 유니온을 구조적 부분집합(NetInfoLikeState)으로 좁힌다.
            setSnapshot(buildNetworkDiagnosticsSnapshot(state as NetInfoLikeState));
        };

        void NetInfo.fetch().then(applyState).catch(() => {
            if (active) {
                setSnapshot(buildNetworkDiagnosticsSnapshot(null));
            }
        });

        const unsubscribe = NetInfo.addEventListener(applyState);
        return () => {
            active = false;
            unsubscribe();
        };
    }, [enabled]);

    return snapshot;
}
