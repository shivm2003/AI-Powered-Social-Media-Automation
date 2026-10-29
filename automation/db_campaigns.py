"""
Database synchronizer for Campaigns across PostgreSQL and SQLite.
Ensures every post (image or video) published via Telegram Bot or Webpage
is reliably created or updated in the campaigns table.
"""
import os
import json
import time
import datetime
import logging
from pathlib import Path

logger = logging.getLogger("automation.db_campaigns")

BASE_DIR = Path(__file__).parent.parent


def get_pg_connection():
    """Connect to PostgreSQL database using environment or default credentials."""
    import psycopg2
    pg_user = os.environ.get("DB_USER", "postgres")
    pg_pass = os.environ.get("DB_PASSWORD", "Shivam@123")
    pg_host = os.environ.get("DB_HOST", "localhost")
    pg_port = int(os.environ.get("DB_PORT", "5432"))
    pg_db = os.environ.get("DB_NAME", "Social_Media")
    return psycopg2.connect(dbname=pg_db, user=pg_user, password=pg_pass, host=pg_host, port=pg_port)


def find_default_product_id(product_name: str = None) -> str:
    """Finds an existing product ID from PostgreSQL, matching by name if provided."""
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        if product_name:
            cur.execute("SELECT id FROM products WHERE LOWER(name) LIKE %s LIMIT 1", (f"%{product_name.lower().strip()}%",))
            row = cur.fetchone()
            if row:
                cur.close()
                conn.close()
                return row[0]
        cur.execute("SELECT id FROM products ORDER BY created_at DESC LIMIT 1")
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return row[0]
    except Exception as e:
        logger.debug(f"Product lookup note: {e}")
    return None


