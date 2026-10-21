import { NextResponse } from "next/server";
import { resolveWikiLink } from "@/lib/vault";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const target = url.searchParams.get("target") ?? "";
  if (!target) {
    return NextResponse.json({ error: "missing target" }, { status: 400 });
  }
  const slug = await resolveWikiLink(target);
  return NextResponse.json({ target, slug });
}
