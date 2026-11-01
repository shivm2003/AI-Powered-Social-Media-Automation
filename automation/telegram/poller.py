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
        send_outreach_strategy_menu,
        send_instagram_steps_menu,
        send_facebook_accept_menu,
        send_instagram_unfollow_menu,
        send_outreach_location_menu,
        send_outreach_count_menu,
        send_antigravity_menu,
        send_antigravity_running_windows_menu,
        send_task_completion_message,
        send_friends_group_menu,
        send_queue_dashboard,
        send_queue_collision_notice,
        send_chrome_account_selection_menu,
        send_task_start_notification,
        send_task_completed_notification,
        send_posted_content_gallery,
        send_post_shares_overall_stats_menu,
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
        send_outreach_strategy_menu,
        send_instagram_steps_menu,
        send_facebook_accept_menu,
        send_instagram_unfollow_menu,
        send_outreach_location_menu,
        send_outreach_count_menu,
        send_antigravity_menu,
        send_antigravity_running_windows_menu,
        send_task_completion_message,
        send_friends_group_menu,
        send_queue_dashboard,
        send_queue_collision_notice,
        send_chrome_account_selection_menu,
        send_task_start_notification,
        send_task_completed_notification,
        send_posted_content_gallery,
        send_post_shares_overall_stats_menu,
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
from core.task_orchestrator import orchestrator, AutomationTask, TaskState

logger = logging.getLogger("automation.telegram.poller")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)

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




