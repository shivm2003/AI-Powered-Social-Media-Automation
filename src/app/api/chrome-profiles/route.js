import { NextResponse } from "next/server";
import path from "path";
import fs from "fs";
import { execSync } from "child_process";
import { upsertAccount, getAccountByPlatform } from "@/lib/db";
import { v4 as uuidv4 } from "uuid";

function getChromeUserDataDir() {
  const localAppData = process.env.LOCALAPPDATA || (process.env.USERPROFILE ? path.join(process.env.USERPROFILE, "AppData", "Local") : "");
  if (!localAppData) return null;
  return path.join(localAppData, "Google", "Chrome", "User Data");
}

function detectProfileLogins(userDataDir, folderName) {
  try {
    const profilePath = path.join(userDataDir, folderName);
    const helperScript = path.join(process.cwd(), "automation", "utils", "detect_logins.py");
    if (!fs.existsSync(helperScript) || !fs.existsSync(profilePath)) return [];

    const out = execSync(`python "${helperScript}" "${profilePath}"`, {
      timeout: 3000,
      encoding: "utf8",
    });
    return JSON.parse(out.trim() || "[]");
  } catch {
    return [];
  }
}

export async function GET() {
  try {
    const userDataDir = getChromeUserDataDir();
    if (!userDataDir || !fs.existsSync(userDataDir)) {
      return NextResponse.json({
        available: false,
        profiles: [],
        message: "Chrome User Data directory not found.",
      });
    }

    const localStatePath = path.join(userDataDir, "Local State");
    if (!fs.existsSync(localStatePath)) {
      return NextResponse.json({
        available: false,
        profiles: [],
        message: "Chrome Local State not found.",
      });
    }

    const localState = JSON.parse(fs.readFileSync(localStatePath, "utf8"));
    const infoCache = localState?.profile?.info_cache || {};

    const profiles = Object.entries(infoCache).map(([folderName, info]) => {
      const logins = detectProfileLogins(userDataDir, folderName);
      return {
        id: folderName,
        name: info.name || folderName,
        email: info.user_name || info.hosted_domain || "",
        isDefault: folderName === "Default",
        detectedLogins: logins,
      };
    });

    // Check currently cloned profiles in project
    const projectRoot = process.cwd();
    const chromeProfilesDir = path.join(projectRoot, "chrome_profiles");
    const activePlatforms = {};

    const allPlatforms = ["facebook", "instagram", "linkedin", "whatsapp", "gemini", "chatgpt", "claude", "shared_browser"];
    allPlatforms.forEach((p) => {
      const pDir = path.join(chromeProfilesDir, p, "Default");
      const hasCookies = fs.existsSync(path.join(pDir, "Network", "Cookies")) || fs.existsSync(path.join(pDir, "Preferences"));
      activePlatforms[p] = hasCookies;
    });

    return NextResponse.json({
      available: true,
      profiles,
      activePlatforms,
    });
  } catch (error) {
    console.error("Error discovering Chrome profiles:", error);
    return NextResponse.json({ error: error.message || "Failed to scan Chrome profiles" }, { status: 500 });
  }
}

