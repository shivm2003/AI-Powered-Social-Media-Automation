import { NextResponse } from "next/server";
import { runAutomationCommand } from "@/lib/automation";
import { v4 as uuidv4 } from "uuid";
import fs from "fs";
import path from "path";

// Active unfollow jobs tracker for in-memory status polling
const activeUnfollowJobs = new Map();

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const jobId = searchParams.get("jobId");

    // If polling an active unfollow job
    if (jobId && activeUnfollowJobs.has(jobId)) {
      const job = activeUnfollowJobs.get(jobId);
      return NextResponse.json({ success: true, job });
    }

    // Otherwise, fetch live following accounts from Instagram
    const result = await runAutomationCommand({
      action: "ig_get_following_list",
      max_count: 50,
    }, 60000);

    return NextResponse.json({
      success: true,
      username: result.username || "loansolutions2026",
      totalFollowing: result.total_following || 0,
      accounts: result.accounts || [],
      message: result.message || "",
      status: result.status,
    });
  } catch (error) {
    console.error("GET /api/growth/instagram-unfollow error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function POST(request) {
  try {
    const body = await request.json();
    const {
      targetCount = 10, // 0 means all
      specificUsers = null,
      safetyDelay = 10,
    } = body;

    const jobId = uuidv4();
    const jobData = {
      id: jobId,
      status: "running",
      targetCount,
      specificUsers,
      safetyDelay,
      unfollowedCount: 0,
      unfollowedAccounts: [],
      logs: ["Unfollow sequence initiated. Connecting to Instagram profile..."],
      startedAt: new Date().toISOString(),
    };
    activeUnfollowJobs.set(jobId, jobData);

    // Launch automation asynchronously
    runAutomationCommand({
      action: "ig_unfollow_accounts",
      target_count: targetCount,
      specific_users: specificUsers,
      safety_delay: safetyDelay,
      campaign_id: jobId,
    }, 600000).then((res) => {
      const updated = activeUnfollowJobs.get(jobId) || jobData;
      updated.status = res.status === "completed" ? "completed" : (res.status === "stopped" ? "stopped" : "failed");
      updated.unfollowedCount = res.unfollowed_count || 0;
      updated.unfollowedAccounts = res.unfollowed_accounts || [];
      if (res.logs && Array.isArray(res.logs)) {
        updated.logs = res.logs;
      }
      activeUnfollowJobs.set(jobId, updated);
    }).catch((err) => {
      console.error(`Error in unfollow job ${jobId}:`, err);
      const updated = activeUnfollowJobs.get(jobId) || jobData;
      updated.status = "failed";
      updated.logs.push(`Error: ${err.message}`);
      activeUnfollowJobs.set(jobId, updated);
    });

    return NextResponse.json({
      success: true,
      jobId,
      message: `Started Instagram unfollow task (target=${targetCount || "ALL"})`,
    });
  } catch (error) {
    console.error("POST /api/growth/instagram-unfollow error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function DELETE(request) {
  try {
    const { searchParams } = new URL(request.url);
    const jobId = searchParams.get("jobId");

    if (!jobId) {
      return NextResponse.json({ error: "Missing jobId parameter" }, { status: 400 });
    }

    const dataDir = path.join(process.cwd(), "data");
    if (!fs.existsSync(dataDir)) {
      fs.mkdirSync(dataDir, { recursive: true });
    }

    const stopFlagPath = path.join(dataDir, `stop_${jobId}.flag`);
    fs.writeFileSync(stopFlagPath, "STOP", "utf-8");

    if (activeUnfollowJobs.has(jobId)) {
      const job = activeUnfollowJobs.get(jobId);
      job.status = "stopped";
      job.logs.push("🛑 Stop signal written to disk.");
      activeUnfollowJobs.set(jobId, job);
    }

    return NextResponse.json({
      success: true,
      message: `Stop flag set for unfollow job ${jobId}`,
    });
  } catch (error) {
    console.error("DELETE /api/growth/instagram-unfollow error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
