import { NextResponse } from "next/server";
import { getDashboard } from "@/lib/api";
export const dynamic = "force-dynamic";
export async function GET() {
  const data = await getDashboard();
  return NextResponse.json(data, { headers: { "Cache-Control": "no-store" } });
}
