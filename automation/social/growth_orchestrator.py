"""
Growth & Outreach Orchestrator.
Manages Facebook Friend Requests and Instagram Follows execution,
handles simultaneous dual-platform runs, updates databases, and streams live progress to Telegram.
"""
import os
import sys
import time
import json
import uuid
import random
import threading
import logging
from pathlib import Path

# Add automation directory to path
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.append(str(BASE_DIR / "automation"))

from telegram.bot import make_telegram_request, get_telegram_credentials, edit_message_text, send_text_message
from social.facebook_friends import send_facebook_friend_requests
from social.instagram_follow import send_instagram_follow_requests

logger = logging.getLogger("automation.social.growth_orchestrator")

# In-memory registry of active growth tasks
ACTIVE_TASKS = {}
ACTIVE_TASKS_LOCK = threading.Lock()


def stop_growth_campaign(campaign_id: str) -> bool:
    """Signals an active campaign to stop across processes and threads."""
    # 1. File flag (works across separate child processes)
    try:
        flag_file = BASE_DIR / "data" / f"stop_{campaign_id}.flag"
        flag_file.parent.mkdir(parents=True, exist_ok=True)
        flag_file.write_text("STOP", encoding="utf-8")
        logger.info(f"Wrote file stop flag: {flag_file}")
    except Exception as e:
        logger.warning(f"Could not write stop flag file: {e}")

    # 2. In-memory event (if in same process)
    with ACTIVE_TASKS_LOCK:
        task = ACTIVE_TASKS.get(campaign_id)
        if task and "stop_event" in task:
            task["stop_event"].set()
            logger.info(f"Stop signal set in memory for campaign {campaign_id}")
            return True
    return True


def get_progress_bar(current: int, total: int, length: int = 10) -> str:
    """Generates a text progress bar: [■■■■□□□□□□]"""
    if total <= 0:
        return "[□" * length + "]"
    fraction = min(1.0, max(0.0, current / total))
    filled = int(round(fraction * length))
    empty = length - filled
    return f"[{'■' * filled}{'□' * empty}]"


def ensure_db_campaign_exists(campaign_id: str, platform: str, location: str, target_count: int):
    """Ensures campaign record exists in PostgreSQL and SQLite before updating."""
    # 1. PostgreSQL
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
            INSERT INTO growth_campaigns (id, platform, location, target_count, fb_sent_count, ig_sent_count, status, logs, created_at, updated_at)
            VALUES (%s, %s, %s, %s, 0, 0, 'running', '[]', NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """, (campaign_id, platform, location, target_count))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.debug(f"PG campaign insert note: {e}")

    # 2. SQLite
    db_path = BASE_DIR / "data" / "database.sqlite"
    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("""
                INSERT OR IGNORE INTO growth_campaigns (id, platform, location, target_count, fb_sent_count, ig_sent_count, status, logs, created_at, updated_at)
                VALUES (?, ?, ?, ?, 0, 0, 'running', '[]', datetime('now'), datetime('now'))
            """, (campaign_id, platform, location, target_count))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"SQLite campaign insert note: {e}")


def update_db_campaign_status(campaign_id: str, fb_sent: int, ig_sent: int, status: str, log_list: list = None):
    """Updates campaign status and counters in PostgreSQL and SQLite."""
    # 1. PostgreSQL
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
            UPDATE growth_campaigns
            SET fb_sent_count = %s,
                ig_sent_count = %s,
                status = %s,
                logs = %s,
                updated_at = NOW()
            WHERE id = %s
        """, (fb_sent, ig_sent, status, json.dumps(log_list or []), campaign_id))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.debug(f"PG growth update note: {e}")

    # 2. SQLite
    db_path = BASE_DIR / "data" / "database.sqlite"
    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("""
                UPDATE growth_campaigns
                SET fb_sent_count = ?,
                    ig_sent_count = ?,
                    status = ?,
                    logs = ?,
                    updated_at = datetime('now')
                WHERE id = ?
            """, (fb_sent, ig_sent, status, json.dumps(log_list or []), campaign_id))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"SQLite growth update note: {e}")


