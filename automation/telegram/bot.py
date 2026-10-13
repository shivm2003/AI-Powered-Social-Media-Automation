"""
Telegram Bot for Preview and Approval Workflow.
Features:
- Sends photo/video previews with inline interactive buttons: [✅ Approve], [✏️ Revise], [❌ Reject]
- Handles approval to trigger social posting
- Handles user revision feedback/suggestions to remake content and resend preview
"""
import os
import json
import urllib.request
import urllib.parse
import logging
from pathlib import Path
import sqlite3

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
    except Exception as e:
        logger.error(f"Telegram API request failed ({method}): {e}")
        return {"ok": False, "description": str(e)}


def send_preview_to_telegram(
    campaign_id: str,
    caption: str,
    media_path: str,
    platforms: list = None,
    revision_count: int = 0
) -> dict:
    """
    Sends generated image/video along with caption and interactive approval buttons to Telegram.
    """
    bot_token, chat_id = get_telegram_credentials()
    if not bot_token or not chat_id:
        logger.warning("Telegram Bot Token or Chat ID not configured.")
        return {
            "status": "warning",
            "message": "Telegram Bot Token or Chat ID not configured. Please set them in Settings."
        }

    import html
    safe_caption = html.escape(caption)
    platforms_str = ", ".join(platforms or ["Facebook", "Instagram"])
    text_content = (
        f"🌟 <b>Content Preview for {platforms_str}</b>\n"
        f"{f'<i>(Revision #{revision_count})</i>' if revision_count > 0 else ''}\n\n"
        f"📝 <b>Caption:</b>\n{safe_caption}\n\n"
        f"👉 <i>Review above and choose an action:</i>"
    )

    # Inline keyboard buttons
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Approve & Post", "callback_data": f"approve:{campaign_id}"},
                {"text": "✏️ Suggest Revision", "callback_data": f"revise:{campaign_id}"},
            ],
            [
                {"text": "❌ Reject / Cancel", "callback_data": f"reject:{campaign_id}"}
            ]
        ]
    }

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


def send_platform_selection_menu(campaign_id: str, chat_id: str = None) -> dict:
    """
    Sends an action keyboard asking the user which social media platform to publish to.
    """
    bot_token, default_chat_id = get_telegram_credentials()
    target_chat_id = chat_id or default_chat_id
    if not bot_token or not target_chat_id:
        return {"status": "error", "message": "Missing Telegram credentials."}

    text = (
        "🚀 <b>Campaign Approved!</b>\n\n"
        "Which social media platform would you like to publish this post to?"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "📘 Facebook", "callback_data": f"post_to:facebook:{campaign_id}"},
                {"text": "📸 Instagram", "callback_data": f"post_to:instagram:{campaign_id}"},
            ],
            [
                {"text": "💼 LinkedIn", "callback_data": f"post_to:linkedin:{campaign_id}"},
                {"text": "💬 WhatsApp", "callback_data": f"post_to:whatsapp:{campaign_id}"},
            ],
            [
                {"text": "❌ Cancel", "callback_data": f"cancel_post:{campaign_id}"}
            ]
        ]
    }

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


def send_text_message(chat_id: str, text: str) -> dict:
    """Sends a plain or HTML formatted text message."""
    bot_token, _ = get_telegram_credentials()
    if not bot_token:
        return {"ok": False}
    return make_telegram_request(bot_token, "sendMessage", data={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})


def send_start_dashboard(chat_id: str, products: list) -> dict:
    """
    Sends the welcome dashboard explaining the 5-step automation workflow
    and provides interactive buttons for each registered product.
    """
    bot_token, _ = get_telegram_credentials()
    if not bot_token:
        return {"status": "error", "message": "Missing Telegram credentials."}

    text = (
        "🚀 <b>AI-Powered Social Media Automation</b>\n"
        "<i>Welcome! Automate high-converting marketing posts with human-like AI.</i>\n\n"
        "📋 <b>5-Step Workflow:</b>\n"
        "1️⃣ <b>Select Product</b> — Choose from your registered products below.\n"
        "2️⃣ <b>Human AI Flow</b> — Chrome opens ChatGPT & injects prompts like a human.\n"
        "3️⃣ <b>Image & Copy Generation</b> — Generates custom graphics & viral hashtags.\n"
        "4️⃣ <b>Review in Telegram</b> — Complete preview sent here for your one-click approval.\n"
        "5️⃣ <b>Auto-Publish</b> — Upon your approval, post is published directly to Facebook or Instagram!\n\n"
        "👇 <b>Select a product to start generating:</b>"
    )

    inline_keyboard = []
    if products:
        for p in products:
            p_id = p.get("id")
            p_name = p.get("name") or "Featured Product"
            p_cat = (p.get("category") or "").capitalize()
            btn_text = f"🚀 Generate: {p_name} ({p_cat})" if p_cat else f"🚀 Generate: {p_name}"
            inline_keyboard.append([{"text": btn_text, "callback_data": f"gen_prod:{p_id}"}])
    else:
        inline_keyboard.append([{"text": "🚀 Generate Quick Post", "callback_data": "gen_prod:default"}])

    inline_keyboard.append([
        {"text": "ℹ️ How It Works", "callback_data": "info:how_it_works"},
        {"text": "📋 Active Products", "callback_data": "info:products"}
    ])

    keyboard = {"inline_keyboard": inline_keyboard}

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
    if not res.get("ok"):
        plain_text = (
            "🚀 AI-Powered Social Media Automation\n"
            "Welcome! Automate high-converting marketing posts with human-like AI.\n\n"
            "5-Step Workflow:\n"
            "1. Select Product — Choose from your registered products below.\n"
            "2. Human AI Flow — Chrome opens ChatGPT & injects prompts like a human.\n"
            "3. Image & Copy Generation — Generates custom graphics & viral hashtags.\n"
            "4. Review in Telegram — Complete preview sent here for your approval.\n"
            "5. Auto-Publish — Upon approval, post is published to Facebook/Instagram!\n\n"
            "Select a product below:"
        )
        res = make_telegram_request(
            bot_token,
            "sendMessage",
            data={
                "chat_id": chat_id,
                "text": plain_text,
                "reply_markup": json.dumps(keyboard),
            }
        )
    return {"status": "success" if res.get("ok") else "error", "response": res}