def save_or_update_campaign(
    campaign_id: str,
    status: str = "posted",
    platforms=None,
    media_path: str = None,
    caption: str = None,
    hashtags=None,
    content_type: str = None,
    product_id: str = None,
    product_name: str = None,
    llm_provider: str = None,
    posted_at_now: bool = True,
    telegram_message_id: str = None,
    revision_notes: str = None,
    revision_count: int = None,
    contact_number: str = None,
    account_id: str = None
) -> bool:
    """
    Saves or updates a campaign record in PostgreSQL and SQLite.
    Guarantees that posts published via Telegram bot or web dashboard
    are immediately reflected in campaigns.
    """
    if not campaign_id:
        return False

    # 1. Format inputs cleanly
    if platforms:
        if isinstance(platforms, str):
            plat_list = [p.strip().lower() for p in platforms.split(",") if p.strip()]
        elif isinstance(platforms, list):
            plat_list = []
            for p in platforms:
                if isinstance(p, str) and "," in p:
                    plat_list.extend([x.strip().lower() for x in p.split(",") if x.strip()])
                elif isinstance(p, str) and p.strip():
                    plat_list.append(p.strip().lower())
        else:
            plat_list = [str(platforms)]
        seen = set()
        plat_list = [x for x in plat_list if not (x in seen or seen.add(x))]
    else:
        plat_list = ["facebook"]
    platforms_json = json.dumps(plat_list)

    media_paths_json = None
    if media_path:
        if isinstance(media_path, list):
            media_paths_json = json.dumps(media_path)
        else:
            media_paths_json = json.dumps([str(media_path)])

    hashtags_json = None
    if hashtags:
        if isinstance(hashtags, list):
            hashtags_json = json.dumps(hashtags)
        else:
            hashtags_json = json.dumps([str(hashtags)])

    if not content_type:
        if media_path and (str(media_path).lower().endswith(".mp4") or str(media_path).lower().endswith(".mov")):
            content_type = "video"
        else:
            content_type = "image"

    if not product_id:
        product_id = find_default_product_id(product_name)

    llm_provider = llm_provider or "chatgpt"

    # 2. Update or Insert in PostgreSQL
    success = False
    try:
        conn = get_pg_connection()
        cur = conn.cursor()

        # Check existing
        cur.execute("SELECT id, platforms, media_paths, generated_caption FROM campaigns WHERE id = %s", (campaign_id,))
        existing = cur.fetchone()

        if existing:
            # Merge platforms if needed
            existing_plats = []
            if existing[1]:
                try:
                    existing_plats = json.loads(existing[1]) if isinstance(existing[1], str) else existing[1]
                except Exception:
                    pass
            combined_plats = list(dict.fromkeys(existing_plats + plat_list))
            final_plats_json = json.dumps(combined_plats)

            # Update existing campaign
            set_parts = ["status = %s", "updated_at = NOW()"]
            params = [status]

            if final_plats_json:
                set_parts.append("platforms = %s")
                params.append(final_plats_json)
            if media_paths_json:
                set_parts.append("media_paths = %s")
                params.append(media_paths_json)
            if caption:
                set_parts.append("generated_caption = %s")
                params.append(caption)
            if hashtags_json:
                set_parts.append("generated_hashtags = %s")
                params.append(hashtags_json)
            if content_type:
                set_parts.append("content_type = %s")
                params.append(content_type)
            if telegram_message_id:
                set_parts.append("telegram_message_id = %s")
                params.append(str(telegram_message_id))
            if revision_notes is not None:
                set_parts.append("revision_notes = %s")
                params.append(revision_notes)
            if revision_count is not None:
                set_parts.append("revision_count = %s")
                params.append(revision_count)
            if contact_number is not None:
                set_parts.append("contact_number = %s")
                params.append(contact_number)
            if account_id is not None:
                set_parts.append("account_id = %s")
                params.append(account_id)
            if posted_at_now and status == "posted":
                set_parts.append("posted_at = NOW()")

            params.append(campaign_id)
            query = f"UPDATE campaigns SET {', '.join(set_parts)} WHERE id = %s"
            cur.execute(query, tuple(params))
            conn.commit()
            logger.info(f"Updated campaign {campaign_id} in PostgreSQL with status='{status}' (Platforms: {combined_plats}).")
        else:
            # Insert brand new campaign record
            insert_query = """
                INSERT INTO campaigns (
                    id, product_id, llm_provider, content_type, language,
                    platforms, media_paths, generated_caption, generated_hashtags,
                    status, telegram_message_id, revision_notes, revision_count,
                    contact_number, account_id, posted_at, created_at, updated_at
                )
                VALUES (
                    %s, %s, %s, %s, 'english',
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, (CASE WHEN %s THEN NOW() ELSE NULL END), NOW(), NOW()
                )
            """
            cur.execute(insert_query, (
                campaign_id,
                product_id,
                llm_provider,
                content_type,
                platforms_json,
                media_paths_json or "[]",
                caption or "",
                hashtags_json or "[]",
                status,
                str(telegram_message_id) if telegram_message_id else None,
                revision_notes,
                revision_count or 0,
                contact_number,
                account_id,
                (status == "posted" and posted_at_now),
            ))
            conn.commit()
            logger.info(f"Inserted brand new campaign {campaign_id} into PostgreSQL with status='{status}'.")

        cur.close()
        conn.close()
        success = True
    except Exception as e_pg:
        logger.error(f"PostgreSQL campaign save error for {campaign_id}: {e_pg}")

    # 3. Synchronize with SQLite if exists
    db_path = BASE_DIR / "data" / "database.sqlite"
    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT id FROM campaigns WHERE id = ?", (campaign_id,))
            exists_sqlite = cur.fetchone()
            if exists_sqlite:
                cur.execute("""
                    UPDATE campaigns
                    SET status = ?,
                        platforms = COALESCE(?, platforms),
                        media_paths = COALESCE(?, media_paths),
                        generated_caption = COALESCE(?, generated_caption),
                        content_type = COALESCE(?, content_type),
                        revision_notes = COALESCE(?, revision_notes),
                        revision_count = COALESCE(?, revision_count),
                        contact_number = COALESCE(?, contact_number),
                        account_id = COALESCE(?, account_id),
                        posted_at = CASE WHEN ? THEN datetime('now') ELSE posted_at END,
                        updated_at = datetime('now')
                    WHERE id = ?
                """, (status, platforms_json, media_paths_json, caption, content_type, revision_notes, revision_count, contact_number, account_id, (status == "posted" and posted_at_now), campaign_id))
            else:
                cur.execute("""
                    INSERT INTO campaigns (
                        id, product_id, llm_provider, content_type, language,
                        platforms, media_paths, generated_caption, generated_hashtags,
                        status, telegram_message_id, revision_notes, revision_count,
                        contact_number, account_id, posted_at, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, 'english', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CASE WHEN ? THEN datetime('now') ELSE NULL END, datetime('now'), datetime('now'))
                """, (
                    campaign_id,
                    product_id,
                    llm_provider,
                    content_type,
                    platforms_json,
                    media_paths_json or "[]",
                    caption or "",
                    hashtags_json or "[]",
                    status,
                    str(telegram_message_id) if telegram_message_id else None,
                    revision_notes,
                    revision_count or 0,
                    contact_number,
                    account_id,
                    (status == "posted" and posted_at_now),
                ))
            conn.commit()
            conn.close()
        except Exception as e_sq:
            logger.debug(f"SQLite campaign sync note: {e_sq}")

    # 4. Save to local JSON cache in data/
    try:
        data_dir = BASE_DIR / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        cache_file = data_dir / f"campaign_{campaign_id}.json"
        cache_data = {
            "id": campaign_id,
            "status": status,
            "platforms": plat_list,
            "media_path": media_path,
            "caption": caption,
            "content_type": content_type,
            "product_id": product_id,
            "llm_provider": llm_provider,
            "revision_notes": revision_notes,
            "revision_count": revision_count,
        }
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)
    except Exception:
        pass

    return success


