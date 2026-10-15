"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import styles from "./FacebookAcceptDeck.module.css";

export default function FacebookAcceptDeck() {
  const [pendingCount, setPendingCount] = useState(null);
  const [titleBadge, setTitleBadge] = useState("");
  const [requests, setRequests] = useState([]);
  const [scanning, setScanning] = useState(false);

  // Configuration options
  const [targetCount, setTargetCount] = useState(0); // 0 = all
  const [likeRecent, setLikeRecent] = useState(true);
  const [safetyDelay, setSafetyDelay] = useState(3);

  // Active Job State
  const [activeJob, setActiveJob] = useState(null);
  const pollIntervalRef = useRef(null);

  // Scan Facebook for pending requests
  const scanRequests = useCallback(async () => {
    setScanning(true);
    try {
      const res = await fetch("/api/growth/requests");
      const data = await res.json();
      if (data.success) {
        setPendingCount(data.count);
        setTitleBadge(data.titleBadge || "");
        setRequests(data.requests || []);
      }
    } catch (err) {
      console.error("Error scanning friend requests:", err);
    } finally {
      setScanning(false);
    }
  }, []);

  useEffect(() => {
    scanRequests();
  }, [scanRequests]);

  // Poll running job
  const pollJobStatus = useCallback(async (jobId) => {
    try {
      const res = await fetch(`/api/growth/requests?jobId=${jobId}`);
      const data = await res.json();
      if (data.success && data.job) {
        setActiveJob(data.job);
        if (data.job.status === "completed" || data.job.status === "failed" || data.job.status === "stopped") {
          clearInterval(pollIntervalRef.current);
          scanRequests();
        }
      }
    } catch (err) {
      console.error("Error polling job status:", err);
    }
  }, [scanRequests]);

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

  // Handle Accept All
  const handleStartAccepting = async () => {
    try {
      const res = await fetch("/api/growth/requests", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          targetCount: parseInt(targetCount, 10),
          likeRecent,
          safetyDelay: parseInt(safetyDelay, 10),
        }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setActiveJob({
          id: data.jobId,
          status: "running",
          targetCount,
          likeRecent,
          acceptedCount: 0,
          likedCount: 0,
          acceptedPeople: [],
          logs: ["Acceptance sequence initiated. Connecting to Facebook on port 9222..."],
        });
      } else {
        alert(data.error || "Failed to start accept sequence.");
      }
    } catch (err) {
      alert("Error: " + err.message);
    }
  };

  // Handle Stop
  const handleStopAccepting = async () => {
    if (!activeJob) return;
    try {
      await fetch(`/api/growth/requests?jobId=${activeJob.id}`, {
        method: "DELETE",
      });
      setActiveJob((prev) => prev ? { ...prev, status: "stopped" } : null);
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    } catch (err) {
      console.error("Error stopping accept job:", err);
    }
  };

  const isRunning = activeJob && activeJob.status === "running";
  const displayCount = pendingCount !== null ? pendingCount : (titleBadge ? `${titleBadge}` : "...");

  return (
    <div className={styles.deckContainer}>
      {/* Pending Requests Counter Banner */}
      <div className={styles.counterBanner}>
        <div className={styles.counterLeft}>
          <div className={styles.fbIconCircle}>
            <span>👥</span>
          </div>
          <div>
            <div className={styles.counterTitle}>
              <span>Facebook Friend Requests Center</span>
            </div>
            <p className={styles.counterSubtitle}>
              Detect, batch-accept pending friend requests, and automatically like their recent post using your authenticated Chrome profile.
            </p>
          </div>
        </div>

        <div className={styles.counterBadgeGroup}>
          <div className={styles.countPill}>
            <span className={styles.countNumber}>
              {scanning ? "..." : displayCount}
            </span>
            <span className={styles.countLabel}>
              {titleBadge ? `Pending (${titleBadge})` : "Pending Requests"}
            </span>
          </div>

          <button
            onClick={scanRequests}
            disabled={scanning || isRunning}
            className={styles.refreshBtn}
            title="Rescan Facebook for fresh incoming requests"
          >
            <span className={scanning ? styles.spinning : ""}>🔄</span>
            <span>{scanning ? "Scanning..." : "Rescan"}</span>
          </button>
        </div>
      </div>

      {/* Control Configuration Card */}
      <div className={styles.controlsCard}>
        <div className={styles.configGrid}>
          <div className={styles.configGroup}>
            <label className={styles.configLabel}>
              <span>🎯</span> Batch Target
            </label>
            <select
              value={targetCount}
              onChange={(e) => setTargetCount(parseInt(e.target.value, 10))}
              disabled={isRunning}
              className={styles.configSelect}
            >
              <option value={0}>Accept All at Once ({displayCount} Pending)</option>
              <option value={10}>Accept First 10</option>
              <option value={20}>Accept First 20</option>
              <option value={50}>Accept Up to 50</option>
            </select>
          </div>

          <div className={styles.configGroup}>
            <label className={styles.configLabel}>
              <span>⏱️</span> Human Safety Delay
            </label>
            <select
              value={safetyDelay}
              onChange={(e) => setSafetyDelay(parseInt(e.target.value, 10))}
              disabled={isRunning}
              className={styles.configSelect}
            >
              <option value={2}>Fast (2 - 3 seconds)</option>
              <option value={3}>Recommended (3 - 5 seconds)</option>
              <option value={6}>Ultra Safe (5 - 8 seconds)</option>
            </select>
          </div>

          <div className={styles.configGroup}>
            <label className={styles.configLabel}>
              <span>🌐</span> Target Browser
            </label>
            <input
              type="text"
              readOnly
              value="Chrome Port 9222 (Shivam Mishra)"
              className={styles.configInput}
              style={{ opacity: 0.8, cursor: "not-allowed" }}
            />
          </div>
        </div>

        {/* Auto-Like Toggle */}
        <div
          className={styles.checkboxCard}
          onClick={() => !isRunning && setLikeRecent(!likeRecent)}
        >
          <div className={`${styles.customCheckbox} ${likeRecent ? styles.checkboxChecked : ""}`}>
            {likeRecent && "✓"}
          </div>
          <div>
            <div className={styles.checkboxTextTitle}>
              👍 Also like their latest post after accepting
            </div>
            <div className={styles.checkboxTextDesc}>
              Visits each requester&apos;s profile feed in a background tab and hits Like on their top post to build immediate engagement and reciprocity.
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className={styles.buttonRow}>
          <button
            onClick={handleStartAccepting}
            disabled={isRunning || pendingCount === 0}
            className={styles.btnAcceptAll}
          >
            <span>{isRunning ? "⏳" : "⚡"}</span>
            <span>
              {isRunning
                ? "Accepting Requests in Progress..."
                : `Accept All at Once (${displayCount} Pending) ${likeRecent ? "+ Like" : ""}`}
            </span>
          </button>

          {isRunning && (
            <button onClick={handleStopAccepting} className={styles.btnStop}>
              <span>🛑</span>
              <span>Stop Accepting</span>
            </button>
          )}
        </div>
      </div>

      {/* Live Execution Progress HUD */}
      {activeJob && (
        <div className={styles.progressHUD}>
          <div className={styles.hudHeader}>
            <div className={styles.hudTitle}>
              <span>⚡</span>
              <span>
                {activeJob.status === "running" && "Acceptance & Engagement Active"}
                {activeJob.status === "completed" && "✅ All Selected Requests Accepted!"}
                {activeJob.status === "stopped" && "🛑 Sequence Halted by User"}
                {activeJob.status === "failed" && "❌ Acceptance Encountered an Issue"}
              </span>
            </div>

            <div className={styles.hudStatsRow}>
              <div className={styles.hudStat}>
                <span className={styles.hudStatNumber}>{activeJob.acceptedCount || 0}</span>
                <span className={styles.hudStatLabel}>Accepted</span>
              </div>
              {likeRecent && (
                <div className={styles.hudStat}>
                  <span className={styles.hudStatNumber} style={{ color: "#38bdf8" }}>
                    {activeJob.likedCount || 0}
                  </span>
                  <span className={styles.hudStatLabel}>Posts Liked</span>
                </div>
              )}
            </div>
          </div>

          <div className={styles.progressBarContainer}>
            <div
              className={styles.progressBarFill}
              style={{
                width: `${Math.min(
                  100,
                  activeJob.targetCount > 0
                    ? ((activeJob.acceptedCount || 0) / activeJob.targetCount) * 100
                    : pendingCount > 0
                    ? ((activeJob.acceptedCount || 0) / pendingCount) * 100
                    : 100
                )}%`,
              }}
            />
          </div>

          {/* Activity Log Stream */}
          <div className={styles.logBox}>
            {activeJob.logs?.map((log, idx) => (
              <div key={idx} dangerouslySetInnerHTML={{ __html: log }} />
            ))}
          </div>
        </div>
      )}

      {/* Pending Requesters Preview Grid */}
      {requests.length > 0 && (
        <div style={{ marginTop: "1rem" }}>
          <div style={{ fontSize: "1rem", fontWeight: 700, color: "#ffffff", marginBottom: "0.5rem" }}>
            📋 Incoming Friend Requests Preview ({requests.length} Detected)
          </div>
          <div className={styles.requestsGrid}>
            {requests.slice(0, 12).map((req, i) => (
              <div key={req.id || i} className={styles.requestCard}>
                <div className={styles.requestUser}>
                  <div className={styles.userAvatar}>
                    {req.name ? req.name.charAt(0).toUpperCase() : "U"}
                  </div>
                  <div>
                    <div className={styles.requestName}>{req.name}</div>
                    <div className={styles.requestSub}>
                      {req.mutual_friends || "Pending Request"} {req.time_ago ? `• ${req.time_ago}` : ""}
                    </div>
                  </div>
                </div>
                <span className={styles.pendingTag}>Pending</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
