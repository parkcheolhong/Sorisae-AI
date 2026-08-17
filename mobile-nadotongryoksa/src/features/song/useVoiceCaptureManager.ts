import { useCallback, useEffect, useRef, useState, type Dispatch, type SetStateAction } from 'react';
import { Alert, Platform } from 'react-native';
import * as DocumentPicker from 'expo-document-picker';
import * as FileSystem from 'expo-file-system/legacy';

import { Audio, type AudioRecording } from '../../compat/expoAvAudio';
import { APP_ALERT_TEXT } from '../../app/appConstants';
import { acquireVoiceCapture, releaseVoiceCapture } from '../../services/voiceCaptureLease';
import { getFeatureUiText } from '../i18n/featureUiCatalog';
import type {
    SongFileJobStatus,
    VoiceConsentResponse,
    VoiceLicenseMode,
    VoiceOutputScope,
    VoicePreviewResponse,
    VoiceProfileResponse,
} from '../../app/appTypes';

type VoiceCaptureManagerDeps = {
    songFileJob: SongFileJobStatus | null;
    isVoiceRecording: boolean;
    createVoiceConsent: () => Promise<VoiceConsentResponse>;
    createVoiceProfile: (asset: DocumentPicker.DocumentPickerAsset, consentId: string) => Promise<VoiceProfileResponse>;
    deleteVoiceProfile: (profileId: string) => Promise<void>;
    createVoicePreview: (params: {
        jobId: string;
        voiceProfileId: string;
        licenseMode: VoiceLicenseMode;
        outputScope: VoiceOutputScope;
        rightsAcknowledged: boolean;
    }) => Promise<VoicePreviewResponse>;
};

type VoiceCaptureManagerState = {
    voiceConsent: VoiceConsentResponse | null;
    voiceProfile: VoiceProfileResponse | null;
    voiceProfileLoading: boolean;
    voiceProfileRecording: boolean;
    voiceProfileStatus: string;
    voicePreview: VoicePreviewResponse | null;
    voiceLicenseMode: VoiceLicenseMode;
    setVoiceLicenseMode: Dispatch<SetStateAction<VoiceLicenseMode>>;
    voiceOutputScope: VoiceOutputScope;
    setVoiceOutputScope: Dispatch<SetStateAction<VoiceOutputScope>>;
    voiceRightsAcknowledged: boolean;
    setVoiceRightsAcknowledged: Dispatch<SetStateAction<boolean>>;
    handlePickVoiceSample: () => Promise<void>;
    handleToggleVoiceSampleRecording: () => Promise<void>;
    handleDeleteVoiceProfile: () => Promise<void>;
    handleCreateVoicePreview: () => Promise<void>;
};

