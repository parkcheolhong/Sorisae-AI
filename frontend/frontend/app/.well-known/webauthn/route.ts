import { NextRequest, NextResponse } from "next/server";

function isLoopbackHost(host: string | null | undefined): boolean {
  const normalized = (host || '').split(',')[0].trim().toLowerCase();
  return normalized === 'localhost' || normalized === '127.0.0.1' || normalized === '::1';
}

function resolveOrigin(request: NextRequest): string {
  const forwardedProto = request.headers.get("x-forwarded-proto")?.split(",")[0]?.trim();
  const forwardedHost = request.headers.get("x-forwarded-host")?.split(",")[0]?.trim();
  const requestHost = request.headers.get("host")?.split(",")[0]?.trim();
  const trustedHost = forwardedHost && !isLoopbackHost(forwardedHost) ? forwardedHost : requestHost || "metanova1004.com";
  const host = trustedHost || "metanova1004.com";
  const protocol = forwardedProto || (isLoopbackHost(host) ? "http" : "https");
  return `${protocol}://${host}`;
}

function resolveRpId(origin: string): string {
  try {
    const host = new URL(origin).hostname.toLowerCase();
    if (host === "127.0.0.1" || host === "::1") {
      return "localhost";
    }
    return host || "localhost";
  } catch {
    return "localhost";
  }
}

export async function GET(request: NextRequest) {
  const origin = resolveOrigin(request);
  const rpId = resolveRpId(origin);

  return NextResponse.json(
    {
      provider: "DevAnalysis114 Admin",
      passkey: true,
      rpId,
      origins: [origin],
    },
    {
      headers: {
        "Cache-Control": "no-store",
      },
    },
  );
}
