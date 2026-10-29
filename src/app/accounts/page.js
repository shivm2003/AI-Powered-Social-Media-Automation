"use client";

import { useState, useEffect } from "react";
import { PLATFORMS } from "@/lib/constants";

const ALL_AUTOMATION_PLATFORMS = [
  { id: "facebook", name: "Facebook", icon: "📘", category: "Social" },
  { id: "instagram", name: "Instagram", icon: "📸", category: "Social" },
  { id: "linkedin", name: "LinkedIn", icon: "💼", category: "Social" },
  { id: "whatsapp", name: "WhatsApp", icon: "💬", category: "Social" },
  { id: "gemini", name: "Gemini", icon: "♊", category: "AI LLM" },
  { id: "chatgpt", name: "ChatGPT", icon: "🟢", category: "AI LLM" },
  { id: "claude", name: "Claude", icon: "🟣", category: "AI LLM" },
];

const ALL_PLATFORMS_MAP = {
  ...PLATFORMS,
  gemini: {
    name: "Gemini",
    icon: "♊",
    color: "hsl(217, 89%, 61%)",
    colorMuted: "hsla(217, 89%, 61%, 0.15)",
    fields: [
      { key: "username", label: "Google Email / Account", type: "text", required: false, placeholder: "your@gmail.com" },
      { key: "password", label: "Password (or use Chrome sync)", type: "password", required: false, placeholder: "••••••••" },
    ],
    loginNote: "Used for AI text generation. Sync your active browser or import your Chrome profile.",
  },
  chatgpt: {
    name: "ChatGPT",
    icon: "🟢",
    color: "hsl(160, 84%, 39%)",
    colorMuted: "hsla(160, 84%, 39%, 0.15)",
    fields: [
      { key: "username", label: "Email / Username", type: "text", required: false, placeholder: "your@email.com" },
      { key: "password", label: "Password (or use Chrome sync)", type: "password", required: false, placeholder: "••••••••" },
    ],
    loginNote: "Used for AI text generation. Sync your active browser or import your Chrome profile.",
  },
  claude: {
    name: "Claude",
    icon: "🟣",
    color: "hsl(25, 95%, 53%)",
    colorMuted: "hsla(25, 95%, 53%, 0.15)",
    fields: [
      { key: "username", label: "Email / Username", type: "text", required: false, placeholder: "your@email.com" },
      { key: "password", label: "Password (or use Chrome sync)", type: "password", required: false, placeholder: "••••••••" },
    ],
    loginNote: "Used for AI text generation. Sync your active browser or import your Chrome profile.",
  },
};

function getPlatformConfig(key) {
  if (!key) return { name: "Platform", icon: "🌐", color: "#7C5CFC", colorMuted: "rgba(124,92,252,0.15)", fields: [] };
  return (
    ALL_PLATFORMS_MAP[key] || {
      name: key.charAt(0).toUpperCase() + key.slice(1),
      icon: "🌐",
      color: "hsl(250, 85%, 65%)",
      colorMuted: "hsla(250, 85%, 65%, 0.15)",
      fields: [
        { key: "username", label: "Username / Email", type: "text", required: false, placeholder: "Username or email" },
      ],
      loginNote: null,
    }
  );
}