def get_campaign_from_db(campaign_id: str) -> dict:
    """Retrieves full campaign information and joined product info from PostgreSQL or SQLite."""
    if not campaign_id:
        return {}

    # 1. Try PostgreSQL
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT c.id, c.product_id, c.llm_provider, c.content_type, c.platforms,
                   c.generated_caption, c.generated_hashtags, c.media_paths, c.status,
                   c.revision_notes, c.revision_count, c.aspect_ratio, c.visual_style, c.contact_number,
                   p.name as product_name, p.description as product_desc, p.category as product_category,
                   p.target_audience as product_audience, p.key_benefits as product_benefits,
                   p.brand_colors as product_colors, p.logo_path as product_logo, p.contact_number as product_contact
            FROM campaigns c
            LEFT JOIN products p ON c.product_id = p.id
            WHERE c.id = %s
        """, (campaign_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            p_name = row[14]
            c_phone = row[13] or row[21] or ("8112570656" if "loan" in (p_name or "").lower() else None)
            return {
                "id": row[0],
                "product_id": row[1],
                "llm_provider": row[2],
                "content_type": row[3],
                "platforms": json.loads(row[4]) if row[4] and row[4].startswith("[") else row[4],
                "generated_caption": row[5],
                "generated_hashtags": json.loads(row[6]) if row[6] and row[6].startswith("[") else row[6],
                "media_paths": json.loads(row[7]) if row[7] and row[7].startswith("[") else row[7],
                "status": row[8],
                "revision_notes": row[9],
                "revision_count": row[10] or 0,
                "aspect_ratio": row[11] or "1:1",
                "visual_style": row[12] or "photorealistic",
                "contact_number": c_phone,
                "product": {
                    "name": row[14],
                    "description": row[15],
                    "category": row[16],
                    "target_audience": row[17],
                    "key_benefits": json.loads(row[18]) if row[18] and row[18].startswith("[") else row[18],
                    "brand_colors": json.loads(row[19]) if row[19] and row[19].startswith("{") else row[19],
                    "logo_path": row[20],
                    "contact_number": c_phone,
                }
            }
    except Exception as e_pg:
        logger.debug(f"Postgres get_campaign note: {e_pg}")

    # 2. Try SQLite
    db_path = BASE_DIR / "data" / "database.sqlite"
    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT c.*, p.name as product_name, p.description as product_desc,
                       p.category as product_category, p.target_audience as product_audience,
                       p.key_benefits as product_benefits, p.brand_colors as product_colors,
                       p.logo_path as product_logo
                FROM campaigns c
                LEFT JOIN products p ON c.product_id = p.id
                WHERE c.id = ?
            """, (campaign_id,))
            row = cur.fetchone()
            conn.close()
            if row:
                d = dict(row)
                return {
                    "id": d.get("id"),
                    "product_id": d.get("product_id"),
                    "llm_provider": d.get("llm_provider"),
                    "content_type": d.get("content_type"),
                    "platforms": json.loads(d.get("platforms") or "[]") if d.get("platforms", "").startswith("[") else d.get("platforms"),
                    "generated_caption": d.get("generated_caption"),
                    "generated_hashtags": json.loads(d.get("generated_hashtags") or "[]") if d.get("generated_hashtags", "").startswith("[") else d.get("generated_hashtags"),
                    "media_paths": json.loads(d.get("media_paths") or "[]") if d.get("media_paths", "").startswith("[") else d.get("media_paths"),
                    "status": d.get("status"),
                    "revision_notes": d.get("revision_notes"),
                    "revision_count": d.get("revision_count") or 0,
                    "aspect_ratio": d.get("aspect_ratio") or "1:1",
                    "visual_style": d.get("visual_style") or "photorealistic",
                    "product": {
                        "name": d.get("product_name"),
                        "description": d.get("product_desc"),
                        "category": d.get("product_category"),
                        "target_audience": d.get("product_audience"),
                        "key_benefits": json.loads(d.get("product_benefits") or "[]") if (d.get("product_benefits") or "").startswith("[") else d.get("product_benefits"),
                        "brand_colors": json.loads(d.get("product_colors") or "{}") if (d.get("product_colors") or "").startswith("{") else d.get("product_colors"),
                        "logo_path": d.get("product_logo"),
                    }
                }
        except Exception as e_sq:
            logger.debug(f"SQLite get_campaign note: {e_sq}")

    return {}


