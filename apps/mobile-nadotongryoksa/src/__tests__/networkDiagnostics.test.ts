import {
    buildNetworkDiagnosticsSnapshot,
    formatNetworkTransportLabel,
    toClientNetworkContext,
} from '../utils/networkDiagnostics';

describe('networkDiagnostics', () => {
    it('labels WiFi-only paths as not accurate for VoIP field testing', () => {
        const snapshot = buildNetworkDiagnosticsSnapshot({
            type: 'wifi',
            isConnected: true,
            isInternetReachable: true,
            details: { ssid: 'Lab-WiFi' },
        });

        expect(snapshot.label).toBe('WiFi');
        expect(snapshot.isAccurateVoipTestReady).toBe(false);
        expect(snapshot.warningMessage).toMatch(/LTE\/5G/);
        expect(toClientNetworkContext(snapshot).transport).toBe('wifi');
    });

    it('labels LTE/5G cellular as accurate for VoIP field testing', () => {
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
        expect(snapshot.isAccurateVoipTestReady).toBe(true);
        expect(snapshot.warningMessage).toBeNull();
        expect(toClientNetworkContext(snapshot).carrier).toBe('SKT');
    });

    it('warns when offline', () => {
        const snapshot = buildNetworkDiagnosticsSnapshot({
            type: 'none',
            isConnected: false,
            isInternetReachable: false,
        });

        expect(snapshot.transport).toBe('none');
        expect(snapshot.warningMessage).toMatch(/인터넷 연결/);
    });
});
