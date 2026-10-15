"use client";

import { useState, useEffect } from "react";
import { LLM_PROVIDERS, TONES, LANGUAGES } from "@/lib/constants";

export default function SettingsPage() {
  const [settings, setSettings] = useState({
    llm_provider: "gemini",
    telegram_bot_token: "",
    telegram_chat_id: "",
    default_language: "english",
    default_tone: "professional",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  async function fetchSettings() {
    try {
      const res = await fetch("/api/settings");
      const data = await res.json();
      setSettings((prev) => ({ ...prev, ...data }));
    } catch (error) {
      console.error("Failed to fetch settings:", error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchSettings();
  }, []);

  async function handleSave() {
    setSaving(true);
    try {
      await fetch("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (error) {
      console.error("Failed to save settings:", error);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="loading-overlay">
        <div className="spinner" />
        <span>Loading settings...</span>
      </div>
    );
  }

  return (
    <div className="animate-fadeIn">
      <div className="page-header">
        <div>
          <h1 className="page-title">Settings</h1>
          <p className="page-subtitle">Configure your AI providers, Telegram bot, and defaults</p>
        </div>
        <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? "Saving..." : saved ? "✅ Saved!" : "💾 Save Settings"}
        </button>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
        {/* LLM Provider */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">🤖 Default AI Provider</h3>
          </div>
          <p className="card-description" style={{ marginBottom: "var(--space-5)" }}>
            Select the default LLM to use for content generation. You can override this per campaign.
          </p>
          <div className="grid-3">
            {Object.entries(LLM_PROVIDERS).map(([key, provider]) => (
              <div
                key={key}
                onClick={() => setSettings({ ...settings, llm_provider: key })}
                style={{
                  padding: "var(--space-5)",
                  border: `2px solid ${settings.llm_provider === key ? provider.color : "var(--border)"}`,
                  borderRadius: "var(--radius-lg)",
                  cursor: "pointer",
                  background: settings.llm_provider === key ? provider.colorMuted : "var(--bg-tertiary)",
                  transition: "all var(--transition-fast)",
                  textAlign: "center",
                }}
              >
                <div style={{ fontSize: "2rem", marginBottom: "var(--space-2)" }}>{provider.icon}</div>
                <h4 style={{ fontSize: "var(--font-md)" }}>{provider.name}</h4>
                <p style={{ fontSize: "var(--font-xs)", color: "var(--text-secondary)", marginTop: "var(--space-1)" }}>
                  {provider.description}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Telegram Bot Configuration */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">📱 Telegram Bot</h3>
          </div>
          <p className="card-description" style={{ marginBottom: "var(--space-5)" }}>
            Set up your Telegram bot for content approval workflow. You&apos;ll receive previews and can approve/reject directly from Telegram.
          </p>

          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
            <div className="form-group">
              <label className="form-label">Bot Token <span className="required">*</span></label>
              <input
                className="form-input"
                type="password"
                value={settings.telegram_bot_token}
                onChange={(e) => setSettings({ ...settings, telegram_bot_token: e.target.value })}
                placeholder="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
              />
              <span className="form-help">
                Get this from @BotFather on Telegram. Send /newbot and follow the prompts.
              </span>
            </div>

            <div className="form-group">
              <label className="form-label">Chat ID <span className="required">*</span></label>
              <input
                className="form-input"
                value={settings.telegram_chat_id}
                onChange={(e) => setSettings({ ...settings, telegram_chat_id: e.target.value })}
                placeholder="Your Telegram Chat ID"
              />
              <span className="form-help">
                Send any message to your bot, then visit: https://api.telegram.org/bot&lt;TOKEN&gt;/getUpdates to find your chat_id.
              </span>
            </div>
          </div>

          {/* Telegram Setup Guide */}
          <div
            style={{
              marginTop: "var(--space-5)",
              padding: "var(--space-4)",
              background: "var(--info-muted)",
              borderRadius: "var(--radius-md)",
              border: "1px solid hsla(210, 80%, 58%, 0.2)",
            }}
          >
            <h4 style={{ fontSize: "var(--font-sm)", marginBottom: "var(--space-3)", color: "var(--info)" }}>
              📋 Quick Setup Guide
            </h4>
            <ol style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)", lineHeight: 2, paddingLeft: "var(--space-5)" }}>
              <li>Open Telegram and search for <strong>@BotFather</strong></li>
              <li>Send <code style={{ background: "var(--bg-tertiary)", padding: "2px 6px", borderRadius: 4 }}>/newbot</code> and follow the prompts</li>
              <li>Copy the <strong>bot token</strong> and paste above</li>
              <li>Start a chat with your new bot (send any message)</li>
              <li>Visit <code style={{ background: "var(--bg-tertiary)", padding: "2px 6px", borderRadius: 4 }}>https://api.telegram.org/bot&lt;TOKEN&gt;/getUpdates</code></li>
              <li>Find your <strong>chat_id</strong> in the response and paste above</li>
            </ol>
          </div>
        </div>

        {/* Default Settings */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">⚙️ Default Content Settings</h3>
          </div>
          <p className="card-description" style={{ marginBottom: "var(--space-5)" }}>
            These defaults will be pre-selected when creating new campaigns. You can always override them.
          </p>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Default Language</label>
              <select
                className="form-select"
                value={settings.default_language}
                onChange={(e) => setSettings({ ...settings, default_language: e.target.value })}
              >
                {LANGUAGES.map((l) => (
                  <option key={l.value} value={l.value}>{l.label}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Default Tone</label>
              <select
                className="form-select"
                value={settings.default_tone}
                onChange={(e) => setSettings({ ...settings, default_tone: e.target.value })}
              >
                {TONES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* System Info */}
        <div className="card" style={{ opacity: 0.7 }}>
          <div className="card-header">
            <h3 className="card-title">🔧 System Information</h3>
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "160px 1fr",
              gap: "var(--space-2) var(--space-4)",
              fontSize: "var(--font-sm)",
            }}
          >
            <span style={{ color: "var(--text-tertiary)" }}>Application:</span>
            <span>Manvxi AI</span>
            <span style={{ color: "var(--text-tertiary)" }}>Version:</span>
            <span>2.0.0 (3D Edition)</span>
            <span style={{ color: "var(--text-tertiary)" }}>Database:</span>
            <span>SQLite (local)</span>
            <span style={{ color: "var(--text-tertiary)" }}>Automation:</span>
            <span>Python + Selenium</span>
            <span style={{ color: "var(--text-tertiary)" }}>Encryption:</span>
            <span>AES-256-GCM</span>
          </div>
        </div>
      </div>

      {/* Toast Notification */}
      {saved && (
        <div className="toast success">
          ✅ Settings saved successfully!
        </div>
      )}
    </div>
  );
}
