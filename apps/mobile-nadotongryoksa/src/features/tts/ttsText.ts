// [기능 분리 Phase5.5 선행] 공용 발화(TTS) 텍스트 헬퍼 — 대면/소리새/노래가 공유.
// 발화 직전 텍스트 정규화 + 발화 로케일 결정(스크립트 누수 교정 SSOT 위임). 순수, React 상태 비의존.
// App.tsx 모놀리스에서 추출. 로케일 교정 로직은 scriptLangResolver/voipLanguageLocales 에 위임(중복 금지).

import { resolveVoipTtsLocale } from '../../constants/voipLanguageLocales';
import { correctTtsLocaleForScriptLeak } from '../../utils/scriptLangResolver';

/** 발화 직전 텍스트 정규화 — `(offline)`/`[offline]` 마커 제거 후 트림. */
export function normalizeSpeakText(text: string): string {
    return text
        .replace(/\(offline\)/gi, '')
        .replace(/\[offline\]/gi, '')
        .trim();
}

// 발화 로케일 SSOT(50개국 정확 발화의 핵심).
// 라틴·키릴·아랍·데바나가리·한자처럼 여러 언어가 공유하는 스크립트를 '스크립트만'으로
// 추정하면 스페인어/베트남어=영어, 우크라이나어=러시아어, 일본어(한자)=중국어처럼
// 50개국 언어가 엉뚱한 음성으로 뭉개진다. 따라서 지정 타깃 언어 로케일(fallback)을 신뢰하고,
// 번역문이 '단일 언어 전용' 스크립트(한글/가나/타이/히브리/그리스)로 샌 경우에만 그 언어로 교정한다.
export function inferTtsLanguage(text: string, fallback: string): string {
    const target = fallback && fallback.includes('-') ? fallback : 'en-US';
    // (G5) 스크립트 누수 교정 단일 SSOT 위임 — 백엔드 9-스크립트 로직과 동일하며,
    // 기존 5종(ko/ja/th/he/el)은 동일 로케일을 유지하고 zh/ru/ar/hi 4종을 추가 커버한다.
    return correctTtsLocaleForScriptLeak(text, target, (lang) => resolveVoipTtsLocale(lang));
}
