import { createFourFeatureKernel } from '../fourFeatureKernel';
import {
    activateFeatureExclusive,
    deactivateFeatureExclusive,
    getActiveFeatureId,
    getFeatureLeaseOwner,
    registerFeatureQuiesceHandlers,
    startFeatureLease,
    stopFeatureLease,
} from '../fourFeatureRuntime';

describe('fourFeatureKernel ownership arbitration', () => {
    it('blocks second owner on the same exclusive resource', () => {
        const kernel = createFourFeatureKernel();

        const first = kernel.claim('mic-capture', 'face-translate');
        const second = kernel.claim('mic-capture', 'voip-call');

        expect(first).toEqual({ ok: true });
        expect(second).toEqual({ ok: false, owner: 'face-translate' });
        expect(kernel.getOwner('mic-capture')).toBe('face-translate');
    });

    it('releases all owned resources on stop command', () => {
        const kernel = createFourFeatureKernel();

        kernel.claim('mic-capture', 'sorisae-ai');
        kernel.claim('tts-playback', 'sorisae-ai');

        const events = kernel.handleLifecycleCommand({
            featureId: 'sorisae-ai',
            command: 'stop',
            reason: 'test_stop',
            source: 'system',
            atMs: 1,
        });

        expect(kernel.getOwner('mic-capture')).toBeNull();
        expect(kernel.getOwner('tts-playback')).toBeNull();
        expect(events.some((event) => event.type === 'resource-release')).toBe(true);
    });
});

describe('fourFeatureRuntime shared kernel integration', () => {
    beforeEach(() => {
        deactivateFeatureExclusive('face-translate', 'test_reset', 'system');
        deactivateFeatureExclusive('voip-call', 'test_reset', 'system');
        deactivateFeatureExclusive('pstn-assist', 'test_reset', 'system');
        deactivateFeatureExclusive('sorisae-ai', 'test_reset', 'system');
        registerFeatureQuiesceHandlers('face-translate', null);
        registerFeatureQuiesceHandlers('voip-call', null);
        registerFeatureQuiesceHandlers('pstn-assist', null);
        registerFeatureQuiesceHandlers('sorisae-ai', null);
    });

    afterEach(() => {
        deactivateFeatureExclusive('face-translate', 'test_cleanup', 'system');
        deactivateFeatureExclusive('voip-call', 'test_cleanup', 'system');
        deactivateFeatureExclusive('pstn-assist', 'test_cleanup', 'system');
        deactivateFeatureExclusive('sorisae-ai', 'test_cleanup', 'system');
        registerFeatureQuiesceHandlers('face-translate', null);
        registerFeatureQuiesceHandlers('voip-call', null);
        registerFeatureQuiesceHandlers('pstn-assist', null);
        registerFeatureQuiesceHandlers('sorisae-ai', null);
    });

    it('keeps the original owner when a conflicting feature starts', () => {
        const faceStart = startFeatureLease('face-translate', 'test_face_start', 'system');
        const voipStart = startFeatureLease('voip-call', 'test_voip_start', 'system');

        expect(faceStart.ok).toBe(true);
        expect(voipStart.ok).toBe(false);
        expect(getFeatureLeaseOwner('mic-capture')).toBe('face-translate');
    });

    it('allows next feature to own resources after previous one stops', () => {
        startFeatureLease('face-translate', 'test_face_start', 'system');
        stopFeatureLease('face-translate', 'test_face_stop', 'system');

        const voipStart = startFeatureLease('voip-call', 'test_voip_start', 'system');

        expect(voipStart.ok).toBe(true);
        expect(getFeatureLeaseOwner('mic-capture')).toBe('voip-call');
    });

    it('enforces single-active policy with deterministic quiesce ordering', async () => {
        const steps: string[] = [];
        registerFeatureQuiesceHandlers('face-translate', {
            stopCapture: () => {
                steps.push('capture_stop');
            },
            stopPlayback: () => {
                steps.push('playback_stop');
            },
        });

        const first = await activateFeatureExclusive('face-translate', 'test_face_start', 'user');
        const second = await activateFeatureExclusive('pstn-assist', 'test_pstn_start', 'user');

        expect(first.ok).toBe(true);
        expect(second.ok).toBe(true);
        expect(steps).toEqual(['capture_stop', 'playback_stop']);
        expect(getActiveFeatureId()).toBe('pstn-assist');
    });

    it('rolls back to previous feature when transition quiesce fails', async () => {
        registerFeatureQuiesceHandlers('face-translate', {
            stopCapture: () => {
                throw new Error('quiesce_capture_fail');
            },
            stopPlayback: () => {
                // no-op
            },
            restore: () => {
                // no-op
            },
        });

        const first = await activateFeatureExclusive('face-translate', 'test_face_start', 'user');
        const second = await activateFeatureExclusive('voip-call', 'test_voip_start', 'user');

        expect(first.ok).toBe(true);
        expect(second.ok).toBe(false);
        expect(second.rolledBack).toBe(true);
        expect(getActiveFeatureId()).toBe('face-translate');
    });
});
