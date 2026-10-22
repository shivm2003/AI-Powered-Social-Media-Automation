"""
Manvxi AI — Social Friends Group Automator.
Handles:
1. Facebook Community Group Creation & Friend Invitations (facebook.com/groups/create)
2. Facebook Messenger Group Chat Creation (facebook.com/messages/new)
3. Instagram Direct Group DM Creation (instagram.com/direct/inbox/ with compliant 30-member batching)
"""
import os
import sys
import time
import json
import random
import logging
import threading
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
        sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "automation"))

from browser.driver import browser
from config import PLATFORM_URLS
from telegram.bot import make_telegram_request, get_telegram_credentials, edit_message_text, send_text_message

logger = logging.getLogger("automation.social.social_groups")

ACTIVE_GROUP_TASKS = {}
ACTIVE_GROUP_TASKS_LOCK = threading.Lock()


def stop_social_group_task(task_id: str) -> bool:
    """Signals early cancellation to a running group task."""
    flag_file = BASE_DIR / "data" / f"stop_grp_{task_id}.flag"
    flag_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        flag_file.write_text("STOP", encoding="utf-8")
    except Exception:
        pass

    with ACTIVE_GROUP_TASKS_LOCK:
        task = ACTIVE_GROUP_TASKS.get(task_id)
        if task and "stop_event" in task:
            task["stop_event"].set()
            return True
    return flag_file.exists()


