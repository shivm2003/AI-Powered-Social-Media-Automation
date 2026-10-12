import Database from "better-sqlite3";
import path from "path";
import fs from "fs";

// Ensure data directory exists
const dataDir = path.join(process.cwd(), "data");
if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir, { recursive: true });
}

const dbPath = path.join(dataDir, "database.sqlite");

let db;

function getDb() {
  if (!db) {
    db = new Database(dbPath);
    db.pragma("journal_mode = WAL");
    db.pragma("foreign_keys = ON");
    initializeDatabase(db);
  }
  return db;
}

function initializeDatabase(database) {
  database.exec(`
    -- Products table
    CREATE TABLE IF NOT EXISTS products (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      description TEXT,
      category TEXT DEFAULT 'other',
      website_url TEXT,
      logo_path TEXT,
      target_audience TEXT,
      key_benefits TEXT DEFAULT '[]',
      brand_colors TEXT DEFAULT '{"primary":"#7C5CFC","secondary":"#3DD6D0","accent":"#FFB347"}',
      tone TEXT DEFAULT 'professional',
      disclaimer TEXT,
      custom_prompt TEXT,
      campaign_objectives TEXT DEFAULT '[]',
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    );

    -- Product images
    CREATE TABLE IF NOT EXISTS product_images (
      id TEXT PRIMARY KEY,
      product_id TEXT NOT NULL,
      file_path TEXT NOT NULL,
      file_name TEXT,
      created_at TEXT DEFAULT (datetime('now')),
      FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
    );

    -- Social accounts
    CREATE TABLE IF NOT EXISTS social_accounts (
      id TEXT PRIMARY KEY,
      platform TEXT NOT NULL,
      username TEXT,
      encrypted_password TEXT,
      extra_fields TEXT DEFAULT '{}',
      chrome_profile_path TEXT,
      session_status TEXT DEFAULT 'unverified',
      last_verified TEXT,
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    );

    -- Campaigns
    CREATE TABLE IF NOT EXISTS campaigns (
      id TEXT PRIMARY KEY,
      product_id TEXT,
      llm_provider TEXT,
      content_type TEXT DEFAULT 'text',
      language TEXT DEFAULT 'english',
      platforms TEXT DEFAULT '[]',
      audience TEXT,
      tone TEXT,
      cta TEXT,
      hashtags TEXT,
      aspect_ratio TEXT DEFAULT '1:1',
      video_duration INTEGER DEFAULT 15,
      visual_style TEXT DEFAULT 'minimal',
      custom_instructions TEXT,
      generated_caption TEXT,
      generated_hashtags TEXT,
      media_paths TEXT DEFAULT '[]',
      status TEXT DEFAULT 'draft',
      telegram_message_id TEXT,
      revision_notes TEXT,
      revision_count INTEGER DEFAULT 0,
      posted_at TEXT,
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now')),
      FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
    );

    -- Settings
    CREATE TABLE IF NOT EXISTS settings (
      key TEXT PRIMARY KEY,
      value TEXT
    );

    -- Insert default settings if not exists
    INSERT OR IGNORE INTO settings (key, value) VALUES ('llm_provider', 'gemini');
    INSERT OR IGNORE INTO settings (key, value) VALUES ('telegram_bot_token', '');
    INSERT OR IGNORE INTO settings (key, value) VALUES ('telegram_chat_id', '');
    INSERT OR IGNORE INTO settings (key, value) VALUES ('default_language', 'english');
    INSERT OR IGNORE INTO settings (key, value) VALUES ('default_tone', 'professional');
  `);
}

// ── Product Queries ──

export function getAllProducts() {
  return getDb().prepare("SELECT * FROM products ORDER BY created_at DESC").all();
}

export function getProductById(id) {
  return getDb().prepare("SELECT * FROM products WHERE id = ?").get(id);
}

