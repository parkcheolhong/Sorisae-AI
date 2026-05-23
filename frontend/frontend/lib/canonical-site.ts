const DEFAULT_ADMIN_SITE_ORIGIN = 'https://개발분석114.com';
const DEFAULT_MARKETPLACE_SITE_ORIGIN = 'https://metanova1004.com';

function normalizePath(path: string, fallback: string): string {
    const raw = (path || fallback || '/').trim();
    if (!raw) {
        return fallback || '/';
    }
    return raw.startsWith('/') ? raw : `/${raw}`;
}

function resolveOrigin(siteType: 'admin' | 'marketplace'): string {
    if (siteType === 'admin') {
        return (process.env.NEXT_PUBLIC_ADMIN_SITE_ORIGIN || DEFAULT_ADMIN_SITE_ORIGIN).trim();
    }
    return (process.env.NEXT_PUBLIC_MARKETPLACE_SITE_ORIGIN || DEFAULT_MARKETPLACE_SITE_ORIGIN).trim();
}

function buildAbsoluteSiteHref(siteType: 'admin' | 'marketplace', path: string, fallbackPath: string): string {
    const normalizedPath = normalizePath(path, fallbackPath);
    const forceAbsolute = (process.env.NEXT_PUBLIC_FORCE_CANONICAL_SITE_HREF || '').trim().toLowerCase();
    if (!['1', 'true', 'yes'].includes(forceAbsolute)) {
        return normalizedPath;
    }
    const origin = resolveOrigin(siteType);
    try {
        return new URL(normalizedPath, origin).toString();
    } catch {
        return normalizedPath;
    }
}

export function resolveMarketplaceSiteHref(path = '/marketplace'): string {
    return buildAbsoluteSiteHref('marketplace', path, '/marketplace');
}

export function resolveAdminSiteHref(path = '/admin'): string {
    return buildAbsoluteSiteHref('admin', path, '/admin');
}

export function resolveStaffSiteHref(path = '/staff/login'): string {
    return resolveAdminSiteHref(path || '/staff/login');
}
