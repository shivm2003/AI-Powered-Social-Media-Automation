import { NextResponse } from "next/server";
import { execFile } from "child_process";

function runPython(code) {
  return new Promise((resolve) => {
    const cwd = process.cwd();
    execFile("python", ["-c", code], { cwd }, (err, stdout, stderr) => {
      if (err) return resolve({ error: stderr || err.message });
      try {
        resolve(JSON.parse(stdout.trim()));
      } catch (e) {
        resolve({ raw: stdout.trim() });
      }
    });
  });
}

export async function GET() {
  try {
    const code = `
import sys, json
sys.path.insert(0, 'automation')
from core.task_orchestrator import orchestrator
snap = orchestrator.get_snapshot()
print(json.dumps(snap))
    `.trim();

    const data = await runPython(code);
    return NextResponse.json({ success: true, ...data });
  } catch (error) {
    console.error("GET /api/queue error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function POST(request) {
  try {
    const body = await request.json();
    const { action, taskId } = body;

    if (action === "cancel" && taskId) {
      const code = `
import sys, json
sys.path.insert(0, 'automation')
from core.task_orchestrator import orchestrator
res = orchestrator.cancel_task('${taskId}')
print(json.dumps({'cancelled': res}))
      `.trim();

      const data = await runPython(code);
      return NextResponse.json({ success: true, taskId, ...data });
    }

    return NextResponse.json({ error: "Invalid action or missing taskId" }, { status: 400 });
  } catch (error) {
    console.error("POST /api/queue error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
