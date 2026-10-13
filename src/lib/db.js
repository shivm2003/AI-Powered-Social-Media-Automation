import { Pool } from "pg";

let pool;

function getPool() {
  if (!globalThis.__pgPool) {
    globalThis.__pgPool = new Pool({
      user: process.env.DB_USER || "postgres",
      password: process.env.DB_PASSWORD || "Shivam@123",
      host: process.env.DB_HOST || "localhost",
      port: parseInt(process.env.DB_PORT || "5432", 10),
      database: process.env.DB_NAME || "Social_Media",
      max: 10,
      idleTimeoutMillis: 30000,
    });

    // Run table initialization once
    initializeDatabase(globalThis.__pgPool).catch((err) => {
      console.error("PostgreSQL database initialization warning:", err.message);
    });
  }
  return globalThis.__pgPool;
}

pool = getPool();

async function query(text, params = []) {
  const client = getPool();
  return client.query(text, params);
}

async function initializeDatabase(client) {
  await client.query(`
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
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS product_images (
      id TEXT PRIMARY KEY,
      product_id TEXT NOT NULL,
      file_path TEXT NOT NULL,
      file_name TEXT,
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS social_accounts (
      id TEXT PRIMARY KEY,
      platform TEXT NOT NULL,
      username TEXT,
      encrypted_password TEXT,
      extra_fields TEXT DEFAULT '{}',
      chrome_profile_path TEXT,
      session_status TEXT DEFAULT 'unverified',
      last_verified TIMESTAMP WITH TIME ZONE,
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

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
      posted_at TIMESTAMP WITH TIME ZONE,
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS settings (
      key TEXT PRIMARY KEY,
      value TEXT
    );

    INSERT INTO settings (key, value) VALUES ('llm_provider', 'gemini') ON CONFLICT (key) DO NOTHING;
    INSERT INTO settings (key, value) VALUES ('telegram_bot_token', '') ON CONFLICT (key) DO NOTHING;
    INSERT INTO settings (key, value) VALUES ('telegram_chat_id', '') ON CONFLICT (key) DO NOTHING;
    INSERT INTO settings (key, value) VALUES ('default_language', 'english') ON CONFLICT (key) DO NOTHING;
    INSERT INTO settings (key, value) VALUES ('default_tone', 'professional') ON CONFLICT (key) DO NOTHING;
  `);
}

// ── Product Queries ──

export async function getAllProducts() {
  const { rows } = await query("SELECT * FROM products ORDER BY created_at DESC");
  return rows;
}

export async function getProductById(id) {
  const { rows } = await query("SELECT * FROM products WHERE id = $1", [id]);
  return rows[0] || null;
}

export async function createProduct(product) {
  const sql = `
    INSERT INTO products (
      id, name, description, category, website_url, logo_path,
      target_audience, key_benefits, brand_colors, tone,
      disclaimer, custom_prompt, campaign_objectives
    )
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
  `;
  return query(sql, [
    product.id,
    product.name,
    product.description || null,
    product.category || "other",
    product.website_url || null,
    product.logo_path || null,
    product.target_audience || null,
    typeof product.key_benefits === "string" ? product.key_benefits : JSON.stringify(product.key_benefits || []),
    typeof product.brand_colors === "string" ? product.brand_colors : JSON.stringify(product.brand_colors || { primary: "#7C5CFC", secondary: "#3DD6D0", accent: "#FFB347" }),
    product.tone || "professional",
    product.disclaimer || null,
    product.custom_prompt || null,
    typeof product.campaign_objectives === "string" ? product.campaign_objectives : JSON.stringify(product.campaign_objectives || []),
  ]);
}

export async function updateProduct(id, product) {
  const sql = `
    UPDATE products SET
      name = $1, description = $2, category = $3, website_url = $4,
      target_audience = $5, key_benefits = $6, brand_colors = $7,
      tone = $8, disclaimer = $9, custom_prompt = $10, campaign_objectives = $11,
      updated_at = NOW()
    WHERE id = $12
  `;
  return query(sql, [
    product.name,
    product.description || null,
    product.category || "other",
    product.website_url || null,
    product.target_audience || null,
    typeof product.key_benefits === "string" ? product.key_benefits : JSON.stringify(product.key_benefits || []),
    typeof product.brand_colors === "string" ? product.brand_colors : JSON.stringify(product.brand_colors || {}),
    product.tone || "professional",
    product.disclaimer || null,
    product.custom_prompt || null,
    typeof product.campaign_objectives === "string" ? product.campaign_objectives : JSON.stringify(product.campaign_objectives || []),
    id,
  ]);
}

export async function deleteProduct(id) {
  return query("DELETE FROM products WHERE id = $1", [id]);
}

export async function updateProductLogo(id, logoPath) {
  return query("UPDATE products SET logo_path = $1, updated_at = NOW() WHERE id = $2", [logoPath, id]);
}

// ── Social Account Queries ──

export async function getAllAccounts() {
  const { rows } = await query("SELECT * FROM social_accounts ORDER BY platform, created_at");
  return rows;
}

export async function getAccountById(id) {
  const { rows } = await query("SELECT * FROM social_accounts WHERE id = $1", [id]);
  return rows[0] || null;
}

export async function getAccountByPlatform(platform) {
  const { rows } = await query("SELECT * FROM social_accounts WHERE platform = $1", [platform]);
  return rows[0] || null;
}

