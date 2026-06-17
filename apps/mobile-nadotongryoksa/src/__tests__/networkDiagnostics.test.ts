import {
    buildNetworkDiagnosticsSnapshot,
    formatNetworkTransportLabel,
    toClientNetworkContext,
} from '../utils/networkDiagnostics';

describe('networkDiagnostics', () => {
    it('shows friendly WiFi status for beta users without scary warnings', () => {
        const snapshot = buildNetworkDiagnosticsSnapshot({
            type: 'wifi',
            isConnected: true,
            isInternetReachable: true,
            details: { ssid: 'Lab-WiFi' },
        });

        expect(snapshot.label).toBe('WiFi');
        expect(snapshot.statusMessage).toMatch(/WiFi 연결됨/);
        expect(snapshot.warningMessage).toBeNull();
        expect(snapshot.fieldTestHint).toMatch(/LTE\/5G/);
        expect(snapshot.isAccurateVoipTestReady).toBe(false);
        expect(toClientNetworkContext(snapshot).transport).toBe('wifi');
    });

    it('labels LTE/5G cellular as ready for VoIP field testing', () => {
        const snapshot = buildNetworkDiagnosticsSnapshot({
            type: 'cellular',
            isConnected: true,
            isInternetReachable: true,
            details: {
                cellularGeneration: '5g',
                carrier: 'SKT',
            },
        });

        expect(formatNetworkTransportLabel(snapshot)).toBe('LTE/5G (셀룰러)');
        expect(snapshot.statusMessage).toMatch(/LTE\/5G/);
        expect(snapshot.isAccurateVoipTestReady).toBe(true);
        expect(snapshot.warningMessage).toBeNull();
        expect(toClientNetworkContext(snapshot).carrier).toBe('SKT');
    });

    it('warns only when offline', () => {
        const snapshot = buildNetworkDiagnosticsSnapshot({
            type: 'none',
            isConnected: false,
            isInternetReachable: false,
        });

        expect(snapshot.transport).toBe('none');
        expect(snapshot.warningMessage).toMatch(/인터넷 연결/);
    });
});
