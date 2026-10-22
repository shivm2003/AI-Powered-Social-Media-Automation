"use client";

import { useState, useEffect, useRef } from "react";
import styles from "./FriendsGroupDeck.module.css";

export default function FriendsGroupDeck() {
  const [platform, setPlatform] = useState("both"); // "facebook" | "instagram" | "both"
  const [groupType, setGroupType] = useState("all"); // "community_group" | "messenger_chat" | "ig_direct_group" | "all"
  const [groupName, setGroupName] = useState("My VIP Community 2026");
  const [privacy, setPrivacy] = useState("private");
  const [maxInvites, setMaxInvites] = useState(50);
  const [initialMessage, setInitialMessage] = useState("Welcome everyone to our exclusive community group!");

  const [activeTask, setActiveTask] = useState(null);
  const [createdGroups, setCreatedGroups] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState([]);
  const [errorMsg, setErrorMsg] = useState(null);

  const pollIntervalRef = useRef(null);

  // Load existing groups on mount
  useEffect(() => {
    fetchCreatedGroups();
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  const fetchCreatedGroups = async () => {
    try {
      const res = await fetch("/api/growth/groups");
      const data = await res.json();
      if (data.success && data.groups) {
        setCreatedGroups(data.groups);
      }
    } catch (e) {
      console.debug("Failed fetching groups:", e);
    }
  };

  const handleStartGroupCreation = async () => {
    setErrorMsg(null);
    setIsRunning(true);
    setLogs([`🚀 Launching group creation task for ${platform.toUpperCase()}...`]);

    try {
      const res = await fetch("/api/growth/groups", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          platform,
          groupType: platform === "facebook" && groupType === "all" ? "community_group" : groupType,
          groupName,
          privacy,
          initialMessage,
          maxInvites: parseInt(maxInvites, 10),
        }),
      });

      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.error || "Failed to start group creation");
      }

      setActiveTask({
        id: data.taskId,
        status: "creating",
        groupName,
        platform,
        memberCount: 0,
      });

      // Start polling for progress
      pollIntervalRef.current = setInterval(() => {
        checkTaskStatus(data.taskId);
      }, 2500);

    } catch (err) {
      console.error("Error creating group:", err);
      setErrorMsg(err.message);
      setIsRunning(false);
    }
  };

  const checkTaskStatus = async (taskId) => {
    try {
      const res = await fetch(`/api/growth/groups?id=${taskId}`);
      const data = await res.json();

      if (data.success && data.group) {
        const grp = data.group;
        setActiveTask(grp);

        if (grp.logs) {
          const parsed = typeof grp.logs === "string" ? JSON.parse(grp.logs) : grp.logs;
          setLogs(parsed);
        }

        if (grp.status === "completed" || grp.status === "failed" || grp.status === "stopped") {
          setIsRunning(false);
          clearInterval(pollIntervalRef.current);
          fetchCreatedGroups();
        }
      }
    } catch (e) {
      console.debug("Polling task error:", e);
    }
  };

  const handleStopTask = async () => {
    if (!activeTask) return;
    try {
      await fetch(`/api/growth/groups?id=${activeTask.id}`, { method: "DELETE" });
      setIsRunning(false);
      setLogs((prev) => [...prev, "🛑 Task stop signal dispatched by user."]);
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      fetchCreatedGroups();
    } catch (e) {
      console.error("Error stopping task:", e);
    }
  };

  const totalMembersInvited = createdGroups.reduce((acc, g) => acc + (g.member_count || 0), 0);

  return (
    <div className={styles.deckContainer}>
      {/* Banner */}
      <div className={styles.counterBanner}>
        <div className={styles.counterLeft}>
          <div className={styles.iconCircle}>👨‍👩‍👧‍👦</div>
          <div>
            <div className={styles.counterTitle}>
              <span>Social Friends Group Creator</span>
              <span className="badge badge-success" style={{ fontSize: "0.75rem", padding: "2px 8px" }}>
                Auto-Invite Engine
              </span>
            </div>
            <div className={styles.counterSubtitle}>
              Assemble all your Facebook and Instagram friends into native groups or group chats with automated invitations.
            </div>
          </div>
        </div>

        <div className={styles.counterBadgeGroup}>
          <div className={styles.countPill}>
            <span className={styles.countNumber}>{createdGroups.length}</span>
            <span className={styles.countLabel}>Groups Created</span>
          </div>
          <div className={styles.countPill}>
            <span className={styles.countNumber} style={{ color: "#3dd6d0" }}>{totalMembersInvited}</span>
            <span className={styles.countLabel}>Friends Invited</span>
          </div>
        </div>
      </div>

      {/* Configuration Controls */}
      <div className={styles.controlsCard}>
        <div className={styles.configGroup}>
          <label className={styles.configLabel}>
            <span>🌐</span> Target Social Platform
          </label>
          <div className={styles.platformPills}>
            {[
              { id: "both", label: "⚡ Both (FB + IG)", icon: "✨" },
              { id: "facebook", label: "📘 Facebook", icon: "📘" },
              { id: "instagram", label: "📸 Instagram", icon: "📸" },
            ].map((p) => (
              <button
                key={p.id}
                type="button"
                disabled={isRunning}
                onClick={() => setPlatform(p.id)}
                className={`${styles.platformPill} ${platform === p.id ? styles.platformPillActive : ""}`}
              >
                <span>{p.icon}</span>
                <span>{p.label}</span>
              </button>
            ))}
          </div>
        </div>

        <div className={styles.configGrid}>
          {/* Group Type */}
          <div className={styles.configGroup}>
            <label className={styles.configLabel}>
              <span>🎯</span> Group Structure Format
            </label>
            <select
              value={groupType}
              onChange={(e) => setGroupType(e.target.value)}
              disabled={isRunning}
              className={styles.configSelect}
            >
              {platform === "both" && (
                <>
                  <option value="all">⚡ All Formats (FB Community + Messenger + IG DM)</option>
                  <option value="community_group">FB Community Group + IG Direct Group</option>
                </>
              )}
              {platform === "facebook" && (
                <>
                  <option value="community_group">📘 Community / Discussion Group (facebook.com/groups/create)</option>
                  <option value="messenger_chat">💬 Messenger Group Chat (facebook.com/messages/new)</option>
                  <option value="all">⚡ Create Both Formats</option>
                </>
              )}
              {platform === "instagram" && (
                <option value="ig_direct_group">📸 Direct Message Group (Max 30 members per batch)</option>
              )}
            </select>
          </div>

          {/* Group Name */}
          <div className={styles.configGroup}>
            <label className={styles.configLabel}>
              <span>✏️</span> Group Name
            </label>
            <input
              type="text"
              value={groupName}
              onChange={(e) => setGroupName(e.target.value)}
              disabled={isRunning}
              placeholder="e.g. My VIP Community 2026"
              className={styles.configInput}
            />
          </div>

          {/* Max Invites */}
          <div className={styles.configGroup}>
            <label className={styles.configLabel}>
              <span>👥</span> Max Friend Invites per Group
            </label>
            <select
              value={maxInvites}
              onChange={(e) => setMaxInvites(parseInt(e.target.value, 10))}
              disabled={isRunning}
              className={styles.configSelect}
            >
              <option value={30}>30 Friends (Instagram DM Safe Limit)</option>
              <option value={50}>50 Friends (Standard Batch)</option>
              <option value={100}>100 Friends (High Velocity)</option>
              <option value={250}>250 Friends (Full Cap)</option>
            </select>
          </div>

          {/* Facebook Privacy */}
          {platform !== "instagram" && (
            <div className={styles.configGroup}>
              <label className={styles.configLabel}>
                <span>🔒</span> Facebook Group Privacy
              </label>
              <select
                value={privacy}
                onChange={(e) => setPrivacy(e.target.value)}
                disabled={isRunning}
                className={styles.configSelect}
              >
                <option value="private">Private (Only members see who's in group)</option>
                <option value="public">Public (Anyone can see members & posts)</option>
              </select>
            </div>
          )}
        </div>

        {/* Initial Welcome Message */}
        <div className={styles.configGroup}>
          <label className={styles.configLabel}>
            <span>💬</span> Introductory Welcome Message (For Messenger & IG DMs)
          </label>
          <input
            type="text"
            value={initialMessage}
            onChange={(e) => setInitialMessage(e.target.value)}
            disabled={isRunning}
            placeholder="e.g. Hey everyone, welcome to our group!"
            className={styles.configInput}
          />
        </div>

        {errorMsg && (
          <div style={{ padding: "0.75rem", borderRadius: "8px", background: "rgba(239, 68, 68, 0.15)", border: "1px solid rgba(239, 68, 68, 0.4)", color: "#f87171", fontSize: "0.85rem" }}>
            ⚠️ {errorMsg}
          </div>
        )}

        {/* Action Button */}
        <div className={styles.actionRow}>
          <button
            type="button"
            onClick={handleStartGroupCreation}
            disabled={isRunning || !groupName.trim()}
            className={styles.btnPrimary}
          >
            <span>{isRunning ? "⏳" : "⚡"}</span>
            <span>{isRunning ? "Creating Group & Inviting Friends..." : "Create Group & Add All Friends"}</span>
          </button>

          {isRunning && (
            <button
              type="button"
              onClick={handleStopTask}
              className={styles.btnDanger}
            >
              <span>🛑</span>
              <span>Stop Group Creation</span>
            </button>
          )}

          <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
            🔒 Executes inside authenticated Chrome session on Port 9222.
          </span>
        </div>
      </div>

      {/* Live Running Progress */}
      {isRunning && (
        <div className={styles.liveTaskCard}>
          <div className={styles.taskHeader}>
            <div className={styles.taskTitle}>
              <span className="pulse-indicator" style={{ display: "inline-block", width: "8px", height: "8px", borderRadius: "50%", background: "#3dd6d0" }} />
              <span>Creating & Inviting Friends to '{groupName}'...</span>
            </div>
            <span className="badge badge-info" style={{ fontSize: "0.8rem" }}>
              {activeTask?.member_count || 0} Friends Invited
            </span>
          </div>

          <div className={styles.progressBarContainer}>
            <div className={styles.progressBarFill} style={{ width: "65%" }} />
          </div>

          <div className={styles.terminalLog}>
            {logs.map((log, idx) => (
              <div key={idx}>{log}</div>
            ))}
          </div>
        </div>
      )}

      {/* Created Groups History */}
      {createdGroups.length > 0 && (
        <div className={styles.controlsCard}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ fontWeight: "700", color: "#ffffff", fontSize: "0.95rem" }}>
              📋 Created Social Groups ({createdGroups.length})
            </div>
            <button
              type="button"
              onClick={fetchCreatedGroups}
              style={{ background: "none", border: "none", color: "#38bdf8", cursor: "pointer", fontSize: "0.8rem" }}
            >
              🔄 Refresh List
            </button>
          </div>

          <div className={styles.createdGroupsList}>
            {createdGroups.slice(0, 6).map((grp) => (
              <div key={grp.id} className={styles.groupItemCard}>
                <div className={styles.groupItemLeft}>
                  <span className={styles.groupIcon}>
                    {grp.platform === "facebook" ? "📘" : "📸"}
                  </span>
                  <div>
                    <div className={styles.groupItemName}>{grp.group_name}</div>
                    <div className={styles.groupItemMeta}>
                      <span>{grp.platform?.toUpperCase()}</span>
                      <span> • </span>
                      <span>{grp.group_type?.replace("_", " ")}</span>
                      <span> • </span>
                      <span style={{ color: "#3dd6d0" }}>{grp.member_count || 0} members</span>
                    </div>
                  </div>
                </div>

                {grp.group_url && (
                  <a
                    href={grp.group_url}
                    target="_blank"
                    rel="noreferrer"
                    className={styles.groupLink}
                  >
                    <span>Open Group</span>
                    <span>↗</span>
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
