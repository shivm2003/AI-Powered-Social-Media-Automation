import * as SQLite from 'expo-sqlite';

export interface Product {
  id: string;
  name: string;
  category: string;
  description: string;
  target_audience: string;
  key_benefits: string[];
  cta_text: string;
  cta_url: string;
  brand_colors: { primary: string; secondary: string; accent: string };
  logo_icon?: string;
  created_at: number;
}

export interface Campaign {
  id: string;
  product_id: string;
  product_name: string;
  content_type: 'image' | 'video';
  headline: string;
  caption: string;
  hashtags: string[];
  apply_url: string;
  local_image_uri: string;
  status: 'draft' | 'approved' | 'posted';
  platforms: string[];
  created_at: number;
  posted_at?: number;
}

export interface StorageStats {
  totalCampaigns: number;
  totalPublished: number;
  totalProducts: number;
  storageMode: string;
}

let dbInstance: SQLite.SQLiteDatabase | null = null;

export function getDatabase(): SQLite.SQLiteDatabase {
  if (!dbInstance) {
    dbInstance = SQLite.openDatabaseSync('manvix_ai_local.db');
  }
  return dbInstance;
}

export async function initDatabase(): Promise<void> {
  const db = getDatabase();

  // 1. Try setting journal mode safely
  try {
    db.runSync(`PRAGMA journal_mode = WAL;`);
  } catch (e) {
    // Some Android environments don't permit WAL mode change, ignore safely
  }

  // 2. Create products table
  db.runSync(`
    CREATE TABLE IF NOT EXISTS local_products (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      category TEXT,
      description TEXT,
      target_audience TEXT,
      key_benefits TEXT,
      cta_text TEXT,
      cta_url TEXT,
      brand_colors TEXT,
      logo_icon TEXT,
      created_at INTEGER
    );
  `);

  // 3. Create campaigns table
  db.runSync(`
    CREATE TABLE IF NOT EXISTS local_campaigns (
      id TEXT PRIMARY KEY,
      product_id TEXT,
      product_name TEXT,
      content_type TEXT,
      headline TEXT,
      caption TEXT,
      hashtags TEXT,
      apply_url TEXT,
      local_image_uri TEXT,
      status TEXT,
      platforms TEXT,
      created_at INTEGER,
      posted_at INTEGER
    );
  `);

  // 4. Create history table
  db.runSync(`
    CREATE TABLE IF NOT EXISTS published_history (
      id TEXT PRIMARY KEY,
      campaign_id TEXT,
      platform TEXT,
      posted_at INTEGER
    );
  `);

  // 5. Purge any legacy loan data safely
  try {
    db.runSync(`DELETE FROM local_products WHERE id LIKE '%loan%' OR name LIKE '%Loan%'`);
    db.runSync(`DELETE FROM local_campaigns WHERE product_id LIKE '%loan%' OR product_name LIKE '%Loan%'`);
  } catch (e) {
    // ignore
  }

  // 6. Pre-seed default universal starter product if empty
  try {
    const existing = db.getAllSync<any>(`SELECT id FROM local_products`);
    if (!existing || existing.length === 0) {
      const starterProductId = `prod-universal-starter`;
      db.runSync(
        `INSERT INTO local_products (id, name, category, description, target_audience, key_benefits, cta_text, cta_url, brand_colors, logo_icon, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [
          starterProductId,
          'NovaTech Ultra Smartwatch',
          'Wearable Tech & Electronics',
          'Next-generation AMOLED smartwatch with AI health diagnostics, 14-day battery life, and aerospace titanium bezel.',
          'Fitness enthusiasts, tech lovers, and modern professionals seeking premium performance.',
          JSON.stringify([
            'Medical-grade AI heart & ECG monitoring',
            'Ultra-bright 2000-nit sapphire crystal display',
            'Instant wireless supercharging with 14-day standby',
            'Military-grade waterproof & dustproof chassis'
          ]),
          'Shop 40% Off Launch Deal',
          'https://novatech.shop/ultra-watch',
          JSON.stringify({ primary: '#00F2FE', secondary: '#7C5CFC', accent: '#FFB347' }),
          '⌚',
          Date.now(),
        ]
      );

      db.runSync(
        `INSERT INTO local_campaigns (id, product_id, product_name, content_type, headline, caption, hashtags, apply_url, local_image_uri, status, platforms, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [
          `camp-starter-watch`,
          starterProductId,
          'NovaTech Ultra Smartwatch',
          'image',
          '⚡ Experience the Future on Your Wrist: NovaTech Ultra is Here! ⌚✨',
          'Engineered with aerospace titanium, real-time AI biometrics, and a brilliant 2000-nit sapphire display. Elevate your everyday fitness and productivity with 14-day continuous battery life.\n\n🔥 Launch Special: Enjoy 40% OFF this week only!\n\n👉 Shop Now: https://novatech.shop/ultra-watch',
          JSON.stringify(['#NovaTechUltra', '#Smartwatch', '#WearableAI', '#TechLifestyle', '#FitnessGoals', '#Innovation']),
          'https://novatech.shop/ultra-watch',
          'bundled://icon.png',
          'approved',
          JSON.stringify(['facebook', 'instagram', 'whatsapp']),
          Date.now(),
        ]
      );
    }
  } catch (err) {
    console.warn('Error during seeding:', err);
  }
}

function safeParseArray(raw: any): string[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function getAllProducts(): Product[] {
  try {
    const db = getDatabase();
    const rows = db.getAllSync<any>(`SELECT * FROM local_products ORDER BY created_at DESC`);
    return rows.map((r) => {
      let colors = { primary: '#7C5CFC', secondary: '#00F2FE', accent: '#FFB347' };
      try {
        if (r.brand_colors) colors = JSON.parse(r.brand_colors);
      } catch {}

      return {
        id: r.id,
        name: r.name || 'Unnamed Product',
        category: r.category || 'General',
        description: r.description || '',
        target_audience: r.target_audience || '',
        key_benefits: safeParseArray(r.key_benefits),
        cta_text: r.cta_text || 'Learn More',
        cta_url: r.cta_url || '',
        brand_colors: colors,
        logo_icon: r.logo_icon || '🚀',
        created_at: r.created_at || Date.now(),
      };
    });
  } catch (e) {
    console.error('getAllProducts error:', e);
    return [];
  }
}

export function getProductById(id: string): Product | null {
  try {
    const db = getDatabase();
    const r = db.getFirstSync<any>(`SELECT * FROM local_products WHERE id = ?`, [id]);
    if (!r) return null;
    let colors = { primary: '#7C5CFC', secondary: '#00F2FE', accent: '#FFB347' };
    try {
      if (r.brand_colors) colors = JSON.parse(r.brand_colors);
    } catch {}

    return {
      id: r.id,
      name: r.name || 'Unnamed Product',
      category: r.category || 'General',
      description: r.description || '',
      target_audience: r.target_audience || '',
      key_benefits: safeParseArray(r.key_benefits),
      cta_text: r.cta_text || 'Learn More',
      cta_url: r.cta_url || '',
      brand_colors: colors,
      logo_icon: r.logo_icon || '🚀',
      created_at: r.created_at || Date.now(),
    };
  } catch {
    return null;
  }
}

export function saveProduct(product: Product): void {
  const db = getDatabase();
  db.runSync(
    `INSERT OR REPLACE INTO local_products
     (id, name, category, description, target_audience, key_benefits, cta_text, cta_url, brand_colors, logo_icon, created_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      product.id,
      product.name,
      product.category,
      product.description,
      product.target_audience,
      JSON.stringify(product.key_benefits || []),
      product.cta_text,
      product.cta_url,
      JSON.stringify(product.brand_colors || {}),
      product.logo_icon || '🚀',
      product.created_at,
    ]
  );
}

export function deleteProduct(productId: string): void {
  const db = getDatabase();
  db.runSync(`DELETE FROM local_products WHERE id = ?`, [productId]);
  db.runSync(`DELETE FROM local_campaigns WHERE product_id = ?`, [productId]);
}

export function getAllCampaigns(): Campaign[] {
  try {
    const db = getDatabase();
    const rows = db.getAllSync<any>(`SELECT * FROM local_campaigns ORDER BY created_at DESC`);
    return rows.map((r) => ({
      id: r.id,
      product_id: r.product_id,
      product_name: r.product_name || 'Brand Campaign',
      content_type: r.content_type || 'image',
      headline: r.headline || '',
      caption: r.caption || '',
      hashtags: safeParseArray(r.hashtags),
      apply_url: r.apply_url || '',
      local_image_uri: r.local_image_uri || 'bundled://icon.png',
      status: r.status || 'approved',
      platforms: safeParseArray(r.platforms),
      created_at: r.created_at || Date.now(),
      posted_at: r.posted_at,
    }));
  } catch (e) {
    console.error('getAllCampaigns error:', e);
    return [];
  }
}

export function saveCampaign(campaign: Campaign): void {
  const db = getDatabase();
  db.runSync(
    `INSERT OR REPLACE INTO local_campaigns
     (id, product_id, product_name, content_type, headline, caption, hashtags, apply_url, local_image_uri, status, platforms, created_at, posted_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      campaign.id,
      campaign.product_id,
      campaign.product_name,
      campaign.content_type,
      campaign.headline,
      campaign.caption,
      JSON.stringify(campaign.hashtags || []),
      campaign.apply_url,
      campaign.local_image_uri,
      campaign.status,
      JSON.stringify(campaign.platforms || []),
      campaign.created_at,
      campaign.posted_at || null,
    ]
  );
}

export function deleteCampaign(campaignId: string): void {
  const db = getDatabase();
  db.runSync(`DELETE FROM published_history WHERE campaign_id = ?`, [campaignId]);
  db.runSync(`DELETE FROM local_campaigns WHERE id = ?`, [campaignId]);
}

export function markCampaignPosted(campaignId: string, platforms: string[]): void {
  const db = getDatabase();
  const now = Date.now();
  db.runSync(
    `UPDATE local_campaigns SET status = 'posted', platforms = ?, posted_at = ? WHERE id = ?`,
    [JSON.stringify(platforms), now, campaignId]
  );

  for (const plat of platforms) {
    db.runSync(
      `INSERT INTO published_history (id, campaign_id, platform, posted_at) VALUES (?, ?, ?, ?)`,
      [`pub-${Date.now()}-${plat}`, campaignId, plat, now]
    );
  }
}

export function getStorageStats(): StorageStats {
  try {
    const db = getDatabase();
    const campCount = db.getFirstSync<any>(`SELECT COUNT(*) as c FROM local_campaigns`)?.c || 0;
    const pubCount = db.getFirstSync<any>(`SELECT COUNT(*) as c FROM published_history`)?.c || 0;
    const prodCount = db.getFirstSync<any>(`SELECT COUNT(*) as c FROM local_products`)?.c || 0;

    return {
      totalCampaigns: campCount,
      totalPublished: pubCount,
      totalProducts: prodCount,
      storageMode: '100% On-Device SQLite (Internal Memory)',
    };
  } catch {
    return {
      totalCampaigns: 0,
      totalPublished: 0,
      totalProducts: 0,
      storageMode: '100% On-Device SQLite (Internal Memory)',
    };
  }
}
