"""
Manvxi AI — Main Entry Point

Receives JSON commands from the Node.js backend via stdin/stdout IPC.
Handles:
- test_login: Opens Chrome with persistent profile for one-time manual MFA
- generate_text: Generates high-converting marketing copy via chosen LLM (Gemini, ChatGPT, Claude)
- generate_image: Creates branded social media graphics (1:1, 4:5, 9:16, 16:9)
- generate_video: Assembles promotional video clips using MoviePy
- send_telegram_preview: Sends media preview with [✅ Approve], [✏️ Revise], [❌ Reject] buttons
- post: Publishes approved content to Facebook, Instagram, LinkedIn, and WhatsApp
"""
import sys
import json
import uuid
import argparse
import logging
from pathlib import Path

from config import LOGS_DIR, PLATFORM_URLS
from browser.driver import browser
from browser.profiles import get_profile_dir
from llm import generate_marketing_content
from media import generate_social_image, generate_promo_video
from social import publish_to_platform, publish_to_all_platforms
from telegram.bot import send_preview_to_telegram

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "automation.log", encoding="utf-8"),
        logging.StreamHandler(sys.stderr),  # stderr for logs, stdout for IPC
    ],
)
logger = logging.getLogger("automation")


def send_response(data: dict):
    """Send JSON response to Node.js backend via stdout."""
    print(json.dumps(data), flush=True)


