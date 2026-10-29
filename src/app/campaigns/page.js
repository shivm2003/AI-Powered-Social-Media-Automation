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
  const [targetPlatforms, setTargetPlatforms] = useState(["facebook", "instagram"]);
  const [postingStatus, setPostingStatus] = useState("idle"); // "idle" | "posting" | "success" | "error"
  const [postingMessage, setPostingMessage] = useState("");

  // Revision modal state
  const [selectedCampaignForRevision, setSelectedCampaignForRevision] = useState(null);
  const [revisionNotes, setRevisionNotes] = useState("");
  const [revisionContactNumber, setRevisionContactNumber] = useState("");
  const [revisionProvider, setRevisionProvider] = useState("gemini");
  const [revisionStatus, setRevisionStatus] = useState("idle"); // "idle" | "generating" | "success" | "error"
  const [revisionMessage, setRevisionMessage] = useState("");

  function openRevisionModal(campaign) {
    setSelectedCampaignForRevision(campaign);
    setRevisionNotes("");
    setRevisionContactNumber(campaign.contact_number || (campaign.product_name?.toLowerCase().includes("loan") ? "8112570656" : ""));
    setRevisionProvider(campaign.llm_provider || "gemini");
    setRevisionStatus("idle");
    setRevisionMessage("");
  }

  function applyPresetNote(note) {
    setRevisionNotes((prev) => {
      if (!prev.trim()) return note;
      if (prev.includes(note)) return prev;
      return `${prev.trim()}\n• ${note}`;
    });
  }

  async function handleSubmitRevision() {
    if (!selectedCampaignForRevision) return;
    if (!revisionNotes.trim()) {
      alert("Please enter revision instructions or choose from the suggested ideas.");
      return;
    }

    setRevisionStatus("generating");
    setRevisionMessage("Connecting to AI engine to rewrite copy, synthesize revised visual graphic, and dispatch updated preview to Telegram...");

    try {
      const res = await fetch(`/api/campaigns/${selectedCampaignForRevision.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "revise",
          notes: revisionNotes.trim(),
          provider: revisionProvider,
          contact_number: revisionContactNumber || null,
        }),
      });

      const data = await res.json();
      if (res.ok && data.success) {
        setRevisionStatus("success");
        setRevisionMessage(data.message || "🎉 Revision generated! Updated preview sent to Telegram.");
        fetchCampaigns();
      } else {
        setRevisionStatus("error");
        setRevisionMessage(data.error || data.warning || "Revision failed to generate.");
      }
    } catch (err) {
      setRevisionStatus("error");
      setRevisionMessage(err.message || "An unexpected error occurred during revision.");
    }
  }

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
    const existing = safeArray(campaign.platforms);
    setTargetPlatforms(existing.length > 0 ? existing : ["facebook", "instagram"]);
    setPostingStatus("idle");
    setPostingMessage("");
  }

  function toggleTargetPlatform(platId) {
    if (postingStatus === "posting") return;
    setTargetPlatforms((prev) =>
      prev.includes(platId) ? prev.filter((p) => p !== platId) : [...prev, platId]
    );
  }

  function selectBothMeta() {
    if (postingStatus === "posting") return;
    setTargetPlatforms(["facebook", "instagram"]);
  }

  async function handlePublishToSelectedPlatform() {
    if (!selectedCampaignForPost) return;
    if (targetPlatforms.length === 0) {
      alert("Please select at least one platform to publish to.");
      return;
    }
    setPostingStatus("posting");
    const platLabels = targetPlatforms.map((p) => p.toUpperCase()).join(" + ");
    setPostingMessage(
      `Connecting to Chrome browser and publishing to ${platLabels}... If login is required, please check your Telegram bot!`
    );

    try {
      const res = await fetch(`/api/campaigns/${selectedCampaignForPost.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "approve", platforms: targetPlatforms }),
      });
      const data = await res.json();
      if (res.ok) {
        setPostingStatus("success");
        setPostingMessage(data.message || `🎉 Successfully published to ${platLabels}!`);
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
                      <div style={{ display: "flex", gap: "var(--space-3)", fontSize: "var(--font-xs)", color: "var(--text-secondary)", marginTop: "var(--space-1)", flexWrap: "wrap", alignItems: "center" }}>
                        <span>{CONTENT_TYPES[campaign.content_type]?.name || campaign.content_type}</span>
                        <span>•</span>
                        <span>{LLM_PROVIDERS[campaign.llm_provider]?.icon} {LLM_PROVIDERS[campaign.llm_provider]?.name || campaign.llm_provider}</span>
                        <span>•</span>
                        <span style={{ textTransform: "capitalize" }}>{campaign.language}</span>
                        {(campaign.contact_number || campaign.product_name?.toLowerCase().includes("loan")) && (
                          <>
                            <span>•</span>
                            <span className="tag tag-success" style={{ fontSize: "11px", fontWeight: 600 }}>
                              📞 +91 {campaign.contact_number || "8112570656"}
                            </span>
                          </>
                        )}
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
                        <>
                          <button
                            className="btn btn-sm btn-secondary"
                            onClick={() => openRevisionModal(campaign)}
                            title="Suggest revision for marketing copy or visual graphic"
                            style={{
                              borderColor: "rgba(245, 158, 11, 0.4)",
                              color: "#FBBF24",
                              background: "rgba(245, 158, 11, 0.08)",
                            }}
                          >
                            ✏️ Suggest Revision
                          </button>
                          <button
                            className="btn btn-sm btn-primary"
                            onClick={() => openPlatformModal(campaign)}
                            title="Approve and choose social account to publish"
                          >
                            🚀 Approve & Post
                          </button>
                        </>
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
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--space-1)" }}>
                <span style={{ fontSize: "var(--font-xs)", fontWeight: 600, color: "var(--text-tertiary)", textTransform: "uppercase" }}>
                  Select Target Platforms ({targetPlatforms.length} selected):
                </span>
                <div style={{ display: "flex", gap: "var(--space-2)" }}>
                  <button
                    type="button"
                    className="btn btn-sm btn-secondary"
                    onClick={selectBothMeta}
                    style={{ fontSize: "11px", padding: "2px 8px" }}
                    title="Select Facebook & Instagram together"
                  >
                    ⚡ Facebook + Instagram
                  </button>
                  <button
                    type="button"
                    className="btn btn-sm btn-secondary"
                    onClick={() => setTargetPlatforms(["facebook", "instagram", "linkedin", "whatsapp"])}
                    style={{ fontSize: "11px", padding: "2px 8px" }}
                  >
                    Select All
                  </button>
                </div>
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
                  highlight: "✨ Direct Creator Studio & Post Pipeline",
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
                const isSelected = targetPlatforms.includes(plat.id);
                return (
                  <div
                    key={plat.id}
                    onClick={() => toggleTargetPlatform(plat.id)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "var(--space-3) var(--space-4)",
                      borderRadius: "var(--radius-md)",
                      border: `1.5px solid ${isSelected ? "var(--primary)" : "var(--border)"}`,
                      background: isSelected ? "rgba(99, 102, 241, 0.15)" : "var(--bg-tertiary)",
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
                        width: 20,
                        height: 20,
                        borderRadius: "4px",
                        border: `2px solid ${isSelected ? "var(--primary)" : "var(--border-light)"}`,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        background: isSelected ? "var(--primary)" : "transparent",
                        color: "#fff",
                        fontSize: "12px",
                        fontWeight: "bold",
                      }}
                    >
                      {isSelected ? "✓" : ""}
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
                  disabled={postingStatus === "posting" || targetPlatforms.length === 0}
                  onClick={handlePublishToSelectedPlatform}
                >
                  {postingStatus === "posting" ? (
                    <>
                      <span className="spinner" style={{ width: 16, height: 16, borderTopColor: "#fff" }} />
                      Publishing to {targetPlatforms.map((p) => p.toUpperCase()).join(" + ")}...
                    </>
                  ) : (
                    `🚀 Post to ${targetPlatforms.length === 0 ? "Select Platform" : targetPlatforms.map((p) => p.charAt(0).toUpperCase() + p.slice(1)).join(" & ")}`
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── Interactive Suggest Revision Modal ── */}
      {selectedCampaignForRevision && (
        <div
          className="modal-overlay"
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.75)",
            backdropFilter: "blur(8px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "var(--space-4)",
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget && revisionStatus !== "generating") {
              setSelectedCampaignForRevision(null);
              setRevisionStatus("idle");
              setRevisionMessage("");
            }
          }}
        >
          <div
            className="modal card"
            style={{
              maxWidth: "640px",
              width: "100%",
              maxHeight: "90vh",
              overflowY: "auto",
              padding: "var(--space-6)",
              background: "linear-gradient(145deg, rgba(26, 26, 46, 0.96), rgba(15, 15, 26, 0.98))",
              border: "1px solid rgba(245, 158, 11, 0.35)",
              boxShadow: "0 25px 60px -15px rgba(245, 158, 11, 0.25)",
              display: "flex",
              flexDirection: "column",
              gap: "var(--space-4)",
            }}
          >
            {/* Header */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", marginBottom: "var(--space-1)" }}>
                  <span style={{ fontSize: "1.4rem" }}>✏️</span>
                  <h3 style={{ margin: 0, fontSize: "var(--font-xl)", fontWeight: 700, color: "#fff" }}>
                    Suggest AI Revision
                  </h3>
                  <span
                    className="tag"
                    style={{
                      background: "rgba(245, 158, 11, 0.15)",
                      color: "#FBBF24",
                      border: "1px solid rgba(245, 158, 11, 0.3)",
                      fontSize: "11px",
                    }}
                  >
                    Revision #{((selectedCampaignForRevision.revision_count || 0) + 1)}
                  </span>
                </div>
                <p style={{ margin: 0, fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>
                  Refine copy tone, highlight key offers, or re-render visual graphics with AI.
                </p>
              </div>

              <button
                type="button"
                className="btn btn-ghost btn-sm"
                disabled={revisionStatus === "generating"}
                onClick={() => {
                  setSelectedCampaignForRevision(null);
                  setRevisionStatus("idle");
                  setRevisionMessage("");
                }}
                style={{ fontSize: "1.2rem", padding: "4px 8px" }}
              >
                ✕
              </button>
            </div>

            {/* Current Campaign Context */}
            <div
              style={{
                padding: "var(--space-3) var(--space-4)",
                background: "rgba(255, 255, 255, 0.03)",
                borderRadius: "var(--radius-md)",
                border: "1px solid rgba(255, 255, 255, 0.08)",
                fontSize: "var(--font-sm)",
              }}
            >
              <div style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: "4px" }}>
                Target Product: <span style={{ color: "var(--primary-light)" }}>{selectedCampaignForRevision.product_name || "Loan Solutions"}</span>
              </div>
              <div
                style={{
                  color: "var(--text-secondary)",
                  fontSize: "var(--font-xs)",
                  maxHeight: "60px",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  lineHeight: 1.4,
                }}
              >
                Previous Draft: {selectedCampaignForRevision.generated_caption ? selectedCampaignForRevision.generated_caption.slice(0, 140) + "..." : "No prior caption"}
              </div>
            </div>

            {/* Quick Preset Revision Chips */}
            <div>
              <label style={{ fontSize: "var(--font-xs)", fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: "var(--space-2)" }}>
                💡 QUICK REVISION IDEAS (CLICK TO APPLY)
              </label>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>
                {[
                  "📞 Highlight helpline +91 8112570656",
                  "⚡ Make tone higher energy & urgent",
                  "💰 Highlight ₹50 Lakh instant disbursal & 0% processing fee",
                  "📱 Shorten copy for quick mobile feed reading",
                  "🎨 Regenerate visual image with festive Indian theme",
                  "🏠 Focus on Griha Pravesh & Low EMI Home Loans",
                  "🤝 Highlight 100% paperless digital KYC",
                ].map((preset, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => applyPresetNote(preset)}
                    style={{
                      background: "rgba(124, 92, 252, 0.08)",
                      border: "1px solid rgba(124, 92, 252, 0.25)",
                      color: "var(--text-primary)",
                      padding: "4px 10px",
                      borderRadius: "20px",
                      fontSize: "12px",
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                      textAlign: "left",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = "rgba(124, 92, 252, 0.2)";
                      e.currentTarget.style.borderColor = "var(--primary-light)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = "rgba(124, 92, 252, 0.08)";
                      e.currentTarget.style.borderColor = "rgba(124, 92, 252, 0.25)";
                    }}
                  >
                    {preset}
                  </button>
                ))}
              </div>
            </div>

            {/* Optional Helpline / Mobile Number for Revision */}
            <div>
              <label style={{ fontSize: "var(--font-xs)", fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: "var(--space-1)" }}>
                📞 REVISION HELPLINE / MOBILE NUMBER (OPTIONAL)
              </label>
              <div style={{ position: "relative" }}>
                <span
                  style={{
                    position: "absolute",
                    left: "var(--space-3)",
                    top: "50%",
                    transform: "translateY(-50%)",
                    fontSize: "var(--font-sm)",
                    color: "var(--text-tertiary)",
                    fontWeight: 600,
                  }}
                >
                  +91
                </span>
                <input
                  type="tel"
                  value={revisionContactNumber}
                  onChange={(e) => setRevisionContactNumber(e.target.value.replace(/\D/g, "").slice(0, 10))}
                  placeholder="8112570656"
                  disabled={revisionStatus === "generating"}
                  style={{
                    width: "100%",
                    background: "var(--bg-tertiary)",
                    color: "var(--text-primary)",
                    border: "1px solid rgba(245, 158, 11, 0.3)",
                    borderRadius: "var(--radius-md)",
                    padding: "var(--space-2) var(--space-3) var(--space-2) 3.2rem",
                    fontSize: "var(--font-sm)",
                    boxSizing: "border-box",
                  }}
                />
              </div>
              <span style={{ fontSize: "11px", color: "var(--text-tertiary)", marginTop: "2px", display: "block" }}>
                Reflected on the regenerated visual graphic badge and Line 2 caption CTA.
              </span>
            </div>

            {/* AI Engine & Custom Instructions */}
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--space-2)" }}>
                <label style={{ fontSize: "var(--font-xs)", fontWeight: 600, color: "var(--text-secondary)", margin: 0 }}>
                  SPECIFIC REVISION INSTRUCTIONS
                </label>
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <span style={{ fontSize: "11px", color: "var(--text-secondary)" }}>Engine:</span>
                  <select
                    value={revisionProvider}
                    onChange={(e) => setRevisionProvider(e.target.value)}
                    disabled={revisionStatus === "generating"}
                    style={{
                      background: "var(--bg-tertiary)",
                      color: "var(--text-primary)",
                      border: "1px solid rgba(255, 255, 255, 0.12)",
                      borderRadius: "var(--radius-sm)",
                      padding: "2px 8px",
                      fontSize: "11px",
                    }}
                  >
                    <option value="gemini">♊ Gemini 2.5 Flash (Fastest)</option>
                    <option value="chatgpt">🤖 ChatGPT</option>
                    <option value="claude">🧠 Claude</option>
                  </select>
                </div>
              </div>

              <textarea
                rows={4}
                value={revisionNotes}
                onChange={(e) => setRevisionNotes(e.target.value)}
                disabled={revisionStatus === "generating"}
                placeholder="Describe what you want changed (e.g. 'Emphasize instant loan approval in 2 minutes, use golden and royal blue colors for Griha Pravesh image')..."
                style={{
                  width: "100%",
                  background: "var(--bg-tertiary)",
                  color: "var(--text-primary)",
                  border: "1px solid rgba(245, 158, 11, 0.3)",
                  borderRadius: "var(--radius-md)",
                  padding: "var(--space-3)",
                  fontSize: "var(--font-sm)",
                  lineHeight: 1.5,
                  resize: "vertical",
                  boxSizing: "border-box",
                  fontFamily: "inherit",
                }}
              />
            </div>

            {/* Status Feedback Banner */}
            {revisionStatus !== "idle" && (
              <div
                style={{
                  padding: "var(--space-3) var(--space-4)",
                  borderRadius: "var(--radius-md)",
                  fontSize: "var(--font-sm)",
                  background:
                    revisionStatus === "generating"
                      ? "rgba(245, 158, 11, 0.12)"
                      : revisionStatus === "success"
                        ? "rgba(16, 185, 129, 0.12)"
                        : "rgba(239, 68, 68, 0.12)",
                  border: `1px solid ${
                    revisionStatus === "generating"
                      ? "rgba(245, 158, 11, 0.35)"
                      : revisionStatus === "success"
                        ? "rgba(16, 185, 129, 0.35)"
                        : "rgba(239, 68, 68, 0.35)"
                  }`,
                  color:
                    revisionStatus === "generating"
                      ? "#FDE68A"
                      : revisionStatus === "success"
                        ? "var(--success)"
                        : "var(--danger)",
                  display: "flex",
                  alignItems: "center",
                  gap: "var(--space-3)",
                }}
              >
                {revisionStatus === "generating" && <span className="spinner" style={{ width: 18, height: 18 }} />}
                {revisionStatus === "success" && <span style={{ fontSize: "1.2rem" }}>✅</span>}
                {revisionStatus === "error" && <span style={{ fontSize: "1.2rem" }}>⚠️</span>}
                <div style={{ flex: 1, lineHeight: 1.4 }}>{revisionMessage}</div>
              </div>
            )}

            {/* Action Buttons */}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "var(--space-3)", marginTop: "var(--space-2)" }}>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={revisionStatus === "generating"}
                onClick={() => {
                  setSelectedCampaignForRevision(null);
                  setRevisionStatus("idle");
                  setRevisionMessage("");
                }}
              >
                Cancel
              </button>

              {revisionStatus === "success" ? (
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => {
                    setSelectedCampaignForRevision(null);
                    setRevisionStatus("idle");
                    setRevisionMessage("");
                  }}
                >
                  Done
                </button>
              ) : (
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={revisionStatus === "generating" || !revisionNotes.trim()}
                  onClick={handleSubmitRevision}
                  style={{
                    background: "linear-gradient(135deg, #F59E0B, #D97706)",
                    color: "#fff",
                    border: "none",
                    fontWeight: 600,
                  }}
                >
                  {revisionStatus === "generating" ? (
                    <>
                      <span className="spinner" style={{ width: 16, height: 16, borderTopColor: "#fff" }} />
                      Regenerating Content & Preview...
                    </>
                  ) : (
                    "🔄 Generate Revision & Update Preview"
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
