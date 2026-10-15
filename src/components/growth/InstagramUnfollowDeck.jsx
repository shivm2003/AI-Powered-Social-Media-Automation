"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import styles from "./InstagramUnfollowDeck.module.css";

export default function InstagramUnfollowDeck() {
  const [totalFollowing, setTotalFollowing] = useState(null);
  const [username, setUsername] = useState("loansolutions2026");
  const [accounts, setAccounts] = useState([]);
  const [scanning, setScanning] = useState(false);
  const [selectedUsers, setSelectedUsers] = useState(new Set());

  // Configuration options
  const [targetCount, setTargetCount] = useState(10);
  const [safetyDelay, setSafetyDelay] = useState(10);

  // Active Job State
  const [activeJob, setActiveJob] = useState(null);
  const pollIntervalRef = useRef(null);

  // Scan Instagram for following accounts
  const scanFollowing = useCallback(async () => {
    setScanning(true);
    try {
      const res = await fetch("/api/growth/instagram-unfollow");
      const data = await res.json();
      if (data.success) {
        setTotalFollowing(data.totalFollowing);
        setUsername(data.username || "loansolutions2026");
        setAccounts(data.accounts || []);
      }
    } catch (err) {
      console.error("Error scanning Instagram following:", err);
    } finally {
      setScanning(false);
    }
  }, []);

  useEffect(() => {
    scanFollowing();
  }, [scanFollowing]);

  // Poll running job
  const pollJobStatus = useCallback(async (jobId) => {
    try {
      const res = await fetch(`/api/growth/instagram-unfollow?jobId=${jobId}`);
      const data = await res.json();
      if (data.success && data.job) {
        setActiveJob(data.job);
        if (data.job.status === "completed" || data.job.status === "failed" || data.job.status === "stopped") {
          clearInterval(pollIntervalRef.current);
          scanFollowing();
        }
      }
    } catch (err) {
      console.error("Error polling unfollow job status:", err);
    }
  }, [scanFollowing]);

  useEffect(() => {
    if (activeJob && activeJob.status === "running") {
      pollIntervalRef.current = setInterval(() => {
        pollJobStatus(activeJob.id);
      }, 2500);
    } else {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    }
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [activeJob, pollJobStatus]);

  // Handle Start Unfollowing
  const handleStartUnfollow = async (overrideCount = null, usersList = null) => {
    const effectiveCount = overrideCount !== null ? overrideCount : targetCount;
    try {
      const res = await fetch("/api/growth/instagram-unfollow", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          targetCount: parseInt(effectiveCount, 10),
          specificUsers: usersList,
          safetyDelay: parseInt(safetyDelay, 10),
        }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setActiveJob({
          id: data.jobId,
          status: "running",
          targetCount: effectiveCount,
          unfollowedCount: 0,
          unfollowedAccounts: [],
          logs: ["Unfollow sequence initiated. Connecting to Instagram profile..."],
        });
      } else {
        alert(data.error || "Failed to start unfollow task.");
      }
    } catch (err) {
      console.error("Error starting unfollow:", err);
      alert("Error starting unfollow task: " + err.message);
    }
  };

  // Stop Running Job
  const handleStopJob = async () => {
    if (!activeJob) return;
    try {
      await fetch(`/api/growth/instagram-unfollow?jobId=${activeJob.id}`, {
        method: "DELETE",
      });
      setActiveJob((prev) => ({
        ...prev,
        status: "stopped",
        logs: [...(prev.logs || []), "🛑 Stop requested by user."],
      }));
    } catch (err) {
      console.error("Error stopping unfollow job:", err);
    }
  };

  const toggleSelectUser = (uName) => {
    const next = new Set(selectedUsers);
    if (next.has(uName)) {
      next.delete(uName);
    } else {
      next.add(uName);
    }
    setSelectedUsers(next);
  };

  const toggleSelectAll = () => {
    if (selectedUsers.size === accounts.length) {
      setSelectedUsers(new Set());
    } else {
      setSelectedUsers(new Set(accounts.map((a) => a.username)));
    }
  };

  return (
    <div className={styles.deckContainer}>
      {/* Hero Header Card */}
      <div className={styles.heroCard}>
        <div className={styles.heroHeader}>
          <div className={styles.titleArea}>
            <h2>
              <span>📸</span> Instagram Unfollow Manager
            </h2>
            <p>
              Prune your following list cleanly with automated confirmation handling and human safety pacing.
            </p>
          </div>
          <div style={{ display: "flex", gap: "var(--space-3)", alignItems: "center" }}>
            <div className={styles.statsBadge}>
              <div>
                <div className={styles.statsCount}>
                  {scanning ? "..." : (totalFollowing !== null ? totalFollowing : "—")}
                </div>
                <div className={styles.statsLabel}>Total Following</div>
              </div>
            </div>
            <button
              onClick={scanFollowing}
              disabled={scanning}
              className={styles.btnSecondaryOutline}
              style={{ padding: "0.5rem 0.85rem", fontSize: "0.85rem" }}
            >
              {scanning ? "🔄 Scanning..." : "🔄 Refresh List"}
            </button>
          </div>
        </div>

        {/* Browser & Account Status Bar */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-3)", fontSize: "0.8rem", color: "var(--text-secondary)" }}>
          <span style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#10b981" }}></span>
            Active Account: <strong style={{ color: "var(--text-primary)" }}>@{username}</strong>
          </span>
          <span>•</span>
          <span>Browser Session: <strong>Chrome Port 9222</strong></span>
          <span>•</span>
          <span>Mode: <strong>Human Confirmation Dialog Bypass</strong></span>
        </div>
      </div>

      {/* Control Grid */}
      <div className={styles.controlGrid}>
        {/* Left: Accounts Following List */}
        <div className={styles.sectionBox}>
          <div className={styles.sectionTitle}>
            <span>📋 Accounts You Follow ({accounts.length})</span>
            {accounts.length > 0 && (
              <button
                onClick={toggleSelectAll}
                style={{ background: "none", border: "none", color: "#e1306c", fontSize: "0.75rem", cursor: "pointer", fontWeight: 600 }}
              >
                {selectedUsers.size === accounts.length ? "Deselect All" : "Select All"}
              </button>
            )}
          </div>

          <div className={styles.accountList}>
            {scanning ? (
              <div style={{ padding: "var(--space-4)", textAlign: "center", color: "var(--text-secondary)", fontSize: "0.875rem" }}>
                ⏳ Scanning your Instagram following list...
              </div>
            ) : accounts.length === 0 ? (
              <div style={{ padding: "var(--space-4)", textAlign: "center", color: "var(--text-secondary)", fontSize: "0.875rem" }}>
                No followed accounts discovered or list empty.
              </div>
            ) : (
              accounts.map((acc) => {
                const isSelected = selectedUsers.has(acc.username);
                return (
                  <div key={acc.username} className={styles.accountRow}>
                    <div className={styles.accountInfo}>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelectUser(acc.username)}
                        style={{ cursor: "pointer", accentColor: "#e1306c" }}
                      />
                      <div className={styles.accountAvatar}>
                        {acc.username.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <div className={styles.accountUsername}>@{acc.username}</div>
                        <a
                          href={acc.profile_url}
                          target="_blank"
                          rel="noreferrer"
                          className={styles.accountLink}
                        >
                          View Profile ↗
                        </a>
                      </div>
                    </div>
                    <span style={{ fontSize: "0.75rem", background: "rgba(255,255,255,0.06)", padding: "0.2rem 0.5rem", borderRadius: "var(--radius-sm)", color: "var(--text-secondary)" }}>
                      Following
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right: Quick Unfollow Actions & Active Job */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
          {/* Quick Actions Card */}
          <div className={styles.sectionBox}>
            <div className={styles.sectionTitle}>
              <span>⚡ Quick Unfollow Presets</span>
            </div>

            {/* Target & Delay controls */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3)" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "4px" }}>
                  UNFOLLOW COUNT
                </label>
                <select
                  value={targetCount}
                  onChange={(e) => setTargetCount(parseInt(e.target.value, 10))}
                  style={{ width: "100%", padding: "0.5rem", background: "var(--bg-primary)", border: "1px solid var(--border-color)", borderRadius: "var(--radius-md)", color: "var(--text-primary)" }}
                >
                  <option value={5}>Unfollow 5 Accounts</option>
                  <option value={10}>Unfollow 10 Accounts</option>
                  <option value={20}>Unfollow 20 Accounts</option>
                  <option value={0}>Unfollow All (0)</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "4px" }}>
                  SAFETY COOLDOWN
                </label>
                <select
                  value={safetyDelay}
                  onChange={(e) => setSafetyDelay(parseInt(e.target.value, 10))}
                  style={{ width: "100%", padding: "0.5rem", background: "var(--bg-primary)", border: "1px solid var(--border-color)", borderRadius: "var(--radius-md)", color: "var(--text-primary)" }}
                >
                  <option value={15}>Conservative (12-18s delay)</option>
                  <option value={10}>Balanced (8-13s delay)</option>
                  <option value={6}>Fast (5-8s delay)</option>
                </select>
              </div>
            </div>

            <div className={styles.actionButtonsGrid}>
              <button
                onClick={() => handleStartUnfollow(targetCount)}
                disabled={activeJob && activeJob.status === "running"}
                className={styles.btnPrimaryGradient}
              >
                <span>⚡ Unfollow {targetCount === 0 ? "All" : targetCount}</span>
              </button>

              <button
                onClick={() => handleStartUnfollow(selectedUsers.size, Array.from(selectedUsers))}
                disabled={selectedUsers.size === 0 || (activeJob && activeJob.status === "running")}
                className={styles.btnSecondaryOutline}
              >
                <span>🎯 Unfollow Selected ({selectedUsers.size})</span>
              </button>
            </div>
          </div>

          {/* Running Job Status Card */}
          {activeJob && (
            <div className={styles.activeJobCard}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-primary)" }}>
                    {activeJob.status === "running" && "⏳ Unfollow Sequence Active"}
                    {activeJob.status === "completed" && "🎉 Unfollow Finished"}
                    {activeJob.status === "stopped" && "🛑 Unfollow Stopped"}
                    {activeJob.status === "failed" && "⚠️ Unfollow Failed"}
                  </span>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                    Unfollowed: <strong>{activeJob.unfollowedCount || 0}</strong>
                    {activeJob.targetCount > 0 ? ` / ${activeJob.targetCount}` : ""}
                  </div>
                </div>

                {activeJob.status === "running" && (
                  <button
                    onClick={handleStopJob}
                    style={{ background: "#ef4444", color: "#fff", border: "none", padding: "0.4rem 0.8rem", borderRadius: "var(--radius-sm)", fontSize: "0.75rem", fontWeight: 600, cursor: "pointer" }}
                  >
                    🛑 Stop
                  </button>
                )}
              </div>

              {/* Progress bar */}
              {activeJob.targetCount > 0 && (
                <div className={styles.progressBarContainer}>
                  <div
                    className={styles.progressBarFill}
                    style={{
                      width: `${Math.min(100, Math.round(((activeJob.unfollowedCount || 0) / activeJob.targetCount) * 100))}%`,
                    }}
                  />
                </div>
              )}

              {/* Live Logs */}
              <div className={styles.logTerminal}>
                {(activeJob.logs || []).map((l, idx) => (
                  <div key={idx}>{l}</div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
