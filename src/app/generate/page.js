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
    llmProvider: "chatgpt",
    selectedPlatforms: [],
    contentType: "image",
    language: "english",
    tone: "professional",
    cta: "learn_more",
    hashtagStrategy: "auto",
    aspectRatio: "1:1",
    videoDuration: 15,
    visualStyle: "auto",
    customInstructions: "",
    skillImagePath: "",
    skillImageUrl: "",
    skillImageName: "",
  });

  const [uploadingSkillImage, setUploadingSkillImage] = useState(false);

  async function handleSkillImageUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    setUploadingSkillImage(true);
    try {
      const res = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (res.ok && data.filePath) {
        setConfig((prev) => ({
          ...prev,
          skillImagePath: data.filePath,
          skillImageUrl: data.fileUrl,
          skillImageName: file.name,
        }));
      } else {
        alert(`Upload failed: ${data.error || "Unknown error"}`);
      }
    } catch (err) {
      alert(`Upload error: ${err.message}`);
    } finally {
      setUploadingSkillImage(false);
    }
  }

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

  const [generateStatus, setGenerateStatus] = useState("");
  const [generatedCampaign, setGeneratedCampaign] = useState(null);
  const [humanFlowActive, setHumanFlowActive] = useState(true);
  const [humanCurrentStep, setHumanCurrentStep] = useState(1);
  const [humanLogs, setHumanLogs] = useState([]);
  const [telegramDispatched, setTelegramDispatched] = useState(false);

  async function handleGenerate() {
    setGenerating(true);
    setGeneratedCampaign(null);
    setTelegramDispatched(false);
    setHumanCurrentStep(1);

    const providerLabel = LLM_PROVIDERS[config.llmProvider]?.name || config.llmProvider.toUpperCase();

    setHumanLogs([
      `🌐 Step 1: Launching Google Chrome like a human with Shivam Mishra's profile...`,
    ]);
    setGenerateStatus(`🌐 Step 1: Launching Chrome like a human with profile 2003shivam1990@gmail.com...`);

    const timer1 = setTimeout(() => {
      setHumanCurrentStep(2);
      setHumanLogs((prev) => [
        ...prev,
        `👤 Step 2: Selecting / verifying account: Shivam Mishra (2003shivam1990@gmail.com)...`,
      ]);
      setGenerateStatus(`👤 Step 2: Selecting account: Shivam Mishra...`);
    }, 2800);

    const timer2 = setTimeout(() => {
      setHumanCurrentStep(3);
      setHumanLogs((prev) => [
        ...prev,
        `💬 Step 3: Navigating to ${providerLabel} & typing prompt with human cadence...`,
      ]);
      setGenerateStatus(`💬 Step 3: Navigating to ${providerLabel} & human-typing prompt...`);
    }, 6500);

    const timer3 = setTimeout(() => {
      setHumanCurrentStep(4);
      setHumanLogs((prev) => [
        ...prev,
        `🎨 Step 4: AI generating marketing copy & synthesizing branded graphic asset...`,
      ]);
      setGenerateStatus(`🎨 Step 4: Generating marketing copy & visual assets...`);
    }, 13000);

    const timer4 = setTimeout(() => {
      setHumanCurrentStep(5);
      setHumanLogs((prev) => [
        ...prev,
        `📱 Step 5: Dispatching preview to Telegram bot for review & approval...`,
      ]);
      setGenerateStatus(`📱 Step 5: Dispatching preview to Telegram...`);
    }, 20000);

    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...config,
          humanFlow: humanFlowActive,
        }),
      });

      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      clearTimeout(timer4);

      const data = await res.json();
      if (res.ok && data.campaign) {
        setHumanCurrentStep(5);
        setGeneratedCampaign(data.campaign);
        setTelegramDispatched(!!data.telegramDispatched);
        if (data.logs && Array.isArray(data.logs)) {
          setHumanLogs(data.logs);
        } else {
          setHumanLogs((prev) => [
            ...prev,
            `✅ Flow completed successfully! Dispatched to Telegram.`,
          ]);
        }
        setGenerateStatus(
          data.telegramDispatched
            ? "✅ Success! Dispatched to Telegram with interactive Approve/Reject buttons."
            : "✅ Success! Content and branded graphic created successfully."
        );
      } else {
        setGenerateStatus("");
        alert(`Error: ${data.error || "Failed to generate content"}`);
      }
    } catch (err) {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      clearTimeout(timer4);
      console.error("Generation error:", err);
      setGenerateStatus("");
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

                  {/* Visual Style & Template Archetype */}
                  <div className="form-group">
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--space-2)" }}>
                      <label className="form-label" style={{ margin: 0 }}>Design Template & Creative Style</label>
                      <span style={{ fontSize: "var(--font-xs)", color: "var(--accent-primary)", fontWeight: 600 }}>
                        ✨ 50,000+ Combinatorial Variations
                      </span>
                    </div>
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

                  {/* ── Skill / Product Reference Image Selection ── */}
                  <div className="form-group" style={{ marginTop: "var(--space-4)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--space-2)" }}>
                      <label className="form-label" style={{ margin: 0 }}>
                        🎯 Skill / Product Reference Image
                      </label>
                      <span style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)" }}>
                        ChatGPT will use this as visual inspiration & branding
                      </span>
                    </div>

                    {config.skillImageUrl ? (
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "var(--space-4)",
                          padding: "var(--space-3)",
                          background: "var(--bg-tertiary)",
                          border: "1px solid var(--accent-primary)",
                          borderRadius: "var(--radius-md)",
                        }}
                      >
                        <img
                          src={config.skillImageUrl}
                          alt="Skill reference"
                          style={{ width: 64, height: 64, objectFit: "cover", borderRadius: "var(--radius-sm)" }}
                        />
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: "var(--font-sm)", fontWeight: 600, color: "var(--text-primary)" }}>
                            {config.skillImageName || "Skill Reference Image"}
                          </div>
                          <div style={{ fontSize: "var(--font-xs)", color: "var(--success)", display: "flex", alignItems: "center", gap: 4 }}>
                            <span>✓</span> Image attached for ChatGPT generation
                          </div>
                        </div>
                        <button
                          type="button"
                          className="btn btn-ghost btn-sm"
                          style={{ color: "var(--danger)" }}
                          onClick={() => setConfig((prev) => ({ ...prev, skillImagePath: "", skillImageUrl: "", skillImageName: "" }))}
                        >
                          ✕ Remove
                        </button>
                      </div>
                    ) : (
                      <div>
                        <label
                          style={{
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "center",
                            justifyContent: "center",
                            padding: "var(--space-5)",
                            border: "2px dashed var(--border)",
                            borderRadius: "var(--radius-md)",
                            background: "var(--bg-tertiary)",
                            cursor: "pointer",
                            transition: "all var(--transition-fast)",
                          }}
                        >
                          <input
                            type="file"
                            accept="image/*"
                            style={{ display: "none" }}
                            onChange={handleSkillImageUpload}
                            disabled={uploadingSkillImage}
                          />
                          <span style={{ fontSize: "1.75rem", marginBottom: "var(--space-2)" }}>
                            {uploadingSkillImage ? "⏳" : "🖼️"}
                          </span>
                          <span style={{ fontSize: "var(--font-sm)", fontWeight: 600, color: "var(--accent-primary)" }}>
                            {uploadingSkillImage ? "Uploading Skill Image..." : "Click to Upload Skill / Product Image"}
                          </span>
                          <span style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)", marginTop: 4 }}>
                            PNG, JPG, WEBP up to 10MB
                          </span>
                        </label>
                      </div>
                    )}
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

                    {config.skillImageName && (
                      <>
                        <span style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>Skill Image:</span>
                        <span style={{ fontSize: "var(--font-sm)", fontWeight: 600, color: "var(--accent-primary)" }}>
                          🎯 {config.skillImageName}
                        </span>
                      </>
                    )}
                  </>
                )}
              </div>

              {/* Human Flow Mode Selector */}
              <div
                style={{
                  padding: "var(--space-4)",
                  background: humanFlowActive ? "rgba(124, 92, 252, 0.08)" : "var(--bg-tertiary)",
                  border: `1px solid ${humanFlowActive ? "rgba(124, 92, 252, 0.4)" : "var(--border)"}`,
                  borderRadius: "var(--radius-lg)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: "var(--space-4)",
                  flexWrap: "wrap",
                }}
              >
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                    <span style={{ fontSize: "1.2rem" }}>🚀</span>
                    <strong style={{ fontSize: "var(--font-sm)", color: "var(--text-primary)" }}>
                      Execute Human Flow Workflow
                    </strong>
                    <span className="tag tag-success" style={{ fontSize: "0.65rem" }}>
                      Active
                    </span>
                  </div>
                  <p style={{ fontSize: "var(--font-xs)", color: "var(--text-secondary)", marginTop: 4, margin: 0 }}>
                    Opens visible Chrome ➜ Selects Shivam Mishra (2003shivam1990@gmail.com) ➜ Types prompt with human pauses ➜ AI creates creative copy & graphic ➜ Sends to Telegram for phone approval!
                  </p>
                </div>
                <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={humanFlowActive}
                    onChange={(e) => setHumanFlowActive(e.target.checked)}
                    style={{ width: 18, height: 18, accentColor: "var(--accent-primary)", cursor: "pointer" }}
                  />
                  <span style={{ fontSize: "var(--font-xs)", fontWeight: 600 }}>
                    {humanFlowActive ? "Human Flow ON" : "Instant API Engine"}
                  </span>
                </label>
              </div>

              {/* Live Human Flow Execution Stepper */}
              {generating && (
                <div
                  className="animate-fadeIn"
                  style={{
                    padding: "var(--space-4)",
                    background: "rgba(15, 17, 26, 0.8)",
                    border: "1px solid rgba(124, 92, 252, 0.35)",
                    borderRadius: "var(--radius-lg)",
                    boxShadow: "0 8px 32px rgba(0, 0, 0, 0.4)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "var(--space-3)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                      <span className="spinner" style={{ width: 16, height: 16, borderTopColor: "var(--accent-primary)" }} />
                      <strong style={{ fontSize: "var(--font-sm)", color: "var(--primary-light)" }}>
                        Human Flow In Progress: Step {humanCurrentStep} of 5
                      </strong>
                    </div>
                    <span style={{ fontSize: "var(--font-xs)", color: "var(--accent-secondary)", animation: "pulse 1.5s infinite" }}>
                      ● Active Chrome Automation
                    </span>
                  </div>

                  {/* Visual 5-Step Pipeline */}
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "var(--space-2)", marginBottom: "var(--space-3)" }}>
                    {[
                      { n: 1, label: "Open Chrome", icon: "🌐" },
                      { n: 2, label: "Select Shivam", icon: "👤" },
                      { n: 3, label: `Type in ${config.llmProvider.toUpperCase()}`, icon: "💬" },
                      { n: 4, label: "Generate Graphic", icon: "🎨" },
                      { n: 5, label: "Telegram Dispatch", icon: "📱" },
                    ].map((st) => {
                      const isActive = humanCurrentStep === st.n;
                      const isDone = humanCurrentStep > st.n;
                      return (
                        <div
                          key={st.n}
                          style={{
                            padding: "8px 6px",
                            borderRadius: "var(--radius-md)",
                            background: isActive
                              ? "rgba(124, 92, 252, 0.25)"
                              : isDone
                              ? "rgba(16, 185, 129, 0.2)"
                              : "var(--bg-tertiary)",
                            border: `1px solid ${isActive ? "var(--primary-light)" : isDone ? "var(--success)" : "var(--border)"}`,
                            textAlign: "center",
                            transition: "all var(--transition-fast)",
                          }}
                        >
                          <div style={{ fontSize: "1.1rem" }}>{isDone ? "✓" : st.icon}</div>
                          <div
                            style={{
                              fontSize: "0.68rem",
                              fontWeight: 600,
                              marginTop: 2,
                              color: isActive ? "var(--primary-light)" : isDone ? "var(--success)" : "var(--text-tertiary)",
                              whiteSpace: "nowrap",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                            }}
                          >
                            {st.label}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Terminal Log Console */}
                  <div
                    style={{
                      background: "#08090E",
                      borderRadius: "var(--radius-md)",
                      padding: "10px 12px",
                      fontFamily: "monospace",
                      fontSize: "0.75rem",
                      color: "#3DD6D0",
                      maxHeight: 120,
                      overflowY: "auto",
                      border: "1px solid rgba(255, 255, 255, 0.08)",
                      lineHeight: 1.5,
                    }}
                  >
                    {humanLogs.map((log, idx) => (
                      <div key={idx} style={{ marginBottom: 2 }}>
                        ➜ {log}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Generate Button */}
              <button
                className="btn btn-primary btn-lg"
                onClick={handleGenerate}
                disabled={generating}
                style={{ width: "100%", marginTop: "var(--space-2)", padding: "var(--space-5)" }}
              >
                {generating ? (
                  <>
                    <span className="spinner" style={{ borderTopColor: "white" }} />
                    {generateStatus || "Executing Human Flow & Generating..."}
                  </>
                ) : (
                  "🚀 Generate & Send to Telegram for Approval"
                )}
              </button>

              {generateStatus && (
                <div
                  style={{
                    marginTop: "var(--space-2)",
                    padding: "var(--space-2) var(--space-3)",
                    background: "rgba(124, 92, 252, 0.1)",
                    border: "1px solid rgba(124, 92, 252, 0.25)",
                    borderRadius: "var(--radius-md)",
                    fontSize: "var(--font-xs)",
                    textAlign: "center",
                    color: "var(--primary-light)",
                    fontWeight: 600,
                  }}
                >
                  {generateStatus}
                </div>
              )}

              <p style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)", textAlign: "center" }}>
                Content will be sent to your Telegram for review. Nothing is published until you approve.
              </p>

              {/* ── Generated Content & Graphic Preview ── */}
              {generatedCampaign && (
                <div
                  className="card animate-fadeIn"
                  style={{
                    marginTop: "var(--space-5)",
                    border: "1px solid rgba(16, 185, 129, 0.4)",
                    background: "linear-gradient(180deg, rgba(16, 185, 129, 0.08) 0%, var(--bg-tertiary) 100%)",
                    boxShadow: "0 12px 32px rgba(0, 0, 0, 0.3)",
                    textAlign: "left",
                  }}
                >
                  {/* Telegram Notification Banner */}
                  {telegramDispatched && (
                    <div
                      style={{
                        padding: "var(--space-3) var(--space-4)",
                        background: "rgba(59, 130, 246, 0.15)",
                        border: "1px solid rgba(59, 130, 246, 0.4)",
                        borderRadius: "var(--radius-md)",
                        marginBottom: "var(--space-4)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: "var(--space-3)",
                        flexWrap: "wrap",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                        <span style={{ fontSize: "1.3rem" }}>📱</span>
                        <div>
                          <strong style={{ fontSize: "var(--font-sm)", color: "#60A5FA" }}>
                            Preview Sent to Telegram!
                          </strong>
                          <p style={{ margin: 0, fontSize: "var(--font-xs)", color: "var(--text-secondary)" }}>
                            Check your Telegram on your phone. Tap <b>✅ Approve & Post</b> to publish to your social accounts.
                          </p>
                        </div>
                      </div>
                      <span className="tag tag-success" style={{ fontWeight: 600 }}>
                        ● Awaiting Approval
                      </span>
                    </div>
                  )}

                  <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", marginBottom: "var(--space-4)" }}>
                    <span style={{ fontSize: "1.4rem" }}>🎉</span>
                    <h3 style={{ margin: 0, fontSize: "var(--font-lg)" }}>Generated Content & Graphic Ready!</h3>
                  </div>

                  {/* Media Graphic Preview */}
                  {(() => {
                    let mediaArr = [];
                    try {
                      mediaArr = Array.isArray(generatedCampaign.media_paths)
                        ? generatedCampaign.media_paths
                        : JSON.parse(generatedCampaign.media_paths || "[]");
                    } catch {}
                    const firstMedia = mediaArr[0];
                    const filename = firstMedia ? firstMedia.split(/[/\\]/).pop() : null;
                    const mediaUrl = filename ? `/api/media?file=${encodeURIComponent(filename)}` : null;

                    if (!mediaUrl) return null;

                    return (
                      <div style={{ marginBottom: "var(--space-4)", display: "flex", justifyContent: "center" }}>
                        <div
                          style={{
                            maxWidth: 360,
                            width: "100%",
                            borderRadius: "var(--radius-lg)",
                            overflow: "hidden",
                            border: "1px solid var(--border)",
                            boxShadow: "0 8px 24px rgba(0,0,0,0.5)",
                            background: "#0d0f17",
                          }}
                        >
                          <img
                            src={mediaUrl}
                            alt="Generated Graphic"
                            style={{ width: "100%", height: "auto", display: "block" }}
                          />
                        </div>
                      </div>
                    );
                  })()}

                  {/* Caption */}
                  {generatedCampaign.generated_caption && (
                    <div
                      style={{
                        padding: "var(--space-3)",
                        background: "var(--bg-secondary)",
                        borderRadius: "var(--radius-md)",
                        fontSize: "var(--font-sm)",
                        whiteSpace: "pre-line",
                        lineHeight: 1.6,
                        borderLeft: "3px solid var(--accent-primary)",
                        marginBottom: "var(--space-4)",
                      }}
                    >
                      {generatedCampaign.generated_caption}
                    </div>
                  )}

                  {/* Action Buttons */}
                  <div style={{ display: "flex", gap: "var(--space-3)", flexWrap: "wrap" }}>
                    <a href="/campaigns" className="btn btn-primary" style={{ flex: 1, textAlign: "center" }}>
                      🚀 View in Campaigns
                    </a>
                    <button
                      onClick={() => {
                        setGeneratedCampaign(null);
                        setGenerateStatus("");
                      }}
                      className="btn btn-secondary"
                    >
                      ✨ Generate Another
                    </button>
                  </div>
                </div>
              )}
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
