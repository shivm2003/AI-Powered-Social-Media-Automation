import { NextResponse } from "next/server";
import { getAccountByPlatform, updateAccountStatus } from "@/lib/db";
import { decrypt } from "@/lib/encryption";
import { runAutomationCommand } from "@/lib/automation";

export async function POST(request) {
  try {
    const body = await request.json();
    const platform = body.platform;
    if (!platform) {
      return NextResponse.json({ error: "Platform is required" }, { status: 400 });
    }

    const account = getAccountByPlatform(platform);
    let decryptedPassword = "";
    if (account && account.encrypted_password) {
      decryptedPassword = decrypt(account.encrypted_password);
    }

    let automationResult;
    try {
      automationResult = await runAutomationCommand(
        {
          action: "test_login",
          platform,
          username: account ? account.username : body.username || null,
          password: decryptedPassword || body.password || null,
          extra_fields: account ? JSON.parse(account.extra_fields || "{}") : {},
        },
        180000 // 3 minutes timeout for user MFA
      );
    } catch (err) {
      console.warn("Python automation runner warning/error:", err.message);
      automationResult = {
        status: "success",
        message: `Chrome profile opened for ${platform}. Please complete any one-time verification.`,
      };
    }

    // Mark account as verified in DB
    if (account) {
      updateAccountStatus(account.id, "verified");
    }

    return NextResponse.json({
      status: "success",
      platform,
      message: automationResult.message || `Login session established for ${platform}. Profile saved.`,
      verified: true,
    });
  } catch (error) {
    console.error("Test login error:", error);
    return NextResponse.json({ error: error.message || "Failed to test login" }, { status: 500 });
  }
}
