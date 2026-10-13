import { NextResponse } from "next/server";
import net from "net";
import { execSync, spawn } from "child_process";
import path from "path";
import fs from "fs";

function checkPort(port = 9222, host = "127.0.0.1") {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    socket.setTimeout(400);

    socket.on("connect", () => {
      socket.destroy();
      resolve(true);
    });

    socket.on("timeout", () => {
      socket.destroy();
      resolve(false);
    });

    socket.on("error", () => {
      socket.destroy();
      resolve(false);
    });

    socket.connect(port, host);
  });
}

function findChromePath() {
  const candidates = [
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    path.join(process.env.LOCALAPPDATA || "", "Google", "Chrome", "Application", "chrome.exe"),
  ];
  for (const c of candidates) {
    if (fs.existsSync(c)) return c;
  }
  return null;
}

function getChromeUserDataDir() {
  const localAppData =
    process.env.LOCALAPPDATA ||
    (process.env.USERPROFILE ? path.join(process.env.USERPROFILE, "AppData", "Local") : "");
  if (!localAppData) return null;
  return path.join(localAppData, "Google", "Chrome", "User Data");
}

function getProfileDetails(profileDir) {
  try {
    const localStatePath = path.join(profileDir, "Local State");
    if (fs.existsSync(localStatePath)) {
      const ls = JSON.parse(fs.readFileSync(localStatePath, "utf8"));
      const def = ls?.profile?.info_cache?.Default;
      if (def) {
        return {
          email: def.user_name || def.hosted_domain || "",
          name: def.name || def.shortcut_name || "Primary Profile",
        };
      }
    }
  } catch {}
  return { email: "2003shivam1990@gmail.com", name: "Shivam" };
}

function syncProfileToSharedDir(srcProfileId = "Default") {
  const userDataDir = getChromeUserDataDir();
  if (!userDataDir || !fs.existsSync(userDataDir)) return false;

  const srcProfileDir = path.join(userDataDir, srcProfileId);
  const srcLocalState = path.join(userDataDir, "Local State");
  const destDir = path.join(process.cwd(), "chrome_profiles", "shared_browser");
  const destDefaultDir = path.join(destDir, "Default");

  fs.mkdirSync(destDefaultDir, { recursive: true });

  // 1. Sanitize Local State with DPAPI os_crypt
  if (fs.existsSync(srcLocalState)) {
    try {
      const lsRaw = JSON.parse(fs.readFileSync(srcLocalState, "utf8"));
      const selectedInfo = lsRaw?.profile?.info_cache?.[srcProfileId] || {
        name: "Shivam",
        user_name: "2003shivam1990@gmail.com",
      };
      const sanitizedLocalState = {
        os_crypt: lsRaw.os_crypt || {},
        profile: {
          info_cache: {
            Default: {
              ...selectedInfo,
              name: selectedInfo.name || "Shivam",
              user_name: selectedInfo.user_name || "2003shivam1990@gmail.com",
            },
          },
          last_used: "Default",
          picker_shown: false,
        },
      };
      fs.writeFileSync(
        path.join(destDir, "Local State"),
        JSON.stringify(sanitizedLocalState, null, 2),
        "utf8"
      );
    } catch (err) {
      console.warn("Failed to write Local State:", err);
    }
  }

  // 2. Essential files
  const essentialFiles = [
    "Preferences",
    "Secure Preferences",
    "Login Data",
    "Web Data",
    "Bookmarks",
    "Favicons",
    "History",
    "Cookies",
    "Top Sites",
    "Visited Links",
  ];

  for (const f of essentialFiles) {
    const s = path.join(srcProfileDir, f);
    const d = path.join(destDefaultDir, f);
    if (fs.existsSync(s)) {
      try {
        fs.copyFileSync(s, d);
      } catch {}
    }
  }

  // 3. Essential directories
  const essentialDirs = [
    "Network",
    "Local Storage",
    "Session Storage",
    "IndexedDB",
    "Sessions",
  ];

  function copyDirClean(src, dest) {
    if (!fs.existsSync(src)) return;
    fs.mkdirSync(dest, { recursive: true });
    try {
      const entries = fs.readdirSync(src, { withFileTypes: true });
      for (const entry of entries) {
        const s = path.join(src, entry.name);
        const d = path.join(dest, entry.name);
        const lower = entry.name.toLowerCase();
        if (
          lower === "lock" ||
          lower.includes("singleton") ||
          lower.endsWith(".lock") ||
          lower.endsWith(".tmp")
        ) {
          continue;
        }
        if (entry.isDirectory()) {
          copyDirClean(s, d);
        } else {
          try {
            fs.copyFileSync(s, d);
          } catch {}
        }
      }
    } catch {}
  }

  for (const d of essentialDirs) {
    copyDirClean(path.join(srcProfileDir, d), path.join(destDefaultDir, d));
  }

  // 4. Remove any stale locks in destination
  try {
    const entries = fs.readdirSync(destDefaultDir);
    for (const ent of entries) {
      if (ent.toLowerCase() === "lock" || ent.toLowerCase().includes("singleton")) {
        try {
          fs.unlinkSync(path.join(destDefaultDir, ent));
        } catch {}
      }
    }
  } catch {}

  return true;
}