def get_all_chrome_accounts() -> list:
    """Retrieves all 7 Chrome accounts with their Google identity and linked social handles."""
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, profile_dir, google_name, google_email, facebook_name, facebook_id, facebook_page_url, instagram_username, instagram_url, is_default, is_active FROM chrome_accounts ORDER BY is_default DESC, created_at ASC")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        accounts = []
        for r in rows:
            accounts.append({
                "id": r[0],
                "profile_dir": r[1],
                "google_name": r[2],
                "google_email": r[3],
                "facebook_name": r[4],
                "facebook_id": r[5],
                "facebook_page_url": r[6],
                "instagram_username": r[7],
                "instagram_url": r[8],
                "is_default": bool(r[9]),
                "is_active": bool(r[10]),
            })
        if accounts:
            return accounts
    except Exception as e:
        logger.debug(f"PostgreSQL accounts fetch note: {e}")

    # Fallback SQLite
    db_path = BASE_DIR / "data" / "database.sqlite"
    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM chrome_accounts ORDER BY is_default DESC, created_at ASC")
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            return rows
        except Exception:
            pass
    return []


def get_chrome_account(account_id_or_profile_dir: str = None) -> dict:
    """Finds a specific Chrome account by ID, profile_dir, email, or profile index."""
    accounts = get_all_chrome_accounts()
    if not accounts:
        return {}
    if not account_id_or_profile_dir:
        # Return default or first
        for a in accounts:
            if a.get("is_default"):
                return a
        return accounts[0]

    val = str(account_id_or_profile_dir).lower().strip()
    # 1. Exact match on id, profile_dir, or google_email
    for a in accounts:
        if (
            str(a.get("id", "")).lower() == val
            or str(a.get("profile_dir", "")).lower() == val
            or str(a.get("google_email", "")).lower() == val
        ):
            return a

    # 2. Match email username prefix or substring
    for a in accounts:
        email = str(a.get("google_email", "")).lower()
        if email and (val in email or email.split("@")[0] == val):
            return a

    # 3. Match numeric directory (e.g. '14' -> 'Profile 14', '1' -> 'Profile 1')
    digits = "".join(ch for ch in val if ch.isdigit())
    if digits:
        for a in accounts:
            p_digits = "".join(ch for ch in str(a.get("profile_dir", "")) if ch.isdigit())
            if p_digits == digits:
                return a

    # 4. Fallback to default
    for a in accounts:
        if a.get("is_default"):
            return a
    return accounts[0]


