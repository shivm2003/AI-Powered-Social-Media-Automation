"use client";

import { useState, useEffect } from "react";
import { PLATFORMS } from "@/lib/constants";

export default function AccountsPage() {
  const [selectedPlatforms, setSelectedPlatforms] = useState([]);
  const [accounts, setAccounts] = useState({});
  const [savedAccounts, setSavedAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testingLogin, setTestingLogin] = useState(null);

  useEffect(() => {
    fetchAccounts();
  }, []);

  async function fetchAccounts() {
    try {
      const res = await fetch("/api/accounts");
      const data = await res.json();
      setSavedAccounts(data);

      // Populate selected platforms and form state from saved accounts
      const platforms = [];
      const accountState = {};
      data.forEach((acc) => {
        platforms.push(acc.platform);
        accountState[acc.platform] = {
          username: acc.username || "",
          password: "",
          status: acc.session_status,
          ...acc.extra_fields,
        };
      });
      setSelectedPlatforms(platforms);
      setAccounts(accountState);
    } catch (error) {
      console.error("Failed to fetch accounts:", error);
    } finally {
      setLoading(false);
    }
  }

  function togglePlatform(platform) {
    setSelectedPlatforms((prev) => {
      if (prev.includes(platform)) {
        return prev.filter((p) => p !== platform);
      }
      // Initialize default form state for this platform
      if (!accounts[platform]) {
        const defaults = {};
        PLATFORMS[platform].fields.forEach((field) => {
          defaults[field.key] = field.defaultValue || "";
        });
        setAccounts((prev) => ({ ...prev, [platform]: { ...defaults, status: "unverified" } }));
      }
      return [...prev, platform];
    });
  }

  function updateField(platform, key, value) {
    setAccounts((prev) => ({
      ...prev,
      [platform]: { ...prev[platform], [key]: value },
    }));
  }

  async function saveAllAccounts() {
    setSaving(true);
    try {
      for (const platform of selectedPlatforms) {
        const accountData = accounts[platform] || {};
        const config = PLATFORMS[platform];

        // Extract username from appropriate field
        const usernameField = config.fields.find((f) => f.key === "username" || f.key === "email" || f.key === "phone");
        const passwordField = config.fields.find((f) => f.key === "password");

        // Collect extra fields (everything except username/password)
        const extra_fields = {};
        config.fields.forEach((field) => {
          if (field.key !== "password" && field.key !== usernameField?.key) {
            if (accountData[field.key]) {
              extra_fields[field.key] = accountData[field.key];
            }
          }
        });

        await fetch("/api/accounts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            platform,
            username: usernameField ? accountData[usernameField.key] : null,
            password: passwordField ? accountData[passwordField.key] : null,
            extra_fields,
          }),
        });
      }

      // Remove unselected platforms
      for (const acc of savedAccounts) {
        if (!selectedPlatforms.includes(acc.platform)) {
          await fetch(`/api/accounts?id=${acc.id}`, { method: "DELETE" });
        }
      }

      await fetchAccounts();
      alert("All accounts saved successfully!");
    } catch (error) {
      console.error("Failed to save accounts:", error);
    } finally {
      setSaving(false);
    }
  }

  async function testLogin(platform) {
    setTestingLogin(platform);
    try {
      const platformData = accounts[platform] || {};
      const config = PLATFORMS[platform];
      const usernameField = config.fields.find((f) => f.key === "username" || f.key === "email" || f.key === "phone");
      const passwordField = config.fields.find((f) => f.key === "password");

      const res = await fetch("/api/accounts/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          platform,
          username: usernameField ? platformData[usernameField.key] : null,
          password: passwordField ? platformData[passwordField.key] : null,
        }),
      });

      const data = await res.json();
      if (res.ok && data.verified) {
        setAccounts((prev) => ({
          ...prev,
          [platform]: { ...prev[platform], status: "verified" },
        }));
        alert(`✅ ${data.message || `Session verified for ${PLATFORMS[platform]?.name}! Profile saved.`}`);
      } else {
        alert(`Notice: ${data.message || data.error || "Login window closed."}`);
      }
    } catch (err) {
      console.error("Test login failed:", err);
      alert(`Could not complete login test: ${err.message}`);
    } finally {
      setTestingLogin(null);
      fetchAccounts();
    }
  }

  function shouldShowField(field, platformData) {
    if (!field.showIf) return true;
    return platformData[field.showIf.field] === field.showIf.value;
  }

  if (loading) {
    return (
      <div className="loading-overlay">
        <div className="spinner" />
        <span>Loading accounts...</span>
      </div>
    );
  }

  return (
    <div className="animate-fadeIn">
      <div className="page-header">
        <div>
          <h1 className="page-title">Social Accounts</h1>
          <p className="page-subtitle">Connect and manage your social media accounts</p>
        </div>
        <button
          className="btn btn-primary"
          onClick={saveAllAccounts}
          disabled={saving || selectedPlatforms.length === 0}
        >
          {saving ? "Saving..." : "💾 Save All Credentials"}
        </button>
      </div>

      {/* Platform Selection */}
      <div className="card" style={{ marginBottom: "var(--space-6)" }}>
        <div className="card-header">
          <h3 className="card-title">Select Platforms</h3>
          <span style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>
            {selectedPlatforms.length} selected
          </span>
        </div>
        <div className="checkbox-group">
          {Object.entries(PLATFORMS).map(([key, platform]) => (
            <label
              key={key}
              className={`checkbox-label ${selectedPlatforms.includes(key) ? "checked" : ""}`}
              style={{
                borderColor: selectedPlatforms.includes(key) ? platform.color : undefined,
                background: selectedPlatforms.includes(key) ? platform.colorMuted : undefined,
                minWidth: 160,
              }}
            >
              <input
                type="checkbox"
                checked={selectedPlatforms.includes(key)}
                onChange={() => togglePlatform(key)}
              />
              <span style={{ fontSize: "1.2rem" }}>{platform.icon}</span>
              <span style={{ fontWeight: 600 }}>{platform.name}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Dynamic Credential Fields */}
      {selectedPlatforms.length > 0 ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
          {selectedPlatforms.map((platformKey) => {
            const platform = PLATFORMS[platformKey];
            const platformData = accounts[platformKey] || {};
            const savedAccount = savedAccounts.find((a) => a.platform === platformKey);
            const status = platformData.status || savedAccount?.session_status || "unverified";

            return (
              <div
                className="card"
                key={platformKey}
                style={{
                  borderLeft: `3px solid ${platform.color}`,
                }}
              >
                <div className="card-header">
                  <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                    <span style={{ fontSize: "1.5rem" }}>{platform.icon}</span>
                    <div>
                      <h3 className="card-title">{platform.name}</h3>
                      {platform.loginNote && (
                        <p style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)", marginTop: "var(--space-1)" }}>
                          {platform.loginNote}
                        </p>
                      )}
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                      <span className={`status-dot ${status} pulse`} />
                      <span style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)", textTransform: "capitalize" }}>
                        {status}
                      </span>
                    </div>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => testLogin(platformKey)}
                      disabled={testingLogin === platformKey}
                    >
                      {testingLogin === platformKey ? (
                        <>
                          <span className="spinner" style={{ width: 14, height: 14 }} />
                          Testing...
                        </>
                      ) : (
                        "🔑 Test Login"
                      )}
                    </button>
                  </div>
                </div>

                <div className="form-row">
                  {platform.fields.map((field) => {
                    if (!shouldShowField(field, platformData)) return null;

                    return (
                      <div className="form-group" key={field.key}>
                        <label className="form-label">
                          {field.label}
                          {field.required && <span className="required">*</span>}
                        </label>
                        {field.type === "select" ? (
                          <select
                            className="form-select"
                            value={platformData[field.key] || field.defaultValue || ""}
                            onChange={(e) => updateField(platformKey, field.key, e.target.value)}
                          >
                            {field.options.map((opt) => (
                              <option key={opt} value={opt} style={{ textTransform: "capitalize" }}>
                                {opt.charAt(0).toUpperCase() + opt.slice(1)}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <input
                            className="form-input"
                            type={field.type}
                            value={platformData[field.key] || ""}
                            onChange={(e) => updateField(platformKey, field.key, e.target.value)}
                            placeholder={field.placeholder}
                          />
                        )}
                      </div>
                    );
                  })}
                </div>

                {savedAccount?.has_password && !platformData.password && (
                  <div
                    style={{
                      marginTop: "var(--space-3)",
                      padding: "var(--space-2) var(--space-3)",
                      background: "var(--success-muted)",
                      borderRadius: "var(--radius-sm)",
                      fontSize: "var(--font-xs)",
                      color: "var(--success)",
                      display: "flex",
                      alignItems: "center",
                      gap: "var(--space-2)",
                    }}
                  >
                    🔒 Password is saved. Leave blank to keep existing password.
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">🔗</div>
            <h3 className="empty-state-title">No Platforms Selected</h3>
            <p className="empty-state-description">
              Select one or more social media platforms above to configure your accounts.
            </p>
          </div>
        </div>
      )}

      {/* Info Box */}
      <div
        className="card"
        style={{
          marginTop: "var(--space-6)",
          background: "var(--info-muted)",
          borderColor: "var(--info)",
        }}
      >
        <h4 style={{ marginBottom: "var(--space-3)", display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
          ℹ️ How Login Works
        </h4>
        <div style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)", lineHeight: 1.8 }}>
          <p><strong>1. First Time:</strong> Click &quot;Test Login&quot; — a Chrome window opens. Log in manually and complete MFA (2FA).</p>
          <p><strong>2. Session Saved:</strong> Your Chrome session (cookies, tokens) is saved locally in a dedicated profile.</p>
          <p><strong>3. Auto-Login:</strong> All future operations reuse your saved session — no MFA needed again.</p>
          <p><strong>4. Security:</strong> Passwords are encrypted with AES-256 and stored only on your local machine.</p>
        </div>
      </div>
    </div>
  );
}
