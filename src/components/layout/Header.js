"use client";

import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";

const pageTitles = {
  "/": "Dashboard",
  "/products": "Products",
  "/accounts": "Accounts",
  "/generate": "Generate Content",
  "/growth": "Outreach & Growth",
  "/campaigns": "Campaigns",
  "/settings": "Settings",
};

export default function Header() {
  const pathname = usePathname();
  const [mounted, setMounted] = useState(false);
  const [browserConnected, setBrowserConnected] = useState(false);
  const [profileEmail, setProfileEmail] = useState("2003shivam1990@gmail.com");
  const [launchingBrowser, setLaunchingBrowser] = useState(false);

  async function checkBrowserStatus() {
    try {
      const res = await fetch("/api/browser");
      if (res.ok) {
        const data = await res.json();
        setBrowserConnected(!!data.connected);
        if (data.profileEmail) setProfileEmail(data.profileEmail);
      }
    } catch {
      // ignore
    }
  }

  useEffect(() => {
    setMounted(true);
    checkBrowserStatus();
    const interval = setInterval(checkBrowserStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  async function handleLaunchBrowser() {
    setLaunchingBrowser(true);
    try {
      const res = await fetch("/api/browser", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profileId: "Default", forceSync: true }),
      });
      const data = await res.json();
      if (res.ok) {
        setBrowserConnected(true);
        if (data.profileEmail) setProfileEmail(data.profileEmail);
        alert(data.message || `Chrome launched with ${data.profileEmail || "2003shivam1990@gmail.com"} on port 9222!`);
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

  const getTitle = () => {
    if (!mounted || !pathname) return "Dashboard";
    if (pageTitles[pathname]) return pageTitles[pathname];
    if (pathname.startsWith("/products/")) return "Edit Product";
    if (pathname.startsWith("/generate/")) return "Generate Content";
    if (pathname.startsWith("/campaigns/")) return "Campaign Details";
    if (pathname.startsWith("/growth")) return "Outreach & Growth";
    return "Dashboard";
  };

  return (
    <header className="header">
      <div className="header-left">
        <div className="header-breadcrumb">
          <span>AI Social</span>
          <span>›</span>
          <span className="current" suppressHydrationWarning>{getTitle()}</span>
        </div>
      </div>

      <div className="header-right" style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
        {/* Browser Connection Indicator */}
        {browserConnected ? (
          <div
            title={`Bot is attached to Chrome profile: ${profileEmail} on port 9222`}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "var(--space-2)",
              padding: "var(--space-1) var(--space-3)",
              background: "rgba(16, 185, 129, 0.15)",
              border: "1px solid rgba(16, 185, 129, 0.3)",
              borderRadius: "var(--radius-full)",
              fontSize: "var(--font-xs)",
              fontWeight: 600,
              color: "var(--success)",
            }}
          >
            <span className="status-dot verified pulse" />
            🌐 Synced: {profileEmail}
          </div>
        ) : (
          <button
            onClick={handleLaunchBrowser}
            disabled={launchingBrowser}
            title={`Launch Chrome with ${profileEmail} and remote debugging so bot works in the same browser`}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "var(--space-2)",
              padding: "var(--space-1) var(--space-3)",
              background: "rgba(124, 92, 252, 0.15)",
              border: "1px solid rgba(124, 92, 252, 0.35)",
              borderRadius: "var(--radius-full)",
              fontSize: "var(--font-xs)",
              fontWeight: 600,
              color: "var(--primary-light)",
              cursor: "pointer",
            }}
          >
            <span>{launchingBrowser ? "⏳ Launching..." : `⚡ Sync Chrome (${profileEmail})`}</span>
          </button>
        )}

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "var(--space-2)",
            padding: "var(--space-1) var(--space-3)",
            background: "var(--success-muted)",
            borderRadius: "var(--radius-full)",
            fontSize: "var(--font-xs)",
            fontWeight: 600,
            color: "var(--success)",
          }}
        >
          <span className="status-dot verified pulse" />
          System Online
        </div>
      </div>
    </header>
  );
}
