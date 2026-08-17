export function normalizeAuthToken(rawToken: string | null | undefined): string {
  const trimmed = String(rawToken || '').trim();
  if (!trimmed) {
    return '';
  }
  return trimmed.replace(/^Bearer\s+/i, '').trim();
}

export function buildBearerAuthHeader(rawToken: string | null | undefined): string {
  const normalized = normalizeAuthToken(rawToken);
  return normalized ? `Bearer ${normalized}` : '';
}