/**
 * WorldLinco 디자인 시스템 토큰(SSOT) — 컬러 · 타이포 · 스페이싱 · 라운드 · 그림자.
 *
 * `docs/worldlinco-v2/APP_DESIGN.md` 의 디자인 시스템을 코드 토큰으로 옮긴 단일 진실원천이다.
 * 화면/컴포넌트는 인라인 hex 대신 본 토큰을 참조한다(브랜드 일관성·테마 전환 대비).
 *
 * 채널 컬러(`colors.channel.*`)는 `features/navigation/sectionRegistry` 의 섹션 키 및
 * `features/channelProfiles`(face/voip/chat) 정책과 시각적으로 정합한다.
 */
import { WORLDLINGO_BRAND_NAME } from '../constants/worldlincoBrand';

export const palette = {
    azure: '#1E6FE0', // Primary — 브랜드·주요 버튼·링크
    azureDark: '#1556B0',
    azureSoft: '#EAF1FC', // 연한 배경(선택/하이라이트)
    navy: '#0B2E5E', // VoIP 통화 배경·헤더
    coral: '#FF8A5B', // 핵심 CTA·마이크·통화 시작
    coralDark: '#F26A36',
    success: '#19C37D',
    warning: '#F5A623',
    danger: '#E5484D', // 통화 종료
    bg: '#F4F6FA',
    surface: '#FFFFFF',
    surfaceAlt: '#F8FAFD',
    textStrong: '#1A1F36',
    text: '#1F2937',
    textMuted: '#6B7280',
    border: '#E5E8EF',
    white: '#FFFFFF',
    black: '#000000',
} as const;

export type ColorScheme = 'light' | 'dark';

/** 의미론적 컬러 토큰 — light/dark 두 스킴이 동일 키를 채운다. */
export interface Colors {
    primary: string;
    primaryDark: string;
    primarySoft: string;
    accent: string;
    accentDark: string;
    success: string;
    warning: string;
    danger: string;

    background: string;
    /** 앱 전역 배경 그라데이션(위→아래). 소리새 하늘색 톤 — GradientBackground 래퍼에서 사용. */
    backgroundGradient: readonly string[];
    surface: string;
    surfaceAlt: string;
    border: string;

    text: string;
    textBody: string;
    textMuted: string;
    onPrimary: string;
    onAccent: string;

    /** 번역쌍 표기 규칙: 원문은 보조색·작게, 번역은 강조색·크게. */
    translationOriginal: string;
    translationPrimary: string;

    /** 채널/기능별 강조색 — sectionRegistry 키 정합. */
    channel: {
        face: string;
        voip: string;
        chat: string;
        song: string;
        booking: string;
        sorisae: string;
    };

    /** 상태 배너(연결/정보/경고) — 배경·테두리·강조 텍스트. */
    status: {
        successBg: string;
        successBorder: string;
        infoBg: string;
        infoBorder: string;
        dangerBg: string;
        dangerBorder: string;
        dangerText: string;
    };
}

/** 라이트 스킴 — 디자인 시스템 기본(마케팅/신규 화면 방향). */
export const lightColors: Colors = {
    primary: palette.azure,
    primaryDark: palette.azureDark,
    primarySoft: palette.azureSoft,
    accent: palette.coral,
    accentDark: palette.coralDark,
    success: palette.success,
    warning: palette.warning,
    danger: palette.danger,

    background: palette.bg,
    // 소리새 하늘색: 연한 스카이블루 → 화이트(전역 배경). 콘텐츠 카드는 surface 위에 떠 있음.
    backgroundGradient: ['#E3F0FF', '#F0F7FF', '#FFFFFF'],
    surface: palette.surface,
    surfaceAlt: palette.surfaceAlt,
    border: palette.border,

    text: palette.textStrong,
    textBody: palette.text,
    textMuted: palette.textMuted,
    onPrimary: palette.white,
    onAccent: palette.white,

    translationOriginal: palette.textMuted,
    translationPrimary: palette.textStrong,

    channel: {
        face: palette.azure,
        voip: palette.navy,
        chat: palette.azure,
        song: '#7C5CFC',
        booking: palette.success,
        sorisae: palette.azure,
    },

    status: {
        successBg: '#E6F7EF',
        successBorder: '#19C37D',
        infoBg: '#EAF1FC',
        infoBorder: '#1E6FE0',
        dangerBg: '#FDECEC',
        dangerBorder: '#E5484D',
        dangerText: '#B42318',
    },
};

