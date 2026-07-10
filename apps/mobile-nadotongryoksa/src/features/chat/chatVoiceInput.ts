// 채팅 음성(마이크) 입력 순수 헬퍼 SSOT.
// - 녹음 → 서버 STT(voiceTranslate.original_text) → 입력칸 채움 흐름의 순수 로직만 담는다.
// - 부수효과(녹음/파일/네트워크)는 useChatVoiceInput 훅이 담당하고, 여기서는 테스트 가능한 결정만 둔다.

// base64 오디오 최소 길이(이보다 짧으면 빈 녹음/소음으로 보고 STT를 생략).
export const MIN_VOICE_BASE64_LEN = 800;

// STT 호출용 언어쌍 결정.
// 채팅 입력칸에 말하는 주체는 **로컬 사용자**이므로, STT 원문은 항상 사용자 자신의
// 지정 언어(selfLang)다. 따라서 from 은 'auto' 가 아니라 사용자 언어로 **고정(designated)**
// 한다. (designated 경로는 detected_from_lang=from_lang 으로 고정하므로 from='auto' 면
// 'auto' 에서 번역을 시도해 422/오류로 실패한다 — 그게 마이크 STT 작동불능의 원인이었다.)
// - mode: 양쪽 언어를 모두 알면 'bilingual'(face 자동감지, 사용자가 상대 언어로 말해도 처리),
//   한쪽만 알면 'designated'(face/voip 공통, 화자 언어 고정 STT).
// - to: 번역 결과는 쓰지 않고 original_text 만 사용하지만 voiceTranslate 계약상 필수라 채운다.
export interface VoiceSttLangs {
    from: string;
    to: string;
    langA: string;
    langB: string;
    mode: 'designated' | 'bilingual';
}

function normalizeLang(value?: string | null): string {
    const normalized = String(value ?? '').trim().toLowerCase();
    return normalized && normalized !== 'auto' ? normalized : '';
}

export function resolveVoiceSttLangs(
    selfLang?: string | null,
    counterpartLang?: string | null,
): VoiceSttLangs {
    const self = normalizeLang(selfLang) || 'ko';
    const counterpart = normalizeLang(counterpartLang);
    if (counterpart && counterpart !== self) {
        // 양쪽 언어를 알면 bilingual 로 사용자가 자기/상대 언어 중 무엇으로 말해도 자동 감지.
        return { from: self, to: counterpart, langA: self, langB: counterpart, mode: 'bilingual' };
    }
    // 한쪽만 알면 화자(사용자) 언어로 고정한 designated STT.
    return { from: self, to: self, langA: self, langB: self, mode: 'designated' };
}

// STT 원문 정리: 앞뒤 공백/제어문자 제거, 내부 연속 공백 1칸으로 축약.
export function cleanVoiceTranscript(text?: string | null): string {
    const raw = String(text ?? '');
    // eslint-disable-next-line no-control-regex
    const noControl = raw.replace(/[\u0000-\u001f\u007f]/g, ' ');
    return noControl.replace(/\s+/g, ' ').trim();
}

// 기존 입력 초안에 STT 결과를 합칠 때의 텍스트 결합 규칙.
// - 초안이 비어 있으면 STT 결과만, 있으면 공백 한 칸으로 이어 붙인다.
export function mergeTranscriptIntoDraft(draft: string, transcript: string): string {
    const cleanedDraft = String(draft ?? '');
    const cleaned = cleanVoiceTranscript(transcript);
    if (!cleaned) {
        return cleanedDraft;
    }
    if (!cleanedDraft.trim()) {
        return cleaned;
    }
    return `${cleanedDraft.replace(/\s+$/, '')} ${cleaned}`;
}

// base64 오디오가 STT 를 시도할 만큼 충분한지.
export function isVoiceAudioLongEnough(base64?: string | null): boolean {
    return Boolean(base64) && String(base64).length >= MIN_VOICE_BASE64_LEN;
}
