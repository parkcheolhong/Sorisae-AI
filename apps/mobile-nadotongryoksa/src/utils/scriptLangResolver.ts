/**
 * (G5) TTS 로케일 스크립트-누수 교정 단일 SSOT.
 *
 * 백엔드 `backend/llm/voice_gateway.py:_detect_dominant_script_lang` 와 1:1 동일한
 * 9-스크립트 우세 판정 로직. 대면(App.tsx inferTtsLanguage)·VoIP(resolveVoipTtsLocale)가
 * 각자 다른(5종/0종) 교정기를 두던 것을 이 한 곳으로 수렴시킨다.
 *
 * Edge 뉴럴 TTS / 단말 음성팩 모두 텍스트 스크립트와 보이스 언어가 불일치하면 발음이
 * 깨지거나(라틴권=영어로 읽음) 오디오가 거부되므로, 실제 글자 스크립트에 맞는 로케일로
 * 교정해 50개국 일관 발화를 보장한다. 라틴 등 다국어 공유 스크립트는 모호 → null.
 */

/** 텍스트의 우세 스크립트를 감지해 언어 코드를 돌려준다(가나가 하나라도 있으면 ja 확정). */
export function detectDominantScriptLang(text: string): string | null {
    const counts: Record<string, number> = {};
    for (const ch of String(text || '')) {
        const code = ch.codePointAt(0) ?? 0;
        if ((code >= 0xac00 && code <= 0xd7a3) || (code >= 0x1100 && code <= 0x11ff)) {
            counts.ko = (counts.ko ?? 0) + 1;
        } else if (code >= 0x3040 && code <= 0x30ff) {
            counts.ja = (counts.ja ?? 0) + 1; // 히라가나/가타카나 → 일본어 확정
        } else if (code >= 0x4e00 && code <= 0x9fff) {
            counts.zh = (counts.zh ?? 0) + 1; // CJK 한자(가나 없으면 중국어)
        } else if (code >= 0x0400 && code <= 0x04ff) {
            counts.ru = (counts.ru ?? 0) + 1;
        } else if (code >= 0x0600 && code <= 0x06ff) {
            counts.ar = (counts.ar ?? 0) + 1;
        } else if (code >= 0x0e00 && code <= 0x0e7f) {
            counts.th = (counts.th ?? 0) + 1;
        } else if (code >= 0x0590 && code <= 0x05ff) {
            counts.he = (counts.he ?? 0) + 1;
        } else if (code >= 0x0900 && code <= 0x097f) {
            counts.hi = (counts.hi ?? 0) + 1;
        } else if (code >= 0x0370 && code <= 0x03ff) {
            counts.el = (counts.el ?? 0) + 1;
        }
    }
    const keys = Object.keys(counts);
    if (keys.length === 0) {
        return null;
    }
    if (counts.ja) {
        return 'ja';
    }
    return keys.reduce((best, key) => (counts[key] > counts[best] ? key : best));
}

/**
 * 스크립트 누수 교정된 TTS 로케일을 돌려준다.
 * 텍스트의 우세 스크립트가 타깃 언어와 다르면 실제 스크립트 언어 로케일로 교정,
 * 같거나 모호(라틴 등)하면 타깃 로케일 그대로.
 *
 * @param resolveLocale 스크립트 언어 코드 → BCP-47 로케일 매퍼(대면/voip 공용 SSOT 주입)
 */
export function correctTtsLocaleForScriptLeak(
    text: string,
    targetLocale: string,
    resolveLocale: (lang: string) => string,
): string {
    const targetLang = String(targetLocale || '').split('-')[0].toLowerCase();
    const scriptLang = detectDominantScriptLang(text);
    if (scriptLang && scriptLang !== targetLang) {
        const corrected = resolveLocale(scriptLang);
        if (corrected) {
            return corrected;
        }
    }
    return targetLocale;
}
