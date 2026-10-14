"""
Database synchronizer for Campaigns across PostgreSQL and SQLite.
Ensures every post (image or video) published via Telegram Bot or Webpage
is reliably created or updated in the campaigns table.
"""
import os
import json
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
    telegram_message_id: str = None
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
        plat_list = platforms if isinstance(platforms, list) else [platforms]
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
                    status, telegram_message_id, posted_at, created_at, updated_at
                )
                VALUES (
                    %s, %s, %s, %s, 'english',
                    %s, %s, %s, %s,
                    %s, %s, (CASE WHEN %s THEN NOW() ELSE NULL END), NOW(), NOW()
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
                        posted_at = CASE WHEN ? THEN datetime('now') ELSE posted_at END,
                        updated_at = datetime('now')
                    WHERE id = ?
                """, (status, platforms_json, media_paths_json, caption, content_type, (status == "posted" and posted_at_now), campaign_id))
            else:
                cur.execute("""
                    INSERT INTO campaigns (
                        id, product_id, llm_provider, content_type, language,
                        platforms, media_paths, generated_caption, generated_hashtags,
                        status, telegram_message_id, posted_at, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, 'english', ?, ?, ?, ?, ?, ?, CASE WHEN ? THEN datetime('now') ELSE NULL END, datetime('now'), datetime('now'))
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
        }
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)
    except Exception:
        pass

    return success