def update_db_social_group(group_id: str, status: str, member_count: int = 0, group_url: str = None, external_id: str = None, logs: list = None):
    """Updates group record in PostgreSQL and SQLite."""
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
            UPDATE social_groups
            SET status = %s,
                member_count = %s,
                group_url = COALESCE(%s, group_url),
                external_group_id = COALESCE(%s, external_group_id),
                logs = %s,
                updated_at = NOW()
            WHERE id = %s
        """, (status, member_count, group_url, external_id, json.dumps(logs or []), group_id))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.debug(f"PG group update note: {e}")

    # 2. SQLite
    db_path = BASE_DIR / "data" / "database.sqlite"
    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS social_groups (
                    id TEXT PRIMARY KEY,
                    platform TEXT,
                    group_type TEXT,
                    group_name TEXT,
                    group_url TEXT,
                    external_group_id TEXT,
                    member_count INTEGER,
                    status TEXT,
                    logs TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            cur.execute("""
                UPDATE social_groups
                SET status = ?,
                    member_count = ?,
                    group_url = COALESCE(?, group_url),
                    external_group_id = COALESCE(?, external_group_id),
                    logs = ?,
                    updated_at = datetime('now')
                WHERE id = ?
            """, (status, member_count, group_url, external_id, json.dumps(logs or []), group_id))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"SQLite group update note: {e}")


def ensure_db_social_group(group_id: str, platform: str, group_type: str, group_name: str):
    """Initializes social group record in PostgreSQL & SQLite."""
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
            CREATE TABLE IF NOT EXISTS social_groups (
                id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                group_type TEXT NOT NULL,
                group_name TEXT NOT NULL,
                group_url TEXT,
                external_group_id TEXT,
                member_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                logs TEXT DEFAULT '[]',
                telegram_message_id TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        cur.execute("""
            INSERT INTO social_groups (id, platform, group_type, group_name, status, logs)
            VALUES (%s, %s, %s, %s, 'creating', '[]')
            ON CONFLICT (id) DO NOTHING
        """, (group_id, platform, group_type, group_name))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.debug(f"PG group insert note: {e}")


def create_facebook_community_group(
    group_name: str,
    privacy: str = "private",
    max_invites: int = 50,
    on_progress=None,
    stop_event=None
) -> dict:
    """
    Creates a native Facebook Group (facebook.com/groups/create) and invites friends.
    """
    logger.info(f"Starting Facebook Community Group creation: '{group_name}' (Privacy: {privacy})...")
    logs = []
    invited_count = 0
    group_url = ""
    external_group_id = ""

    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains

    try:
        # 1. Navigate to Groups Create
        create_url = "https://www.facebook.com/groups/create/"
        driver = browser.navigate("facebook", create_url, refresh_first=False)
        time.sleep(3.0)

        from social.facebook import is_facebook_login_needed
        if is_facebook_login_needed(driver):
            msg = "Facebook login required. Please verify login in Chrome on Port 9222."
            logs.append(f"⚠️ {msg}")
            return {"status": "login_required", "platform": "facebook", "logs": logs}

        logs.append(f"🌐 Navigated to Facebook Group Creator: {create_url}")
        if on_progress:
            on_progress(0, f"Navigated to Facebook Group Creator...")

        # 2. Enter Group Name
        name_inputs = driver.find_elements(
            By.XPATH,
            "//input[@aria-label='Group name'] | //input[@type='text' and not(@placeholder='Search')]"
        )
        if not name_inputs:
            name_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")

        if not name_inputs:
            return {"status": "error", "message": "Group name input field not found on page.", "logs": logs}

        name_input = name_inputs[0]
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", name_input)
        time.sleep(0.5)
        name_input.click()
        name_input.clear()

        # Natural human keystrokes
        for char in group_name:
            name_input.send_keys(char)
            time.sleep(random.uniform(0.04, 0.09))

        logs.append(f"✏️ Entered Group Name: '{group_name}'")
        time.sleep(1.2)

        # 3. Select Privacy Dropdown if available
        try:
            privacy_dropdowns = driver.find_elements(
                By.XPATH,
                "//div[@aria-label='Choose privacy'] | //span[text()='Choose privacy']/ancestor::div[@role='button'] | //span[text()='Choose privacy']/ancestor::div[1]"
            )
            if privacy_dropdowns:
                privacy_dropdowns[0].click()
                time.sleep(1.0)
                # Select Private or Public
                target_opt = "Private" if privacy.lower() == "private" else "Public"
                opt_btns = driver.find_elements(
                    By.XPATH,
                    f"//span[contains(text(), '{target_opt}')]/ancestor::div[@role='button' or @role='menuitem' or @role='radio'][1]"
                )
                if opt_btns:
                    opt_btns[0].click()
                    logs.append(f"🔒 Set Group Privacy: {target_opt}")
                time.sleep(0.8)
        except Exception as e_priv:
            logger.debug(f"Privacy dropdown note: {e_priv}")

        # 4. Click 'Create' button
        create_btns = driver.find_elements(
            By.XPATH,
            "//div[@aria-label='Create'] | //span[text()='Create']/ancestor::div[@role='button'] | //button[contains(., 'Create')]"
        )
        clicked_create = False
        for c_btn in create_btns:
            try:
                if c_btn.is_displayed():
                    driver.execute_script("arguments[0].click();", c_btn)
                    clicked_create = True
                    logs.append("⚡ Clicked 'Create' button")
                    break
            except Exception:
                continue

        if not clicked_create and create_btns:
            create_btns[0].click()
            clicked_create = True

        # Wait for Facebook to provision the group & redirect
        time.sleep(5.0)
        group_url = driver.current_url
        if "facebook.com/groups/" in group_url:
            parts = [p for p in group_url.split("groups/")[-1].split("/") if p]
            if parts:
                external_group_id = parts[0]
            logs.append(f"🎉 Group successfully created! URL: {group_url}")
            logger.info(f"Facebook group created: {group_url}")
        else:
            logs.append(f"ℹ️ Submitted creation. Current URL: {group_url}")

        if on_progress:
            on_progress(invited_count, f"Group created! Inviting friends to '{group_name}'...")

        # 5. Invite Friends to the new Group
        time.sleep(2.0)
        try:
            # Look for Invite button on the group page
            invite_btns = driver.find_elements(
                By.XPATH,
                "//div[@aria-label='Invite'] | //span[text()='Invite']/ancestor::div[@role='button'] | //a[contains(@href, '/members') and contains(., 'Invite')]"
            )
            if invite_btns:
                invite_btns[0].click()
                time.sleep(2.5)
                logs.append("📋 Opened 'Invite Friends' modal")

                # Find checkable friend items in modal
                friend_checkboxes = driver.find_elements(
                    By.XPATH,
                    "//div[@role='dialog']//input[@type='checkbox'] | //div[@role='dialog']//div[@role='checkbox'] | //div[@role='dialog']//div[@aria-checked='false']"
                )

                logs.append(f"👥 Discovered {len(friend_checkboxes)} friend invitation candidates in dialog")

                for cb in friend_checkboxes[:max_invites]:
                    if stop_event and stop_event.is_set():
                        logs.append("🛑 Stop signal received during friend invitations.")
                        break
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", cb)
                        time.sleep(0.3)
                        driver.execute_script("arguments[0].click();", cb)
                        invited_count += 1
                        time.sleep(random.uniform(0.8, 1.6))
                    except Exception:
                        continue

                # Click Send Invites in modal
                send_inv_btns = driver.find_elements(
                    By.XPATH,
                    "//div[@role='dialog']//div[@aria-label='Send Invites' or @aria-label='Send invites'] | //div[@role='dialog']//span[text()='Send Invites' or text()='Send invites']/ancestor::div[@role='button']"
                )
                if send_inv_btns:
                    driver.execute_script("arguments[0].click();", send_inv_btns[0])
                    logs.append(f"✉️ Sent invitations to {invited_count} friends!")
                    time.sleep(2.0)
        except Exception as e_inv:
            logger.warning(f"Error during friend invitations: {e_inv}")
            logs.append(f"ℹ️ Invitation note: {e_inv}")

        return {
            "status": "success",
            "platform": "facebook",
            "group_type": "community_group",
            "group_name": group_name,
            "group_url": group_url,
            "external_group_id": external_group_id,
            "member_count": invited_count,
            "logs": logs,
        }

    except Exception as e:
        logger.error(f"Error creating Facebook community group: {e}", exc_info=True)
        logs.append(f"⚠️ Error: {str(e)}")
        return {
            "status": "error",
            "platform": "facebook",
            "group_type": "community_group",
            "group_name": group_name,
            "error": str(e),
            "logs": logs,
        }


def create_facebook_messenger_group(
    group_name: str,
    initial_message: str = None,
    max_members: int = 50,
    on_progress=None,
    stop_event=None
) -> dict:
    """
    Creates a Facebook Messenger Group Chat (facebook.com/messages/new) with selected friends.
    """
    logger.info(f"Starting Facebook Messenger Group Chat: '{group_name}' (Max members: {max_members})...")
    logs = []
    members_added = 0
    chat_url = ""

    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys

    try:
        msg_url = "https://www.facebook.com/messages/new"
        driver = browser.navigate("facebook", msg_url, refresh_first=False)
        time.sleep(3.0)

        logs.append(f"🌐 Navigated to Messenger New Chat: {msg_url}")
        if on_progress:
            on_progress(0, "Opening Messenger New Chat composer...")

        # Search / Select friends to add to group
        search_inputs = driver.find_elements(
            By.XPATH,
            "//input[@aria-label='Search to send a message'] | //input[@placeholder='Search' or contains(@placeholder, 'Type a name')]"
        )
        if search_inputs:
            inp = search_inputs[0]
            inp.click()
            time.sleep(1.0)

            # Pick from suggested friends list
            suggested = driver.find_elements(
                By.XPATH,
                "//ul[@role='listbox']//li | //div[@role='listbox']//div[@role='option'] | //div[contains(@class, 'x1n2onr6')]//div[@role='button'][.//span]"
            )
            for item in suggested[:max_members]:
                if stop_event and stop_event.is_set():
                    break
                try:
                    driver.execute_script("arguments[0].click();", item)
                    members_added += 1
                    time.sleep(random.uniform(0.6, 1.2))
                except Exception:
                    continue

            logs.append(f"👥 Added {members_added} friends to group recipient list")

        # Focus message box and send initial greeting
        textboxes = driver.find_elements(
            By.XPATH,
            "//div[@role='textbox' and contains(@aria-label, 'Message')] | //div[@contenteditable='true']"
        )
        if textboxes:
            tb = textboxes[0]
            tb.click()
            time.sleep(0.5)
            greeting = initial_message or f"Hello everyone! Welcome to our group '{group_name}'."
            tb.send_keys(greeting)
            time.sleep(0.5)
            tb.send_keys(Keys.ENTER)
            logs.append(f"💬 Sent initial greeting: '{greeting[:40]}...'")
            time.sleep(2.5)

        chat_url = driver.current_url
        logs.append(f"🎉 Messenger Group Chat created! Thread URL: {chat_url}")

        return {
            "status": "success",
            "platform": "facebook",
            "group_type": "messenger_chat",
            "group_name": group_name,
            "group_url": chat_url,
            "member_count": members_added,
            "logs": logs,
        }

    except Exception as e:
        logger.error(f"Error creating Facebook Messenger group: {e}", exc_info=True)
        logs.append(f"⚠️ Error: {str(e)}")
        return {
            "status": "error",
            "platform": "facebook",
            "group_type": "messenger_chat",
            "group_name": group_name,
            "error": str(e),
            "logs": logs,
        }


def create_instagram_direct_group(
    group_name: str,
    initial_message: str = None,
    max_members: int = 30,
    on_progress=None,
    stop_event=None
) -> dict:
    """
    Creates an Instagram Direct Message Group Chat (instagram.com/direct/inbox/)
    safely batched to max 30 members (strictly below Instagram's 32-member DM ceiling).
    """
    logger.info(f"Starting Instagram Direct Group creation: '{group_name}' (Target members: {max_members})...")
    logs = []
    members_added = 0
    group_url = ""

    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys

    try:
        inbox_url = "https://www.instagram.com/direct/inbox/"
        driver = browser.navigate("instagram", inbox_url, refresh_first=False)
        time.sleep(3.0)

        logs.append(f"🌐 Navigated to Instagram Direct Inbox: {inbox_url}")
        if on_progress:
            on_progress(0, "Opening Instagram Direct Inbox...")

        # Dismiss notification prompt if any
        for b in driver.find_elements(By.XPATH, "//button[text()='Not Now' or text()='Cancel']"):
            try:
                if b.is_displayed():
                    b.click()
                    time.sleep(0.5)
            except Exception:
                pass

        # Click New Message icon
        new_msg_btns = driver.find_elements(
            By.XPATH,
            "//svg[@aria-label='New message']/ancestor::div[@role='button'] | //svg[@aria-label='New message']/ancestor::a | //button[contains(., 'Send message')]"
        )
        if not new_msg_btns:
            new_msg_btns = driver.find_elements(By.CSS_SELECTOR, "a[href*='/direct/new/']")

        if not new_msg_btns:
            return {"status": "error", "message": "Could not find 'New Message' button in Instagram Direct.", "logs": logs}

        new_msg_btns[0].click()
        time.sleep(2.0)
        logs.append("📋 Opened Instagram 'New Message' recipient modal")

        # Select members from suggested accounts in modal
        checkboxes = driver.find_elements(
            By.XPATH,
            "//div[@role='dialog']//input[@type='checkbox'] | //div[@role='dialog']//input[@name='ContactSearchResultCheckbox'] | //div[@role='dialog']//div[@role='button'][.//span]"
        )

        effective_limit = min(max_members, 30)  # Safe Instagram DM ceiling
        logs.append(f"👥 Discovered {len(checkboxes)} potential accounts. Selecting up to {effective_limit} members...")

        for cb in checkboxes[:effective_limit]:
            if stop_event and stop_event.is_set():
                logs.append("🛑 Stop signal received during Instagram group creation.")
                break
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", cb)
                time.sleep(0.2)
                driver.execute_script("arguments[0].click();", cb)
                members_added += 1
                time.sleep(random.uniform(0.4, 0.9))
            except Exception:
                continue

        # Click 'Chat' / 'Next' button in modal
        chat_btns = driver.find_elements(
            By.XPATH,
            "//div[@role='dialog']//button[text()='Chat' or text()='Next'] | //div[@role='dialog']//div[@role='button'][text()='Chat']"
        )
        if chat_btns:
            chat_btns[0].click()
            time.sleep(3.0)
            logs.append("⚡ Clicked 'Chat' to provision group thread")

        # Send introductory welcome message
        msg_boxes = driver.find_elements(
            By.XPATH,
            "//div[@role='textbox' and contains(@aria-label, 'Message')] | //div[@contenteditable='true'] | //textarea"
        )
        if msg_boxes:
            mb = msg_boxes[0]
            mb.click()
            time.sleep(0.5)
            greeting = initial_message or f"Hey everyone! Welcome to '{group_name}'."
            mb.send_keys(greeting)
            time.sleep(0.5)
            mb.send_keys(Keys.ENTER)
            logs.append(f"💬 Sent initial welcome message: '{greeting}'")
            time.sleep(2.0)

        group_url = driver.current_url
        logs.append(f"🎉 Instagram Direct Group successfully created! Thread URL: {group_url}")

        return {
            "status": "success",
            "platform": "instagram",
            "group_type": "ig_direct_group",
            "group_name": group_name,
            "group_url": group_url,
            "member_count": members_added,
            "logs": logs,
        }

    except Exception as e:
        logger.error(f"Error creating Instagram direct group: {e}", exc_info=True)
        logs.append(f"⚠️ Error: {str(e)}")
        return {
            "status": "error",
            "platform": "instagram",
            "group_type": "ig_direct_group",
            "group_name": group_name,
            "error": str(e),
            "logs": logs,
        }


def run_social_group_task(
    task_id: str,
    platform: str,
    group_type: str,
    group_name: str,
    privacy: str = "private",
    initial_message: str = None,
    max_invites: int = 50,
    tg_chat_id: str = None,
    tg_message_id: int = None
) -> dict:
    """
    Unified manager for executing and tracking social group creation tasks.
    """
    clean_platform = (platform or "facebook").lower().strip()
    clean_type = (group_type or "community_group").lower().strip()
    clean_name = (group_name or f"My Community {time.strftime('%Y')}").strip()

    stop_event = threading.Event()
    with ACTIVE_GROUP_TASKS_LOCK:
        ACTIVE_GROUP_TASKS[task_id] = {
            "stop_event": stop_event,
            "platform": clean_platform,
            "group_type": clean_type,
            "group_name": clean_name,
            "started_at": time.time(),
        }

    ensure_db_social_group(task_id, clean_platform, clean_type, clean_name)

    # Initial Telegram update
    if tg_chat_id and tg_message_id:
        try:
            edit_message_text(
                tg_chat_id,
                tg_message_id,
                f"👥 <b>Creating Social Group:</b> <code>{clean_name}</code>\n\n"
                f"📍 <b>Platform:</b> {clean_platform.capitalize()} ({clean_type})\n"
                f"⏳ <b>Status:</b> Initializing Chrome session & navigating to group creator...",
                keyboard={"inline_keyboard": [[{"text": "🛑 Stop Creation", "callback_data": f"grp:stop:{task_id}"}]]}
            )
        except Exception:
            pass

    def on_progress(count, msg):
        update_db_social_group(task_id, "creating", member_count=count, logs=[msg])
        if tg_chat_id and tg_message_id:
            try:
                edit_message_text(
                    tg_chat_id,
                    tg_message_id,
                    f"👥 <b>Creating Social Group:</b> <code>{clean_name}</code>\n\n"
                    f"📍 <b>Platform:</b> {clean_platform.capitalize()} ({clean_type})\n"
                    f"📊 <b>Invited/Added:</b> {count} friends\n"
                    f"⏳ <b>Status:</b> {msg}",
                    keyboard={"inline_keyboard": [[{"text": "🛑 Stop Creation", "callback_data": f"grp:stop:{task_id}"}]]}
                )
            except Exception:
                pass

    results = []

    try:
        if clean_platform in ["facebook", "both"]:
            if clean_type in ["community_group", "all"]:
                res_fb = create_facebook_community_group(
                    group_name=clean_name,
                    privacy=privacy,
                    max_invites=max_invites,
                    on_progress=on_progress,
                    stop_event=stop_event
                )
                results.append(res_fb)
                update_db_social_group(
                    task_id,
                    res_fb.get("status", "completed"),
                    member_count=res_fb.get("member_count", 0),
                    group_url=res_fb.get("group_url"),
                    external_id=res_fb.get("external_group_id"),
                    logs=res_fb.get("logs", [])
                )

            if clean_type in ["messenger_chat", "all"]:
                res_ms = create_facebook_messenger_group(
                    group_name=clean_name,
                    initial_message=initial_message,
                    max_members=max_invites,
                    on_progress=on_progress,
                    stop_event=stop_event
                )
                results.append(res_ms)

        if clean_platform in ["instagram", "both"]:
            res_ig = create_instagram_direct_group(
                group_name=clean_name,
                initial_message=initial_message,
                max_members=min(max_invites, 30),
                on_progress=on_progress,
                stop_event=stop_event
            )
            results.append(res_ig)
            update_db_social_group(
                task_id,
                res_ig.get("status", "completed"),
                member_count=res_ig.get("member_count", 0),
                group_url=res_ig.get("group_url"),
                logs=res_ig.get("logs", [])
            )

    finally:
        with ACTIVE_GROUP_TASKS_LOCK:
            ACTIVE_GROUP_TASKS.pop(task_id, None)

    # Final summary in Telegram
    if tg_chat_id and tg_message_id:
        finish_text = (
            f"🎉 <b>Friends Group Created Successfully!</b>\n\n"
            f"🏷️ <b>Group Name:</b> <code>{clean_name}</code>\n"
            f"👥 <b>Platform:</b> {clean_platform.capitalize()}\n"
        )
        for r in results:
            finish_text += f"\n• <b>{r.get('group_type', 'Group')}:</b> {r.get('member_count', 0)} friends invited"
            if r.get('group_url'):
                finish_text += f"\n  🔗 <code>{r.get('group_url')}</code>"

        keyboard = {
            "inline_keyboard": [
                [{"text": "👥 Create Another Group", "callback_data": "root:friends_group"}],
                [{"text": "📋 Main Menu", "callback_data": "flow:start"}]
            ]
        }
        try:
            edit_message_text(tg_chat_id, tg_message_id, finish_text, keyboard=keyboard)
        except Exception:
            send_text_message(tg_chat_id, finish_text, reply_markup=keyboard)

    return {
        "status": "success",
        "task_id": task_id,
        "platform": clean_platform,
        "results": results
    }
