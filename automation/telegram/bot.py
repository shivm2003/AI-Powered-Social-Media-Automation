"""
Telegram Bot for Preview and Approval Workflow.
Features:
- Sends photo/video previews with inline interactive buttons: [✅ Approve], [✏️ Revise], [❌ Reject]
- Handles approval to trigger social posting
- Handles user revision feedback/suggestions to remake content and resend preview
"""
import os
import time
import json
import urllib.request
import urllib.parse
import urllib.error
import logging
import sys
from pathlib import Path
import sqlite3
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
except Exception:
    pass

logger = logging.getLogger("automation.telegram")

BASE_DIR = Path(__file__).parent.parent.parent
DB_PATH = BASE_DIR / "data" / "database.sqlite"

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env.local")
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass


def get_telegram_credentials():
    """Retrieve bot token and chat ID from DB settings or environment."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    # If missing from env, check PostgreSQL
    if not bot_token or not chat_id:
        try:
            import psycopg2
            pg_user = os.environ.get("DB_USER", "postgres")
            pg_pass = os.environ.get("DB_PASSWORD", "Shivam@123")
            pg_host = os.environ.get("DB_HOST", "localhost")
            pg_port = int(os.environ.get("DB_PORT", "5432"))
            pg_db = os.environ.get("DB_NAME", "Social_Media")
            conn = psycopg2.connect(dbname=pg_db, user=pg_user, password=pg_pass, host=pg_host, port=pg_port)
            cur = conn.cursor()
            cur.execute("SELECT key, value FROM settings WHERE key IN ('telegram_bot_token', 'telegram_chat_id')")
            rows = cur.fetchall()
            cur.close()
            conn.close()
            for k, v in rows:
                if k == "telegram_bot_token" and v:
                    bot_token = v
                elif k == "telegram_chat_id" and v:
                    chat_id = v
        except Exception as e:
            logger.debug(f"Could not read Telegram settings from PostgreSQL: {e}")

    # Fallback to SQLite if still missing
    if (not bot_token or not chat_id) and DB_PATH.exists():
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT key, value FROM settings WHERE key IN ('telegram_bot_token', 'telegram_chat_id')")
            rows = cur.fetchall()
            conn.close()
            for k, v in rows:
                if k == "telegram_bot_token" and v:
                    bot_token = v
                elif k == "telegram_chat_id" and v:
                    chat_id = v
        except Exception as e:
            logger.warning(f"Failed to read Telegram settings from DB: {e}")

    return bot_token, chat_id


def make_telegram_request(token: str, method: str, data: dict = None, files: dict = None) -> dict:
    """Helper to call Telegram Bot API using urllib."""
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        if files:
            # Multipart form-data
            boundary = f"----WebKitFormBoundary{os.urandom(8).hex()}"
            body = bytearray()

            for key, val in (data or {}).items():
                body.extend(f"--{boundary}\r\n".encode("utf-8"))
                body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
                body.extend(f"{val}\r\n".encode("utf-8"))

            for key, (filename, file_bytes, mime) in files.items():
                body.extend(f"--{boundary}\r\n".encode("utf-8"))
                body.extend(f'Content-Disposition: form-data; name="{key}"; filename="{filename}"\r\n'.encode("utf-8"))
                body.extend(f"Content-Type: {mime}\r\n\r\n".encode("utf-8"))
                body.extend(file_bytes)
                body.extend(b"\r\n")

            body.extend(f"--{boundary}--\r\n".encode("utf-8"))

            req = urllib.request.Request(
                url,
                data=bytes(body),
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
            )
        else:
            json_bytes = json.dumps(data or {}).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=json_bytes,
                headers={"Content-Type": "application/json"}
            )

        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            pass
        if "message is not modified" in err_body:
            logger.debug(f"Telegram notice: message content unchanged ({method})")
            return {"ok": True, "description": "message not modified"}
        if getattr(e, "code", None) == 409 or "409" in str(e):
            logger.warning(f"Telegram 409 Conflict ({method}): Another bot instance is polling with this token.")
            return {"ok": False, "error_code": 409, "description": err_body or "Conflict: duplicate bot instance"}
        logger.error(f"Telegram API request failed ({method}): {e} {err_body}")
        return {"ok": False, "description": err_body or str(e)}
    except Exception as e:
        logger.error(f"Telegram API request failed ({method}): {e}")
        return {"ok": False, "description": str(e)}


LOAN_SOLUTIONS_APPLY_URL = "https://loansolutions.everythingrental.in/application"


def send_preview_to_telegram(
    campaign_id: str,
    caption: str,
    media_path: str,
    platforms: list = None,
    revision_count: int = 0,
    product_name: str = None,
    apply_url: str = None
) -> dict:
    """
    Sends generated image/video along with caption and interactive approval buttons to Telegram.
    When the product is Loan Solutions, includes the Apply Now Button pointing to
    https://loansolutions.everythingrental.in/application
    """
    bot_token, chat_id = get_telegram_credentials()
    if not bot_token or not chat_id:
        logger.warning("Telegram Bot Token or Chat ID not configured.")
        return {
            "status": "warning",
            "message": "Telegram Bot Token or Chat ID not configured. Please set them in Settings."
        }

    # Check if this campaign/product is Loan Solutions
    is_loan_solutions = False
    if apply_url or (product_name and "loan" in product_name.lower()):
        is_loan_solutions = True
    elif caption and ("loan" in caption.lower() or "everythingrental.in" in caption.lower()):
        is_loan_solutions = True
    elif campaign_id:
        try:
            from telegram.poller import get_campaign_data
            camp_info = get_campaign_data(campaign_id)
            if camp_info:
                p_name = camp_info.get("product_name") or ""
                p_cat = camp_info.get("product_category") or ""
                if "loan" in p_name.lower() or "finance" in p_cat.lower():
                    is_loan_solutions = True
        except Exception:
            pass

    target_apply_url = apply_url or LOAN_SOLUTIONS_APPLY_URL

    # If Loan Solutions, ensure caption strictly begins with the mandatory Apply Now link at Line 1
    if is_loan_solutions:
        try:
            from social.caption_helper import ensure_apply_now_at_start
            caption = ensure_apply_now_at_start(caption, apply_url=target_apply_url, is_loan=True)
        except Exception:
            if target_apply_url not in caption:
                caption = f"👉 Apply Now: {target_apply_url}\n\n{caption.strip()}"

    import html
    safe_caption = html.escape(caption)
    platforms_str = ", ".join(platforms or ["Facebook", "Instagram"])
    text_content = (
        f"🌟 <b>Content Preview for {platforms_str}</b>\n"
        f"{f'<i>(Revision #{revision_count})</i>' if revision_count > 0 else ''}\n\n"
        f"📝 <b>Caption:</b>\n{safe_caption}\n\n"
        f"👉 <i>Review above and choose an action:</i>"
    )

    # Inline keyboard buttons - includes Apply Now button for Loan Solutions
    keyboard_rows = [
        [
            {"text": "✅ Approve & Post", "callback_data": f"approve:{campaign_id}"},
            {"text": "✏️ Suggest Revision", "callback_data": f"revise:{campaign_id}"},
        ],
    ]
    if is_loan_solutions:
        keyboard_rows.append([
            {"text": "📝 Apply Now 🔗", "url": target_apply_url}
        ])
    keyboard_rows.append([
        {"text": "❌ Reject / Cancel", "callback_data": f"reject:{campaign_id}"}
    ])
    keyboard = {"inline_keyboard": keyboard_rows}

    # If media exists, sendPhoto or sendVideo
    if media_path and os.path.exists(media_path):
        filename = os.path.basename(media_path)
        ext = filename.lower().split(".")[-1]
        with open(media_path, "rb") as f:
            file_bytes = f.read()

        if ext in ["mp4", "mov", "avi"]:
            res = make_telegram_request(
                bot_token,
                "sendVideo",
                data={
                    "chat_id": chat_id,
                    "caption": text_content[:1024],
                    "parse_mode": "HTML",
                    "reply_markup": json.dumps(keyboard),
                },
                files={"video": (filename, file_bytes, "video/mp4")}
            )
            if not res.get("ok"):
                plain_text = f"🌟 Content Preview for {platforms_str}\n\n📝 Caption:\n{caption[:900]}\n\n👉 Review above and choose an action:"
                res = make_telegram_request(
                    bot_token,
                    "sendVideo",
                    data={
                        "chat_id": chat_id,
                        "caption": plain_text[:1024],
                        "reply_markup": json.dumps(keyboard),
                    },
                    files={"video": (filename, file_bytes, "video/mp4")}
                )
        else:
            res = make_telegram_request(
                bot_token,
                "sendPhoto",
                data={
                    "chat_id": chat_id,
                    "caption": text_content[:1024],
                    "parse_mode": "HTML",
                    "reply_markup": json.dumps(keyboard),
                },
                files={"photo": (filename, file_bytes, "image/png")}
            )
            if not res.get("ok"):
                plain_text = f"🌟 Content Preview for {platforms_str}\n\n📝 Caption:\n{caption[:900]}\n\n👉 Review above and choose an action:"
                res = make_telegram_request(
                    bot_token,
                    "sendPhoto",
                    data={
                        "chat_id": chat_id,
                        "caption": plain_text[:1024],
                        "reply_markup": json.dumps(keyboard),
                    },
                    files={"photo": (filename, file_bytes, "image/png")}
                )
    else:
        # Send text message
        res = make_telegram_request(
            bot_token,
            "sendMessage",
            data={
                "chat_id": chat_id,
                "text": text_content,
                "parse_mode": "HTML",
                "reply_markup": json.dumps(keyboard),
            }
        )
        if not res.get("ok"):
            plain_text = f"🌟 Content Preview for {platforms_str}\n\n📝 Caption:\n{caption[:3500]}\n\n👉 Review above and choose an action:"
            res = make_telegram_request(
                bot_token,
                "sendMessage",
                data={
                    "chat_id": chat_id,
                    "text": plain_text,
                    "reply_markup": json.dumps(keyboard),
                }
            )

    logger.info(f"Sent Telegram preview for campaign {campaign_id}: {res.get('ok')}")
    return {
        "status": "success" if res.get("ok") else "error",
        "response": res
    }


def answer_callback_query(callback_id: str, text: str = None) -> dict:
    """Answers a Telegram callback query to clear the loading spinner."""
    bot_token, _ = get_telegram_credentials()
    if not bot_token:
        return {"ok": False}
    data = {"callback_query_id": callback_id}
    if text:
        data["text"] = text
    return make_telegram_request(bot_token, "answerCallbackQuery", data=data)


def build_platform_keyboard(campaign_id: str, selected_platforms: list = None) -> dict:
    """Builds interactive inline keyboard with checkboxes for multi-platform selection."""
    if selected_platforms is None:
        selected_platforms = ["facebook", "instagram"]
    selected = set(str(p).lower().strip() for p in selected_platforms)

    fb_icon = "✅ 📘 Facebook" if "facebook" in selected else "⬜ 📘 Facebook"
    ig_icon = "✅ 📸 Instagram" if "instagram" in selected else "⬜ 📸 Instagram"
    li_icon = "✅ 💼 LinkedIn" if "linkedin" in selected else "⬜ 💼 LinkedIn"
    wa_icon = "✅ 💬 WhatsApp" if "whatsapp" in selected else "⬜ 💬 WhatsApp"

    count = len(selected)
    if count > 0:
        names = []
        if "facebook" in selected:
            names.append("Facebook")
        if "instagram" in selected:
            names.append("Instagram")
        if "linkedin" in selected:
            names.append("LinkedIn")
        if "whatsapp" in selected:
            names.append("WhatsApp")
        action_text = f"🚀 Post to {' + '.join(names)} ({count}) ➜" if count <= 2 else f"🚀 Post to {count} Platforms ➜"
    else:
        action_text = "⚠️ Select at least 1 Platform"

    return {
        "inline_keyboard": [
            [
                {"text": fb_icon, "callback_data": f"toggle_plat:facebook:{campaign_id}"},
                {"text": ig_icon, "callback_data": f"toggle_plat:instagram:{campaign_id}"},
            ],
            [
                {"text": li_icon, "callback_data": f"toggle_plat:linkedin:{campaign_id}"},
                {"text": wa_icon, "callback_data": f"toggle_plat:whatsapp:{campaign_id}"},
            ],
            [
                {"text": "✨ Select All", "callback_data": f"plat_select_all:{campaign_id}"},
                {"text": "🔄 Clear All", "callback_data": f"plat_clear_all:{campaign_id}"},
            ],
            [
                {"text": action_text, "callback_data": f"publish_multi:{campaign_id}"}
            ],
            [
                {"text": "❌ Cancel", "callback_data": f"cancel_post:{campaign_id}"}
            ]
        ]
    }


def send_platform_selection_menu(
    campaign_id: str,
    chat_id: str = None,
    selected_platforms: list = None,
    message_id: int = None
) -> dict:
    """
    Sends an action keyboard asking the user which social media platform(s) to publish to.
    Supports selecting multiple options (e.g. Facebook + Instagram together) with live checkboxes!
    """
    bot_token, default_chat_id = get_telegram_credentials()
    target_chat_id = chat_id or default_chat_id
    if not bot_token or not target_chat_id:
        return {"status": "error", "message": "Missing Telegram credentials."}

    if selected_platforms is None:
        selected_platforms = ["facebook", "instagram"]

    keyboard = build_platform_keyboard(campaign_id, selected_platforms)

    text = (
        "🚀 <b>Campaign Approved! Select Destination Platforms</b>\n\n"
        "Tap the buttons below to toggle destination platforms (you can select multiple):\n"
        "• 📘 <b>Facebook</b> + 📸 <b>Instagram</b> (Default)\n"
        "• 💼 <b>LinkedIn</b> | 💬 <b>WhatsApp</b>\n\n"
        "👉 <i>Choose platforms, then tap <b>'Post to Selected'</b> to broadcast!</i>"
    )

    if message_id:
        res = edit_message_text(target_chat_id, message_id, text, keyboard=keyboard)
        if res.get("ok"):
            return {"status": "success", "response": res}

    res = make_telegram_request(
        bot_token,
        "sendMessage",
        data={
            "chat_id": target_chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard),
        }
    )
    return {"status": "success" if res.get("ok") else "error", "response": res}


def send_password_request_prompt(chat_id: str, platform: str, campaign_id: str) -> dict:
    """Asks the user on Telegram for their social account password."""
    bot_token, _ = get_telegram_credentials()
    if not bot_token:
        return {"status": "error", "message": "Missing Telegram token."}

    text = (
        f"🔒 <b>{platform.capitalize()} Login Required</b>\n\n"
        f"The browser requires your {platform.capitalize()} password to publish this post.\n\n"
        f"👉 <i>Please reply to this message directly with your password (or <code>email:password</code>).</i>\n\n"
        f"The automation will safely paste it into the browser and proceed immediately."
    )

    res = make_telegram_request(
        bot_token,
        "sendMessage",
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
    )
    return {"status": "success" if res.get("ok") else "error", "response": res}


def delete_telegram_message(chat_id: str, message_id: int) -> dict:
    """Deletes a Telegram message (e.g. user password message for security)."""
    bot_token, _ = get_telegram_credentials()
    if not bot_token:
        return {"ok": False}
    return make_telegram_request(bot_token, "deleteMessage", data={"chat_id": chat_id, "message_id": message_id})


def send_text_message(chat_id: str, text: str, reply_markup: dict = None) -> dict:
    """Sends a plain or HTML formatted text message with optional inline keyboard."""
    bot_token, _ = get_telegram_credentials()
    if not bot_token:
        return {"ok": False}
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup is not None:
        data["reply_markup"] = json.dumps(reply_markup) if isinstance(reply_markup, dict) else reply_markup
    return make_telegram_request(bot_token, "sendMessage", data=data)


def edit_message_text(chat_id: str, message_id: int, text: str, keyboard: dict = None) -> dict:
    """Edits text and optionally reply markup of an existing text message."""
    bot_token, _ = get_telegram_credentials()
    if not bot_token or not chat_id or not message_id:
        return {"ok": False}
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
    }
    if keyboard is not None:
        data["reply_markup"] = json.dumps(keyboard) if isinstance(keyboard, dict) else keyboard
    return make_telegram_request(bot_token, "editMessageText", data=data)


def edit_message_caption(chat_id: str, message_id: int, caption: str, keyboard: dict = None) -> dict:
    """Edits caption and optionally reply markup of a photo/video message."""
    bot_token, _ = get_telegram_credentials()
    if not bot_token or not chat_id or not message_id:
        return {"ok": False}
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "caption": caption,
        "parse_mode": "HTML",
    }
    if keyboard is not None:
        data["reply_markup"] = json.dumps(keyboard) if isinstance(keyboard, dict) else keyboard
    return make_telegram_request(bot_token, "editMessageCaption", data=data)


def edit_message_reply_markup(chat_id: str, message_id: int, keyboard: dict = None) -> dict:
    """Updates or clears inline buttons on any message."""
    bot_token, _ = get_telegram_credentials()
    if not bot_token or not chat_id or not message_id:
        return {"ok": False}
    markup = keyboard or {"inline_keyboard": []}
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "reply_markup": json.dumps(markup) if isinstance(markup, dict) else markup,
    }
    return make_telegram_request(bot_token, "editMessageReplyMarkup", data=data)


def send_chrome_account_selection_menu(
    chat_id: str,
    content_type: str = "image",
    llm_provider: str = "chatgpt",
    product_id: str = "default",
    message_id: int = None
) -> dict:
    """
    Displays the interactive Google Chrome Account selector showing all 7 accounts
    with their mapped Google Email/Name, Facebook Account/Page, and Instagram Username.
    """
    bot_token, _ = get_telegram_credentials()
    if not bot_token:
        return {"status": "error", "message": "Missing Telegram credentials."}

    from db_campaigns import get_all_chrome_accounts
    accounts = get_all_chrome_accounts() or []

    text_parts = [
        "🌐 <b>Select Google Chrome Account & Profile</b>\n",
        "<i>Select which Google Chrome profile to run this campaign with. All 7 Google accounts are mapped with their Facebook and Instagram profiles:</i>\n\n"
    ]

    inline_kb = []
    for idx, acc in enumerate(accounts):
        email = acc.get("google_email") or acc.get("email") or "Unknown Email"
        name = acc.get("google_name") or acc.get("name") or "User"
        p_dir = acc.get("profile_dir") or acc.get("profile_directory") or f"Profile {idx}"
        fb = acc.get("facebook_name") or "Linked Facebook"
        ig = acc.get("instagram_username") or "Linked IG"
        acc_id = acc.get("id")

        text_parts.append(
            f"<b>{idx+1}. {name}</b> (<code>{email}</code>)\n"
            f"   📁 Chrome: <code>{p_dir}</code>\n"
            f"   📘 FB: <b>{fb}</b> | 📸 IG: <b>@{ig}</b>\n\n"
        )

        btn_label = f"👤 {idx+1}. {email[:24]} ({p_dir})"
        cb_data = f"flow:acc:{acc_id}:{content_type}:{llm_provider}:{product_id}"
        inline_kb.append([{"text": btn_label, "callback_data": cb_data}])

    back_cb = "root:outreach" if product_id == "outreach" else f"flow:llm:{llm_provider}:{content_type}"
    back_text = "🔙 Back to Outreach Menu" if product_id == "outreach" else "🔙 Back to Product Selection"
    inline_kb.append([
        {"text": back_text, "callback_data": back_cb},
        {"text": "📋 Main Menu", "callback_data": "root:main"}
    ])

    full_text = "".join(text_parts)
    keyboard = {"inline_keyboard": inline_kb}

    if message_id:
        res = edit_message_text(chat_id, message_id, full_text, keyboard=keyboard)
        if res.get("ok"):
            return {"status": "success", "response": res}

    res = make_telegram_request(
        bot_token,
        "sendMessage",
        data={
            "chat_id": chat_id,
            "text": full_text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard),
        }
    )
    return {"status": "success" if res.get("ok") else "error", "response": res}


def send_start_flow_menu(chat_id: str, message_id: int = None) -> dict:
    """
    Step 1: Asks user whether to generate Image or Video.
    """
    bot_token, _ = get_telegram_credentials()
    if not bot_token:
        return {"status": "error", "message": "Missing Telegram credentials."}

    text = (
        "🚀 <b>AI-Powered Social Media Automation</b>\n"
        "<i>Welcome! Automate high-converting marketing campaigns with human-like AI.</i>\n\n"
        "🎯 <b>Step 1 of 3: Select Content Type</b>\n"
        "What type of content would you like to generate today?"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🖼️ Generate Image", "callback_data": "flow:type:image"},
                {"text": "🎥 Generate Video", "callback_data": "flow:type:video"},
            ],
            [
                {"text": "ℹ️ How It Works", "callback_data": "info:how_it_works"},
                {"text": "📋 Active Products", "callback_data": "info:products"},
            ]
        ]
    }

    if message_id:
        res = edit_message_text(chat_id, message_id, text, keyboard=keyboard)
        if res.get("ok"):
            return {"status": "success", "response": res}

    res = make_telegram_request(
        bot_token,
        "sendMessage",
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard),
        }
    )
    return {"status": "success" if res.get("ok") else "error", "response": res}


def send_llm_selection_menu(chat_id: str, content_type: str = "image", message_id: int = None) -> dict:
    """
    Step 2 (for Image): Asks user which LLM model to use (Gemini, ChatGPT, Claude).
    """
    bot_token, _ = get_telegram_credentials()
    if not bot_token:
        return {"status": "error", "message": "Missing Telegram credentials."}

    text = (
        "🖼️ <b>Content Type:</b> Social Media Image Post\n\n"
        "🤖 <b>Step 2 of 3: Select AI / LLM Model</b>\n"
        "Which LLM model would you like to use for generating this post?"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "♊ Gemini (Google AI)", "callback_data": f"flow:llm:gemini:{content_type}"},
            ],
            [
                {"text": "🤖 ChatGPT (OpenAI)", "callback_data": f"flow:llm:chatgpt:{content_type}"},
            ],
            [
                {"text": "🎭 Claude (Anthropic)", "callback_data": f"flow:llm:claude:{content_type}"},
            ],
            [
                {"text": "🔙 Back to Content Type", "callback_data": "flow:start"},
            ]
        ]
    }

    if message_id:
        res = edit_message_text(chat_id, message_id, text, keyboard=keyboard)
        if res.get("ok"):
            return {"status": "success", "response": res}

    res = make_telegram_request(
        bot_token,
        "sendMessage",
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard),
        }
    )
    return {"status": "success" if res.get("ok") else "error", "response": res}


def send_product_selection_menu(
    chat_id: str,
    content_type: str,
    llm_provider: str,
    products: list,
    message_id: int = None
) -> dict:
    """
    Step 3: Asks user which product to generate for.
    Note: For video, Gemini is automatically selected.
    """
    bot_token, _ = get_telegram_credentials()
    if not bot_token:
        return {"status": "error", "message": "Missing Telegram credentials."}

    provider_label = {
        "gemini": "♊ Gemini",
        "chatgpt": "🤖 ChatGPT",
        "claude": "🎭 Claude"
    }.get(llm_provider.lower(), llm_provider.capitalize())

    if content_type == "video":
        text = (
            "🎥 <b>Content Type:</b> Promotional Video Reel (9:16)\n"
            f"⚡ <b>AI Engine:</b> {provider_label} <i>(Auto-selected for dynamic video generation)</i>\n\n"
            "📦 <b>Step 2 of 2: Select Target Product</b>\n"
            "Which product would you like to create a promotional video for?"
        )
    else:
        text = (
            "🖼️ <b>Content Type:</b> Social Media Image Post\n"
            f"🤖 <b>AI Engine:</b> {provider_label}\n\n"
            "📦 <b>Step 3 of 3: Select Target Product</b>\n"
            "Which product would you like to generate this post for?"
        )

    inline_keyboard = []
    if products:
        for p in products:
            p_id = p.get("id")
            p_name = p.get("name") or "Featured Product"
            p_cat = (p.get("category") or "").capitalize()
            btn_text = f"🚀 Generate: {p_name} ({p_cat})" if p_cat else f"🚀 Generate: {p_name}"
            inline_keyboard.append([{"text": btn_text, "callback_data": f"flow:run:{content_type}:{llm_provider}:{p_id}"}])
    else:
        inline_keyboard.append([{"text": "🚀 Generate Quick Post", "callback_data": f"flow:run:{content_type}:{llm_provider}:default"}])

    back_callback = "flow:start" if content_type == "video" else f"flow:type:{content_type}"
    back_label = "🔙 Change Content Type" if content_type == "video" else "🔙 Change AI Model"
    inline_keyboard.append([{"text": back_label, "callback_data": back_callback}])

    keyboard = {"inline_keyboard": inline_keyboard}

    if message_id:
        res = edit_message_text(chat_id, message_id, text, keyboard=keyboard)
        if res.get("ok"):
            return {"status": "success", "response": res}

    res = make_telegram_request(
        bot_token,
        "sendMessage",
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard),
        }
    )
    return {"status": "success" if res.get("ok") else "error", "response": res}


def send_root_choice_menu(chat_id: str, message_id: int = None) -> dict:
    """
    Root Question: Choose between Content Generation vs Growth Outreach vs Antigravity.
    """
    bot_token, _ = get_telegram_credentials()
    if not bot_token:
        return {"status": "error", "message": "Missing Telegram credentials."}

    text = (
        "⚡ <b>Manvxi AI & Growth Engine</b>\n"
        "<i>Welcome! Automate viral campaigns & grow your audience with human-like AI.</i>\n\n"
        "🎯 <b>What would you like to execute today?</b>"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🎨 1. Generate & Post Content", "callback_data": "root:content"}
            ],
            [
                {"text": "🖼️ 2. Posted Content Gallery (Share to All)", "callback_data": "post_page:0"}
            ],
            [
                {"text": "👥 3. Outreach (Follow & Friend Requests)", "callback_data": "root:outreach"}
            ],
            [
                {"text": "👨‍👩‍👧‍👦 4. Group Friends (Facebook & Instagram)", "callback_data": "root:friends_group"}
            ],
            [
                {"text": "💻 5. Remote Prompt / Antigravity Assistant", "callback_data": "root:antigravity"}
            ],
            [
                {"text": "⚡ 6. Live Tasks & Queue Dashboard", "callback_data": "root:queue"}
            ],
            [
                {"text": "ℹ️ How It Works", "callback_data": "info:how_it_works"},
                {"text": "📋 Active Products", "callback_data": "info:products"}
            ]
        ]
    }

    if message_id:
        res = edit_message_text(chat_id, message_id, text, keyboard=keyboard)
        if res.get("ok"):
            return {"status": "success", "response": res}

    res = make_telegram_request(
        bot_token,
        "sendMessage",
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard),
        }
    )
    return {"status": "success" if res.get("ok") else "error", "response": res}


def send_start_dashboard(chat_id: str, products: list = None) -> dict:
    """
    Entry point for /start command: initiates the root choice menu.
    """
    return send_root_choice_menu(chat_id)


def send_outreach_platform_menu(chat_id: str, message_id: int = None, account_id: str = None) -> dict:
    """Outreach Step 1: Platform Selection."""
    bot_token, _ = get_telegram_credentials()
    if not bot_token:
        return {"status": "error"}

    from db_campaigns import get_chrome_account
    acc = get_chrome_account(account_id) or {}
    acc_name = acc.get("google_name") or acc.get("name", "Shivam Mishra")
    acc_email = acc.get("google_email") or acc.get("email", "2003shivam1990@gmail.com")
    acc_pdir = acc.get("profile_dir") or acc.get("profile_directory", "Default")
    acc_fb = acc.get("facebook_name", "Techie Shivam (Loan Solutions)")
    acc_ig = acc.get("instagram_username", "loansolutions2026")

    text = (
        "👥 <b>Outreach & Growth Engine — Step 1: Platform</b>\n\n"
        f"👤 <b>Google Chrome Account:</b> {acc_name}\n"
        f"📧 <b>Google Email:</b> <code>{acc_email}</code>\n"
        f"📁 <b>Profile Directory:</b> <code>{acc_pdir}</code>\n"
        f"📘 <b>Facebook Page:</b> {acc_fb}\n"
        f"📸 <b>Instagram Account:</b> @{acc_ig}\n\n"
        "Which platform would you like to send outreach requests on?"
    )

    keyboard = {
        "inline_keyboard": [
            [{"text": f"👤 Profile: {acc_name} ({acc_pdir}) — Change", "callback_data": "outreach:account_select"}],
            [{"text": "🖼️ View Posted Images & Videos (Share to All)", "callback_data": "post_page:0"}],
            [{"text": "👨‍👩‍👧‍👦 Group All Friends (Facebook & Instagram)", "callback_data": "root:friends_group"}],
            [{"text": "🤝 Accept Pending Friend Requests (FB)", "callback_data": "outreach:fb_accept_menu"}],
            [{"text": "📉 Prune / Unfollow Accounts (Instagram)", "callback_data": "outreach:ig_unfollow_menu"}],
            [{"text": "⚡ Both Simultaneously (FB + IG)", "callback_data": "outreach:plat:both"}],
            [
                {"text": "📘 Facebook (Send Requests)", "callback_data": "outreach:plat:facebook"},
                {"text": "📸 Instagram (Follows)", "callback_data": "outreach:plat:instagram"}
            ],
            [{"text": "🔙 Back to Main Menu", "callback_data": "root:main"}]
        ]
    }

    if message_id:
        res = edit_message_text(chat_id, message_id, text, keyboard=keyboard)
        if res.get("ok"):
            return {"status": "success", "response": res}

    res = make_telegram_request(
        bot_token,
        "sendMessage",
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard),
        }
    )
    return {"status": "success" if res.get("ok") else "error", "response": res}


def send_friends_group_menu(chat_id: str, message_id: int = None) -> dict:
    """Outreach: Social Friends Group Creator Menu."""
    bot_token, _ = get_telegram_credentials()
    if not bot_token:
        return {"status": "error"}

    text = (
        "👨‍👩‍👧‍👦 <b>Social Friends Group Creator</b>\n\n"
        "Assemble your friends on Facebook and Instagram into groups and group chats with automated member invitations.\n\n"
        "🎯 <b>Select group type to create:</b>"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "📘 FB Community Group", "callback_data": "grp:type:facebook:community_group"},
                {"text": "💬 FB Messenger Chat", "callback_data": "grp:type:facebook:messenger_chat"}
            ],
            [
                {"text": "📸 Instagram Direct Group (Batch 30)", "callback_data": "grp:type:instagram:ig_direct_group"}
            ],
            [
                {"text": "⚡ Dual Platform (All 3 Groups)", "callback_data": "grp:type:both:all"}
            ],
            [
                {"text": "🔙 Back to Outreach", "callback_data": "root:outreach"},
                {"text": "📋 Main Menu", "callback_data": "root:main"}
            ]
        ]
    }

    if message_id:
        res = edit_message_text(chat_id, message_id, text, keyboard=keyboard)
        if res.get("ok"):
            return {"status": "success", "response": res}

    res = make_telegram_request(
        bot_token,
        "sendMessage",
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard),
        }
    )
    return {"status": "success" if res.get("ok") else "error", "response": res}


def send_instagram_steps_menu(chat_id: str, message_id: int = None) -> dict:
    """Outreach: Dedicated Instagram Growth & Follow Steps Menu."""
    bot_token, _ = get_telegram_credentials()
    if not bot_token:
        return {"status": "error"}

    text = (
        "📸 <b>Instagram Growth & Follow Engine — Guided Steps</b>\n"
        "<i>Connected to your authenticated Chrome browser on port 9222</i>\n\n"
        "👇 <b>Select an Instagram Step below:</b>\n\n"
        "🎯 <b>Step 1: Enter User ID -> Save Followers & Follow:</b>\n"
        "Input any Instagram User ID/username. Manvix AI navigates inside the ID, extracts & saves their exact follower count to the database, and dispatches the follow request!\n\n"
        "📊 <b>Step 2: View Saved Follows & Lead Counters:</b>\n"
        "Inspect all saved target profiles, extracted follower numbers, and cumulative follow metrics.\n\n"
        "📍 <b>Step 3: Auto-Follow by Location / City:</b>\n"
        "Discover & follow real local people in Lucknow, Delhi, Mumbai, etc. (strictly filters out channels, broadcast channels, & news pages) with human safety pacing.\n\n"
        "📉 <b>Step 4: Prune / Unfollow Accounts:</b>\n"
        "Clean inactive followings and manage your follow ratio safely.\n\n"
        "💡 <i>Quick Tip: You can also type <code>/follow @username</code> directly in chat!</i>"
    )

    keyboard = {
        "inline_keyboard": [
            [{"text": "🎯 Step 1: Follow User ID & Save Followers", "callback_data": "outreach:ig_mode:username"}],
            [{"text": "📊 Step 2: View Saved Follows & Stats", "callback_data": "outreach:ig_follow_stats"}],
            [{"text": "📍 Step 3: Auto-Follow by Location / City", "callback_data": "outreach:ig_mode:location"}],
            [{"text": "📉 Step 4: Prune / Unfollow Accounts", "callback_data": "outreach:ig_unfollow_menu"}],
            [{"text": "🔙 Back to Outreach Menu", "callback_data": "root:outreach"}]
        ]
    }

    if message_id:
        res = edit_message_text(chat_id, message_id, text, keyboard=keyboard)
        if res.get("ok"):
            return {"status": "success", "response": res}

    res = make_telegram_request(
        bot_token,
        "sendMessage",
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard),
        }
    )
    return {"status": "success" if res.get("ok") else "error", "response": res}


def send_instagram_leads_stats_menu(chat_id: str, message_id: int = None) -> dict:
    """Outreach: Displays cumulative statistics of all Instagram target accounts, follower counts, and follow actions."""
    bot_token, _ = get_telegram_credentials()
    if not bot_token:
        return {"status": "error"}

    try:
        from db_campaigns import get_instagram_leads_stats
        data = get_instagram_leads_stats()
    except Exception as e:
        logger.warning(f"Error fetching leads stats: {e}")
        data = {}

    stats = data.get("stats", {})
    recent = data.get("recent_leads", [])

    lines = []
    for lead in recent[:8]:
        u = lead.get("username", "")
        f_txt = lead.get("followers_text", "0")
        st = lead.get("follow_status", "")
        icon = "✅" if st == "success" else ("📨" if st == "requested" else ("ℹ️" if st == "already_following" else "🛡️"))
        lines.append(f"• {icon} <b>@{u}</b>: <code>{f_txt}</code> followers ({st})")

    leads_text = "\n".join(lines) if lines else "<i>No leads recorded yet. Use /follow to start!</i>"

    text = (
        "📊 <b>MANVIX AI — INSTAGRAM LEADS & FOLLOWER TRACKER</b>\n\n"
        f"👥 <b>Total Target Profiles Scanned:</b> <code>{stats.get('total_scanned', 0)}</code>\n"
        f"🏆 <b>Total Follows Dispatched:</b> <code>{stats.get('total_followed', 0)}</code>\n"
        f"📨 <b>Total Private Requests Sent:</b> <code>{stats.get('total_requested', 0)}</code>\n"
        f"👥 <b>Already Following Profiles:</b> <code>{stats.get('total_already_following', 0)}</code>\n\n"
        f"📋 <b>Recent Target Accounts (with Extracted Followers):</b>\n"
        f"{leads_text}\n\n"
        "💾 <i>Data is persisted in SQLite (<code>instagram_target_leads</code>) & JSON tracker.</i>"
    )

    keyboard = {
        "inline_keyboard": [
            [{"text": "🎯 Follow New User ID", "callback_data": "outreach:ig_mode:username"}],
            [{"text": "📸 Instagram Steps Menu", "callback_data": "outreach:ig_steps"}],
            [{"text": "👥 Main Outreach Menu", "callback_data": "root:outreach"}]
        ]
    }

    if message_id:
        res = edit_message_text(chat_id, message_id, text, keyboard=keyboard)
        if res.get("ok"):
            return {"status": "success", "response": res}

    res = make_telegram_request(
        bot_token,
        "sendMessage",
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard),
        }
    )
def send_posted_content_gallery(
    chat_id: str,
    page_index: int = 0,
    platform: str = None,
    message_id: int = None
) -> dict:
    """
    Renders an interactive Post Gallery showing all published Instagram & Facebook images and videos.
    Users can inspect post details, see who it was shared with, and click [🚀 Share to ALL Friends]
    or share selectively to Instagram / Facebook friends.
    """
    bot_token, _ = get_telegram_credentials()
    if not bot_token:
        return {"status": "error"}

    from db_campaigns import get_all_published_posts
    posts = get_all_published_posts(platform=platform, limit=30)

    if not posts:
        text = (
            "🖼️ <b>Manvix AI — Posted Content Gallery</b>\n\n"
            "⚠️ <i>No posted images or videos found yet in the system.</i>\n\n"
            "Use /generate or publish a campaign to populate your gallery, then return here to share posts to all your friends!"
        )
        keyboard = {
            "inline_keyboard": [
                [{"text": "⚡ Generate New Content", "callback_data": "root:generate"}],
                [{"text": "🔙 Back to Outreach Menu", "callback_data": "root:outreach"}]
            ]
        }
        if message_id:
            edit_message_text(chat_id, message_id, text, keyboard=keyboard)
        else:
            send_text_message(chat_id, text, reply_markup=keyboard)
        return {"status": "empty"}

    page_index = max(0, min(page_index, len(posts) - 1))
    camp = posts[page_index]
    camp_id = camp["id"]
    media_path = camp.get("media_path") or ""
    content_type = camp.get("content_type") or "image"
    plats = [p.capitalize() for p in camp.get("platforms", ["Facebook", "Instagram"])]
    caption = camp.get("caption") or ""
    p_name = camp.get("product_name") or "Loan Solutions"
    total_shares = camp.get("total_shares") or 0
    updated_at = camp.get("updated_at") or "Recently"

    import html
    safe_cap = html.escape(caption.strip())
    cap_preview = (safe_cap[:220] + "...") if len(safe_cap) > 220 else safe_cap

    text = (
        f"🖼️ <b>MANVIX AI — POSTED CONTENT VIEWER ({page_index + 1}/{len(posts)})</b>\n\n"
        f"🏷️ <b>Product:</b> {p_name}\n"
        f"📱 <b>Published On:</b> {' + '.join(plats)}\n"
        f"📅 <b>Posted Date:</b> <code>{updated_at}</code>\n"
        f"👥 <b>Friends Shared With:</b> <code>{total_shares} friends</code>\n\n"
        f"📝 <b>Post Caption / Copy:</b>\n"
        f"<i>\"{cap_preview}\"</i>\n\n"
        f"👇 <b>Select an action to share this post to your friends:</b>"
    )

    prev_idx = (page_index - 1) % len(posts)
    next_idx = (page_index + 1) % len(posts)

    keyboard = {
        "inline_keyboard": [
            [{"text": "🚀 Share to ALL Friends (Instagram + Facebook)", "callback_data": f"post_shr:all:{camp_id}"}],
            [
                {"text": "📸 Share to Instagram Friends", "callback_data": f"post_shr:ig:{camp_id}"},
                {"text": "📘 Share to Facebook Friends", "callback_data": f"post_shr:fb:{camp_id}"}
            ],
            [
                {"text": "⬅️ Prev", "callback_data": f"post_page:{prev_idx}"},
                {"text": f"📍 {page_index + 1} / {len(posts)}", "callback_data": f"post_page:{page_index}"},
                {"text": "Next ➡️", "callback_data": f"post_page:{next_idx}"}
            ],
            [
                {"text": "📊 Overall Post Share Stats", "callback_data": "post_shr:stats"},
                {"text": "🔙 Back to Outreach Menu", "callback_data": "root:outreach"}
            ]
        ]
    }

    # Send media (photo or video) if file exists
    if media_path and os.path.exists(media_path):
        fname = os.path.basename(media_path)
        with open(media_path, "rb") as f:
            file_bytes = f.read()

        if content_type == "video" or fname.lower().endswith((".mp4", ".mov")):
            res = make_telegram_request(
                bot_token,
                "sendVideo",
                data={
                    "chat_id": chat_id,
                    "caption": text[:1024],
                    "parse_mode": "HTML",
                    "reply_markup": json.dumps(keyboard),
                },
                files={"video": (fname, file_bytes, "video/mp4")}
            )
            return {"status": "success", "response": res}
        else:
            res = make_telegram_request(
                bot_token,
                "sendPhoto",
                data={
                    "chat_id": chat_id,
                    "caption": text[:1024],
                    "parse_mode": "HTML",
                    "reply_markup": json.dumps(keyboard),
                },
                files={"photo": (fname, file_bytes, "image/png")}
            )
            return {"status": "success", "response": res}

    # Fallback to text message
    if message_id:
        res = edit_message_text(chat_id, message_id, text, keyboard=keyboard)
        if res.get("ok"):
            return {"status": "success", "response": res}

    res = make_telegram_request(
        bot_token,
        "sendMessage",
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard),
        }
    )
    return {"status": "success" if res.get("ok") else "error", "response": res}


def send_post_shares_overall_stats_menu(chat_id: str, message_id: int = None) -> dict:
    """Displays cumulative friend sharing statistics across all published posts."""
    bot_token, _ = get_telegram_credentials()
    if not bot_token:
        return {"status": "error"}

    from db_campaigns import get_post_shares_stats
    stats = get_post_shares_stats()
    recent = stats.get("recent_shares", [])

    lines = []
    for s in recent[:8]:
        rec = s.get("recipient_name", "Friend")
        plat = s.get("platform", "ig").capitalize()
        dt = s.get("created_at", "")
        lines.append(f"• 📤 <b>{rec}</b> via {plat} (<code>{dt}</code>)")

    recent_text = "\n".join(lines) if lines else "<i>No shares recorded yet. Share a post to get started!</i>"

    text = (
        "📊 <b>MANVIX AI — POST SHARING TO FRIENDS DASHBOARD</b>\n\n"
        f"🚀 <b>Total Friend Shares Dispatched:</b> <code>{stats.get('total_shares', 0)}</code>\n"
        f"📸 <b>Instagram Direct Shares:</b> <code>{stats.get('instagram_shares', 0)}</code>\n"
        f"📘 <b>Facebook Messenger Shares:</b> <code>{stats.get('facebook_shares', 0)}</code>\n\n"
        f"📋 <b>Recent Friend Recipients:</b>\n"
        f"{recent_text}\n\n"
        "💾 <i>Logged in <code>post_shares_log</code> database table with human safety timestamps.</i>"
    )

    keyboard = {
        "inline_keyboard": [
            [{"text": "🖼️ View Posted Images & Videos", "callback_data": "post_page:0"}],
            [{"text": "👥 Back to Outreach Menu", "callback_data": "root:outreach"}]
        ]
    }

    if message_id:
        res = edit_message_text(chat_id, message_id, text, keyboard=keyboard)
        if res.get("ok"):
            return {"status": "success", "response": res}

    res = make_telegram_request(
        bot_token,
        "sendMessage",
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard),
        }
    )
    return {"status": "success" if res.get("ok") else "error", "response": res}




def send_instagram_unfollow_menu(chat_id: str, message_id: int = None) -> dict:
    """Outreach: Instagram Following Pruning & Unfollow Menu."""
    bot_token, _ = get_telegram_credentials()
    if not bot_token:
        return {"status": "error"}

    following_info = None
    try:
        from social.instagram_unfollow import get_instagram_following_list
        following_info = get_instagram_following_list(max_count=15)
    except Exception as e:
        logger.warning(f"Error fetching Instagram following list: {e}")

    total_cnt = following_info.get("total_following", 0) if following_info else 0
    username = following_info.get("username", "loansolutions2026") if following_info else "loansolutions2026"
    accounts = following_info.get("accounts", []) if following_info else []

    sample_lines = ""
    if accounts:
        sample_lines = "\n\n📋 <b>Currently Followed Accounts:</b>\n"
        for acc in accounts[:5]:
            sample_lines += f"• <b>@{acc['username']}</b>\n"
        if len(accounts) > 5:
            sample_lines += f"<i>...and {total_cnt - 5} more</i>\n"

    text = (
        "📉 <b>Instagram Unfollow & Pruning Center</b>\n"
        "<i>Connected to your authenticated Chrome browser on port 9222</i>\n\n"
        f"📊 <b>Total Following:</b> <code>{total_cnt} accounts</code>\n"
        f"👤 <b>Active Account:</b> @{username}"
        f"{sample_lines}\n"
        "👇 <b>Select an action to execute:</b>"
    )

    keyboard = {
        "inline_keyboard": [
            [{"text": f"⚡ Unfollow All ({total_cnt})", "callback_data": "ig_unf:run:all"}],
            [
                {"text": "5️⃣ Unfollow 5", "callback_data": "ig_unf:run:5"},
                {"text": "🔟 Unfollow 10", "callback_data": "ig_unf:run:10"}
            ],
            [
                {"text": "🔄 Refresh List", "callback_data": "outreach:ig_unfollow_menu"},
                {"text": "🔙 Back to Outreach", "callback_data": "root:outreach"}
            ]
        ]
    }

    if message_id:
        res = edit_message_text(chat_id, message_id, text, keyboard=keyboard)
        if res.get("ok"):
            return {"status": "success", "response": res}

    res = make_telegram_request(
        bot_token,
        "sendMessage",
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard),
        }
    )
    return {"status": "success" if res.get("ok") else "error", "response": res}


def send_facebook_accept_menu(chat_id: str, message_id: int = None) -> dict:
    """Outreach: Facebook Friend Requests Auto-Accept Menu."""
    bot_token, _ = get_telegram_credentials()
    if not bot_token:
        return {"status": "error"}

    # Scan pending requests
    pending_info = None
    try:
        from social.facebook_accept import get_pending_friend_requests
        pending_info = get_pending_friend_requests(max_scrolls=1)
    except Exception as e:
        logger.warning(f"Error scanning pending requests for Telegram: {e}")

    count = pending_info.get("count", 0) if pending_info else 0
    title_badge = pending_info.get("title_badge", "") if pending_info else ""
    requests = pending_info.get("requests", []) if pending_info else []

    count_str = f"{count}"
    if title_badge and title_badge != str(count):
        count_str += f" ({title_badge})"

    sample_lines = ""
    if requests:
        sample_lines = "\n\n📋 <b>Pending Requesters:</b>\n"
        for r in requests[:4]:
            mutual = f" • <i>{r['mutual_friends']}</i>" if r.get("mutual_friends") else ""
            sample_lines += f"• <b>{r['name']}</b>{mutual}\n"
        if len(requests) > 4:
            sample_lines += f"<i>...and {len(requests) - 4} more waiting</i>\n"

    text = (
        "🤝 <b>Facebook Friend Requests Center</b>\n"
        "<i>Connected to your authenticated Chrome browser on port 9222</i>\n\n"
        f"📊 <b>Pending Requests:</b> <code>{count_str}</code>"
        f"{sample_lines}\n"
        "👇 <b>Select an action to execute:</b>"
    )

    keyboard = {
        "inline_keyboard": [
            [{"text": f"⚡ Accept All ({count}) + Auto-Like 👍", "callback_data": "fb_acc:run:all:like"}],
            [{"text": f"⚡ Accept All ({count}) (No Like)", "callback_data": "fb_acc:run:all:nolike"}],
            [
                {"text": "🔟 Accept 10 + Like", "callback_data": "fb_acc:run:10:like"},
                {"text": "🔄 Rescan Requests", "callback_data": "outreach:fb_accept_menu"}
            ],
            [{"text": "🔙 Back to Outreach Menu", "callback_data": "root:outreach"}]
        ]
    }

    if message_id:
        res = edit_message_text(chat_id, message_id, text, keyboard=keyboard)
        if res.get("ok"):
            return {"status": "success", "response": res}

    res = make_telegram_request(
        bot_token,
        "sendMessage",
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard),
        }
    )
    return {"status": "success" if res.get("ok") else "error", "response": res}


def send_outreach_strategy_menu(chat_id: str, platform: str, message_id: int = None) -> dict:
    """Outreach Step 2: Discovery Strategy Selection."""
    bot_token, _ = get_telegram_credentials()
    if not bot_token:
        return {"status": "error"}

    plat_label = {
        "both": "⚡ Dual (Facebook + Instagram)",
        "facebook": "📘 Facebook",
        "instagram": "📸 Instagram"
    }.get(platform, platform.capitalize())

    text = (
        f"👥 <b>Platform:</b> {plat_label}\n\n"
        "🎯 <b>Outreach Step 2 of 3: Choose Strategy</b>\n\n"
        "How would you like to discover accounts to send friend requests / follows to?\n\n"
        "• 🌟 <b>Algorithmic Suggestions:</b> Targets Facebook's 'People You May Know' & Instagram's 'Suggested for You' (highest acceptance rate).\n"
        "• 🎲 <b>Random Discovery:</b> Organic diversified exploration from explore feeds & shuffled suggestions (natural browsing footprint).\n"
        "• 📍 <b>Target Specific Location:</b> Finds & follows real people in your target city (auto-filters out channels, broadcast channels & media pages)."
    )

    keyboard = {
        "inline_keyboard": [
            [{"text": "🌟 Algorithmic Suggestions (Recommended)", "callback_data": f"outreach:strat:{platform}:suggestions"}],
            [{"text": "🎲 Random Discovery (Explore Grid)", "callback_data": f"outreach:strat:{platform}:random"}],
            [{"text": "📍 Target Specific City / Location", "callback_data": f"outreach:strat:{platform}:location"}],
            [{"text": "🔙 Change Platform", "callback_data": "root:outreach"}]
        ]
    }

    if message_id:
        res = edit_message_text(chat_id, message_id, text, keyboard=keyboard)
        if res.get("ok"):
            return {"status": "success", "response": res}

    res = make_telegram_request(
        bot_token,
        "sendMessage",
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard),
        }
    )
    return {"status": "success" if res.get("ok") else "error", "response": res}


def send_outreach_location_menu(chat_id: str, platform: str, message_id: int = None) -> dict:
    """Outreach Step 2 (Optional): Target Location Selection."""
    bot_token, _ = get_telegram_credentials()
    if not bot_token:
        return {"status": "error"}

    plat_label = {
        "both": "⚡ Dual (FB + IG)",
        "facebook": "📘 Facebook",
        "instagram": "📸 Instagram"
    }.get(platform, platform.capitalize())

    text = (
        f"👥 <b>Platform:</b> {plat_label}\n\n"
        "📍 <b>Select Target Location</b>\n"
        "Finds & follows <b>real local residents</b> in your target city (auto-skips channels, broadcast channels, news, & media pages).\n\n"
        "Select your target location from presets or type any city name directly in this chat:"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "📍 Lucknow", "callback_data": f"outreach:loc:{platform}:Lucknow"},
                {"text": "📍 New Delhi", "callback_data": f"outreach:loc:{platform}:New Delhi"}
            ],
            [
                {"text": "📍 Mumbai", "callback_data": f"outreach:loc:{platform}:Mumbai"},
                {"text": "📍 Bangalore", "callback_data": f"outreach:loc:{platform}:Bangalore"}
            ],
            [
                {"text": "📍 New York", "callback_data": f"outreach:loc:{platform}:New York"},
                {"text": "📍 London", "callback_data": f"outreach:loc:{platform}:London"}
            ],
            [
                {"text": "📍 Dubai", "callback_data": f"outreach:loc:{platform}:Dubai"},
                {"text": "✏️ Type Custom City Name", "callback_data": f"outreach:loc_custom:{platform}"}
            ],
            [{"text": "🔙 Change Strategy", "callback_data": f"outreach:plat:{platform}"}]
        ]
    }

    if message_id:
        res = edit_message_text(chat_id, message_id, text, keyboard=keyboard)
        if res.get("ok"):
            return {"status": "success", "response": res}

    res = make_telegram_request(
        bot_token,
        "sendMessage",
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard),
        }
    )
    return {"status": "success" if res.get("ok") else "error", "response": res}


def send_outreach_count_menu(chat_id: str, platform: str, location: str, mode: str = "location", message_id: int = None) -> dict:
    """Outreach Step 3: Request Count Selection."""
    bot_token, _ = get_telegram_credentials()
    if not bot_token:
        return {"status": "error"}

    plat_label = {
        "both": "⚡ Dual (Facebook + Instagram)",
        "facebook": "📘 Facebook Friends",
        "instagram": "📸 Instagram Follows"
    }.get(platform, platform.capitalize())

    strat_label = {
        "suggestions": "🌟 Algorithmic Suggestions",
        "random": "🎲 Random Discovery",
        "location": f"📍 Location: {location}"
    }.get(mode, f"📍 Location: {location}")

    text = (
        f"👥 <b>Platform:</b> {plat_label}\n"
        f"🎯 <b>Strategy:</b> {strat_label}\n\n"
        "🔢 <b>Outreach Step 3 of 3: Request Count</b>\n"
        "Select a preset below (up to 1,000) or tap <b>✏️ Enter Custom Number</b>:\n"
        "<i>(Note: A 2-minute safety cooldown automatically pauses after every 250 requests)</i>"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "10 Requests (Quick)", "callback_data": f"outreach:run:{platform}:{mode}:{location}:10"},
                {"text": "25 Requests", "callback_data": f"outreach:run:{platform}:{mode}:{location}:25"}
            ],
            [
                {"text": "50 Requests", "callback_data": f"outreach:run:{platform}:{mode}:{location}:50"},
                {"text": "100 Requests", "callback_data": f"outreach:run:{platform}:{mode}:{location}:100"}
            ],
            [
                {"text": "250 Requests", "callback_data": f"outreach:run:{platform}:{mode}:{location}:250"},
                {"text": "500 Requests (2 Breaks)", "callback_data": f"outreach:run:{platform}:{mode}:{location}:500"}
            ],
            [
                {"text": "🚀 1,000 Requests (Max)", "callback_data": f"outreach:run:{platform}:{mode}:{location}:1000"}
            ],
            [
                {"text": "✏️ Enter Custom Number (1-1000)", "callback_data": f"outreach:count_custom:{platform}:{mode}:{location}"}
            ],
            [{"text": "🔙 Change Strategy", "callback_data": f"outreach:plat:{platform}"}]
        ]
    }

    if message_id:
        res = edit_message_text(chat_id, message_id, text, keyboard=keyboard)
        if res.get("ok"):
            return {"status": "success", "response": res}

    res = make_telegram_request(
        bot_token,
        "sendMessage",
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard),
        }
    )
    return {"status": "success" if res.get("ok") else "error", "response": res}


def download_telegram_file(token: str, file_id: str, dest_path: str) -> bool:
    """Downloads a file from Telegram by file_id using getFile API."""
    try:
        res = make_telegram_request(token, "getFile", data={"file_id": file_id})
        if res.get("ok") and "result" in res:
            file_rel_path = res["result"].get("file_path")
            if not file_rel_path:
                return False
            download_url = f"https://api.telegram.org/file/bot{token}/{file_rel_path}"
            req = urllib.request.Request(download_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = resp.read()
            p = Path(dest_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "wb") as f:
                f.write(data)
            logger.info(f"Downloaded Telegram file {file_id} ({len(data)} bytes) -> {dest_path}")
            return True
    except Exception as e:
        logger.error(f"Failed to download file from Telegram: {e}")
    return False


def send_antigravity_menu(chat_id: str, message_id: int = None, selected_mode: str = "antigravity_chat") -> dict:
    """Displays the Antigravity & Remote Laptop Control Menu."""
    bot_token, _ = get_telegram_credentials()
    if not bot_token:
        return {"status": "error"}

    mode_label = {
        "antigravity_chat": "⚡ Antigravity IDE (Chat Prompt)",
        "antigravity_inline": "💻 Antigravity IDE (Inline Ctrl+I)",
        "active_window": "🖥️ Active Laptop Window",
        "notepad": "📝 Notepad (Testing)",
    }.get(selected_mode, selected_mode)

    text = (
        "💻 <b>Antigravity & Laptop Remote Prompt Control</b>\n\n"
        "Control your laptop and running software directly from Telegram!\n\n"
        "💡 <b>How it works:</b>\n"
        "1️⃣ Type or paste any prompt/instruction directly in this chat.\n"
        "2️⃣ The bot will paste it into the running prompt of your laptop software and submit it.\n"
        "3️⃣ You will receive an instant <b>Task Number</b> and a <b>Task Complete Message</b>!\n\n"
        f"🎯 <b>Active Target:</b> <code>{mode_label}</code>\n\n"
        "👇 <i>Type your prompt now, or switch target mode below:</i>"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "⚡ Antigravity (Chat Prompt)", "callback_data": "agy:setmode:antigravity_chat"},
                {"text": "💻 Antigravity (Inline Ctrl+I)", "callback_data": "agy:setmode:antigravity_inline"}
            ],
            [
                {"text": "🖥️ Active Foreground Window", "callback_data": "agy:setmode:active_window"},
                {"text": "📋 Running Windows on Laptop", "callback_data": "agy:windows"}
            ],
            [
                {"text": "🔙 Back to Main Menu", "callback_data": "root:main"}
            ]
        ]
    }

    if message_id:
        res = edit_message_text(chat_id, message_id, text, keyboard=keyboard)
        if res.get("ok"):
            return {"status": "success", "response": res}

    res = make_telegram_request(
        bot_token,
        "sendMessage",
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard),
        }
    )
    return {"status": "success" if res.get("ok") else "error", "response": res}


def send_antigravity_running_windows_menu(chat_id: str, message_id: int = None) -> dict:
    """Lists currently open desktop windows on the laptop."""
    bot_token, _ = get_telegram_credentials()
    if not bot_token:
        return {"status": "error"}

    try:
        from remote.antigravity_controller import get_running_windows
        wins = get_running_windows()
    except Exception:
        wins = []

    text = "📋 <b>Currently Visible Software Windows on Laptop:</b>\n\n"
    if wins:
        for idx, w in enumerate(wins[:10], 1):
            text += f"<b>{idx}.</b> <code>{w['title'][:55]}</code>\n"
    else:
        text += "<i>No visible desktop windows detected or laptop is locked.</i>\n"

    text += "\n💡 <i>Prompts will be injected into Antigravity IDE by default.</i>"

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "⚡ Prompt Antigravity IDE", "callback_data": "agy:setmode:antigravity_chat"},
                {"text": "🔄 Refresh List", "callback_data": "agy:windows"}
            ],
            [
                {"text": "🔙 Back to Remote Menu", "callback_data": "root:antigravity"}
            ]
        ]
    }

    if message_id:
        res = edit_message_text(chat_id, message_id, text, keyboard=keyboard)
        if res.get("ok"):
            return {"status": "success", "response": res}

    res = make_telegram_request(
        bot_token,
        "sendMessage",
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard),
        }
    )
    return {"status": "success" if res.get("ok") else "error", "response": res}


def send_task_completion_message(chat_id: str, task_id: str, prompt: str, window_title: str, success: bool = True, details: str = "") -> dict:
    """Sends the official Task Number Complete Message to the user."""
    bot_token, _ = get_telegram_credentials()
    if not bot_token:
        return {"status": "error"}

    time_str = time.strftime("%H:%M:%S")
    prompt_snip = (prompt[:140] + "...") if len(prompt) > 140 else prompt

    if success:
        text = (
            f"✅ <b>Task #{task_id} Completed!</b>\n\n"
            f"🖥️ <b>Software:</b> <code>{window_title}</code>\n"
            f"📝 <b>Injected Prompt:</b>\n<i>\"{prompt_snip}\"</i>\n\n"
            f"🕒 <b>Submitted At:</b> {time_str}\n"
            f"⚡ <b>Action:</b> Pasted & submitted into running prompt successfully.\n\n"
            f"💻 <i>Your laptop is running this task now. Send another prompt anytime or type /start for menu!</i>"
        )
    else:
        text = (
            f"⚠️ <b>Task #{task_id} Notice</b>\n\n"
            f"🖥️ <b>Target:</b> <code>{window_title}</code>\n"
            f"📝 <b>Prompt:</b> <i>\"{prompt_snip}\"</i>\n\n"
            f"❌ <b>Issue:</b> {details or 'Could not complete injection.'}\n\n"
            f"💡 <i>Please verify that Antigravity IDE is open on your laptop.</i>"
        )

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "💻 Send Another Prompt", "callback_data": "root:antigravity"},
                {"text": "📋 Main Menu", "callback_data": "root:main"}
            ]
        ]
    }

    res = make_telegram_request(
        bot_token,
        "sendMessage",
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard),
        }
    )
    return {"status": "success" if res.get("ok") else "error", "response": res}


def send_queue_dashboard(chat_id: str, message_id: int = None) -> dict:
    """Renders real-time multitasking status, active workers, and queued tasks."""
    bot_token, _ = get_telegram_credentials()
    if not bot_token:
        return {"status": "error"}

    try:
        from core.task_orchestrator import orchestrator
        snapshot = orchestrator.get_snapshot()
    except Exception as e:
        snapshot = {"active_workers_count": 0, "max_worker_slots": 6, "queued_tasks_count": 0, "active_tasks": [], "queued_tasks": []}

    active_cnt = snapshot.get("active_workers_count", 0)
    max_slots = snapshot.get("max_worker_slots", 6)
    queued_cnt = snapshot.get("queued_tasks_count", 0)
    active_tasks = snapshot.get("active_tasks", [])
    queued_tasks = snapshot.get("queued_tasks", [])

    text_parts = [
        "⚡ <b>MANVXI AI MULTITASKING & QUEUE DASHBOARD</b>\n"
        f"<i>Capacity: {active_cnt}/{max_slots} Active Worker Slots</i>\n"
        "────────────────────────────────────\n"
    ]

    if active_tasks:
        text_parts.append(f"🟢 <b>ACTIVE WORKERS ({len(active_tasks)} Running Simultaneously):</b>\n")
        for idx, t in enumerate(active_tasks, 1):
            plat_icon = {"facebook": "📘", "instagram": "📸", "linkedin": "💼", "whatsapp": "💬"}.get(t.get("platform", ""), "⚡")
            curr_act = t.get("current_activity") or "Working in background..."
            recent_acts = t.get("recent_activities") or []
            skipped_cnt = t.get("skipped_count", 0)

            worker_block = (
                f"{idx}. {plat_icon} <b>{t.get('name', 'Task')}</b>\n"
                f"   • <b>Lock:</b> <code>{t.get('lock_key')}</code> | <b>Elapsed:</b> {t.get('elapsed_seconds', 0)}s\n"
                f"   • <b>Progress:</b> <code>{t.get('progress', 'In progress')}</code>\n"
            )
            if skipped_cnt > 0:
                worker_block += f"   • 🛡️ <b>Skipped Channels/Pages:</b> {skipped_cnt}\n"
            worker_block += f"   • ⚡ <b>Current Activity:</b> <code>{curr_act}</code>\n"
            if recent_acts:
                worker_block += f"   • 📜 <b>Recent:</b> <i>{recent_acts[-1]}</i>\n"
            text_parts.append(worker_block)
    else:
        text_parts.append("🟢 <b>ACTIVE WORKERS:</b> None active (Workers idle & ready!)\n")

    text_parts.append("────────────────────────────────────\n")

    if queued_tasks:
        text_parts.append(f"⏳ <b>QUEUED TASKS ({len(queued_tasks)} Waiting Sequentially):</b>\n")
        for q in queued_tasks:
            text_parts.append(
                f"• <b>Position #{q.get('position')}:</b> {q.get('name')}\n"
                f"  <i>Waiting for active task on <code>{q.get('lock_key')}</code> to release.</i>\n"
            )
    else:
        text_parts.append("⏳ <b>QUEUED TASKS:</b> Queue is empty.\n")

    inline_kb = []
    # Add stop buttons for running tasks
    for t in active_tasks[:4]:
        t_id = t.get("task_id", "")
        t_name = t.get("name", "Task")[:16]
        inline_kb.append([{"text": f"🛑 Stop {t_name}", "callback_data": f"task:stop:{t_id}"}])

    inline_kb.append([
        {"text": "🔄 Refresh Status", "callback_data": "root:queue"},
        {"text": "📋 Main Menu", "callback_data": "root:main"}
    ])

    keyboard = {"inline_keyboard": inline_kb}
    full_text = "".join(text_parts)

    if message_id:
        res = edit_message_text(chat_id, message_id, full_text, keyboard=keyboard)
        if res.get("ok"):
            return {"status": "success", "response": res}

    res = make_telegram_request(
        bot_token,
        "sendMessage",
        data={
            "chat_id": chat_id,
            "text": full_text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard),
        }
    )
    return {"status": "success" if res.get("ok") else "error", "response": res}


def send_queue_collision_notice(chat_id: str, task_name: str, lock_key: str, position: int, active_ahead: str = None) -> dict:
    """Dispatches a notification when a task collides with an active account and is queued."""
    bot_token, _ = get_telegram_credentials()
    if not bot_token:
        return {"status": "error"}

    text = (
        f"⏳ <b>Task Placed in Sequential Queue (Position #{position})</b>\n\n"
        f"🎯 <b>Task:</b> <code>{task_name}</code>\n"
        f"🔒 <b>Account Lock:</b> <code>{lock_key}</code>\n"
        f"⚠️ <b>Collision Guard:</b> Another task is currently active on this social account.\n\n"
        f"⚡ <i>Your task is queued in FIFO order and will start automatically as soon as the current task finishes!</i>\n\n"
        f"Tap below to view live multitasking progress:"
    )

    keyboard = {
        "inline_keyboard": [
            [{"text": "⚡ View Queue & Active Tasks", "callback_data": "root:queue"}],
            [{"text": "📋 Main Menu", "callback_data": "root:main"}]
        ]
    }

    res = make_telegram_request(
        bot_token,
        "sendMessage",
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard),
        }
    )
    return {"status": "success" if res.get("ok") else "error", "response": res}


def send_task_start_notification(
    account: dict = None,
    product_name: str = "Loan Solutions",
    platforms: list = None,
    llm_provider: str = "ChatGPT",
    campaign_id: str = None,
    chat_id: str = None
) -> dict:
    """
    Dispatches a real-time notification to Telegram when a campaign / generation task starts.
    Includes active Google Chrome profile and mapped Facebook & Instagram IDs.
    """
    bot_token, default_chat_id = get_telegram_credentials()
    target_chat = chat_id or default_chat_id
    if not bot_token or not target_chat:
        return {"status": "error", "message": "Missing Telegram credentials."}

    acc = account or {}
    email = acc.get("google_email") or acc.get("email") or "2003shivam1990@gmail.com"
    name = acc.get("google_name") or acc.get("name") or "Shivam Mishra"
    p_dir = acc.get("profile_dir") or acc.get("profile_directory") or "Default"
    fb = acc.get("facebook_name") or "Techie Shivam (Loan Solutions)"
    fb_id = acc.get("facebook_id") or "techieshivam"
    ig = acc.get("instagram_username") or "loansolutions2026"

    plats = platforms or ["Facebook", "Instagram"]
    plat_str = ", ".join([p.capitalize() for p in plats])
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")

    text = (
        "🚀 <b>CAMPAIGN TASK STARTED!</b>\n\n"
        f"👤 <b>Google Account:</b> {name}\n"
        f"📧 <b>Google Email:</b> <code>{email}</code>\n"
        f"📁 <b>Chrome Profile:</b> <code>{p_dir}</code>\n"
        f"📘 <b>Linked Facebook:</b> <b>{fb}</b> (ID: <code>{fb_id}</code>)\n"
        f"📸 <b>Linked Instagram:</b> <b>@{ig}</b>\n\n"
        f"🎯 <b>Campaign / Product:</b> <code>{product_name}</code>\n"
        f"🌐 <b>Target Platforms:</b> {plat_str}\n"
        f"🤖 <b>AI Provider:</b> {llm_provider.upper()}\n"
        f"🕒 <b>Started At:</b> {now_str}\n\n"
        "⚡ <i>Launching Google Chrome with isolated profile session. AI generating viral marketing copy & branded graphic...</i>"
    )

    res = make_telegram_request(
        bot_token,
        "sendMessage",
        data={
            "chat_id": target_chat,
            "text": text,
            "parse_mode": "HTML",
        }
    )
    return {"status": "success" if res.get("ok") else "error", "response": res}


def send_task_completed_notification(
    account: dict = None,
    product_name: str = "Loan Solutions",
    campaign_id: str = None,
    results: list = None,
    platforms: list = None,
    chat_id: str = None
) -> dict:
    """
    Dispatches a real-time notification to Telegram when a campaign task completes and is published.
    Includes active Google Chrome profile, mapped Facebook & Instagram IDs, and live post URLs.
    """
    bot_token, default_chat_id = get_telegram_credentials()
    target_chat = chat_id or default_chat_id
    if not bot_token or not target_chat:
        return {"status": "error", "message": "Missing Telegram credentials."}

    acc = account or {}
    email = acc.get("google_email") or acc.get("email") or "2003shivam1990@gmail.com"
    name = acc.get("google_name") or acc.get("name") or "Shivam Mishra"
    p_dir = acc.get("profile_dir") or acc.get("profile_directory") or "Default"
    fb = acc.get("facebook_name") or "Techie Shivam (Loan Solutions)"
    ig = acc.get("instagram_username") or "loansolutions2026"

    now_str = time.strftime("%Y-%m-%d %H:%M:%S")

    res_items = results or []
    link_rows = []
    for r in res_items:
        p_name = r.get("name") or r.get("platform", "Platform").capitalize()
        url = r.get("url")
        verified = r.get("verified", True)
        v_badge = "Verified Live ✅" if verified else "Published ✅"
        if url:
            link_rows.append(f"• <b>{p_name}:</b> {v_badge} — <a href=\"{url}\">View Live Post</a>")
        else:
            link_rows.append(f"• <b>{p_name}:</b> {v_badge}")

    links_text = "\n".join(link_rows) if link_rows else "• Verified live across social channels ✅"

    text = (
        "🎉 <b>CAMPAIGN TASK COMPLETED & PUBLICLY PUBLISHED!</b>\n\n"
        f"👤 <b>Google Account:</b> {name} (<code>{email}</code>)\n"
        f"📁 <b>Chrome Profile:</b> <code>{p_dir}</code>\n"
        f"📘 <b>Facebook Page:</b> {fb}\n"
        f"📸 <b>Instagram Account:</b> @{ig}\n"
        f"🎯 <b>Campaign:</b> {product_name}\n"
        f"🕒 <b>Completed At:</b> {now_str}\n\n"
        "🔗 <b>Public Post Links:</b>\n"
        f"{links_text}\n\n"
        "🚀 <i>All posts verified live on public social media feeds!</i>"
    )

    buttons = []
    for r in res_items:
        u = r.get("url")
        p = r.get("platform", "").lower()
        if u:
            if "instagram" in p or "instagr.am" in u:
                buttons.append([{"text": "📸 View on Instagram ↗️", "url": u}])
            elif "facebook" in p or "facebook.com" in u:
                buttons.append([{"text": "📘 View on Facebook ↗️", "url": u}])
            else:
                buttons.append([{"text": f"🌐 View on {p.capitalize()} ↗️", "url": u}])

    keyboard = {"inline_keyboard": buttons} if buttons else None

    req_data = {
        "chat_id": target_chat,
        "text": text,
        "parse_mode": "HTML",
    }
    if keyboard:
        req_data["reply_markup"] = json.dumps(keyboard)

    res = make_telegram_request(
        bot_token,
        "sendMessage",
        data=req_data
    )
    return {"status": "success" if res.get("ok") else "error", "response": res}


def send_telegram_document(chat_id: str, file_path: str, caption: str = None) -> dict:
    """Sends a local document (e.g., .docx, .pdf) to a Telegram chat with HTML caption."""
    bot_token, default_chat = get_telegram_credentials()
    target_chat = chat_id or default_chat
    if not bot_token or not target_chat:
        return {"status": "error", "message": "Missing Telegram credentials."}

    p = Path(file_path)
    if not p.exists():
        return {"status": "error", "message": f"File not found: {file_path}"}

    fname = p.name
    with open(p, "rb") as f:
        file_bytes = f.read()

    data = {
        "chat_id": target_chat,
        "parse_mode": "HTML"
    }
    if caption:
        data["caption"] = caption[:1024]

    mime = "application/octet-stream"
    if fname.lower().endswith(".docx"):
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif fname.lower().endswith(".pdf"):
        mime = "application/pdf"

    res = make_telegram_request(
        bot_token,
        "sendDocument",
        data=data,
        files={"document": (fname, file_bytes, mime)}
    )
    return {"status": "success" if res.get("ok") else "error", "response": res}






