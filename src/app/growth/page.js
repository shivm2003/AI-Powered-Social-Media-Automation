"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import FacebookAcceptDeck from "@/components/growth/FacebookAcceptDeck";
import InstagramUnfollowDeck from "@/components/growth/InstagramUnfollowDeck";
import FriendsGroupDeck from "@/components/growth/FriendsGroupDeck";

const PRESET_LOCATIONS = [
  "New Delhi",
  "Mumbai",
  "Bangalore",
  "New York",
  "London",
  "Dubai",
  "Singapore",
  "Toronto",
];

export default function GrowthPage() {
  const [platform, setPlatform] = useState("both"); // 'facebook', 'instagram', 'both'
  const [strategyMode, setStrategyMode] = useState("suggestions"); // 'suggestions', 'random', 'location'
  const [location, setLocation] = useState("New Delhi");
  const [targetCount, setTargetCount] = useState(10);
  const [safetyDelay, setSafetyDelay] = useState(15);
  const [loading, setLoading] = useState(false);
  const [stopping, setStopping] = useState(false);

  const [activeCampaign, setActiveCampaign] = useState(null);
  const [campaigns, setCampaigns] = useState([]);
  const [activeTab, setActiveTab] = useState("accept"); // 'accept', 'launcher', 'history'

  const pollIntervalRef = useRef(null);

  // Fetch campaigns
  const fetchCampaigns = useCallback(async () => {
    try {
      const res = await fetch("/api/growth");
      const data = await res.json();
      if (data.success && Array.isArray(data.campaigns)) {
        setCampaigns(data.campaigns);
        // Look for any running campaign
        const running = data.campaigns.find((c) => c.status === "running");
        if (running) {
          setActiveCampaign(running);
        } else if (activeCampaign && activeCampaign.status === "running") {
          const updated = data.campaigns.find((c) => c.id === activeCampaign.id);
          setActiveCampaign(updated || null);
        }
      }
    } catch (err) {
      console.error("Error fetching growth campaigns:", err);
    }
  }, [activeCampaign]);

  useEffect(() => {
    fetchCampaigns();
  }, [fetchCampaigns]);

  // Poll when active campaign is running
  useEffect(() => {
    if (activeCampaign && activeCampaign.status === "running") {
      pollIntervalRef.current = setInterval(fetchCampaigns, 3000);
    } else {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    }
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [activeCampaign, fetchCampaigns]);

  const handleStartCampaign = async () => {
    if (strategyMode === "location" && !location.trim()) {
      alert("Please specify a target location.");
      return;
    }

    const effectiveLocation =
      strategyMode === "suggestions"
        ? "Algorithmic Suggestions"
        : strategyMode === "random"
        ? "Random Discovery"
        : location.trim();

    setLoading(true);
    try {
      const res = await fetch("/api/growth", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          platform,
          mode: strategyMode,
          location: effectiveLocation,
          targetCount: parseInt(targetCount, 10),
          safetyDelay: parseInt(safetyDelay, 10),
        }),
      });

      const data = await res.json();
      if (res.ok && data.success) {
        setActiveCampaign({
          id: data.campaignId,
          platform,
          mode: strategyMode,
          location: effectiveLocation,
          target_count: targetCount,
          fb_sent_count: 0,
          ig_sent_count: 0,
          status: "running",
          logs: JSON.stringify(["Campaign initiated. Connecting to browser on port 9222..."]),
        });
        fetchCampaigns();
      } else {
        alert(data.error || "Failed to initiate growth campaign.");
      }
    } catch (err) {
      alert(`Network error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleStopCampaign = async (id) => {
    if (!confirm("Are you sure you want to stop this outreach campaign?")) return;
    setStopping(true);
    try {
      const res = await fetch(`/api/growth?id=${id}`, {
        method: "DELETE",
      });
      const data = await res.json();
      if (res.ok && data.success) {
        fetchCampaigns();
        if (activeCampaign && activeCampaign.id === id) {
          setActiveCampaign((prev) => (prev ? { ...prev, status: "stopped" } : null));
        }
      } else {
        alert(data.error || "Could not stop campaign.");
      }
    } catch (err) {
      alert(`Error: ${err.message}`);
    } finally {
      setStopping(false);
    }
  };

  // Parse logs array safely
  const parsedLogs = (() => {
    if (!activeCampaign || !activeCampaign.logs) return [];
    if (Array.isArray(activeCampaign.logs)) return activeCampaign.logs;
    try {
      const p = JSON.parse(activeCampaign.logs);
      return Array.isArray(p) ? p : [];
    } catch {
      return [activeCampaign.logs];
    }
  })();

  const totalTarget =
    activeCampaign
      ? activeCampaign.platform === "both"
        ? activeCampaign.target_count * 2
        : activeCampaign.target_count
      : (platform === "both" ? targetCount * 2 : targetCount);

  const totalSent = activeCampaign
    ? (activeCampaign.fb_sent_count || 0) + (activeCampaign.ig_sent_count || 0)
    : 0;

  const progressPercent = totalTarget > 0 ? Math.min(100, Math.round((totalSent / totalTarget) * 100)) : 0;

  return (
    <div className="page-container" style={{ padding: "var(--space-6)" }}>
      {/* Header */}
      <div style={{ marginBottom: "var(--space-8)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", marginBottom: "var(--space-2)" }}>
          <span style={{ fontSize: "2rem" }}>👥</span>
          <h1 style={{ fontSize: "1.875rem", fontWeight: "700", color: "var(--text-primary)", margin: 0 }}>
            Social Outreach & Growth Engine
          </h1>
          <span className="badge badge-primary" style={{ padding: "0.25rem 0.75rem", fontSize: "0.75rem" }}>
            Dual-Platform Active
          </span>
        </div>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.95rem", maxWidth: "800px", margin: 0 }}>
          Automatically send location-targeted <b>Facebook Friend Requests</b> and <b>Instagram Follow Requests</b> simultaneously
          using your connected Chrome profile with human-paced safety delays.
        </p>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: "var(--space-2)", marginBottom: "var(--space-6)", flexWrap: "wrap" }}>
        <button
          id="btn-tab-accept"
          onClick={() => setActiveTab("accept")}
          className={`btn ${activeTab === "accept" ? "btn-primary" : "btn-secondary"}`}
          style={{ padding: "0.6rem 1.25rem", display: "flex", alignItems: "center", gap: "0.5rem" }}
        >
          <span>🤝 Accept Friend Requests</span>
          <span style={{ background: "rgba(56, 189, 248, 0.2)", color: "#38bdf8", padding: "0.15rem 0.5rem", borderRadius: "9999px", fontSize: "0.75rem", fontWeight: 700 }}>
            Batch & Like
          </span>
        </button>
        <button
          id="btn-tab-unfollow"
          onClick={() => setActiveTab("unfollow")}
          className={`btn ${activeTab === "unfollow" ? "btn-primary" : "btn-secondary"}`}
          style={{ padding: "0.6rem 1.25rem", display: "flex", alignItems: "center", gap: "0.5rem" }}
        >
          <span>📉 Instagram Unfollow</span>
          <span style={{ background: "rgba(244, 63, 94, 0.2)", color: "#f43f5e", padding: "0.15rem 0.5rem", borderRadius: "9999px", fontSize: "0.75rem", fontWeight: 700 }}>
            Prune
          </span>
        </button>
        <button
          id="btn-tab-groups"
          onClick={() => setActiveTab("groups")}
          className={`btn ${activeTab === "groups" ? "btn-primary" : "btn-secondary"}`}
          style={{ padding: "0.6rem 1.25rem", display: "flex", alignItems: "center", gap: "0.5rem" }}
        >
          <span>👨‍👩‍👧‍👦 Group All Friends</span>
          <span style={{ background: "rgba(124, 92, 252, 0.25)", color: "#a78bfa", padding: "0.15rem 0.5rem", borderRadius: "9999px", fontSize: "0.75rem", fontWeight: 700 }}>
            FB & IG
          </span>
        </button>
        <button
          id="btn-tab-launcher"
          onClick={() => setActiveTab("launcher")}
          className={`btn ${activeTab === "launcher" ? "btn-primary" : "btn-secondary"}`}
          style={{ padding: "0.6rem 1.25rem" }}
        >
          🚀 Launch Outreach
        </button>
        <button
          id="btn-tab-history"
          onClick={() => setActiveTab("history")}
          className={`btn ${activeTab === "history" ? "btn-primary" : "btn-secondary"}`}
          style={{ padding: "0.6rem 1.25rem" }}
        >
          📋 Campaign History ({campaigns.length})
        </button>
      </div>

      {activeTab === "accept" && (
        <FacebookAcceptDeck />
      )}

      {activeTab === "unfollow" && (
        <InstagramUnfollowDeck />
      )}

      {activeTab === "groups" && (
        <FriendsGroupDeck />
      )}

      {activeTab === "launcher" ? (
        <div style={{ display: "grid", gridTemplateColumns: activeCampaign ? "1.1fr 0.9fr" : "1fr", gap: "var(--space-6)" }}>
          {/* Setup Card */}
          <div className="card" style={{ padding: "var(--space-6)", borderRadius: "var(--radius-lg)" }}>
            <h2 style={{ fontSize: "1.25rem", fontWeight: "600", color: "var(--text-primary)", marginBottom: "var(--space-5)" }}>
              ⚙️ Outreach Configuration
            </h2>

            {/* Platform Selection */}
            <div style={{ marginBottom: "var(--space-6)" }}>
              <label style={{ display: "block", fontSize: "0.875rem", fontWeight: "600", color: "var(--text-secondary)", marginBottom: "var(--space-3)" }}>
                SELECT OUTREACH PLATFORM
              </label>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "var(--space-3)" }}>
                {[
                  { id: "both", name: "⚡ Both Simultaneously", desc: "Facebook + Instagram" },
                  { id: "facebook", name: "📘 Facebook Friends", desc: "Friend Requests Only" },
                  { id: "instagram", name: "📸 Instagram Follows", desc: "Follow Requests Only" },
                ].map((p) => (
                  <div
                    key={p.id}
                    id={`platform-${p.id}`}
                    onClick={() => setPlatform(p.id)}
                    style={{
                      padding: "var(--space-4)",
                      borderRadius: "var(--radius-md)",
                      border: platform === p.id ? "2px solid var(--accent-primary)" : "1px solid var(--border-color)",
                      background: platform === p.id ? "rgba(124, 92, 252, 0.12)" : "var(--bg-secondary)",
                      cursor: "pointer",
                      transition: "all 0.2s ease",
                    }}
                  >
                    <div style={{ fontWeight: "600", color: platform === p.id ? "var(--accent-primary)" : "var(--text-primary)", fontSize: "0.95rem" }}>
                      {p.name}
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "4px" }}>
                      {p.desc}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Discovery & Outreach Strategy */}
            <div style={{ marginBottom: "var(--space-6)" }}>
              <label style={{ display: "block", fontSize: "0.875rem", fontWeight: "600", color: "var(--text-secondary)", marginBottom: "var(--space-3)" }}>
                DISCOVERY STRATEGY
              </label>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "var(--space-3)" }}>
                {[
                  {
                    id: "suggestions",
                    icon: "🌟",
                    name: "Algorithmic Suggestions",
                    badge: "Recommended",
                    desc: "Facebook People You May Know & Instagram Suggested for You (High acceptance)",
                  },
                  {
                    id: "random",
                    icon: "🎲",
                    name: "Random Discovery",
                    badge: "Explore Feed",
                    desc: "Organic explore posts & randomized candidate shuffling for wide discovery",
                  },
                  {
                    id: "location",
                    icon: "📍",
                    name: "Location Target",
                    badge: "Geo Specific",
                    desc: "Filter friends and people by specific city or geographic location",
                  },
                ].map((m) => (
                  <div
                    key={m.id}
                    id={`strategy-${m.id}`}
                    onClick={() => setStrategyMode(m.id)}
                    style={{
                      padding: "var(--space-4)",
                      borderRadius: "var(--radius-md)",
                      border: strategyMode === m.id ? "2px solid #38bdf8" : "1px solid var(--border-color)",
                      background: strategyMode === m.id ? "rgba(56, 189, 248, 0.12)" : "var(--bg-secondary)",
                      cursor: "pointer",
                      transition: "all 0.2s ease",
                      position: "relative",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                      <span style={{ fontSize: "1.1rem" }}>{m.icon}</span>
                      <span
                        style={{
                          fontSize: "0.68rem",
                          fontWeight: "700",
                          padding: "0.15rem 0.45rem",
                          borderRadius: "9999px",
                          background: strategyMode === m.id ? "rgba(56, 189, 248, 0.25)" : "var(--bg-tertiary)",
                          color: strategyMode === m.id ? "#38bdf8" : "var(--text-muted)",
                        }}
                      >
                        {m.badge}
                      </span>
                    </div>
                    <div style={{ fontWeight: "600", color: strategyMode === m.id ? "#38bdf8" : "var(--text-primary)", fontSize: "0.92rem" }}>
                      {m.name}
                    </div>
                    <div style={{ fontSize: "0.74rem", color: "var(--text-muted)", marginTop: "4px", lineHeight: "1.3" }}>
                      {m.desc}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Location Targeting (Conditionally rendered for Location mode) */}
            {strategyMode === "location" ? (
              <div style={{ marginBottom: "var(--space-6)" }}>
                <label htmlFor="input-target-location" style={{ display: "block", fontSize: "0.875rem", fontWeight: "600", color: "var(--text-secondary)", marginBottom: "var(--space-2)" }}>
                  TARGET GEOGRAPHIC LOCATION
                </label>
                <input
                  id="input-target-location"
                  type="text"
                  className="input"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="e.g. New Delhi, Mumbai, New York, London..."
                  style={{ width: "100%", padding: "0.75rem 1rem", fontSize: "1rem", borderRadius: "var(--radius-md)" }}
                />

                {/* Preset Chips */}
                <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)", marginTop: "var(--space-3)" }}>
                  {PRESET_LOCATIONS.map((loc) => (
                    <button
                      key={loc}
                      type="button"
                      onClick={() => setLocation(loc)}
                      style={{
                        padding: "0.25rem 0.65rem",
                        fontSize: "0.75rem",
                        borderRadius: "9999px",
                        background: location === loc ? "var(--accent-primary)" : "var(--bg-tertiary)",
                        color: location === loc ? "#fff" : "var(--text-secondary)",
                        border: "none",
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}
                    >
                      📍 {loc}
                    </button>
                  ))}
                </div>
              </div>
            ) : strategyMode === "suggestions" ? (
              <div
                style={{
                  marginBottom: "var(--space-6)",
                  padding: "var(--space-3) var(--space-4)",
                  borderRadius: "var(--radius-md)",
                  background: "rgba(56, 189, 248, 0.08)",
                  border: "1px solid rgba(56, 189, 248, 0.25)",
                  display: "flex",
                  alignItems: "center",
                  gap: "var(--space-3)",
                }}
              >
                <span style={{ fontSize: "1.5rem" }}>🌟</span>
                <div style={{ fontSize: "0.82rem", color: "var(--text-secondary)", lineHeight: "1.4" }}>
                  <strong style={{ color: "#38bdf8" }}>Algorithmic Suggestions Feed:</strong> The bot will harvest friend requests directly from Facebook's <b>People You May Know</b> (<code>/friends/suggestions</code>) and Instagram's <b>Suggested for You</b> (<code>/explore/people/</code>). No city filter needed.
                </div>
              </div>
            ) : (
              <div
                style={{
                  marginBottom: "var(--space-6)",
                  padding: "var(--space-3) var(--space-4)",
                  borderRadius: "var(--radius-md)",
                  background: "rgba(168, 85, 247, 0.08)",
                  border: "1px solid rgba(168, 85, 247, 0.25)",
                  display: "flex",
                  alignItems: "center",
                  gap: "var(--space-3)",
                }}
              >
                <span style={{ fontSize: "1.5rem" }}>🎲</span>
                <div style={{ fontSize: "0.82rem", color: "var(--text-secondary)", lineHeight: "1.4" }}>
                  <strong style={{ color: "#c084fc" }}>Random Discovery Mode:</strong> Randomizes friend candidate shuffling on Facebook and browses active Instagram explore feeds to follow creators organically across varied niches.
                </div>
              </div>
            )}

            {/* Target Quantity */}
            <div style={{ marginBottom: "var(--space-6)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--space-2)" }}>
                <label htmlFor="range-target-count" style={{ fontSize: "0.875rem", fontWeight: "600", color: "var(--text-secondary)" }}>
                  REQUESTS PER PLATFORM (MAX 1,000)
                </label>
                <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                  <input
                    type="number"
                    min="1"
                    max="1000"
                    value={targetCount}
                    onChange={(e) => setTargetCount(Math.min(1000, Math.max(1, parseInt(e.target.value, 10) || 1)))}
                    style={{
                      width: "80px",
                      padding: "4px 8px",
                      borderRadius: "var(--radius-sm)",
                      border: "1px solid var(--border-color)",
                      background: "var(--bg-secondary)",
                      color: "var(--text-primary)",
                      fontWeight: "700",
                      textAlign: "center",
                      fontSize: "0.875rem",
                    }}
                  />
                  <span className="badge badge-info" style={{ fontSize: "0.85rem", fontWeight: "700" }}>
                    {targetCount} {platform === "both" ? `(${targetCount * 2} Total)` : "Reqs"}
                  </span>
                </div>
              </div>
              <input
                id="range-target-count"
                type="range"
                min="1"
                max="1000"
                value={targetCount}
                onChange={(e) => setTargetCount(parseInt(e.target.value, 10))}
                style={{ width: "100%", accentColor: "var(--accent-primary)", cursor: "pointer" }}
              />
              <div style={{ display: "flex", gap: "6px", marginTop: "8px", flexWrap: "wrap" }}>
                {[10, 50, 100, 250, 500, 1000].map((num) => (
                  <button
                    key={num}
                    type="button"
                    onClick={() => setTargetCount(num)}
                    style={{
                      padding: "3px 10px",
                      borderRadius: "var(--radius-full)",
                      fontSize: "0.75rem",
                      fontWeight: targetCount === num ? "700" : "500",
                      background: targetCount === num ? "var(--accent-primary)" : "var(--bg-secondary)",
                      color: targetCount === num ? "#fff" : "var(--text-secondary)",
                      border: "1px solid var(--border-color)",
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                    }}
                  >
                    {num === 1000 ? "🚀 1000 (Max)" : num === 250 ? "250 (Milestone)" : `${num}`}
                  </button>
                ))}
              </div>
              {targetCount > 250 && (
                <div style={{
                  marginTop: "8px",
                  padding: "6px 10px",
                  borderRadius: "var(--radius-sm)",
                  background: "rgba(255, 179, 71, 0.12)",
                  border: "1px solid rgba(255, 179, 71, 0.3)",
                  color: "#FFB347",
                  fontSize: "0.75rem",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px"
                }}>
                  <span>☕</span>
                  <span><strong>Safety Notice:</strong> Target exceeds 250. The engine will automatically pause for <strong>2 minutes</strong> after every 250 requests to preserve account safety.</span>
                </div>
              )}
            </div>

            {/* Safety Delay */}
            <div style={{ marginBottom: "var(--space-8)" }}>
              <label style={{ display: "block", fontSize: "0.875rem", fontWeight: "600", color: "var(--text-secondary)", marginBottom: "var(--space-2)" }}>
                HUMAN SAFETY COOLDOWN PACING
              </label>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "var(--space-3)" }}>
                {[
                  { value: 18, label: "🛡️ Conservative", pace: "15-25s delay (Safest)" },
                  { value: 12, label: "⚖️ Balanced", pace: "10-16s delay (Optimal)" },
                  { value: 8, label: "⚡ Accelerated", pace: "7-11s delay (Fast)" },
                ].map((s) => (
                  <div
                    key={s.value}
                    onClick={() => setSafetyDelay(s.value)}
                    style={{
                      padding: "var(--space-3)",
                      borderRadius: "var(--radius-md)",
                      border: safetyDelay === s.value ? "2px solid var(--accent-secondary)" : "1px solid var(--border-color)",
                      background: safetyDelay === s.value ? "rgba(61, 214, 208, 0.1)" : "var(--bg-secondary)",
                      cursor: "pointer",
                      fontSize: "0.85rem",
                    }}
                  >
                    <div style={{ fontWeight: "600", color: "var(--text-primary)" }}>{s.label}</div>
                    <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>{s.pace}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Launch Button */}
            <button
              id="btn-launch-growth"
              onClick={handleStartCampaign}
              disabled={loading || (activeCampaign && activeCampaign.status === "running")}
              className="btn btn-primary"
              style={{
                width: "100%",
                padding: "0.875rem",
                fontSize: "1.05rem",
                fontWeight: "700",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "var(--space-3)",
                background: "linear-gradient(135deg, #7C5CFC 0%, #3DD6D0 100%)",
                boxShadow: "0 8px 24px rgba(124, 92, 252, 0.35)",
              }}
            >
              {loading ? "⏳ Initializing Engine..." : activeCampaign?.status === "running" ? "⚙️ Campaign In Progress..." : "🚀 Launch Outreach Campaign"}
            </button>
          </div>

          {/* Live Progress Card (if active) */}
          {activeCampaign && (
            <div className="card" style={{ padding: "var(--space-6)", borderRadius: "var(--radius-lg)", display: "flex", flexDirection: "column" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--space-4)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                  <span className={`status-indicator ${activeCampaign.status === "running" ? "status-online" : "status-offline"}`} />
                  <h3 style={{ fontSize: "1.15rem", fontWeight: "600", margin: 0, color: "var(--text-primary)" }}>
                    Live Outreach Monitor
                  </h3>
                </div>
                <span className={`badge ${activeCampaign.status === "running" ? "badge-success" : activeCampaign.status === "completed" ? "badge-primary" : "badge-warning"}`}>
                  {activeCampaign.status?.toUpperCase()}
                </span>
              </div>

              {/* Progress Bar & Counters */}
              <div style={{ marginBottom: "var(--space-5)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: "var(--space-2)" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <span>Target: <b>{activeCampaign.location}</b></span>
                    {activeCampaign.mode && (
                      <span
                        style={{
                          fontSize: "0.72rem",
                          padding: "2px 8px",
                          borderRadius: "9999px",
                          background:
                            activeCampaign.mode === "suggestions"
                              ? "rgba(56, 189, 248, 0.2)"
                              : activeCampaign.mode === "random"
                              ? "rgba(168, 85, 247, 0.2)"
                              : "rgba(34, 197, 94, 0.2)",
                          color:
                            activeCampaign.mode === "suggestions"
                              ? "#38bdf8"
                              : activeCampaign.mode === "random"
                              ? "#c084fc"
                              : "#4ade80",
                          fontWeight: "600",
                        }}
                      >
                        {activeCampaign.mode === "suggestions"
                          ? "🌟 Suggestions"
                          : activeCampaign.mode === "random"
                          ? "🎲 Random"
                          : "📍 Location"}
                      </span>
                    )}
                  </div>
                  <span><b>{totalSent} / {totalTarget}</b> completed ({progressPercent}%)</span>
                </div>
                <div style={{ width: "100%", height: "10px", background: "var(--bg-tertiary)", borderRadius: "9999px", overflow: "hidden" }}>
                  <div
                    style={{
                      width: `${progressPercent}%`,
                      height: "100%",
                      background: "linear-gradient(90deg, #7C5CFC 0%, #3DD6D0 100%)",
                      borderRadius: "9999px",
                      transition: "width 0.4s ease",
                    }}
                  />
                </div>
              </div>

              {/* Dual Counter Badges */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3)", marginBottom: "var(--space-5)" }}>
                <div style={{ padding: "var(--space-3)", background: "var(--bg-secondary)", borderRadius: "var(--radius-md)", textAlign: "center" }}>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>📘 Facebook Friends</div>
                  <div style={{ fontSize: "1.25rem", fontWeight: "700", color: "#1877F2" }}>
                    {activeCampaign.fb_sent_count || 0}
                  </div>
                </div>
                <div style={{ padding: "var(--space-3)", background: "var(--bg-secondary)", borderRadius: "var(--radius-md)", textAlign: "center" }}>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>📸 Instagram Follows</div>
                  <div style={{ fontSize: "1.25rem", fontWeight: "700", color: "#E1306C" }}>
                    {activeCampaign.ig_sent_count || 0}
                  </div>
                </div>
              </div>

              {/* Terminal Logs Window */}
              <div style={{ flex: 1, minHeight: "180px", maxHeight: "250px", background: "#0D1117", borderRadius: "var(--radius-md)", padding: "var(--space-3)", overflowY: "auto", fontFamily: "monospace", fontSize: "0.75rem", color: "#58A6FF" }}>
                <div style={{ color: "#8B949E", marginBottom: "4px" }}>{"// Live Automation Feed:"}</div>
                {parsedLogs.length === 0 ? (
                  <div style={{ color: "#8B949E" }}>Waiting for initial events...</div>
                ) : (
                  parsedLogs.map((log, idx) => (
                    <div key={idx} style={{ color: log.includes("Error") ? "#FF7B72" : log.includes("Sent") || log.includes("Followed") ? "#7EE787" : "#C9D1D9", marginBottom: "3px" }}>
                      {log}
                    </div>
                  ))
                )}
              </div>

              {/* Action Buttons */}
              {activeCampaign.status === "running" && (
                <button
                  id="btn-stop-campaign"
                  onClick={() => handleStopCampaign(activeCampaign.id)}
                  disabled={stopping}
                  className="btn btn-danger"
                  style={{ width: "100%", marginTop: "var(--space-4)", padding: "0.6rem" }}
                >
                  {stopping ? "Stopping..." : "🛑 Emergency Stop"}
                </button>
              )}
            </div>
          )}
        </div>
      ) : (
        /* History Tab */
        <div className="card" style={{ padding: "var(--space-6)", borderRadius: "var(--radius-lg)" }}>
          <h2 style={{ fontSize: "1.25rem", fontWeight: "600", color: "var(--text-primary)", marginBottom: "var(--space-4)" }}>
            📋 Past Outreach Campaigns
          </h2>
          {campaigns.length === 0 ? (
            <div style={{ textAlign: "center", padding: "var(--space-8)", color: "var(--text-muted)" }}>
              No outreach campaigns executed yet. Launch one above!
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.875rem" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border-color)", color: "var(--text-muted)" }}>
                    <th style={{ padding: "var(--space-3)" }}>Platform</th>
                    <th style={{ padding: "var(--space-3)" }}>Location</th>
                    <th style={{ padding: "var(--space-3)" }}>Sent / Target</th>
                    <th style={{ padding: "var(--space-3)" }}>Status</th>
                    <th style={{ padding: "var(--space-3)" }}>Created</th>
                    <th style={{ padding: "var(--space-3)" }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {campaigns.map((c) => (
                    <tr key={c.id} style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                      <td style={{ padding: "var(--space-3)", fontWeight: "600" }}>
                        {c.platform === "both" ? "⚡ Dual (FB + IG)" : c.platform === "facebook" ? "📘 Facebook" : "📸 Instagram"}
                      </td>
                      <td style={{ padding: "var(--space-3)" }}>
                        {c.mode === "suggestions" ? (
                          <span style={{ color: "#38bdf8", fontWeight: "600", fontSize: "0.85rem" }}>🌟 Suggestions</span>
                        ) : c.mode === "random" ? (
                          <span style={{ color: "#c084fc", fontWeight: "600", fontSize: "0.85rem" }}>🎲 Random</span>
                        ) : (
                          <span>📍 {c.location}</span>
                        )}
                      </td>
                      <td style={{ padding: "var(--space-3)" }}>
                        <b>{(c.fb_sent_count || 0) + (c.ig_sent_count || 0)}</b> / {c.platform === "both" ? c.target_count * 2 : c.target_count}
                        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginLeft: "6px" }}>
                          (FB: {c.fb_sent_count || 0}, IG: {c.ig_sent_count || 0})
                        </span>
                      </td>
                      <td style={{ padding: "var(--space-3)" }}>
                        <span className={`badge ${c.status === "completed" ? "badge-success" : c.status === "running" ? "badge-info" : "badge-warning"}`}>
                          {c.status}
                        </span>
                      </td>
                      <td style={{ padding: "var(--space-3)", color: "var(--text-muted)", fontSize: "0.8rem" }}>
                        {new Date(c.created_at).toLocaleString()}
                      </td>
                      <td style={{ padding: "var(--space-3)" }}>
                        <button
                          onClick={() => {
                            setActiveCampaign(c);
                            setActiveTab("launcher");
                          }}
                          className="btn btn-secondary"
                          style={{ padding: "0.25rem 0.6rem", fontSize: "0.75rem" }}
                        >
                          Inspect
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
