"""
Telegram Long-Polling Daemon for Interactive Social Media Publishing.
Handles:
1. Approval callback -> Sends social platform selection action buttons.
2. Platform selection (Facebook, Instagram, LinkedIn, etc.) -> Triggers browser automation.
3. Login detection -> Requests password in Telegram if account is logged out.
4. Password ingestion -> Automatically types/pastes password into browser & completes post.
"""
import os
import sys
import time
import json
import logging
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = Path(__file__).parent.parent.parent
sys.path.append(str(BASE_DIR / "automation"))

import config
from telegram.bot import (
    get_telegram_credentials,
    make_telegram_request,
    answer_callback_query,
    send_platform_selection_menu,
    send_password_request_prompt,
    delete_telegram_message,
    send_text_message,
    send_start_dashboard,
)
from social.facebook import is_facebook_login_needed, submit_facebook_login, post_to_facebook
from browser.driver import browser

logger = logging.getLogger("automation.telegram.poller")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# In-memory session state per chat_id
chat_sessions = {}


def get_all_products() -> list:
    """Finds all registered products from PostgreSQL or SQLite."""
    # 1. Try PostgreSQL
    try:
        import psycopg2
        pg_user = os.environ.get("DB_USER", "postgres")
        pg_pass = os.environ.get("DB_PASSWORD", "Shivam@123")
        pg_host = os.environ.get("DB_HOST", "localhost")
        pg_port = int(os.environ.get("DB_PORT", "5432"))
        pg_db = os.environ.get("DB_NAME", "Social_Media")
        conn = psycopg2.connect(dbname=pg_db, user=pg_user, password=pg_pass, host=pg_host, port=pg_port)
        cur = conn.cursor()
        cur.execute("SELECT id, name, category, description FROM products ORDER BY name ASC")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        if rows:
            return [{"id": str(r[0]), "name": r[1], "category": r[2], "description": r[3]} for r in rows]
    except Exception as e:
        logger.debug(f"PG products lookup note: {e}")

    # 2. Try SQLite
    db_path = BASE_DIR / "data" / "database.sqlite"
    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT id, name, category, description FROM products ORDER BY name ASC")
            rows = cur.fetchall()
            conn.close()
            if rows:
                return [{"id": str(r[0]), "name": r[1], "category": r[2], "description": r[3]} for r in rows]
        except Exception as e:
            logger.debug(f"SQLite products lookup note: {e}")

    return []



