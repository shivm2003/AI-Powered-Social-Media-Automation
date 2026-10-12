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


def get_telegram_credentials():
    """Retrieve bot token and chat ID from DB settings or environment."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

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

    platforms_str = ", ".join(platforms or ["Facebook", "Instagram"])
    text_content = (
        f"🌟 <b>Content Preview for {platforms_str}</b>\n"
        f"{f'<i>(Revision #{revision_count})</i>' if revision_count > 0 else ''}\n\n"
        f"📝 <b>Caption:</b>\n{caption}\n\n"
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

    logger.info(f"Sent Telegram preview for campaign {campaign_id}: {res.get('ok')}")
    return {
        "status": "success" if res.get("ok") else "error",
        "response": res
    }