def handle_command(command: dict):
    """Process a command from the backend."""
    action = command.get("action")
    logger.info(f"Processing command: {action}")

    try:
        if action == "test_login":
            platform = command.get("platform", "").lower()
            logger.info(f"Initiating login test for {platform}...")
            # Ensure profile directory exists
            get_profile_dir(platform)
            # Launch Chrome with platform's dedicated profile
            try:
                driver = browser.navigate(platform, PLATFORM_URLS.get(platform))
                logger.info(f"Chrome opened for {platform}. Session cookies will persist in profile.")
                send_response({
                    "status": "success",
                    "action": action,
                    "platform": platform,
                    "message": f"Browser opened for {platform}. Complete any verification or MFA. The session is saved.",
                })
            except Exception as e:
                logger.warning(f"Browser launch exception: {e}")
                send_response({
                    "status": "success",
                    "action": action,
                    "platform": platform,
                    "message": f"Profile initialized for {platform}. (Browser launch notice: {e})",
                })

        elif action == "generate_text":
            product = command.get("product", {})
            provider = command.get("provider", "gemini")
            platforms = command.get("platforms", ["facebook", "instagram"])
            content_type = command.get("content_type", "image")
            language = command.get("language", "english")
            tone = command.get("tone", "professional")
            cta = command.get("cta", "learn_more")
            custom_instructions = command.get("custom_instructions", "")

            content = generate_marketing_content(
                product=product,
                provider=provider,
                platforms=platforms,
                content_type=content_type,
                language=language,
                tone=tone,
                cta=cta,
                custom_instructions=custom_instructions
            )

            send_response({
                "status": "success",
                "action": action,
                "provider": provider,
                "content": content,
            })

        elif action == "generate_image":
            provider = command.get("provider", "chatgpt").lower()
            product = command.get("product", {})
            headline = command.get("headline", "")
            subheadline = command.get("subheadline", "")
            brand_colors = command.get("brand_colors", {})
            aspect_ratio = command.get("aspect_ratio", "1:1")
            cta_text = command.get("cta_text", "Learn More ➜")
            logo_path = command.get("logo_path", None)
            skill_image_path = command.get("skill_image_path", logo_path)
            visual_style = command.get("visual_style", "photorealistic")
            custom_instructions = command.get("custom_instructions", "")
            category = product.get("category", "Featured")

            img_path = None
            if provider == "chatgpt":
                try:
                    from llm.chatgpt import generate_image_with_chatgpt_browser
                    img_path = generate_image_with_chatgpt_browser(
                        product_name=product.get("name", "Product"),
                        headline=headline,
                        subheadline=subheadline,
                        visual_style=visual_style,
                        aspect_ratio=aspect_ratio,
                        cta_text=cta_text,
                        skill_image_path=skill_image_path,
                        custom_instructions=custom_instructions,
                        brand_colors=brand_colors,
                        category=category
                    )
                except Exception as e_cg:
                    logger.warning(f"ChatGPT browser image generator notice: {e_cg}")
            elif provider == "gemini":
                try:
                    from llm.gemini import generate_image_with_gemini_browser
                    img_path = generate_image_with_gemini_browser(
                        product_name=product.get("name", "Product"),
                        headline=headline,
                        subheadline=subheadline,
                        visual_style=visual_style,
                        aspect_ratio=aspect_ratio,
                        cta_text=cta_text,
                        skill_image_path=skill_image_path,
                        custom_instructions=custom_instructions,
                        brand_colors=brand_colors,
                        category=category
                    )
                except Exception as e_gem:
                    logger.warning(f"Gemini browser image generator notice: {e_gem}")

            if not img_path:
                img_path = generate_social_image(
                    product_name=product.get("name", "Product"),
                    headline=headline,
                    subheadline=subheadline,
                    brand_colors=brand_colors,
                    aspect_ratio=aspect_ratio,
                    cta_text=cta_text,
                    logo_path=skill_image_path,
                    category=category
                )

            send_response({
                "status": "success",
                "action": action,
                "image_path": str(img_path),
                "filename": img_path.name,
            })

        elif action == "generate_video":
            product = command.get("product", {})
            slides = command.get("slides", [])
            brand_colors = command.get("brand_colors", {})
            duration = command.get("duration", 15)
            aspect_ratio = command.get("aspect_ratio", "9:16")
            logo_path = command.get("logo_path", None)

            video_path = generate_promo_video(
                product_name=product.get("name", "Product"),
                slides=slides,
                brand_colors=brand_colors,
                duration=duration,
                aspect_ratio=aspect_ratio,
                logo_path=logo_path
            )

            send_response({
                "status": "success",
                "action": action,
                "video_path": str(video_path),
                "filename": video_path.name,
            })

        elif action == "send_telegram_preview":
            campaign_id = command.get("campaign_id", "")
            caption = command.get("caption", "")
            media_path = command.get("media_path", "")
            platforms = command.get("platforms", [])
            revision_count = command.get("revision_count", 0)
            product_name = command.get("product_name")
            apply_url = command.get("apply_url")

            result = send_preview_to_telegram(
                campaign_id=campaign_id,
                caption=caption,
                media_path=media_path,
                platforms=platforms,
                revision_count=revision_count,
                product_name=product_name,
                apply_url=apply_url
            )

            send_response({
                "status": result.get("status", "success"),
                "action": action,
                "message": result.get("message", "Telegram preview dispatched"),
                "details": result,
            })

        elif action == "post":
            platforms = command.get("platforms", [])
            if not platforms and command.get("platform"):
                platforms = [command.get("platform")]

            media_path = command.get("media_path")
            caption = command.get("caption", "")
            campaign_id = command.get("campaign_id") or str(uuid.uuid4())

            results = publish_to_all_platforms(
                platforms=platforms,
                media_path=media_path,
                caption=caption
            )

            # Persist campaign status in PostgreSQL & SQLite database
            try:
                from db_campaigns import save_or_update_campaign
                save_or_update_campaign(
                    campaign_id=campaign_id,
                    status="posted",
                    platforms=platforms,
                    media_path=media_path,
                    caption=caption,
                    posted_at_now=True
                )
            except Exception as e_p_db:
                logger.warning(f"Database save error during post action: {e_p_db}")

            send_response({
                "status": "success",
                "action": action,
                "campaign_id": campaign_id,
                "results": results,
                "message": f"Posted to {', '.join(platforms)}",
            })

        elif action == "human_flow":
            platform = command.get("platform", "gemini")
            query = command.get("query", "Search and draft a viral marketing post for our product.")
            logger.info(f"Executing human_flow for platform: {platform}...")
            from browser.human_operator import execute_full_human_flow
            result = execute_full_human_flow(platform=platform, query=query)
            send_response(result)

        elif action == "human_flow_generate":
            platform = command.get("platform") or command.get("provider", "chatgpt")
            product = command.get("product", {})
            platforms = command.get("platforms", ["facebook", "instagram"])
            content_type = command.get("content_type", "image")
            language = command.get("language", "english")
            tone = command.get("tone", "professional")
            cta = command.get("cta", "learn_more")
            custom_instructions = command.get("custom_instructions", "")
            aspect_ratio = command.get("aspect_ratio", "1:1")
            visual_style = command.get("visual_style", "photorealistic")
            skill_image_path = command.get("skill_image_path", None)
            campaign_id = command.get("campaign_id", None)

            logger.info(f"Executing human_flow_generate for platform: {platform}...")
            from browser.human_operator import execute_human_generation_and_telegram_flow
            result = execute_human_generation_and_telegram_flow(
                platform=platform,
                product=product,
                platforms=platforms,
                content_type=content_type,
                language=language,
                tone=tone,
                cta=cta,
                custom_instructions=custom_instructions,
                aspect_ratio=aspect_ratio,
                visual_style=visual_style,
                skill_image_path=skill_image_path,
                campaign_id=campaign_id
            )
            send_response(result)

        elif action == "human_chatgpt_image_telegram":
            product = command.get("product", {})
            logger.info("Executing human_chatgpt_image_telegram flow...")
            from chatgpt_human_image_telegram import run_chatgpt_human_image_and_telegram
            result = run_chatgpt_human_image_and_telegram(custom_product=product)
            send_response(result)

        elif action == "growth_outreach":
            campaign_id = command.get("campaign_id") or str(uuid.uuid4())
            platform = command.get("platform", "both")
            location = command.get("location", "New Delhi")
            target_count = int(command.get("target_count", 10))
            safety_delay = int(command.get("safety_delay", 15))
            tg_chat_id = command.get("telegram_chat_id", None)
            tg_message_id = command.get("telegram_message_id", None)

            logger.info(f"Executing growth_outreach for {platform} in {location}...")
            from social.growth_orchestrator import run_growth_campaign
            result = run_growth_campaign(
                campaign_id=campaign_id,
                platform=platform,
                location=location,
                target_count=target_count,
                safety_delay=safety_delay,
                tg_chat_id=tg_chat_id,
                tg_message_id=tg_message_id
            )
            send_response(result)

        elif action == "growth_stop":
            campaign_id = command.get("campaign_id", "")
            from social.growth_orchestrator import stop_growth_campaign
            stopped = stop_growth_campaign(campaign_id)
            send_response({
                "status": "success",
                "campaign_id": campaign_id,
                "stopped": stopped
            })

        elif action == "fb_get_pending_requests":
            from social.facebook_accept import get_pending_friend_requests
            max_scrolls = int(command.get("max_scrolls", 3))
            res = get_pending_friend_requests(max_scrolls=max_scrolls)
            send_response(res)

        elif action == "fb_accept_requests":
            from social.facebook_accept import accept_facebook_friend_requests
            target_count = command.get("target_count")
            if target_count is not None and str(target_count).lower() != "all":
                try:
                    target_count = int(target_count)
                except Exception:
                    target_count = 0
            else:
                target_count = 0

            like_recent = bool(command.get("like_recent", False))
            safety_delay = int(command.get("safety_delay", 3))
            campaign_id = command.get("campaign_id")

            res = accept_facebook_friend_requests(
                target_count=target_count,
                like_recent=like_recent,
                safety_delay=safety_delay,
                campaign_id=campaign_id
            )
            send_response(res)

        elif action == "ig_get_following_list":
            from social.instagram_unfollow import get_instagram_following_list
            max_count = int(command.get("max_count", 50))
            res = get_instagram_following_list(max_count=max_count)
            send_response(res)

        elif action == "ig_unfollow_accounts":
            from social.instagram_unfollow import unfollow_instagram_accounts
            target_count = command.get("target_count")
            if target_count is not None and str(target_count).lower() != "all":
                try:
                    target_count = int(target_count)
                except Exception:
                    target_count = 10
            else:
                target_count = 0

            safety_delay = int(command.get("safety_delay", 10))
            specific_users = command.get("specific_users")
            campaign_id = command.get("campaign_id")

            res = unfollow_instagram_accounts(
                target_count=target_count,
                specific_users=specific_users,
                safety_delay=safety_delay,
                campaign_id=campaign_id
            )
            send_response(res)

        else:
            send_response({
                "status": "error",
                "action": action,
                "message": f"Unknown action: {action}",
            })

    except Exception as e:
        logger.error(f"Error executing command {action}: {e}", exc_info=True)
        send_response({
            "status": "error",
            "action": action,
            "message": str(e),
        })


def interactive_mode():
    """Read commands from stdin in a loop."""
    logger.info("Automation engine listening on stdin...")
    send_response({"status": "ready", "message": "Automation engine ready"})

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            cmd = json.loads(line)
            handle_command(cmd)
        except json.JSONDecodeError as e:
            send_response({"status": "error", "message": f"Invalid JSON input: {e}"})


def main():
    parser = argparse.ArgumentParser(description="Manvxi AI Engine")
    parser.add_argument("--test-login", type=str, help="Test login for a platform (facebook, instagram, linkedin, whatsapp)")
    parser.add_argument("--test-llm", type=str, help="Test LLM (gemini, chatgpt, claude)")
    args = parser.parse_args()

    if args.test_login:
        handle_command({"action": "test_login", "platform": args.test_login})
    elif args.test_llm:
        handle_command({
            "action": "generate_text",
            "provider": args.test_llm,
            "product": {"name": "SmartWidget", "description": "AI tool for makers"},
        })
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
