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

    # If Loan Solutions, ensure caption always includes the mandatory Apply Now link
    if is_loan_solutions and target_apply_url not in caption:
        if "#" in caption:
            parts = caption.split("#", 1)
            caption = f"{parts[0].rstrip()}\n\n👉 Apply Now: {target_apply_url}\n\n#{parts[1]}"
        else:
            caption = f"{caption.rstrip()}\n\n👉 Apply Now: {target_apply_url}"

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
                {"text": "👥 2. Outreach (Follow & Friend Requests)", "callback_data": "root:outreach"}
            ],
            [
                {"text": "💻 3. Remote Prompt / Antigravity Assistant", "callback_data": "root:antigravity"}
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


def send_outreach_platform_menu(chat_id: str, message_id: int = None) -> dict:
    """Outreach Step 1: Platform Selection."""
    bot_token, _ = get_telegram_credentials()
    if not bot_token:
        return {"status": "error"}

    text = (
        "👥 <b>Outreach & Growth Engine — Step 1: Platform</b>\n\n"
        "Which platform would you like to send outreach requests on?"
    )

    keyboard = {
        "inline_keyboard": [
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


def send_outreach_location_menu(chat_id: str, platform: str, message_id: int = None) -> dict:
    """Outreach Step 2: Target Location Selection."""
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
        "📍 <b>Outreach Step 2 of 3: Target Location</b>\n"
        "Select your target location from presets or type any city name directly in this chat:"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "📍 New Delhi", "callback_data": f"outreach:loc:{platform}:New Delhi"},
                {"text": "📍 Mumbai", "callback_data": f"outreach:loc:{platform}:Mumbai"}
            ],
            [
                {"text": "📍 Bangalore", "callback_data": f"outreach:loc:{platform}:Bangalore"},
                {"text": "📍 New York", "callback_data": f"outreach:loc:{platform}:New York"}
            ],
            [
                {"text": "📍 London", "callback_data": f"outreach:loc:{platform}:London"},
                {"text": "📍 Dubai", "callback_data": f"outreach:loc:{platform}:Dubai"}
            ],
            [{"text": "✏️ Type Custom City Name", "callback_data": f"outreach:loc_custom:{platform}"}],
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


def send_outreach_count_menu(chat_id: str, platform: str, location: str, message_id: int = None) -> dict:
    """Outreach Step 3: Request Count Selection."""
    bot_token, _ = get_telegram_credentials()
    if not bot_token:
        return {"status": "error"}

    plat_label = {
        "both": "⚡ Dual (Facebook + Instagram)",
        "facebook": "📘 Facebook Friends",
        "instagram": "📸 Instagram Follows"
    }.get(platform, platform.capitalize())

    text = (
        f"👥 <b>Platform:</b> {plat_label}\n"
        f"📍 <b>Location:</b> {location}\n\n"
        "🎯 <b>Outreach Step 3 of 3: Request Count</b>\n"
        "Select a preset below or tap <b>✏️ Enter Custom Number</b> to enter any specific quantity:"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "5 Requests (Test)", "callback_data": f"outreach:run:{platform}:{location}:5"},
                {"text": "10 Requests (Recommended)", "callback_data": f"outreach:run:{platform}:{location}:10"}
            ],
            [
                {"text": "25 Requests", "callback_data": f"outreach:run:{platform}:{location}:25"},
                {"text": "50 Requests", "callback_data": f"outreach:run:{platform}:{location}:50"}
            ],
            [
                {"text": "✏️ Enter Custom Number", "callback_data": f"outreach:count_custom:{platform}:{location}"}
            ],
            [{"text": "🔙 Change Location", "callback_data": f"outreach:plat:{platform}"}]
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