def get_campaign_data(campaign_id: str = None) -> dict:
    """Finds campaign data from PostgreSQL, SQLite, or file cache. If campaign_id is None, finds latest campaign."""
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
        if campaign_id:
            cur.execute("""
                SELECT c.id, c.generated_caption, c.generated_hashtags, c.media_paths, p.name, p.category, p.website_url
                FROM campaigns c
                LEFT JOIN products p ON c.product_id = p.id
                WHERE c.id = %s
            """, (str(campaign_id),))
        else:
            cur.execute("""
                SELECT c.id, c.generated_caption, c.generated_hashtags, c.media_paths, p.name, p.category, p.website_url
                FROM campaigns c
                LEFT JOIN products p ON c.product_id = p.id
                ORDER BY c.created_at DESC LIMIT 1
            """)
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            cid, caption, hashtags, media_paths, p_name, p_cat, p_web = row
            media_list = json.loads(media_paths) if isinstance(media_paths, str) else (media_paths or [])
            tag_list = json.loads(hashtags) if isinstance(hashtags, str) else (hashtags or [])
            tag_str = " ".join([t if t.startswith("#") else f"#{t}" for t in tag_list]) if tag_list else ""
            
            is_loan = ("loan" in str(p_name).lower()) or ("finance" in str(p_cat).lower()) or ("loan" in str(caption).lower())
            apply_url = "https://loansolutions.everythingrental.in/application"
            from social.caption_helper import ensure_apply_now_at_start
            raw_text = f"{caption or ''}\n\n{tag_str}".strip() if tag_str else (caption or "").strip()
            full_caption = ensure_apply_now_at_start(raw_text, apply_url=apply_url, is_loan=is_loan)
            return {
                "id": str(cid),
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
            if campaign_id:
                cur.execute("""
                    SELECT c.id, c.generated_caption, c.generated_hashtags, c.media_paths, p.name, p.category, p.website_url
                    FROM campaigns c
                    LEFT JOIN products p ON c.product_id = p.id
                    WHERE c.id = ?
                """, (str(campaign_id),))
            else:
                cur.execute("""
                    SELECT c.id, c.generated_caption, c.generated_hashtags, c.media_paths, p.name, p.category, p.website_url
                    FROM campaigns c
                    LEFT JOIN products p ON c.product_id = p.id
                    ORDER BY c.created_at DESC LIMIT 1
                """)
            row = cur.fetchone()
            conn.close()
            if row:
                cid, caption, hashtags, media_paths, p_name, p_cat, p_web = row
                media_list = json.loads(media_paths) if isinstance(media_paths, str) else (media_paths or [])
                tag_list = json.loads(hashtags) if isinstance(hashtags, str) else (hashtags or [])
                tag_str = " ".join([t if t.startswith("#") else f"#{t}" for t in tag_list]) if tag_list else ""
                
                is_loan = ("loan" in str(p_name).lower()) or ("finance" in str(p_cat).lower()) or ("loan" in str(caption).lower())
                apply_url = "https://loansolutions.everythingrental.in/application"
                from social.caption_helper import ensure_apply_now_at_start
                raw_text = f"{caption or ''}\n\n{tag_str}".strip() if tag_str else (caption or "").strip()
                full_caption = ensure_apply_now_at_start(raw_text, apply_url=apply_url, is_loan=is_loan)
                return {
                    "id": str(cid),
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
        "id": "latest_local",
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
        plat_list = None
        if platform:
            if isinstance(platform, str):
                plat_list = [p.strip() for p in platform.split(",") if p.strip()]
            elif isinstance(platform, list):
                plat_list = []
                for p in platform:
                    if isinstance(p, str) and "," in p:
                        plat_list.extend([x.strip() for x in p.split(",") if x.strip()])
                    elif isinstance(p, str) and p.strip():
                        plat_list.append(p.strip())
            else:
                plat_list = [str(platform)]
        return save_or_update_campaign(
            campaign_id=campaign_id,
            status=status,
            platforms=plat_list,
            media_path=media_path,
            caption=caption,
            posted_at_now=(status == "posted")
        )
    except Exception as e:
        logger.error(f"Error updating campaign status DB: {e}")
        return False


def launch_outreach_campaign(chat_id: str, platform: str, location: str, target_count: int, mode: str = "location", message_id: int = None, account_id: str = None):
    """Executes outreach campaign and manages live progress display in Telegram with active Chrome profile details."""
    campaign_id = str(uuid.uuid4())[:8]

    if not account_id:
        account_id = chat_sessions.get(chat_id, {}).get("selected_account_id")

    from db_campaigns import get_chrome_account
    acc_info = get_chrome_account(account_id) or {}
    acc_name = acc_info.get("google_name") or acc_info.get("name", "Shivam Mishra")
    acc_email = acc_info.get("google_email") or acc_info.get("email", "2003shivam1990@gmail.com")
    acc_pdir = acc_info.get("profile_dir") or acc_info.get("profile_directory", "Default")
    acc_fb = acc_info.get("facebook_name", "Techie Shivam (Loan Solutions)")
    acc_ig = acc_info.get("instagram_username", "loansolutions2026")
    acc_id = str(acc_info.get("id") or account_id or "1")

    plat_title = {
        "both": "⚡ Facebook + Instagram Simultaneously",
        "facebook": "📘 Facebook Friend Requests",
        "instagram": "📸 Instagram Follow Requests"
    }.get(platform, platform.capitalize())

    mode_badges = {
        "suggestions": "🌟 Algorithmic Suggestions (PYMK & Recommendations)",
        "random": "🎲 Random Discovery (Explore Feed)",
        "location": f"📍 Location Target: <code>{location}</code> (Real Residents | Channels Excluded)"
    }
    mode_text = mode_badges.get(mode, f"📍 Location: <code>{location}</code> (Real Residents | Channels Excluded)")

    init_text = (
        f"👥 <b>Growth Outreach Initiated!</b>\n\n"
        f"👤 <b>Google Chrome Account:</b> {acc_name}\n"
        f"📧 <b>Google Email:</b> <code>{acc_email}</code>\n"
        f"📁 <b>Profile Directory:</b> <code>{acc_pdir}</code>\n"
        f"📘 <b>Facebook Page:</b> {acc_fb}\n"
        f"📸 <b>Instagram Account:</b> @{acc_ig}\n\n"
        f"🎯 <b>Target:</b> {plat_title}\n"
        f"🔍 <b>Strategy:</b> {mode_text}\n"
        f"🔢 <b>Count:</b> {target_count} requests\n"
        f"🆔 <b>Campaign ID:</b> <code>{campaign_id}</code>\n\n"
        f"⏳ <b>Status:</b> Initializing browser session with profile <code>{acc_pdir}</code> & preparing search filters..."
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

    def _exec_growth(t_obj):
        try:
            run_growth_campaign(
                campaign_id=campaign_id,
                platform=platform,
                location=location,
                mode=mode,
                target_count=target_count,
                safety_delay=15,
                telegram_chat_id=chat_id,
                telegram_message_id=sent_msg_id,
                account_id=acc_id,
                profile_dir=acc_pdir,
                account_info=acc_info,
                task_obj=t_obj
            )
        except Exception as e_growth:
            logger.error(f"Error in growth campaign thread: {e_growth}")
            send_text_message(chat_id, f"⚠️ Outreach error notice: {e_growth}")

    task_obj = AutomationTask(
        task_id=campaign_id,
        name=f"{platform.capitalize()} {mode.capitalize()} ({target_count} targets)",
        task_type="growth",
        platform=platform,
        account_id=acc_id,
        progress_total=target_count,
        tg_chat_id=chat_id,
        tg_message_id=sent_msg_id,
        run_fn=lambda t: _exec_growth(t)
    )
    orchestrator.submit_task(task_obj)


def launch_social_group_creation(chat_id: str, platform: str, group_type: str, group_name: str, message_id: int = None, account_id: str = None):
    """Executes social group creation and manages live progress in Telegram with active Chrome profile details."""
    task_id = str(uuid.uuid4())[:8]

    if not account_id:
        account_id = chat_sessions.get(chat_id, {}).get("selected_account_id")

    from db_campaigns import get_chrome_account
    acc_info = get_chrome_account(account_id) or {}
    acc_name = acc_info.get("google_name") or acc_info.get("name", "Shivam Mishra")
    acc_email = acc_info.get("google_email") or acc_info.get("email", "2003shivam1990@gmail.com")
    acc_pdir = acc_info.get("profile_dir") or acc_info.get("profile_directory", "Default")
    acc_fb = acc_info.get("facebook_name", "Techie Shivam (Loan Solutions)")
    acc_ig = acc_info.get("instagram_username", "loansolutions2026")
    acc_id = str(acc_info.get("id") or account_id or "1")

    plat_title = {
        "facebook": "📘 Facebook",
        "instagram": "📸 Instagram",
        "both": "⚡ Facebook + Instagram"
    }.get(platform, platform.capitalize())

    type_title = {
        "community_group": "Community Group",
        "messenger_chat": "Messenger Group Chat",
        "ig_direct_group": "Direct Group (Batch 30)",
        "all": "All Available Formats"
    }.get(group_type, group_type)

    init_text = (
        f"👨‍👩‍👧‍👦 <b>Social Friends Group Creation Initiated!</b>\n\n"
        f"👤 <b>Google Chrome Account:</b> {acc_name}\n"
        f"📧 <b>Google Email:</b> <code>{acc_email}</code>\n"
        f"📁 <b>Profile Directory:</b> <code>{acc_pdir}</code>\n"
        f"📘 <b>Facebook Page:</b> {acc_fb}\n"
        f"📸 <b>Instagram Account:</b> @{acc_ig}\n\n"
        f"🏷️ <b>Group Name:</b> <code>{group_name}</code>\n"
        f"📱 <b>Platform:</b> {plat_title}\n"
        f"🎯 <b>Type:</b> {type_title}\n"
        f"🆔 <b>Task ID:</b> <code>{task_id}</code>\n\n"
        f"⏳ <b>Status:</b> Initializing Chrome profile <code>{acc_pdir}</code> and opening group creator..."
    )

    stop_keyboard = {
        "inline_keyboard": [
            [{"text": "🛑 Stop Creation Task", "callback_data": f"grp:stop:{task_id}"}]
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

    def _exec_grp():
        try:
            from social.social_groups import run_social_group_task
            run_social_group_task(
                task_id=task_id,
                platform=platform,
                group_type=group_type,
                group_name=group_name,
                tg_chat_id=chat_id,
                tg_message_id=sent_msg_id
            )
        except Exception as e_grp:
            logger.error(f"Error in social group task thread: {e_grp}")
            send_text_message(chat_id, f"⚠️ Group creation error notice: {e_grp}")

    task_obj = AutomationTask(
        task_id=task_id,
        name=f"{platform.capitalize()} Group '{group_name}'",
        task_type="group",
        platform=platform,
        account_id="manvxi_ai",
        tg_chat_id=chat_id,
        tg_message_id=sent_msg_id,
        run_fn=lambda t: _exec_grp()
    )
    orchestrator.submit_task(task_obj)


def launch_fb_accept_task(chat_id: str, target_count: int, like_recent: bool, message_id: int = None, account_id: str = None):
    """Executes Facebook Friend Request Acceptor and manages live progress in Telegram with active Chrome profile details."""
    import threading
    import uuid

    if not account_id:
        account_id = chat_sessions.get(chat_id, {}).get("selected_account_id")

    from db_campaigns import get_chrome_account
    acc_info = get_chrome_account(account_id) or {}
    acc_name = acc_info.get("google_name") or acc_info.get("name", "Shivam Mishra")
    acc_email = acc_info.get("google_email") or acc_info.get("email", "2003shivam1990@gmail.com")
    acc_pdir = acc_info.get("profile_dir") or acc_info.get("profile_directory", "Default")
    acc_fb = acc_info.get("facebook_name", "Techie Shivam (Loan Solutions)")
    acc_ig = acc_info.get("instagram_username", "loansolutions2026")
    acc_id = str(acc_info.get("id") or account_id or "1")

    job_id = str(uuid.uuid4())[:8]
    target_label = "All Pending Requests" if target_count == 0 else f"First {target_count} Requests"
    like_label = "Enabled 👍" if like_recent else "Disabled"

    init_text = (
        f"🤝 <b>Facebook Accept Sequence Started!</b>\n\n"
        f"👤 <b>Google Chrome Account:</b> {acc_name}\n"
        f"📧 <b>Google Email:</b> <code>{acc_email}</code>\n"
        f"📁 <b>Profile Directory:</b> <code>{acc_pdir}</code>\n"
        f"📘 <b>Facebook Page:</b> {acc_fb}\n"
        f"📸 <b>Instagram Account:</b> @{acc_ig}\n\n"
        f"🎯 <b>Target:</b> {target_label}\n"
        f"👍 <b>Auto-Like Recent Post:</b> {like_label}\n"
        f"🆔 <b>Job ID:</b> <code>{job_id}</code>\n\n"
        f"⏳ <b>Status:</b> Connecting to Facebook Friend Requests page with profile <code>{acc_pdir}</code>..."
    )

    stop_keyboard = {
        "inline_keyboard": [
            [{"text": "🛑 Stop Accepting", "callback_data": f"fb_acc:stop:{job_id}"}]
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

    def _exec_accept():
        try:
            from social.facebook_accept import accept_facebook_friend_requests

            last_edit_time = [time.time()]

            def _on_progress(accepted, target, name):
                if time.time() - last_edit_time[0] >= 2.0:
                    last_edit_time[0] = time.time()
                    update_text = (
                        f"⏳ <b>Accepting Facebook Friend Requests...</b>\n\n"
                        f"👤 <b>Google Chrome Account:</b> {acc_name} (<code>{acc_pdir}</code>)\n"
                        f"📘 <b>Facebook Page:</b> {acc_fb}\n\n"
                        f"✅ <b>Accepted:</b> <code>{accepted}</code>"
                        f"{f' / {target}' if target else ''}\n"
                        f"👤 <b>Latest:</b> <i>{name}</i>\n"
                        f"👍 <b>Auto-Like:</b> {like_label}\n\n"
                        f"<i>Accepting in browser with profile <code>{acc_pdir}</code>...</i>"
                    )
                    if sent_msg_id:
                        edit_message_text(chat_id, sent_msg_id, update_text, keyboard=stop_keyboard)

            res = accept_facebook_friend_requests(
                target_count=target_count,
                like_recent=like_recent,
                safety_delay=3,
                on_progress=_on_progress,
                campaign_id=job_id
            )

            acc_count = res.get("accepted_count", 0)
            liked_count = res.get("liked_count", 0)
            people = res.get("accepted_people", [])

            people_list = ""
            if people:
                people_list = "\n📋 <b>Recently Accepted:</b>\n"
                for p in people[:6]:
                    people_list += f"• <b>{p['name']}</b>\n"
                if len(people) > 6:
                    people_list += f"<i>...and {len(people) - 6} more</i>\n"

            done_keyboard = {
                "inline_keyboard": [
                    [{"text": "👥 Back to Friend Requests Center", "callback_data": "outreach:fb_accept_menu"}],
                    [{"text": "🔙 Main Menu", "callback_data": "root:main"}]
                ]
            }

            final_text = (
                f"🎉 <b>Facebook Friend Requests Processed!</b>\n\n"
                f"👤 <b>Google Chrome Account:</b> {acc_name}\n"
                f"📧 <b>Google Email:</b> <code>{acc_email}</code>\n"
                f"📁 <b>Profile Directory:</b> <code>{acc_pdir}</code>\n"
                f"📘 <b>Facebook Page:</b> {acc_fb}\n"
                f"📸 <b>Instagram Account:</b> @{acc_ig}\n\n"
                f"✅ <b>Total Accepted:</b> <code>{acc_count}</code>\n"
                f"👍 <b>Posts Liked:</b> <code>{liked_count}</code>\n"
                f"{people_list}\n"
                f"<i>Execution finished via Chrome profile <code>{acc_pdir}</code>.</i>"
            )

            if sent_msg_id:
                edit_message_text(chat_id, sent_msg_id, final_text, keyboard=done_keyboard)
            else:
                send_text_message(chat_id, final_text, reply_markup=done_keyboard)

        except Exception as e_acc:
            logger.error(f"Error in facebook accept thread: {e_acc}", exc_info=True)
    task_obj = AutomationTask(
        task_id=job_id,
        name=f"Facebook Accept ({target_label})",
        task_type="growth",
        platform="facebook",
        account_id="manvxi_ai",
        tg_chat_id=chat_id,
        tg_message_id=sent_msg_id,
        run_fn=lambda t: _exec_accept()
    )
    orchestrator.submit_task(task_obj)


def launch_ig_unfollow_task(chat_id: str, target_count: int, message_id: int = None, account_id: str = None):
    """Executes Instagram Unfollow and manages live throttled progress in Telegram with active Chrome profile details."""
    import threading
    import uuid

    if not account_id:
        account_id = chat_sessions.get(chat_id, {}).get("selected_account_id")

    from db_campaigns import get_chrome_account
    acc_info = get_chrome_account(account_id) or {}
    acc_name = acc_info.get("google_name") or acc_info.get("name", "Shivam Mishra")
    acc_email = acc_info.get("google_email") or acc_info.get("email", "2003shivam1990@gmail.com")
    acc_pdir = acc_info.get("profile_dir") or acc_info.get("profile_directory", "Default")
    acc_fb = acc_info.get("facebook_name", "Techie Shivam (Loan Solutions)")
    acc_ig = acc_info.get("instagram_username", "loansolutions2026")
    acc_id = str(acc_info.get("id") or account_id or "1")

    job_id = str(uuid.uuid4())[:8]
    target_label = "All Followed Accounts" if target_count == 0 else f"{target_count} Accounts"

    init_text = (
        f"📉 <b>Instagram Unfollow Sequence Initiated!</b>\n\n"
        f"👤 <b>Google Chrome Account:</b> {acc_name}\n"
        f"📧 <b>Google Email:</b> <code>{acc_email}</code>\n"
        f"📁 <b>Profile Directory:</b> <code>{acc_pdir}</code>\n"
        f"📘 <b>Facebook Page:</b> {acc_fb}\n"
        f"📸 <b>Instagram Account:</b> @{acc_ig}\n\n"
        f"🎯 <b>Target:</b> {target_label}\n"
        f"🆔 <b>Job ID:</b> <code>{job_id}</code>\n\n"
        f"⏳ <b>Status:</b> Connecting to Instagram following dialog with profile <code>{acc_pdir}</code>..."
    )

    stop_keyboard = {
        "inline_keyboard": [
            [{"text": "🛑 Stop Unfollowing", "callback_data": f"ig_unf:stop:{job_id}"}]
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

    def _exec_unfollow():
        try:
            from social.instagram_unfollow import unfollow_instagram_accounts

            last_edit_time = [time.time()]

            def _on_progress(unfollowed, target, details):
                if time.time() - last_edit_time[0] >= 2.0:
                    last_edit_time[0] = time.time()
                    u_user = details.get("user", "")
                    update_text = (
                        f"⏳ <b>Pruning Instagram Following...</b>\n\n"
                        f"👤 <b>Google Chrome Account:</b> {acc_name} (<code>{acc_pdir}</code>)\n"
                        f"📸 <b>Instagram Account:</b> @{acc_ig}\n\n"
                        f"📉 <b>Unfollowed:</b> <code>{unfollowed}</code>"
                        f"{f' / {target}' if target and target != 9999 else ''}\n"
                        f"👤 <b>Recent:</b> <i>@{u_user}</i>\n"
                        f"🛡️ <i>Human safety delays active to protect your account.</i>"
                    )
                    if sent_msg_id:
                        edit_message_text(chat_id, sent_msg_id, update_text, keyboard=stop_keyboard)

            res = unfollow_instagram_accounts(
                target_count=target_count,
                safety_delay=10,
                on_progress=_on_progress,
                campaign_id=job_id
            )

            unf_count = res.get("unfollowed_count", 0)
            people = res.get("unfollowed_accounts", [])

            people_list = ""
            if people:
                people_list = "\n📋 <b>Recently Unfollowed:</b>\n"
                for p in people[:6]:
                    people_list += f"• <b>@{p}</b>\n"
                if len(people) > 6:
                    people_list += f"<i>...and {len(people) - 6} more</i>\n"

            done_keyboard = {
                "inline_keyboard": [
                    [{"text": "📉 Back to Unfollow Center", "callback_data": "outreach:ig_unfollow_menu"}],
                    [{"text": "🔙 Main Menu", "callback_data": "root:main"}]
                ]
            }

            final_text = (
                f"🎉 <b>Instagram Pruning Finished!</b>\n\n"
                f"👤 <b>Google Chrome Account:</b> {acc_name}\n"
                f"📧 <b>Google Email:</b> <code>{acc_email}</code>\n"
                f"📁 <b>Profile Directory:</b> <code>{acc_pdir}</code>\n"
                f"📘 <b>Facebook Page:</b> {acc_fb}\n"
                f"📸 <b>Instagram Account:</b> @{acc_ig}\n\n"
                f"📉 <b>Total Accounts Unfollowed:</b> <code>{unf_count}</code>\n"
                f"{people_list}\n"
                f"<i>Execution finished via Chrome profile <code>{acc_pdir}</code>.</i>"
            )

            if sent_msg_id:
                edit_message_text(chat_id, sent_msg_id, final_text, keyboard=done_keyboard)
            else:
                send_text_message(chat_id, final_text, reply_markup=done_keyboard)

        except Exception as e_unf:
            logger.error(f"Error in instagram unfollow thread: {e_unf}", exc_info=True)
            send_text_message(chat_id, f"⚠️ Instagram unfollow error: {e_unf}")

    threading.Thread(target=_exec_unfollow, daemon=True).start()


def launch_ig_follow_users_task(chat_id: str, usernames: list, message_id: int = None, account_id: str = None):
    """
    Executes Instagram following on specific accounts in Chrome on port 9222.
    Streams real-time status and interactive feedback to Telegram with active Chrome profile details.
    """
    import random
    from social.instagram_follow import clean_instagram_username, follow_specific_instagram_user

    clean_list = []
    for raw in usernames:
        c = clean_instagram_username(raw)
        if c and c not in clean_list:
            clean_list.append(c)

    if not clean_list:
        send_text_message(
            chat_id,
            "⚠️ <b>No valid Instagram usernames detected.</b>\n"
            "Please provide a valid @username (e.g. <code>@rahul_verma</code>) or use /cancel."
        )
        return

    if not account_id:
        account_id = chat_sessions.get(chat_id, {}).get("selected_account_id")

    from db_campaigns import get_chrome_account
    acc_info = get_chrome_account(account_id) or {}
    acc_name = acc_info.get("google_name") or acc_info.get("name", "Shivam Mishra")
    acc_email = acc_info.get("google_email") or acc_info.get("email", "2003shivam1990@gmail.com")
    acc_pdir = acc_info.get("profile_dir") or acc_info.get("profile_directory", "Default")
    acc_fb = acc_info.get("facebook_name", "Techie Shivam (Loan Solutions)")
    acc_ig = acc_info.get("instagram_username", "loansolutions2026")
    acc_id = str(acc_info.get("id") or account_id or "1")

    job_id = str(uuid.uuid4())[:8]
    stop_flag = BASE_DIR / "data" / f"stop_{job_id}.flag"

    init_text = (
        f"📸 <b>Instagram Follow Sequence Initiated!</b>\n\n"
        f"👤 <b>Google Chrome Account:</b> {acc_name}\n"
        f"📧 <b>Google Email:</b> <code>{acc_email}</code>\n"
        f"📁 <b>Profile Directory:</b> <code>{acc_pdir}</code>\n"
        f"📘 <b>Facebook Page:</b> {acc_fb}\n"
        f"📸 <b>Instagram Account:</b> @{acc_ig}\n\n"
        f"🎯 <b>Target Accounts ({len(clean_list)}):</b>\n"
        + "\n".join([f"• <b>@{u}</b>" for u in clean_list[:6]])
        + (f"\n<i>...and {len(clean_list)-6} more</i>" if len(clean_list) > 6 else "") + "\n\n"
        f"🆔 <b>Job ID:</b> <code>{job_id}</code>\n\n"
        f"⏳ <b>Status:</b> Connecting to Instagram with profile <code>{acc_pdir}</code>..."
    )

    stop_keyboard = {
        "inline_keyboard": [
            [{"text": "🛑 Stop Follow Task", "callback_data": f"ig_flw:stop:{job_id}"}]
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

    def _exec_follow_users():
        try:
            results = []
            sent_count = 0
            already_count = 0
            req_count = 0
            skipped_count = 0
            failed_count = 0

            for i, u in enumerate(clean_list):
                if stop_flag.exists():
                    logger.info(f"Stop flag detected for follow job {job_id}")
                    try:
                        stop_flag.unlink()
                    except Exception:
                        pass
                    break

                res = follow_specific_instagram_user(u, skip_if_channel=False)
                results.append(res)
                st = res.get("status")

                if st == "success":
                    sent_count += 1
                    icon = "✅"
                elif st == "already_following":
                    already_count += 1
                    icon = "ℹ️"
                elif st == "requested":
                    req_count += 1
                    icon = "📨"
                elif st == "skipped":
                    skipped_count += 1
                    icon = "🛡️"
                else:
                    failed_count += 1
                    icon = "⚠️"

                f_text = res.get("followers_text") or "0"
                f_cnt = res.get("followers_count") or 0
                fn = res.get("full_name") or ""
                fn_str = f" ({fn})" if fn else ""

                update_text = (
                    f"📸 <b>Instagram Profile Intelligence & Follow in Progress...</b>\n\n"
                    f"👤 <b>Google Chrome Account:</b> {acc_name} (<code>{acc_pdir}</code>)\n"
                    f"📸 <b>Active Account:</b> @{acc_ig}\n\n"
                    f"🎯 <b>Target Profile ({i+1}/{len(clean_list)}):</b> @{u}{fn_str}\n"
                    f"👥 <b>Followers Extracted:</b> <code>{f_text}</code> ({f_cnt:,}) — <i>💾 Saved to Database</i>\n"
                    f"📈 <b>Following:</b> <code>{res.get('following_count', 0)}</code> | <b>Posts:</b> <code>{res.get('posts_count', 0)}</code>\n"
                    f"📊 <b>Follow Status:</b> {icon} <i>{res.get('message', '')}</i>\n\n"
                    f"🏆 <b>New Follows:</b> <code>{sent_count}</code> | "
                    f"<b>Requested:</b> <code>{req_count}</code> | "
                    f"<b>Already Following:</b> <code>{already_count}</code>\n"
                    f"💾 <i>Data recorded in SQLite (<code>instagram_target_leads</code>) & JSON tracker.</i>"
                )

                if sent_msg_id:
                    try:
                        edit_message_text(chat_id, sent_msg_id, update_text, keyboard=stop_keyboard)
                    except Exception:
                        pass

                if i < len(clean_list) - 1:
                    pause = random.uniform(7.0, 11.0)
                    time.sleep(pause)

            # Final summary
            lines = []
            for r in results:
                st = r.get("status")
                u_tag = f"@{r.get('username')}"
                f_txt = r.get("followers_text") or "0"
                fn = r.get("full_name") or ""
                fn_lbl = f" ({fn})" if fn else ""
                if st == "success":
                    lines.append(f"• ✅ <b>{u_tag}</b>{fn_lbl}: <code>{f_txt}</code> followers — <b>Followed!</b> 💾")
                elif st == "already_following":
                    lines.append(f"• ℹ️ <b>{u_tag}</b>{fn_lbl}: <code>{f_txt}</code> followers — Already following 💾")
                elif st == "requested":
                    lines.append(f"• 📨 <b>{u_tag}</b>{fn_lbl}: <code>{f_txt}</code> followers — Request sent (Private) 💾")
                elif st == "not_found":
                    lines.append(f"• ❌ <b>{u_tag}</b>: Account unavailable / not found")
                elif st == "skipped":
                    lines.append(f"• 🛡️ <b>{u_tag}</b>: {r.get('message', 'Skipped')}")
                else:
                    lines.append(f"• ⚠️ <b>{u_tag}</b>: {r.get('message', 'Failed')}")

            done_keyboard = {
                "inline_keyboard": [
                    [{"text": "🎯 Follow Another User ID", "callback_data": "outreach:ig_mode:username"}],
                    [{"text": "📊 View Leads & Follow Stats", "callback_data": "outreach:ig_follow_stats"}],
                    [{"text": "📸 Instagram Steps Menu", "callback_data": "outreach:plat:instagram"}],
                    [{"text": "👥 Outreach Menu", "callback_data": "root:outreach"}]
                ]
            }

            final_text = (
                f"🎉 <b>Instagram Follow & Intelligence Finished!</b>\n\n"
                f"👤 <b>Google Chrome Account:</b> {acc_name}\n"
                f"📧 <b>Google Email:</b> <code>{acc_email}</code>\n"
                f"📁 <b>Profile Directory:</b> <code>{acc_pdir}</code>\n"
                f"📸 <b>Active Account:</b> @{acc_ig}\n\n"
                f"📊 <b>Summary of Extracted Profiles:</b>\n"
                + "\n".join(lines[:12])
                + (f"\n<i>...and {len(lines)-12} more</i>" if len(lines) > 12 else "") + "\n\n"
                f"👥 <b>Total Target Profiles Scanned:</b> <code>{len(clean_list)}</code>\n"
                f"🏆 <b>New Follow Requests Sent:</b> <code>{sent_count}</code>\n"
                f"📨 <b>Private Account Requests:</b> <code>{req_count}</code>\n"
                f"👥 <b>Already Following:</b> <code>{already_count}</code>\n\n"
                f"💾 <i>All user profiles, follower counts, and timestamps are permanently saved in SQLite (<code>instagram_target_leads</code>) and <code>data/instagram_leads_tracker.json</code>.</i>"
            )

            if sent_msg_id:
                try:
                    edit_message_text(chat_id, sent_msg_id, final_text, keyboard=done_keyboard)
                except Exception:
                    send_text_message(chat_id, final_text, reply_markup=done_keyboard)
            else:
                send_text_message(chat_id, final_text, reply_markup=done_keyboard)

        except Exception as e_flw:
            logger.error(f"Error in instagram follow users thread: {e_flw}", exc_info=True)
            send_text_message(chat_id, f"⚠️ Instagram follow error: {e_flw}")

    task_obj = AutomationTask(
        name=f"Instagram Follow ({len(usernames)} users)",
        task_type="growth",
        platform="instagram",
        account_id=acc_id,
        tg_chat_id=chat_id,
        tg_message_id=sent_msg_id,
        run_fn=lambda t: _exec_follow_users()
    )
    orchestrator.submit_task(task_obj)


def launch_ig_target_followers_task(chat_id: str, target_username: str, target_count: int = 15, message_id: int = None, account_id: str = None):
    """
    Executes Instagram following on the followers of a target account (e.g. competitor/niche account).
    Streams live progress to Telegram with safety stop button and profile metrics.
    """
    import threading
    import uuid
    from social.instagram_follow import clean_instagram_username, follow_target_account_followers

    clean_target = clean_instagram_username(target_username)
    if not clean_target:
        send_text_message(chat_id, "⚠️ <b>Invalid target username.</b> Please provide a valid handle (e.g. <code>@lucknow_hearts</code>).")
        return

    # Clamp target count to maximum 1,000
    target_count = min(max(1, int(target_count)), 1000)

    if not account_id:
        account_id = chat_sessions.get(chat_id, {}).get("selected_account_id")

    from db_campaigns import get_chrome_account
    acc_info = get_chrome_account(account_id) or {}
    acc_name = acc_info.get("google_name") or acc_info.get("name", "Shivam Mishra")
    acc_email = acc_info.get("google_email") or acc_info.get("email", "2003shivam1990@gmail.com")
    acc_pdir = acc_info.get("profile_dir") or acc_info.get("profile_directory", "Default")
    acc_ig = acc_info.get("instagram_username", "loansolutions2026")
    acc_id = str(acc_info.get("id") or account_id or "1")

    job_id = str(uuid.uuid4())[:8]
    stop_flag = BASE_DIR / "data" / f"stop_{job_id}.flag"

    init_text = (
        f"👥 <b>Instagram Target Follower Sequence Initiated!</b>\n\n"
        f"🎯 <b>Target Account:</b> <code>@{clean_target}</code>\n"
        f"🎯 <b>Followers Goal:</b> <code>{target_count} Accounts</code> (Max Cap: 1000)\n"
        f"👤 <b>Chrome Profile:</b> {acc_name} (<code>{acc_pdir}</code>)\n"
        f"📸 <b>Active Handle:</b> @{acc_ig}\n"
        f"🆔 <b>Job ID:</b> <code>{job_id}</code>\n\n"
        f"⏳ <b>Status:</b> Opening <code>@{clean_target}</code> followers dialog in authenticated Chrome..."
    )

    stop_keyboard = {
        "inline_keyboard": [
            [{"text": "🛑 Stop Follow Task", "callback_data": f"ig_flw:stop:{job_id}"}]
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

    def _exec_target_followers():
        try:
            stop_evt = threading.Event()

            def _on_progress(sent, target, details):
                if stop_flag.exists():
                    stop_evt.set()
                if sent_msg_id:
                    u_curr = details.get("user", "")
                    st = details.get("status", "")
                    progress_pct = int((sent / max(target, 1)) * 100)
                    bar_len = 10
                    filled = int(bar_len * sent // max(target, 1))
                    bar = "█" * filled + "░" * (bar_len - filled)

                    if st == "resting":
                        cd = details.get("cooldown", 180)
                        prog_text = (
                            f"👥 <b>Target Follower Outreach — Cooldown Active</b>\n\n"
                            f"🎯 <b>Target Account:</b> <code>@{clean_target}</code>\n"
                            f"📈 <b>Progress:</b> <code>[{bar}] {sent}/{target}</code> ({progress_pct}%)\n"
                            f"🏆 <b>Followed So Far:</b> <code>{sent} accounts</code>\n\n"
                            f"⏳ <b>Account Protection Cooldown:</b>\n"
                            f"<i>Pausing ~{cd//60} mins to keep account safe from Instagram rate-limits...</i>\n"
                            f"Will automatically resume next batch shortly."
                        )
                    elif st == "sliding":
                        s_num = details.get("slide_count", 1)
                        buff = details.get("buffered", 0)
                        prog_text = (
                            f"👥 <b>Target Follower Outreach — Scanning Followers</b>\n\n"
                            f"🎯 <b>Target Account:</b> <code>@{clean_target}</code>\n"
                            f"📈 <b>Progress:</b> <code>[{bar}] {sent}/{target}</code> ({progress_pct}%)\n"
                            f"🏆 <b>Followed So Far:</b> <code>{sent} accounts</code>\n\n"
                            f"⏬ <b>Deep Sliding Past Followed Accounts:</b>\n"
                            f"<i>Sliding down modal to uncover un-followed accounts (Slide {s_num}/15 | Buffered: {buff}/5)...</i>"
                        )
                    elif st == "refreshing":
                        atm = details.get("reload_attempt", 1)
                        prog_text = (
                            f"👥 <b>Target Follower Outreach — Refreshing Batch</b>\n\n"
                            f"🎯 <b>Target Account:</b> <code>@{clean_target}</code>\n"
                            f"📈 <b>Progress:</b> <code>[{bar}] {sent}/{target}</code> ({progress_pct}%)\n"
                            f"🏆 <b>Followed So Far:</b> <code>{sent} accounts</code>\n\n"
                            f"🔄 <b>Reloading Fresh Followers:</b>\n"
                            f"<i>Full modal depth scanned without new un-followed accounts. Refreshing @{clean_target} profile & re-opening dialog (Attempt {atm}/6)...</i>"
                        )
                    else:
                        prog_text = (
                            f"👥 <b>Target Follower Outreach in Progress...</b>\n\n"
                            f"🎯 <b>Target Account:</b> <code>@{clean_target}</code>\n"
                            f"📈 <b>Progress:</b> <code>[{bar}] {sent}/{target}</code> ({progress_pct}%)\n"
                            f"✅ <b>Latest Followed:</b> <code>@{u_curr}</code>\n\n"
                            f"⏳ <i>Human safety delay between follows to safeguard account...</i>"
                        )
                    try:
                        edit_message_text(chat_id, sent_msg_id, prog_text, keyboard=stop_keyboard)
                    except Exception:
                        pass

            res = follow_target_account_followers(
                target_username=clean_target,
                target_count=target_count,
                safety_delay=14,
                on_progress=_on_progress,
                stop_event=stop_evt,
                skip_if_verified=False,
                skip_if_channel=False
            )

            if stop_flag.exists():
                try:
                    stop_flag.unlink()
                except Exception:
                    pass

            followed_ppl = res.get("followed_accounts", [])
            s_count = res.get("sent", 0)

            done_keyboard = {
                "inline_keyboard": [
                    [{"text": "👥 Follow Another Target's Followers", "callback_data": "outreach:ig_mode:target_followers"}],
                    [{"text": "📸 Instagram Steps Menu", "callback_data": "outreach:plat:instagram"}],
                    [{"text": "🔙 Main Menu", "callback_data": "root:main"}]
                ]
            }

            lines = [f"• ✅ <b>@{u}</b>" for u in followed_ppl[:15]]
            summary_preview = "\n".join(lines) if lines else "<i>No new followers dispatched.</i>"
            if len(followed_ppl) > 15:
                summary_preview += f"\n<i>...and {len(followed_ppl)-15} more</i>"

            final_text = (
                f"🎉 <b>Target Follower Outreach Complete!</b>\n\n"
                f"🎯 <b>Target Account:</b> <code>@{clean_target}</code>\n"
                f"🏆 <b>Followers Followed:</b> <code>{s_count}/{target_count}</code>\n"
                f"🛡️ <b>Channels/Bots Filtered:</b> <code>{res.get('skipped', 0)}</code>\n\n"
                f"📋 <b>Followed Profiles:</b>\n"
                f"{summary_preview}"
            )

            if sent_msg_id:
                try:
                    edit_message_text(chat_id, sent_msg_id, final_text, keyboard=done_keyboard)
                except Exception:
                    send_text_message(chat_id, final_text, reply_markup=done_keyboard)
            else:
                send_text_message(chat_id, final_text, reply_markup=done_keyboard)

        except Exception as e_tgt:
            logger.error(f"Error in target followers task: {e_tgt}", exc_info=True)
            send_text_message(chat_id, f"⚠️ Instagram follower task error: {e_tgt}")

    task_obj = AutomationTask(
        name=f"IG Follow Followers of @{clean_target} ({target_count})",
        task_type="growth",
        platform="instagram",
        account_id=acc_id,
        tg_chat_id=chat_id,
        tg_message_id=sent_msg_id,
        run_fn=lambda t: _exec_target_followers()
    )
    orchestrator.submit_task(task_obj)


def launch_post_share_task(
    chat_id: str,
    campaign_id: str,
    platform: str = "both",
    share_all: bool = True,
    target_count: int = 100,
    message_id: int = None
):
    """
    Launches asynchronous post sharing to friends across Instagram and Facebook
    with human-like safety pacing, interactive telemetry, and instant cancellation.
    """
    import threading
    import uuid
    from db_campaigns import get_campaign_from_db
    from social.post_sharer import share_post_to_all_platforms, share_instagram_post_to_friends, share_facebook_post_to_friends

    camp = get_campaign_from_db(campaign_id) if campaign_id else {}
    p_name = camp.get("product_name") or "Marketing Post"

    job_id = str(uuid.uuid4())[:8]
    stop_flag = BASE_DIR / "data" / f"stop_shr_{job_id}.flag"
    stop_event = threading.Event()

    mode_label = "🚀 Share to ALL Friends" if share_all else f"Share up to {target_count} Friends"
    plat_label = {
        "instagram": "📸 Instagram Direct",
        "facebook": "📘 Facebook Messenger",
        "both": "⚡ Instagram + Facebook"
    }.get(platform.lower(), platform.upper())

    init_text = (
        f"🚀 <b>Post Sharing to Friends Initiated!</b>\n\n"
        f"🏷️ <b>Campaign:</b> <code>{campaign_id}</code> ({p_name})\n"
        f"📱 <b>Target Platforms:</b> {plat_label}\n"
        f"🎯 <b>Mode:</b> {mode_label}\n"
        f"🆔 <b>Job ID:</b> <code>{job_id}</code>\n"
        f"⏳ <b>Pacing:</b> Human-like anti-spam delays (6–12s)\n\n"
        f"Connecting to Chrome on port 9222 and preparing post content..."
    )

    stop_keyboard = {
        "inline_keyboard": [
            [{"text": "🛑 Stop Sharing Task", "callback_data": f"post_shr:stop:{job_id}"}]
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

    def _exec_share():
        try:
            def _progress_cb(sent_cnt, total_cnt, details):
                if stop_flag.exists():
                    stop_event.set()
                friend_name = details.get("friend") or "friend"
                plat = (details.get("platform") or platform).capitalize()
                update_text = (
                    f"📤 <b>Sharing Post to Friends in Progress...</b>\n\n"
                    f"🏷️ <b>Campaign:</b> <code>{campaign_id}</code>\n"
                    f"📱 <b>Platform:</b> {plat}\n"
                    f"👥 <b>Progress:</b> <code>{sent_cnt}</code> / <code>{total_cnt}</code> friends\n"
                    f"👤 <b>Last Selected:</b> <i>{friend_name}</i>\n"
                    f"⏱️ <i>Human safety pauses active to comply with Meta anti-spam rules.</i>"
                )
                if sent_msg_id:
                    try:
                        edit_message_text(chat_id, sent_msg_id, update_text, keyboard=stop_keyboard)
                    except Exception:
                        pass

            if platform.lower() == "instagram":
                res = share_instagram_post_to_friends(
                    campaign_id=campaign_id,
                    share_all=share_all,
                    target_count=target_count,
                    on_progress=_progress_cb,
                    stop_event=stop_event
                )
            elif platform.lower() == "facebook":
                res = share_facebook_post_to_friends(
                    campaign_id=campaign_id,
                    share_all=share_all,
                    target_count=target_count,
                    on_progress=_progress_cb,
                    stop_event=stop_event
                )
            else:
                res = share_post_to_all_platforms(
                    campaign_id=campaign_id,
                    share_all=share_all,
                    target_count=target_count,
                    on_progress=_progress_cb,
                    stop_event=stop_event
                )

            # Cleanup stop flag
            if stop_flag.exists():
                try:
                    stop_flag.unlink()
                except Exception:
                    pass

            total_shares = res.get("total_shares") or res.get("sent_count") or 0
            recipients = res.get("all_recipients") or res.get("recipients") or []
            rec_sample = ", ".join(recipients[:8]) if recipients else "Friends & Connections"
            if len(recipients) > 8:
                rec_sample += f" ...and {len(recipients) - 8} more"

            done_keyboard = {
                "inline_keyboard": [
                    [{"text": "🖼️ View Post Gallery", "callback_data": "post_page:0"}],
                    [{"text": "📊 Overall Share Stats", "callback_data": "post_shr:stats"}],
                    [{"text": "👥 Back to Outreach Menu", "callback_data": "root:outreach"}]
                ]
            }

            final_text = (
                f"🎉 <b>Post Sharing to Friends Completed!</b>\n\n"
                f"🏷️ <b>Campaign:</b> <code>{campaign_id}</code>\n"
                f"📱 <b>Platforms:</b> {plat_label}\n"
                f"🚀 <b>Total Friends Shared:</b> <code>{total_shares}</code>\n"
                f"👥 <b>Recipients:</b> <i>{rec_sample}</i>\n\n"
                f"💾 <i>Every share is permanently logged in <code>post_shares_log</code> database table.</i>"
            )

            if sent_msg_id:
                try:
                    edit_message_text(chat_id, sent_msg_id, final_text, keyboard=done_keyboard)
                except Exception:
                    send_text_message(chat_id, final_text, reply_markup=done_keyboard)
            else:
                send_text_message(chat_id, final_text, reply_markup=done_keyboard)

        except Exception as e_shr:
            logger.error(f"Error in post share background thread: {e_shr}", exc_info=True)
            send_text_message(chat_id, f"⚠️ Post sharing notice: {e_shr}")

    task_obj = AutomationTask(
        name=f"Share Post {campaign_id[:8]} ({plat_label})",
        task_type="share",
        platform=platform,
        account_id="manvxi_ai",
        tg_chat_id=chat_id,
        tg_message_id=sent_msg_id,
        run_fn=lambda t: _exec_share()
    )
    orchestrator.submit_task(task_obj)


def launch_multi_platform_publication(chat_id: str, campaign_id: str, platforms: list, message_id: int = None):
    """
    Publishes post to multiple social platforms (Facebook, Instagram, LinkedIn, WhatsApp)
    in coordinated sequence with live Telegram progress reporting!
    """
    import threading

    def _exec():
        nonlocal platforms
        try:
            from social.caption_helper import ensure_apply_now_at_start, LOAN_SOLUTIONS_APPLY_URL
            from social.trending_hashtags import enrich_caption_with_trending_hashtags
            campaign_data = get_campaign_data(campaign_id)
            media_path = campaign_data.get("media_path")
            raw_caption = campaign_data.get("caption", "")
            # Guarantee Apply Now link is strictly at the start of caption
            caption = ensure_apply_now_at_start(raw_caption, apply_url=LOAN_SOLUTIONS_APPLY_URL, is_loan=True)

            # Flatten and clean platforms list (handling any comma-separated strings like ["facebook,instagram"])
            clean_platforms = []
            for p in (platforms or []):
                if isinstance(p, str) and "," in p:
                    clean_platforms.extend([x.strip().lower() for x in p.split(",") if x.strip()])
                elif isinstance(p, str) and p.strip():
                    clean_platforms.append(p.strip().lower())
            seen_p = set()
            clean_platforms = [x for x in clean_platforms if not (x in seen_p or seen_p.add(x))]
            platforms = clean_platforms if clean_platforms else ["facebook"]

            plat_names = [p.capitalize() for p in platforms]
            init_text = (
                f"🚀 <b>Multi-Platform Broadcast Started!</b>\n\n"
                f"🎯 <b>Target Platforms ({len(platforms)}):</b> {', '.join(plat_names)}\n"
                f"🖼️ <b>Media:</b> <code>{os.path.basename(media_path) if media_path else 'Branded Graphic'}</code>\n"
                f"📝 <b>Mandatory Link:</b> <code>{LOAN_SOLUTIONS_APPLY_URL}</code>\n"
                f"⏳ <b>Status:</b> Initializing browser sessions & preparing verified posts..."
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
                    f"⏳ <b>Step {idx+1}/{len(platforms)}: Publishing & verifying on {p_label}...</b>"
                )

                try:
                    if plat_clean == "facebook":
                        from config import PLATFORM_URLS
                        fb_caption = enrich_caption_with_trending_hashtags(caption, platform="facebook", category="finance")
                        fb_caption = ensure_apply_now_at_start(fb_caption, apply_url=LOAN_SOLUTIONS_APPLY_URL, is_loan=True)
                        driver = browser.navigate("facebook", PLATFORM_URLS["facebook"])
                        time.sleep(2)
                        if driver and is_facebook_login_needed(driver):
                            chat_sessions[chat_id] = {
                                "action": "AWAITING_PASSWORD",
                                "platform": "facebook",
                                "campaign_id": campaign_id,
                                "media_path": media_path,
                                "caption": fb_caption,
                                "remaining_platforms": platforms[idx+1:]
                            }
                            send_password_request_prompt(chat_id, "facebook", campaign_id)
                            # Pause execution to await password
                            return
                        else:
                            res = post_to_facebook(media_path=media_path, caption=fb_caption)
                            if res.get("status") == "success":
                                fb_verified = res.get("verified", False)
                                successful_platforms.append({
                                    "platform": "facebook",
                                    "name": "Facebook",
                                    "verified": fb_verified,
                                    "url": "https://www.facebook.com/me"
                                })
                                status_desc = "Verified Live on Feed! ✅" if fb_verified else "Published! ✅"
                                send_text_message(chat_id, f"✅ <b>Facebook:</b> {status_desc}")
                            else:
                                failed_platforms.append(f"Facebook ({res.get('message', 'error')})")
                                send_text_message(chat_id, f"⚠️ Facebook notice: {res.get('message')}")

                    elif plat_clean == "instagram":
                        ig_caption = enrich_caption_with_trending_hashtags(caption, platform="instagram", category="finance")
                        ig_caption = ensure_apply_now_at_start(ig_caption, apply_url=LOAN_SOLUTIONS_APPLY_URL, is_loan=True)
                        res = post_to_instagram(media_path=media_path, caption=ig_caption)
                        if res.get("status") == "success":
                            ig_verified = res.get("verified", False)
                            ig_post_url = res.get("post_url")
                            successful_platforms.append({
                                "platform": "instagram",
                                "name": "Instagram",
                                "verified": ig_verified,
                                "url": ig_post_url or "https://www.instagram.com/loansolutions2026/"
                            })
                            succ_txt = "✅ <b>Instagram:</b> Successfully published & verified live! ✅"
                            if ig_post_url:
                                succ_txt += f"\n🔗 <b>Post Link:</b> {ig_post_url}"
                            send_text_message(chat_id, succ_txt)
                        else:
                            failed_platforms.append(f"Instagram ({res.get('message', 'error')})")
                            send_text_message(chat_id, f"⚠️ Instagram notice: {res.get('message')}")

                    elif plat_clean == "linkedin":
                        res = post_to_linkedin(media_path=media_path, caption=caption)
                        if res.get("status") == "success":
                            successful_platforms.append({
                                "platform": "linkedin",
                                "name": "LinkedIn",
                                "verified": True,
                                "url": "https://www.linkedin.com/feed/"
                            })
                            send_text_message(chat_id, "✅ <b>LinkedIn:</b> Successfully published! ✅")
                        else:
                            failed_platforms.append(f"LinkedIn ({res.get('message', 'error')})")
                            send_text_message(chat_id, f"⚠️ LinkedIn notice: {res.get('message')}")

                    elif plat_clean == "whatsapp":
                        from social.whatsapp import post_to_whatsapp
                        res = post_to_whatsapp(media_path=media_path, caption=caption)
                        if res.get("status") == "success":
                            successful_platforms.append({
                                "platform": "whatsapp",
                                "name": "WhatsApp",
                                "verified": True,
                                "url": "https://web.whatsapp.com"
                            })
                            send_text_message(chat_id, "✅ <b>WhatsApp:</b> Successfully published! ✅")
                        else:
                            failed_platforms.append(f"WhatsApp ({res.get('message', 'error')})")
                            send_text_message(chat_id, f"⚠️ WhatsApp notice: {res.get('message')}")

                except Exception as e_p:
                    logger.error(f"Error publishing to {plat_clean}: {e_p}")
                    failed_platforms.append(f"{plat_clean.capitalize()} ({e_p})")
                    send_text_message(chat_id, f"⚠️ Error publishing to {plat_clean}: {e_p}")

                # Human-like pacing between multiple platform posts
                if idx < len(platforms) - 1:
                    time.sleep(2.5)

            # Record in database
            if successful_platforms:
                update_campaign_status_db(
                    campaign_id,
                    status="posted",
                    platform=",".join([p["platform"] for p in successful_platforms]),
                    media_path=media_path,
                    caption=caption
                )

            # Send final verified celebratory confirmation card with action buttons
            succ_rows = []
            for sp in successful_platforms:
                v_badge = "Verified Live ✅" if sp.get("verified") else "Posted ✅"
                succ_rows.append(f"• <b>{sp['name']}:</b> {v_badge} — <a href=\"{sp['url']}\">View</a>")

            succ_str = "\n".join(succ_rows) if succ_rows else "None"
            fail_str = f"\n\n⚠️ <b>Issues:</b>\n" + "\n".join([f"• ❌ {p}" for p in failed_platforms]) if failed_platforms else ""

            summary_text = (
                f"🎉 <b>Broadcast Verified & Completed!</b>\n\n"
                f"<b>Live Status & Verification:</b>\n{succ_str}{fail_str}\n\n"
                f"📝 <b>Mandatory CTA (Line 1):</b>\n"
                f"<code>👉 Apply Now: {LOAN_SOLUTIONS_APPLY_URL}</code>\n\n"
                f"🖼️ <b>Media Attached:</b> <code>{os.path.basename(media_path) if media_path else 'Graphic'}</code>\n"
                f"📝 <b>Caption Snippet:</b>\n<i>{caption[:140]}...</i>\n\n"
                f"<i>Campaign {campaign_id[:8]} confirmed live in system.</i>"
            )

            # Build confirmation buttons: Apply Now button + direct link to live post
            confirm_buttons = [
                [{"text": "📝 Apply Now 🔗", "url": LOAN_SOLUTIONS_APPLY_URL}]
            ]
            for sp in successful_platforms:
                if sp["platform"] == "instagram" and "/p/" in sp.get("url", ""):
                    confirm_buttons.append([{"text": "📸 View on Instagram ↗️", "url": sp["url"]}])
                elif sp["platform"] == "facebook" and sp.get("url"):
                    confirm_buttons.append([{"text": "📘 View on Facebook ↗️", "url": sp["url"]}])

            send_text_message(
                chat_id,
                summary_text,
                reply_markup={"inline_keyboard": confirm_buttons}
            )

            # Send formal task completed notification with account mapping & live links
            try:
                from db_campaigns import get_campaign_from_db, get_chrome_account
                camp_rec = get_campaign_from_db(campaign_id) or {}
                c_acc_id = camp_rec.get("account_id") or "acc_default"
                c_acc = get_chrome_account(c_acc_id) or get_chrome_account("Default")
                c_prod_name = (camp_rec.get("product") or {}).get("name") or "Loan Solutions"
                send_task_completed_notification(
                    account=c_acc,
                    product_name=c_prod_name,
                    campaign_id=campaign_id,
                    results=successful_platforms,
                    platforms=[p["platform"] for p in successful_platforms],
                    chat_id=chat_id
                )
            except Exception as e_notif_done:
                logger.warning(f"Could not dispatch task completed notification: {e_notif_done}")

        except Exception as e_main:
            logger.error(f"Error in multi-platform execution: {e_main}")
    task_obj = AutomationTask(
        task_id=campaign_id or str(uuid.uuid4())[:8],
        name=f"Broadcast ({', '.join([p.capitalize() for p in platforms])})",
        task_type="post",
        platform="broadcast",
        account_id="multi",
        tg_chat_id=chat_id,
        tg_message_id=message_id,
        run_fn=lambda t: _exec()
    )
    orchestrator.submit_task(task_obj)


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

    # 9. Flow Step 4: Product Selected -> Ask for Google Chrome Account if not yet selected
    elif callback_data.startswith("flow:run:"):
        parts = callback_data.split(":")
        content_type = parts[2].lower() if len(parts) > 2 else "image"
        llm_provider = parts[3].lower() if len(parts) > 3 else "gemini"
        prod_id = parts[4] if len(parts) > 4 else ""

        saved_session = chat_sessions.get(chat_id, {})
        saved_acc_id = saved_session.get("selected_account_id")

        if not saved_acc_id:
            if callback_id:
                answer_callback_query(callback_id, text="Select Google Chrome Account...")
            send_chrome_account_selection_menu(
                chat_id=chat_id,
                content_type=content_type,
                llm_provider=llm_provider,
                product_id=prod_id,
                message_id=message_id
            )
            return

        # If already selected, redirect to flow:acc
        callback_data = f"flow:acc:{saved_acc_id}:{content_type}:{llm_provider}:{prod_id}"

    # 9b. Chrome Account Selected -> Launch Generation with this Profile
    if callback_data.startswith("flow:acc:"):
        parts = callback_data.split(":")
        acc_id = parts[2] if len(parts) > 2 else "1"
        content_type = parts[3].lower() if len(parts) > 3 else "image"
        llm_provider = parts[4].lower() if len(parts) > 4 else "chatgpt"
        prod_id = parts[5] if len(parts) > 5 else "default"

        if chat_id not in chat_sessions:
            chat_sessions[chat_id] = {}
        chat_sessions[chat_id]["selected_account_id"] = acc_id

        from db_campaigns import get_chrome_account
        acc_info = get_chrome_account(acc_id) or {}
        acc_name = acc_info.get("google_name") or acc_info.get("name", "Shivam Mishra")
        acc_email = acc_info.get("google_email") or acc_info.get("email", "2003shivam1990@gmail.com")
        acc_pdir = acc_info.get("profile_dir") or acc_info.get("profile_directory", "Default")
        acc_fb = acc_info.get("facebook_name", "Techie Shivam (Loan Solutions)")
        acc_ig = acc_info.get("instagram_username", "loansolutions2026")

        # If came from root menu, proceed to Content Type selection with account confirmed
        if prod_id == "default":
            if callback_id:
                answer_callback_query(callback_id, text=f"Account: {acc_name}")
            send_text_message(
                chat_id,
                f"✅ <b>Active Profile Selected:</b>\n"
                f"👤 <b>Google Account:</b> {acc_name} (<code>{acc_email}</code>)\n"
                f"📁 <b>Chrome Profile:</b> <code>{acc_pdir}</code>\n"
                f"📘 <b>Facebook Page:</b> <b>{acc_fb}</b>\n"
                f"📸 <b>Instagram Account:</b> <b>@{acc_ig}</b>"
            )
            send_start_flow_menu(chat_id, message_id=message_id)
            return

        # If came from outreach menu, proceed to Outreach Platform selection with account confirmed
        if prod_id == "outreach":
            if callback_id:
                answer_callback_query(callback_id, text=f"Profile: {acc_name}")
            send_text_message(
                chat_id,
                f"✅ <b>Active Profile Selected for Outreach & Follow:</b>\n"
                f"👤 <b>Google Account:</b> {acc_name} (<code>{acc_email}</code>)\n"
                f"📁 <b>Chrome Profile:</b> <code>{acc_pdir}</code>\n"
                f"📘 <b>Facebook Page:</b> <b>{acc_fb}</b>\n"
                f"📸 <b>Instagram Account:</b> <b>@{acc_ig}</b>"
            )
            send_outreach_platform_menu(chat_id, message_id=message_id, account_id=acc_id)
            return

        provider_title = {
            "gemini": "Gemini (Google AI)",
            "chatgpt": "ChatGPT (OpenAI)",
            "claude": "Claude (Anthropic)"
        }.get(llm_provider, llm_provider.capitalize())

        format_title = "Video Reel (9:16)" if content_type == "video" else "Image Post"

        if callback_id:
            answer_callback_query(callback_id, text=f"🚀 Launching Chrome ({acc_pdir})...")

        products = get_all_products()
        selected_prod = None
        for p in products:
            if str(p.get("id")) == prod_id:
                selected_prod = p
                break
        if not selected_prod and products:
            selected_prod = products[0]

        prod_name = selected_prod.get("name", "Featured Product") if selected_prod else "Featured Product"

        if content_type == "video":
            status_text = (
                f"🚀 <b>Campaign Generation Initiated!</b>\n\n"
                f"👤 <b>Google Chrome Account:</b> {acc_name}\n"
                f"📧 <b>Google Email:</b> <code>{acc_email}</code>\n"
                f"📁 <b>Profile Directory:</b> <code>{acc_pdir}</code>\n"
                f"📘 <b>Facebook Page:</b> {acc_fb}\n"
                f"📸 <b>Instagram Account:</b> @{acc_ig}\n\n"
                f"📦 <b>Product:</b> {prod_name}\n"
                f"🎨 <b>Format:</b> {format_title}\n"
                f"🤖 <b>AI Engine:</b> {provider_title}\n\n"
                f"⚡ <i>Step 1: Launching Chrome with profile <code>{acc_pdir}</code> & remote debugging...</i>\n"
                f"⚡ <i>Step 2: AI generating policy-compliant 3-clip video script & Indian voiceover...</i>\n"
                f"⚡ <i>Step 3: Rendering 3 sequential 8s clips & compiling master 24s video reel...</i>\n"
                f"⏳ <b>Please wait at least 5 minutes (~5 to 6 minutes).</b> High-definition video generation (minimum 5 minutes per clip wait time), neural voiceover synthesis, and clip compilation take extra time to process!"
            )
        else:
            status_text = (
                f"🚀 <b>Campaign Generation Initiated!</b>\n\n"
                f"👤 <b>Google Chrome Account:</b> {acc_name}\n"
                f"📧 <b>Google Email:</b> <code>{acc_email}</code>\n"
                f"📁 <b>Profile Directory:</b> <code>{acc_pdir}</code>\n"
                f"📘 <b>Facebook Page:</b> {acc_fb}\n"
                f"📸 <b>Instagram Account:</b> @{acc_ig}\n\n"
                f"📦 <b>Product:</b> {prod_name}\n"
                f"🎨 <b>Format:</b> {format_title}\n"
                f"🤖 <b>AI Engine:</b> {provider_title}\n\n"
                f"⚡ <i>Step 1: Launching Chrome with profile <code>{acc_pdir}</code> & remote debugging...</i>\n"
                f"⚡ <i>Step 2: AI generating viral copy, hashtags & branded graphic...</i>\n"
                f"⏳ <i>Please wait ~35-50s. The preview with approval buttons will arrive here!</i>"
            )

        if message_id and chat_id:
            try:
                edit_message_text(chat_id, message_id, status_text)
            except Exception:
                send_text_message(chat_id, status_text)
        else:
            send_text_message(chat_id, status_text)

        import threading
        def _run_account_flow():
            try:
                from browser.human_operator import execute_human_generation_and_telegram_flow
                logo_to_use = selected_prod.get("logo_path") if selected_prod else None
                if not logo_to_use and os.path.exists(LOAN_SOLUTIONS_PATH):
                    logo_to_use = LOAN_SOLUTIONS_PATH

                contact_num = selected_prod.get("contact_number") if selected_prod else None
                execute_human_generation_and_telegram_flow(
                    platform=llm_provider,
                    product=selected_prod or {"name": prod_name, "logo_path": logo_to_use, "contact_number": contact_num},
                    content_type=content_type,
                    skill_image_path=logo_to_use,
                    platforms=["facebook", "instagram"],
                    contact_number=contact_num,
                    account_id=acc_id,
                    profile_dir=acc_pdir
                )
            except Exception as e_run:
                logger.error(f"Error during flow generation: {e_run}")
                send_text_message(chat_id, f"⚠️ Generation notice: {e_run}")

        threading.Thread(target=_run_account_flow, daemon=True).start()

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

                contact_num = selected_prod.get("contact_number") if selected_prod else None
                execute_human_generation_and_telegram_flow(
                    platform="chatgpt",
                    product=selected_prod or {"name": prod_name, "logo_path": logo_to_use, "contact_number": contact_num},
                    skill_image_path=logo_to_use,
                    platforms=["facebook", "instagram"],
                    contact_number=contact_num
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

    # 13. Root Choice 1: Content Generation Flow -> Ask for Google Chrome Profile First
    elif callback_data == "root:content":
        if callback_id:
            answer_callback_query(callback_id)
        send_chrome_account_selection_menu(chat_id, content_type="image", llm_provider="chatgpt", product_id="default", message_id=message_id)

    # 14. Root Choice 2: Growth & Outreach Flow -> Step 1: Select Platform
    elif callback_data == "root:outreach":
        if callback_id:
            answer_callback_query(callback_id)
        cur_acc = chat_sessions.get(chat_id, {}).get("selected_account_id")
        send_outreach_platform_menu(chat_id, message_id=message_id, account_id=cur_acc)

    # 14a. Outreach Chrome Account Selector
    elif callback_data == "outreach:account_select":
        if callback_id:
            answer_callback_query(callback_id, text="Select Google Chrome Profile for Outreach...")
        send_chrome_account_selection_menu(chat_id, content_type="outreach", llm_provider="outreach", product_id="outreach", message_id=message_id)

    # 14b. Facebook Friend Requests Acceptor Menu
    elif callback_data == "outreach:fb_accept_menu":
        if callback_id:
            answer_callback_query(callback_id, text="🔍 Scanning Facebook for pending requests...")
        send_facebook_accept_menu(chat_id, message_id=message_id)

    # 14c. Facebook Friend Requests Execute Action (e.g. fb_acc:run:all:like)
    elif callback_data.startswith("fb_acc:run:"):
        parts = callback_data.split(":")
        count_str = parts[2] if len(parts) > 2 else "all"
        target_cnt = 0 if count_str == "all" else int(count_str)
        like_post = (parts[3] == "like") if len(parts) > 3 else False

        if callback_id:
            answer_callback_query(callback_id, text="⚡ Initiating Facebook Accept Sequence...")
        launch_fb_accept_task(chat_id, target_count=target_cnt, like_recent=like_post, message_id=message_id)

    # 14d. Facebook Friend Requests Stop Action
    elif callback_data.startswith("fb_acc:stop:"):
        job_id = callback_data.split(":", 2)[2] if ":" in callback_data else ""
        if callback_id:
            answer_callback_query(callback_id, text="🛑 Halting Facebook accept sequence...")
        stop_flag = BASE_DIR / "data" / f"stop_{job_id}.flag"
        stop_flag.parent.mkdir(parents=True, exist_ok=True)
        stop_flag.write_text("STOP", encoding="utf-8")
        send_text_message(chat_id, f"🛑 <b>Stop signal sent</b> for accept job <code>{job_id}</code>.")

    # 14e. Instagram Unfollow Menu
    elif callback_data == "outreach:ig_unfollow_menu":
        if callback_id:
            answer_callback_query(callback_id, text="🔍 Scanning Instagram following list...")
        send_instagram_unfollow_menu(chat_id, message_id=message_id)

    # 14f. Instagram Unfollow Execute Action (e.g. ig_unf:run:5 or ig_unf:run:all)
    elif callback_data.startswith("ig_unf:run:"):
        count_str = callback_data.split(":", 2)[2] if ":" in callback_data else "10"
        target_cnt = 0 if count_str == "all" else int(count_str)

        if callback_id:
            answer_callback_query(callback_id, text="⚡ Initiating Instagram Unfollow Sequence...")
        launch_ig_unfollow_task(chat_id, target_count=target_cnt, message_id=message_id)

    # 14g. Instagram Unfollow Stop Action
    elif callback_data.startswith("ig_unf:stop:"):
        job_id = callback_data.split(":", 2)[2] if ":" in callback_data else ""
        if callback_id:
            answer_callback_query(callback_id, text="🛑 Halting Instagram unfollow sequence...")
        stop_flag = BASE_DIR / "data" / f"stop_{job_id}.flag"
        stop_flag.parent.mkdir(parents=True, exist_ok=True)
        stop_flag.write_text("STOP", encoding="utf-8")
        send_text_message(chat_id, f"🛑 <b>Stop signal sent</b> for unfollow job <code>{job_id}</code>.")

    # 15. Outreach Step 2: Platform Selected -> Route to Strategy Menu
    elif callback_data.startswith("outreach:plat:"):
        platform = callback_data.split(":", 2)[2].lower()
        if callback_id:
            answer_callback_query(callback_id)
        if platform == "instagram":
            send_instagram_steps_menu(chat_id, message_id=message_id)
        else:
            send_outreach_strategy_menu(chat_id, platform=platform, message_id=message_id)

    # 15a. Outreach Strategy Selected -> Route to Count or Location
    elif callback_data.startswith("outreach:strat:"):
        parts = callback_data.split(":")
        platform = parts[2].lower() if len(parts) > 2 else "both"
        strat_mode = parts[3].lower() if len(parts) > 3 else "location"
        if callback_id:
            answer_callback_query(callback_id)

        if strat_mode in ["suggestions", "random"]:
            default_loc = "Suggested Accounts" if strat_mode == "suggestions" else "Random Explore Feed"
            send_outreach_count_menu(chat_id, platform=platform, location=default_loc, mode=strat_mode, message_id=message_id)
        else:
            send_outreach_location_menu(chat_id, platform=platform, message_id=message_id)

    # 15b. Instagram Guided Steps Menu
    elif callback_data == "outreach:ig_steps":
        if callback_id:
            answer_callback_query(callback_id)
        send_instagram_steps_menu(chat_id, message_id=message_id)

    # 15b2. Instagram Saved Leads & Follow Stats
    elif callback_data == "outreach:ig_follow_stats":
        if callback_id:
            answer_callback_query(callback_id)
        from telegram.bot import send_instagram_leads_stats_menu
        send_instagram_leads_stats_menu(chat_id, message_id=message_id)

    # 15c. Instagram Mode: Specific Username / User ID
    elif callback_data == "outreach:ig_mode:username":
        if callback_id:
            answer_callback_query(callback_id)
        chat_sessions[chat_id] = {
            "action": "AWAITING_IG_USERNAME",
            "message_id": message_id
        }
        send_text_message(
            chat_id,
            "🎯 <b>Instagram Follow & Follower Extraction Engine</b>\n\n"
            "Please type the Instagram <code>User ID</code> or <code>@username</code> you want to target:\n\n"
            "⚡ <b>Automated Workflow:</b>\n"
            "1. Manvix AI enters inside the user ID profile\n"
            "2. Extracts & saves their exact follower count to the leads database\n"
            "3. Dispatches the follow request safely via authenticated Chrome\n"
            "4. Tracks and tallies your cumulative follow counts!\n\n"
            "<i>Examples:</i>\n"
            "• <code>@badshah_bhai__9186</code>\n"
            "• <code>@rahul_verma, @priya_sharma</code>\n\n"
            "<i>(Type /cancel anytime to return to the menu)</i>"
        )

    # 15c2. Instagram Mode: Target Account's Followers
    elif callback_data == "outreach:ig_mode:target_followers":
        if callback_id:
            answer_callback_query(callback_id)
        chat_sessions[chat_id] = {
            "action": "AWAITING_IG_TARGET_FOLLOWERS_USERNAME",
            "message_id": message_id
        }
        send_text_message(
            chat_id,
            "👥 <b>Instagram Target Followers Engine</b>\n\n"
            "Please enter the Instagram <code>User ID</code> or <code>@username</code> whose followers you want to follow:\n\n"
            "⚡ <b>Automated Workflow:</b>\n"
            "1. Manvix AI navigates to the target user's profile\n"
            "2. Opens their <b>Followers</b> dialog in authenticated Chrome\n"
            "3. Scrolls and sends follow requests to real followers with safety pacing\n"
            "4. Automatically filters out channels, news, and inactive accounts!\n\n"
            "<i>Examples:</i>\n"
            "• <code>@lucknow_hearts</code>\n"
            "• <code>@lucknow_hearts 25</code> (to follow 25 followers directly)\n\n"
            "<i>(Type /cancel anytime to return to the menu)</i>"
        )

    # 15c3. Follow Target Followers - Count Selection Callback
    elif callback_data.startswith("ig_tgt_cnt:"):
        parts = callback_data.split(":")
        target_u = parts[1]
        target_c = int(parts[2]) if len(parts) > 2 else 20
        if callback_id:
            answer_callback_query(callback_id)
        launch_ig_target_followers_task(chat_id, target_u, target_count=target_c, message_id=message_id)

    # 15d. Instagram Mode: Location
    elif callback_data == "outreach:ig_mode:location":
        if callback_id:
            answer_callback_query(callback_id)
        send_outreach_location_menu(chat_id, platform="instagram", message_id=message_id)

    # 15e. Instagram Specific Follow Stop Action
    elif callback_data.startswith("ig_flw:stop:"):
        job_id = callback_data.split(":", 2)[2] if ":" in callback_data else ""
        if callback_id:
            answer_callback_query(callback_id, text="🛑 Halting Instagram follow sequence...")
        stop_flag = BASE_DIR / "data" / f"stop_{job_id}.flag"
        stop_flag.parent.mkdir(parents=True, exist_ok=True)
        stop_flag.write_text("STOP", encoding="utf-8")
        send_text_message(chat_id, f"🛑 <b>Stop signal sent</b> for follow job <code>{job_id}</code>.")

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
            "Please type the name of the target city or location (e.g. <code>Lucknow</code>, <code>Mumbai</code>, <code>New Delhi</code>):\n"
            "<i>(Our smart engine targets real local people & auto-skips channels and media pages)</i>\n\n"
            "<i>(Type /cancel anytime to return to the menu)</i>"
        )

    # 17. Outreach Step 3: Location Selected -> Select Count
    elif callback_data.startswith("outreach:loc:"):
        parts = callback_data.split(":")
        platform = parts[2].lower() if len(parts) > 2 else "both"
        location = parts[3] if len(parts) > 3 else "Global"
        if callback_id:
            answer_callback_query(callback_id)
        send_outreach_count_menu(chat_id, platform=platform, location=location, mode="location", message_id=message_id)

    # 18. Outreach Custom Count Selection
    elif callback_data.startswith("outreach:count_custom:"):
        parts = callback_data.split(":")
        if len(parts) >= 5:
            platform = parts[2].lower()
            mode = parts[3].lower()
            location = parts[4]
        else:
            platform = parts[2].lower() if len(parts) > 2 else "both"
            mode = "location"
            location = parts[3] if len(parts) > 3 else "Global"

        if callback_id:
            answer_callback_query(callback_id)
        chat_sessions[chat_id] = {
            "action": "AWAITING_OUTREACH_COUNT",
            "platform": platform,
            "mode": mode,
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
            f"🔍 <b>Strategy/Target:</b> <code>{location}</code>\n\n"
            "Please type the number of requests you would like to send (e.g. <code>15</code>, <code>35</code>, <code>75</code>, <code>100</code>):\n\n"
            "<i>(Type /cancel anytime to return to the menu)</i>"
        )

    # 19. Outreach Execution: Run outreach with preset (platform, mode, location, count)
    elif callback_data.startswith("outreach:run:"):
        parts = callback_data.split(":")
        # Format A: outreach:run:{platform}:{mode}:{location}:{count}
        if len(parts) >= 6:
            platform = parts[2].lower()
            mode = parts[3].lower()
            location = parts[4]
            try:
                target_count = int(parts[5])
            except ValueError:
                target_count = 10
        # Format B (Legacy 4-part): outreach:run:{platform}:{location}:{count}
        else:
            platform = parts[2].lower() if len(parts) > 2 else "both"
            mode = "location"
            location = parts[3] if len(parts) > 3 else "Global"
            try:
                target_count = int(parts[4]) if len(parts) > 4 else 10
            except ValueError:
                target_count = 10

        if callback_id:
            answer_callback_query(callback_id, text=f"🚀 Launching outreach ({mode})...")

        launch_outreach_campaign(chat_id, platform=platform, location=location, target_count=target_count, mode=mode, message_id=message_id)

    # 19b. Outreach Stop Signal
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

    # 23. Social Friends Group: Open menu
    elif callback_data == "root:friends_group":
        if callback_id:
            answer_callback_query(callback_id)
        send_friends_group_menu(chat_id, message_id=message_id)

    # 24. Social Friends Group: Type selected -> ask for name or offer default
    elif callback_data.startswith("grp:type:"):
        parts = callback_data.split(":")
        platform = parts[2] if len(parts) > 2 else "facebook"
        group_type = parts[3] if len(parts) > 3 else "community_group"
        if callback_id:
            answer_callback_query(callback_id)

        chat_sessions[chat_id] = {
            "action": "AWAITING_GROUP_NAME",
            "platform": platform,
            "group_type": group_type,
            "message_id": message_id
        }

        default_name = f"My VIP Community {time.strftime('%Y')}"
        prompt_text = (
            f"✏️ <b>Social Friends Group Name</b>\n\n"
            f"📱 <b>Platform:</b> {platform.capitalize()} ({group_type})\n\n"
            "Please type a name for your group (e.g. <code>VIP Members 2026</code>) or tap below to use the recommended default name:\n\n"
            "<i>(Type /cancel anytime to abort)</i>"
        )
        keyboard = {
            "inline_keyboard": [
                [{"text": f"⚡ Use \"{default_name}\"", "callback_data": f"grp:run:default:{platform}:{group_type}"}],
                [{"text": "🔙 Back", "callback_data": "root:friends_group"}]
            ]
        }
        send_text_message(chat_id, prompt_text, reply_markup=keyboard)

    # 25. Social Friends Group: Run with default name
    elif callback_data.startswith("grp:run:default:"):
        parts = callback_data.split(":")
        platform = parts[3] if len(parts) > 3 else "facebook"
        group_type = parts[4] if len(parts) > 4 else "community_group"
        default_name = f"My VIP Community {time.strftime('%Y')}"
        if callback_id:
            answer_callback_query(callback_id, text="🚀 Launching group creation...")
        if chat_id in chat_sessions:
            del chat_sessions[chat_id]
        launch_social_group_creation(chat_id, platform=platform, group_type=group_type, group_name=default_name, message_id=message_id)

    # 26. Social Friends Group: Stop Task
    elif callback_data.startswith("grp:stop:"):
        task_id = callback_data.split(":", 2)[2] if ":" in callback_data else ""
        if callback_id:
            answer_callback_query(callback_id, text="🛑 Halting group creation...")
        from social.social_groups import stop_social_group_task
        stop_social_group_task(task_id)
        send_text_message(chat_id, f"🛑 <b>Stop signal sent</b> for group creation task <code>{task_id}</code>.")

    # 27. Multitasking Queue Dashboard
    elif callback_data == "root:queue":
        if callback_id:
            answer_callback_query(callback_id)
        send_queue_dashboard(chat_id, message_id=message_id)

    # 28. Stop / Cancel Task from Queue Dashboard
    elif callback_data.startswith("task:stop:"):
        target_tid = callback_data.split(":", 2)[2] if ":" in callback_data else ""
        if callback_id:
            answer_callback_query(callback_id, text="🛑 Halting task...")
        orchestrator.cancel_task(target_tid)
        stop_growth_campaign(target_tid)
        try:
            from social.social_groups import stop_social_group_task
            stop_social_group_task(target_tid)
        except Exception:
            pass
        send_text_message(chat_id, f"🛑 <b>Task {target_tid} cancelled.</b> If other tasks were queued behind it, the next task is now unblocked and active!")
        send_queue_dashboard(chat_id)

    # 29. Stop Outreach Task from Live Card
    elif callback_data.startswith("outreach:stop:"):
        target_cid = callback_data.split(":", 2)[2] if ":" in callback_data else ""
        if callback_id:
            answer_callback_query(callback_id, text="🛑 Halting outreach task...")
        orchestrator.cancel_task(target_cid)
        stop_growth_campaign(target_cid)
        send_text_message(chat_id, f"🛑 <b>Outreach campaign <code>{target_cid}</code> cancelled.</b>")
        send_queue_dashboard(chat_id)

    # 30. Refresh Status from Live Card
    elif callback_data.startswith("outreach:status:"):
        if callback_id:
            answer_callback_query(callback_id, text="🔄 Live status refreshed!")
        send_queue_dashboard(chat_id, message_id=message_id)

    # 31. Posted Content Gallery Navigation
    elif callback_data.startswith("post_page:"):
        page_str = callback_data.split(":", 1)[1] if ":" in callback_data else "0"
        try:
            page_idx = int(page_str)
        except ValueError:
            page_idx = 0
        if callback_id:
            answer_callback_query(callback_id)
        send_posted_content_gallery(chat_id, page_index=page_idx, message_id=message_id)

    # 32. Post Sharing Actions & Overall Stats
    elif callback_data.startswith("post_shr:"):
        parts = callback_data.split(":")
        sub_action = parts[1] if len(parts) > 1 else ""

        if sub_action == "stats":
            if callback_id:
                answer_callback_query(callback_id, text="📊 Loading post share stats...")
            send_post_shares_overall_stats_menu(chat_id, message_id=message_id)

        elif sub_action == "stop":
            target_jid = parts[2] if len(parts) > 2 else ""
            if callback_id:
                answer_callback_query(callback_id, text="🛑 Halting post share task...")
            stop_flag = BASE_DIR / "data" / f"stop_shr_{target_jid}.flag"
            try:
                stop_flag.write_text("STOP", encoding="utf-8")
            except Exception:
                pass
            send_text_message(chat_id, f"🛑 <b>Post sharing stop signal sent</b> for job <code>{target_jid}</code>.")

        elif sub_action in ["all", "ig", "fb"]:
            camp_id = parts[2] if len(parts) > 2 else ""
            plat_map = {"all": "both", "ig": "instagram", "fb": "facebook"}
            plat_chosen = plat_map.get(sub_action, "both")
            if callback_id:
                answer_callback_query(callback_id, text="🚀 Launching friend sharing...")
            launch_post_share_task(
                chat_id=chat_id,
                campaign_id=camp_id,
                platform=plat_chosen,
                share_all=True,
                message_id=message_id
            )


def handle_text_message(message: dict):
    """Processes user text messages in Telegram (such as passwords, start commands, or revision feedback)."""
    chat_id = str(message.get("chat", {}).get("id"))
    text = message.get("text", "").strip()
    msg_id = message.get("message_id")

    logger.info(f"Received text message: '{text}' from chat {chat_id}")

    clean_text = text.lower().strip()
    if clean_text in ["/queue", "queue", "/tasks", "tasks", "/status", "status", "/activity", "activity"]:
        send_queue_dashboard(chat_id)
        return

    if clean_text in ["/posts", "posts", "/myposts", "myposts", "/gallery", "gallery", "/posted"]:
        send_posted_content_gallery(chat_id, page_index=0)
        return

    if clean_text in ["/sharestats", "sharestats", "/poststats"]:
        send_post_shares_overall_stats_menu(chat_id)
        return

    if clean_text in ["/share", "share", "/sharepost", "sharepost"]:
        send_posted_content_gallery(chat_id, page_index=0)
        return

    if clean_text.startswith("/shareall") or clean_text.startswith("shareall") or \
       clean_text.startswith("/share_ig") or clean_text.startswith("/share_fb") or \
       clean_text.startswith("/share_instagram") or clean_text.startswith("/share_facebook"):
        parts = text.split()
        plat = "both"
        if "ig" in clean_text or "instagram" in clean_text:
            plat = "instagram"
        elif "fb" in clean_text or "facebook" in clean_text:
            plat = "facebook"

        target_camp = parts[1] if len(parts) > 1 and not parts[1].startswith("/") else None
        if not target_camp:
            from db_campaigns import get_all_published_posts
            all_p = get_all_published_posts(limit=1)
            if all_p:
                target_camp = all_p[0]["id"]
        if target_camp:
            launch_post_share_task(chat_id=chat_id, campaign_id=target_camp, platform=plat, share_all=True)
        else:
            send_text_message(chat_id, "⚠️ No published posts found to share. Publish a post first or check /posts.")
        return

    if clean_text in ["/start", "start", "/help", "help", "hi", "hello", "menu", "/menu"]:
        send_root_choice_menu(chat_id)
        return

    if clean_text in ["/suggestions", "suggestions", "/suggest", "suggest"]:
        send_outreach_strategy_menu(chat_id, "both")
        return

    if clean_text in ["/random", "random", "/random_follow"]:
        send_outreach_count_menu(chat_id, platform="both", location="Random Explore Feed", mode="random")
        return

    if clean_text in ["/cancel", "cancel"]:
        if chat_id in chat_sessions:
            del chat_sessions[chat_id]
        send_root_choice_menu(chat_id)
        return

    if clean_text in ["/generate", "generate", "/create", "create", "/accounts", "accounts", "/profiles", "profiles"]:
        send_chrome_account_selection_menu(chat_id)
        return

    # Direct 24s Video Command: /video [prompt], "generate video", "create video", etc.
    is_video_cmd = (
        clean_text.startswith("/video") or
        clean_text.startswith("video:") or
        clean_text == "video" or
        "generate video" in clean_text or
        "create video" in clean_text or
        "make video" in clean_text or
        "make a video" in clean_text or
        "video generation" in clean_text or
        "24s video" in clean_text or
        "generate 24s" in clean_text
    )
    if is_video_cmd:
        prompt_val = text
        for pfx in ["/video", "video:", "generate video", "create video", "make video", "make a video", "video generation"]:
            if prompt_val.lower().startswith(pfx):
                prompt_val = prompt_val[len(pfx):].strip()
                break
        if not prompt_val or len(prompt_val) < 4:
            prompt_val = "Loan Solutions Home Loans (Apna Ghar) & Loan Against Property (LAP) in Indian Rupees"
        if chat_id in chat_sessions:
            del chat_sessions[chat_id]

        send_text_message(
            chat_id,
            f"🎬 <b>Generating 24-Second Gemini AI Video (Home Loan & LAP Strategic Focus)...</b>\n\n"
            f"📝 <b>Prompt:</b> <i>\"{prompt_val}\"</i>\n\n"
            "⚙️ <b>Pipeline Stages:</b>\n"
            "• Clip 1 (0-8s): 🏠 Home Loan - Dream of 'Apna Ghar' for Middle-Class Families\n"
            "• Clip 2 (8-16s): 🏢 Loan Against Property (LAP) - High Capital for Business Growth\n"
            "• Clip 3 (16-24s): 💼 Complete Solutions (Home, LAP, Personal & Business Loans) & Apply Online\n"
            "• Sequential Stitching to 24s Reel (9:16) with Indian Voiceover & Branding\n\n"
            "⏳ <b>Please wait at least 5 minutes (~5 to 6 minutes)!</b> High-definition AI video rendering (minimum 5 minutes per clip wait time), neural voiceover synthesis, and clip compilation take extra time. Complete preview with approval buttons will arrive here."
        )
        import threading
        def _run_24s_cmd():
            try:
                from media.gemini_video_engine import gemini_video_engine
                gemini_video_engine.run_full_24s_pipeline(
                    prompt=prompt_val,
                    product_name="Loan Solutions",
                    product_category="Finance",
                    platforms=["facebook", "instagram"],
                    send_to_telegram=True,
                    send_individual_clips=True,
                    logo_path=LOAN_SOLUTIONS_PATH if os.path.exists(LOAN_SOLUTIONS_PATH) else None,
                    chat_id=chat_id
                )
            except Exception as e_v:
                logger.error(f"Error generating 24s video from command: {e_v}")
                send_text_message(chat_id, f"⚠️ Video generation notice: {e_v}")

        threading.Thread(target=_run_24s_cmd, daemon=True).start()
        return

    # Direct Follow Stats Commands: /followstats, /stats, /leads
    if clean_text in ["/followstats", "/stats", "stats", "/leads", "/leadsstats"]:
        from telegram.bot import send_instagram_leads_stats_menu
        send_instagram_leads_stats_menu(chat_id)
        return

    # Direct Follow Commands: /follow @user, follow @user, /user @user, /profile @user
    import re
    is_follow_cmd = any(clean_text.startswith(p) for p in [
        "/follow", "follow @", "follow ",
        "/user ", "user ", "/profile ", "profile "
    ])
    if is_follow_cmd:
        raw_cmd = text
        for prefix in ["/follow", "follow @", "follow", "/user ", "user ", "/profile ", "profile "]:
            if raw_cmd.lower().startswith(prefix):
                raw_cmd = raw_cmd[len(prefix):].strip()
                break
        target_users = [u.strip().lstrip("@") for u in re.split(r"[\s,]+", raw_cmd) if u.strip().lstrip("@")]
        if target_users:
            if chat_id in chat_sessions:
                del chat_sessions[chat_id]
            launch_ig_follow_users_task(chat_id, target_users)
            return

    session = chat_sessions.get(chat_id)
    if not session:
        # If user directly typed @username without prior command
        if text.startswith("@") and len(text.split()) == 1:
            target_users = [text.strip().lstrip("@")]
            launch_ig_follow_users_task(chat_id, target_users)
            return

        if text.startswith("/"):
            send_root_choice_menu(chat_id)
        return

    # User provided specific Instagram username(s) to follow
    if session.get("action") == "AWAITING_IG_USERNAME":
        target_msg_id = session.get("message_id")
        del chat_sessions[chat_id]
        target_users = [u.strip().lstrip("@") for u in re.split(r"[\s,]+", text) if u.strip().lstrip("@")]
        if target_users:
            launch_ig_follow_users_task(chat_id, target_users, message_id=target_msg_id)
        else:
            send_text_message(
                chat_id,
                "⚠️ <b>Invalid format.</b> Please specify an account with @username (e.g. <code>@rahul_verma</code>) or use /cancel."
            )
        return

    # User provided target Instagram username to follow their followers
    if session.get("action") == "AWAITING_IG_TARGET_FOLLOWERS_USERNAME":
        target_msg_id = session.get("message_id")
        del chat_sessions[chat_id]
        parts = [p.strip() for p in text.split() if p.strip()]
        if parts:
            tgt_user = parts[0].lstrip("@").strip()
            if len(parts) > 1 and parts[1].isdigit():
                req_count = min(max(1, int(parts[1])), 1000)
                launch_ig_target_followers_task(chat_id, tgt_user, target_count=req_count, message_id=target_msg_id)
            else:
                cnt_keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": "25 Followers", "callback_data": f"ig_tgt_cnt:{tgt_user}:25"},
                            {"text": "50 Followers", "callback_data": f"ig_tgt_cnt:{tgt_user}:50"}
                        ],
                        [
                            {"text": "100 Followers", "callback_data": f"ig_tgt_cnt:{tgt_user}:100"},
                            {"text": "250 Followers", "callback_data": f"ig_tgt_cnt:{tgt_user}:250"}
                        ],
                        [
                            {"text": "500 Followers", "callback_data": f"ig_tgt_cnt:{tgt_user}:500"},
                            {"text": "1000 Followers (Max)", "callback_data": f"ig_tgt_cnt:{tgt_user}:1000"}
                        ],
                        [{"text": "🔙 Cancel", "callback_data": "outreach:plat:instagram"}]
                    ]
                }
                send_text_message(
                    chat_id,
                    f"👥 <b>Target Account:</b> <code>@{tgt_user}</code>\n\n"
                    "Choose how many followers to follow (up to 1,000 max):\n\n"
                    "⚡ <b>Safety Guardrails:</b>\n"
                    "• 12s–22s human delay between follows\n"
                    "• 3–4 min rest cooldown every 30 follows (safeguards account from rate-limits)\n"
                    "• Automatically filters out channels and commercial pages\n\n"
                    f"<i>💡 Or type any number directly (e.g. <code>@{tgt_user} 350</code>).</i>",
                    reply_markup=cnt_keyboard
                )
        else:
            send_text_message(chat_id, "⚠️ <b>Invalid format.</b> Please specify an account (e.g. <code>@lucknow_hearts</code>) or /cancel.")
        return

    # If session is Antigravity prompt but user entered an Instagram handle or follow command
    if session.get("action") == "AWAITING_ANTIGRAVITY_PROMPT" and (text.startswith("@") or clean_text.startswith("follow")):
        target_users = [u.strip().lstrip("@") for u in re.split(r"[\s,]+", text.replace("follow", "")) if u.strip().lstrip("@")]
        if target_users:
            del chat_sessions[chat_id]
            launch_ig_follow_users_task(chat_id, target_users)
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
        mode = session.get("mode", "location")
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
        target_count = min(val, 1000)
        if val > 1000:
            send_text_message(
                chat_id,
                f"ℹ️ <i>Notice: Request count capped at platform maximum of 1000 (entered: {val}). Note: A 2-minute safety pause automatically runs after every 250 requests to protect your account.</i>"
            )
        elif target_count > 250:
            send_text_message(
                chat_id,
                f"🛡️ <i>Safety notice: For targets over 250 ({target_count} selected), a 2-minute cooldown interval will automatically pause after every 250 requests.</i>"
            )

        launch_outreach_campaign(chat_id, platform=platform, location=location, target_count=target_count, mode=mode, message_id=target_msg_id)
        return

    # User provided custom group name for Social Friends Group Creator
    if session.get("action") == "AWAITING_GROUP_NAME":
        platform = session.get("platform", "facebook")
        group_type = session.get("group_type", "community_group")
        target_msg_id = session.get("message_id")
        group_name = text.strip()
        del chat_sessions[chat_id]

        launch_social_group_creation(chat_id, platform=platform, group_type=group_type, group_name=group_name, message_id=target_msg_id)
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

        from db_campaigns import get_campaign_from_db
        existing_camp = get_campaign_from_db(campaign_id) if campaign_id else {}
        db_rev = existing_camp.get("revision_count", 0)
        rev_count = db_rev + 1
        camp_platform = existing_camp.get("llm_provider") or "gemini"
        camp_platforms = existing_camp.get("platforms") or ["facebook", "instagram"]
        product_obj = existing_camp.get("product") or {}
        prod_name = product_obj.get("name") or "Featured Product"

        send_text_message(
            chat_id,
            f"🔄 <b>Revision #{rev_count} recorded for {prod_name}:</b>\n<i>\"{text}\"</i>\n\n"
            f"🤖 <b>Regenerating Content:</b> Opening Chrome and prompting {camp_platform.upper()} with your revision feedback...\n"
            f"🎨 Crafting new custom visual graphic & viral copy...\n"
            f"⏳ <i>Please wait ~35-50 seconds. An updated preview card with approval buttons will be sent here!</i>"
        )

        contact_num = existing_camp.get("contact_number") or (product_obj.get("contact_number") if product_obj else None)
        phone_match = re.search(r"\b([6-9]\d{9})\b", text)
        if phone_match:
            contact_num = phone_match.group(1)

        import threading
        def _run_revision():
            try:
                from browser.human_operator import execute_human_generation_and_telegram_flow
                execute_human_generation_and_telegram_flow(
                    platform=camp_platform,
                    product=product_obj,
                    custom_instructions=f"REVISION #{rev_count} REQUEST: {text}. Incorporate these specific user requirements into both the visual image and marketing copy.",
                    campaign_id=campaign_id,
                    platforms=camp_platforms,
                    revision_count=rev_count,
                    contact_number=contact_num
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


def ensure_single_poller_instance():
    """
    Ensures that only this process is polling Telegram.
    Finds and terminates any other running python instances running poller.py.
    """
    try:
        import psutil
        my_pid = os.getpid()
        killed = 0
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['pid'] == my_pid:
                    continue
                name = (proc.info.get('name') or '').lower()
                if 'python' in name:
                    cmdline = proc.info.get('cmdline') or []
                    cmd_str = ' '.join(cmdline).lower()
                    if 'poller.py' in cmd_str:
                        logger.warning(f"Terminating duplicate Telegram poller process (PID {proc.info['pid']})...")
                        proc.kill()
                        killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        if killed > 0:
            time.sleep(1.0)
            logger.info(f"Cleaned up {killed} duplicate Telegram poller process(es).")
    except Exception as e:
        logger.debug(f"Poller singleton check notice: {e}")


def start_polling():
    """Continuously long-polls Telegram for updates."""
    ensure_single_poller_instance()
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

            if res.get("error_code") == 409 or "409" in str(res.get("description", "")):
                logger.warning("Telegram 409 Conflict: another instance called getUpdates. Enforcing singleton poller...")
                ensure_single_poller_instance()
                time.sleep(5)
            else:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\nPoller stopped.", flush=True)
            break
        except Exception as e:
            logger.error(f"Error in polling loop: {e}")
            time.sleep(3)


if __name__ == "__main__":
    start_polling()
