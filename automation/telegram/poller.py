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
import uuid
import logging
from pathlib import Path

# Ensure UTF-8 output on Windows and unbuffered streaming
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
except Exception:
    pass

BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "automation"))
sys.path.insert(0, str(Path(__file__).parent))

import config

try:
    from bot import (
        get_telegram_credentials,
        make_telegram_request,
        answer_callback_query,
        build_platform_keyboard,
        send_platform_selection_menu,
        send_password_request_prompt,
        delete_telegram_message,
        send_text_message,
        send_start_dashboard,
        send_start_flow_menu,
        send_llm_selection_menu,
        send_product_selection_menu,
        edit_message_text,
        edit_message_caption,
        edit_message_reply_markup,
        send_root_choice_menu,
        send_outreach_platform_menu,
        send_outreach_location_menu,
        send_outreach_count_menu,
        send_antigravity_menu,
        send_antigravity_running_windows_menu,
        send_task_completion_message,
    )
except (ImportError, ModuleNotFoundError):
    from telegram.bot import (
        get_telegram_credentials,
        make_telegram_request,
        answer_callback_query,
        build_platform_keyboard,
        send_platform_selection_menu,
        send_password_request_prompt,
        delete_telegram_message,
        send_text_message,
        send_start_dashboard,
        send_start_flow_menu,
        send_llm_selection_menu,
        send_product_selection_menu,
        edit_message_text,
        edit_message_caption,
        edit_message_reply_markup,
        send_root_choice_menu,
        send_outreach_platform_menu,
        send_outreach_location_menu,
        send_outreach_count_menu,
        send_antigravity_menu,
        send_antigravity_running_windows_menu,
        send_task_completion_message,
    )
from social.facebook import is_facebook_login_needed, submit_facebook_login, post_to_facebook
from social.instagram import post_to_instagram
from social.linkedin import post_to_linkedin
from social.growth_orchestrator import run_growth_campaign, stop_growth_campaign
from remote.antigravity_controller import (
    allocate_new_task,
    update_task_status,
    inject_prompt_to_antigravity,
)
from browser.driver import browser

logger = logging.getLogger("automation.telegram.poller")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# In-memory session state per chat_id
chat_sessions = {}


LOAN_SOLUTIONS_PATH = str(BASE_DIR / "Loan Solutions.png")


def get_all_products() -> list:
    """Finds all registered products from PostgreSQL or SQLite, automatically resolving logo paths."""
    products = []
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
        cur.execute("SELECT id, name, category, description, logo_path FROM products ORDER BY name ASC")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        if rows:
            for r in rows:
                p_name = r[1] or ""
                p_logo = r[4]
                if "loan" in p_name.lower():
                    if not p_logo or not os.path.exists(str(p_logo)):
                        if os.path.exists(LOAN_SOLUTIONS_PATH):
                            p_logo = LOAN_SOLUTIONS_PATH
                products.append({
                    "id": str(r[0]),
                    "name": p_name,
                    "category": r[2],
                    "description": r[3],
                    "logo_path": p_logo
                })
            return products
    except Exception as e:
        logger.debug(f"PG products lookup note: {e}")

    # 2. Try SQLite
    db_path = BASE_DIR / "data" / "database.sqlite"
    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT id, name, category, description, logo_path FROM products ORDER BY name ASC")
            rows = cur.fetchall()
            conn.close()
            if rows:
                for r in rows:
                    p_name = r[1] or ""
                    p_logo = r[4]
                    if "loan" in p_name.lower():
                        if not p_logo or not os.path.exists(str(p_logo)):
                            if os.path.exists(LOAN_SOLUTIONS_PATH):
                                p_logo = LOAN_SOLUTIONS_PATH
                    products.append({
                        "id": str(r[0]),
                        "name": p_name,
                        "category": r[2],
                        "description": r[3],
                        "logo_path": p_logo
                    })
                return products
        except Exception as e:
            logger.debug(f"SQLite products lookup note: {e}")

    return products


