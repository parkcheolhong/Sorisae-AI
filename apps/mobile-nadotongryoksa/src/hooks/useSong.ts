import type * as DocumentPicker from 'expo-document-picker';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  callCreateSongFileJob,
  callCreateVoiceConsent,
  callCreateVoicePreview,
  callCreateVoiceProfile,
  callDeleteVoiceProfile,
  callExportSongFileTimeline,
  callPatchSongFileSegment,
  callSongFileJobStatus,
  callSongFileTimeline,
} from '../api';
import type { LangCode } from '../features/language/languageCatalog';
import type { VoiceLicenseMode, VoiceOutputScope } from '../app/appTypes';

export function useSongJobStatus(jobId: string, enabled = true) {
  return useQuery({
    queryKey: ['song', 'job-status', jobId],
    queryFn: () => callSongFileJobStatus(jobId),
    enabled: enabled && Boolean(jobId),
    staleTime: 0,
  });
}

export function useSongTimeline(jobId: string, enabled = true) {
  return useQuery({
    queryKey: ['song', 'timeline', jobId],
    queryFn: () => callSongFileTimeline(jobId),
    enabled: enabled && Boolean(jobId),
    staleTime: 0,
  });
}

export function useSongActions() {
  const createSongJobMutation = useMutation({
    mutationFn: (params: {
      asset: DocumentPicker.DocumentPickerAsset;
      targetLanguage: LangCode;
    }) => callCreateSongFileJob(params.asset, params.targetLanguage),
  });

  const patchSegmentMutation = useMutation({
    mutationFn: (params: { jobId: string; segmentId: string; translated: string }) =>
      callPatchSongFileSegment(params.jobId, params.segmentId, params.translated),
  });

  const exportTimelineMutation = useMutation({
    mutationFn: (params: { jobId: string; format: 'srt' | 'vtt' | 'lrc' | 'json' }) =>
      callExportSongFileTimeline(params.jobId, params.format),
  });

  const createVoiceConsentMutation = useMutation({
    mutationFn: () => callCreateVoiceConsent(),
  });

  const createVoiceProfileMutation = useMutation({
    mutationFn: (params: { asset: DocumentPicker.DocumentPickerAsset; consentId: string }) =>
      callCreateVoiceProfile(params.asset, params.consentId),
  });

  const deleteVoiceProfileMutation = useMutation({
    mutationFn: (params: { profileId: string }) => callDeleteVoiceProfile(params.profileId),
  });

  const createVoicePreviewMutation = useMutation({
    mutationFn: (params: {
      jobId: string;
      voiceProfileId: string;
      licenseMode: VoiceLicenseMode;
      outputScope: VoiceOutputScope;
      rightsAcknowledged: boolean;
    }) => callCreateVoicePreview(params),
  });

  return {
    createSongJobMutation,
    patchSegmentMutation,
    exportTimelineMutation,
    createVoiceConsentMutation,
    createVoiceProfileMutation,
    deleteVoiceProfileMutation,
    createVoicePreviewMutation,
  };
}
