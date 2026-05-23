import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({ refreshedAt: new Date().toISOString() });
}
