const RELAY_NEUTRAL_CHAR = /[\s\d.,!?;:'"()[\]{}<>/\\|@#$%^&*+=~`\-—…·]/u;

const RELAY_LANG_CHAR_CHECKS: Record<string, RegExp> = {
  ko: /[\uAC00-\uD7A3\u3131-\u318E]/u,
  en: /[A-Za-z]/,
  ja: /[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]/u,
  zh: /[\u4E00-\u9FFF]/u,
  'zh-tw': /[\u4E00-\u9FFF]/u,
  vi: /[\u00C0-\u024FA-Za-z\u1E00-\u1EFF]/u,
  th: /[\u0E00-\u0E7F]/u,
  ar: /[\u0600-\u06FF]/u,
  ru: /[\u0400-\u04FF]/u,
};

export const DESIGNATED_LANGUAGE_MISMATCH_MESSAGE =
  '지정 언어와 다른 언어가 감지되었습니다. 프로필에서 설정한 언어로만 말씀하거나 입력해 주세요. 필요하면 설정에서 언어를 변경할 수 있습니다.';

export function normalizeDesignatedLanguage(value?: string | null): string | null {
  const normalized = String(value || '').trim().toLowerCase().split('-')[0];
  return normalized || null;
}

function charMatchesDesignatedLanguage(char: string, designatedLang: string): boolean {
  if (RELAY_NEUTRAL_CHAR.test(char)) {
    return true;
  }
  const pattern = RELAY_LANG_CHAR_CHECKS[designatedLang];
  if (pattern?.test(char)) {
    return true;
  }
  if (!RELAY_LANG_CHAR_CHECKS[designatedLang] && /[A-Za-z\u00C0-\u024F]/u.test(char)) {
    return true;
  }
  return false;
}

export function textMatchesDesignatedLanguage(
  text: string,
  designatedLang?: string | null,
  minMatchRatio = 0.70,
): boolean {
  const normalizedLang = normalizeDesignatedLanguage(designatedLang);
  const trimmed = String(text || '').trim();
  if (!trimmed) {
    return false;
  }
  if (!normalizedLang) {
    return true;
  }

  const compact = trimmed.replace(RELAY_NEUTRAL_CHAR, '');
  if (!compact) {
    return true;
  }

  const letterLike = [...compact].filter((char) => !RELAY_NEUTRAL_CHAR.test(char));
  if (letterLike.length === 0) {
    return true;
  }

  const allowed = letterLike.filter((char) => charMatchesDesignatedLanguage(char, normalizedLang)).length;
  return allowed / letterLike.length >= minMatchRatio;
}

export function detectedLanguageMatchesDesignated(
  detectedLang?: string | null,
  designatedLang?: string | null,
): boolean {
  const normalizedDetected = normalizeDesignatedLanguage(detectedLang);
  const normalizedDesignated = normalizeDesignatedLanguage(designatedLang);
  if (!normalizedDesignated) {
    return true;
  }
  if (!normalizedDetected) {
    return true;
  }
  return normalizedDetected === normalizedDesignated;
}