/**
 * 다크 스킴 — **현재 출시 앱(build 111~)의 실제 GitHub-dark 팔레트**를 의미론적으로 정리한 값.
 * 기존 화면을 토큰으로 옮길 때 픽셀 변화가 없도록 실제 사용값을 그대로 채택했다.
 */
export const darkColors: Colors = {
    primary: '#1F6FEB',
    primaryDark: '#1B4FB0',
    primarySoft: '#17324D',
    accent: palette.coral,
    accentDark: palette.coralDark,
    success: '#56D364',
    warning: '#F2C078',
    danger: '#FF7B72',

    background: '#0D1117',
    // 다크 스킴은 기존 출시 룩 유지(딥 네이비 미세 그라데이션).
    backgroundGradient: ['#0D1117', '#0E1320', '#111827'],
    surface: '#111827',
    surfaceAlt: '#0F1723',
    border: '#243244',

    text: '#F0F6FC',
    textBody: '#C9D1D9',
    textMuted: '#8B949E',
    onPrimary: '#79C0FF',
    onAccent: '#FFFFFF',

    translationOriginal: '#8B949E',
    translationPrimary: '#9BE9A8',

    channel: {
        face: '#1F6FEB',
        voip: '#0B2E5E',
        chat: '#1F6FEB',
        song: '#7C5CFC',
        booking: '#56D364',
        sorisae: '#1F6FEB',
    },

    // NetworkTestBanner 의 실제 사용값(픽셀 보존).
    status: {
        successBg: '#14261A',
        successBorder: '#2F6B45',
        infoBg: '#151C28',
        infoBorder: '#2E3F58',
        dangerBg: '#241418',
        dangerBorder: '#6B2F3D',
        dangerText: '#F0A0A8',
    },
};

export const schemes: Record<ColorScheme, Colors> = {
    light: lightColors,
    dark: darkColors,
};

/** 스킴별 컬러 토큰 조회(컴포넌트에서 makeStyles(getColors(scheme)) 패턴 권장). */
export function getColors(scheme: ColorScheme): Colors {
    return schemes[scheme];
}

/**
 * 활성 컬러 스킴(앱 기본값 = 현재 출시 룩 유지를 위해 `dark`).
 * 라이트 전환 시 `setColorScheme('light')` 후 화면 재마운트/리렌더.
 */
export let activeColorScheme: ColorScheme = 'light';  // NOSONAR

export function setColorScheme(scheme: ColorScheme): void {
    activeColorScheme = scheme;
}

/** 하위호환: 기존 `colors.*` 참조 표면 — 디자인 시스템(라이트) 기준 SSOT. */
export const colors = lightColors;

/** 폰트 패밀리 — 한글 Pretendard / 라틴 Inter(폴백 system). */
export const fontFamily = {
    regular: 'Pretendard-Regular',
    medium: 'Pretendard-Medium',
    semibold: 'Pretendard-SemiBold',
    bold: 'Pretendard-Bold',
} as const;

export const fontWeight = {
    regular: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
} as const;

export const fontSize = {
    display: 32,
    title: 20,
    subtitle: 18,
    body: 16,
    label: 14,
    caption: 12,
} as const;

export const lineHeight = {
    display: 40,
    title: 28,
    subtitle: 26,
    body: 24,
    label: 20,
    caption: 16,
} as const;

