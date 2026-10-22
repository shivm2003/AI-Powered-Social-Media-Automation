"use client";

import { useState, useEffect } from "react";
import { CAMPAIGN_STATUSES, CONTENT_TYPES, LLM_PROVIDERS, PLATFORMS } from "@/lib/constants";

function safeArray(val) {
  if (Array.isArray(val)) return val;
  if (!val) return [];
  try {
    const parsed = JSON.parse(val);
    return Array.isArray(parsed) ? parsed : [parsed];
  } catch {
    return typeof val === "string" ? [val] : [];
  }
}

function getMediaUrl(mediaPath) {
  if (!mediaPath) return null;
  const filename = mediaPath.split(/[/\\]/).pop();
  return `/api/media?file=${encodeURIComponent(filename)}`;
}

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [previewMedia, setPreviewMedia] = useState(null);

  // Platform selection modal state
  const [selectedCampaignForPost, setSelectedCampaignForPost] = useState(null);
  const [targetPlatform, setTargetPlatform] = useState("facebook");
  const [postingStatus, setPostingStatus] = useState("idle"); // "idle" | "posting" | "success" | "error"
  const [postingMessage, setPostingMessage] = useState("");

  async function fetchCampaigns() {
    try {
      const res = await fetch("/api/campaigns");
      if (res.ok) {
        const data = await res.json();
        setCampaigns(data);
      }
    } catch (error) {
      console.error("Failed to fetch campaigns:", error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchCampaigns();
  }, []);

  function openPlatformModal(campaign) {
    setSelectedCampaignForPost(campaign);
    setTargetPlatform("facebook");
    setPostingStatus("idle");
    setPostingMessage("");
  }

  async function handlePublishToSelectedPlatform() {
    if (!selectedCampaignForPost) return;
    setPostingStatus("posting");
    setPostingMessage(
      targetPlatform === "facebook"
        ? "Opening Chrome and verifying Facebook login... If login is required, please check your Telegram bot to enter your password!"
        : `Connecting to browser and preparing to publish to ${targetPlatform}...`
    );

    try {
      const res = await fetch(`/api/campaigns/${selectedCampaignForPost.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "approve", platform: targetPlatform }),
      });
      const data = await res.json();
      if (res.ok) {
        setPostingStatus("success");
        setPostingMessage(data.message || `🎉 Successfully published to ${targetPlatform}!`);
        fetchCampaigns();
      } else {
        setPostingStatus("error");
        setPostingMessage(data.error || "Failed to publish post.");
      }
    } catch (err) {
      setPostingStatus("error");
      setPostingMessage(err.message || "An unexpected error occurred.");
    }
  }

  async function handleDelete(id) {
    if (!confirm("Are you sure you want to delete this campaign?")) return;
    try {
      const res = await fetch(`/api/campaigns/${id}`, { method: "DELETE" });
      if (res.ok) {
        fetchCampaigns();
      }
    } catch (err) {
      alert("Error: " + err.message);
    }
  }

  const filteredCampaigns = filter === "all"
    ? campaigns
    : campaigns.filter((c) => c.status === filter);

  const statusCounts = {};
  campaigns.forEach((c) => {
    statusCounts[c.status] = (statusCounts[c.status] || 0) + 1;
  });

  if (loading) {
    return (
      <div className="loading-overlay">
        <div className="spinner" />
        <span>Loading campaigns...</span>
      </div>
    );
  }

  return (
    <div className="animate-fadeIn">
      <div className="page-header">
        <div>
          <h1 className="page-title">Campaigns</h1>
          <p className="page-subtitle">Track all your generated content, images, and publishing status</p>
        </div>
        <a href="/generate" className="btn btn-primary">
          ✨ New Campaign
        </a>
      </div>

      {/* Filter Tabs */}
      <div
        style={{
          display: "flex",
          gap: "var(--space-2)",
          marginBottom: "var(--space-6)",
          overflowX: "auto",
          paddingBottom: "var(--space-2)",
        }}
      >
        <button
          className={`btn btn-sm ${filter === "all" ? "btn-primary" : "btn-secondary"}`}
          onClick={() => setFilter("all")}
        >
          All ({campaigns.length})
        </button>
        {Object.entries(CAMPAIGN_STATUSES).map(([key, status]) => (
          <button
            key={key}
            className={`btn btn-sm ${filter === key ? "btn-primary" : "btn-secondary"}`}
            onClick={() => setFilter(key)}
          >
            {status.icon} {status.label} ({statusCounts[key] || 0})
          </button>
        ))}
      </div>

      {/* Campaigns List */}
      {filteredCampaigns.length > 0 ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
          {filteredCampaigns.map((campaign) => {
            const statusConfig = CAMPAIGN_STATUSES[campaign.status] || CAMPAIGN_STATUSES.draft;
            const platforms = safeArray(campaign.platforms);
            const mediaPaths = safeArray(campaign.media_paths);
            const primaryMediaUrl = mediaPaths.length > 0 ? getMediaUrl(mediaPaths[0]) : null;

            const isVideo = campaign.content_type === "video" || (primaryMediaUrl && (primaryMediaUrl.endsWith(".mp4") || primaryMediaUrl.endsWith(".mov") || primaryMediaUrl.endsWith(".webm")));

            return (
              <div className="card" key={campaign.id} style={{ overflow: "hidden" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "var(--space-4)" }}>
                  <div style={{ display: "flex", gap: "var(--space-4)", flex: 1, minWidth: 280 }}>
                    {/* Media Thumbnail or Fallback Icon */}
                    {primaryMediaUrl ? (
                      <div
                        onClick={() => setPreviewMedia({ url: primaryMediaUrl, isVideo, title: campaign.product_name })}
                        style={{
                          width: 130,
                          height: 130,
                          borderRadius: "var(--radius-md)",
                          overflow: "hidden",
                          position: "relative",
                          cursor: "pointer",
                          flexShrink: 0,
                          border: "1px solid var(--border)",
                          boxShadow: "0 4px 16px rgba(0,0,0,0.3)",
                          background: "#0d0f17",
                        }}
                        title={isVideo ? "Click to play full video reel" : "Click to view full image in high-res"}
                      >
                        {isVideo ? (
                          <video
                            src={primaryMediaUrl}
                            muted
                            playsInline
                            style={{ width: "100%", height: "100%", objectFit: "cover" }}
                          />
                        ) : (
                          <img
                            src={primaryMediaUrl}
                            alt={campaign.product_name || "Generated Media"}
                            style={{ width: "100%", height: "100%", objectFit: "cover" }}
                          />
                        )}
                        <div
                          style={{
                            position: "absolute",
                            bottom: 4,
                            right: 4,
                            background: "rgba(0,0,0,0.75)",
                            color: "#fff",
                            fontSize: "10px",
                            padding: "2px 6px",
                            borderRadius: "4px",
                            backdropFilter: "blur(4px)",
                          }}
                        >
                          {isVideo ? "▶️ Play Reel" : "🔍 View Full"}
                        </div>
                      </div>
                    ) : (
                      <div
                        style={{
                          width: 54,
                          height: 54,
                          borderRadius: "var(--radius-md)",
                          background: "var(--accent-primary-muted)",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          fontSize: "1.6rem",
                          flexShrink: 0,
                        }}
                      >
                        {CONTENT_TYPES[campaign.content_type]?.icon || "📝"}
                      </div>
                    )}

                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", marginBottom: "var(--space-1)", flexWrap: "wrap" }}>
                        <h4 style={{ margin: 0, fontSize: "var(--font-md)" }}>{campaign.product_name || "Untitled Campaign"}</h4>
                        <span className={`tag tag-${statusConfig.color}`}>
                          {statusConfig.icon} {statusConfig.label}
                        </span>
                      </div>
                      <div style={{ display: "flex", gap: "var(--space-3)", fontSize: "var(--font-xs)", color: "var(--text-secondary)", marginTop: "var(--space-1)" }}>
                        <span>{CONTENT_TYPES[campaign.content_type]?.name || campaign.content_type}</span>
                        <span>•</span>
                        <span>{LLM_PROVIDERS[campaign.llm_provider]?.icon} {LLM_PROVIDERS[campaign.llm_provider]?.name || campaign.llm_provider}</span>
                        <span>•</span>
                        <span style={{ textTransform: "capitalize" }}>{campaign.language}</span>
                      </div>

                      {/* Target Platforms */}
                      {platforms.length > 0 && (
                        <div style={{ display: "flex", gap: "var(--space-2)", marginTop: "var(--space-2)", flexWrap: "wrap" }}>
                          {platforms.map((p) => (
                            <span key={p} className="tag tag-default" style={{ fontSize: "11px" }}>
                              {PLATFORMS[p]?.icon} {PLATFORMS[p]?.name || p}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Generated Caption Preview */}
                      {campaign.generated_caption && (
                        <div
                          style={{
                            marginTop: "var(--space-3)",
                            fontSize: "var(--font-sm)",
                            color: "var(--text-primary)",
                            background: "var(--bg-tertiary)",
                            padding: "var(--space-3)",
                            borderRadius: "var(--radius-sm)",
                            borderLeft: "3px solid var(--accent-primary)",
                            whiteSpace: "pre-line",
                            lineHeight: 1.5,
                          }}
                        >
                          {campaign.generated_caption}
                        </div>
                      )}

                      {/* Hashtags */}
                      {campaign.generated_hashtags && (
                        <div style={{ display: "flex", gap: "var(--space-1)", marginTop: "var(--space-2)", flexWrap: "wrap" }}>
                          {safeArray(campaign.generated_hashtags).map((tag, idx) => (
                            <span
                              key={idx}
                              style={{
                                fontSize: "11px",
                                color: "var(--primary-light)",
                                background: "rgba(124, 92, 252, 0.12)",
                                padding: "2px 8px",
                                borderRadius: "4px",
                                fontWeight: 500,
                              }}
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Revision notes if any */}
                      {campaign.revision_notes && (
                        <p
                          style={{
                            marginTop: "var(--space-2)",
                            fontSize: "var(--font-xs)",
                            color: "var(--warning)",
                            background: "var(--warning-muted)",
                            padding: "var(--space-2) var(--space-3)",
                            borderRadius: "var(--radius-sm)",
                          }}
                        >
                          ✏️ Revision notes: {campaign.revision_notes}
                        </p>
                      )}
                    </div>
                  </div>

                  <div style={{ textAlign: "right", flexShrink: 0, display: "flex", flexDirection: "column", gap: "var(--space-2)", alignItems: "flex-end" }}>
                    <div style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)" }}>
                      {new Date(campaign.created_at).toLocaleDateString()}
                    </div>
                    {campaign.revision_count > 0 && (
                      <div style={{ fontSize: "var(--font-xs)", color: "var(--warning)" }}>
                        {campaign.revision_count} revision{campaign.revision_count > 1 ? "s" : ""}
                      </div>
                    )}
                    <div style={{ display: "flex", gap: "var(--space-2)", marginTop: "var(--space-2)", flexWrap: "wrap" }}>
                      {primaryMediaUrl && (
                        <a
                          href={primaryMediaUrl}
                          download={`campaign-${campaign.id}.${isVideo ? "mp4" : "png"}`}
                          className="btn btn-sm btn-secondary"
                          title={isVideo ? "Download video reel" : "Download generated graphic"}
                        >
                          {isVideo ? "⬇️ Download Video" : "⬇️ Download Image"}
                        </a>
                      )}
                      {((campaign.product_name || "").toLowerCase().includes("loan") ||
                        (campaign.generated_caption || "").toLowerCase().includes("loan")) && (
                          <a
                            href="https://loansolutions.everythingrental.in/application"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="btn btn-sm"
                            style={{
                              background: "linear-gradient(135deg, #10B981, #059669)",
                              color: "#fff",
                              border: "none",
                              fontWeight: 600,
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "4px",
                            }}
                            title="Open official Loan Solutions application page"
                          >
                            📝 Apply Now 🔗
                          </a>
                        )}
                      {campaign.status !== "posted" && (
                        <button
                          className="btn btn-sm btn-primary"
                          onClick={() => openPlatformModal(campaign)}
                          title="Approve and choose social account to publish"
                        >
                          🚀 Approve & Post
                        </button>
                      )}
                      <button
                        className="btn btn-sm btn-ghost"
                        onClick={() => handleDelete(campaign.id)}
                        title="Delete campaign"
                        style={{ color: "var(--danger)" }}
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">📋</div>
            <h3 className="empty-state-title">
              {filter === "all" ? "No Campaigns Yet" : `No ${CAMPAIGN_STATUSES[filter]?.label || filter} Campaigns`}
            </h3>
            <p className="empty-state-description">
              {filter === "all"
                ? "Generate your first content to see campaigns and graphics here."
                : "No campaigns match this filter."}
            </p>
            {filter === "all" && (
              <a href="/generate" className="btn btn-primary">
                ✨ Create First Campaign
              </a>
            )}
          </div>
        </div>
      )}

      {/* Lightbox Media Modal (Image or Video) */}
      {previewMedia && (
        <div
          onClick={() => setPreviewMedia(null)}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.88)",
            backdropFilter: "blur(10px)",
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "var(--space-4)",
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              position: "relative",
              maxWidth: "92vw",
              maxHeight: "92vh",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
            }}
          >
            <div style={{ width: "100%", display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--space-2)" }}>
              <span style={{ color: "#fff", fontWeight: 600, fontSize: "var(--font-sm)" }}>
                {previewMedia.isVideo ? "🎬 Generated Video Reel Preview" : "🖼️ Generated Social Graphic Preview"}
              </span>
              <button
                onClick={() => setPreviewMedia(null)}
                style={{
                  background: "rgba(255,255,255,0.15)",
                  border: "none",
                  color: "#fff",
                  fontSize: "1.1rem",
                  cursor: "pointer",
                  borderRadius: "50%",
                  width: 32,
                  height: 32,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                ✕
              </button>
            </div>
            {previewMedia.isVideo ? (
              <video
                src={previewMedia.url}
                controls
                autoPlay
                style={{
                  maxWidth: "100%",
                  maxHeight: "78vh",
                  borderRadius: "var(--radius-md)",
                  boxShadow: "0 16px 48px rgba(0,0,0,0.8)",
                  border: "1px solid rgba(255,255,255,0.2)",
                }}
              />
            ) : (
              <img
                src={previewMedia.url}
                alt="Generated Social Graphic"
                style={{
                  maxWidth: "100%",
                  maxHeight: "78vh",
                  borderRadius: "var(--radius-md)",
                  boxShadow: "0 16px 48px rgba(0,0,0,0.8)",
                  border: "1px solid rgba(255,255,255,0.2)",
                }}
              />
            )}
            <div style={{ marginTop: "var(--space-3)", display: "flex", gap: "var(--space-3)" }}>
              <a
                href={previewMedia.url}
                download={previewMedia.isVideo ? "social-media-reel.mp4" : "social-media-graphic.png"}
                className="btn btn-primary btn-sm"
              >
                {previewMedia.isVideo ? "⬇️ Download HD Video Reel" : "⬇️ Download High-Res Graphic"}
              </a>
              <button
                onClick={() => setPreviewMedia(null)}
                className="btn btn-secondary btn-sm"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Platform Selection & Approval Modal */}
      {selectedCampaignForPost && (
        <div
          onClick={() => {
            if (postingStatus !== "posting") setSelectedCampaignForPost(null);
          }}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.82)",
            backdropFilter: "blur(12px)",
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "var(--space-4)",
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              position: "relative",
              maxWidth: 560,
              width: "100%",
              background: "var(--bg-secondary)",
              border: "1px solid var(--border-light)",
              borderRadius: "var(--radius-xl)",
              padding: "var(--space-6)",
              boxShadow: "0 24px 64px rgba(0, 0, 0, 0.6)",
              display: "flex",
              flexDirection: "column",
              gap: "var(--space-5)",
              animation: "fadeIn 0.25s ease-out",
            }}
          >
            {/* Header */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <h3 style={{ margin: 0, fontSize: "var(--font-xl)", fontWeight: 700, display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                  <span>🚀</span> Approve & Post
                </h3>
                <p style={{ margin: "var(--space-1) 0 0", fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>
                  Which social media platform would you like to publish this post to?
                </p>
              </div>
              <button
                disabled={postingStatus === "posting"}
                onClick={() => setSelectedCampaignForPost(null)}
                style={{
                  background: "rgba(255,255,255,0.06)",
                  border: "1px solid var(--border)",
                  color: "var(--text-secondary)",
                  borderRadius: "50%",
                  width: 32,
                  height: 32,
                  cursor: postingStatus === "posting" ? "not-allowed" : "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "1rem",
                }}
                title="Cancel and close"
              >
                ✕
              </button>
            </div>

            {/* Campaign Summary snippet */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "var(--space-3)",
                padding: "var(--space-3)",
                background: "var(--bg-tertiary)",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border)",
              }}
            >
              {(() => {
                const mediaArr = safeArray(selectedCampaignForPost.media_paths);
                const firstMediaUrl = mediaArr.length > 0 ? getMediaUrl(mediaArr[0]) : null;
                return firstMediaUrl ? (
                  <img
                    src={firstMediaUrl}
                    alt="Preview"
                    style={{ width: 50, height: 50, objectFit: "cover", borderRadius: "var(--radius-sm)", flexShrink: 0 }}
                  />
                ) : (
                  <div style={{ width: 50, height: 50, background: "var(--bg-primary)", display: "flex", alignItems: "center", justifyContent: "center", borderRadius: "var(--radius-sm)", fontSize: "1.4rem" }}>
                    📋
                  </div>
                );
              })()}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)", textTransform: "uppercase", fontWeight: 600 }}>
                  Selected Campaign #{selectedCampaignForPost.id.slice(0, 8)}
                </div>
                <div style={{ fontSize: "var(--font-sm)", fontWeight: 600, color: "var(--text-primary)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {selectedCampaignForPost.generated_caption?.slice(0, 60) || "Social Media Post"}...
                </div>
              </div>
            </div>

            {/* Platform Selection Options */}
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
              <div style={{ fontSize: "var(--font-xs)", fontWeight: 600, color: "var(--text-tertiary)", textTransform: "uppercase" }}>
                Select Social Platform:
              </div>

              {[
                {
                  id: "facebook",
                  name: "Facebook",
                  icon: "📘",
                  desc: "Publishes directly to Facebook Feed with media & hashtags",
                  highlight: "🔐 Checks login · Prompts for password via Telegram if required",
                },
                {
                  id: "instagram",
                  name: "Instagram",
                  icon: "📸",
                  desc: "Publishes image and captions directly to your Instagram profile",
                },
                {
                  id: "linkedin",
                  name: "LinkedIn",
                  icon: "💼",
                  desc: "Shares marketing update with attached image to LinkedIn feed",
                },
                {
                  id: "whatsapp",
                  name: "WhatsApp",
                  icon: "💬",
                  desc: "Broadcasts graphic and copy via WhatsApp Web",
                },
              ].map((plat) => {
                const isSelected = targetPlatform === plat.id;
                return (
                  <div
                    key={plat.id}
                    onClick={() => {
                      if (postingStatus !== "posting") setTargetPlatform(plat.id);
                    }}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "var(--space-3) var(--space-4)",
                      borderRadius: "var(--radius-md)",
                      border: `1.5px solid ${isSelected ? "var(--primary)" : "var(--border)"}`,
                      background: isSelected ? "rgba(99, 102, 241, 0.12)" : "var(--bg-tertiary)",
                      cursor: postingStatus === "posting" ? "not-allowed" : "pointer",
                      transition: "all 0.15s ease",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                      <span style={{ fontSize: "1.5rem" }}>{plat.icon}</span>
                      <div>
                        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                          <strong style={{ fontSize: "var(--font-sm)", color: isSelected ? "var(--primary-light)" : "var(--text-primary)" }}>
                            {plat.name}
                          </strong>
                          {plat.highlight && (
                            <span
                              style={{
                                fontSize: "10px",
                                padding: "1px 6px",
                                borderRadius: "4px",
                                background: "rgba(59, 130, 246, 0.2)",
                                color: "#60A5FA",
                                border: "1px solid rgba(59, 130, 246, 0.4)",
                                fontWeight: 600,
                              }}
                            >
                              {plat.highlight}
                            </span>
                          )}
                        </div>
                        <div style={{ fontSize: "var(--font-xs)", color: "var(--text-secondary)", marginTop: 2 }}>
                          {plat.desc}
                        </div>
                      </div>
                    </div>
                    <div
                      style={{
                        width: 18,
                        height: 18,
                        borderRadius: "50%",
                        border: `2px solid ${isSelected ? "var(--primary)" : "var(--border-light)"}`,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        background: isSelected ? "var(--primary)" : "transparent",
                      }}
                    >
                      {isSelected && <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#fff" }} />}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Posting Status Feedback Banner */}
            {postingStatus !== "idle" && (
              <div
                style={{
                  padding: "var(--space-3) var(--space-4)",
                  borderRadius: "var(--radius-md)",
                  fontSize: "var(--font-sm)",
                  background:
                    postingStatus === "posting"
                      ? "rgba(59, 130, 246, 0.12)"
                      : postingStatus === "success"
                        ? "rgba(16, 185, 129, 0.12)"
                        : "rgba(239, 68, 68, 0.12)",
                  border: `1px solid ${postingStatus === "posting"
                      ? "rgba(59, 130, 246, 0.3)"
                      : postingStatus === "success"
                        ? "rgba(16, 185, 129, 0.3)"
                        : "rgba(239, 68, 68, 0.3)"
                    }`,
                  color:
                    postingStatus === "posting"
                      ? "#93C5FD"
                      : postingStatus === "success"
                        ? "var(--success)"
                        : "var(--danger)",
                  display: "flex",
                  alignItems: "center",
                  gap: "var(--space-3)",
                }}
              >
                {postingStatus === "posting" && <span className="spinner" style={{ width: 18, height: 18 }} />}
                {postingStatus === "success" && <span style={{ fontSize: "1.2rem" }}>✅</span>}
                {postingStatus === "error" && <span style={{ fontSize: "1.2rem" }}>⚠️</span>}
                <div style={{ flex: 1, lineHeight: 1.4 }}>{postingMessage}</div>
              </div>
            )}

            {/* Action Buttons: Cancel + Confirm */}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "var(--space-3)", marginTop: "var(--space-2)" }}>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={postingStatus === "posting"}
                onClick={() => {
                  setSelectedCampaignForPost(null);
                  setPostingStatus("idle");
                  setPostingMessage("");
                }}
              >
                ❌ Cancel
              </button>

              {postingStatus === "success" ? (
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => {
                    setSelectedCampaignForPost(null);
                    setPostingStatus("idle");
                    setPostingMessage("");
                  }}
                >
                  Done
                </button>
              ) : (
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={postingStatus === "posting"}
                  onClick={handlePublishToSelectedPlatform}
                >
                  {postingStatus === "posting" ? (
                    <>
                      <span className="spinner" style={{ width: 16, height: 16, borderTopColor: "#fff" }} />
                      Publishing to {targetPlatform.toUpperCase()}...
                    </>
                  ) : (
                    `🚀 Post to ${targetPlatform.charAt(0).toUpperCase() + targetPlatform.slice(1)}`
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