def init_instagram_leads_tables():
    """Initializes instagram_target_leads table in SQLite and PostgreSQL if available."""
    schema_sqlite = """
    CREATE TABLE IF NOT EXISTS instagram_target_leads (
        id TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        user_id_input TEXT,
        profile_url TEXT NOT NULL,
        full_name TEXT,
        followers_count INTEGER DEFAULT 0,
        followers_text TEXT,
        following_count INTEGER DEFAULT 0,
        posts_count INTEGER DEFAULT 0,
        bio TEXT,
        is_private BOOLEAN DEFAULT 0,
        follow_status TEXT NOT NULL,
        follow_button_state TEXT,
        account_used TEXT,
        source TEXT DEFAULT 'bot',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_ig_leads_username ON instagram_target_leads(username);
    CREATE INDEX IF NOT EXISTS idx_ig_leads_status ON instagram_target_leads(follow_status);
    """
    db_path = BASE_DIR / "data" / "database.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.executescript(schema_sqlite)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error initializing SQLite instagram_target_leads: {e}")

    # Optional PostgreSQL
    try:
        conn_pg = get_pg_connection()
        cur = conn_pg.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS instagram_target_leads (
            id VARCHAR(100) PRIMARY KEY,
            username VARCHAR(100) NOT NULL,
            user_id_input VARCHAR(100),
            profile_url TEXT NOT NULL,
            full_name TEXT,
            followers_count INTEGER DEFAULT 0,
            followers_text VARCHAR(50),
            following_count INTEGER DEFAULT 0,
            posts_count INTEGER DEFAULT 0,
            bio TEXT,
            is_private BOOLEAN DEFAULT FALSE,
            follow_status VARCHAR(50) NOT NULL,
            follow_button_state VARCHAR(50),
            account_used VARCHAR(100),
            source VARCHAR(50) DEFAULT 'bot',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_ig_leads_username_pg ON instagram_target_leads(username);
        """)
        conn_pg.commit()
        cur.close()
        conn_pg.close()
    except Exception as e:
        logger.debug(f"Postgres instagram_target_leads init note: {e}")


def save_instagram_target_lead(lead: dict) -> dict:
    """
    Saves or updates an Instagram target account lead with follower count,
    following count, posts, bio, and follow status.
    Persists to both SQLite and persistent JSON tracker.
    Returns aggregated cumulative counters.
    """
    init_instagram_leads_tables()
    username = (lead.get("username") or "").strip().lower()
    if not username:
        return {}

    lead_id = f"ig_{username}"
    user_id_input = lead.get("user_id_input") or username
    profile_url = lead.get("profile_url") or f"https://www.instagram.com/{username}/"
    full_name = lead.get("full_name") or ""
    followers_count = int(lead.get("followers_count") or 0)
    followers_text = lead.get("followers_text") or str(followers_count)
    following_count = int(lead.get("following_count") or 0)
    posts_count = int(lead.get("posts_count") or 0)
    bio = lead.get("bio") or ""
    is_private = 1 if lead.get("is_private") else 0
    follow_status = lead.get("follow_status") or lead.get("status") or "unknown"
    follow_button_state = lead.get("follow_button_state") or lead.get("new_state") or ""
    account_used = lead.get("account_used") or "Default"
    source = lead.get("source") or "bot"

    # 1. Save to SQLite
    db_path = BASE_DIR / "data" / "database.sqlite"
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO instagram_target_leads (
                id, username, user_id_input, profile_url, full_name,
                followers_count, followers_text, following_count, posts_count,
                bio, is_private, follow_status, follow_button_state,
                account_used, source, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                full_name = excluded.full_name,
                followers_count = excluded.followers_count,
                followers_text = excluded.followers_text,
                following_count = excluded.following_count,
                posts_count = excluded.posts_count,
                bio = excluded.bio,
                is_private = excluded.is_private,
                follow_status = excluded.follow_status,
                follow_button_state = excluded.follow_button_state,
                account_used = excluded.account_used,
                updated_at = CURRENT_TIMESTAMP
        """, (
            lead_id, username, user_id_input, profile_url, full_name,
            followers_count, followers_text, following_count, posts_count,
            bio, is_private, follow_status, follow_button_state,
            account_used, source
        ))
        conn.commit()
        conn.close()
    except Exception as e_sq:
        logger.error(f"Error saving lead to SQLite: {e_sq}")

    # 2. Try PostgreSQL
    try:
        conn_pg = get_pg_connection()
        cur = conn_pg.cursor()
        cur.execute("""
            INSERT INTO instagram_target_leads (
                id, username, user_id_input, profile_url, full_name,
                followers_count, followers_text, following_count, posts_count,
                bio, is_private, follow_status, follow_button_state,
                account_used, source, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT(id) DO UPDATE SET
                full_name = EXCLUDED.full_name,
                followers_count = EXCLUDED.followers_count,
                followers_text = EXCLUDED.followers_text,
                following_count = EXCLUDED.following_count,
                posts_count = EXCLUDED.posts_count,
                bio = EXCLUDED.bio,
                is_private = EXCLUDED.is_private,
                follow_status = EXCLUDED.follow_status,
                follow_button_state = EXCLUDED.follow_button_state,
                account_used = EXCLUDED.account_used,
                updated_at = NOW()
        """, (
            lead_id, username, user_id_input, profile_url, full_name,
            followers_count, followers_text, following_count, posts_count,
            bio, bool(is_private), follow_status, follow_button_state,
            account_used, source
        ))
        conn_pg.commit()
        cur.close()
        conn_pg.close()
    except Exception as e_pg:
        logger.debug(f"PostgreSQL lead save note: {e_pg}")

    # 3. Save to JSON Tracker
    json_path = BASE_DIR / "data" / "instagram_leads_tracker.json"
    tracker_data = {"leads": {}, "stats": {}}
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                tracker_data = json.load(f)
        except Exception:
            pass

    leads_map = tracker_data.get("leads", {})
    leads_map[username] = {
        "username": username,
        "full_name": full_name,
        "profile_url": profile_url,
        "followers_count": followers_count,
        "followers_text": followers_text,
        "following_count": following_count,
        "posts_count": posts_count,
        "bio": bio,
        "is_private": bool(is_private),
        "follow_status": follow_status,
        "follow_button_state": follow_button_state,
        "account_used": account_used,
        "source": source,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    # Recalculate stats
    total_scanned = len(leads_map)
    total_followed = sum(1 for item in leads_map.values() if item.get("follow_status") == "success")
    total_requested = sum(1 for item in leads_map.values() if item.get("follow_status") == "requested")
    total_already = sum(1 for item in leads_map.values() if item.get("follow_status") == "already_following")
    total_skipped = sum(1 for item in leads_map.values() if item.get("follow_status") == "skipped")

    tracker_data["leads"] = leads_map
    tracker_data["stats"] = {
        "total_scanned": total_scanned,
        "total_followed": total_followed,
        "total_requested": total_requested,
        "total_already_following": total_already,
        "total_skipped": total_skipped,
        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(tracker_data, f, indent=2, ensure_ascii=False)
    except Exception as e_json:
        logger.error(f"Error writing to instagram_leads_tracker.json: {e_json}")

    return tracker_data["stats"]


def get_instagram_leads_stats() -> dict:
    """Returns overall summary statistics and recent records for Instagram leads."""
    json_path = BASE_DIR / "data" / "instagram_leads_tracker.json"
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                stats = data.get("stats", {})
                leads = list(data.get("leads", {}).values())
                # Sort newest first
                leads.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
                return {
                    "stats": stats,
                    "recent_leads": leads[:15],
                    "total_count": len(leads)
                }
        except Exception:
            pass

    # Fallback to SQLite
    db_path = BASE_DIR / "data" / "database.sqlite"
    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM instagram_target_leads ORDER BY updated_at DESC LIMIT 15")
            rows = [dict(r) for r in cur.fetchall()]
            cur.execute("SELECT COUNT(*), SUM(CASE WHEN follow_status='success' THEN 1 ELSE 0 END), SUM(CASE WHEN follow_status='requested' THEN 1 ELSE 0 END) FROM instagram_target_leads")
            cnt_row = cur.fetchone()
            conn.close()
            return {
                "stats": {
                    "total_scanned": cnt_row[0] or 0,
                    "total_followed": cnt_row[1] or 0,
                    "total_requested": cnt_row[2] or 0
                },
                "recent_leads": rows,
                "total_count": cnt_row[0] or 0
            }
        except Exception:
            pass

    return {"stats": {"total_scanned": 0, "total_followed": 0, "total_requested": 0}, "recent_leads": [], "total_count": 0}


def init_post_shares_table():
    """Initializes post_shares_log table in SQLite and PostgreSQL."""
    schema_sqlite = """
    CREATE TABLE IF NOT EXISTS post_shares_log (
        id TEXT PRIMARY KEY,
        campaign_id TEXT,
        platform TEXT NOT NULL,
        recipient_name TEXT NOT NULL,
        recipient_id TEXT,
        post_url TEXT,
        media_path TEXT,
        content_type TEXT DEFAULT 'image',
        status TEXT NOT NULL,
        share_mode TEXT DEFAULT 'share_all',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_post_shares_camp ON post_shares_log(campaign_id);
    CREATE INDEX IF NOT EXISTS idx_post_shares_plat ON post_shares_log(platform);
    """
    db_path = BASE_DIR / "data" / "database.sqlite"
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.executescript(schema_sqlite)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error initializing SQLite post_shares_log: {e}")

    try:
        conn_pg = get_pg_connection()
        cur = conn_pg.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS post_shares_log (
            id VARCHAR(100) PRIMARY KEY,
            campaign_id VARCHAR(100),
            platform VARCHAR(50) NOT NULL,
            recipient_name VARCHAR(255) NOT NULL,
            recipient_id VARCHAR(255),
            post_url TEXT,
            media_path TEXT,
            content_type VARCHAR(20) DEFAULT 'image',
            status VARCHAR(50) NOT NULL,
            share_mode VARCHAR(50) DEFAULT 'share_all',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_post_shares_camp_pg ON post_shares_log(campaign_id);
        CREATE INDEX IF NOT EXISTS idx_post_shares_plat_pg ON post_shares_log(platform);
        """)
        conn_pg.commit()
        cur.close()
        conn_pg.close()
    except Exception as e:
        logger.debug(f"PostgreSQL post_shares_log init note: {e}")


def record_post_share(
    campaign_id: str,
    platform: str,
    recipient_name: str,
    recipient_id: str = None,
    post_url: str = None,
    media_path: str = None,
    content_type: str = "image",
    status: str = "sent",
    share_mode: str = "share_all"
) -> bool:
    """Records an individual post share action in the database and JSON tracker."""
    import uuid
    init_post_shares_table()
    share_id = f"shr_{uuid.uuid4().hex[:12]}"

    db_path = BASE_DIR / "data" / "database.sqlite"
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO post_shares_log (
                id, campaign_id, platform, recipient_name, recipient_id,
                post_url, media_path, content_type, status, share_mode, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            share_id, campaign_id, platform.lower(), recipient_name, recipient_id,
            post_url, media_path, content_type, status, share_mode
        ))
        conn.commit()
        conn.close()
    except Exception as e_sq:
        logger.error(f"Error saving share to SQLite: {e_sq}")

    try:
        conn_pg = get_pg_connection()
        cur = conn_pg.cursor()
        cur.execute("""
            INSERT INTO post_shares_log (
                id, campaign_id, platform, recipient_name, recipient_id,
                post_url, media_path, content_type, status, share_mode, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            share_id, campaign_id, platform.lower(), recipient_name, recipient_id,
            post_url, media_path, content_type, status, share_mode
        ))
        conn_pg.commit()
        cur.close()
        conn_pg.close()
    except Exception as e_pg:
        logger.debug(f"PostgreSQL post share note: {e_pg}")

    return True


def get_all_published_posts(platform: str = None, limit: int = 25) -> list:
    """
    Retrieves all campaigns that have been published/posted on Instagram, Facebook, or both,
    with existing media files on disk. Returns rich metadata, captions, and share counts.
    """
    import os
    init_post_shares_table()
    posts = []

    db_path = BASE_DIR / "data" / "database.sqlite"
    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT c.id, c.status, c.platforms, c.media_paths, c.generated_caption,
                       c.content_type, c.updated_at, c.created_at, p.name as product_name,
                       (SELECT COUNT(*) FROM post_shares_log s WHERE s.campaign_id = c.id AND s.status = 'sent') as total_shares
                FROM campaigns c
                LEFT JOIN products p ON c.product_id = p.id
                WHERE c.media_paths IS NOT NULL
                  AND (c.status IN ('posted', 'published', 'completed', 'approved', 'preview_sent')
                       OR c.media_paths LIKE '%.png%' OR c.media_paths LIKE '%.mp4%')
                ORDER BY c.updated_at DESC
                LIMIT ?
            """, (limit * 2,))
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()

            for r in rows:
                mps = []
                if r.get("media_paths"):
                    try:
                        mps = json.loads(r["media_paths"]) if r["media_paths"].startswith("[") else [r["media_paths"]]
                    except Exception:
                        mps = [r["media_paths"]]

                valid_mps = [p for p in mps if p and os.path.exists(p)]
                if not valid_mps:
                    continue

                primary_media = valid_mps[0]
                is_video = primary_media.lower().endswith(".mp4") or primary_media.lower().endswith(".mov")
                ctype = "video" if is_video else "image"

                raw_plats = r.get("platforms") or "[]"
                try:
                    plats = json.loads(raw_plats) if raw_plats.startswith("[") else [raw_plats]
                except Exception:
                    plats = ["facebook", "instagram"]

                plats = [str(p).lower() for p in plats if str(p).strip()]
                if not plats:
                    plats = ["facebook", "instagram"]

                if platform and platform.lower() != "both" and platform.lower() not in plats:
                    continue

                posts.append({
                    "id": r["id"],
                    "status": r.get("status", "posted"),
                    "platforms": plats,
                    "media_path": primary_media,
                    "media_paths": valid_mps,
                    "content_type": ctype,
                    "caption": r.get("generated_caption") or "",
                    "product_name": r.get("product_name") or "Loan Solutions",
                    "updated_at": r.get("updated_at") or "",
                    "total_shares": r.get("total_shares") or 0
                })

                if len(posts) >= limit:
                    break

        except Exception as e_sq:
            logger.error(f"Error fetching published posts: {e_sq}")

    return posts


def get_post_shares_stats(campaign_id: str = None) -> dict:
    """Returns aggregated share counts and recent recipients for a campaign or overall."""
    init_post_shares_table()
    db_path = BASE_DIR / "data" / "database.sqlite"
    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            if campaign_id:
                cur.execute("""
                    SELECT COUNT(*),
                           SUM(CASE WHEN platform='instagram' THEN 1 ELSE 0 END),
                           SUM(CASE WHEN platform='facebook' THEN 1 ELSE 0 END)
                    FROM post_shares_log WHERE campaign_id = ? AND status = 'sent'
                """, (campaign_id,))
                c_row = cur.fetchone()
                cur.execute("""
                    SELECT * FROM post_shares_log WHERE campaign_id = ? ORDER BY created_at DESC LIMIT 10
                """, (campaign_id,))
                recent = [dict(r) for r in cur.fetchall()]
            else:
                cur.execute("""
                    SELECT COUNT(*),
                           SUM(CASE WHEN platform='instagram' THEN 1 ELSE 0 END),
                           SUM(CASE WHEN platform='facebook' THEN 1 ELSE 0 END)
                    FROM post_shares_log WHERE status = 'sent'
                """)
                c_row = cur.fetchone()
                cur.execute("""
                    SELECT * FROM post_shares_log ORDER BY created_at DESC LIMIT 10
                """)
                recent = [dict(r) for r in cur.fetchall()]

            conn.close()
            return {
                "total_shares": c_row[0] or 0,
                "instagram_shares": c_row[1] or 0,
                "facebook_shares": c_row[2] or 0,
                "recent_shares": recent
            }
        except Exception as e:
            logger.error(f"Error querying post share stats: {e}")

    return {"total_shares": 0, "instagram_shares": 0, "facebook_shares": 0, "recent_shares": []}




