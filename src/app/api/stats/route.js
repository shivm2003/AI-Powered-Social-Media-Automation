import { NextResponse } from "next/server";
import { getDashboardStats } from "@/lib/db";

export async function GET() {
  try {
    const stats = getDashboardStats();
    // Parse JSON fields in recent campaigns
    stats.recentCampaigns = stats.recentCampaigns.map((c) => ({
      ...c,
      platforms: JSON.parse(c.platforms || "[]"),
      media_paths: JSON.parse(c.media_paths || "[]"),
    }));
    return NextResponse.json(stats);
  } catch (error) {
    console.error("Error fetching stats:", error);
    return NextResponse.json({ error: "Failed to fetch stats" }, { status: 500 });
  }
}
