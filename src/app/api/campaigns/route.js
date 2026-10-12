import { NextResponse } from "next/server";
import { getAllCampaigns, createCampaign, deleteCampaign } from "@/lib/db";
import { v4 as uuidv4 } from "uuid";

export async function GET() {
  try {
    const campaigns = getAllCampaigns();
    const parsed = campaigns.map((c) => ({
      ...c,
      platforms: JSON.parse(c.platforms || "[]"),
      media_paths: JSON.parse(c.media_paths || "[]"),
    }));
    return NextResponse.json(parsed);
  } catch (error) {
    console.error("Error fetching campaigns:", error);
    return NextResponse.json({ error: "Failed to fetch campaigns" }, { status: 500 });
  }
}

export async function POST(request) {
  try {
    const body = await request.json();
    const campaign = {
      id: uuidv4(),
      ...body,
    };
    createCampaign(campaign);
    return NextResponse.json({ id: campaign.id, message: "Campaign created" }, { status: 201 });
  } catch (error) {
    console.error("Error creating campaign:", error);
    return NextResponse.json({ error: "Failed to create campaign" }, { status: 500 });
  }
}
