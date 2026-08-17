import { beforeEach, describe, expect, it, jest } from '@jest/globals';

jest.mock('../services/audioEngineKernel', () => ({
  transitionToAudioEngine: jest.fn((_featureId: string, _reason: string, handlers: {
    stopPrevious: () => void;
    startNext: () => void;
  }) => {
    handlers.stopPrevious();
    handlers.startNext();
  }),
  clearActiveAudioEngine: jest.fn(),
}));

import {
  acquireVoiceCapture,
  currentVoiceCaptureOwner,
  releaseVoiceCapture,
  resolveVoiceCaptureLeaseFeature,
  revokeCurrentVoiceCapture,
  shouldRouteMainSorisaeCapture,
} from '../services/voiceCaptureLease';

import {
  clearActiveAudioEngine,
  transitionToAudioEngine,
} from '../services/audioEngineKernel';

describe('voiceCaptureLease', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Ensure module-level lease state is reset before every test.
    revokeCurrentVoiceCapture('test_reset');
  });

  it('acquires owner and releases owner deterministically', () => {
    acquireVoiceCapture('face', jest.fn());
    expect(currentVoiceCaptureOwner()).toBe('face');

    releaseVoiceCapture('face');
    expect(currentVoiceCaptureOwner()).toBeNull();
    expect(clearActiveAudioEngine).toHaveBeenCalledWith('face', 'voice_capture_release');
  });

  it('revokes previous owner when a new owner acquires', () => {
    const revokeFace = jest.fn();
    const revokeSong = jest.fn();

    acquireVoiceCapture('face', revokeFace);
    acquireVoiceCapture('song', revokeSong);

    expect(revokeFace).toHaveBeenCalledTimes(1);
    expect(currentVoiceCaptureOwner()).toBe('song');
    expect(transitionToAudioEngine).toHaveBeenCalledTimes(2);
  });

  it('refreshes revoke callback when same owner re-acquires', () => {
    const firstRevoke = jest.fn();
    const updatedRevoke = jest.fn();

    acquireVoiceCapture('sorisae', firstRevoke);
    acquireVoiceCapture('sorisae', updatedRevoke);
    acquireVoiceCapture('inter_call', jest.fn());

    expect(firstRevoke).not.toHaveBeenCalled();
    expect(updatedRevoke).toHaveBeenCalledTimes(1);
    expect(currentVoiceCaptureOwner()).toBe('inter_call');
  });

  it('force revokes current owner and clears state', () => {
    const revokeSong = jest.fn();
    acquireVoiceCapture('song', revokeSong);

    revokeCurrentVoiceCapture('feature_switch');

    expect(revokeSong).toHaveBeenCalledTimes(1);
    expect(clearActiveAudioEngine).toHaveBeenCalledWith('song', 'feature_switch');
    expect(currentVoiceCaptureOwner()).toBeNull();
  });

  it('resolves lease ownership and sorisae routing from capture context', () => {
    expect(resolveVoiceCaptureLeaseFeature({ target: 'inter_call', songModeEnabled: false, sorisaeWindowOpen: true, faceScreenOpen: false })).toBe('inter_call');
    expect(resolveVoiceCaptureLeaseFeature({ target: 'main', songModeEnabled: true, sorisaeWindowOpen: true, faceScreenOpen: false })).toBe('song');
    expect(resolveVoiceCaptureLeaseFeature({ target: 'main', songModeEnabled: false, sorisaeWindowOpen: true, faceScreenOpen: false })).toBe('sorisae');
    expect(resolveVoiceCaptureLeaseFeature({ target: 'main', songModeEnabled: false, sorisaeWindowOpen: false, faceScreenOpen: false })).toBe('face');
    expect(shouldRouteMainSorisaeCapture({ songModeEnabled: false, sorisaeWindowOpen: true, faceScreenOpen: false })).toBe(true);
    expect(shouldRouteMainSorisaeCapture({ songModeEnabled: false, sorisaeWindowOpen: true, faceScreenOpen: true })).toBe(false);
  });
});
