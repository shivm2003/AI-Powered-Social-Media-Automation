import { NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";

/**
 * GET /api/prompt-verifier
 * Returns agent readiness and active AI tabs on port 9222.
 */
export async function GET() {
  try {
    const pythonScript = path.join(process.cwd(), "automation", "llm", "prompt_paste_verifier_agent.py");

    return NextResponse.json({
      status: "ready",
      agent: "PromptPasteVerifierAgent",
      supported_platforms: ["gemini", "chatgpt"],
      description: "Verifies whether prompts are pasted properly in ChatGPT/Gemini, and actively pastes & activates them if not.",
    });
  } catch (err) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

/**
 * POST /api/prompt-verifier
 * Body: { platform?: "gemini" | "chatgpt" | "auto", prompt?: string, verifyOnly?: boolean }
 */
export async function POST(req) {
  try {
    const body = await req.json().catch(() => ({}));
    const platform = body.platform || "auto";
    const prompt = body.prompt || "";
    const verifyOnly = Boolean(body.verifyOnly);

    const scriptPath = path.join(process.cwd(), "automation", "llm", "prompt_paste_verifier_agent.py");
    const args = ["-u", scriptPath];

    if (platform !== "auto") {
      args.push("--platform", platform);
    }
    if (verifyOnly) {
      args.push("--verify-only");
    } else {
      args.push("--test");
    }

    return new Promise((resolve) => {
      const py = spawn("python", args, {
        cwd: process.cwd(),
        env: { ...process.env, PYTHONIOENCODING: "utf-8" },
      });

      let stdout = "";
      let stderr = "";

      py.stdout.on("data", (data) => {
        stdout += data.toString();
      });

      py.stderr.on("data", (data) => {
        stderr += data.toString();
      });

      py.on("close", (code) => {
        resolve(
          NextResponse.json({
            success: code === 0,
            exitCode: code,
            platform,
            output: stdout,
            error: stderr || null,
          })
        );
      });

      // 30s timeout guard
      setTimeout(() => {
        try {
          py.kill();
        } catch (_) {}
        resolve(
          NextResponse.json(
            { success: false, error: "Prompt verifier agent timed out after 30 seconds" },
            { status: 504 }
          )
        );
      }, 30000);
    });
  } catch (err) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
