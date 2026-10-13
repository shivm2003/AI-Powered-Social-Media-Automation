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
  const [previewImage, setPreviewImage] = useState(null);

  useEffect(() => {
    fetchCampaigns();
  }, []);

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

  async function handleApprove(id) {
    if (!confirm("Are you sure you want to approve and publish this campaign to selected social accounts?")) return;
    try {
      const res = await fetch(`/api/campaigns/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "approve" }),
      });
      if (res.ok) {
        alert("🚀 Campaign approved and publishing dispatched!");
        fetchCampaigns();
      }
    } catch (err) {
      alert("Error: " + err.message);
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

            return (
              <div className="card" key={campaign.id} style={{ overflow: "hidden" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "var(--space-4)" }}>
                  <div style={{ display: "flex", gap: "var(--space-4)", flex: 1, minWidth: 280 }}>
                    {/* Media Thumbnail or Fallback Icon */}
                    {primaryMediaUrl ? (
                      <div
                        onClick={() => setPreviewImage(primaryMediaUrl)}
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
                        title="Click to view full image in high-res"
                      >
                        <img
                          src={primaryMediaUrl}
                          alt={campaign.product_name || "Generated Media"}
                          style={{ width: "100%", height: "100%", objectFit: "cover" }}
                        />
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
                          🔍 View Full
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
                          download={`campaign-${campaign.id}.png`}
                          className="btn btn-sm btn-secondary"
                          title="Download generated graphic"
                        >
                          ⬇️ Download Image
                        </a>
                      )}
                      {campaign.status !== "posted" && (
                        <button
                          className="btn btn-sm btn-primary"
                          onClick={() => handleApprove(campaign.id)}
                          title="Approve and post to social accounts"
                        >
                          🚀 Post Now
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

      {/* Lightbox Image Modal */}
      {previewImage && (
        <div
          onClick={() => setPreviewImage(null)}
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
              <span style={{ color: "#fff", fontWeight: 600, fontSize: "var(--font-sm)" }}>Generated Social Graphic Preview</span>
              <button
                onClick={() => setPreviewImage(null)}
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
            <img
              src={previewImage}
              alt="Generated Social Graphic"
              style={{
                maxWidth: "100%",
                maxHeight: "78vh",
                borderRadius: "var(--radius-md)",
                boxShadow: "0 16px 48px rgba(0,0,0,0.8)",
                border: "1px solid rgba(255,255,255,0.2)",
              }}
            />
            <div style={{ marginTop: "var(--space-3)", display: "flex", gap: "var(--space-3)" }}>
              <a
                href={previewImage}
                download="social-media-graphic.png"
                className="btn btn-primary btn-sm"
              >
                ⬇️ Download High-Res Graphic
              </a>
              <button
                onClick={() => setPreviewImage(null)}
                className="btn btn-secondary btn-sm"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
