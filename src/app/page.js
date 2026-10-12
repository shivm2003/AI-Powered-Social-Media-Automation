"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { CAMPAIGN_STATUSES } from "@/lib/constants";

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  async function fetchStats() {
    try {
      const res = await fetch("/api/stats");
      const data = await res.json();
      setStats(data);
    } catch (error) {
      console.error("Failed to fetch stats:", error);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="loading-overlay">
        <div className="spinner" />
        <span>Loading dashboard...</span>
      </div>
    );
  }

  return (
    <div className="animate-fadeIn">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Your AI-powered social media command center</p>
        </div>
        <Link href="/generate" className="btn btn-primary btn-lg">
          ✨ Generate Content
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-icon purple">📦</div>
          <div>
            <div className="stat-value">{stats?.productCount || 0}</div>
            <div className="stat-label">Products</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon cyan">🔗</div>
          <div>
            <div className="stat-value">{stats?.accountCount || 0}</div>
            <div className="stat-label">Connected Accounts</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon green">🎉</div>
          <div>
            <div className="stat-value">{stats?.postedCount || 0}</div>
            <div className="stat-label">Published Posts</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon orange">⏳</div>
          <div>
            <div className="stat-value">{stats?.pendingCount || 0}</div>
            <div className="stat-label">Pending Approval</div>
          </div>
        </div>
      </div>

      {/* Quick Actions + Recent Activity */}
      <div className="grid-2">
        {/* Quick Actions */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">⚡ Quick Actions</h3>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
            <Link href="/products" className="btn btn-secondary" style={{ justifyContent: "flex-start" }}>
              📦 Manage Products
            </Link>
            <Link href="/accounts" className="btn btn-secondary" style={{ justifyContent: "flex-start" }}>
              🔗 Connect Social Accounts
            </Link>
            <Link href="/generate" className="btn btn-secondary" style={{ justifyContent: "flex-start" }}>
              ✨ Generate New Content
            </Link>
            <Link href="/settings" className="btn btn-secondary" style={{ justifyContent: "flex-start" }}>
              ⚙️ Configure Settings
            </Link>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">📋 Recent Activity</h3>
          </div>
          {stats?.recentCampaigns?.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
              {stats.recentCampaigns.slice(0, 5).map((campaign) => {
                const statusConfig = CAMPAIGN_STATUSES[campaign.status] || CAMPAIGN_STATUSES.draft;
                return (
                  <div
                    key={campaign.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "var(--space-3) var(--space-4)",
                      background: "var(--bg-tertiary)",
                      borderRadius: "var(--radius-md)",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                      <span>{statusConfig.icon}</span>
                      <div>
                        <div style={{ fontSize: "var(--font-sm)", fontWeight: 600 }}>
                          {campaign.product_name || "Untitled"}
                        </div>
                        <div style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)" }}>
                          {campaign.content_type} • {campaign.llm_provider}
                        </div>
                      </div>
                    </div>
                    <span className={`tag tag-${statusConfig.color}`}>{statusConfig.label}</span>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="empty-state" style={{ padding: "var(--space-8) 0" }}>
              <div className="empty-state-icon">📋</div>
              <p className="empty-state-description">
                No campaigns yet. Generate your first content to get started!
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Getting Started Guide */}
      {stats?.productCount === 0 && (
        <div
          className="card animate-slideUp"
          style={{
            marginTop: "var(--space-8)",
            background: "var(--accent-primary-muted)",
            borderColor: "var(--accent-primary)",
          }}
        >
          <div className="card-header">
            <h3 className="card-title">🚀 Getting Started</h3>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)" }}>
              <div className="stepper-number" style={{ background: "var(--accent-primary)", color: "white", borderColor: "var(--accent-primary)" }}>1</div>
              <div>
                <div style={{ fontWeight: 600 }}>Add your first product</div>
                <div style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>
                  Define your brand, target audience, and visual identity
                </div>
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)" }}>
              <div className="stepper-number">2</div>
              <div>
                <div style={{ fontWeight: 600 }}>Connect social media accounts</div>
                <div style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>
                  Link Facebook, Instagram, LinkedIn, or WhatsApp
                </div>
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)" }}>
              <div className="stepper-number">3</div>
              <div>
                <div style={{ fontWeight: 600 }}>Configure Telegram bot</div>
                <div style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>
                  Set up approval workflow via Telegram
                </div>
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)" }}>
              <div className="stepper-number">4</div>
              <div>
                <div style={{ fontWeight: 600 }}>Generate your first post!</div>
                <div style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>
                  Let AI create amazing content for your social media
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