export async function POST(request) {
  try {
    const body = await request.json();
    const {
      profileId = "Default",
      platforms = ["facebook", "instagram", "linkedin", "whatsapp", "gemini", "chatgpt", "claude", "shared_browser"],
      forceClose = true,
    } = body;
    const finalPlatforms = Array.from(new Set([...platforms, "shared_browser"]));

    const userDataDir = getChromeUserDataDir();
    if (!userDataDir || !fs.existsSync(userDataDir)) {
      return NextResponse.json({ error: "Chrome installation not found." }, { status: 400 });
    }

    const srcProfileDir = path.join(/*turbopackIgnore: true*/ userDataDir, profileId);
    const srcLocalState = path.join(/*turbopackIgnore: true*/ userDataDir, "Local State");

    if (!fs.existsSync(/*turbopackIgnore: true*/ srcProfileDir)) {
      return NextResponse.json({ error: `Selected Chrome profile "${profileId}" does not exist.` }, { status: 404 });
    }

    // Get email/name from profile for record keeping
    let profileEmail = "";
    let profileName = profileId;
    let localStateRaw = null;
    if (fs.existsSync(srcLocalState)) {
      try {
        localStateRaw = JSON.parse(fs.readFileSync(srcLocalState, "utf8"));
        const info = localStateRaw?.profile?.info_cache?.[profileId];
        profileEmail = info?.user_name || info?.name || "";
        profileName = info?.name || profileId;
      } catch {
        // ignore
      }
    }

    // Close running Chrome if requested to release locks on Cookies/IndexedDB
    if (forceClose) {
      try {
        execSync('powershell -Command "Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue"', {
          stdio: "ignore",
          timeout: 6000,
        });
        // Give Chrome 2.5 seconds to flush memory and release all file locks
        await new Promise((r) => setTimeout(r, 2500));
      } catch (err) {
        console.warn("Could not stop Chrome processes automatically:", err.message);
      }
    }

    const projectRoot = process.cwd();
    const chromeProfilesDir = path.join(projectRoot, "chrome_profiles");

    const essentialFiles = [
      "Preferences",
      "Secure Preferences",
      "Login Data",
      "Login Data-journal",
      "Web Data",
      "Web Data-journal",
      "Bookmarks",
      "Favicons",
      "History",
      "Cookies",
      "Cookies-journal",
      "Top Sites",
      "Visited Links",
      "CURRENT",
      "TransportSecurity",
    ];

    const essentialDirs = [
      "Network",
      "Local Storage",
      "Session Storage",
      "IndexedDB",
      "Sessions",
      "Service Worker",
      "databases",
      "Extension State",
      "blob_storage",
    ];

    const copied = [];
    const failed = [];

    // Helper: copy files, skipping any lock/singleton files
    function copyDirClean(src, dest) {
      if (!fs.existsSync(src)) return;
      fs.mkdirSync(dest, { recursive: true });
      const entries = fs.readdirSync(src, { withFileTypes: true });

      for (const entry of entries) {
        const srcPath = path.join(src, entry.name);
        const destPath = path.join(dest, entry.name);
        const lowerName = entry.name.toLowerCase();

        // Skip lock files and temporary runtime files
        if (
          lowerName === "lock" ||
          lowerName.includes("singleton") ||
          lowerName.endsWith(".lock") ||
          lowerName.endsWith(".pma") ||
          lowerName.endsWith(".tmp")
        ) {
          continue;
        }

        if (entry.isDirectory()) {
          copyDirClean(srcPath, destPath);
        } else {
          try {
            fs.copyFileSync(srcPath, destPath);
          } catch {
            // Ignore single locked files in cache/extensions
          }
        }
      }
    }

    function copyFileSafe(src, dest) {
      try {
        if (fs.existsSync(src)) {
          fs.copyFileSync(src, dest);
          return true;
        }
      } catch (err) {
        console.warn(`File copy skipped for ${src}: ${err.message}`);
      }
      return false;
    }

    for (const platform of finalPlatforms) {
      try {
        const targetPlatformDir = path.join(chromeProfilesDir, platform);
        const targetDefaultDir = path.join(targetPlatformDir, "Default");

        fs.mkdirSync(targetDefaultDir, { recursive: true });

        // ── 1. Create SANITIZED Local State ──
        // Critical: keep os_crypt (DPAPI encryption key) but set ONLY Default in info_cache
        // and set picker_shown: false so Chrome NEVER opens the profile selector screen!
        if (localStateRaw && localStateRaw.os_crypt) {
          const selectedInfo = localStateRaw?.profile?.info_cache?.[profileId] || { name: profileName };
          const sanitizedLocalState = {
            os_crypt: localStateRaw.os_crypt,
            profile: {
              info_cache: {
                Default: {
                  ...selectedInfo,
                  name: selectedInfo.name || "Default",
                },
              },
              last_used: "Default",
              picker_shown: false,
            },
          };
          fs.writeFileSync(
            path.join(targetPlatformDir, "Local State"),
            JSON.stringify(sanitizedLocalState, null, 2),
            "utf8"
          );
        }

        // ── 2. Copy essential profile files ──
        for (const fname of essentialFiles) {
          const srcFile = path.join(srcProfileDir, fname);
          copyFileSafe(srcFile, path.join(targetDefaultDir, fname));
        }

        // ── 3. Copy essential directories cleanly (no lock files) ──
        for (const dname of essentialDirs) {
          const srcDir = path.join(srcProfileDir, dname);
          const targetDir = path.join(targetDefaultDir, dname);
          copyDirClean(srcDir, targetDir);
        }

        // ── 4. Clean up any stale lock files that might exist in destination ──
        try {
          const defaultEntries = fs.readdirSync(targetDefaultDir);
          for (const ent of defaultEntries) {
            if (ent.toLowerCase() === "lock" || ent.toLowerCase().includes("singleton")) {
              try { fs.unlinkSync(path.join(targetDefaultDir, ent)); } catch {}
            }
          }
        } catch {}

        // ── 5. Save/update database record ──
        const existing = await getAccountByPlatform(platform);
        await upsertAccount({
          id: existing ? existing.id : uuidv4(),
          platform,
          username: existing?.username || profileEmail || `${profileName} (${platform})`,
          encrypted_password: existing?.encrypted_password || null,
          extra_fields: existing?.extra_fields || {},
          session_status: "verified",
        });

        copied.push(platform);
      } catch (err) {
        console.error(`Failed to clone profile to ${platform}:`, err);
        failed.push({ platform, error: err.message });
      }
    }

    return NextResponse.json({
      success: true,
      message: `Successfully imported "${profileName}" (${profileId}) into ${copied.length} platform(s)! Sessions are ready to use.`,
      profileId,
      profileName,
      profileEmail,
      copiedPlatforms: copied,
      failedPlatforms: failed,
    });
  } catch (error) {
    console.error("Chrome profile cloning error:", error);
    return NextResponse.json({ error: error.message || "Failed to clone profile" }, { status: 500 });
  }
}
