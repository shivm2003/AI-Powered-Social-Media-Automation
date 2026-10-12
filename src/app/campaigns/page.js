"use client";

import { useState, useEffect } from "react";
import { CAMPAIGN_STATUSES, CONTENT_TYPES, LLM_PROVIDERS, PLATFORMS } from "@/lib/constants";

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

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
          <p className="page-subtitle">Track all your generated content and their publishing status</p>
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
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          {filteredCampaigns.map((campaign) => {
            const statusConfig = CAMPAIGN_STATUSES[campaign.status] || CAMPAIGN_STATUSES.draft;
            const platforms = JSON.parse(campaign.platforms || "[]");

            return (
              <div className="card" key={campaign.id}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div style={{ display: "flex", gap: "var(--space-4)", flex: 1 }}>
                    <div
                      style={{
                        width: 48,
                        height: 48,
                        borderRadius: "var(--radius-md)",
                        background: "var(--accent-primary-muted)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: "1.5rem",
                        flexShrink: 0,
                      }}
                    >
                      {CONTENT_TYPES[campaign.content_type]?.icon || "📝"}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", marginBottom: "var(--space-1)" }}>
                        <h4>{campaign.product_name || "Untitled Campaign"}</h4>
                        <span className={`tag tag-${statusConfig.color}`}>
                          {statusConfig.icon} {statusConfig.label}
                        </span>
                      </div>
                      <div style={{ display: "flex", gap: "var(--space-4)", fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>
                        <span>{CONTENT_TYPES[campaign.content_type]?.name || campaign.content_type}</span>
                        <span>•</span>
                        <span>{LLM_PROVIDERS[campaign.llm_provider]?.icon} {LLM_PROVIDERS[campaign.llm_provider]?.name || campaign.llm_provider}</span>
                        <span>•</span>
                        <span style={{ textTransform: "capitalize" }}>{campaign.language}</span>
                      </div>
                      {/* Target Platforms */}
                      {platforms.length > 0 && (
                        <div style={{ display: "flex", gap: "var(--space-2)", marginTop: "var(--space-2)" }}>
                          {platforms.map((p) => (
                            <span key={p} className="tag tag-default">
                              {PLATFORMS[p]?.icon} {PLATFORMS[p]?.name}
                            </span>
                          ))}
                        </div>
                      )}
                      {/* Generated Caption Preview */}
                      {campaign.generated_caption && (
                        <p style={{
                          marginTop: "var(--space-3)",
                          fontSize: "var(--font-sm)",
                          color: "var(--text-secondary)",
                          background: "var(--bg-tertiary)",
                          padding: "var(--space-3)",
                          borderRadius: "var(--radius-sm)",
                          borderLeft: "2px solid var(--accent-primary)",
                        }}>
                          {campaign.generated_caption.slice(0, 150)}{campaign.generated_caption.length > 150 ? "..." : ""}
                        </p>
                      )}
                      {/* Revision notes if any */}
                      {campaign.revision_notes && (
                        <p style={{
                          marginTop: "var(--space-2)",
                          fontSize: "var(--font-xs)",
                          color: "var(--warning)",
                          background: "var(--warning-muted)",
                          padding: "var(--space-2) var(--space-3)",
                          borderRadius: "var(--radius-sm)",
                        }}>
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
                    <div style={{ display: "flex", gap: "var(--space-2)", marginTop: "var(--space-2)" }}>
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
                ? "Generate your first content to see campaigns here."
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
    </div>
  );
}