export default function AccountsPage() {
  const [selectedPlatforms, setSelectedPlatforms] = useState([]);
  const [accounts, setAccounts] = useState({});
  const [savedAccounts, setSavedAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testingLogin, setTestingLogin] = useState(null);

  // Chrome Profile Import State
  const [chromeProfiles, setChromeProfiles] = useState([]);
  const [activeChromePlatforms, setActiveChromePlatforms] = useState({});
  const [selectedChromeProfile, setSelectedChromeProfile] = useState("Default");
  const [targetPlatforms, setTargetPlatforms] = useState([
    "facebook",
    "instagram",
    "linkedin",
    "whatsapp",
    "gemini",
    "chatgpt",
    "claude",
  ]);
  const [forceCloseChrome, setForceCloseChrome] = useState(true);
  const [cloningProfile, setCloningProfile] = useState(false);
  const [cloneFeedback, setCloneFeedback] = useState(null);
  const [browserConnected, setBrowserConnected] = useState(false);
  const [browserProfileEmail, setBrowserProfileEmail] = useState("2003shivam1990@gmail.com");
  const [launchingBrowser, setLaunchingBrowser] = useState(false);

  // 3-Step Human Chrome Operator State
  const [humanAiPlatform, setHumanAiPlatform] = useState("gemini");
  const [humanQuery, setHumanQuery] = useState(
    "Search and draft a high-converting viral marketing hook for our new product."
  );
  const [humanRunning, setHumanRunning] = useState(false);
  const [humanCurrentStep, setHumanCurrentStep] = useState(0); // 0=idle, 1=click chrome, 2=select profile, 3=search AI, 4=done
  const [humanLogs, setHumanLogs] = useState([]);
  const [humanResult, setHumanResult] = useState(null);
  const [humanError, setHumanError] = useState(null);

  useEffect(() => {
    fetchAccounts();
    fetchChromeProfiles();
    checkBrowserStatus();
    const interval = setInterval(checkBrowserStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  async function checkBrowserStatus() {
    try {
      const res = await fetch("/api/browser");
      if (res.ok) {
        const data = await res.json();
        setBrowserConnected(!!data.connected);
        if (data.profileEmail) setBrowserProfileEmail(data.profileEmail);
      }
    } catch { }
  }

  async function handleRunHumanFlow() {
    if (!humanQuery.trim()) {
      alert("Please enter what you want the bot to search/prompt.");
      return;
    }
    setHumanRunning(true);
    setHumanError(null);
    setHumanResult(null);
    setHumanCurrentStep(1);
    const activeProf = chromeProfiles.find((p) => p.id === selectedChromeProfile) || {
      name: "Shivam Mishra",
      email: "2003shivam1990@gmail.com",
    };
    setHumanLogs([
      `Step 1: Clicking & launching Google Chrome tab like a human for ${activeProf.name} (${selectedChromeProfile || "Default"})...`,
    ]);

    const step2Timer = setTimeout(() => {
      setHumanCurrentStep(2);
      setHumanLogs((prev) => [
        ...prev,
        `Step 2: Selecting ${activeProf.email || activeProf.name} account like a human...`,
      ]);
    }, 2800);

    const step3Timer = setTimeout(() => {
      setHumanCurrentStep(3);
      setHumanLogs((prev) => [
        ...prev,
        `Step 3: Navigating to ${humanAiPlatform.toUpperCase()} & typing search requirement with human cadence...`,
      ]);
    }, 6000);

    try {
      const res = await fetch("/api/browser/human-flow", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          platform: humanAiPlatform,
          query: humanQuery,
          profileDir: selectedChromeProfile || "Default",
        }),
      });

      clearTimeout(step2Timer);
      clearTimeout(step3Timer);

      const data = await res.json();
      if (res.ok && data.success) {
        setHumanCurrentStep(4);
        setHumanResult(data.data?.result || data.message);
        if (data.data?.logs && Array.isArray(data.data.logs)) {
          setHumanLogs(data.data.logs);
        } else {
          setHumanLogs((prev) => [
            ...prev,
            `✅ Flow finished successfully on ${humanAiPlatform.toUpperCase()}!`,
          ]);
        }
        checkBrowserStatus();
      } else {
        setHumanError(data.error || "Failed to execute human workflow.");
        setHumanLogs((prev) => [
          ...prev,
          `❌ Error: ${data.error || "Execution failed"}`,
        ]);
      }
    } catch (err) {
      clearTimeout(step2Timer);
      clearTimeout(step3Timer);
      setHumanError(err.message || "Network error occurred.");
      setHumanLogs((prev) => [...prev, `❌ Error: ${err.message}`]);
    } finally {
      setHumanRunning(false);
    }
  }

  async function handleLaunchBrowser(profileIdToUse = null) {
    const prof = typeof profileIdToUse === "string" ? profileIdToUse : (selectedChromeProfile || "Default");
    setLaunchingBrowser(true);
    try {
      const res = await fetch("/api/browser", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profileId: prof, forceSync: true }),
      });
      const data = await res.json();
      if (res.ok) {
        setBrowserConnected(true);
        if (data.profileEmail) setBrowserProfileEmail(data.profileEmail);
        alert(data.message || `Chrome launched with ${data.profileEmail || prof} on port 9222!`);
      } else {
        alert(data.error || "Failed to launch Chrome");
      }
    } catch (err) {
      alert("Error: " + err.message);
    } finally {
      setLaunchingBrowser(false);
      checkBrowserStatus();
    }
  }

  async function fetchAccounts() {
    try {
      const res = await fetch("/api/accounts");
      const data = await res.json();
      setSavedAccounts(data);

      // Populate selected platforms and form state from saved accounts
      const platforms = [];
      const accountState = {};
      data.forEach((acc) => {
        if (acc.platform && !platforms.includes(acc.platform)) {
          platforms.push(acc.platform);
        }
        accountState[acc.platform] = {
          username: acc.username || "",
          password: "",
          status: acc.session_status,
          ...acc.extra_fields,
        };
      });
      setSelectedPlatforms([...new Set(platforms)]);
      setAccounts(accountState);
    } catch (error) {
      console.error("Failed to fetch accounts:", error);
    } finally {
      setLoading(false);
    }
  }

  async function fetchChromeProfiles() {
    try {
      const res = await fetch("/api/chrome-profiles");
      const data = await res.json();
      if (data.available && data.profiles) {
        setChromeProfiles(data.profiles);
        setActiveChromePlatforms(data.activePlatforms || {});
        if (data.profiles.length > 0 && !selectedChromeProfile) {
          setSelectedChromeProfile(data.profiles[0].id);
        }
      }
    } catch (err) {
      console.error("Failed to load Chrome profiles:", err);
    }
  }

  async function handleCloneChromeProfile(profileIdToUse = null) {
    const targetProfile = typeof profileIdToUse === "string" ? profileIdToUse : selectedChromeProfile;
    if (typeof profileIdToUse === "string") {
      setSelectedChromeProfile(profileIdToUse);
    }
    setCloningProfile(true);
    setCloneFeedback(null);
    try {
      const res = await fetch("/api/chrome-profiles", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          profileId: targetProfile,
          platforms: targetPlatforms,
          forceClose: forceCloseChrome,
        }),
      });
      const data = await res.json();

      if (res.ok && data.success) {
        setCloneFeedback({
          type: "success",
          message: data.message || "Profile successfully imported into automation!",
        });
        await fetchChromeProfiles();
        await fetchAccounts();
      } else {
        setCloneFeedback({
          type: "error",
          message: data.error || "Failed to clone profile",
        });
      }
    } catch (err) {
      setCloneFeedback({
        type: "error",
        message: err.message || "Network error occurred",
      });
    } finally {
      setCloningProfile(false);
    }
  }

  function toggleTargetPlatform(pId) {
    setTargetPlatforms((prev) =>
      prev.includes(pId) ? prev.filter((id) => id !== pId) : [...prev, pId]
    );
  }

  function selectAllTargetPlatforms() {
    setTargetPlatforms(ALL_AUTOMATION_PLATFORMS.map((p) => p.id));
  }

  function deselectAllTargetPlatforms() {
    setTargetPlatforms([]);
  }

  function togglePlatform(platform) {
    setSelectedPlatforms((prev) => {
      if (prev.includes(platform)) {
        return prev.filter((p) => p !== platform);
      }
      if (!accounts[platform]) {
        const defaults = {};
        const config = getPlatformConfig(platform);
        (config.fields || []).forEach((field) => {
          defaults[field.key] = field.defaultValue || "";
        });
        setAccounts((prev) => ({ ...prev, [platform]: { ...defaults, status: "unverified" } }));
      }
      return [...prev, platform];
    });
  }

  function updateField(platform, key, value) {
    setAccounts((prev) => ({
      ...prev,
      [platform]: { ...prev[platform], [key]: value },
    }));
  }

  async function saveAllAccounts() {
    setSaving(true);
    try {
      for (const platform of selectedPlatforms) {
        const accountData = accounts[platform] || {};
        const config = getPlatformConfig(platform);

        const usernameField = (config.fields || []).find(
          (f) => f.key === "username" || f.key === "email" || f.key === "phone"
        );
        const passwordField = (config.fields || []).find((f) => f.key === "password");

        const extra_fields = {};
        (config.fields || []).forEach((field) => {
          if (field.key !== "password" && field.key !== usernameField?.key) {
            if (accountData[field.key]) {
              extra_fields[field.key] = accountData[field.key];
            }
          }
        });

        await fetch("/api/accounts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            platform,
            username: usernameField ? accountData[usernameField.key] : null,
            password: passwordField ? accountData[passwordField.key] : null,
            extra_fields,
          }),
        });
      }

      for (const acc of savedAccounts) {
        if (!selectedPlatforms.includes(acc.platform)) {
          await fetch(`/api/accounts?id=${acc.id}`, { method: "DELETE" });
        }
      }

      await fetchAccounts();
      alert("All accounts saved successfully!");
    } catch (error) {
      console.error("Failed to save accounts:", error);
    } finally {
      setSaving(false);
    }
  }

  async function testLogin(platform) {
    setTestingLogin(platform);
    try {
      const platformData = accounts[platform] || {};
      const config = getPlatformConfig(platform);
      const usernameField = (config.fields || []).find(
        (f) => f.key === "username" || f.key === "email" || f.key === "phone"
      );
      const passwordField = (config.fields || []).find((f) => f.key === "password");

      const res = await fetch("/api/accounts/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          platform,
          username: usernameField ? platformData[usernameField.key] : null,
          password: passwordField ? platformData[passwordField.key] : null,
        }),
      });

      const data = await res.json();
      if (res.ok && data.verified) {
        setAccounts((prev) => ({
          ...prev,
          [platform]: { ...prev[platform], status: "verified" },
        }));
        alert(`✅ ${data.message || `Session verified for ${config.name}! Profile saved.`}`);
      } else {
        alert(`Notice: ${data.message || data.error || "Login window closed."}`);
      }
    } catch (err) {
      console.error("Test login failed:", err);
      alert(`Could not complete login test: ${err.message}`);
    } finally {
      setTestingLogin(null);
      fetchAccounts();
    }
  }

  function shouldShowField(field, platformData) {
    if (!field.showIf) return true;
    return platformData[field.showIf.field] === field.showIf.value;
  }

  const selectedProfileDetails = chromeProfiles.find((p) => p.id === selectedChromeProfile);

  if (loading) {
    return (
      <div className="loading-overlay">
        <div className="spinner" />
        <span>Loading accounts...</span>
      </div>
    );
  }

  return (
    <div className="animate-fadeIn">
      <div className="page-header">
        <div>
          <h1 className="page-title">Social Accounts</h1>
          <p className="page-subtitle">Connect and manage your social media automation profiles</p>
        </div>
        <button
          className="btn btn-primary"
          onClick={saveAllAccounts}
          disabled={saving || selectedPlatforms.length === 0}
        >
          {saving ? "Saving..." : "💾 Save All Credentials"}
        </button>
      </div>

      {/* ── Same Browser Automation Card (Port 9222) ── */}
      <div
        className="card"
        style={{
          marginBottom: "var(--space-6)",
          border: browserConnected ? "1px solid rgba(16, 185, 129, 0.4)" : "1px solid rgba(124, 92, 252, 0.35)",
          background: browserConnected
            ? "linear-gradient(180deg, rgba(16, 185, 129, 0.08) 0%, var(--bg-secondary) 100%)"
            : "linear-gradient(180deg, rgba(124, 92, 252, 0.08) 0%, var(--bg-secondary) 100%)",
          boxShadow: "0 8px 32px rgba(0, 0, 0, 0.15)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "var(--space-4)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: "var(--radius-md)",
                background: browserConnected ? "var(--success)" : "var(--accent-primary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "1.4rem",
                color: "#fff",
              }}
            >
              {browserConnected ? "🟢" : "🌐"}
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                <h3 className="card-title" style={{ fontSize: "var(--font-lg)", margin: 0 }}>
                  Same Browser Control (Live Sync)
                </h3>
                <span
                  className={`badge ${browserConnected ? "badge-success" : "badge-secondary"}`}
                  style={{ fontSize: "var(--font-xs)" }}
                >
                  {browserConnected ? "✅ Connected to Active Browser" : "⚪ Standalone Mode"}
                </span>
              </div>
              <p style={{ fontSize: "var(--font-xs)", color: "var(--text-secondary)", marginTop: "4px" }}>
                {browserConnected
                  ? "Bot is attached to your open Chrome browser window. All commands, previews, and posts execute in your active browser tabs!"
                  : "Run the bot inside your exact active Chrome window! Click below to launch Chrome with remote debugging on port 9222."}
              </p>
            </div>
          </div>

          <div style={{ display: "flex", gap: "var(--space-2)" }}>
            <button
              className={`btn ${browserConnected ? "btn-secondary" : "btn-primary"}`}
              onClick={handleLaunchBrowser}
              disabled={launchingBrowser}
            >
              {launchingBrowser
                ? "⏳ Launching..."
                : browserConnected
                  ? "🔄 Re-Sync Browser"
                  : "🚀 Launch Chrome in Same Window"}
            </button>
          </div>
        </div>
      </div>

      {/* ── Human-Like Chrome AI Operator (3-Step Automation) ── */}
      <div
        className="card"
        style={{
          marginBottom: "var(--space-6)",
          border: humanRunning
            ? "1px solid var(--accent-primary)"
            : "1px solid rgba(124, 92, 252, 0.4)",
          background: "linear-gradient(135deg, rgba(124, 92, 252, 0.12) 0%, rgba(61, 214, 208, 0.05) 50%, var(--bg-secondary) 100%)",
          boxShadow: "0 12px 36px rgba(0, 0, 0, 0.25)",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Glow accent */}
        <div
          style={{
            position: "absolute",
            top: -40,
            right: -40,
            width: 140,
            height: 140,
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(124, 92, 252, 0.3) 0%, transparent 70%)",
            pointerEvents: "none",
          }}
        />

        <div className="card-header" style={{ paddingBottom: "var(--space-3)" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "var(--space-3)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
              <div
                style={{
                  width: 44,
                  height: 44,
                  borderRadius: "var(--radius-md)",
                  background: "linear-gradient(135deg, #7C5CFC, #3DD6D0)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "1.5rem",
                  color: "#fff",
                  boxShadow: "0 4px 16px rgba(124, 92, 252, 0.4)",
                }}
              >
                🤖
              </div>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                  <h3 className="card-title" style={{ fontSize: "var(--font-lg)", margin: 0 }}>
                    Human Chrome AI Operator
                  </h3>
                  <span className="badge badge-primary" style={{ fontSize: "var(--font-xs)" }}>
                    3-Step Workflow
                  </span>
                </div>
                <p style={{ fontSize: "var(--font-xs)", color: "var(--text-secondary)", marginTop: "4px" }}>
                  Clicks Chrome tab from app ➜ Selects account <strong>{selectedProfileDetails?.name || "Shivam Mishra"} ({selectedProfileDetails?.email || "2003shivam1990@gmail.com"})</strong> ➜ Searches Gemini, Claude, or ChatGPT with human typing.
                </p>
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
              <span
                style={{
                  fontSize: "var(--font-xs)",
                  padding: "4px 10px",
                  borderRadius: "var(--radius-full)",
                  background: "rgba(16, 185, 129, 0.15)",
                  color: "#34D399",
                  border: "1px solid rgba(16, 185, 129, 0.3)",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#34D399", display: "inline-block" }} />
                Target: {selectedProfileDetails?.name || "Shivam Mishra"} ({selectedProfileDetails?.email || "2003shivam1990@gmail.com"})
              </span>
            </div>
          </div>
        </div>

        {/* ── 3-Step Visual Stepper Bar ── */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: "var(--space-3)",
            margin: "var(--space-4) 0",
          }}
        >
          {/* Step 1 */}
          <div
            style={{
              padding: "var(--space-3)",
              borderRadius: "var(--radius-md)",
              border: humanCurrentStep >= 1 ? "1px solid var(--accent-primary)" : "1px solid var(--border-color)",
              background: humanCurrentStep === 1
                ? "rgba(124, 92, 252, 0.2)"
                : humanCurrentStep > 1
                  ? "rgba(16, 185, 129, 0.12)"
                  : "var(--bg-tertiary)",
              transition: "all 0.3s ease",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "4px" }}>
              <span style={{ fontSize: "var(--font-xs)", fontWeight: 700, color: humanCurrentStep >= 1 ? "var(--accent-primary)" : "var(--text-tertiary)" }}>
                STEP 1
              </span>
              <span style={{ fontSize: "var(--font-xs)" }}>
                {humanCurrentStep > 1 ? "✅ Done" : humanCurrentStep === 1 ? "⏳ Launching..." : "⚪ Waiting"}
              </span>
            </div>
            <div style={{ fontWeight: 600, fontSize: "var(--font-sm)" }}>
              🖱️ Click Chrome Tab
            </div>
            <div style={{ fontSize: "var(--font-xs)", color: "var(--text-secondary)", marginTop: "2px" }}>
              Launches browser like a human from app
            </div>
          </div>

          {/* Step 2 */}
          <div
            style={{
              padding: "var(--space-3)",
              borderRadius: "var(--radius-md)",
              border: humanCurrentStep >= 2 ? "1px solid var(--accent-primary)" : "1px solid var(--border-color)",
              background: humanCurrentStep === 2
                ? "rgba(124, 92, 252, 0.2)"
                : humanCurrentStep > 2
                  ? "rgba(16, 185, 129, 0.12)"
                  : "var(--bg-tertiary)",
              transition: "all 0.3s ease",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "4px" }}>
              <span style={{ fontSize: "var(--font-xs)", fontWeight: 700, color: humanCurrentStep >= 2 ? "var(--accent-primary)" : "var(--text-tertiary)" }}>
                STEP 2
              </span>
              <span style={{ fontSize: "var(--font-xs)" }}>
                {humanCurrentStep > 2 ? "✅ Selected" : humanCurrentStep === 2 ? "⏳ Selecting..." : "⚪ Waiting"}
              </span>
            </div>
            <div style={{ fontWeight: 600, fontSize: "var(--font-sm)" }}>
              👤 Select {selectedProfileDetails?.name || "Shivam Mishra"}
            </div>
            <div style={{ fontSize: "var(--font-xs)", color: "var(--text-secondary)", marginTop: "2px" }}>
              Selects {selectedProfileDetails?.email || "2003shivam1990@gmail.com"}
            </div>
          </div>

          {/* Step 3 */}
          <div
            style={{
              padding: "var(--space-3)",
              borderRadius: "var(--radius-md)",
              border: humanCurrentStep >= 3 ? "1px solid var(--accent-primary)" : "1px solid var(--border-color)",
              background: humanCurrentStep === 3
                ? "rgba(124, 92, 252, 0.2)"
                : humanCurrentStep > 3
                  ? "rgba(16, 185, 129, 0.12)"
                  : "var(--bg-tertiary)",
              transition: "all 0.3s ease",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "4px" }}>
              <span style={{ fontSize: "var(--font-xs)", fontWeight: 700, color: humanCurrentStep >= 3 ? "var(--accent-primary)" : "var(--text-tertiary)" }}>
                STEP 3
              </span>
              <span style={{ fontSize: "var(--font-xs)" }}>
                {humanCurrentStep === 4 ? "✅ Completed" : humanCurrentStep === 3 ? "⏳ Typing & Prompting..." : "⚪ Ready"}
              </span>
            </div>
            <div style={{ fontWeight: 600, fontSize: "var(--font-sm)" }}>
              🔍 Search Gemini / Claude / ChatGPT
            </div>
            <div style={{ fontSize: "var(--font-xs)", color: "var(--text-secondary)", marginTop: "2px" }}>
              Human typing of your search requirement
            </div>
          </div>
        </div>

        {/* ── Controls: Profile Choice, AI Choice & Requirement Prompt ── */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
          {/* Chrome Profile Selector */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
              <label style={{ fontSize: "var(--font-xs)", fontWeight: 600, color: "var(--text-secondary)", margin: 0 }}>
                Target Chrome Profile:
              </label>
              <span style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)" }}>
                Selected: <strong>{selectedProfileDetails?.name || "Shivam Mishra"}</strong> ({selectedProfileDetails?.email || selectedChromeProfile})
              </span>
            </div>
            <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
              {chromeProfiles.map((p) => {
                const isSelected = selectedChromeProfile === p.id;
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => setSelectedChromeProfile(p.id)}
                    style={{
                      flex: "1 1 180px",
                      padding: "8px 12px",
                      borderRadius: "var(--radius-md)",
                      border: isSelected ? "2px solid var(--accent-primary)" : "1px solid var(--border-color)",
                      background: isSelected ? "var(--accent-primary-muted)" : "var(--bg-tertiary)",
                      color: isSelected ? "#fff" : "var(--text-secondary)",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      fontWeight: isSelected ? 600 : 500,
                      transition: "all 0.2s ease",
                    }}
                  >
                    <span style={{ fontSize: "1.1rem" }}>👤</span>
                    <div style={{ textAlign: "left", overflow: "hidden" }}>
                      <div style={{ fontSize: "var(--font-xs)", fontWeight: 600, whiteSpace: "nowrap", textOverflow: "ellipsis" }}>
                        {p.name} {p.isDefault && <span style={{ color: "var(--accent-secondary)", fontSize: "0.7rem" }}>(Default)</span>}
                      </div>
                      <div style={{ fontSize: "0.68rem", opacity: 0.7, whiteSpace: "nowrap", textOverflow: "ellipsis" }}>
                        {p.email || p.id}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
          {/* AI Selector Buttons */}
          <div>
            <label style={{ fontSize: "var(--font-xs)", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "6px", display: "block" }}>
              Select AI Engine to Search:
            </label>
            <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
              {[
                { id: "gemini", name: "Gemini", icon: "♊", desc: "gemini.google.com" },
                { id: "chatgpt", name: "ChatGPT", icon: "🟢", desc: "chatgpt.com" },
                { id: "claude", name: "Claude", icon: "🟣", desc: "claude.ai" },
              ].map((ai) => {
                const isActive = humanAiPlatform === ai.id;
                return (
                  <button
                    key={ai.id}
                    type="button"
                    onClick={() => setHumanAiPlatform(ai.id)}
                    style={{
                      flex: "1 1 140px",
                      padding: "10px 14px",
                      borderRadius: "var(--radius-md)",
                      border: isActive ? "2px solid var(--accent-primary)" : "1px solid var(--border-color)",
                      background: isActive ? "rgba(124, 92, 252, 0.2)" : "var(--bg-tertiary)",
                      color: isActive ? "#fff" : "var(--text-secondary)",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      fontWeight: isActive ? 600 : 500,
                      transition: "all 0.2s ease",
                    }}
                  >
                    <span style={{ fontSize: "1.2rem" }}>{ai.icon}</span>
                    <div style={{ textAlign: "left" }}>
                      <div style={{ fontSize: "var(--font-sm)" }}>{ai.name}</div>
                      <div style={{ fontSize: "0.7rem", opacity: 0.7 }}>{ai.desc}</div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Search Requirement Prompt */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
              <label style={{ fontSize: "var(--font-xs)", fontWeight: 600, color: "var(--text-secondary)" }}>
                What do you require to search / prompt?
              </label>
              <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                {[
                  { label: "🔥 Viral Hooks", text: "Search and draft 3 high-converting viral marketing hooks with hashtags for our business." },
                  { label: "📸 Instagram Post", text: "Create an engaging, aesthetic Instagram caption with call to action for our new launch." },
                  { label: "💼 LinkedIn Thought Post", text: "Write an insightful LinkedIn post about how AI automation drives revenue growth." },
                ].map((tpl) => (
                  <button
                    key={tpl.label}
                    type="button"
                    onClick={() => setHumanQuery(tpl.text)}
                    style={{
                      background: "rgba(255, 255, 255, 0.05)",
                      border: "1px solid var(--border-color)",
                      color: "var(--text-secondary)",
                      borderRadius: "var(--radius-full)",
                      fontSize: "0.7rem",
                      padding: "2px 8px",
                      cursor: "pointer",
                    }}
                  >
                    {tpl.label}
                  </button>
                ))}
              </div>
            </div>
            <textarea
              className="form-control"
              rows={3}
              value={humanQuery}
              onChange={(e) => setHumanQuery(e.target.value)}
              placeholder="e.g. Search and draft high-converting marketing copy for our products..."
              style={{
                width: "100%",
                background: "var(--bg-tertiary)",
                borderRadius: "var(--radius-md)",
                padding: "10px 12px",
                fontSize: "var(--font-sm)",
                resize: "vertical",
              }}
            />
          </div>

          {/* Action Trigger Button */}
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", flexWrap: "wrap" }}>
            <button
              className="btn btn-primary"
              onClick={handleRunHumanFlow}
              disabled={humanRunning || !humanQuery.trim()}
              style={{
                padding: "12px 24px",
                fontSize: "var(--font-sm)",
                fontWeight: 600,
                boxShadow: "0 4px 16px rgba(124, 92, 252, 0.4)",
              }}
            >
              {humanRunning ? (
                <>
                  <span className="spinner" style={{ width: 16, height: 16, marginRight: 8 }} />
                  Executing Step {humanCurrentStep} of 3...
                </>
              ) : (
                `🚀 Execute Human Flow: Click Chrome ➜ Select ${selectedProfileDetails?.name || "Shivam"} ➜ Search ${humanAiPlatform.toUpperCase()}`
              )}
            </button>

            {humanRunning && (
              <span style={{ fontSize: "var(--font-xs)", color: "var(--accent-secondary)", animation: "pulse 1.5s infinite" }}>
                ⏳ Live browser automation is active. Watching Chrome...
              </span>
            )}
          </div>

          {/* Error notice */}
          {humanError && (
            <div
              style={{
                padding: "10px 14px",
                borderRadius: "var(--radius-md)",
                background: "rgba(239, 68, 68, 0.15)",
                border: "1px solid rgba(239, 68, 68, 0.4)",
                color: "#F87171",
                fontSize: "var(--font-xs)",
              }}
            >
              ⚠️ {humanError}
            </div>
          )}

          {/* Live Activity Terminal */}
          {humanLogs.length > 0 && (
            <div
              style={{
                marginTop: "var(--space-2)",
                padding: "12px 14px",
                borderRadius: "var(--radius-md)",
                background: "rgba(10, 12, 20, 0.8)",
                border: "1px solid rgba(255, 255, 255, 0.08)",
                fontFamily: "monospace",
                fontSize: "0.78rem",
                color: "#A7F3D0",
                maxHeight: 140,
                overflowY: "auto",
              }}
            >
              <div style={{ color: "var(--text-tertiary)", marginBottom: "4px", fontSize: "0.7rem" }}>
                LIVE AUTOMATION ACTIVITY LOG:
              </div>
              {humanLogs.map((log, idx) => (
                <div key={idx} style={{ marginBottom: "2px" }}>
                  ➜ {log}
                </div>
              ))}
            </div>
          )}

          {/* Result Card */}
          {humanResult && (
            <div
              style={{
                marginTop: "var(--space-3)",
                padding: "var(--space-4)",
                borderRadius: "var(--radius-md)",
                background: "linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, var(--bg-tertiary) 100%)",
                border: "1px solid rgba(16, 185, 129, 0.4)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <span style={{ fontWeight: 600, fontSize: "var(--font-sm)", color: "#34D399" }}>
                  ✅ Generated Response from {humanAiPlatform.toUpperCase()}:
                </span>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ padding: "4px 10px", fontSize: "0.75rem" }}
                  onClick={() => {
                    navigator.clipboard.writeText(humanResult);
                    alert("Copied AI response to clipboard!");
                  }}
                >
                  📋 Copy Response
                </button>
              </div>
              <div
                style={{
                  whiteSpace: "pre-wrap",
                  fontSize: "var(--font-xs)",
                  color: "var(--text-primary)",
                  lineHeight: 1.6,
                  maxHeight: 220,
                  overflowY: "auto",
                  padding: "10px",
                  background: "rgba(0, 0, 0, 0.25)",
                  borderRadius: "var(--radius-sm)",
                }}
              >
                {humanResult}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── 1-Click Chrome Profile Importer ── */}
      <div
        className="card"
        style={{
          marginBottom: "var(--space-6)",
          border: "1px solid hsla(250, 85%, 65%, 0.35)",
          background: "linear-gradient(180deg, hsla(250, 85%, 65%, 0.08) 0%, var(--bg-secondary) 100%)",
          boxShadow: "0 8px 32px rgba(0, 0, 0, 0.2)",
        }}
      >
        <div className="card-header" style={{ paddingBottom: "var(--space-3)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
            <div
              style={{
                width: 42,
                height: 42,
                borderRadius: "var(--radius-md)",
                background: "linear-gradient(135deg, #4285F4, #34A853, #FBBC05, #EA4335)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "1.4rem",
                boxShadow: "0 4px 12px rgba(66, 133, 244, 0.3)",
              }}
            >
              🌐
            </div>
            <div>
              <h3 className="card-title" style={{ fontSize: "var(--font-lg)" }}>
                1-Click Import from Google Chrome
              </h3>
              <p style={{ fontSize: "var(--font-xs)", color: "var(--text-secondary)", marginTop: "2px" }}>
                Import your saved logins, sessions, and cookies from your local Chrome browser with zero typing
              </p>
            </div>
          </div>
          <span
            className="badge badge-primary"
            style={{ fontSize: "var(--font-xs)", padding: "4px 10px" }}
          >
            {chromeProfiles.length} Chrome Profile{chromeProfiles.length !== 1 ? "s" : ""} Detected
          </span>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)", marginTop: "var(--space-3)" }}>
          {/* Step 1: Profile Selector */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--space-2)" }}>
              <label className="form-label" style={{ fontWeight: 600, margin: 0 }}>
                1. Choose Chrome Profile to Copy:
              </label>
              <span style={{ fontSize: "var(--font-xs)", color: "var(--text-secondary)" }}>
                Click a profile to select, or click <strong>⚡ Sync This Profile</strong> for instant 1-click import
              </span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "var(--space-3)" }}>
              {chromeProfiles.map((p) => {
                const isSelected = selectedChromeProfile === p.id;
                return (
                  <div
                    key={p.id}
                    onClick={() => setSelectedChromeProfile(p.id)}
                    style={{
                      padding: "var(--space-3) var(--space-4)",
                      borderRadius: "var(--radius-md)",
                      border: `2px solid ${isSelected ? "var(--accent-primary)" : "var(--border)"}`,
                      background: isSelected ? "var(--accent-primary-muted)" : "var(--bg-tertiary)",
                      cursor: "pointer",
                      transition: "all var(--transition-fast)",
                      display: "flex",
                      flexDirection: "column",
                      gap: "var(--space-2)",
                      boxShadow: isSelected ? "0 0 14px hsla(250, 85%, 65%, 0.25)" : "none",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                        <div
                          style={{
                            width: 36,
                            height: 36,
                            borderRadius: "50%",
                            background: isSelected ? "var(--accent-primary)" : "var(--bg-elevated)",
                            color: isSelected ? "#fff" : "var(--text-secondary)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            fontWeight: 700,
                            fontSize: "0.9rem",
                          }}
                        >
                          {p.name.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <div style={{ fontWeight: 600, fontSize: "var(--font-sm)", color: "var(--text-primary)" }}>
                            {p.name} {p.isDefault && <span style={{ color: "var(--accent-secondary)", fontSize: "0.75rem" }}>(Default)</span>}
                          </div>
                          <div style={{ fontSize: "var(--font-xs)", color: "var(--text-secondary)" }}>
                            {p.email || p.id}
                          </div>
                        </div>
                      </div>
                      <input
                        type="radio"
                        name="chromeProfile"
                        checked={isSelected}
                        onChange={() => setSelectedChromeProfile(p.id)}
                        style={{ accentColor: "var(--accent-primary)" }}
                      />
                    </div>

                    {/* Detected Logins in this profile */}
                    {p.detectedLogins && p.detectedLogins.length > 0 && (
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "2px" }}>
                        {p.detectedLogins.map((login) => (
                          <span
                            key={login}
                            style={{
                              fontSize: "0.68rem",
                              padding: "2px 7px",
                              borderRadius: "10px",
                              background: "rgba(52, 168, 83, 0.15)",
                              color: "#34A853",
                              fontWeight: 600,
                              border: "1px solid rgba(52, 168, 83, 0.3)",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "3px",
                            }}
                          >
                            <span>✓</span>
                            <span>
                              {login === "chatgpt" ? "ChatGPT Logged In" :
                                login === "claude" ? "Claude Logged In" :
                                  login === "linkedin" ? "LinkedIn" :
                                    login === "instagram" ? "Instagram" :
                                      login === "facebook" ? "Facebook" :
                                        login === "whatsapp" ? "WhatsApp" :
                                          login === "gemini" ? "Gemini" : login}
                            </span>
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Card Actions */}
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "4px", paddingTop: "6px", borderTop: "1px solid var(--border-subtle)" }}>
                      <span style={{ fontSize: "0.72rem", color: isSelected ? "var(--accent-primary)" : "var(--text-tertiary)", fontWeight: 500 }}>
                        {isSelected ? "● Selected Profile" : "Click to select"}
                      </span>
                      <div style={{ display: "flex", gap: "6px" }}>
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleLaunchBrowser(p.id);
                          }}
                          disabled={launchingBrowser}
                          style={{
                            fontSize: "0.72rem",
                            padding: "3px 8px",
                            borderRadius: "var(--radius-sm)",
                          }}
                          title="Launch this profile in Chrome on port 9222"
                        >
                          {launchingBrowser && selectedChromeProfile === p.id ? "Opening..." : "🌐 Launch Chrome"}
                        </button>
                        <button
                          type="button"
                          className="btn btn-primary btn-sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleCloneChromeProfile(p.id);
                          }}
                          disabled={cloningProfile}
                          style={{
                            fontSize: "0.72rem",
                            padding: "3px 8px",
                            fontWeight: 600,
                            borderRadius: "var(--radius-sm)",
                          }}
                        >
                          {cloningProfile && selectedChromeProfile === p.id ? "Syncing..." : "⚡ Sync"}
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Quick Active Selection Banner */}
            {selectedProfileDetails && (
              <div
                style={{
                  marginTop: "var(--space-3)",
                  padding: "var(--space-3) var(--space-4)",
                  borderRadius: "var(--radius-sm)",
                  background: "var(--bg-tertiary)",
                  border: "1px solid var(--accent-primary)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  flexWrap: "wrap",
                  gap: "var(--space-2)",
                }}
              >
                <div>
                  <span style={{ fontSize: "var(--font-sm)", fontWeight: 600, color: "var(--text-primary)" }}>
                    Ready to Use: {selectedProfileDetails.name} ({selectedProfileDetails.email || selectedProfileDetails.id})
                  </span>
                  <div style={{ fontSize: "var(--font-xs)", color: "var(--text-secondary)", marginTop: "2px" }}>
                    {browserConnected
                      ? `🟢 Browser is currently running and attached to automation on port 9222 (${browserProfileEmail || selectedProfileDetails.email})`
                      : "Click 'Launch Chrome' to open this profile on port 9222 for live AI generation and posting."}
                  </div>
                </div>
                <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => handleLaunchBrowser(selectedChromeProfile)}
                    disabled={launchingBrowser}
                    style={{ fontWeight: 600 }}
                  >
                    {launchingBrowser ? "Launching..." : `🌐 Launch Chrome (${selectedProfileDetails.email || "Port 9222"})`}
                  </button>
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    onClick={() => handleCloneChromeProfile()}
                    disabled={cloningProfile || targetPlatforms.length === 0}
                    style={{ fontWeight: 600 }}
                  >
                    {cloningProfile ? "Importing..." : `🚀 Import & Sync Now (${targetPlatforms.length} Platforms)`}
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Step 2: Destination Platforms */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--space-2)" }}>
              <label className="form-label" style={{ fontWeight: 600, margin: 0 }}>
                2. Select Automation Platforms to Sync:
              </label>
              <div style={{ display: "flex", gap: "var(--space-2)" }}>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  style={{ fontSize: "0.75rem", padding: "2px 8px" }}
                  onClick={selectAllTargetPlatforms}
                >
                  Select All
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  style={{ fontSize: "0.75rem", padding: "2px 8px" }}
                  onClick={deselectAllTargetPlatforms}
                >
                  Deselect All
                </button>
              </div>
            </div>

            <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>
              {ALL_AUTOMATION_PLATFORMS.map((platform) => {
                const isChecked = targetPlatforms.includes(platform.id);
                const hasSession = activeChromePlatforms[platform.id];
                return (
                  <label
                    key={platform.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "var(--space-2)",
                      padding: "var(--space-2) var(--space-3)",
                      borderRadius: "var(--radius-sm)",
                      border: `1px solid ${isChecked ? "var(--accent-primary)" : "var(--border)"}`,
                      background: isChecked ? "var(--accent-primary-muted)" : "var(--bg-tertiary)",
                      cursor: "pointer",
                      fontSize: "var(--font-xs)",
                      fontWeight: 500,
                      userSelect: "none",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => toggleTargetPlatform(platform.id)}
                      style={{ accentColor: "var(--accent-primary)" }}
                    />
                    <span>{platform.icon}</span>
                    <span>{platform.name}</span>
                    {hasSession && (
                      <span
                        style={{
                          fontSize: "0.65rem",
                          padding: "1px 5px",
                          borderRadius: "10px",
                          background: "var(--success-muted)",
                          color: "var(--success)",
                          marginLeft: 4,
                        }}
                      >
                        Active
                      </span>
                    )}
                  </label>
                );
              })}
            </div>
          </div>

          {/* Step 3: Options & Action */}
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "var(--space-3)",
              paddingTop: "var(--space-3)",
              borderTop: "1px solid var(--border)",
            }}
          >
            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: "var(--space-2)",
                fontSize: "var(--font-xs)",
                color: "var(--text-secondary)",
                cursor: "pointer",
              }}
            >
              <input
                type="checkbox"
                checked={forceCloseChrome}
                onChange={(e) => setForceCloseChrome(e.target.checked)}
                style={{ accentColor: "var(--accent-primary)" }}
              />
              <span>
                <strong>Automatically close Chrome during import</strong> (Required to unlock cookie files)
              </span>
            </label>

            <button
              className="btn btn-primary"
              onClick={handleCloneChromeProfile}
              disabled={cloningProfile || targetPlatforms.length === 0}
              style={{
                padding: "var(--space-2) var(--space-5)",
                display: "flex",
                alignItems: "center",
                gap: "var(--space-2)",
                fontWeight: 600,
              }}
            >
              {cloningProfile ? (
                <>
                  <span className="spinner" style={{ width: 14, height: 14 }} />
                  <span>Importing Profiles...</span>
                </>
              ) : (
                <>
                  <span>📥</span>
                  <span>
                    Import & Sync into {targetPlatforms.length} Platform{targetPlatforms.length !== 1 ? "s" : ""}
                  </span>
                </>
              )}
            </button>
          </div>

          {/* Feedback message */}
          {cloneFeedback && (
            <div
              style={{
                padding: "var(--space-3) var(--space-4)",
                borderRadius: "var(--radius-sm)",
                fontSize: "var(--font-sm)",
                background:
                  cloneFeedback.type === "success" ? "var(--success-muted)" : "var(--danger-muted)",
                color: cloneFeedback.type === "success" ? "var(--success)" : "var(--danger)",
                border: `1px solid ${cloneFeedback.type === "success" ? "var(--success)" : "var(--danger)"}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <span>{cloneFeedback.message}</span>
              <button
                type="button"
                onClick={() => setCloneFeedback(null)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "inherit",
                  cursor: "pointer",
                  fontWeight: "bold",
                }}
              >
                ✕
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Platform Selection */}
      <div className="card" style={{ marginBottom: "var(--space-6)" }}>
        <div className="card-header">
          <h3 className="card-title">Connected Social Media & AI Accounts</h3>
          <span style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>
            {selectedPlatforms.length} selected
          </span>
        </div>
        <div className="checkbox-group">
          {Object.entries(ALL_PLATFORMS_MAP).map(([key, platform]) => (
            <label
              key={key}
              className={`checkbox-label ${selectedPlatforms.includes(key) ? "checked" : ""}`}
              style={{
                borderColor: selectedPlatforms.includes(key) ? (platform.color || "var(--accent-primary)") : undefined,
                background: selectedPlatforms.includes(key) ? (platform.colorMuted || "var(--accent-primary-muted)") : undefined,
                minWidth: 160,
              }}
            >
              <input
                type="checkbox"
                checked={selectedPlatforms.includes(key)}
                onChange={() => togglePlatform(key)}
              />
              <span style={{ fontSize: "1.2rem" }}>{platform.icon || "🌐"}</span>
              <span style={{ fontWeight: 600 }}>{platform.name || key}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Dynamic Credential Fields */}
      {selectedPlatforms.length > 0 ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
          {[...new Set(selectedPlatforms)].map((platformKey, idx) => {
            const platform = getPlatformConfig(platformKey);
            const platformData = accounts[platformKey] || {};
            const savedAccount = savedAccounts.find((a) => a.platform === platformKey);
            const status = platformData.status || savedAccount?.session_status || "unverified";

            return (
              <div
                className="card"
                key={`platform-card-${platformKey}-${idx}`}
                style={{
                  borderLeft: `3px solid ${platform?.color || "var(--accent-primary)"}`,
                }}
              >
                <div className="card-header">
                  <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                    <span style={{ fontSize: "1.5rem" }}>{platform?.icon || "🌐"}</span>
                    <div>
                      <h3 className="card-title">{platform?.name || platformKey}</h3>
                      {platform?.loginNote && (
                        <p
                          style={{
                            fontSize: "var(--font-xs)",
                            color: "var(--text-tertiary)",
                            marginTop: "var(--space-1)",
                          }}
                        >
                          {platform.loginNote}
                        </p>
                      )}
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                      <span className={`status-dot ${status} pulse`} />
                      <span
                        style={{
                          fontSize: "var(--font-sm)",
                          color: "var(--text-secondary)",
                          textTransform: "capitalize",
                        }}
                      >
                        {status}
                      </span>
                    </div>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => testLogin(platformKey)}
                      disabled={testingLogin === platformKey}
                    >
                      {testingLogin === platformKey ? (
                        <>
                          <span className="spinner" style={{ width: 14, height: 14 }} />
                          Testing...
                        </>
                      ) : (
                        "🔑 Launch & Verify"
                      )}
                    </button>
                  </div>
                </div>

                <div className="form-row">
                  {(platform?.fields || []).map((field) => {
                    if (!shouldShowField(field, platformData)) return null;

                    return (
                      <div className="form-group" key={field.key}>
                        <label className="form-label">
                          {field.label}
                          {field.required && <span className="required">*</span>}
                        </label>
                        {field.type === "select" ? (
                          <select
                            className="form-select"
                            value={platformData[field.key] || field.defaultValue || ""}
                            onChange={(e) => updateField(platformKey, field.key, e.target.value)}
                          >
                            {field.options.map((opt) => (
                              <option key={opt} value={opt} style={{ textTransform: "capitalize" }}>
                                {opt.charAt(0).toUpperCase() + opt.slice(1)}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <input
                            className="form-input"
                            type={field.type}
                            value={platformData[field.key] || ""}
                            onChange={(e) => updateField(platformKey, field.key, e.target.value)}
                            placeholder={field.placeholder}
                          />
                        )}
                      </div>
                    );
                  })}
                </div>

                {savedAccount?.has_password && !platformData.password && (
                  <div
                    style={{
                      marginTop: "var(--space-3)",
                      padding: "var(--space-2) var(--space-3)",
                      background: "var(--success-muted)",
                      borderRadius: "var(--radius-sm)",
                      fontSize: "var(--font-xs)",
                      color: "var(--success)",
                      display: "flex",
                      alignItems: "center",
                      gap: "var(--space-2)",
                    }}
                  >
                    🔒 Password or session is saved in profile.
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : null}

      {/* ── AI & LLM Automation Accounts ── */}
      <div className="card" style={{ marginTop: "var(--space-6)", marginBottom: "var(--space-6)" }}>
        <div className="card-header">
          <div>
            <h3 className="card-title">🤖 AI Content Generation Profiles</h3>
            <p style={{ fontSize: "var(--font-xs)", color: "var(--text-secondary)", marginTop: "2px" }}>
              Browser automation accounts used to generate high-converting marketing text, product headlines, and social captions.
            </p>
          </div>
          <span className="badge badge-secondary" style={{ fontSize: "var(--font-xs)" }}>
            Zero API Keys Required
          </span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(290px, 1fr))", gap: "var(--space-4)", marginTop: "var(--space-4)" }}>
          {[
            {
              id: "chatgpt",
              name: "ChatGPT (OpenAI)",
              icon: "🟢",
              color: "#10a37f",
              url: "https://chatgpt.com",
              desc: "Generates high-converting marketing hooks, viral copy, and ad headlines",
            },
            {
              id: "claude",
              name: "Claude (Anthropic)",
              icon: "🟣",
              color: "#d97706",
              url: "https://claude.ai",
              desc: "Crafts engaging storytelling, long-form LinkedIn posts, and product descriptions",
            },
            {
              id: "gemini",
              name: "Google Gemini",
              icon: "♊",
              color: "#4285F4",
              url: "https://gemini.google.com",
              desc: "Deep research, multichannel post strategies, and multilingual translations",
            },
          ].map((ai) => {
            const hasProfile = activeChromePlatforms[ai.id];
            const isTesting = testingLogin === ai.id;
            return (
              <div
                key={ai.id}
                style={{
                  padding: "var(--space-4)",
                  borderRadius: "var(--radius-md)",
                  border: `1.5px solid ${hasProfile ? "var(--accent-primary)" : "var(--border)"}`,
                  background: "var(--bg-tertiary)",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  gap: "var(--space-3)",
                }}
              >
                <div>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "var(--space-2)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                      <span style={{ fontSize: "1.4rem" }}>{ai.icon}</span>
                      <strong style={{ fontSize: "var(--font-sm)", color: "var(--text-primary)" }}>{ai.name}</strong>
                    </div>
                    <span
                      style={{
                        fontSize: "0.7rem",
                        padding: "2px 8px",
                        borderRadius: "10px",
                        background: hasProfile ? "var(--success-muted)" : "var(--bg-elevated)",
                        color: hasProfile ? "var(--success)" : "var(--text-tertiary)",
                        fontWeight: 600,
                      }}
                    >
                      {hasProfile ? "✓ Profile Active" : "Not Synced"}
                    </span>
                  </div>
                  <p style={{ fontSize: "var(--font-xs)", color: "var(--text-secondary)", lineHeight: 1.4, margin: 0 }}>
                    {ai.desc}
                  </p>
                </div>

                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: "var(--space-2)", borderTop: "1px solid var(--border-subtle)" }}>
                  <a
                    href={ai.url}
                    target="_blank"
                    rel="noreferrer"
                    style={{ fontSize: "0.75rem", color: "var(--accent-primary)", textDecoration: "none" }}
                  >
                    Visit {ai.id}.com ↗
                  </a>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => testLogin(ai.id)}
                    disabled={isTesting}
                    style={{ fontSize: "0.75rem", padding: "4px 10px" }}
                  >
                    {isTesting ? (
                      <>
                        <span className="spinner" style={{ width: 12, height: 12 }} />
                        Opening...
                      </>
                    ) : (
                      "🔑 Open & Verify in Chrome"
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>


      {/* Info Box */}
      <div
        className="card"
        style={{
          marginTop: "var(--space-6)",
          background: "var(--info-muted)",
          borderColor: "var(--info)",
        }}
      >
        <h4
          style={{
            marginBottom: "var(--space-3)",
            display: "flex",
            alignItems: "center",
            gap: "var(--space-2)",
          }}
        >
          ℹ️ How Login & Profiles Work
        </h4>
        <div style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)", lineHeight: 1.8 }}>
          <p>
            <strong>1. 1-Click Import (Method 3):</strong> Select your existing Chrome profile above and click <em>&quot;Import &amp; Sync&quot;</em>. All existing sessions, cookies, and tokens are instantly cloned.
          </p>
          <p>
            <strong>2. Manual Verification:</strong> Click &quot;Launch &amp; Verify&quot; on any card to open a dedicated Chrome browser window for that platform.
          </p>
          <p>
            <strong>3. Zero API Keys:</strong> The automation uses undetected-chromedriver with your saved profiles to post as a real human.
          </p>
        </div>
      </div>
    </div>
  );
}