export async function upsertAccount(account) {
  const existing = await getAccountByPlatform(account.platform);
  if (existing) {
    const sql = `
      UPDATE social_accounts SET
        username = $1, encrypted_password = $2, extra_fields = $3,
        session_status = $4, updated_at = NOW()
      WHERE platform = $5
    `;
    return query(sql, [
      account.username || null,
      account.encrypted_password || null,
      typeof account.extra_fields === "string" ? account.extra_fields : JSON.stringify(account.extra_fields || {}),
      account.session_status || "unverified",
      account.platform,
    ]);
  } else {
    const sql = `
      INSERT INTO social_accounts (id, platform, username, encrypted_password, extra_fields, session_status)
      VALUES ($1, $2, $3, $4, $5, $6)
    `;
    return query(sql, [
      account.id,
      account.platform,
      account.username || null,
      account.encrypted_password || null,
      typeof account.extra_fields === "string" ? account.extra_fields : JSON.stringify(account.extra_fields || {}),
      account.session_status || "unverified",
    ]);
  }
}

export async function deleteAccount(id) {
  return query("DELETE FROM social_accounts WHERE id = $1", [id]);
}

export async function updateAccountStatus(id, status) {
  return query(
    "UPDATE social_accounts SET session_status = $1, last_verified = NOW(), updated_at = NOW() WHERE id = $2",
    [status, id]
  );
}

// ── Campaign Queries ──

export async function getAllCampaigns() {
  const { rows } = await query(`
    SELECT c.*, p.name as product_name
    FROM campaigns c
    LEFT JOIN products p ON c.product_id = p.id
    ORDER BY c.created_at DESC
  `);
  return rows;
}

export async function getCampaignById(id) {
  const { rows } = await query(`
    SELECT c.*, p.name as product_name
    FROM campaigns c
    LEFT JOIN products p ON c.product_id = p.id
    WHERE c.id = $1
  `, [id]);
  return rows[0] || null;
}

export async function createCampaign(campaign) {
  const sql = `
    INSERT INTO campaigns (
      id, product_id, llm_provider, content_type, language,
      platforms, audience, tone, cta, hashtags,
      aspect_ratio, video_duration, visual_style, custom_instructions, status
    )
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
  `;
  return query(sql, [
    campaign.id,
    campaign.product_id || null,
    campaign.llm_provider || "gemini",
    campaign.content_type || "text",
    campaign.language || "english",
    typeof campaign.platforms === "string" ? campaign.platforms : JSON.stringify(campaign.platforms || []),
    campaign.audience || null,
    campaign.tone || "professional",
    campaign.cta || null,
    campaign.hashtags || null,
    campaign.aspect_ratio || "1:1",
    campaign.video_duration || 15,
    campaign.visual_style || "minimal",
    campaign.custom_instructions || null,
    campaign.status || "draft",
  ]);
}

export async function updateCampaignStatus(id, status, extra = {}) {
  const setClauses = ["status = $1", "updated_at = NOW()"];
  const params = [status];
  let paramIdx = 2;

  if (extra.generated_caption) {
    setClauses.push(`generated_caption = $${paramIdx++}`);
    params.push(extra.generated_caption);
  }
  if (extra.generated_hashtags) {
    setClauses.push(`generated_hashtags = $${paramIdx++}`);
    params.push(typeof extra.generated_hashtags === "string" ? extra.generated_hashtags : JSON.stringify(extra.generated_hashtags));
  }
  if (extra.media_paths) {
    setClauses.push(`media_paths = $${paramIdx++}`);
    params.push(typeof extra.media_paths === "string" ? extra.media_paths : JSON.stringify(extra.media_paths));
  }
  if (extra.telegram_message_id) {
    setClauses.push(`telegram_message_id = $${paramIdx++}`);
    params.push(extra.telegram_message_id);
  }
  if (extra.revision_notes) {
    setClauses.push(`revision_notes = $${paramIdx++}`);
    params.push(extra.revision_notes);
    setClauses.push("revision_count = revision_count + 1");
  }
  if (status === "posted") {
    setClauses.push("posted_at = NOW()");
  }

  const sql = `UPDATE campaigns SET ${setClauses.join(", ")} WHERE id = $${paramIdx}`;
  params.push(id);

  return query(sql, params);
}

export async function deleteCampaign(id) {
  return query("DELETE FROM campaigns WHERE id = $1", [id]);
}

// ── Settings Queries ──

export async function getAllSettings() {
  const { rows } = await query("SELECT * FROM settings");
  const settings = {};
  rows.forEach((row) => {
    settings[row.key] = row.value;
  });
  return settings;
}

export async function getSetting(key) {
  const { rows } = await query("SELECT value FROM settings WHERE key = $1", [key]);
  return rows[0] ? rows[0].value : null;
}

export async function setSetting(key, value) {
  const sql = `
    INSERT INTO settings (key, value)
    VALUES ($1, $2)
    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
  `;
  return query(sql, [key, value]);
}

// ── Stats ──

export async function getDashboardStats() {
  const [pCount, aCount, cCount, postCount, pendCount, recent] = await Promise.all([
    query("SELECT COUNT(*) as count FROM products"),
    query("SELECT COUNT(*) as count FROM social_accounts WHERE session_status = 'verified'"),
    query("SELECT COUNT(*) as count FROM campaigns"),
    query("SELECT COUNT(*) as count FROM campaigns WHERE status = 'posted'"),
    query("SELECT COUNT(*) as count FROM campaigns WHERE status IN ('preview_sent', 'generating')"),
    query(`
      SELECT c.*, p.name as product_name
      FROM campaigns c
      LEFT JOIN products p ON c.product_id = p.id
      ORDER BY c.updated_at DESC
      LIMIT 10
    `),
  ]);

  return {
    productCount: parseInt(pCount.rows[0].count, 10),
    accountCount: parseInt(aCount.rows[0].count, 10),
    campaignCount: parseInt(cCount.rows[0].count, 10),
    postedCount: parseInt(postCount.rows[0].count, 10),
    pendingCount: parseInt(pendCount.rows[0].count, 10),
    recentCampaigns: recent.rows,
  };
}
