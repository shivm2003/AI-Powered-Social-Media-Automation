"use client";

import { usePathname } from "next/navigation";
import { useState, useEffect, useCallback } from "react";
import styles from "./Header.module.css";

const pageTitles = {
  "/": "Command Dashboard",
  "/products": "Products & Brands",
  "/accounts": "Accounts & Browser Sync",
  "/generate": "Content Studio",
  "/growth": "Outreach & Growth",
  "/campaigns": "Campaign Management",
  "/settings": "System Settings",
};

export default function Header() {
  const pathname = usePathname();
  const [browserConnected, setBrowserConnected] = useState(false);
  const [profileEmail, setProfileEmail] = useState("2003shivam1990@gmail.com");
  const [launchingBrowser, setLaunchingBrowser] = useState(false);

  const checkBrowserStatus = useCallback(async () => {
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
  }, []);

  useEffect(() => {
    checkBrowserStatus();
    const interval = setInterval(checkBrowserStatus, 5000);
    return () => clearInterval(interval);
  }, [checkBrowserStatus]);

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
    if (!pathname) return "Command Dashboard";
    if (pageTitles[pathname]) return pageTitles[pathname];
    if (pathname.startsWith("/products/")) return "Edit Product";
    if (pathname.startsWith("/generate/")) return "Content Studio";
    if (pathname.startsWith("/campaigns/")) return "Campaign Details";
    if (pathname.startsWith("/growth")) return "Outreach & Growth";
    return "Command Dashboard";
  };

  return (
    <header className={styles.header}>
      <div className={styles.headerLeft}>
        <div className={styles.breadcrumb}>
          <span className={styles.brandLink}>
            <span>⚡</span> Manvxi AI
          </span>
          <span className={styles.separator}>›</span>
          <span className={styles.currentPage} suppressHydrationWarning>
            {getTitle()}
          </span>
        </div>
      </div>

      <div className={styles.headerRight}>
        {/* Browser Connection Indicator */}
        {browserConnected ? (
          <div
            className={styles.syncedBadge}
            title={`Bot is attached to Chrome profile: ${profileEmail} on port 9222`}
          >
            <span className={styles.statusDot} />
            <span>🌐 Synced: {profileEmail}</span>
          </div>
        ) : (
          <button
            onClick={handleLaunchBrowser}
            disabled={launchingBrowser}
            className={styles.launchButton}
            title={`Launch Chrome with ${profileEmail} and remote debugging on port 9222`}
          >
            <span>{launchingBrowser ? "⏳ Launching..." : `⚡ Sync Chrome (${profileEmail})`}</span>
          </button>
        )}

        <div className={styles.systemBadge}>
          <span className={styles.statusDot} />
          <span>System Online</span>
        </div>
      </div>
    </header>
  );
}
