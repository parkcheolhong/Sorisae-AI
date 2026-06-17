import axios from 'axios';

function resolveConfiguredApiUrl(): string {
    const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
    return configured && configured.length > 0 ? configured : 'http://localhost:8000';
}

function isDirectLocalBackendUrl(value: string | undefined): boolean {
    const normalized = String(value || '').trim().toLowerCase();
    return normalized.startsWith('http://localhost:8000') || normalized.startsWith('http://127.0.0.1:8000');
}

export function resolveBackendDocsUrl(apiBaseUrl?: string): string {
    const normalizedBase = String(apiBaseUrl || resolveApiBaseUrl()).trim().replace(/\/$/, '');

    if (typeof window !== 'undefined') {
        const { hostname, origin, port, protocol } = window.location;
        const isLocalHost = hostname === 'localhost' || hostname === '127.0.0.1';
        const isDirectFrontendDevPort = port === '3000' || port === '3005';
        const isGatewayPort = port === '8080' || port === '8443';

        if (isDirectFrontendDevPort && protocol !== 'https:') {
            return `${origin.replace(/\/$/, '')}/docs`;
        }

        if (normalizedBase === origin.replace(/\/$/, '') && isLocalHost) {
            return `${origin.replace(/\/$/, '')}/docs`;
        }

        if (!isLocalHost || isGatewayPort || protocol === 'https:') {
            return `${origin.replace(/\/$/, '')}/docs`;
        }
    }

    return `${normalizedBase}/docs`;
}

export function resolveApiBaseUrl(): string {
    if (typeof window !== 'undefined') {
        const { hostname, origin, port, protocol } = window.location;
        const isLocalHost = hostname === 'localhost' || hostname === '127.0.0.1';
        const isDirectFrontendDevPort = port === '3000' || port === '3005';
        const isGatewayPort = port === '8080' || port === '8443';

        if (isDirectFrontendDevPort && protocol !== 'https:') {
            // Keep browser traffic same-origin so Next.js can proxy and backend restarts do not surface as direct localhost failures.
            const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
            return isDirectLocalBackendUrl(configured) ? origin : (configured && configured.length > 0 ? configured : origin);
        }

        if (!isLocalHost || isGatewayPort || protocol === 'https:') {
            return origin;
        }
    }

    return resolveConfiguredApiUrl();
}

export const api = axios.create({
    baseURL: typeof window !== 'undefined' ? resolveApiBaseUrl() : resolveConfiguredApiUrl(),
    headers: { 'Content-Type': 'application/json' },
});
