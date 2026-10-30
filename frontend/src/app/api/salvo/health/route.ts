import { NextResponse } from "next/server";

const SALVO_API_URL = process.env.SALVO_API_URL || process.env.NEXT_PUBLIC_SALVO_API || "http://127.0.0.1:4173";

export async function GET() {
  try {
    const res = await fetch(`${SALVO_API_URL}/api/health`, {
      signal: AbortSignal.timeout(1500),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json({ ...data, status: "online", proxy: true });
    }
  } catch {
    // Engine offline
  }

  return NextResponse.json({
    status: "offline",
    engine: "salvo-core",
    port: 4173,
    degradedMode: true,
    message: "Engine offline. Local pipeline cache active.",
  });
}