def update_loan_solution_logo_db(logo_path: str):
    """Updates logo_path for Loan Solutions in PostgreSQL and SQLite."""
    try:
        import psycopg2
        pg_user = os.environ.get("DB_USER", "postgres")
        pg_pass = os.environ.get("DB_PASSWORD", "Shivam@123")
        pg_host = os.environ.get("DB_HOST", "localhost")
        pg_port = int(os.environ.get("DB_PORT", "5432"))
        pg_db = os.environ.get("DB_NAME", "Social_Media")
        conn = psycopg2.connect(dbname=pg_db, user=pg_user, password=pg_pass, host=pg_host, port=pg_port)
        cur = conn.cursor()
        cur.execute("UPDATE products SET logo_path = %s WHERE name ILIKE '%loan%'", (logo_path,))
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Updated PostgreSQL logo_path for Loan Solutions to: {logo_path}")
    except Exception as e:
        logger.debug(f"PG logo update note: {e}")

    db_path = BASE_DIR / "data" / "database.sqlite"
    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("UPDATE products SET logo_path = ? WHERE name LIKE '%Loan%'", (logo_path,))
            conn.commit()
            conn.close()
            logger.info(f"Updated SQLite logo_path for Loan Solutions to: {logo_path}")
        except Exception as e:
            logger.debug(f"SQLite logo update note: {e}")




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
        cur.execute("""
            SELECT c.generated_caption, c.generated_hashtags, c.media_paths, p.name, p.category, p.website_url
            FROM campaigns c
            LEFT JOIN products p ON c.product_id = p.id
            WHERE c.id = %s
        """, (campaign_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            caption, hashtags, media_paths, p_name, p_cat, p_web = row
            media_list = json.loads(media_paths) if isinstance(media_paths, str) else (media_paths or [])
            tag_list = json.loads(hashtags) if isinstance(hashtags, str) else (hashtags or [])
            tag_str = " ".join([t if t.startswith("#") else f"#{t}" for t in tag_list]) if tag_list else ""
            
            is_loan = ("loan" in str(p_name).lower()) or ("finance" in str(p_cat).lower()) or ("loan" in str(caption).lower())
            apply_url = "https://loansolutions.everythingrental.in/application"
            if is_loan and apply_url not in str(caption):
                full_caption = f"{caption or ''}\n\n👉 Apply Now: {apply_url}\n\n{tag_str}".strip()
            else:
                full_caption = f"{caption or ''}\n\n{tag_str}".strip()
            return {
                "media_path": media_list[0] if media_list else "",
                "caption": full_caption or "Discover our latest solution!",
                "product_name": p_name or "",
                "product_category": p_cat or "",
                "apply_url": apply_url if is_loan else None
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
            cur.execute("""
                SELECT c.generated_caption, c.generated_hashtags, c.media_paths, p.name, p.category, p.website_url
                FROM campaigns c
                LEFT JOIN products p ON c.product_id = p.id
                WHERE c.id = ?
            """, (campaign_id,))
            row = cur.fetchone()
            conn.close()
            if row:
                caption, hashtags, media_paths, p_name, p_cat, p_web = row
                media_list = json.loads(media_paths) if isinstance(media_paths, str) else (media_paths or [])
                tag_list = json.loads(hashtags) if isinstance(hashtags, str) else (hashtags or [])
                tag_str = " ".join([t if t.startswith("#") else f"#{t}" for t in tag_list]) if tag_list else ""
                
                is_loan = ("loan" in str(p_name).lower()) or ("finance" in str(p_cat).lower()) or ("loan" in str(caption).lower())
                apply_url = "https://loansolutions.everythingrental.in/application"
                if is_loan and apply_url not in str(caption):
                    full_caption = f"{caption or ''}\n\n👉 Apply Now: {apply_url}\n\n{tag_str}".strip()
                else:
                    full_caption = f"{caption or ''}\n\n{tag_str}".strip()
                return {
                    "media_path": media_list[0] if media_list else "",
                    "caption": full_caption or "Discover our latest solution!",
                    "product_name": p_name or "",
                    "product_category": p_cat or "",
                    "apply_url": apply_url if is_loan else None
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


def update_campaign_status_db(
    campaign_id: str,
    status: str = "posted",
    platform: str = None,
    media_path: str = None,
    caption: str = None
):
    """
    Updates or inserts campaign record in PostgreSQL and SQLite.
    Guarantees that posts published via Telegram are saved in campaigns with all details.
    """
    if not campaign_id:
        return False
    try:
        from db_campaigns import save_or_update_campaign
        return save_or_update_campaign(
            campaign_id=campaign_id,
            status=status,
            platforms=[platform] if platform else None,
            media_path=media_path,
            caption=caption,
            posted_at_now=(status == "posted")
        )
    except Exception as e:
        logger.error(f"Error updating campaign status DB: {e}")
        return False


def launch_outreach_campaign(chat_id: str, platform: str, location: str, target_count: int, message_id: int = None):
    """Executes outreach campaign and manages live progress display in Telegram."""
    campaign_id = str(uuid.uuid4())[:8]

    plat_title = {
        "both": "⚡ Facebook + Instagram Simultaneously",
        "facebook": "📘 Facebook Friend Requests",
        "instagram": "📸 Instagram Follow Requests"
    }.get(platform, platform.capitalize())

    init_text = (
        f"👥 <b>Growth Outreach Initiated!</b>\n\n"
        f"🎯 <b>Target:</b> {plat_title}\n"
        f"📍 <b>Location Filter:</b> <code>{location}</code>\n"
        f"🔢 <b>Count:</b> {target_count} requests\n"
        f"🆔 <b>Campaign ID:</b> <code>{campaign_id}</code>\n\n"
        f"⏳ <b>Status:</b> Initializing browser sessions & preparing search filters..."
    )

    stop_keyboard = {
        "inline_keyboard": [
            [{"text": "🛑 Emergency Stop", "callback_data": f"outreach:stop:{campaign_id}"}]
        ]
    }

    sent_msg_id = None
    if message_id:
        try:
            res = edit_message_text(chat_id, message_id, init_text, keyboard=stop_keyboard)
            if res.get("ok"):
                sent_msg_id = message_id
        except Exception:
            pass

    if not sent_msg_id:
        res_msg = send_text_message(chat_id, init_text, reply_markup=stop_keyboard)
        if res_msg.get("response", {}).get("result"):
            sent_msg_id = res_msg["response"]["result"].get("message_id")

    import threading
    def _exec_growth():
        try:
            run_growth_campaign(
                campaign_id=campaign_id,
                platform=platform,
                location=location,
                target_count=target_count,
                safety_delay=15,
                telegram_chat_id=chat_id,
                telegram_message_id=sent_msg_id
            )
        except Exception as e_growth:
            logger.error(f"Error in growth campaign thread: {e_growth}")
            send_text_message(chat_id, f"⚠️ Outreach error notice: {e_growth}")

    threading.Thread(target=_exec_growth, daemon=True).start()


def launch_multi_platform_publication(chat_id: str, campaign_id: str, platforms: list, message_id: int = None):
    """
    Publishes post to multiple social platforms (Facebook, Instagram, LinkedIn, WhatsApp)
    in coordinated sequence with live Telegram progress reporting!
    """
    import threading

    def _exec():
        try:
            campaign_data = get_campaign_data(campaign_id)
            media_path = campaign_data.get("media_path")
            caption = campaign_data.get("caption")

            plat_names = [p.capitalize() for p in platforms]
            init_text = (
                f"🚀 <b>Multi-Platform Broadcast Started!</b>\n\n"
                f"🎯 <b>Target Platforms ({len(platforms)}):</b> {', '.join(plat_names)}\n"
                f"🖼️ <b>Media:</b> <code>{os.path.basename(media_path) if media_path else 'Branded Graphic'}</code>\n"
                f"⏳ <b>Status:</b> Initializing browser sessions & preparing posts..."
            )
            if message_id:
                try:
                    edit_message_text(chat_id, message_id, init_text)
                except Exception:
                    pass

            successful_platforms = []
            failed_platforms = []

            for idx, plat in enumerate(platforms):
                plat_clean = plat.lower().strip()
                p_label = {
                    "facebook": "📘 Facebook",
                    "instagram": "📸 Instagram",
                    "linkedin": "💼 LinkedIn",
                    "whatsapp": "💬 WhatsApp"
                }.get(plat_clean, plat_clean.capitalize())

                send_text_message(
                    chat_id,
                    f"⏳ <b>Step {idx+1}/{len(platforms)}: Publishing to {p_label}...</b>"
                )

                try:
                    if plat_clean == "facebook":
                        from config import PLATFORM_URLS
                        driver = browser.navigate("facebook", PLATFORM_URLS["facebook"])
                        time.sleep(2)
                        if is_facebook_login_needed(driver):
                            chat_sessions[chat_id] = {
                                "action": "AWAITING_PASSWORD",
                                "platform": "facebook",
                                "campaign_id": campaign_id,
                                "media_path": media_path,
                                "caption": caption,
                                "remaining_platforms": platforms[idx+1:]
                            }
                            send_password_request_prompt(chat_id, "facebook", campaign_id)
                            # Pause execution to await password
                            return
                        else:
                            res = post_to_facebook(media_path=media_path, caption=caption)
                            if res.get("status") == "success":
                                successful_platforms.append("Facebook")
                                send_text_message(chat_id, "✅ <b>Facebook:</b> Successfully published!")
                            else:
                                failed_platforms.append(f"Facebook ({res.get('message', 'error')})")
                                send_text_message(chat_id, f"⚠️ Facebook notice: {res.get('message')}")

                    elif plat_clean == "instagram":
                        res = post_to_instagram(media_path=media_path, caption=caption)
                        if res.get("status") == "success":
                            successful_platforms.append("Instagram")
                            send_text_message(chat_id, "✅ <b>Instagram:</b> Successfully published!")
                        else:
                            failed_platforms.append(f"Instagram ({res.get('message', 'error')})")
                            send_text_message(chat_id, f"⚠️ Instagram notice: {res.get('message')}")

                    elif plat_clean == "linkedin":
                        res = post_to_linkedin(media_path=media_path, caption=caption)
                        if res.get("status") == "success":
                            successful_platforms.append("LinkedIn")
                            send_text_message(chat_id, "✅ <b>LinkedIn:</b> Successfully published!")
                        else:
                            failed_platforms.append(f"LinkedIn ({res.get('message', 'error')})")
                            send_text_message(chat_id, f"⚠️ LinkedIn notice: {res.get('message')}")

                    elif plat_clean == "whatsapp":
                        from social.whatsapp import post_to_whatsapp
                        res = post_to_whatsapp(media_path=media_path, caption=caption)
                        if res.get("status") == "success":
                            successful_platforms.append("WhatsApp")
                            send_text_message(chat_id, "✅ <b>WhatsApp:</b> Successfully published!")
                        else:
                            failed_platforms.append(f"WhatsApp ({res.get('message', 'error')})")
                            send_text_message(chat_id, f"⚠️ WhatsApp notice: {res.get('message')}")

                except Exception as e_p:
                    logger.error(f"Error publishing to {plat_clean}: {e_p}")
                    failed_platforms.append(f"{plat_clean.capitalize()} ({e_p})")
                    send_text_message(chat_id, f"⚠️ Error publishing to {plat_clean}: {e_p}")

                # Human-like delay between multiple platform posts
                if idx < len(platforms) - 1:
                    time.sleep(2.5)

            # Record in database
            if successful_platforms:
                update_campaign_status_db(
                    campaign_id,
                    status="posted",
                    platform=",".join([p.lower() for p in successful_platforms]),
                    media_path=media_path,
                    caption=caption
                )

            # Send final celebratory summary card
            succ_str = "\n".join([f"• ✅ <b>{p}</b>" for p in successful_platforms]) if successful_platforms else "None"
            fail_str = f"\n\n⚠️ <b>Issues:</b>\n" + "\n".join([f"• ❌ {p}" for p in failed_platforms]) if failed_platforms else ""

            summary_text = (
                f"🎉 <b>Multi-Platform Broadcast Summary</b>\n\n"
                f"<b>Successfully Published To:</b>\n{succ_str}{fail_str}\n\n"
                f"🖼️ <b>Media:</b> <code>{os.path.basename(media_path) if media_path else 'Graphic'}</code>\n"
                f"📝 <b>Caption:</b>\n{caption[:160]}...\n\n"
                f"<i>Campaign {campaign_id[:8]} marked as posted in database.</i>"
            )
            send_text_message(chat_id, summary_text)

        except Exception as e_main:
            logger.error(f"Error in multi-platform execution: {e_main}")
            send_text_message(chat_id, f"⚠️ Multi-platform broadcast error: {e_main}")

    threading.Thread(target=_exec, daemon=True).start()


def handle_callback_query(callback: dict):
    """Processes inline button clicks."""
    callback_id = callback.get("id")
    callback_data = callback.get("data", "")
    message = callback.get("message") or {}
    chat = message.get("chat") or {}
    user = callback.get("from") or {}
    chat_id = str(chat.get("id") or user.get("id") or "")
    message_id = message.get("message_id")

    logger.info(f"Received callback query: {callback_data} from chat {chat_id}")

    # No-op callback (for informative buttons)
    if callback_data == "noop":
        if callback_id:
            answer_callback_query(callback_id)
        return

    # 1. User clicked [✅ Approve & Post]
    if callback_data.startswith("approve:"):
        campaign_id = callback_data.split(":", 1)[1] if ":" in callback_data else ""
        if callback_id:
            answer_callback_query(callback_id, text="✅ Campaign Approved! Choose platform(s) below.")

        # Default multi-selection is Facebook + Instagram
        default_plats = ["facebook", "instagram"]
        chat_sessions[chat_id] = {
            "selected_platforms": default_plats,
            "campaign_id": campaign_id
        }

        # Update buttons on the preview message so user sees approved state
        if message_id and chat_id:
            try:
                edit_message_reply_markup(
                    chat_id,
                    message_id,
                    keyboard={"inline_keyboard": [[{"text": "✅ Approved (Selecting platforms ⬇️)", "callback_data": "noop"}]]}
                )
            except Exception as e_ed:
                logger.debug(f"Edit preview markup note: {e_ed}")

        # Send multi-platform selection menu with action buttons and live checkboxes
        send_platform_selection_menu(campaign_id, chat_id=chat_id, selected_platforms=default_plats)

    # 2. User toggles a platform (checkbox toggle)
    elif callback_data.startswith("toggle_plat:"):
        parts = callback_data.split(":")
        platform = parts[1].lower() if len(parts) > 1 else "facebook"
        campaign_id = parts[2] if len(parts) > 2 else ""

        session = chat_sessions.setdefault(chat_id, {})
        current = session.get("selected_platforms", ["facebook", "instagram"])
        if platform in current:
            current = [p for p in current if p != platform]
            status_text = f"Removed {platform.capitalize()} ⬜"
        else:
            current.append(platform)
            status_text = f"Selected {platform.capitalize()} ✅"
        session["selected_platforms"] = current
        session["campaign_id"] = campaign_id

        if callback_id:
            answer_callback_query(callback_id, text=status_text)

        if message_id and chat_id:
            try:
                edit_message_reply_markup(
                    chat_id,
                    message_id,
                    keyboard=build_platform_keyboard(campaign_id, current)
                )
            except Exception as e_tg:
                logger.debug(f"Toggle platform markup note: {e_tg}")

    # 3. User clicked [✨ Select All]
    elif callback_data.startswith("plat_select_all:"):
        campaign_id = callback_data.split(":", 1)[1] if ":" in callback_data else ""
        all_plats = ["facebook", "instagram", "linkedin", "whatsapp"]
        chat_sessions.setdefault(chat_id, {})["selected_platforms"] = all_plats
        chat_sessions[chat_id]["campaign_id"] = campaign_id
        if callback_id:
            answer_callback_query(callback_id, text="Selected all 4 platforms! ✅")
        if message_id and chat_id:
            try:
                edit_message_reply_markup(
                    chat_id,
                    message_id,
                    keyboard=build_platform_keyboard(campaign_id, all_plats)
                )
            except Exception as e_sa:
                logger.debug(f"Select all markup note: {e_sa}")

    # 4. User clicked [🔄 Clear All]
    elif callback_data.startswith("plat_clear_all:"):
        campaign_id = callback_data.split(":", 1)[1] if ":" in callback_data else ""
        chat_sessions.setdefault(chat_id, {})["selected_platforms"] = []
        chat_sessions[chat_id]["campaign_id"] = campaign_id
        if callback_id:
            answer_callback_query(callback_id, text="Cleared all selections 🔄")
        if message_id and chat_id:
            try:
                edit_message_reply_markup(
                    chat_id,
                    message_id,
                    keyboard=build_platform_keyboard(campaign_id, [])
                )
            except Exception as e_ca:
                logger.debug(f"Clear all markup note: {e_ca}")

    # 5. User clicked [🚀 Publish to X Selected Platforms]
    elif callback_data.startswith("publish_multi:"):
        campaign_id = callback_data.split(":", 1)[1] if ":" in callback_data else ""
        session = chat_sessions.get(chat_id, {})
        selected = session.get("selected_platforms", ["facebook", "instagram"])
        if not selected:
            if callback_id:
                answer_callback_query(callback_id, text="⚠️ Please select at least one platform before publishing!")
            return

        plat_str = " + ".join([p.capitalize() for p in selected])
        if callback_id:
            answer_callback_query(callback_id, text=f"🚀 Broadcasting to {plat_str}!")

        launch_multi_platform_publication(chat_id, campaign_id, selected, message_id=message_id)

    # 6. Legacy single-platform button fallback (e.g. post_to:facebook:<campaign_id>)
    elif callback_data.startswith("post_to:"):
        parts = callback_data.split(":")
        platform = parts[1].lower() if len(parts) > 1 else "facebook"
        campaign_id = parts[2] if len(parts) > 2 else ""

        if callback_id:
            answer_callback_query(callback_id, text=f"🚀 Selected {platform.capitalize()}!")

        launch_multi_platform_publication(chat_id, campaign_id, [platform], message_id=message_id)

    # 3. User clicked [❌ Cancel] on Platform selection menu
    elif callback_data.startswith("cancel_post:"):
        if callback_id:
            answer_callback_query(callback_id, text="❌ Post publication cancelled.")
        if message_id and chat_id:
            try:
                edit_message_text(chat_id, message_id, "❌ <b>Post publication was cancelled.</b> No post will be made.")
            except Exception:
                send_text_message(chat_id, "❌ <b>Post publication was cancelled.</b> No post will be made.")
        else:
            send_text_message(chat_id, "❌ <b>Post publication was cancelled.</b> No post will be made.")

    # 4. User clicked [✏️ Suggest Revision]
    elif callback_data.startswith("revise:"):
        campaign_id = callback_data.split(":", 1)[1] if ":" in callback_data else ""
        if callback_id:
            answer_callback_query(callback_id, text="✏️ Revision requested.")
        chat_sessions[chat_id] = {
            "action": "AWAITING_REVISION",
            "campaign_id": campaign_id,
            "message_id": message_id,
        }
        send_text_message(
            chat_id,
            f"✏️ <b>Revision Requested</b>\n\n"
            f"Please reply directly to this message with your requested changes (e.g. <i>'Change tone to exciting, use cyan and gold colors, highlight 20% discount'</i>).\n\n"
            f"🤖 <i>The AI will automatically regenerate the post copy & visual graphic and send you a new preview!</i>"
        )

    # 5. User clicked [❌ Reject / Cancel] on Preview message
    elif callback_data.startswith("reject:"):
        campaign_id = callback_data.split(":", 1)[1] if ":" in callback_data else ""
        if callback_id:
            answer_callback_query(callback_id, text="❌ Campaign rejected & cancelled.")
        if campaign_id:
            update_campaign_status_db(campaign_id, "rejected")
        if message_id and chat_id:
            try:
                edit_message_reply_markup(
                    chat_id,
                    message_id,
                    keyboard={"inline_keyboard": [[{"text": "❌ Rejected / Cancelled", "callback_data": "noop"}]]}
                )
            except Exception as e_ed:
                logger.debug(f"Edit reject markup note: {e_ed}")
        send_text_message(chat_id, "❌ <b>Campaign rejected & cancelled.</b> No post will be made.")

    # 6. Flow Step 1: Return to Start Menu (Image vs Video)
    elif callback_data == "flow:start":
        if callback_id:
            answer_callback_query(callback_id)
        send_start_flow_menu(chat_id, message_id=message_id)

    # 7. Flow Step 2: Content Type Selected (Image or Video)
    elif callback_data.startswith("flow:type:"):
        content_type = callback_data.split(":", 2)[2].lower()
        if callback_id:
            answer_callback_query(callback_id)

        if content_type == "video":
            # NOTE: For video it automatically selects the Gemini LLM
            products = get_all_products()
            send_product_selection_menu(
                chat_id=chat_id,
                content_type="video",
                llm_provider="gemini",
                products=products,
                message_id=message_id
            )
        else:
            # For image: asks which LLM model to use (Gemini, ChatGPT, Claude)
            send_llm_selection_menu(chat_id=chat_id, content_type="image", message_id=message_id)

    # 8. Flow Step 3: LLM Model Selected for Image (Gemini, ChatGPT, Claude)
    elif callback_data.startswith("flow:llm:"):
        parts = callback_data.split(":")
        llm_provider = parts[2].lower() if len(parts) > 2 else "chatgpt"
        content_type = parts[3].lower() if len(parts) > 3 else "image"
        if callback_id:
            answer_callback_query(callback_id)

        products = get_all_products()
        send_product_selection_menu(
            chat_id=chat_id,
            content_type=content_type,
            llm_provider=llm_provider,
            products=products,
            message_id=message_id
        )

    # 9. Flow Step 4: Product Selected -> Run Generation with selected format & LLM
    elif callback_data.startswith("flow:run:"):
        parts = callback_data.split(":")
        content_type = parts[2].lower() if len(parts) > 2 else "image"
        llm_provider = parts[3].lower() if len(parts) > 3 else "gemini"
        prod_id = parts[4] if len(parts) > 4 else ""

        provider_title = {
            "gemini": "Gemini (Google AI)",
            "chatgpt": "ChatGPT (OpenAI)",
            "claude": "Claude (Anthropic)"
        }.get(llm_provider, llm_provider.capitalize())

        format_title = "Video Reel (9:16)" if content_type == "video" else "Image Post"

        if callback_id:
            answer_callback_query(callback_id, text=f"🚀 Generating {format_title} with {llm_provider.capitalize()}...")

        products = get_all_products()
        selected_prod = None
        for p in products:
            if str(p.get("id")) == prod_id:
                selected_prod = p
                break
        if not selected_prod and products:
            selected_prod = products[0]

        prod_name = selected_prod.get("name", "Featured Product") if selected_prod else "Featured Product"

        status_text = (
            f"🚀 <b>Generation Initiated!</b>\n\n"
            f"📦 <b>Product:</b> {prod_name}\n"
            f"🎨 <b>Format:</b> {format_title}\n"
            f"🤖 <b>AI Engine:</b> {provider_title}\n\n"
            f"🤖 <b>Step 1 & 2:</b> Opening Chrome and prompting {llm_provider.capitalize()} like a human...\n"
            f"🎨 <b>Step 3:</b> Generating custom {'promo video reel' if content_type == 'video' else 'visual graphic'} & viral copy...\n"
            f"⏳ <i>Please wait ~35-50 seconds. The complete preview with approval buttons will arrive here!</i>"
        )

        if message_id and chat_id:
            try:
                edit_message_text(chat_id, message_id, status_text)
            except Exception:
                send_text_message(chat_id, status_text)
        else:
            send_text_message(chat_id, status_text)

        import threading
        def _run_flow():
            try:
                from browser.human_operator import execute_human_generation_and_telegram_flow
                logo_to_use = selected_prod.get("logo_path") if selected_prod else None
                if not logo_to_use and os.path.exists(LOAN_SOLUTIONS_PATH):
                    logo_to_use = LOAN_SOLUTIONS_PATH

                execute_human_generation_and_telegram_flow(
                    platform=llm_provider,
                    product=selected_prod or {"name": prod_name, "logo_path": logo_to_use},
                    content_type=content_type,
                    skill_image_path=logo_to_use,
                    platforms=["facebook", "instagram"],
                )
            except Exception as e_run:
                logger.error(f"Error during flow generation: {e_run}")
                send_text_message(chat_id, f"⚠️ Generation notice: {e_run}")

        threading.Thread(target=_run_flow, daemon=True).start()

    # Legacy fallback: User clicked [🚀 Generate: <Product>] from old message
    elif callback_data.startswith("gen_prod:"):
        prod_id = callback_data.split(":", 1)[1] if ":" in callback_data else ""
        if callback_id:
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
                logo_to_use = selected_prod.get("logo_path") if selected_prod else None
                if not logo_to_use and os.path.exists(LOAN_SOLUTIONS_PATH):
                    logo_to_use = LOAN_SOLUTIONS_PATH

                execute_human_generation_and_telegram_flow(
                    platform="chatgpt",
                    product=selected_prod or {"name": prod_name, "logo_path": logo_to_use},
                    skill_image_path=logo_to_use,
                    platforms=["facebook", "instagram"],
                )
            except Exception as e_run:
                logger.error(f"Error during Telegram triggered generation: {e_run}")
                send_text_message(chat_id, f"⚠️ Generation notice: {e_run}")

        threading.Thread(target=_run_human_flow, daemon=True).start()

    # 10. User clicked [ℹ️ How It Works]
    elif callback_data == "info:how_it_works":
        if callback_id:
            answer_callback_query(callback_id)
        send_text_message(
            chat_id,
            "💡 <b>How The Automation Works:</b>\n\n"
            "1️⃣ <b>Select Format & AI</b>: Choose Image or Video, then choose Gemini, ChatGPT, or Claude (Video auto-selects Gemini).\n"
            "2️⃣ <b>Select Product</b>: Choose any of your registered products.\n"
            "3️⃣ <b>Human Browser Flow</b>: Chrome opens the selected AI with your profile and inputs the prompt like a human.\n"
            "4️⃣ <b>Creative Media & Copy</b>: Generates high-res visual artwork / video reel, marketing copy & hashtags.\n"
            "5️⃣ <b>Telegram Review</b>: The bot delivers the preview with interactive Approve/Reject buttons.\n"
            "6️⃣ <b>Auto-Publishing</b>: Upon approval, select Facebook, Instagram, LinkedIn, or WhatsApp to publish!"
        )

    # 11. User clicked [📋 Active Products]
    elif callback_data == "info:products":
        if callback_id:
            answer_callback_query(callback_id)
        prods = get_all_products()
        if prods:
            p_lines = [f"• <b>{p.get('name')}</b> ({p.get('category', 'Product')}): <i>{p.get('description', '')[:70]}...</i>" for p in prods]
            send_text_message(chat_id, "📋 <b>Active Registered Products:</b>\n\n" + "\n".join(p_lines))
        else:
            send_text_message(chat_id, "📋 <i>No registered products found in database.</i>")

    # 12. Root Menu: Return to main root menu
    elif callback_data == "root:main":
        if callback_id:
            answer_callback_query(callback_id)
        send_root_choice_menu(chat_id, message_id=message_id)

    # 13. Root Choice 1: Content Generation Flow
    elif callback_data == "root:content":
        if callback_id:
            answer_callback_query(callback_id)
        send_start_flow_menu(chat_id, message_id=message_id)

    # 14. Root Choice 2: Growth & Outreach Flow -> Step 1: Select Platform
    elif callback_data == "root:outreach":
        if callback_id:
            answer_callback_query(callback_id)
        send_outreach_platform_menu(chat_id, message_id=message_id)

    # 15. Outreach Step 2: Platform Selected -> Select Location
    elif callback_data.startswith("outreach:plat:"):
        platform = callback_data.split(":", 2)[2].lower()
        if callback_id:
            answer_callback_query(callback_id)
        send_outreach_location_menu(chat_id, platform=platform, message_id=message_id)

    # 16. Outreach Custom Location: Prompt user to type location text
    elif callback_data.startswith("outreach:loc_custom:"):
        platform = callback_data.split(":", 2)[2].lower()
        if callback_id:
            answer_callback_query(callback_id)
        chat_sessions[chat_id] = {
            "action": "AWAITING_OUTREACH_LOCATION",
            "platform": platform,
            "message_id": message_id
        }
        send_text_message(
            chat_id,
            f"📍 <b>Custom Location for {platform.capitalize()} Outreach</b>\n\n"
            "Please type the name of the target city or location (e.g. <code>New York</code>, <code>Mumbai</code>, <code>San Francisco</code>):\n\n"
            "<i>(Type /cancel anytime to return to the menu)</i>"
        )

    # 17. Outreach Step 3: Location Selected -> Select Count
    elif callback_data.startswith("outreach:loc:"):
        parts = callback_data.split(":")
        platform = parts[2].lower() if len(parts) > 2 else "both"
        location = parts[3] if len(parts) > 3 else "Global"
        if callback_id:
            answer_callback_query(callback_id)
        send_outreach_count_menu(chat_id, platform=platform, location=location, message_id=message_id)

    # 18. Outreach Custom Count Selection
    elif callback_data.startswith("outreach:count_custom:"):
        parts = callback_data.split(":")
        platform = parts[2].lower() if len(parts) > 2 else "both"
        location = parts[3] if len(parts) > 3 else "Global"
        if callback_id:
            answer_callback_query(callback_id)
        chat_sessions[chat_id] = {
            "action": "AWAITING_OUTREACH_COUNT",
            "platform": platform,
            "location": location,
            "message_id": message_id
        }
        plat_label = {
            "both": "⚡ Dual (Facebook + Instagram)",
            "facebook": "📘 Facebook Friends",
            "instagram": "📸 Instagram Follows"
        }.get(platform, platform.capitalize())
        send_text_message(
            chat_id,
            f"🎯 <b>Custom Outreach Request Count</b>\n\n"
            f"👥 <b>Platform:</b> {plat_label}\n"
            f"📍 <b>Location:</b> <code>{location}</code>\n\n"
            "Please type the number of requests you would like to send (e.g. <code>15</code>, <code>35</code>, <code>75</code>, <code>100</code>):\n\n"
            "<i>(Type /cancel anytime to return to the menu)</i>"
        )

    # 19. Outreach Execution: Run outreach with preset (platform, location, count)
    elif callback_data.startswith("outreach:run:"):
        parts = callback_data.split(":")
        platform = parts[2].lower() if len(parts) > 2 else "both"
        location = parts[3] if len(parts) > 3 else "Global"
        try:
            target_count = int(parts[4]) if len(parts) > 4 else 10
        except ValueError:
            target_count = 10

        if callback_id:
            answer_callback_query(callback_id, text=f"🚀 Launching outreach for {location}...")

        launch_outreach_campaign(chat_id, platform=platform, location=location, target_count=target_count, message_id=message_id)

    # 19. Outreach Stop Signal
    elif callback_data.startswith("outreach:stop:"):
        campaign_id = callback_data.split(":", 2)[2] if ":" in callback_data else ""
        if callback_id:
            answer_callback_query(callback_id, text="🛑 Halting outreach campaign safely...")
        stop_growth_campaign(campaign_id)
        send_text_message(
            chat_id,
            f"🛑 <b>Campaign Stop Signal Sent</b> for ID <code>{campaign_id}</code>.\n\n"
            "Automation is finishing the current browser action and will cleanly park the session."
        )

    # 20. Antigravity & Laptop Remote Prompt Control: Open menu
    elif callback_data == "root:antigravity":
        if callback_id:
            answer_callback_query(callback_id)
        chat_sessions[chat_id] = {"action": "AWAITING_ANTIGRAVITY_PROMPT", "mode": "antigravity_chat"}
        send_antigravity_menu(chat_id, message_id=message_id, selected_mode="antigravity_chat")

    # 21. Antigravity Mode Selection
    elif callback_data.startswith("agy:setmode:"):
        mode = callback_data.split(":", 2)[2]
        if callback_id:
            answer_callback_query(callback_id, text=f"🎯 Target set to: {mode}")
        chat_sessions[chat_id] = {"action": "AWAITING_ANTIGRAVITY_PROMPT", "mode": mode}
        send_antigravity_menu(chat_id, message_id=message_id, selected_mode=mode)

    # 22. Antigravity List Running Windows on Laptop
    elif callback_data == "agy:windows":
        if callback_id:
            answer_callback_query(callback_id)
        send_antigravity_running_windows_menu(chat_id, message_id=message_id)


def handle_text_message(message: dict):
    """Processes user text messages in Telegram (such as passwords, start commands, or revision feedback)."""
    chat_id = str(message.get("chat", {}).get("id"))
    text = message.get("text", "").strip()
    msg_id = message.get("message_id")

    logger.info(f"Received text message: '{text}' from chat {chat_id}")

    clean_text = text.lower().strip()
    if clean_text in ["/start", "start", "/help", "help", "hi", "hello", "menu", "/menu"]:
        send_root_choice_menu(chat_id)
        return

    if clean_text in ["/cancel", "cancel"]:
        if chat_id in chat_sessions:
            del chat_sessions[chat_id]
        send_root_choice_menu(chat_id)
        return

    session = chat_sessions.get(chat_id)
    if not session:
        if text.startswith("/"):
            send_root_choice_menu(chat_id)
        return

    # User sent prompt for Antigravity / Laptop Remote Control
    if session.get("action") == "AWAITING_ANTIGRAVITY_PROMPT":
        target_mode = session.get("mode", "antigravity_chat")

        # Allocate sequential Task Number (#TASK-101)
        task = allocate_new_task(prompt=text, target_mode=target_mode)
        task_id = task["task_id"]

        mode_label = {
            "antigravity_chat": "Antigravity IDE (Chat Prompt)",
            "antigravity_inline": "Antigravity IDE (Inline Ctrl+I)",
            "active_window": "Active Laptop Window",
            "notepad": "Notepad (Testing)",
        }.get(target_mode, target_mode)

        prompt_preview = (text[:120] + "...") if len(text) > 120 else text

        ack_text = (
            f"🚀 <b>Task #{task_id} Started!</b>\n\n"
            f"🖥️ <b>Target:</b> <code>{mode_label}</code>\n"
            f"📝 <b>Prompt:</b>\n<i>\"{prompt_preview}\"</i>\n\n"
            f"⏳ <b>Status:</b> Pasting into running software on laptop and submitting..."
        )
        send_text_message(chat_id, ack_text)

        import threading
        def _exec_injection():
            try:
                res = inject_prompt_to_antigravity(prompt=text, target_mode=target_mode)
                if res.get("success"):
                    win_title = res.get("window_title", "Antigravity IDE")
                    update_task_status(task_id, "completed", res.get("message"))
                    send_task_completion_message(chat_id, task_id, text, win_title, success=True)
                else:
                    update_task_status(task_id, "failed", res.get("message"))
                    send_task_completion_message(chat_id, task_id, text, "Antigravity IDE", success=False, details=res.get("message"))
            except Exception as e_inj:
                logger.error(f"Error during remote prompt injection: {e_inj}")
                update_task_status(task_id, "error", str(e_inj))
                send_task_completion_message(chat_id, task_id, text, "Antigravity IDE", success=False, details=str(e_inj))

        threading.Thread(target=_exec_injection, daemon=True).start()
        return

    # User provided custom location for outreach
    if session.get("action") == "AWAITING_OUTREACH_LOCATION":
        platform = session.get("platform", "both")
        location = text.strip()
        del chat_sessions[chat_id]
        send_outreach_count_menu(chat_id, platform=platform, location=location)
        return

    # User provided custom request count for outreach
    if session.get("action") == "AWAITING_OUTREACH_COUNT":
        platform = session.get("platform", "both")
        location = session.get("location", "Global")
        target_msg_id = session.get("message_id")

        try:
            val = int(text.strip())
            if val <= 0:
                raise ValueError("Count must be positive")
        except ValueError:
            send_text_message(
                chat_id,
                "⚠️ <b>Invalid number.</b> Please type a positive number (e.g. <code>15</code>, <code>35</code>, <code>80</code>) or type /cancel to abort."
            )
            return

        del chat_sessions[chat_id]
        target_count = min(val, 250)
        if val > 250:
            send_text_message(
                chat_id,
                f"ℹ️ <i>Notice: Request count capped at platform safety maximum of 250 (entered: {val}) to protect your account.</i>"
            )

        launch_outreach_campaign(chat_id, platform=platform, location=location, target_count=target_count, message_id=target_msg_id)
        return

    # User provided password for a platform
    if session.get("action") == "AWAITING_PASSWORD":
        platform = session.get("platform", "facebook")
        campaign_id = session.get("campaign_id", "")
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

        # Check for remaining platforms in multi-platform queue
        remaining = session.get("remaining_platforms", [])

        # Clear session
        del chat_sessions[chat_id]

        # Proceed to post
        time.sleep(3)
        send_text_message(chat_id, f"📝 Publishing post with media to {platform.capitalize()}...")
        post_res = post_to_facebook(media_path=media_path, caption=caption)

        if post_res.get("status") == "success":
            update_campaign_status_db(campaign_id, "posted", platform=platform, media_path=media_path, caption=caption)
            send_text_message(
                chat_id,
                f"🎉 <b>Success!</b> Authenticated & post published to {platform.capitalize()}!\n\n"
                f"🖼️ Media: <code>{os.path.basename(media_path) if media_path else 'Graphic'}</code>\n"
                f"📝 Caption preview: {caption[:120]}..."
            )
            if remaining:
                send_text_message(chat_id, f"🔄 Continuing multi-platform broadcast with: {', '.join([r.capitalize() for r in remaining])}...")
                launch_multi_platform_publication(chat_id, campaign_id, remaining)
        else:
            send_text_message(chat_id, f"⚠️ Post result: {post_res.get('message')}")
            if remaining:
                launch_multi_platform_publication(chat_id, campaign_id, remaining)

    # User provided revision instructions
    elif session.get("action") == "AWAITING_REVISION":
        campaign_id = session.get("campaign_id", "")
        del chat_sessions[chat_id]
        send_text_message(
            chat_id,
            f"🔄 <b>Revision note recorded:</b> <i>\"{text}\"</i>\n\n"
            f"🤖 <b>Regenerating Content:</b> Opening Chrome and prompting ChatGPT with your feedback...\n"
            f"🎨 Crafting new custom graphic & viral copy...\n"
            f"⏳ <i>Please wait ~35-50 seconds. A new preview with approval buttons will be sent here!</i>"
        )

        import threading
        def _run_revision():
            try:
                from browser.human_operator import execute_human_generation_and_telegram_flow
                execute_human_generation_and_telegram_flow(
                    platform="chatgpt",
                    custom_instructions=f"User revision request: {text}",
                    campaign_id=campaign_id,
                    platforms=["facebook", "instagram"]
                )
            except Exception as e_rev:
                logger.error(f"Error during Telegram revision generation: {e_rev}")
                send_text_message(chat_id, f"⚠️ Revision generation notice: {e_rev}")

        threading.Thread(target=_run_revision, daemon=True).start()


def handle_incoming_message(message: dict):
    """Processes incoming Telegram messages, including uploaded photos and documents."""
    chat_id = str(message.get("chat", {}).get("id"))
    bot_token, _ = get_telegram_credentials()

    # Check if user sent a photo or document file
    photo_list = message.get("photo")
    doc = message.get("document")

    if (photo_list or doc) and bot_token:
        file_id = None
        orig_name = "Loan Solutions.png"
        if photo_list:
            file_id = photo_list[-1].get("file_id")
        elif doc:
            file_id = doc.get("file_id")
            orig_name = doc.get("file_name", "Loan Solutions.png")

        if file_id:
            from telegram.bot import download_telegram_file
            target_path = LOAN_SOLUTIONS_PATH
            logger.info(f"Downloading uploaded Telegram media ({file_id}) for Loan Solutions...")
            download_success = download_telegram_file(bot_token, file_id, target_path)

            if download_success:
                # Mirror to public/uploads and data/media/images
                try:
                    import shutil
                    pub_target = BASE_DIR / "public" / "uploads" / "Loan_Solutions.png"
                    media_target = BASE_DIR / "data" / "media" / "images" / "Loan_Solutions.png"
                    pub_target.parent.mkdir(parents=True, exist_ok=True)
                    media_target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(target_path, pub_target)
                    shutil.copyfile(target_path, media_target)
                except Exception as e_cp:
                    logger.warning(f"Mirror file copy notice: {e_cp}")

                # Permanently update product logo in DB
                update_loan_solution_logo_db(target_path)

                prods = get_all_products()
                loan_id = "default"
                for p in prods:
                    if "loan" in (p.get("name") or "").lower():
                        loan_id = str(p.get("id"))
                        break

                quick_keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": "♊ Generate with Gemini", "callback_data": f"flow:run:image:gemini:{loan_id}"},
                            {"text": "🤖 Generate with ChatGPT", "callback_data": f"flow:run:image:chatgpt:{loan_id}"}
                        ],
                        [
                            {"text": "🎥 Generate Video Reel (Gemini)", "callback_data": f"flow:run:video:gemini:{loan_id}"}
                        ],
                        [
                            {"text": "🔙 Main Menu", "callback_data": "flow:start"}
                        ]
                    ]
                }

                send_text_message(
                    chat_id,
                    "📸 <b>File Upload Received from Telegram!</b>\n\n"
                    "✅ <b>Automatically considered & saved for:</b> <i>Loan Solutions</i>\n"
                    f"📁 <b>File Path:</b> <code>Loan Solutions.png</code>\n\n"
                    "This image is now automatically uploaded and used as the reference branding visual when generating Loan Solutions campaigns in Gemini and ChatGPT.\n\n"
                    "👇 <b>Choose an AI to generate right now:</b>",
                    reply_markup=quick_keyboard
                )
                return

    # Fall back to text message handler
    handle_text_message(message)


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
    print("Supports: Telegram Photo/Document Upload -> Auto-Assigned to Loan Solutions", flush=True)
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
                        handle_incoming_message(update["message"])

            time.sleep(1)

        except KeyboardInterrupt:
            print("\nPoller stopped.", flush=True)
            break
        except Exception as e:
            logger.error(f"Error in polling loop: {e}")
            time.sleep(3)


if __name__ == "__main__":
    start_polling()
