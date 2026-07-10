import { NextResponse } from "next/server";

const BACKEND =
  process.env.API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

export async function GET() {
  let apiOk = false;
  try {
    const res = await fetch(`${BACKEND.replace(/\/$/, "")}/health`, { cache: "no-store" });
    apiOk = res.ok;
  } catch {
    apiOk = false;
  }
  return NextResponse.json({
    web: "ok",
    api: apiOk ? "ok" : "unreachable",
    api_url_configured: Boolean(process.env.API_URL || process.env.NEXT_PUBLIC_API_URL),
  });
}
