"use client";

import { useState, useEffect } from "react";
import {
  PLATFORMS,
  LLM_PROVIDERS,
  CONTENT_TYPES,
  TONES,
  CTA_OPTIONS,
  VISUAL_STYLES,
  LANGUAGES,
  ASPECT_RATIOS,
} from "@/lib/constants";

const STEPS = [
  { number: 1, label: "Product" },
  { number: 2, label: "AI Provider" },
  { number: 3, label: "Platforms" },
  { number: 4, label: "Settings" },
  { number: 5, label: "Generate" },
];

export default function GeneratePage() {
  const [currentStep, setCurrentStep] = useState(1);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  const [config, setConfig] = useState({
    selectedProducts: [],
    llmProvider: "gemini",
    selectedPlatforms: [],
    contentType: "image",
    language: "english",
    tone: "professional",
    cta: "learn_more",
    hashtagStrategy: "auto",
    aspectRatio: "1:1",
    videoDuration: 15,
    visualStyle: "minimal",
    customInstructions: "",
  });

  useEffect(() => {
    fetchProducts();
  }, []);

  async function fetchProducts() {
    try {
      const res = await fetch("/api/products");
      const data = await res.json();
      setProducts(data);
    } catch (error) {
      console.error("Failed to fetch products:", error);
    } finally {
      setLoading(false);
    }
  }

  function toggleProduct(id) {
    setConfig((prev) => ({
      ...prev,
      selectedProducts: prev.selectedProducts.includes(id)
        ? prev.selectedProducts.filter((p) => p !== id)
        : [...prev.selectedProducts, id],
    }));
  }

  function togglePlatform(platform) {
    setConfig((prev) => ({
      ...prev,
      selectedPlatforms: prev.selectedPlatforms.includes(platform)
        ? prev.selectedPlatforms.filter((p) => p !== platform)
        : [...prev.selectedPlatforms, platform],
    }));
  }

  function canProceed() {
    switch (currentStep) {
      case 1: return config.selectedProducts.length > 0;
      case 2: return !!config.llmProvider;
      case 3: return config.selectedPlatforms.length > 0;
      case 4: return true;
      default: return true;
    }
  }

  async function handleGenerate() {
    setGenerating(true);
    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });

      const data = await res.json();
      if (res.ok) {
        alert(`🚀 ${data.message || "Content generated successfully!"}`);
        window.location.href = "/campaigns";
      } else {
        alert(`Error: ${data.error || "Failed to generate content"}`);
      }
    } catch (err) {
      console.error("Generation error:", err);
      alert(`Request failed: ${err.message}`);
    } finally {
      setGenerating(false);
    }
  }

  if (loading) {
    return (
      <div className="loading-overlay">
        <div className="spinner" />
        <span>Loading...</span>
      </div>
    );
  }

  return (
    <div className="animate-fadeIn">
      <div className="page-header">
        <div>
          <h1 className="page-title">Generate Content</h1>
          <p className="page-subtitle">Create AI-powered social media posts in a few steps</p>
        </div>
      </div>

      {/* Stepper */}
      <div className="stepper">
        {STEPS.map((step, i) => (
          <div key={step.number} style={{ display: "contents" }}>
            <div
              className={`stepper-step ${currentStep === step.number ? "active" : ""} ${currentStep > step.number ? "completed" : ""}`}
              style={{ cursor: "pointer" }}
              onClick={() => step.number < currentStep && setCurrentStep(step.number)}
            >
              <div className="stepper-number">
                {currentStep > step.number ? "✓" : step.number}
              </div>
              <span className="stepper-label">{step.label}</span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={`stepper-line ${currentStep > step.number ? "completed" : ""}`} />
            )}
          </div>
        ))}
      </div>

      {/* Step Content */}
      <div className="card animate-scaleIn" key={currentStep}>
        {/* Step 1: Select Products */}
        {currentStep === 1 && (
          <div>
            <h3 style={{ marginBottom: "var(--space-2)" }}>Select Product(s)</h3>
            <p style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-6)" }}>
              Choose which product(s) to create content for
            </p>
            {products.length > 0 ? (
              <div className="grid-auto">
                {products.map((product) => (
                  <div
                    key={product.id}
                    onClick={() => toggleProduct(product.id)}
                    style={{
                      padding: "var(--space-5)",
                      border: `2px solid ${config.selectedProducts.includes(product.id) ? "var(--accent-primary)" : "var(--border)"}`,
                      borderRadius: "var(--radius-lg)",
                      cursor: "pointer",
                      background: config.selectedProducts.includes(product.id) ? "var(--accent-primary-muted)" : "var(--bg-tertiary)",
                      transition: "all var(--transition-fast)",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                      <div>
                        <h4>{product.name}</h4>
                        <p style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)", marginTop: "var(--space-1)" }}>
                          {product.description?.slice(0, 80)}{product.description?.length > 80 ? "..." : ""}
                        </p>
                      </div>
                      <div
                        style={{
                          width: 24,
                          height: 24,
                          borderRadius: "var(--radius-full)",
                          border: `2px solid ${config.selectedProducts.includes(product.id) ? "var(--accent-primary)" : "var(--border)"}`,
                          background: config.selectedProducts.includes(product.id) ? "var(--accent-primary)" : "transparent",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          fontSize: "var(--font-xs)",
                          color: "white",
                          flexShrink: 0,
                        }}
                      >
                        {config.selectedProducts.includes(product.id) && "✓"}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state" style={{ padding: "var(--space-8) 0" }}>
                <div className="empty-state-icon">📦</div>
                <h3 className="empty-state-title">No Products Yet</h3>
                <p className="empty-state-description">
                  You need to add at least one product before generating content.
                </p>
                <a href="/products" className="btn btn-primary">
                  ➕ Add Product
                </a>
              </div>
            )}
          </div>
        )}

        {/* Step 2: LLM Provider */}
        {currentStep === 2 && (
          <div>
            <h3 style={{ marginBottom: "var(--space-2)" }}>Choose AI Provider</h3>
            <p style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-6)" }}>
              Select which AI model to use for content generation
            </p>
            <div className="grid-3">
              {Object.entries(LLM_PROVIDERS).map(([key, provider]) => (
                <div
                  key={key}
                  onClick={() => setConfig({ ...config, llmProvider: key })}
                  style={{
                    padding: "var(--space-6)",
                    border: `2px solid ${config.llmProvider === key ? provider.color : "var(--border)"}`,
                    borderRadius: "var(--radius-lg)",
                    cursor: "pointer",
                    background: config.llmProvider === key ? provider.colorMuted : "var(--bg-tertiary)",
                    transition: "all var(--transition-fast)",
                    textAlign: "center",
                  }}
                >
                  <div style={{ fontSize: "2.5rem", marginBottom: "var(--space-3)" }}>{provider.icon}</div>
                  <h4 style={{ marginBottom: "var(--space-2)" }}>{provider.name}</h4>
                  <p style={{ fontSize: "var(--font-xs)", color: "var(--text-secondary)" }}>
                    {provider.description}
                  </p>
                  <div style={{ display: "flex", justifyContent: "center", gap: "var(--space-1)", marginTop: "var(--space-3)" }}>
                    {provider.capabilities.map((cap) => (
                      <span key={cap} className="tag tag-default">{cap}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Step 3: Target Platforms */}
        {currentStep === 3 && (
          <div>
            <h3 style={{ marginBottom: "var(--space-2)" }}>Select Target Platforms</h3>
            <p style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-6)" }}>
              Where do you want to publish this content?
            </p>
            <div className="grid-2">
              {Object.entries(PLATFORMS).map(([key, platform]) => (
                <div
                  key={key}
                  onClick={() => togglePlatform(key)}
                  style={{
                    padding: "var(--space-5)",
                    border: `2px solid ${config.selectedPlatforms.includes(key) ? platform.color : "var(--border)"}`,
                    borderRadius: "var(--radius-lg)",
                    cursor: "pointer",
                    background: config.selectedPlatforms.includes(key) ? platform.colorMuted : "var(--bg-tertiary)",
                    transition: "all var(--transition-fast)",
                    display: "flex",
                    alignItems: "center",
                    gap: "var(--space-4)",
                  }}
                >
                  <span style={{ fontSize: "2rem" }}>{platform.icon}</span>
                  <div style={{ flex: 1 }}>
                    <h4>{platform.name}</h4>
                    <div style={{ display: "flex", gap: "var(--space-1)", marginTop: "var(--space-2)" }}>
                      {platform.contentTypes.map((ct) => (
                        <span key={ct} className="tag tag-default">{ct}</span>
                      ))}
                    </div>
                  </div>
                  <div
                    style={{
                      width: 24,
                      height: 24,
                      borderRadius: "var(--radius-full)",
                      border: `2px solid ${config.selectedPlatforms.includes(key) ? platform.color : "var(--border)"}`,
                      background: config.selectedPlatforms.includes(key) ? platform.color : "transparent",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "var(--font-xs)",
                      color: "white",
                      flexShrink: 0,
                    }}
                  >
                    {config.selectedPlatforms.includes(key) && "✓"}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Step 4: Content Settings */}
        {currentStep === 4 && (
          <div>
            <h3 style={{ marginBottom: "var(--space-2)" }}>Content Settings</h3>
            <p style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-6)" }}>
              Configure how your content should look and feel
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
              {/* Content Type */}
              <div className="form-group">
                <label className="form-label">Content Type</label>
                <div style={{ display: "flex", gap: "var(--space-3)" }}>
                  {Object.entries(CONTENT_TYPES).map(([key, ct]) => (
                    <button
                      key={key}
                      className={`btn ${config.contentType === key ? "btn-primary" : "btn-secondary"}`}
                      onClick={() => setConfig({ ...config, contentType: key })}
                    >
                      {ct.icon} {ct.name}
                    </button>
                  ))}
                </div>
              </div>

              <div className="form-row">
                {/* Language */}
                <div className="form-group">
                  <label className="form-label">Language</label>
                  <select
                    className="form-select"
                    value={config.language}
                    onChange={(e) => setConfig({ ...config, language: e.target.value })}
                  >
                    {LANGUAGES.map((l) => (
                      <option key={l.value} value={l.value}>{l.label}</option>
                    ))}
                  </select>
                </div>

                {/* Tone */}
                <div className="form-group">
                  <label className="form-label">Tone</label>
                  <select
                    className="form-select"
                    value={config.tone}
                    onChange={(e) => setConfig({ ...config, tone: e.target.value })}
                  >
                    {TONES.map((t) => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-row">
                {/* CTA */}
                <div className="form-group">
                  <label className="form-label">Call to Action</label>
                  <select
                    className="form-select"
                    value={config.cta}
                    onChange={(e) => setConfig({ ...config, cta: e.target.value })}
                  >
                    {CTA_OPTIONS.map((c) => (
                      <option key={c.value} value={c.value}>{c.label}</option>
                    ))}
                  </select>
                </div>

                {/* Hashtag Strategy */}
                <div className="form-group">
                  <label className="form-label">Hashtag Strategy</label>
                  <select
                    className="form-select"
                    value={config.hashtagStrategy}
                    onChange={(e) => setConfig({ ...config, hashtagStrategy: e.target.value })}
                  >
                    <option value="auto">Auto-generate</option>
                    <option value="manual">Manual</option>
                    <option value="mix">Mix (Auto + Manual)</option>
                  </select>
                </div>
              </div>

              {/* Visual Settings (for image/video/carousel) */}
              {config.contentType !== "text" && (
                <>
                  <div className="form-row">
                    {/* Aspect Ratio */}
                    <div className="form-group">
                      <label className="form-label">Aspect Ratio</label>
                      <div style={{ display: "flex", gap: "var(--space-2)" }}>
                        {Object.entries(ASPECT_RATIOS).map(([key, ar]) => (
                          <button
                            key={key}
                            className={`btn btn-sm ${config.aspectRatio === key ? "btn-primary" : "btn-secondary"}`}
                            onClick={() => setConfig({ ...config, aspectRatio: key })}
                          >
                            {ar.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Video Duration (only for video) */}
                    {config.contentType === "video" && (
                      <div className="form-group">
                        <label className="form-label">Video Duration</label>
                        <div style={{ display: "flex", gap: "var(--space-2)" }}>
                          {[15, 30, 60].map((d) => (
                            <button
                              key={d}
                              className={`btn btn-sm ${config.videoDuration === d ? "btn-primary" : "btn-secondary"}`}
                              onClick={() => setConfig({ ...config, videoDuration: d })}
                            >
                              {d}s
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Visual Style */}
                  <div className="form-group">
                    <label className="form-label">Visual Style</label>
                    <div className="grid-3">
                      {VISUAL_STYLES.map((style) => (
                        <div
                          key={style.value}
                          onClick={() => setConfig({ ...config, visualStyle: style.value })}
                          style={{
                            padding: "var(--space-4)",
                            border: `2px solid ${config.visualStyle === style.value ? "var(--accent-primary)" : "var(--border)"}`,
                            borderRadius: "var(--radius-md)",
                            cursor: "pointer",
                            background: config.visualStyle === style.value ? "var(--accent-primary-muted)" : "var(--bg-tertiary)",
                            transition: "all var(--transition-fast)",
                          }}
                        >
                          <div style={{ fontWeight: 600, fontSize: "var(--font-sm)" }}>{style.label}</div>
                          <div style={{ fontSize: "var(--font-xs)", color: "var(--text-secondary)" }}>{style.description}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {/* Custom Instructions */}
              <div className="form-group">
                <label className="form-label">Custom Instructions</label>
                <textarea
                  className="form-textarea"
                  value={config.customInstructions}
                  onChange={(e) => setConfig({ ...config, customInstructions: e.target.value })}
                  placeholder="Any additional instructions for the AI (e.g., 'focus on Diwali theme', 'mention the 50% discount')..."
                  rows={3}
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 5: Review & Generate */}
        {currentStep === 5 && (
          <div>
            <h3 style={{ marginBottom: "var(--space-2)" }}>Review & Generate</h3>
            <p style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-6)" }}>
              Review your settings and generate content
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
              {/* Summary */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "140px 1fr",
                  gap: "var(--space-3) var(--space-6)",
                  padding: "var(--space-5)",
                  background: "var(--bg-tertiary)",
                  borderRadius: "var(--radius-md)",
                }}
              >
                <span style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>Products:</span>
                <span style={{ fontSize: "var(--font-sm)", fontWeight: 600 }}>
                  {config.selectedProducts.map((id) => products.find((p) => p.id === id)?.name).join(", ")}
                </span>

                <span style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>AI Provider:</span>
                <span style={{ fontSize: "var(--font-sm)", fontWeight: 600 }}>
                  {LLM_PROVIDERS[config.llmProvider]?.icon} {LLM_PROVIDERS[config.llmProvider]?.name}
                </span>

                <span style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>Platforms:</span>
                <span style={{ fontSize: "var(--font-sm)", fontWeight: 600 }}>
                  {config.selectedPlatforms.map((p) => `${PLATFORMS[p]?.icon} ${PLATFORMS[p]?.name}`).join(", ")}
                </span>

                <span style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>Content Type:</span>
                <span style={{ fontSize: "var(--font-sm)", fontWeight: 600 }}>
                  {CONTENT_TYPES[config.contentType]?.icon} {CONTENT_TYPES[config.contentType]?.name}
                </span>

                <span style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>Language:</span>
                <span style={{ fontSize: "var(--font-sm)", fontWeight: 600, textTransform: "capitalize" }}>
                  {config.language}
                </span>

                <span style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>Tone:</span>
                <span style={{ fontSize: "var(--font-sm)", fontWeight: 600, textTransform: "capitalize" }}>
                  {config.tone}
                </span>

                {config.contentType !== "text" && (
                  <>
                    <span style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>Aspect Ratio:</span>
                    <span style={{ fontSize: "var(--font-sm)", fontWeight: 600 }}>
                      {ASPECT_RATIOS[config.aspectRatio]?.label}
                    </span>

                    <span style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>Visual Style:</span>
                    <span style={{ fontSize: "var(--font-sm)", fontWeight: 600, textTransform: "capitalize" }}>
                      {config.visualStyle}
                    </span>
                  </>
                )}
              </div>

              {/* Generate Button */}
              <button
                className="btn btn-primary btn-lg"
                onClick={handleGenerate}
                disabled={generating}
                style={{ width: "100%", marginTop: "var(--space-4)", padding: "var(--space-5)" }}
              >
                {generating ? (
                  <>
                    <span className="spinner" style={{ borderTopColor: "white" }} />
                    Generating content...
                  </>
                ) : (
                  "🚀 Generate & Send to Telegram for Approval"
                )}
              </button>

              <p style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)", textAlign: "center" }}>
                Content will be sent to your Telegram for review. Nothing is published until you approve.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Navigation Buttons */}
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: "var(--space-6)" }}>
        <button
          className="btn btn-secondary"
          onClick={() => setCurrentStep((prev) => Math.max(1, prev - 1))}
          disabled={currentStep === 1}
        >
          ← Previous
        </button>
        {currentStep < 5 && (
          <button
            className="btn btn-primary"
            onClick={() => setCurrentStep((prev) => Math.min(5, prev + 1))}
            disabled={!canProceed()}
          >
            Next →
          </button>
        )}
      </div>
    </div>
  );
}
