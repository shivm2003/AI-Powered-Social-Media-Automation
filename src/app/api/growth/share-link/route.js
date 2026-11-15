import { NextResponse } from "next/server";
import { createGrowthCampaign, getGrowthCampaignById, updateGrowthCampaignStatus, getAllGrowthCampaigns } from "@/lib/db";
import { runAutomationCommand } from "@/lib/automation";
import { v4 as uuidv4 } from "uuid";

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get("id");

    if (id) {
      const campaign = await getGrowthCampaignById(id);
      if (!campaign) {
        return NextResponse.json({ error: "Task not found" }, { status: 404 });
      }
      return NextResponse.json({ success: true, task: campaign });
    }

    // Get recent post share tasks (location starts with http)
    const all = await getAllGrowthCampaigns(50);
    const postShareTasks = (all || []).filter(
      (c) => c.location && (c.location.startsWith("http://") || c.location.startsWith("https://"))
    );
    return NextResponse.json({ success: true, tasks: postShareTasks });
  } catch (error) {
    console.error("GET /api/growth/share-link error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function POST(request) {
  try {
    const body = await request.json();
    const {
      postUrl,
      platform = "auto",
      shareAll = true,
      targetCount = 30,
      safetyDelay = 8,
      accountId,
      profileDir,
    } = body;

    if (!postUrl || !postUrl.trim().startsWith("http")) {
      return NextResponse.json(
        { error: "A valid post URL is required (must start with http:// or https://)" },
        { status: 400 }
      );
    }

    const cleanUrl = postUrl.trim();

    // Auto-detect platform if requested
    let effectivePlatform = platform;
    if (effectivePlatform === "auto") {
      if (cleanUrl.includes("instagram.com") || cleanUrl.includes("instagr.am")) {
        effectivePlatform = "instagram";
      } else if (cleanUrl.includes("facebook.com")) {
        effectivePlatform = "facebook";
      } else {
        effectivePlatform = "both";
      }
    }

    const taskId = uuidv4();
    const count = parseInt(targetCount, 10) || 30;
    const delay = parseInt(safetyDelay, 10) || 8;

    // 1. Create tracking record in DB
    await createGrowthCampaign({
      id: taskId,
      platform: effectivePlatform,
      location: cleanUrl,
      target_count: shareAll ? 9999 : count,
      safety_delay_seconds: delay,
      status: "running",
      logs: [
        `🔗 Manual post share initiated for ${effectivePlatform.toUpperCase()}`,
        `📎 Target URL: ${cleanUrl}`,
        `🎯 Mode: ${shareAll ? "Share to ALL Friends/Followers" : `Target up to ${count} friends`}`,
        `⏳ Pacing: ${delay}s human-touch anti-spam delay`,
      ],
    });

    // 2. Launch automation in background
    const effectiveTimeoutMs = Math.max(600000, count * 30000);
    runAutomationCommand(
      {
        action: "share_manual_post_link",
        campaign_id: taskId,
        post_url: cleanUrl,
        platform: effectivePlatform,
        share_all: Boolean(shareAll),
        target_count: count,
        safety_delay: delay,
        account_id: accountId,
        profile_dir: profileDir,
      },
      effectiveTimeoutMs
    ).catch((err) => {
      console.error(`Post share command error for ${taskId}:`, err);
      updateGrowthCampaignStatus(taskId, "failed", { logs: [err.message] });
    });

    return NextResponse.json({
      success: true,
      taskId,
      platform: effectivePlatform,
      message: `Manual post share started for ${effectivePlatform}`,
    });
  } catch (error) {
    console.error("POST /api/growth/share-link error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function DELETE(request) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get("id");

    if (!id) {
      return NextResponse.json({ error: "Task ID required" }, { status: 400 });
    }

    await updateGrowthCampaignStatus(id, "stopped", {
      logs: ["Post sharing stopped by user request"],
    });

    try {
      await runAutomationCommand(
        {
          action: "growth_stop",
          campaign_id: id,
        },
        5000
      );
    } catch (cmdErr) {
      console.warn("Notice during post share stop command:", cmdErr.message);
    }

    return NextResponse.json({ success: true, message: "Post share task stopped successfully" });
  } catch (error) {
    console.error("DELETE /api/growth/share-link error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

