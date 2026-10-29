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

function getProfileDetails(profileDir, targetProfileId = null) {
  try {
    const localStatePath = path.join(profileDir, "Local State");
    if (fs.existsSync(localStatePath)) {
      const ls = JSON.parse(fs.readFileSync(localStatePath, "utf8"));
      const pKey = targetProfileId || ls?.profile?.last_used || "Default";
      const info = ls?.profile?.info_cache?.[pKey] || ls?.profile?.info_cache?.["Default"];
      if (info) {
        return {
          email: info.user_name || info.hosted_domain || "",
          name: info.name || info.shortcut_name || pKey,
          profileDir: pKey,
        };
      }
    }
  } catch {}
  return { email: "2003shivam1990@gmail.com", name: "Shivam Mishra", profileDir: "Default" };
}

function syncProfileToSharedDir(srcProfileId = "Default") {
  const userDataDir = getChromeUserDataDir();
  if (!userDataDir || !fs.existsSync(userDataDir)) return false;

  const srcProfileDir = path.join(userDataDir, srcProfileId);
  const srcLocalState = path.join(userDataDir, "Local State");
  const destDir = path.join(process.cwd(), "chrome_profiles", "shared_browser");
  const destProfileDir = path.join(destDir, srcProfileId);

  fs.mkdirSync(destProfileDir, { recursive: true });

  // 1. Sanitize Local State preserving all profiles
  if (fs.existsSync(srcLocalState)) {
    try {
      const lsRaw = JSON.parse(fs.readFileSync(srcLocalState, "utf8"));
      const rawInfoCache = lsRaw?.profile?.info_cache || {};
      const sanitizedInfoCache = {};
      for (const [pKey, pInfo] of Object.entries(rawInfoCache)) {
        sanitizedInfoCache[pKey] = {
          active_time: pInfo.active_time || 0,
          avatar_icon: pInfo.avatar_icon || "chrome://theme/IDR_PROFILE_AVATAR_26",
          gaia_id: pInfo.gaia_id || "",
          gaia_name: pInfo.gaia_name || "",
          hosted_domain: pInfo.hosted_domain || "NO_HOSTED_DOMAIN",
          name: pInfo.name || pKey,
          shortcut_name: pInfo.shortcut_name || pKey,
          user_name: pInfo.user_name || "",
        };
      }
      const sanitizedLocalState = {
        os_crypt: lsRaw.os_crypt || {},
        profile: {
          info_cache: sanitizedInfoCache,
          last_used: srcProfileId,
          picker_shown: false,
          profiles_order: Object.keys(rawInfoCache),
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
    const d = path.join(destProfileDir, f);
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
    copyDirClean(path.join(srcProfileDir, d), path.join(destProfileDir, d));
  }

  // 4. Remove any stale locks in destination
  try {
    const entries = fs.readdirSync(destProfileDir);
    for (const ent of entries) {
      if (ent.toLowerCase() === "lock" || ent.toLowerCase().includes("singleton")) {
        try {
          fs.unlinkSync(path.join(destProfileDir, ent));
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
    profileName: details.name || "Shivam Mishra",
    profileDir: details.profileDir || "Default",
    message: connected
      ? `Bot is connected to Chrome profile ${details.email} (${details.profileDir}) on port 9222.`
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
    const sharedDir = path.join(process.cwd(), "chrome_profiles", "shared_browser");
    const currentDetails = getProfileDetails(sharedDir);

    const alreadyConnected = await checkPort(9222);
    // If already connected with the EXACT requested profile and forceClose is not set, reuse
    if (alreadyConnected && !forceClose && currentDetails.profileDir?.toLowerCase() === profileId.toLowerCase()) {
      return NextResponse.json({
        success: true,
        alreadyRunning: true,
        connected: true,
        profileEmail: currentDetails.email,
        profileDir: currentDetails.profileDir,
        message: `Chrome is already running with remote debugging on port 9222 (${currentDetails.email})!`,
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
    try {
      execSync(
        'powershell -Command "Stop-Process -Name chrome, chromedriver -Force -ErrorAction SilentlyContinue"',
        { stdio: "ignore", timeout: 6000 }
      );
      await new Promise((r) => setTimeout(r, 1500));
    } catch (err) {
      console.warn("Could not stop Chrome processes:", err.message);
    }

    fs.mkdirSync(sharedDir, { recursive: true });

    // Sync requested profile into shared_browser
    if (forceSync) {
      syncProfileToSharedDir(profileId);
    }

    // Launch Chrome detached with remote debugging enabled and specific profile
    const args = [
      "--remote-debugging-port=9222",
      `--user-data-dir=${sharedDir}`,
      `--profile-directory=${profileId}`,
      "--no-first-run",
      "--no-default-browser-check",
      "http://localhost:3000",
    ];

    const child = spawn(chromePath, args, {
      detached: true,
      stdio: "ignore",
    });
    child.unref();

    // Poll until port 9222 is open (up to 5 seconds)
    let connected = false;
    for (let i = 0; i < 12; i++) {
      await new Promise((r) => setTimeout(r, 500));
      connected = await checkPort(9222);
      if (connected) break;
    }

    const details = getProfileDetails(sharedDir, profileId);

    return NextResponse.json({
      success: true,
      connected,
      profileEmail: details.email,
      profileDir: details.profileDir,
      message: connected
        ? `Chrome successfully launched with profile ${details.email} (${profileId})! Remote debugging active on port 9222.`
        : "Chrome process started. Initializing remote debugging...",
    });
  } catch (error) {
    console.error("Failed to launch Chrome:", error);
    return NextResponse.json({ error: error.message || "Failed to launch Chrome" }, { status: 500 });
  }
}
