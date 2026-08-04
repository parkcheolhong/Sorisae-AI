import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json(
    {
      provider: "DevAnalysis114 Admin",
      passkey: true,
      rpId: "xn--114-2p7l635dz3bh5j.com",
      origins: ["https://xn--114-2p7l635dz3bh5j.com"],
    },
    {
      headers: {
        "Cache-Control": "no-store",
      },
    },
  );
}