/** 의미론적 텍스트 스타일(RN TextStyle 호환). */
export const typography = {
    display: {
        fontFamily: fontFamily.bold,
        fontSize: fontSize.display,
        lineHeight: lineHeight.display,
        letterSpacing: -0.2,
        color: colors.text,
    },
    title: {
        fontFamily: fontFamily.semibold,
        fontSize: fontSize.title,
        lineHeight: lineHeight.title,
        letterSpacing: -0.2,
        color: colors.text,
    },
    subtitle: {
        fontFamily: fontFamily.semibold,
        fontSize: fontSize.subtitle,
        lineHeight: lineHeight.subtitle,
        color: colors.text,
    },
    body: {
        fontFamily: fontFamily.regular,
        fontSize: fontSize.body,
        lineHeight: lineHeight.body,
        color: colors.textBody,
    },
    label: {
        fontFamily: fontFamily.medium,
        fontSize: fontSize.label,
        lineHeight: lineHeight.label,
        color: colors.textBody,
    },
    caption: {
        fontFamily: fontFamily.regular,
        fontSize: fontSize.caption,
        lineHeight: lineHeight.caption,
        color: colors.textMuted,
    },
    /** 번역 말풍선/자막 — 원문(작게·보조) + 번역(크게·강조). */
    translationOriginal: {
        fontFamily: fontFamily.regular,
        fontSize: fontSize.caption,
        lineHeight: lineHeight.caption,
        color: colors.translationOriginal,
    },
    translationPrimary: {
        fontFamily: fontFamily.semibold,
        fontSize: fontSize.subtitle,
        lineHeight: lineHeight.subtitle,
        color: colors.translationPrimary,
    },
} as const;

/** 8pt 기반 스페이싱 스케일. */
export const spacing = {
    none: 0,
    xxs: 2,
    xs: 4,
    sm: 8,
    md: 12,
    lg: 16,
    xl: 24,
    xxl: 32,
    xxxl: 48,
} as const;

export const radius = {
    sm: 6,
    md: 10,
    lg: 16,
    xl: 24,
    pill: 999,
    full: 9999,
} as const;

/** RN 그림자(iOS shadow* + Android elevation) 프리셋. */
export const shadow = {
    none: {
        shadowColor: 'transparent',
        shadowOpacity: 0,
        shadowRadius: 0,
        shadowOffset: { width: 0, height: 0 },
        elevation: 0,
    },
    card: {
        shadowColor: palette.navy,
        shadowOpacity: 0.08,
        shadowRadius: 12,
        shadowOffset: { width: 0, height: 4 },
        elevation: 3,
    },
    floating: {
        shadowColor: palette.navy,
        shadowOpacity: 0.18,
        shadowRadius: 16,
        shadowOffset: { width: 0, height: 8 },
        elevation: 8,
    },
} as const;

/** 컴포넌트 단위 토큰. */
export const components = {
    micButton: {
        size: 72,
        color: colors.accent,
        iconColor: colors.onAccent,
        ringColor: colors.accent,
    },
    sectionRail: {
        height: 64,
        activeColor: colors.primary,
        inactiveColor: colors.textMuted,
        background: colors.surface,
    },
    button: {
        height: 52,
        radius: radius.lg,
        primaryBg: colors.primary,
        primaryText: colors.onPrimary,
        secondaryBorder: colors.primary,
        secondaryText: colors.primary,
    },
    chatBubble: {
        radius: radius.lg,
        selfBg: colors.primary,
        selfText: colors.onPrimary,
        peerBg: colors.surface,
        peerText: colors.text,
    },
} as const;

export const theme = {
    brand: WORLDLINGO_BRAND_NAME,
    colors,
    palette,
    typography,
    fontFamily,
    fontWeight,
    fontSize,
    lineHeight,
    spacing,
    radius,
    shadow,
    components,
} as const;

/** 스킴별 테마 객체(컬러만 교체, 나머지 토큰 공유). */
export function getTheme(scheme: ColorScheme) {
    return { ...theme, colors: getColors(scheme) };
}

export type Theme = typeof theme;
export type ThemeColors = Colors;
export type SpacingToken = keyof typeof spacing;
export type RadiusToken = keyof typeof radius;

export default theme;
