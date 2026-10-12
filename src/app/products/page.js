"use client";

import { useState, useEffect } from "react";
import { PRODUCT_CATEGORIES, TONES, CAMPAIGN_OBJECTIVES } from "@/lib/constants";

export default function ProductsPage() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [saving, setSaving] = useState(false);

  const emptyProduct = {
    name: "",
    description: "",
    category: "other",
    website_url: "",
    target_audience: "",
    key_benefits: [],
    brand_colors: { primary: "#7C5CFC", secondary: "#3DD6D0", accent: "#FFB347" },
    tone: "professional",
    disclaimer: "",
    custom_prompt: "",
    campaign_objectives: [],
  };

  const [form, setForm] = useState(emptyProduct);
  const [benefitInput, setBenefitInput] = useState("");

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

  async function handleSave() {
    if (!form.name.trim()) return;
    setSaving(true);

    try {
      if (editingProduct) {
        await fetch(`/api/products/${editingProduct.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(form),
        });
      } else {
        await fetch("/api/products", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(form),
        });
      }
      await fetchProducts();
      setShowForm(false);
      setEditingProduct(null);
      setForm(emptyProduct);
    } catch (error) {
      console.error("Failed to save product:", error);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id) {
    if (!confirm("Are you sure you want to delete this product?")) return;
    try {
      await fetch(`/api/products/${id}`, { method: "DELETE" });
      await fetchProducts();
    } catch (error) {
      console.error("Failed to delete product:", error);
    }
  }

  function startEdit(product) {
    setForm({
      name: product.name || "",
      description: product.description || "",
      category: product.category || "other",
      website_url: product.website_url || "",
      target_audience: product.target_audience || "",
      key_benefits: product.key_benefits || [],
      brand_colors: product.brand_colors || { primary: "#7C5CFC", secondary: "#3DD6D0", accent: "#FFB347" },
      tone: product.tone || "professional",
      disclaimer: product.disclaimer || "",
      custom_prompt: product.custom_prompt || "",
      campaign_objectives: product.campaign_objectives || [],
    });
    setEditingProduct(product);
    setShowForm(true);
  }

  function addBenefit() {
    if (benefitInput.trim()) {
      setForm((prev) => ({
        ...prev,
        key_benefits: [...prev.key_benefits, benefitInput.trim()],
      }));
      setBenefitInput("");
    }
  }

  function removeBenefit(index) {
    setForm((prev) => ({
      ...prev,
      key_benefits: prev.key_benefits.filter((_, i) => i !== index),
    }));
  }

  function toggleObjective(value) {
    setForm((prev) => ({
      ...prev,
      campaign_objectives: prev.campaign_objectives.includes(value)
        ? prev.campaign_objectives.filter((v) => v !== value)
        : [...prev.campaign_objectives, value],
    }));
  }

  if (loading) {
    return (
      <div className="loading-overlay">
        <div className="spinner" />
        <span>Loading products...</span>
      </div>
    );
  }

  return (
    <div className="animate-fadeIn">
      <div className="page-header">
        <div>
          <h1 className="page-title">Products</h1>
          <p className="page-subtitle">Manage your products, brands, and campaign objectives</p>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => {
            setForm(emptyProduct);
            setEditingProduct(null);
            setShowForm(true);
          }}
        >
          ➕ Add Product
        </button>
      </div>

      {/* Product Form Modal */}
      {showForm && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setShowForm(false)}>
          <div className="modal" style={{ maxWidth: 720, maxHeight: "90vh" }}>
            <div className="modal-header">
              <h3>{editingProduct ? "Edit Product" : "Add New Product"}</h3>
              <button className="btn btn-ghost btn-icon" onClick={() => setShowForm(false)}>✕</button>
            </div>
            <div className="modal-body" style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
              {/* Name & Category */}
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Product Name <span className="required">*</span></label>
                  <input
                    className="form-input"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    placeholder="My Amazing Product"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Category</label>
                  <select
                    className="form-select"
                    value={form.category}
                    onChange={(e) => setForm({ ...form, category: e.target.value })}
                  >
                    {PRODUCT_CATEGORIES.map((c) => (
                      <option key={c.value} value={c.value}>{c.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Description */}
              <div className="form-group">
                <label className="form-label">Description <span className="required">*</span></label>
                <textarea
                  className="form-textarea"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="Describe your product, what it does, and why people love it..."
                  rows={3}
                />
              </div>

              {/* Website & Tone */}
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Website URL</label>
                  <input
                    className="form-input"
                    type="url"
                    value={form.website_url}
                    onChange={(e) => setForm({ ...form, website_url: e.target.value })}
                    placeholder="https://example.com"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Tone of Voice <span className="required">*</span></label>
                  <select
                    className="form-select"
                    value={form.tone}
                    onChange={(e) => setForm({ ...form, tone: e.target.value })}
                  >
                    {TONES.map((t) => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Target Audience */}
              <div className="form-group">
                <label className="form-label">Target Audience <span className="required">*</span></label>
                <textarea
                  className="form-textarea"
                  value={form.target_audience}
                  onChange={(e) => setForm({ ...form, target_audience: e.target.value })}
                  placeholder="Small business owners, age 25-45, interested in growing their online presence..."
                  rows={2}
                />
              </div>

              {/* Key Benefits (Tag Input) */}
              <div className="form-group">
                <label className="form-label">Key Benefits <span className="required">*</span></label>
                <div style={{ display: "flex", gap: "var(--space-2)" }}>
                  <input
                    className="form-input"
                    value={benefitInput}
                    onChange={(e) => setBenefitInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addBenefit())}
                    placeholder="Type a benefit and press Enter"
                  />
                  <button className="btn btn-secondary" onClick={addBenefit} type="button">Add</button>
                </div>
                {form.key_benefits.length > 0 && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)", marginTop: "var(--space-2)" }}>
                    {form.key_benefits.map((benefit, i) => (
                      <span key={i} className="tag tag-primary tag-removable" onClick={() => removeBenefit(i)}>
                        {benefit} ✕
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Brand Colors */}
              <div className="form-group">
                <label className="form-label">Brand Colors</label>
                <div style={{ display: "flex", gap: "var(--space-4)" }}>
                  {["primary", "secondary", "accent"].map((colorKey) => (
                    <div key={colorKey} style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                      <input
                        type="color"
                        value={form.brand_colors[colorKey] || "#7C5CFC"}
                        onChange={(e) =>
                          setForm({
                            ...form,
                            brand_colors: { ...form.brand_colors, [colorKey]: e.target.value },
                          })
                        }
                        style={{
                          width: 36,
                          height: 36,
                          border: "none",
                          borderRadius: "var(--radius-sm)",
                          cursor: "pointer",
                          background: "transparent",
                        }}
                      />
                      <span style={{ fontSize: "var(--font-xs)", color: "var(--text-secondary)", textTransform: "capitalize" }}>
                        {colorKey}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Campaign Objectives */}
              <div className="form-group">
                <label className="form-label">Campaign Objectives</label>
                <div className="checkbox-group">
                  {CAMPAIGN_OBJECTIVES.map((obj) => (
                    <label
                      key={obj.value}
                      className={`checkbox-label ${form.campaign_objectives.includes(obj.value) ? "checked" : ""}`}
                    >
                      <input
                        type="checkbox"
                        checked={form.campaign_objectives.includes(obj.value)}
                        onChange={() => toggleObjective(obj.value)}
                      />
                      <span className="checkbox-indicator">
                        {form.campaign_objectives.includes(obj.value) && "✓"}
                      </span>
                      {obj.label}
                    </label>
                  ))}
                </div>
              </div>

              {/* Disclaimer */}
              <div className="form-group">
                <label className="form-label">Disclaimer Text</label>
                <textarea
                  className="form-textarea"
                  value={form.disclaimer}
                  onChange={(e) => setForm({ ...form, disclaimer: e.target.value })}
                  placeholder="Terms and conditions apply. Subject to approval..."
                  rows={2}
                />
              </div>

              {/* Custom Prompt */}
              <div className="form-group">
                <label className="form-label">Custom Prompt Template</label>
                <textarea
                  className="form-textarea"
                  value={form.custom_prompt}
                  onChange={(e) => setForm({ ...form, custom_prompt: e.target.value })}
                  placeholder="Additional instructions for AI when generating content for this product..."
                  rows={3}
                />
                <span className="form-help">This will be appended to the default AI prompt when generating content for this product.</span>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-ghost" onClick={() => setShowForm(false)}>Cancel</button>
              <button className="btn btn-primary" onClick={handleSave} disabled={saving || !form.name.trim()}>
                {saving ? "Saving..." : editingProduct ? "Update Product" : "Create Product"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Product Cards Grid */}
      {products.length > 0 ? (
        <div className="grid-auto">
          {products.map((product) => (
            <div className="card" key={product.id} style={{ display: "flex", flexDirection: "column" }}>
              {/* Card Header with color bar */}
              <div
                style={{
                  height: 4,
                  borderRadius: "var(--radius-lg) var(--radius-lg) 0 0",
                  background: `linear-gradient(90deg, ${product.brand_colors?.primary || "#7C5CFC"}, ${product.brand_colors?.secondary || "#3DD6D0"})`,
                  margin: "calc(-1 * var(--space-6)) calc(-1 * var(--space-6)) var(--space-4)",
                }}
              />

              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "var(--space-3)" }}>
                <div>
                  <h4 style={{ marginBottom: "var(--space-1)" }}>{product.name}</h4>
                  <span className="tag tag-default" style={{ fontSize: "var(--font-xs)" }}>
                    {PRODUCT_CATEGORIES.find((c) => c.value === product.category)?.label || product.category}
                  </span>
                </div>
                {product.logo_path && (
                  <img
                    src={product.logo_path}
                    alt={product.name}
                    style={{ width: 40, height: 40, borderRadius: "var(--radius-sm)", objectFit: "cover" }}
                  />
                )}
              </div>

              <p style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-3)", flex: 1 }}>
                {product.description?.slice(0, 120)}{product.description?.length > 120 ? "..." : ""}
              </p>

              {/* Benefits */}
              {product.key_benefits?.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-1)", marginBottom: "var(--space-4)" }}>
                  {product.key_benefits.slice(0, 3).map((b, i) => (
                    <span key={i} className="tag tag-primary">{b}</span>
                  ))}
                  {product.key_benefits.length > 3 && (
                    <span className="tag tag-default">+{product.key_benefits.length - 3}</span>
                  )}
                </div>
              )}

              {/* Tone badge */}
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", marginBottom: "var(--space-4)" }}>
                <span style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)" }}>Tone:</span>
                <span className="tag tag-default" style={{ textTransform: "capitalize" }}>{product.tone}</span>
              </div>

              {/* Actions */}
              <div style={{ display: "flex", gap: "var(--space-2)", borderTop: "1px solid var(--border)", paddingTop: "var(--space-4)" }}>
                <button className="btn btn-secondary btn-sm" style={{ flex: 1 }} onClick={() => startEdit(product)}>
                  ✏️ Edit
                </button>
                <button className="btn btn-danger btn-sm" onClick={() => handleDelete(product.id)}>
                  🗑️
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">📦</div>
            <h3 className="empty-state-title">No Products Yet</h3>
            <p className="empty-state-description">
              Add your first product to start generating AI-powered social media content.
            </p>
            <button className="btn btn-primary" onClick={() => { setForm(emptyProduct); setShowForm(true); }}>
              ➕ Add Your First Product
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