def run_growth_campaign(
    campaign_id: str,
    platform: str,
    location: str,
    target_count: int = 10,
    safety_delay: int = 15,
    tg_chat_id: str = None,
    tg_message_id: int = None,
    telegram_chat_id: str = None,
    telegram_message_id: int = None,
    **kwargs
) -> dict:
    """
    Executes a complete growth outreach campaign (Facebook, Instagram, or Both simultaneously).
    """
    tg_chat_id = tg_chat_id or telegram_chat_id or kwargs.get("chat_id")
    tg_message_id = tg_message_id or telegram_message_id or kwargs.get("message_id")

    stop_event = threading.Event()
    with ACTIVE_TASKS_LOCK:
        ACTIVE_TASKS[campaign_id] = {
            "stop_event": stop_event,
            "platform": platform,
            "location": location,
            "target_count": target_count,
            "started_at": time.time(),
        }

    # Background watcher for cross-process file-based stop flag
    def _watch_stop_flag():
        flag_file = BASE_DIR / "data" / f"stop_{campaign_id}.flag"
        while not stop_event.is_set():
            if flag_file.exists():
                logger.info(f"Detected stop flag file for {campaign_id}! Setting stop event.")
                stop_event.set()
                try:
                    flag_file.unlink()
                except Exception:
                    pass
                break
            time.sleep(0.5)

    threading.Thread(target=_watch_stop_flag, daemon=True).start()

    clean_platform = (platform or "both").lower().strip()
    location = (location or "Global").strip()
    target_count = max(1, min(250, int(target_count)))
    safety_delay = max(5, int(safety_delay))

    logger.info(f"=== Launching Growth Campaign {campaign_id}: {clean_platform.upper()} in '{location}' (Target: {target_count}) ===")

    state = {
        "fb_sent": 0,
        "ig_sent": 0,
        "total_sent": 0,
        "last_tg_update": 0,
        "logs": [],
    }

    total_target = (target_count * 2) if clean_platform == "both" else target_count

    def send_tg_live_update(force=False):
        now = time.time()
        if not tg_chat_id:
            return
        # Throttle Telegram edits to max once every 3.5s to avoid hitting rate limits
        if not force and (now - state["last_tg_update"] < 3.5):
            return

        state["last_tg_update"] = now
        progress_str = get_progress_bar(state["total_sent"], total_target)
        
        status_header = (
            f"🚀 <b>Outreach & Growth in Progress</b>\n\n"
            f"📍 <b>Location:</b> {location}\n"
            f"🎯 <b>Target:</b> {total_target} total requests\n\n"
            f"📊 <b>Progress:</b> {progress_str} <b>{state['total_sent']}/{total_target}</b>\n"
        )

        if clean_platform in ["facebook", "both"]:
            status_header += f"📘 <b>Facebook Friends:</b> {state['fb_sent']}/{target_count}\n"
        if clean_platform in ["instagram", "both"]:
            status_header += f"📸 <b>Instagram Follows:</b> {state['ig_sent']}/{target_count}\n"

        status_header += f"⏱️ <i>Human Safety Pacing: ~{safety_delay}s cooldown</i>\n"

        stop_keyboard = {
            "inline_keyboard": [
                [{"text": "🛑 Stop Outreach Task", "callback_data": f"outreach:stop:{campaign_id}"}],
                [{"text": "🔄 Refresh Status", "callback_data": f"outreach:status:{campaign_id}"}]
            ]
        }

        if tg_message_id:
            try:
                edit_message_text(tg_chat_id, tg_message_id, status_header, keyboard=stop_keyboard)
            except Exception as e_ed:
                logger.debug(f"TG live update edit note: {e_ed}")

    # Progress callbacks for Facebook and Instagram
    def on_fb_progress(sent, target, details):
        state["fb_sent"] = sent
        state["total_sent"] = state["fb_sent"] + state["ig_sent"]
        u_name = details.get("user", "User")
        state["logs"].append(f"[Facebook] Sent friend request #{sent} to {u_name}")
        update_db_campaign_status(campaign_id, state["fb_sent"], state["ig_sent"], "running", state["logs"])
        send_tg_live_update()

    def on_ig_progress(sent, target, details):
        state["ig_sent"] = sent
        state["total_sent"] = state["fb_sent"] + state["ig_sent"]
        u_name = details.get("user", "User")
        state["logs"].append(f"[Instagram] Followed #{sent}: @{u_name}")
        update_db_campaign_status(campaign_id, state["fb_sent"], state["ig_sent"], "running", state["logs"])
        send_tg_live_update()

    # Initial DB status
    ensure_db_campaign_exists(campaign_id, clean_platform, location, target_count)
    update_db_campaign_status(campaign_id, 0, 0, "running", ["Outreach campaign started"])
    send_tg_live_update(force=True)

    fb_result = {}
    ig_result = {}

    try:
        if clean_platform == "facebook":
            fb_result = send_facebook_friend_requests(
                location=location,
                target_count=target_count,
                safety_delay=safety_delay,
                on_progress=on_fb_progress,
                stop_event=stop_event
            )
            state["fb_sent"] = fb_result.get("sent", 0)

        elif clean_platform == "instagram":
            ig_result = send_instagram_follow_requests(
                location=location,
                target_count=target_count,
                safety_delay=safety_delay,
                on_progress=on_ig_progress,
                stop_event=stop_event
            )
            state["ig_sent"] = ig_result.get("sent", 0)

        elif clean_platform == "both":
            # Execute alternating batches for natural human browsing stability
            batch_size = 2
            fb_done = 0
            ig_done = 0

            while (fb_done < target_count or ig_done < target_count) and not stop_event.is_set():
                if fb_done < target_count and not stop_event.is_set():
                    to_send = min(batch_size, target_count - fb_done)
                    sub_fb = send_facebook_friend_requests(
                        location=location,
                        target_count=to_send,
                        safety_delay=safety_delay,
                        on_progress=on_fb_progress,
                        stop_event=stop_event
                    )
                    fb_done += sub_fb.get("sent", 0)
                    time.sleep(random.uniform(4.0, 7.0))

                if ig_done < target_count and not stop_event.is_set():
                    to_send = min(batch_size, target_count - ig_done)
                    sub_ig = send_instagram_follow_requests(
                        location=location,
                        target_count=to_send,
                        safety_delay=safety_delay,
                        on_progress=on_ig_progress,
                        stop_event=stop_event
                    )
                    ig_done += sub_ig.get("sent", 0)
                    time.sleep(random.uniform(4.0, 7.0))

            state["fb_sent"] = fb_done
            state["ig_sent"] = ig_done

    finally:
        with ACTIVE_TASKS_LOCK:
            ACTIVE_TASKS.pop(campaign_id, None)

    state["total_sent"] = state["fb_sent"] + state["ig_sent"]
    final_status = "stopped" if stop_event.is_set() else "completed"

    update_db_campaign_status(campaign_id, state["fb_sent"], state["ig_sent"], final_status, state["logs"])

    # Final summary update in Telegram
    if tg_chat_id:
        finish_text = (
            f"🎉 <b>Outreach Campaign {final_status.capitalize()}!</b>\n\n"
            f"📍 <b>Location:</b> {location}\n"
            f"📊 <b>Results Summary:</b>\n"
            f"• 📘 <b>Facebook Friend Requests Sent:</b> {state['fb_sent']}/{target_count if clean_platform in ['facebook', 'both'] else 0}\n"
            f"• 📸 <b>Instagram Follow Requests Sent:</b> {state['ig_sent']}/{target_count if clean_platform in ['instagram', 'both'] else 0}\n"
            f"• 🏆 <b>Total Outreach Actions:</b> {state['total_sent']}/{total_target}\n\n"
            f"🔒 <i>All accounts safely protected with human delay pacing.</i>"
        )
        post_keyboard = {
            "inline_keyboard": [
                [{"text": "👥 Start New Outreach", "callback_data": "root:outreach"}],
                [{"text": "🎨 Generate Content", "callback_data": "root:content"}],
                [{"text": "📋 Main Menu", "callback_data": "flow:start"}]
            ]
        }
        if tg_message_id:
            try:
                edit_message_text(tg_chat_id, tg_message_id, finish_text, keyboard=post_keyboard)
            except Exception:
                send_text_message(tg_chat_id, finish_text, reply_markup=post_keyboard)
        else:
            send_text_message(tg_chat_id, finish_text, reply_markup=post_keyboard)

    return {
        "status": final_status,
        "campaign_id": campaign_id,
        "platform": clean_platform,
        "location": location,
        "fb_sent": state["fb_sent"],
        "ig_sent": state["ig_sent"],
        "total_sent": state["total_sent"],
        "logs": state["logs"],
    }
