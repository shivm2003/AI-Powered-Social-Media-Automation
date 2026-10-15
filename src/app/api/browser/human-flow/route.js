import { NextResponse } from "next/server";
import { runAutomationCommand } from "@/lib/automation";

export async function POST(request) {
  try {
    const body = await request.json();
    const {
      platform = "gemini",
      query = "Search and create a high converting viral marketing post for our product.",
    } = body;

    const cleanPlatform = ["gemini", "chatgpt"].includes(platform.toLowerCase())
      ? platform.toLowerCase()
      : "gemini";

    const cleanQuery = (query || "").trim();
    if (!cleanQuery) {
      return NextResponse.json(
        { error: "Search query or prompt is required." },
        { status: 400 }
      );
    }

    const result = await runAutomationCommand(
      {
        action: "human_flow",
        platform: cleanPlatform,
        query: cleanQuery,
      },
      120000 // 2 minute timeout for human-paced execution
    );

    return NextResponse.json({
      success: true,
      data: result,
      message: `Successfully executed human-like workflow on ${cleanPlatform.toUpperCase()} with account 2003shivam1990@gmail.com!`,
    });
  } catch (error) {
    console.error("Human automation workflow error:", error);
    return NextResponse.json(
      {
        error: error.message || "Failed to execute human flow.",
      },
      { status: 500 }
    );
  }
}
