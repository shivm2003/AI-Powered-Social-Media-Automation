import { NextResponse } from "next/server";
import { runAutomationCommand } from "@/lib/automation";
import { v4 as uuidv4 } from "uuid";
import fs from "fs";
import path from "path";

// Active accept jobs tracker for in-memory status polling
const activeJobs = new Map();

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const jobId = searchParams.get("jobId");

    // If polling an active job
    if (jobId && activeJobs.has(jobId)) {
      const job = activeJobs.get(jobId);
      return NextResponse.json({ success: true, job });
    }

    // Otherwise, fetch live count from Facebook
    const result = await runAutomationCommand({
      action: "fb_get_pending_requests",
      max_scrolls: 2,
    }, 60000);

    return NextResponse.json({
      success: true,
      count: result.count || 0,
      titleBadge: result.title_badge || "",
      requests: result.requests || [],
      message: result.message || "",
      status: result.status,
    });
  } catch (error) {
    console.error("GET /api/growth/requests error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function POST(request) {
  try {
    const body = await request.json();
    const {
      targetCount = 0, // 0 means all
      likeRecent = false,
      safetyDelay = 3,
    } = body;

    const jobId = uuidv4();
    const jobData = {
      id: jobId,
      status: "running",
      targetCount,
      likeRecent,
      safetyDelay,
      acceptedCount: 0,
      likedCount: 0,
      acceptedPeople: [],
      logs: ["Acceptance sequence initiated. Connecting to Facebook..."],
      startedAt: new Date().toISOString(),
    };
    activeJobs.set(jobId, jobData);

    // Launch automation asynchronously
    runAutomationCommand({
      action: "fb_accept_requests",
      target_count: targetCount,
      like_recent: likeRecent,
      safety_delay: safetyDelay,
      campaign_id: jobId,
    }, 600000).then((res) => {
      const updated = activeJobs.get(jobId) || jobData;
      updated.status = res.status === "success" ? "completed" : "failed";
      updated.acceptedCount = res.accepted_count || 0;
      updated.likedCount = res.liked_count || 0;
      updated.acceptedPeople = res.accepted_people || [];
      if (res.logs && Array.isArray(res.logs)) {
        updated.logs = res.logs;
      }
      activeJobs.set(jobId, updated);
    }).catch((err) => {
      console.error(`Error in accept job ${jobId}:`, err);
      const updated = activeJobs.get(jobId) || jobData;
      updated.status = "failed";
      updated.logs.push(`Error: ${err.message}`);
      activeJobs.set(jobId, updated);
    });

    return NextResponse.json({
      success: true,
      jobId,
      message: `Started accepting Facebook friend requests (like_recent=${likeRecent})`,
    });
  } catch (error) {
    console.error("POST /api/growth/requests error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function DELETE(request) {
  try {
    const { searchParams } = new URL(request.url);
    const jobId = searchParams.get("jobId");

    if (jobId) {
      // Write stop flag file
      const projectRoot = process.cwd();
      const flagPath = path.join(projectRoot, "data", `stop_${jobId}.flag`);
      fs.mkdirSync(path.dirname(flagPath), { recursive: true });
      fs.writeFileSync(flagPath, "STOP", "utf-8");

      if (activeJobs.has(jobId)) {
        const job = activeJobs.get(jobId);
        job.status = "stopped";
        job.logs.push("Accepting halted by user request.");
        activeJobs.set(jobId, job);
      }
    }

    return NextResponse.json({ success: true, message: "Stop signal dispatched." });
  } catch (error) {
    console.error("DELETE /api/growth/requests error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