export function useVoiceCaptureManager(deps: VoiceCaptureManagerDeps): VoiceCaptureManagerState {
    const [voiceConsent, setVoiceConsent] = useState<VoiceConsentResponse | null>(null);
    const [voiceProfile, setVoiceProfile] = useState<VoiceProfileResponse | null>(null);
    const [voiceProfileLoading, setVoiceProfileLoading] = useState(false);
    const [voiceProfileRecording, setVoiceProfileRecording] = useState(false);
    const [voiceProfileStatus, setVoiceProfileStatus] = useState('');
    const [voicePreview, setVoicePreview] = useState<VoicePreviewResponse | null>(null);
    const [voiceLicenseMode, setVoiceLicenseMode] = useState<VoiceLicenseMode>('private_preview_unverified');
    const [voiceOutputScope, setVoiceOutputScope] = useState<VoiceOutputScope>('private_preview');
    const [voiceRightsAcknowledged, setVoiceRightsAcknowledged] = useState(false);

    const voiceProfileRecordingRef = useRef<AudioRecording | null>(null);

    const ensureVoiceConsent = useCallback(async (): Promise<VoiceConsentResponse> => {
        if (voiceConsent?.status === 'active') {
            return voiceConsent;
        }

        const createdConsent = await deps.createVoiceConsent();
        setVoiceConsent(createdConsent);
        return createdConsent;
    }, [deps, voiceConsent]);

    const createVoiceProfileFromAsset = useCallback(async (asset: DocumentPicker.DocumentPickerAsset) => {
        setVoiceProfileLoading(true);
        setVoiceProfileStatus(getFeatureUiText('song.voiceSamplePreparing'));
        try {
            const consent = await ensureVoiceConsent();
            const createdProfile = await deps.createVoiceProfile(asset, consent.consent_id);
            setVoiceProfile(createdProfile);
            setVoicePreview(null);
            setVoiceProfileStatus(getFeatureUiText('song.voiceProfileReadyEncrypted', {
                quality: (createdProfile.sample_quality_score * 100).toFixed(0),
            }));
        } catch (error) {
            const message = error instanceof Error ? error.message : getFeatureUiText('song.voiceSampleUploadFailed');
            setVoiceProfileStatus(message);
            Alert.alert(APP_ALERT_TEXT.voiceSampleErrorTitle, message);
        } finally {
            setVoiceProfileLoading(false);
        }
    }, [deps, ensureVoiceConsent]);

    const handlePickVoiceSample = useCallback(async () => {
        if (voiceProfileLoading) {
            return;
        }

        const picked = await DocumentPicker.getDocumentAsync({
            type: ['audio/mpeg', 'audio/mp4', 'audio/m4a', 'audio/wav', 'audio/x-wav', 'audio/webm', 'audio/*'],
            copyToCacheDirectory: true,
            multiple: false,
        });

        if (picked.canceled || !picked.assets?.length) {
            setVoiceProfileStatus(getFeatureUiText('song.voiceSampleCanceled'));
            return;
        }

        await createVoiceProfileFromAsset(picked.assets[0]);
    }, [createVoiceProfileFromAsset, voiceProfileLoading]);

    const stopVoiceSampleRecording = useCallback(async (options?: { releaseLease?: boolean }) => {
        const releaseLease = options?.releaseLease ?? true;
        const recording = voiceProfileRecordingRef.current;
        voiceProfileRecordingRef.current = null;
        setVoiceProfileRecording(false);

        if (!recording) {
            if (releaseLease) {
                releaseVoiceCapture('song');
            }
            return;
        }

        setVoiceProfileLoading(true);
        try {
            await recording.stopAndUnloadAsync();
            await Audio.setAudioModeAsync({
                allowsRecordingIOS: false,
                playsInSilentModeIOS: true,
                shouldDuckAndroid: true,
                playThroughEarpieceAndroid: false,
            });
            const uri = recording.getURI();
            if (!uri) {
                throw new Error('녹음 파일을 찾을 수 없습니다.');
            }

            const consent = await ensureVoiceConsent();
            const createdProfile = await deps.createVoiceProfile({
                uri,
                name: Platform.OS === 'ios' ? 'voice-sample.wav' : 'voice-sample.m4a',
                mimeType: Platform.OS === 'ios' ? 'audio/wav' : 'audio/m4a',
            } as DocumentPicker.DocumentPickerAsset, consent.consent_id);
            setVoiceProfile(createdProfile);
            setVoicePreview(null);
            setVoiceProfileStatus(getFeatureUiText('song.recordedProfileReady', {
                quality: (createdProfile.sample_quality_score * 100).toFixed(0),
            }));
            FileSystem.deleteAsync(uri, { idempotent: true }).catch(() => { /* no-op */ });
        } catch (error) {
            const message = error instanceof Error ? error.message : getFeatureUiText('song.voiceRecordingUploadFailed');
            setVoiceProfileStatus(message);
            Alert.alert(APP_ALERT_TEXT.voiceRecordingErrorTitle, message);
        } finally {
            if (releaseLease) {
                releaseVoiceCapture('song');
            }
            setVoiceProfileLoading(false);
        }
    }, [deps, ensureVoiceConsent]);

    const handleToggleVoiceSampleRecording = useCallback(async () => {
        if (voiceProfileLoading) {
            return;
        }
        if (deps.isVoiceRecording) {
            Alert.alert(APP_ALERT_TEXT.voiceRecordingWaitTitle, APP_ALERT_TEXT.voiceRecordingWaitBody);
            return;
        }

        if (!voiceProfileRecording) {
            try {
                const { granted } = await Audio.requestPermissionsAsync();
                if (!granted) {
                    Alert.alert(APP_ALERT_TEXT.microphonePermissionTitle, APP_ALERT_TEXT.microphonePermissionBody);
                    return;
                }

                await Audio.setAudioModeAsync({
                    allowsRecordingIOS: true,
                    playsInSilentModeIOS: true,
                    staysActiveInBackground: false,
                    shouldDuckAndroid: false,
                    playThroughEarpieceAndroid: false,
                });
                acquireVoiceCapture('song', () => {
                    void stopVoiceSampleRecording({ releaseLease: false });
                });

                const { recording } = await Audio.Recording.createAsync({
                    android: {
                        extension: '.m4a',
                        outputFormat: 2,
                        audioEncoder: 3,
                        sampleRate: 16000,
                        numberOfChannels: 1,
                        bitRate: 64000,
                    },
                    ios: {
                        extension: '.wav',
                        audioQuality: 127,
                        sampleRate: 16000,
                        numberOfChannels: 1,
                        bitRate: 128000,
                        linearPCMBitDepth: 16,
                        linearPCMIsBigEndian: false,
                        linearPCMIsFloat: false,
                    },
                    web: { mimeType: 'audio/webm', bitsPerSecond: 128000 },
                    isMeteringEnabled: false,
                    keepAudioActiveHint: false,
                });
                voiceProfileRecordingRef.current = recording;
                setVoiceProfileRecording(true);
                setVoiceProfileStatus(getFeatureUiText('song.voiceSampleRecording'));
            } catch {
                releaseVoiceCapture('song');
                setVoiceProfileStatus(getFeatureUiText('song.voiceSampleRecordingStartFailed'));
            }
            return;
        }

        await stopVoiceSampleRecording({ releaseLease: true });
    }, [deps.isVoiceRecording, stopVoiceSampleRecording, voiceProfileLoading, voiceProfileRecording]);

    const handleDeleteVoiceProfile = useCallback(async () => {
        if (!voiceProfile) {
            return;
        }

        setVoiceProfileLoading(true);
        try {
            await deps.deleteVoiceProfile(voiceProfile.voice_profile_id);
            setVoiceProfile(null);
            setVoicePreview(null);
            setVoiceProfileStatus(getFeatureUiText('song.voiceProfileDeleted'));
        } catch (error) {
            const message = error instanceof Error ? error.message : getFeatureUiText('song.voiceProfileDeleteFailed');
            setVoiceProfileStatus(message);
        } finally {
            setVoiceProfileLoading(false);
        }
    }, [deps, voiceProfile]);

    const handleCreateVoicePreview = useCallback(async () => {
        if (!deps.songFileJob || deps.songFileJob.status !== 'completed') {
            Alert.alert(APP_ALERT_TEXT.fileSubtitleRequiredTitle, APP_ALERT_TEXT.fileSubtitleRequiredBody);
            return;
        }
        if (!voiceProfile) {
            Alert.alert(APP_ALERT_TEXT.voiceProfileRequiredTitle, APP_ALERT_TEXT.voiceProfileRequiredBody);
            return;
        }

        setVoiceProfileLoading(true);
        setVoiceProfileStatus(getFeatureUiText('song.voicePreviewPolicyChecking'));
        try {
            const preview = await deps.createVoicePreview({
                jobId: deps.songFileJob.job_id,
                voiceProfileId: voiceProfile.voice_profile_id,
                licenseMode: voiceLicenseMode,
                outputScope: voiceOutputScope,
                rightsAcknowledged: voiceRightsAcknowledged,
            });
            setVoicePreview(preview);
            setVoiceProfileStatus(`${preview.message} · ${preview.effective_output_scope}`);
        } catch (error) {
            const message = error instanceof Error ? error.message : getFeatureUiText('song.voicePreviewFailed');
            setVoiceProfileStatus(message);
        } finally {
            setVoiceProfileLoading(false);
        }
    }, [deps, voiceLicenseMode, voiceOutputScope, voiceProfile, voiceRightsAcknowledged]);

    useEffect(() => {
        return () => {
            voiceProfileRecordingRef.current?.stopAndUnloadAsync().catch(() => { /* no-op */ });
            voiceProfileRecordingRef.current = null;
            releaseVoiceCapture('song');
        };
    }, []);

    return {
        voiceConsent,
        voiceProfile,
        voiceProfileLoading,
        voiceProfileRecording,
        voiceProfileStatus,
        voicePreview,
        voiceLicenseMode,
        setVoiceLicenseMode,
        voiceOutputScope,
        setVoiceOutputScope,
        voiceRightsAcknowledged,
        setVoiceRightsAcknowledged,
        handlePickVoiceSample,
        handleToggleVoiceSampleRecording,
        handleDeleteVoiceProfile,
        handleCreateVoicePreview,
    };
}