def get_campaign_data(campaign_id: str) -> dict:
    """Finds campaign data from PostgreSQL, SQLite, or file cache."""
    # 1. Try PostgreSQL
    try:
        import psycopg2
        pg_user = os.environ.get("DB_USER", "postgres")
        pg_pass = os.environ.get("DB_PASSWORD", "Shivam@123")
        pg_host = os.environ.get("DB_HOST", "localhost")
        pg_port = int(os.environ.get("DB_PORT", "5432"))
        pg_db = os.environ.get("DB_NAME", "Social_Media")
        conn = psycopg2.connect(dbname=pg_db, user=pg_user, password=pg_pass, host=pg_host, port=pg_port)
        cur = conn.cursor()
        cur.execute("SELECT generated_caption, generated_hashtags, media_paths FROM campaigns WHERE id = %s", (campaign_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            caption, hashtags, media_paths = row
            media_list = json.loads(media_paths) if isinstance(media_paths, str) else (media_paths or [])
            tag_list = json.loads(hashtags) if isinstance(hashtags, str) else (hashtags or [])
            tag_str = " ".join([t if t.startswith("#") else f"#{t}" for t in tag_list]) if tag_list else ""
            full_caption = f"{caption or ''}\n\n{tag_str}".strip()
            return {
                "media_path": media_list[0] if media_list else "",
                "caption": full_caption or "Discover our latest solution!",
            }
    except Exception as e:
        logger.debug(f"PG campaign lookup note: {e}")

    # 2. Try SQLite
    db_path = BASE_DIR / "data" / "database.sqlite"
    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT generated_caption, generated_hashtags, media_paths FROM campaigns WHERE id = ?", (campaign_id,))
            row = cur.fetchone()
            conn.close()
            if row:
                caption, hashtags, media_paths = row
                media_list = json.loads(media_paths) if isinstance(media_paths, str) else (media_paths or [])
                tag_list = json.loads(hashtags) if isinstance(hashtags, str) else (hashtags or [])
                tag_str = " ".join([t if t.startswith("#") else f"#{t}" for t in tag_list]) if tag_list else ""
                full_caption = f"{caption or ''}\n\n{tag_str}".strip()
                return {
                    "media_path": media_list[0] if media_list else "",
                    "caption": full_caption or "Discover our latest solution!",
                }
        except Exception as e:
            logger.debug(f"SQLite campaign lookup note: {e}")

    # 3. Fallback: find latest generated image in data/media/images
    img_dir = BASE_DIR / "data" / "media" / "images"
    latest_img = None
    if img_dir.exists():
        pngs = sorted(img_dir.glob("*.png"), key=os.path.getmtime, reverse=True)
        if pngs:
            latest_img = str(pngs[0])

    return {
        "media_path": latest_img or "",
        "caption": "Transform your business with intelligent AI automation! 🚀\n\n#AI #Automation #Marketing #Growth",
    }


def handle_callback_query(callback: dict):
    """Processes inline button clicks."""
    callback_id = callback.get("id")
    callback_data = callback.get("data", "")
    message = callback.get("message", {})
    chat_id = str(message.get("chat", {}).get("id"))

    logger.info(f"Received callback query: {callback_data} from chat {chat_id}")

    # 1. User clicked [✅ Approve & Post]
    if callback_data.startswith("approve:"):
        campaign_id = callback_data.split(":", 1)[1]
        answer_callback_query(callback_id, text="Approved! Please choose a platform.")
        # Send platform selection menu with action buttons
        send_platform_selection_menu(campaign_id, chat_id=chat_id)

    # 2. User selected a platform (e.g. post_to:facebook:<campaign_id>)
    elif callback_data.startswith("post_to:"):
        parts = callback_data.split(":")
        platform = parts[1].lower()
        campaign_id = parts[2] if len(parts) > 2 else ""

        answer_callback_query(callback_id, text=f"Selected {platform.capitalize()}!")
        send_text_message(chat_id, f"🚀 <b>Selected {platform.capitalize()}</b>. Connecting to browser and preparing post...")

        campaign_data = get_campaign_data(campaign_id)
        media_path = campaign_data.get("media_path")
        caption = campaign_data.get("caption")

        if platform == "facebook":
            # Check Facebook login
            from config import PLATFORM_URLS
            driver = browser.navigate("facebook", PLATFORM_URLS["facebook"])
            time.sleep(3)

            if is_facebook_login_needed(driver):
                # Save session state: waiting for user's password
                chat_sessions[chat_id] = {
                    "action": "AWAITING_PASSWORD",
                    "platform": "facebook",
                    "campaign_id": campaign_id,
                    "media_path": media_path,
                    "caption": caption,
                }
                send_password_request_prompt(chat_id, "facebook", campaign_id)
            else:
                # Already logged in! Post immediately
                send_text_message(chat_id, "✅ Facebook session verified. Publishing post now...")
                res = post_to_facebook(media_path=media_path, caption=caption)
                if res.get("status") == "success":
                    send_text_message(
                        chat_id,
                        f"🎉 <b>Success!</b> Post successfully published to Facebook!\n\n"
                        f"🖼️ Media: <code>{os.path.basename(media_path) if media_path else 'Graphic'}</code>\n"
                        f"📝 Caption preview: {caption[:120]}..."
                    )
                else:
                    send_text_message(chat_id, f"⚠️ Facebook post status: {res.get('message')}")

        else:
            send_text_message(chat_id, f"ℹ️ Automation for {platform.capitalize()} initialized.")

    # 3. User clicked [❌ Cancel]
    elif callback_data.startswith("cancel_post:"):
        answer_callback_query(callback_id, text="Posting cancelled.")
        send_text_message(chat_id, "❌ Post publication was cancelled.")

    # 4. User clicked [✏️ Suggest Revision]
    elif callback_data.startswith("revise:"):
        campaign_id = callback_data.split(":", 1)[1]
        answer_callback_query(callback_id)
        chat_sessions[chat_id] = {
            "action": "AWAITING_REVISION",
            "campaign_id": campaign_id,
        }
        send_text_message(
            chat_id,
            f"✏️ <b>Revision Requested</b>\n\nPlease reply with your feedback or instructions (e.g. <i>'Change tone to exciting, use cyan colors'</i>)."
        )

    # 5. User clicked [❌ Reject / Cancel]
    elif callback_data.startswith("reject:"):
        answer_callback_query(callback_id, text="Rejected.")
        send_text_message(chat_id, "❌ Campaign rejected. No post will be made.")

    # 6. User clicked [🚀 Generate: <Product>] from /start dashboard
    elif callback_data.startswith("gen_prod:"):
        prod_id = callback_data.split(":", 1)[1]
        answer_callback_query(callback_id, text="Initiating AI generation...")

        products = get_all_products()
        selected_prod = None
        for p in products:
            if str(p.get("id")) == prod_id:
                selected_prod = p
                break
        if not selected_prod and products:
            selected_prod = products[0]

        prod_name = selected_prod.get("name", "Featured Product") if selected_prod else "Featured Product"

        send_text_message(
            chat_id,
            f"🚀 <b>Generation Initiated for '{prod_name}'</b>\n\n"
            f"🤖 <b>Step 1 & 2:</b> Opening Chrome and prompting ChatGPT like a human...\n"
            f"🎨 <b>Step 3:</b> Generating custom visual graphic & viral post copy...\n"
            f"⏳ <i>Please wait ~35-50 seconds. The complete preview with approval buttons will be sent here!</i>"
        )

        import threading
        def _run_human_flow():
            try:
                from browser.human_operator import execute_human_generation_and_telegram_flow
                execute_human_generation_and_telegram_flow(
                    platform="chatgpt",
                    product=selected_prod or {"name": prod_name},
                    platforms=["facebook", "instagram"],
                )
            except Exception as e_run:
                logger.error(f"Error during Telegram triggered generation: {e_run}")
                send_text_message(chat_id, f"⚠️ Generation notice: {e_run}")

        threading.Thread(target=_run_human_flow, daemon=True).start()

    # 7. User clicked [ℹ️ How It Works]
    elif callback_data == "info:how_it_works":
        answer_callback_query(callback_id)
        send_text_message(
            chat_id,
            "💡 <b>How The Automation Works:</b>\n\n"
            "1️⃣ <b>Select Product</b>: Tap any product button or configure on http://localhost:3000.\n"
            "2️⃣ <b>Human Browser Flow</b>: Chrome opens ChatGPT with your profile and inputs the prompt all at once.\n"
            "3️⃣ <b>DALL-E & Copy</b>: Generates high-res visual artwork, headline, marketing copy & hashtags.\n"
            "4️⃣ <b>Telegram Review</b>: The bot delivers the preview with interactive Approve/Reject buttons.\n"
            "5️⃣ <b>Auto-Posting</b>: Upon approval, the bot navigates to Facebook and publishes your post!"
        )

    # 8. User clicked [📋 Active Products]
    elif callback_data == "info:products":
        answer_callback_query(callback_id)
        prods = get_all_products()
        if prods:
            p_lines = [f"• <b>{p.get('name')}</b> ({p.get('category', 'Product')}): <i>{p.get('description', '')[:70]}...</i>" for p in prods]
            send_text_message(chat_id, "📋 <b>Active Registered Products:</b>\n\n" + "\n".join(p_lines))
        else:
            send_text_message(chat_id, "📋 <i>No registered products found in database.</i>")


def handle_text_message(message: dict):
    """Processes user text messages in Telegram (such as passwords, start commands, or revision feedback)."""
    chat_id = str(message.get("chat", {}).get("id"))
    text = message.get("text", "").strip()
    msg_id = message.get("message_id")

    clean_text = text.lower().strip()
    if clean_text in ["/start", "start", "/help", "help", "hi", "hello", "menu", "/menu"]:
        products = get_all_products()
        send_start_dashboard(chat_id, products)
        return

    session = chat_sessions.get(chat_id)
    if not session:
        if text.startswith("/"):
            products = get_all_products()
            send_start_dashboard(chat_id, products)
        return

    # User provided password for a platform
    if session.get("action") == "AWAITING_PASSWORD":
        platform = session.get("platform", "facebook")
        media_path = session.get("media_path")
        caption = session.get("caption")

        # Delete user's password message from Telegram for security
        delete_telegram_message(chat_id, msg_id)

        send_text_message(chat_id, f"🔑 <b>Password received securely.</b> Ingesting into {platform.capitalize()} in Chrome...")

        # Parse password or email:password
        password = text
        email = None
        if ":" in text and not text.startswith("http"):
            parts = text.split(":", 1)
            email, password = parts[0].strip(), parts[1].strip()

        # Connect to browser and inject
        from config import PLATFORM_URLS
        driver = browser.navigate(platform, PLATFORM_URLS.get(platform, "https://www.facebook.com"))
        time.sleep(1)

        login_res = submit_facebook_login(driver, password=password, email_or_user=email)
        send_text_message(chat_id, f"🔐 {login_res.get('message', 'Login processed.')}")

        # Clear session
        del chat_sessions[chat_id]

        # Proceed to post
        time.sleep(3)
        send_text_message(chat_id, f"📝 Publishing post with media to {platform.capitalize()}...")
        post_res = post_to_facebook(media_path=media_path, caption=caption)

        if post_res.get("status") == "success":
            send_text_message(
                chat_id,
                f"🎉 <b>Success!</b> Authenticated & post published to {platform.capitalize()}!\n\n"
                f"🖼️ Media: <code>{os.path.basename(media_path) if media_path else 'Graphic'}</code>\n"
                f"📝 Caption preview: {caption[:120]}..."
            )
        else:
            send_text_message(chat_id, f"⚠️ Post result: {post_res.get('message')}")

    # User provided revision instructions
    elif session.get("action") == "AWAITING_REVISION":
        campaign_id = session.get("campaign_id")
        del chat_sessions[chat_id]
        send_text_message(chat_id, f"🔄 <b>Revision note recorded:</b> <i>\"{text}\"</i>\nRegenerating content now...")


def start_polling():
    """Continuously long-polls Telegram for updates."""
    bot_token, chat_id = get_telegram_credentials()
    if not bot_token:
        print("[ERROR] TELEGRAM_BOT_TOKEN not configured.", flush=True)
        return

    print("=" * 70, flush=True)
    print("🤖 TELEGRAM BOT POLLER DAEMON ACTIVE & LISTENING", flush=True)
    print(f"Target Chat ID: {chat_id or 'Any authorized user'}", flush=True)
    print("Supports: [Approve & Post] -> Platform Selection -> Facebook Posting & Password Ingestion", flush=True)
    print("=" * 70, flush=True)

    offset = None

    while True:
        try:
            params = {"timeout": 20}
            if offset:
                params["offset"] = offset

            res = make_telegram_request(bot_token, "getUpdates", data=params)

            if res.get("ok") and "result" in res:
                updates = res["result"]
                for update in updates:
                    offset = update["update_id"] + 1

                    if "callback_query" in update:
                        handle_callback_query(update["callback_query"])

                    elif "message" in update:
                        handle_text_message(update["message"])

            time.sleep(1)

        except KeyboardInterrupt:
            print("\nPoller stopped.", flush=True)
            break
        except Exception as e:
            logger.error(f"Error in polling loop: {e}")
            time.sleep(3)


if __name__ == "__main__":
    start_polling()
