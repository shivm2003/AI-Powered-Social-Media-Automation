"use client";

import { useState, useEffect, useRef } from "react";
import styles from "./ManualPostShareDeck.module.css";

export default function ManualPostShareDeck() {
  const [postUrl, setPostUrl] = useState("");
  const [platform, setPlatform] = useState("auto"); // "auto" | "instagram" | "facebook" | "both"
  const [shareAll, setShareAll] = useState(true);
  const [targetCount, setTargetCount] = useState(30);
  const [safetyDelay, setSafetyDelay] = useState(8);

  const [chromeAccounts, setChromeAccounts] = useState([]);
  const [selectedAccountId, setSelectedAccountId] = useState("");
  const [selectedProfileDir, setSelectedProfileDir] = useState("Default");

  const [activeTask, setActiveTask] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState([]);
  const [errorMsg, setErrorMsg] = useState(null);
  const [historyTasks, setHistoryTasks] = useState([]);

  const pollIntervalRef = useRef(null);

  const startPolling = (taskId) => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    pollIntervalRef.current = setInterval(async () => {
      try {
        const res = await fetch(`/api/growth/share-link?id=${taskId}`);
        const data = await res.json();
        if (data.success && data.task) {
          const t = data.task;
          setActiveTask(t);
          if (t.logs) {
            const parsed = typeof t.logs === "string" ? JSON.parse(t.logs) : t.logs;
            setLogs(parsed);
          }
          if (t.status === "completed" || t.status === "failed" || t.status === "stopped") {
            setIsRunning(false);
            clearInterval(pollIntervalRef.current);
            fetchHistoryTasks();
          }
        }
      } catch (e) {
        console.debug("Polling error:", e);
      }
    }, 2500);
  };

  const fetchHistoryTasks = async () => {
    try {
      const res = await fetch("/api/growth/share-link");
      const data = await res.json();
      if (data.success && Array.isArray(data.tasks)) {
        setHistoryTasks(data.tasks);
        const running = data.tasks.find((t) => t.status === "running");
        if (running && !activeTask) {
          setActiveTask(running);
          setIsRunning(true);
          startPolling(running.id);
        }
      }
    } catch (e) {
      console.debug("Failed fetching history:", e);
    }
  };

  // Load Chrome accounts & tasks on mount
  useEffect(() => {
    async function loadAccounts() {
      try {
        const res = await fetch("/api/accounts");
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          setChromeAccounts(data);
          const def = data.find((a) => a.is_default) || data[0];
          setSelectedAccountId(def.id || "1");
          setSelectedProfileDir(def.profile_dir || def.profile_directory || "Default");
        }
      } catch (e) {
        console.error("Failed to load Chrome accounts:", e);
      }
    }
    loadAccounts();
    fetchHistoryTasks();

    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  const detectedPlatform = () => {
    const u = (postUrl || "").toLowerCase();
    if (u.includes("instagram.com") || u.includes("instagr.am")) return "instagram";
    if (u.includes("facebook.com")) return "facebook";
    return null;
  };

  const handleStartShare = async () => {
    if (!postUrl.trim().startsWith("http")) {
      setErrorMsg("Please enter a valid post URL starting with http:// or https://");
      return;
    }

    setErrorMsg(null);
    setIsRunning(true);
    setLogs([`🚀 Preparing post share task for: ${postUrl.trim()}...`]);

    try {
      const res = await fetch("/api/growth/share-link", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          postUrl: postUrl.trim(),
          platform,
          shareAll,
          targetCount: parseInt(targetCount, 10),
          safetyDelay: parseInt(safetyDelay, 10),
          accountId: selectedAccountId,
          profileDir: selectedProfileDir,
        }),
      });

      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.error || "Failed to start manual post sharing");
      }

      setActiveTask({
        id: data.taskId,
        status: "running",
        platform: data.platform || platform,
        location: postUrl.trim(),
        target_count: shareAll ? 9999 : targetCount,
      });

      startPolling(data.taskId);
    } catch (err) {
      console.error("Error starting post share:", err);
      setErrorMsg(err.message);
      setIsRunning(false);
    }
  };

  const handleStopShare = async () => {
    if (!activeTask) return;
    try {
      await fetch(`/api/growth/share-link?id=${activeTask.id}`, { method: "DELETE" });
      setIsRunning(false);
      setLogs((prev) => [...prev, "🛑 Stop signal dispatched by user."]);
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      fetchHistoryTasks();
    } catch (e) {
      console.error("Error stopping share task:", e);
    }
  };

  const det = detectedPlatform();
  const totalSharesAllTime = historyTasks.reduce(
    (acc, t) => acc + (t.fb_sent_count || 0) + (t.ig_sent_count || 0),
    0
  );

  return (
    <div className={styles.deckContainer}>
      {/* Top Banner */}
      <div className={styles.counterBanner}>
        <div className={styles.counterLeft}>
          <div className={styles.iconCircle}>🔗</div>
          <div>
            <div className={styles.counterTitle}>
              <span>Manual Post Link Sharer</span>
              <span className="badge badge-success" style={{ fontSize: "0.75rem", padding: "2px 8px" }}>
                Direct Link Mode
              </span>
            </div>
            <div className={styles.counterSubtitle}>
              Share any Instagram or Facebook post/reel directly to your friends and followers using its manual link.
            </div>
          </div>
        </div>

        <div className={styles.counterBadgeGroup}>
          <div className={styles.countPill}>
            <span className={styles.countNumber}>{historyTasks.length}</span>
            <span className={styles.countLabel}>Posts Shared</span>
          </div>
          <div className={styles.countPill}>
            <span className={styles.countNumber} style={{ color: "#3dd6d0" }}>
              {totalSharesAllTime}
            </span>
            <span className={styles.countLabel}>Recipients Reached</span>
          </div>
        </div>
      </div>

      {/* Main Configuration Card */}
      <div className={styles.controlsCard}>
        <div className={styles.sectionHeading}>
          <span>📌</span>
          <span>Target Post URL</span>
        </div>

        <div className={styles.urlInputContainer}>
          <input
            type="text"
            className={styles.urlInput}
            placeholder="Paste Instagram or Facebook post link (e.g. https://www.instagram.com/p/... or https://www.facebook.com/...)"
            value={postUrl}
            onChange={(e) => setPostUrl(e.target.value)}
            disabled={isRunning}
          />
          {det === "instagram" && (
            <div className={`${styles.detectBadge} ${styles.badgeInstagram}`}>
              📸 Instagram Post
            </div>
          )}
          {det === "facebook" && (
            <div className={`${styles.detectBadge} ${styles.badgeFacebook}`}>
              📘 Facebook Post
            </div>
          )}
          {!det && postUrl.trim().startsWith("http") && (
            <div className={`${styles.detectBadge} ${styles.badgeBoth}`}>
              🌐 Web Link
            </div>
          )}
        </div>

        {errorMsg && (
          <div style={{ color: "#f43f5e", fontSize: "0.85rem", fontWeight: 600 }}>
            ⚠️ {errorMsg}
          </div>
        )}

        <div className={styles.gridTwo}>
          {/* Target Platform Selector */}
          <div className={styles.configGroup}>
            <label className={styles.configLabel}>Target Platform</label>
            <div className={styles.segmentedControl}>
              <button
                type="button"
                className={`${styles.segmentedBtn} ${platform === "auto" ? styles.segmentedBtnActive : ""}`}
                onClick={() => setPlatform("auto")}
                disabled={isRunning}
              >
                <span>⚡ Auto-Detect</span>
              </button>
              <button
                type="button"
                className={`${styles.segmentedBtn} ${platform === "instagram" ? styles.segmentedBtnActive : ""}`}
                onClick={() => setPlatform("instagram")}
                disabled={isRunning}
              >
                <span>📸 Instagram</span>
              </button>
              <button
                type="button"
                className={`${styles.segmentedBtn} ${platform === "facebook" ? styles.segmentedBtnActive : ""}`}
                onClick={() => setPlatform("facebook")}
                disabled={isRunning}
              >
                <span>📘 Facebook</span>
              </button>
            </div>
          </div>

          {/* Chrome Account Profile Selector */}
          <div className={styles.configGroup}>
            <label className={styles.configLabel}>Sender Chrome Profile</label>
            <select
              className={styles.selectBox}
              value={selectedAccountId}
              onChange={(e) => {
                const acc = chromeAccounts.find((a) => a.id === e.target.value);
                setSelectedAccountId(e.target.value);
                if (acc) setSelectedProfileDir(acc.profile_dir || acc.profile_directory || "Default");
              }}
              disabled={isRunning}
            >
              {chromeAccounts.map((acc, idx) => (
                <option key={acc.id || idx} value={acc.id}>
                  👤 {acc.google_name || acc.name || `Profile ${idx + 1}`} ({acc.profile_dir || "Default"})
                </option>
              ))}
              {chromeAccounts.length === 0 && <option value="">Default Chrome Profile</option>}
            </select>
          </div>
        </div>

        <div className={styles.gridTwo}>
          {/* Share Mode & Target Count */}
          <div className={styles.configGroup}>
            <label className={styles.configLabel}>Audience Reach</label>
            <div className={styles.toggleRow}>
              <span style={{ fontSize: "0.88rem", fontWeight: 600, color: "#ffffff" }}>
                🚀 Share to ALL Friends & Followers
              </span>
              <input
                type="checkbox"
                checked={shareAll}
                onChange={(e) => setShareAll(e.target.checked)}
                disabled={isRunning}
                style={{ width: "18px", height: "18px", cursor: "pointer" }}
              />
            </div>
            {!shareAll && (
              <div style={{ marginTop: "0.5rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", color: "rgba(226, 232, 240, 0.7)" }}>
                  <span>Custom Target Count:</span>
                  <span style={{ fontWeight: 700, color: "#3dd6d0" }}>{targetCount} friends</span>
                </div>
                <input
                  type="range"
                  min="5"
                  max="150"
                  step="5"
                  value={targetCount}
                  onChange={(e) => setTargetCount(Number(e.target.value))}
                  disabled={isRunning}
                  style={{ width: "100%", marginTop: "0.25rem" }}
                />
              </div>
            )}
          </div>

          {/* Anti-Spam Human Safety Delay */}
          <div className={styles.configGroup}>
            <label className={styles.configLabel}>
              Human Safety Delay: <span style={{ color: "#ec4899" }}>{safetyDelay}s per follow/share</span>
            </label>
            <div className={styles.toggleRow} style={{ flexDirection: "column", alignItems: "stretch", gap: "0.5rem" }}>
              <input
                type="range"
                min="6"
                max="14"
                step="1"
                value={safetyDelay}
                onChange={(e) => setSafetyDelay(Number(e.target.value))}
                disabled={isRunning}
                style={{ width: "100%" }}
              />
              <span style={{ fontSize: "0.75rem", color: "rgba(226, 232, 240, 0.6)" }}>
                Pacing between recipient selections (6-8s recommended to bypass Meta anti-bot limits).
              </span>
            </div>
          </div>
        </div>

        {/* Action Button Row */}
        <div className={styles.actionBtnRow}>
          <button
            type="button"
            className={styles.primaryShareBtn}
            onClick={handleStartShare}
            disabled={isRunning || !postUrl.trim()}
          >
            <span>{isRunning ? "⏳ Sharing Post to Friends..." : "🚀 Start Sharing Post to Friends"}</span>
          </button>

          {isRunning && (
            <button type="button" className={styles.stopBtn} onClick={handleStopShare}>
              🛑 Stop Sharing
            </button>
          )}
        </div>
      </div>

      {/* Live Active Task / Progress Box */}
      {(isRunning || logs.length > 0) && (
        <div className={styles.liveTaskCard}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontWeight: 700 }}>
              <span className={isRunning ? "status-indicator status-running" : "status-indicator status-ready"} />
              <span>{isRunning ? "Live Post Sharing Progress" : "Task Status"}</span>
            </div>
            {activeTask && (
              <span style={{ fontSize: "0.8rem", color: "#3dd6d0", fontFamily: "monospace" }}>
                Task: {activeTask.id?.substring(0, 8)} | Status: {activeTask.status?.toUpperCase()}
              </span>
            )}
          </div>

          <div className={styles.terminalBox}>
            {logs.map((log, idx) => (
              <div key={idx} className={styles.terminalLine}>
                {log}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Past Manual Share Tasks History */}
      {historyTasks.length > 0 && (
        <div className={styles.controlsCard}>
          <div className={styles.sectionHeading}>
            <span>📋</span>
            <span>Recent Manual Post Share History</span>
          </div>

          <div style={{ overflowX: "auto" }}>
            <table className={styles.historyTable}>
              <thead>
                <tr>
                  <th>Platform</th>
                  <th>Post Link</th>
                  <th>Target</th>
                  <th>Status</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {historyTasks.slice(0, 10).map((t) => (
                  <tr key={t.id}>
                    <td>
                      <span style={{ fontWeight: 600 }}>
                        {t.platform === "instagram" ? "📸 Instagram" : t.platform === "facebook" ? "📘 Facebook" : "⚡ Both"}
                      </span>
                    </td>
                    <td>
                      <a
                        href={t.location}
                        target="_blank"
                        rel="noreferrer"
                        style={{ color: "#7c5cfc", textDecoration: "underline", maxWidth: "320px", display: "inline-block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                      >
                        {t.location}
                      </a>
                    </td>
                    <td>{t.target_count >= 9999 ? "All Friends" : `${t.target_count} friends`}</td>
                    <td>
                      <span
                        className={`badge ${
                          t.status === "completed" ? "badge-success" : t.status === "running" ? "badge-warning" : "badge-secondary"
                        }`}
                        style={{ fontSize: "0.75rem", padding: "2px 8px" }}
                      >
                        {t.status}
                      </span>
                    </td>
                    <td style={{ fontSize: "0.75rem", color: "rgba(226, 232, 240, 0.6)" }}>
                      {new Date(t.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