export function createProduct(product) {
  const stmt = getDb().prepare(`
    INSERT INTO products (id, name, description, category, website_url, logo_path, target_audience, key_benefits, brand_colors, tone, disclaimer, custom_prompt, campaign_objectives)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);
  return stmt.run(
    product.id,
    product.name,
    product.description || null,
    product.category || "other",
    product.website_url || null,
    product.logo_path || null,
    product.target_audience || null,
    JSON.stringify(product.key_benefits || []),
    JSON.stringify(product.brand_colors || { primary: "#7C5CFC", secondary: "#3DD6D0", accent: "#FFB347" }),
    product.tone || "professional",
    product.disclaimer || null,
    product.custom_prompt || null,
    JSON.stringify(product.campaign_objectives || [])
  );
}

export function updateProduct(id, product) {
  const stmt = getDb().prepare(`
    UPDATE products SET
      name = ?, description = ?, category = ?, website_url = ?,
      target_audience = ?, key_benefits = ?, brand_colors = ?,
      tone = ?, disclaimer = ?, custom_prompt = ?, campaign_objectives = ?,
      updated_at = datetime('now')
    WHERE id = ?
  `);
  return stmt.run(
    product.name,
    product.description || null,
    product.category || "other",
    product.website_url || null,
    product.target_audience || null,
    JSON.stringify(product.key_benefits || []),
    JSON.stringify(product.brand_colors || {}),
    product.tone || "professional",
    product.disclaimer || null,
    product.custom_prompt || null,
    JSON.stringify(product.campaign_objectives || []),
    id
  );
}

export function deleteProduct(id) {
  return getDb().prepare("DELETE FROM products WHERE id = ?").run(id);
}

export function updateProductLogo(id, logoPath) {
  return getDb().prepare("UPDATE products SET logo_path = ?, updated_at = datetime('now') WHERE id = ?").run(logoPath, id);
}

// ── Social Account Queries ──

export function getAllAccounts() {
  return getDb().prepare("SELECT * FROM social_accounts ORDER BY platform, created_at").all();
}

export function getAccountById(id) {
  return getDb().prepare("SELECT * FROM social_accounts WHERE id = ?").get(id);
}

export function getAccountByPlatform(platform) {
  return getDb().prepare("SELECT * FROM social_accounts WHERE platform = ?").get(platform);
}

export function upsertAccount(account) {
  const existing = getAccountByPlatform(account.platform);
  if (existing) {
    const stmt = getDb().prepare(`
      UPDATE social_accounts SET
        username = ?, encrypted_password = ?, extra_fields = ?,
        session_status = ?, updated_at = datetime('now')
      WHERE platform = ?
    `);
    return stmt.run(
      account.username || null,
      account.encrypted_password || null,
      JSON.stringify(account.extra_fields || {}),
      account.session_status || "unverified",
      account.platform
    );
  } else {
    const stmt = getDb().prepare(`
      INSERT INTO social_accounts (id, platform, username, encrypted_password, extra_fields, session_status)
      VALUES (?, ?, ?, ?, ?, ?)
    `);
    return stmt.run(
      account.id,
      account.platform,
      account.username || null,
      account.encrypted_password || null,
      JSON.stringify(account.extra_fields || {}),
      account.session_status || "unverified"
    );
  }
}

export function deleteAccount(id) {
  return getDb().prepare("DELETE FROM social_accounts WHERE id = ?").run(id);
}

export function updateAccountStatus(id, status) {
  return getDb().prepare(
    "UPDATE social_accounts SET session_status = ?, last_verified = datetime('now'), updated_at = datetime('now') WHERE id = ?"
  ).run(status, id);
}

// ── Campaign Queries ──

export function getAllCampaigns() {
  return getDb().prepare(`
    SELECT c.*, p.name as product_name
    FROM campaigns c
    LEFT JOIN products p ON c.product_id = p.id
    ORDER BY c.created_at DESC
  `).all();
}

export function getCampaignById(id) {
  return getDb().prepare(`
    SELECT c.*, p.name as product_name
    FROM campaigns c
    LEFT JOIN products p ON c.product_id = p.id
    WHERE c.id = ?
  `).get(id);
}

export function createCampaign(campaign) {
  const stmt = getDb().prepare(`
    INSERT INTO campaigns (id, product_id, llm_provider, content_type, language, platforms, audience, tone, cta, hashtags, aspect_ratio, video_duration, visual_style, custom_instructions, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);
  return stmt.run(
    campaign.id,
    campaign.product_id || null,
    campaign.llm_provider || "gemini",
    campaign.content_type || "text",
    campaign.language || "english",
    JSON.stringify(campaign.platforms || []),
    campaign.audience || null,
    campaign.tone || "professional",
    campaign.cta || null,
    campaign.hashtags || null,
    campaign.aspect_ratio || "1:1",
    campaign.video_duration || 15,
    campaign.visual_style || "minimal",
    campaign.custom_instructions || null,
    campaign.status || "draft"
  );
}

export function updateCampaignStatus(id, status, extra = {}) {
  let sql = "UPDATE campaigns SET status = ?, updated_at = datetime('now')";
  const params = [status];

  if (extra.generated_caption) {
    sql += ", generated_caption = ?";
    params.push(extra.generated_caption);
  }
  if (extra.generated_hashtags) {
    sql += ", generated_hashtags = ?";
    params.push(extra.generated_hashtags);
  }
  if (extra.media_paths) {
    sql += ", media_paths = ?";
    params.push(JSON.stringify(extra.media_paths));
  }
  if (extra.telegram_message_id) {
    sql += ", telegram_message_id = ?";
    params.push(extra.telegram_message_id);
  }
  if (extra.revision_notes) {
    sql += ", revision_notes = ?, revision_count = revision_count + 1";
    params.push(extra.revision_notes);
  }
  if (status === "posted") {
    sql += ", posted_at = datetime('now')";
  }

  sql += " WHERE id = ?";
  params.push(id);

  return getDb().prepare(sql).run(...params);
}

export function deleteCampaign(id) {
  return getDb().prepare("DELETE FROM campaigns WHERE id = ?").run(id);
}

// ── Settings Queries ──

export function getAllSettings() {
  const rows = getDb().prepare("SELECT * FROM settings").all();
  const settings = {};
  rows.forEach((row) => {
    settings[row.key] = row.value;
  });
  return settings;
}

export function getSetting(key) {
  const row = getDb().prepare("SELECT value FROM settings WHERE key = ?").get(key);
  return row ? row.value : null;
}

export function setSetting(key, value) {
  return getDb().prepare("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)").run(key, value);
}

// ── Stats ──

export function getDashboardStats() {
  const db = getDb();
  const productCount = db.prepare("SELECT COUNT(*) as count FROM products").get().count;
  const accountCount = db.prepare("SELECT COUNT(*) as count FROM social_accounts WHERE session_status = 'verified'").get().count;
  const campaignCount = db.prepare("SELECT COUNT(*) as count FROM campaigns").get().count;
  const postedCount = db.prepare("SELECT COUNT(*) as count FROM campaigns WHERE status = 'posted'").get().count;
  const pendingCount = db.prepare("SELECT COUNT(*) as count FROM campaigns WHERE status IN ('preview_sent', 'generating')").get().count;

  const recentCampaigns = db.prepare(`
    SELECT c.*, p.name as product_name
    FROM campaigns c
    LEFT JOIN products p ON c.product_id = p.id
    ORDER BY c.updated_at DESC
    LIMIT 10
  `).all();

  return {
    productCount,
    accountCount,
    campaignCount,
    postedCount,
    pendingCount,
    recentCampaigns,
  };
}
