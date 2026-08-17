// App.tsx 에서 분리한 노래/음성 미디어 API + 공용 fetch 헬퍼.
import * as DocumentPicker from 'expo-document-picker';
import { API_BASE } from './appConstants';
import type { LangCode } from '../features/language/languageCatalog';
import type {
    SongFileJobStatus,
    SongFileTimeline,
    SongFileTimelineSegment,
    VoiceConsentResponse,
    VoiceProfileResponse,
    VoicePreviewResponse,
    VoiceLicenseMode,
    VoiceOutputScope,
} from './appTypes';

export function delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function parseApiResponse<T>(response: Response): Promise<T> {
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
        const message = typeof payload.detail === 'string' ? payload.detail : `HTTP ${response.status}`;
        throw new Error(message);
    }
    return payload as T;
}

export async function callCreateSongFileJob(asset: DocumentPicker.DocumentPickerAsset, targetLanguage: LangCode): Promise<SongFileJobStatus> {
    const formData = new FormData();
    const fileName = asset.name || `song-${Date.now()}.mp3`;
    const mimeType = asset.mimeType || 'application/octet-stream';
    if (asset.file) {
        formData.append('file', asset.file as unknown as Blob);
    } else {
        formData.append('file', { uri: asset.uri, name: fileName, type: mimeType } as unknown as Blob);
    }
    formData.append('target_language', targetLanguage);
    formData.append('source_language', 'auto');
    formData.append('quality', 'advanced');
    formData.append('mode', 'subtitle');

    // ===== REQUEST TIMING =====
    const requestStartTime = Date.now();
    const response = await fetch(`${API_BASE}/api/mobile/song-translation/jobs`, {
        method: 'POST',
        body: formData,
    });
    const requestEndTime = Date.now();
    const requestDurationMs = requestEndTime - requestStartTime;

    const result = await parseApiResponse<SongFileJobStatus>(response);
    console.log(`[MOBILE_API] POST song-translation/jobs: ${requestDurationMs}ms`);

    return result;
}

export async function callSongFileJobStatus(jobId: string): Promise<SongFileJobStatus> {
    // ===== POLLING TIMING =====
    const pollStartTime = Date.now();
    const response = await fetch(`${API_BASE}/api/mobile/song-translation/jobs/${encodeURIComponent(jobId)}`);
    const pollEndTime = Date.now();
    const pollDurationMs = pollEndTime - pollStartTime;

    const result = await parseApiResponse<SongFileJobStatus>(response);

    // Log when status changes significantly
    if (result.status === 'completed' || result.status === 'failed') {
        console.log(`[MOBILE_API] GET song-translation/jobs/${jobId}: ${pollDurationMs}ms [${result.status}]`);
    }

    return result;
}

export async function callSongFileTimeline(jobId: string): Promise<SongFileTimeline> {
    const response = await fetch(`${API_BASE}/api/mobile/song-translation/jobs/${encodeURIComponent(jobId)}/subtitles`);
    return parseApiResponse<SongFileTimeline>(response);
}

export async function callPatchSongFileSegment(jobId: string, segmentId: string, translated: string): Promise<SongFileTimelineSegment> {
    const response = await fetch(`${API_BASE}/api/mobile/song-translation/jobs/${encodeURIComponent(jobId)}/segments/${encodeURIComponent(segmentId)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ translated }),
    });
    const payload = await parseApiResponse<{ segment: SongFileTimelineSegment }>(response);
    return payload.segment;
}

export async function callExportSongFileTimeline(jobId: string, format: 'srt' | 'vtt' | 'lrc' | 'json'): Promise<string> {
    const query = new URLSearchParams({ format });
    const response = await fetch(`${API_BASE}/api/mobile/song-translation/jobs/${encodeURIComponent(jobId)}/export?${query.toString()}`);
    const text = await response.text();
    if (!response.ok) throw new Error(text || `HTTP ${response.status}`);
    return text;
}

export async function callCreateVoiceConsent(): Promise<VoiceConsentResponse> {
    const response = await fetch(`${API_BASE}/api/mobile/song-translation/voice-consents`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            consent_version: '2026-05-voice-v1',
            voice_owner: 'self',
            allow_private_preview: true,
            allow_export_for_licensed_audio: true,
            user_id: 'mobile-user',
        }),
    });
    return parseApiResponse<VoiceConsentResponse>(response);
}

export async function callCreateVoiceProfile(asset: DocumentPicker.DocumentPickerAsset, consentId: string): Promise<VoiceProfileResponse> {
    const formData = new FormData();
    const fileName = asset.name || `voice-sample-${Date.now()}.m4a`;
    const mimeType = asset.mimeType || 'audio/m4a';
    if (asset.file) {
        formData.append('sample', asset.file as unknown as Blob);
    } else {
        formData.append('sample', { uri: asset.uri, name: fileName, type: mimeType } as unknown as Blob);
    }
    formData.append('consent_id', consentId);
    formData.append('profile_label', '내 목소리');
    const response = await fetch(`${API_BASE}/api/mobile/song-translation/voice-profiles`, {
        method: 'POST',
        body: formData,
    });
    return parseApiResponse<VoiceProfileResponse>(response);
}

export async function callDeleteVoiceProfile(profileId: string): Promise<void> {
    const response = await fetch(`${API_BASE}/api/mobile/song-translation/voice-profiles/${encodeURIComponent(profileId)}`, {
        method: 'DELETE',
    });
    await parseApiResponse<{ deleted: boolean }>(response);
}

export async function callCreateVoicePreview(params: {
    jobId: string;
    voiceProfileId: string;
    licenseMode: VoiceLicenseMode;
    outputScope: VoiceOutputScope;
    rightsAcknowledged: boolean;
}): Promise<VoicePreviewResponse> {
    const response = await fetch(`${API_BASE}/api/mobile/song-translation/jobs/${encodeURIComponent(params.jobId)}/voice-preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            voice_profile_id: params.voiceProfileId,
            license_mode: params.licenseMode,
            preview_mode: 'translated_lyric_voice',
            output_scope: params.outputScope,
            rights_acknowledged: params.rightsAcknowledged,
            approval_id: params.licenseMode === 'policy_approved_distribution' ? 'mobile-admin-approved' : undefined,
        }),
    });
    return parseApiResponse<VoicePreviewResponse>(response);
}
