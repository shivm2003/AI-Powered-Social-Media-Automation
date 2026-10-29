import { NextResponse } from "next/server";
import { createGrowthCampaign, getAllGrowthCampaigns, getGrowthCampaignById, updateGrowthCampaignStatus } from "@/lib/db";
import { runAutomationCommand } from "@/lib/automation";
import { v4 as uuidv4 } from "uuid";

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get("id");

    if (id) {
      const campaign = await getGrowthCampaignById(id);
      if (!campaign) {
        return NextResponse.json({ error: "Campaign not found" }, { status: 404 });
      }
      return NextResponse.json({ success: true, campaign });
    }

    const campaigns = await getAllGrowthCampaigns(50);
    return NextResponse.json({ success: true, campaigns });
  } catch (error) {
    console.error("GET /api/growth error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function POST(request) {
  try {
    const body = await request.json();
    const {
      platform = "both",
      location = "New Delhi",
      targetCount = 10,
      safetyDelay = 15,
      mode = "location",
      accountId,
      profileDir,
      account_id,
      profile_dir,
    } = body;

    const effectiveAccountId = accountId || account_id;
    const effectiveProfileDir = profileDir || profile_dir;

    const campaignId = uuidv4();
    const effectiveLocation = mode === "suggestions" 
      ? (location || "Suggested Accounts (PYMK)")
      : mode === "random" 
        ? (location || "Random Explore Feed")
        : (location || "New Delhi");

    // 1. Create record in DB
    await createGrowthCampaign({
      id: campaignId,
      platform,
      location: effectiveLocation,
      target_count: parseInt(targetCount, 10),
      safety_delay_seconds: parseInt(safetyDelay, 10),
      status: "running",
      logs: [`Outreach initiated from Web Dashboard | Mode: ${mode}${effectiveProfileDir ? ` | Profile: ${effectiveProfileDir}` : ""}`],
    });

    // 2. Launch execution via automation runner with dynamic timeout based on request count
    const effectiveTimeoutMs = Math.max(600000, parseInt(targetCount, 10) * 35000);
    runAutomationCommand({
      action: "growth_outreach",
      campaign_id: campaignId,
      platform,
      location: effectiveLocation,
      mode,
      target_count: parseInt(targetCount, 10),
      safety_delay: parseInt(safetyDelay, 10),
      account_id: effectiveAccountId,
      profile_dir: effectiveProfileDir,
    }, effectiveTimeoutMs).catch((err) => {
      console.error(`Growth outreach process error for ${campaignId}:`, err);
      updateGrowthCampaignStatus(campaignId, "failed", { logs: [err.message] });
    });

    return NextResponse.json({
      success: true,
      campaignId,
      message: `Outreach campaign started for ${platform} (${mode})`,
    });
  } catch (error) {
    console.error("POST /api/growth error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function DELETE(request) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get("id");

    if (!id) {
      return NextResponse.json({ error: "Campaign ID required" }, { status: 400 });
    }

    // 1. Immediately update database status so the UI stops polling immediately
    await updateGrowthCampaignStatus(id, "stopped", {
      logs: ["Stopped by user request"],
    });

    // 2. Call python stop command with graceful error handling
    try {
      await runAutomationCommand({
        action: "growth_stop",
        campaign_id: id,
      }, 5000);
    } catch (cmdErr) {
      console.warn("Notice during python stop command execution:", cmdErr.message);
    }

    return NextResponse.json({ success: true, message: "Campaign stopped successfully" });
  } catch (error) {
    console.error("DELETE /api/growth error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
