import { spawn } from "child_process";
import path from "path";
import fs from "fs";

const PROJECT_ROOT = process.cwd();
const AUTOMATION_SCRIPT = path.join(PROJECT_ROOT, "automation", "main.py");
const PYTHON_CMD = process.env.PYTHON_PATH || "python";

/**
 * Execute a command on the Python automation engine.
 * @param {Object} command - The command object, e.g. { action: "test_login", platform: "facebook" }
 * @param {number} timeoutMs - Timeout in milliseconds (default: 120s)
 * @returns {Promise<Object>}
 */
export async function runAutomationCommand(command, timeoutMs = 120000) {
  return new Promise((resolve, reject) => {
    // Check if python script exists
    if (!fs.existsSync(AUTOMATION_SCRIPT)) {
      return reject(new Error(`Automation script not found at ${AUTOMATION_SCRIPT}`));
    }

    let stdoutData = "";
    let stderrData = "";
    let finished = false;

    // Spawn python process
    const child = spawn(/*turbopackIgnore: true*/ PYTHON_CMD, [AUTOMATION_SCRIPT], {
      cwd: path.join(PROJECT_ROOT, "automation"),
      env: {
        ...process.env,
        PYTHONUNBUFFERED: "1",
      },
      windowsHide: true,
    });

    const timer = setTimeout(() => {
      if (!finished) {
        finished = true;
        child.kill();
        reject(new Error(`Automation command timed out after ${timeoutMs / 1000}s`));
      }
    }, timeoutMs);

    child.stdout.on("data", (data) => {
      const text = data.toString();
      stdoutData += text;
      // If we see JSON output, try to parse
      const lines = stdoutData.trim().split("\n");
      for (const line of lines) {
        try {
          const parsed = JSON.parse(line.trim());
          if (parsed && (parsed.status === "success" || parsed.status === "error" || parsed.status === "ready")) {
            if (parsed.status !== "ready") {
              finished = true;
              clearTimeout(timer);
              child.kill();
              return resolve(parsed);
            }
          }
        } catch {
          // Continue buffering
        }
      }
    });

    child.stderr.on("data", (data) => {
      stderrData += data.toString();
    });

    child.on("error", (err) => {
      if (!finished) {
        finished = true;
        clearTimeout(timer);
        reject(new Error(`Failed to start Python process (${PYTHON_CMD}): ${err.message}`));
      }
    });

    child.on("close", (code) => {
      if (finished) return;
      finished = true;
      clearTimeout(timer);

      // Try parsing stdout lines from end
      const lines = stdoutData.trim().split("\n");
      for (let i = lines.length - 1; i >= 0; i--) {
        try {
          const parsed = JSON.parse(lines[i].trim());
          return resolve(parsed);
        } catch {
          // ignore
        }
      }

      if (code !== 0) {
        reject(new Error(`Python process exited with code ${code}. Stderr: ${stderrData.slice(-500)}`));
      } else {
        resolve({
          status: "success",
          message: stdoutData.trim() || "Command completed",
          raw: stdoutData,
        });
      }
    });

    // Send the command payload to stdin
    const inputPayload = JSON.stringify(command) + "\n";
    child.stdin.write(inputPayload);
    child.stdin.end();
  });
}
