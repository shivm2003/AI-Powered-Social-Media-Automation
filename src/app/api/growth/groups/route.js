import { NextResponse } from "next/server";
import { createSocialGroup, getAllSocialGroups, getSocialGroupById, updateSocialGroup } from "@/lib/db";
import { runAutomationCommand } from "@/lib/automation";
import { v4 as uuidv4 } from "uuid";

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get("id");

    if (id) {
      const group = await getSocialGroupById(id);
      if (!group) {
        return NextResponse.json({ error: "Group not found" }, { status: 404 });
      }
      return NextResponse.json({ success: true, group });
    }

    const groups = await getAllSocialGroups(50);
    return NextResponse.json({ success: true, groups });
  } catch (error) {
    console.error("GET /api/growth/groups error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function POST(request) {
  try {
    const body = await request.json();
    const {
      platform = "facebook",
      groupType = "community_group",
      groupName = "My Community Group",
      privacy = "private",
      initialMessage = "",
      maxInvites = 50,
    } = body;

    const taskId = uuidv4();

    // 1. Create record in DB
    const record = await createSocialGroup({
      id: taskId,
      platform,
      group_type: groupType,
      group_name: groupName,
      status: "creating",
      logs: ["Social group creation initiated from Web Dashboard"],
    });

    // 2. Launch automation in background
    runAutomationCommand({
      action: "create_social_group",
      task_id: taskId,
      platform,
      group_type: groupType,
      group_name: groupName,
      privacy,
      initial_message: initialMessage,
      max_invites: parseInt(maxInvites, 10),
    }, 600000).catch((err) => {
      console.error(`Social group task error for ${taskId}:`, err);
      updateSocialGroup(taskId, "failed", { logs: [err.message] });
    });

    return NextResponse.json({
      success: true,
      taskId,
      group: record,
      message: `Group creation started for ${platform} (${groupType})`,
    });
  } catch (error) {
    console.error("POST /api/growth/groups error:", error);
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

    await updateSocialGroup(id, "stopped", {
      logs: ["Group creation cancelled by user"],
    });

    try {
      await runAutomationCommand({
        action: "stop_social_group",
        task_id: id,
      }, 5000);
    } catch (cmdErr) {
      console.warn("Notice during group stop command execution:", cmdErr.message);
    }

    return NextResponse.json({ success: true, message: "Group task stopped successfully" });
  } catch (error) {
    console.error("DELETE /api/growth/groups error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