export async function GET() {
  const connected = await checkPort(9222);
  const sharedDir = path.join(process.cwd(), "chrome_profiles", "shared_browser");
  const details = getProfileDetails(sharedDir);

  return NextResponse.json({
    connected,
    port: 9222,
    profileEmail: details.email || "2003shivam1990@gmail.com",
    profileName: details.name || "Shivam",
    message: connected
      ? `Bot is connected to Chrome profile ${details.email} on port 9222.`
      : "No active browser detected on port 9222.",
  });
}

export async function POST(request) {
  try {
    let body = {};
    try {
      body = await request.json();
    } catch {}

    const { profileId = "Default", forceSync = true, forceClose = true } = body;

    const alreadyConnected = await checkPort(9222);
    if (alreadyConnected && !forceClose) {
      const sharedDir = path.join(process.cwd(), "chrome_profiles", "shared_browser");
      const details = getProfileDetails(sharedDir);
      return NextResponse.json({
        success: true,
        alreadyRunning: true,
        connected: true,
        profileEmail: details.email,
        message: `Chrome is already running with remote debugging on port 9222 (${details.email})!`,
      });
    }

    const chromePath = findChromePath();
    if (!chromePath) {
      return NextResponse.json(
        { error: "Google Chrome executable was not found on this system." },
        { status: 404 }
      );
    }

    // Terminate existing Chrome instances to free locks and allow remote debugging
    if (forceClose || !alreadyConnected) {
      try {
        execSync(
          'powershell -Command "Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue"',
          { stdio: "ignore", timeout: 6000 }
        );
        await new Promise((r) => setTimeout(r, 2000));
      } catch (err) {
        console.warn("Could not stop Chrome processes:", err.message);
      }
    }

    const profileDir = path.join(process.cwd(), "chrome_profiles", "shared_browser");
    fs.mkdirSync(profileDir, { recursive: true });

    // Sync user profile (2003shivam1990@gmail.com) into shared_browser
    if (forceSync) {
      syncProfileToSharedDir(profileId);
    }

    // Launch Chrome detached with remote debugging enabled
    const args = [
      "--remote-debugging-port=9222",
      `--user-data-dir=${profileDir}`,
      "--no-first-run",
      "--no-default-browser-check",
      "http://localhost:3000",
      "https://chatgpt.com",
    ];

    const child = spawn(chromePath, args, {
      detached: true,
      stdio: "ignore",
    });
    child.unref();

    // Poll until port 9222 is open (up to 5 seconds)
    let connected = false;
    for (let i = 0; i < 10; i++) {
      await new Promise((r) => setTimeout(r, 500));
      connected = await checkPort(9222);
      if (connected) break;
    }

    const details = getProfileDetails(profileDir);

    return NextResponse.json({
      success: true,
      connected,
      profileEmail: details.email,
      message: connected
        ? `Chrome successfully launched with profile ${details.email}! Remote debugging active on port 9222.`
        : "Chrome process started. Initializing remote debugging...",
    });
  } catch (error) {
    console.error("Failed to launch Chrome:", error);
    return NextResponse.json({ error: error.message || "Failed to launch Chrome" }, { status: 500 });
  }
}
