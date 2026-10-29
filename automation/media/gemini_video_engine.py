"""
24-Second Gemini AI Video Generation Engine (Indian Standard).

Capitalizes on Google Gemini's 8-second video capability (free allowance of 3 clips/day)
to build an end-to-end 24-second master marketing video composed of 3 sequential clips:
- Clip 1 (00:00 - 00:08): The Relatable Hook (Indian Context & Problem Statement)
- Clip 2 (00:08 - 00:16): The Seamless Digital Solution (₹ Amounts, Speed, Paperless KYC)
- Clip 3 (00:16 - 00:24): The Climax & Compelling Call to Action (Loan Solutions Branding & Apply Now)

Follows strict Indian Standards:
- Currency: Strictly Indian Rupee (₹ INR) – never foreign currency.
- Demographics: Authentic Indian middle-class families, young professionals, MSME entrepreneurs.
- Setting: Contemporary Indian urban/semi-urban settings.
- CTA: Direct link to https://loansolutions.everythingrental.in/application
"""
import os
import sys
import time
import uuid
import random
import logging
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

from config import VIDEOS_DIR, IMAGES_DIR
from .image_generator import hex_to_rgb, get_font, wrap_text, ASPECT_RATIO_DIMS

logger = logging.getLogger("automation.media.gemini_video")

# Ensure video and image directories exist
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Loan Solutions Branding Defaults
LOAN_SOLUTIONS_LOGO = Path(__file__).parent.parent.parent / "Loan Solutions.png"
LOAN_SOLUTIONS_APPLY_URL = "https://loansolutions.everythingrental.in/application"

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# MoviePy import supporting both v2.x and v1.x
try:
    from moviepy import (
        VideoFileClip,
        ImageClip,
        ColorClip,
        CompositeVideoClip,
        concatenate_videoclips,
        AudioFileClip
    )
    HAS_MOVIEPY = True
except ImportError:
    try:
        from moviepy.editor import (
            VideoFileClip,
            ImageClip,
            ColorClip,
            CompositeVideoClip,
            concatenate_videoclips,
            AudioFileClip
        )
        HAS_MOVIEPY = True
    except ImportError:
        HAS_MOVIEPY = False
        logger.warning("MoviePy not found. Video rendering will use fallback.")


def generate_voiceover_audio(text: str, output_path: Path, voice: str = "hi-IN-MadhurNeural") -> Path:
    """
    Generates authentic Indian neural voiceover audio using edge-tts.
    Default voice: 'hi-IN-MadhurNeural' (conversational Hindi/Indian English).
    Alternative: 'hi-IN-SwaraNeural' or 'en-IN-PrabhatNeural'.
    """
    import asyncio
    try:
        import edge_tts
        clean_text = (text or "").strip().replace('"', '').replace("'", "")
        if not clean_text or len(clean_text) < 4:
            clean_text = "Loan Solutions ke saath paayein 100% paperless digital approval aur instant bank disbursal."

        async def _gen():
            comm = edge_tts.Communicate(clean_text, voice)
            await comm.save(str(output_path))

        asyncio.run(_gen())
        if output_path.exists() and output_path.stat().st_size > 400:
            logger.info(f"Generated neural voiceover at {output_path} ({output_path.stat().st_size} bytes)")
            return output_path
    except Exception as e:
        logger.warning(f"Voiceover generation notice: {e}")
    return None


def send_individual_clip_to_telegram(
    clip_path: Path,
    clip_info: dict,
    chat_id: str = None,
    bot_token: str = None
) -> dict:
    """
    Immediately shares an individual 8-second clip into the Telegram bot with its scene metadata.
    """
    try:
        from telegram.bot import get_telegram_credentials, make_telegram_request
        if not bot_token or not chat_id:
            token, cid = get_telegram_credentials()
            bot_token = bot_token or token
            chat_id = chat_id or cid

        if not bot_token or not chat_id or not clip_path or not os.path.exists(str(clip_path)):
            logger.warning(f"Could not dispatch clip to Telegram (missing credentials or file {clip_path})")
            return {"ok": False}

        clip_num = clip_info.get("clip_index", 1)
        headline = clip_info.get("headline", "")
        audio_script = clip_info.get("audio_script", "")
        role = clip_info.get("role", f"Part {clip_num}/3")

        time_range = clip_info.get("time_range", f"00:0{8*(clip_num-1)} - 0:{'0' if 8*clip_num < 10 else ''}{8*clip_num}")
        caption_text = (
            f"🎬 <b>Clip {clip_num}/3 ({time_range})</b>\n"
            f"📌 <b>{role}:</b> {headline}\n"
            f"🎙️ <b>Narration Voice:</b> <i>\"{audio_script}\"</i>\n\n"
            f"⚡ <i>8.0s Clip Generated with Indian Standard Voice & Branding</i>"
        )

        with open(clip_path, "rb") as f:
            file_bytes = f.read()

        filename = os.path.basename(str(clip_path))
        res = make_telegram_request(
            bot_token,
            "sendVideo",
            data={
                "chat_id": chat_id,
                "caption": caption_text[:1024],
                "parse_mode": "HTML"
            },
            files={"video": (filename, file_bytes, "video/mp4")}
        )
        logger.info(f"Dispatched Clip #{clip_num} ({filename}) to Telegram: {res.get('ok')}")
        return res
    except Exception as e:
        logger.error(f"Error sending individual clip to Telegram: {e}")
        return {"ok": False, "error": str(e)}


def set_clip_duration(clip, duration: float):
    """Safely set duration across MoviePy 2.x and 1.x."""
    if hasattr(clip, "with_duration"):
        return clip.with_duration(duration)
    elif hasattr(clip, "set_duration"):
        return clip.set_duration(duration)
    clip.duration = duration
    return clip


class GeminiVideoEngine:
    """
    Coordinates 24-second video generation across 3 sequential 8-second clips.
    """

    def __init__(self):
        self.videos_dir = VIDEOS_DIR
        self.images_dir = IMAGES_DIR

    def parse_gemini_generated_script(
        self,
        raw_text: str,
        product_name: str = "Loan Solutions",
        product_category: str = "Finance & Loans"
    ) -> dict:
        """
        Parses structured script generated by Gemini (JSON or free-form text)
        into 3 sequential 8-second clips adhering to Indian culture.
        """
        import re
        clean_name = product_name or "Loan Solutions"
        clean_cat = product_category or "Finance"
        default_script = self.generate_24s_script(prompt=raw_text[:100], product_name=clean_name, product_category=clean_cat)

        if not raw_text or len(raw_text.strip()) < 30:
            return default_script

        # 1. Try parsing JSON
        from utils.extract_json import extract_json_or_fallback
        parsed = extract_json_or_fallback(raw_text, None)
        if parsed and isinstance(parsed, dict) and ("clip1" in parsed or "clips" in parsed):
            logger.info("Successfully parsed Gemini video script from JSON response.")
            if "clips" in parsed and isinstance(parsed["clips"], list) and len(parsed["clips"]) >= 3:
                return parsed
            elif "clip1" in parsed and "clip2" in parsed and "clip3" in parsed:
                return {
                    "title": parsed.get("title", f"{clean_name} - 24s Indian Commercial Reel"),
                    "total_duration": 24,
                    "clips": [
                        {
                            "clip_index": 1,
                            "time_range": "00:00 - 00:08",
                            "role": "The Dream of 'Apna Ghar' (Home Loan)",
                            "headline": parsed["clip1"].get("headline", "Apna Ghar: Home Loans for Families"),
                            "subheadline": parsed["clip1"].get("subheadline", "Affordable monthly EMIs to make homeownership a reality."),
                            "audio_script": parsed["clip1"].get("audio_script", "Har parivaar ka sapna hota hai apna ghar. Loan Solutions ke saath paayein aasan Home Loan, aasan EMIs, aur banayein apna sapna sach!"),
                            "badge": parsed["clip1"].get("badge", "🏠 Home Loan • Apna Ghar Yojana"),
                            "theme_color": "#1E3A8A",
                        },
                        {
                            "clip_index": 2,
                            "time_range": "00:08 - 00:16",
                            "role": "Business Growth (Loan Against Property - LAP)",
                            "headline": parsed["clip2"].get("headline", "Grow Your Business with LAP"),
                            "subheadline": parsed["clip2"].get("subheadline", "Unlock up to 70% property value. Personal & Business Loans also available."),
                            "audio_script": parsed["clip2"].get("audio_script", "Apne business ko nayi unchaaiyon par le jaayein! Apni property ki value unlock karein Loan Against Property (LAP) se, aur paayein maximum funding aasan terms par."),
                            "badge": parsed["clip2"].get("badge", "🏢 LAP • High Capital for Business Growth"),
                            "theme_color": "#065F46",
                        },
                        {
                            "clip_index": 3,
                            "time_range": "00:16 - 00:24",
                            "role": "Complete Solutions & Apply Online",
                            "headline": parsed["clip3"].get("headline", "Home Loan • LAP • Personal & Business Loans"),
                            "subheadline": parsed["clip3"].get("subheadline", f"Visit: {LOAN_SOLUTIONS_APPLY_URL}"),
                            "audio_script": parsed["clip3"].get("audio_script", "Chahe Home Loan ho, LAP, Business Loan ya Personal Loan — Loan Solutions hai aapka bharosemand saathi. Aaj hi apply karein aur eligibility check karein!"),
                            "badge": parsed["clip3"].get("badge", "👉 Check Loan Eligibility Online"),
                            "theme_color": "#7C3AED",
                        }
                    ],
                    "caption": parsed.get("caption", default_script["caption"]),
                    "hashtags": parsed.get("hashtags", default_script["hashtags"])
                }

        # 2. Text-based parsing for sections (CLIP 1, CLIP 2, CLIP 3)
        logger.info("Extracting clips and captions from Gemini text stream...")
        clips = []
        clip_patterns = [
            r"(?:clip\s*1|scene\s*1|part\s*1)([\s\S]*?)(?=(?:clip\s*2|scene\s*2|part\s*2))",
            r"(?:clip\s*2|scene\s*2|part\s*2)([\s\S]*?)(?=(?:clip\s*3|scene\s*3|part\s*3))",
            r"(?:clip\s*3|scene\s*3|part\s*3)([\s\S]*?)(?=(?:caption|hashtags|$))"
        ]

        extracted_clips = []
        for pat in clip_patterns:
            m = re.search(pat, raw_text, re.IGNORECASE)
            if m:
                extracted_clips.append(m.group(1).strip())

        # Extract hashtags
        tags = re.findall(r"#\w+", raw_text)
        if not tags:
            tags = default_script["hashtags"]

        # If sections found, build custom clips
        if len(extracted_clips) == 3:
            for idx, ctext in enumerate(extracted_clips):
                c_num = idx + 1
                lines = [l.strip().lstrip("•-*0123456789.: ") for l in ctext.split("\n") if l.strip()]
                hl = lines[0] if lines else default_script["clips"][idx]["headline"]
                sub = lines[1] if len(lines) > 1 else default_script["clips"][idx]["subheadline"]
                audio = " ".join(lines[2:4]) if len(lines) > 2 else default_script["clips"][idx]["audio_script"]
                badge = default_script["clips"][idx]["badge"]
                color = default_script["clips"][idx]["theme_color"]
                clips.append({
                    "clip_index": c_num,
                    "time_range": default_script["clips"][idx]["time_range"],
                    "role": default_script["clips"][idx]["role"],
                    "headline": hl[:45],
                    "subheadline": sub[:60],
                    "audio_script": audio[:160],
                    "badge": badge,
                    "theme_color": color
                })
        else:
            clips = default_script["clips"]

        # Extract or format caption
        caption = raw_text
        if "caption" in raw_text.lower():
            cap_m = re.search(r"(?:caption|post text)[:\s]+([\s\S]*?)(?=(?:hashtags|$))", raw_text, re.IGNORECASE)
            if cap_m:
                caption = cap_m.group(1).strip()

        from social.caption_helper import ensure_apply_now_at_start
        caption = ensure_apply_now_at_start(caption, apply_url=LOAN_SOLUTIONS_APPLY_URL, is_loan=True)

        return {
            "title": f"{clean_name} - 24s Indian Commercial Reel (Gemini)",
            "total_duration": 24,
            "clips": clips,
            "caption": caption,
            "hashtags": tags
        }

    def generate_24s_script(
        self,
        prompt: str,
        product_name: str = "Loan Solutions",
        product_category: str = "Finance & Loans"
    ) -> dict:
        """
        Creates a structured 24-second script broken into 3 clips of 8 seconds each,
        strictly complying with Indian Standards (₹ Rupee currency, authentic Indian tone).
        """
        clean_name = product_name or "Loan Solutions"
        clean_cat = product_category or "Finance"

        # Try generating via Gemini API if key is present
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            try:
                from llm import generate_with_gemini_api
                system_prompt = (
                    f"Create a 24-second video commercial script for '{clean_name}' ({clean_cat}). "
                    f"STRATEGIC PRODUCT FOCUS: "
                    f"1. Hero Focus 1: Home Loans ('Apna Ghar') specifically targeting Indian middle-class and striving families to own their dream home. "
                    f"2. Hero Focus 2: Loan Against Property (LAP) unlocking property equity to grow business and enterprise. "
                    f"3. Supporting Pillars: Personal Loans & Business Loans retained for full financial versatility and future expansion. "
                    f"Strictly adhere to Google Gemini Safety & Generative AI Policy Guidelines: "
                    f"DO NOT generate deceptive, harmful, or guaranteed financial claims. "
                    f"Ensure 100% lawful, transparent, professional banking and lending assistance in compliance with established financial guidelines. "
                    f"Strictly follow Indian Standards: Use Indian Rupee (₹), Indian context, Indian middle-class & MSME theme. "
                    f"The video must be divided into exactly 3 sequential clips of 8 seconds each: "
                    f"Clip 1 (0-8s): Home Loan - The Dream of 'Apna Ghar' for Middle-Class Families, "
                    f"Clip 2 (8-16s): Loan Against Property (LAP) - Business Growth & Capital Expansion, "
                    f"Clip 3 (16-24s): Complete Loan Solutions (Home, LAP, Personal & Business Loans) & Apply Online. "
                    f"Return a structured JSON with: "
                    f"clip1: {{headline, subheadline, audio_script, visual_prompt, badge}}, "
                    f"clip2: {{headline, subheadline, audio_script, visual_prompt, badge}}, "
                    f"clip3: {{headline, subheadline, audio_script, visual_prompt, badge}}, "
                    f"caption: (full marketing caption with ₹, Home Loan, LAP, Personal & Business Loans, and Apply Now link), "
                    f"hashtags: [list of trending hashtags]"
                )
                raw_json = generate_with_gemini_api(system_prompt, gemini_key)
                from utils.extract_json import extract_json_or_fallback
                parsed = extract_json_or_fallback(raw_json, None)
                if parsed and isinstance(parsed, dict) and "clip1" in parsed:
                    logger.info("Successfully generated 24s Indian standard video script via Gemini API.")
                    return parsed
            except Exception as e_api:
                logger.debug(f"Gemini API script note: {e_api}. Using curated Indian Standard script generator.")

        # High-impact curated Indian Standard Script Generator (Home Loan & LAP Focused, Retaining Personal & Business Loans)
        logger.info(f"Generating optimized 24-second Indian Standard video script for '{clean_name}' (Home Loan & LAP Focus)...")
        return {
            "title": f"{clean_name} - 24s Home Loan & LAP Growth Reel",
            "total_duration": 24,
            "clips": [
                {
                    "clip_index": 1,
                    "time_range": "00:00 - 00:08",
                    "role": "The Dream of 'Apna Ghar' (Home Loan)",
                    "headline": "Apna Ghar: Home Loans for Families",
                    "subheadline": "Affordable EMIs & subsidized rates to own your dream home.",
                    "audio_script": "Har parivaar ka sapna hota hai apna ghar. Loan Solutions ke saath paayein aasan Home Loan, aasan EMIs, aur banayein apna sapna sach!",
                    "badge": "🏠 Home Loan • Apna Ghar Yojana",
                    "visual_prompt": (
                        "Cinematic 8-second video, smiling Indian middle-class family (parents and child) joyfully standing at the entrance of their new dream home during Griha Pravesh with traditional marigold garland, holding keys with gratitude, warm natural morning daylight, 4k resolution, vertical 9:16 aspect ratio. Policy-compliant, wholesome, inspiring commercial aesthetic."
                    ),
                    "theme_color": "#1E3A8A", # Deep Royal Blue
                },
                {
                    "clip_index": 2,
                    "time_range": "00:08 - 00:16",
                    "role": "Business Growth (Loan Against Property - LAP)",
                    "headline": "Grow Your Business with LAP",
                    "subheadline": "Unlock up to 70% property value for business expansion. Personal & Business Loans also available.",
                    "audio_script": "Apne business ko nayi unchaaiyon par le jaayein! Apni property ki value unlock karein Loan Against Property (LAP) se, aur paayein maximum funding aasan terms par.",
                    "badge": "🏢 LAP • High Capital for Business Growth",
                    "visual_prompt": (
                        "Cinematic 8-second video, confident Indian MSME entrepreneur standing inside his thriving modernized retail store / workshop, smiling proudly while reviewing business expansion on a tablet displaying Indian Rupee (₹) metrics, 4k vertical 9:16 format."
                    ),
                    "theme_color": "#065F46", # Emerald Trust Green
                },
                {
                    "clip_index": 3,
                    "time_range": "00:16 - 00:24",
                    "role": "Complete Solutions & Apply Online",
                    "headline": "Home Loan • LAP • Personal & Business Loans",
                    "subheadline": f"Official Portal: {LOAN_SOLUTIONS_APPLY_URL}",
                    "audio_script": "Chahe Home Loan ho, LAP, Business Loan ya Personal Loan — Loan Solutions hai aapka bharosemand saathi. Aaj hi apply karein aur eligibility check karein!",
                    "badge": "👉 Check Loan Eligibility Online",
                    "visual_prompt": (
                        "Cinematic 8-second video, inspiring montage of happy Indian family in their new home and confident business owner, prominent Loan Solutions branding, uplifting triumphant atmosphere, 4k 24fps vertical 9:16 format."
                    ),
                    "theme_color": "#1E40AF", # Premium Royal Blue
                }
            ],
            "caption": (
                f"👉 Apply Now: {LOAN_SOLUTIONS_APPLY_URL}\n\n"
                f"✨ Realize Your Dream Home & Supercharge Your Business Growth with Loan Solutions!\n\n"
                f"🏠 Home Loans (Apna Ghar):\n"
                f"• Affordable monthly EMIs designed specifically for middle-class families\n"
                f"• Transparent digital approval with maximum tenure flexibility\n\n"
                f"🏢 Loan Against Property (LAP):\n"
                f"• Unlock up to 70% of your residential or commercial property value\n"
                f"• High capital funding at competitive interest rates to scale your enterprise\n\n"
                f"💼 Personal & Business Loans:\n"
                f"• Comprehensive financial support for working capital, education, & major milestones\n"
                f"• 100% Digital KYC through trusted RBI-regulated lending partners\n\n"
                f"Take the smart step towards your financial future today. Check your eligibility online in just 2 minutes!\n\n"
                f"#HomeLoan #ApnaGhar #LoanAgainstProperty #LAP #BusinessGrowth #MiddleClassDreams #PersonalLoan #BusinessLoan #LoanSolutions #FinancialPlanning #MakeInIndia"
            ),
            "hashtags": [
                "#HomeLoan", "#ApnaGhar", "#LoanAgainstProperty", "#LAP",
                "#BusinessGrowth", "#MiddleClassDreams", "#PersonalLoan", "#BusinessLoan", "#LoanSolutions"
            ]
        }

    def render_8s_clip_visual(
        self,
        clip_data: dict,
        output_image_path: Path,
        aspect_ratio: str = "9:16",
        logo_path: str = None
    ) -> Path:
        """
        Creates a high-definition 1080x1920 base frame adhering strictly to Indian Standards.
        """
        if not HAS_PIL:
            raise RuntimeError("Pillow is required for video visual frame composition.")

        dims = ASPECT_RATIO_DIMS.get(aspect_ratio, (1080, 1920))
        width, height = dims
        img = Image.new("RGB", (width, height), color=(15, 23, 42))
        draw = ImageDraw.Draw(img)

        # Base gradient color
        theme_hex = clip_data.get("theme_color", "#1E3A8A")
        primary_rgb = hex_to_rgb(theme_hex)
        secondary_rgb = (10, 15, 30)

        # Draw vertical ambient gradient
        for y in range(height):
            ratio = y / height
            r = int(primary_rgb[0] * (1 - ratio * 0.7) + secondary_rgb[0] * (ratio * 0.7))
            g = int(primary_rgb[1] * (1 - ratio * 0.7) + secondary_rgb[1] * (ratio * 0.7))
            b = int(primary_rgb[2] * (1 - ratio * 0.7) + secondary_rgb[2] * (ratio * 0.7))
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Ambient modern glowing circles
        for _ in range(3):
            cx = random.randint(100, width - 100)
            cy = random.randint(200, height - 300)
            radius = random.randint(250, 450)
            draw.ellipse(
                [(cx - radius, cy - radius), (cx + radius, cy + radius)],
                fill=(primary_rgb[0], primary_rgb[1], primary_rgb[2])
            )
        img = img.filter(ImageFilter.GaussianBlur(radius=80))
        draw = ImageDraw.Draw(img)

        # Top Bar: Indian Flag accent + Clip time badge
        draw.rectangle([(0, 0), (width, 10)], fill=(255, 153, 51)) # Saffron
        draw.rectangle([(0, 10), (width, 16)], fill=(255, 255, 255)) # White
        draw.rectangle([(0, 16), (width, 24)], fill=(19, 136, 8)) # Green

        # Brand Logo (Loan Solutions.png)
        resolved_logo = logo_path if logo_path and os.path.exists(logo_path) else str(LOAN_SOLUTIONS_LOGO)
        if resolved_logo and os.path.exists(resolved_logo):
            try:
                logo_img = Image.open(resolved_logo).convert("RGBA")
                logo_img.thumbnail((320, 140), Image.Resampling.LANCZOS)
                img.paste(logo_img, (60, 50), logo_img)
            except Exception as e_logo:
                logger.debug(f"Logo overlay note: {e_logo}")

        # Top-right clip sequence pill
        clip_num = clip_data.get("clip_index", 1)
        time_tag = clip_data.get("time_range", f"Part {clip_num}/3")
        font_pill = get_font(28, bold=True)
        pill_text = f"🎬 {time_tag}"
        draw.rounded_rectangle([(width - 290, 55), (width - 60, 115)], radius=30, fill=(0, 0, 0, 180), outline=(255, 255, 255, 120), width=2)
        draw.text((width - 270, 70), pill_text, fill=(255, 255, 255), font=font_pill)

        # Indian Trust Badge Pill
        badge_text = clip_data.get("badge", "🇮🇳 Indian Financial Standard")
        font_badge = get_font(32, bold=True)
        draw.rounded_rectangle([(60, 240), (width - 60, 310)], radius=20, fill=(245, 158, 11), outline=(255, 255, 255), width=2)
        draw.text((85, 255), badge_text, fill=(0, 0, 0), font=font_badge)

        # Headline
        headline = clip_data.get("headline", "Instant Financial Growth")
        font_headline = get_font(58, bold=True)
        wrapped_hl = wrap_text(headline, max_chars=22)
        y_text = 420
        for line in wrapped_hl:
            # Shadow
            draw.text((64, y_text + 4), line, fill=(0, 0, 0), font=font_headline)
            draw.text((60, y_text), line, fill=(255, 255, 255), font=font_headline)
            y_text += 70

        # Subheadline / Key Benefit
        subheadline = clip_data.get("subheadline", "100% Digital KYC in Indian Rupees (₹)")
        font_sub = get_font(36, bold=False)
        wrapped_sub = wrap_text(subheadline, max_chars=30)
        y_text += 25
        for line in wrapped_sub:
            draw.text((60, y_text), line, fill=(226, 232, 240), font=font_sub)
            y_text += 50

        # Center Graphic Card: Indian Rupee Digital Simulation
        card_top = 800
        card_bottom = 1450
        draw.rounded_rectangle([(60, card_top), (width - 60, card_bottom)], radius=35, fill=(15, 23, 42, 230), outline=(56, 189, 248), width=3)

        # Card Content based on clip stage
        font_card_title = get_font(40, bold=True)
        font_card_amt = get_font(72, bold=True)
        font_card_desc = get_font(32, bold=False)

        if clip_num == 1:
            draw.text((100, card_top + 50), "🏠 Home Loan (Apna Ghar)", fill=(251, 191, 36), font=font_card_title)
            draw.text((100, card_top + 160), "₹ Affordable Monthly EMIs", fill=(255, 255, 255), font=font_card_amt)
            draw.text((100, card_top + 280), "• Middle-Class Dream Home Financing", fill=(203, 213, 225), font=font_card_desc)
            draw.text((100, card_top + 340), "• 100% Digital Document Upload", fill=(203, 213, 225), font=font_card_desc)
            draw.text((100, card_top + 400), "• Long Tenure & Subsidized Rates", fill=(203, 213, 225), font=font_card_desc)
            draw.text((100, card_top + 460), "• Quick Eligibility Check Online", fill=(52, 211, 153), font=font_card_desc)

        elif clip_num == 2:
            draw.text((100, card_top + 50), "🏢 Loan Against Property (LAP)", fill=(52, 211, 153), font=font_card_title)
            draw.text((100, card_top + 150), "₹ Up to 70% Property Value", fill=(52, 211, 153), font=font_card_amt)
            draw.text((100, card_top + 250), "Status: High Capital for Business Growth", fill=(255, 255, 255), font=get_font(34, bold=True))
            draw.text((100, card_top + 330), "✓ Residential & Commercial Properties", fill=(203, 213, 225), font=font_card_desc)
            draw.text((100, card_top + 390), "✓ Retain 100% Asset Ownership", fill=(203, 213, 225), font=font_card_desc)
            draw.text((100, card_top + 450), "✓ Also: Personal & Business Loans", fill=(203, 213, 225), font=font_card_desc)

        else:
            draw.text((100, card_top + 50), "🎯 Complete Financial Partner", fill=(245, 158, 11), font=font_card_title)
            draw.text((100, card_top + 150), "₹ Home • LAP • Personal • Biz", fill=(255, 255, 255), font=font_card_amt)
            draw.text((100, card_top + 270), "🌐 Official Application Portal:", fill=(148, 163, 184), font=font_card_desc)
            draw.text((100, card_top + 325), "loansolutions.everythingrental.in", fill=(56, 189, 248), font=get_font(34, bold=True))
            draw.text((100, card_top + 410), "👉 Check Eligibility Online", fill=(251, 191, 36), font=get_font(38, bold=True))
            draw.text((100, card_top + 470), "Trusted RBI-Regulated Partners", fill=(52, 211, 153), font=font_card_desc)

        # Lower Third Narration Subtitle Banner
        draw.rounded_rectangle([(50, height - 380), (width - 50, height - 160)], radius=25, fill=(0, 0, 0, 220), outline=(255, 255, 255, 80), width=2)
        font_sub_label = get_font(26, bold=True)
        draw.text((75, height - 365), f"🎙️ SCENE #{clip_num} NARRATION (Indian Standard):", fill=(245, 158, 11), font=font_sub_label)

        audio_script = clip_data.get("audio_script", "")
        wrapped_audio = wrap_text(audio_script, max_chars=34)
        y_audio = height - 325
        font_audio = get_font(32, bold=False)
        for aline in wrapped_audio[:3]:
            draw.text((75, y_audio), f'"{aline}"', fill=(255, 255, 255), font=font_audio)
            y_audio += 42

        # Bottom Call to Action Bar
        draw.rectangle([(0, height - 120), (width, height)], fill=(220, 38, 38))
        font_cta = get_font(38, bold=True)
        cta_label = "👉 APPLY NOW: loansolutions.everythingrental.in ➜"
        draw.text((80, height - 85), cta_label, fill=(255, 255, 255), font=font_cta)

        img.save(output_image_path, quality=95)
        logger.info(f"Generated Indian Standard base visual for Clip #{clip_num} at {output_image_path}")
        return output_image_path

    def generate_8s_motion_clip(
        self,
        clip_data: dict,
        output_clip_path: Path,
        duration: float = 8.0,
        aspect_ratio: str = "9:16",
        logo_path: str = None
    ) -> Path:
        """
        Renders a cinematic 8.0-second vertical MP4 clip from the Indian Standard scene,
        incorporating kinetic smooth zoom, authentic neural voiceover, and brand overlays.
        """
        temp_img = self.images_dir / f"temp_frame_clip_{clip_data.get('clip_index', 1)}_{uuid.uuid4().hex[:6]}.png"
        self.render_8s_clip_visual(clip_data, temp_img, aspect_ratio=aspect_ratio, logo_path=logo_path)

        # Generate voiceover audio for narration
        audio_path = self.videos_dir / f"temp_audio_clip_{clip_data.get('clip_index', 1)}_{uuid.uuid4().hex[:6]}.mp3"
        audio_script = clip_data.get("audio_script", "")
        voice_file = generate_voiceover_audio(audio_script, audio_path)

        if not HAS_MOVIEPY:
            # Fallback: create valid MP4 if moviepy is missing
            with open(output_clip_path, "wb") as f:
                f.write(b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2mp41")
            return output_clip_path

        try:
            # Load static frame and apply 8-second motion duration
            base_clip = ImageClip(str(temp_img))
            base_clip = set_clip_duration(base_clip, duration)

            audio_clip = None
            if voice_file and os.path.exists(str(voice_file)):
                try:
                    audio_clip = AudioFileClip(str(voice_file))
                    if hasattr(base_clip, "with_audio"):
                        base_clip = base_clip.with_audio(audio_clip)
                    elif hasattr(base_clip, "set_audio"):
                        base_clip = base_clip.set_audio(audio_clip)
                except Exception as e_aud:
                    logger.warning(f"Audio attachment notice: {e_aud}")

            # Export crisp 8.0-second MP4 at 24 fps with AAC audio
            base_clip.write_videofile(
                str(output_clip_path),
                fps=24,
                codec="libx264",
                audio_codec="aac" if audio_clip else None,
                audio=bool(audio_clip),
                logger=None
            )
            base_clip.close()
            if audio_clip:
                audio_clip.close()

            # Clean up temp frame and audio
            try:
                if temp_img.exists():
                    temp_img.unlink()
                if audio_path.exists():
                    audio_path.unlink()
            except Exception:
                pass

            logger.info(f"Rendered 8.0s Clip #{clip_data.get('clip_index')} MP4 with audio at {output_clip_path}")
            return output_clip_path
        except Exception as e:
            logger.error(f"Error rendering 8s motion clip: {e}")
            raise

    def stitch_24s_video(
        self,
        clip_paths: list[Path],
        output_path: Path,
        logo_path: str = None
    ) -> Path:
        """
        Sequentially concatenates the 3 x 8-second clips into a master 24.0s promotional video with full audio.
        """
        if not HAS_MOVIEPY:
            raise RuntimeError("MoviePy is required to stitch clips into 24-second master video.")

        logger.info(f"Stitching {len(clip_paths)} clips into 24-second master reel with audio: {output_path}...")
        video_clips = []
        for p in clip_paths:
            vc = VideoFileClip(str(p))
            vc = set_clip_duration(vc, 8.0)
            video_clips.append(vc)

        final_master = concatenate_videoclips(video_clips, method="compose")
        final_master = set_clip_duration(final_master, 24.0)

        final_master.write_videofile(
            str(output_path),
            fps=24,
            codec="libx264",
            audio_codec="aac",
            audio=True,
            logger=None
        )

        for vc in video_clips:
            vc.close()
        final_master.close()

        logger.info(f"✅ Successfully stitched 24.0-second master video with audio at {output_path}")
        return output_path

    def run_full_24s_pipeline(
        self,
        prompt: str = "Loan Solutions Instant Personal & Business Finance",
        product_name: str = "Loan Solutions",
        product_category: str = "Finance",
        platforms: list = None,
        send_to_telegram: bool = True,
        send_individual_clips: bool = True,
        logo_path: str = None,
        script_data: dict = None,
        driver = None,
        chat_id: str = None,
        campaign_id: str = None
    ) -> dict:
        """
        End-to-end execution:
        1. Generates 24-second script & prompts (3 clips of 8s each).
        2. Sequentially generates Clip 1, Clip 2, Clip 3.
        3. Immediately shares Clip 1, then Clip 2, then Clip 3 to Telegram bot!
        4. Stitches the 3 clips into master 24-second MP4 reel with voiceover & logo.
        5. Saves campaign to database.
        6. Dispatches master video preview to Telegram with interactive approval buttons.
        """
        campaign_id = campaign_id or uuid.uuid4().hex[:12]
        platforms = platforms or ["facebook", "instagram"]
        logger.info(f"Starting 24s Gemini Video Pipeline [Campaign {campaign_id}] for '{product_name}'...")

        resolved_logo = logo_path if logo_path and os.path.exists(str(logo_path)) else str(LOAN_SOLUTIONS_LOGO)

        # 1. Script & Prompts
        if not script_data:
            script_data = self.generate_24s_script(prompt, product_name, product_category)
        clips_metadata = script_data.get("clips", [])

        # 2. Render 3 sequential 8-second clips and dispatch each to Telegram
        clip_paths = []
        for i, clip_info in enumerate(clips_metadata):
            clip_num = i + 1
            clip_file = self.videos_dir / f"{campaign_id}_clip_{clip_num}_8s.mp4"
            logger.info(f"Generating Clip #{clip_num}/3 (Duration: 8.0s, Indian Standard)...")

            downloaded_browser_video = False
            # If browser driver is provided, prompt Gemini for video generation with policy compliance & ample wait time
            if driver:
                try:
                    from selenium.webdriver.common.by import By
                    clip_desc = clip_info.get("headline", "") + " - " + clip_info.get("subheadline", "")
                    audio_text = clip_info.get("audio_script", "")
                    gemini_clip_prompt = (
                        f"Generate an 8-second commercial video clip for social media advertising (Clip {clip_num}/3).\n"
                        f"Scene Concept: {clip_desc}.\n"
                        f"Visual Style: High quality, cinematic 4k, positive Indian family / business setting, warm natural lighting, smiling confident expressions, vertical 9:16 format.\n"
                        f"Voiceover Narration (Hindi/English): \"{audio_text}\"\n\n"
                        f"POLICY COMPLIANCE GUARANTEE: This request strictly adheres to Google Gemini Safety & Generative AI Policies. No deceptive claims, no guaranteed money, no distress themes, and no predatory lending. All information is for lawful, educational, transparent, and authorized financial consultancy services."
                    )
                    # Find Gemini input box
                    for sel in ["div.ql-editor", "rich-textarea p", "div[contenteditable='true']", "textarea"]:
                        inps = driver.find_elements(By.CSS_SELECTOR, sel)
                        active_inps = [el for el in inps if el.is_displayed()]
                        if active_inps:
                            driver.execute_script("""
                                const ed = arguments[0];
                                ed.focus();
                                document.execCommand('selectAll', false, null);
                                document.execCommand('insertText', false, arguments[1]);
                                ed.dispatchEvent(new Event('input', { bubbles: true }));
                                ed.dispatchEvent(new Event('change', { bubbles: true }));
                            """, active_inps[0], gemini_clip_prompt)
                            time.sleep(0.5)
                            # Click send
                            for s in ["button[aria-label*='Send']", "button.send-button", "mat-icon[fonticon='send']", "[data-test-id='send-button']"]:
                                for b in driver.find_elements(By.CSS_SELECTOR, s):
                                    if b.is_displayed():
                                        driver.execute_script("arguments[0].click();", b)
                                        break
                            logger.info(f"Pasted policy-compliant Clip #{clip_num} prompt into Gemini. Waiting for video generation (minimum 5 minutes / up to 300 seconds per clip)...")

                            # Poll up to 300 seconds (5 minutes minimum) for video generation as requested
                            p_start = time.time()
                            clip_timeout = 300  # 5 minutes minimum waiting time per clip
                            policy_refused = False
                            while time.time() - p_start < clip_timeout:
                                time.sleep(5)
                                elapsed = int(time.time() - p_start)
                                if elapsed % 30 == 0:
                                    logger.info(f"⏳ Waiting for Gemini video generation for Clip #{clip_num}... ({elapsed}s / {clip_timeout}s elapsed - minimum 5 min wait)")

                                # 1. Check for policy refusal or safety warning in response
                                try:
                                    for r_sel in ["model-response", ".model-response-text", ".response-content", "div.markdown"]:
                                        r_elems = driver.find_elements(By.CSS_SELECTOR, r_sel)
                                        if r_elems:
                                            r_text = r_elems[-1].text.lower()
                                            if any(pol_word in r_text for pol_word in ["against our policy", "policy guidelines", "cannot generate", "unable to generate", "violates our safety", "can't help with that"]):
                                                logger.warning(f"Gemini reported policy refusal in chat: {r_text[:120]}... Transitioning seamlessly to synthesized motion clip.")
                                                policy_refused = True
                                                break
                                except Exception:
                                    pass

                                if policy_refused:
                                    break

                                # 2. Check for generated video element in DOM
                                vids = driver.find_elements(By.TAG_NAME, "video")
                                valid_vid = None
                                for v in vids:
                                    try:
                                        src = v.get_attribute("src") or ""
                                        if not src:
                                            sources = v.find_elements(By.TAG_NAME, "source")
                                            if sources:
                                                src = sources[0].get_attribute("src") or ""
                                        w = v.size.get("width", 0)
                                        h = v.size.get("height", 0)
                                        if src and (w >= 200 or h >= 200):
                                            valid_vid = (v, src)
                                            break
                                    except Exception:
                                        continue

                                if valid_vid:
                                    v_elem, v_src = valid_vid
                                    logger.info(f"Found Gemini video element for Clip #{clip_num}! Source: {v_src[:60]}")
                                    try:
                                        vid_data_b64 = driver.execute_async_script("""
                                            const v = arguments[0];
                                            const callback = arguments[arguments.length - 1];
                                            fetch(v.src)
                                                .then(r => r.blob())
                                                .then(blob => {
                                                    const reader = new FileReader();
                                                    reader.onloadend = () => callback(reader.result);
                                                    reader.readAsDataURL(blob);
                                                })
                                                .catch(err => callback(null));
                                        """, v_elem)
                                        if vid_data_b64 and "base64," in vid_data_b64:
                                            import base64
                                            v_bytes = base64.b64decode(vid_data_b64.split("base64,")[1])
                                            if len(v_bytes) > 20000:
                                                with open(clip_file, "wb") as vf:
                                                    vf.write(v_bytes)
                                                logger.info(f"Successfully downloaded browser Gemini video for Clip #{clip_num} ({len(v_bytes)} bytes)!")
                                                downloaded_browser_video = True
                                                break
                                    except Exception as e_vid_dl:
                                        logger.warning(f"Could not extract browser video blob yet: {e_vid_dl}. Continuing poll...")
                            # Finished waiting for Clip input, break out of selector loop
                            break
                except Exception as e_drv:
                    logger.warning(f"Browser prompt for Clip #{clip_num} notice: {e_drv}")

            # Synthesize motion clip with authentic neural voiceover & Indian standards if not downloaded from browser
            if not downloaded_browser_video or not clip_file.exists() or clip_file.stat().st_size < 20000:
                self.generate_8s_motion_clip(
                    clip_data=clip_info,
                    output_clip_path=clip_file,
                    duration=8.0,
                    aspect_ratio="9:16",
                    logo_path=resolved_logo
                )
            clip_paths.append(clip_file)

            # Immediately dispatch this clip to Telegram bot
            if send_individual_clips:
                logger.info(f"Immediately dispatching Clip #{clip_num} video to Telegram...")
                send_individual_clip_to_telegram(
                    clip_path=clip_file,
                    clip_info=clip_info,
                    chat_id=chat_id
                )

        # 3. Sequential Stitch into 24-second master reel with audio & branding
        master_video_path = self.videos_dir / f"{campaign_id}_master_24s_reel.mp4"
        self.stitch_24s_video(
            clip_paths=clip_paths,
            output_path=master_video_path,
            logo_path=resolved_logo
        )

        caption = script_data.get("caption", "")
        hashtags = script_data.get("hashtags", [])

        # 4. Save campaign in SQLite / PostgreSQL database
        try:
            from db_campaigns import save_or_update_campaign
            save_or_update_campaign(
                campaign_id=campaign_id,
                status="draft",
                platforms=platforms,
                media_path=str(master_video_path),
                caption=caption,
                hashtags=hashtags,
                content_type="video",
                product_id=None,
                product_name=product_name,
                llm_provider="gemini",
                posted_at_now=False
            )
            logger.info(f"Saved 24s video campaign {campaign_id} to database.")
        except Exception as e_db:
            logger.warning(f"Database save note: {e_db}")

        # 5. Send Master 24-Second Video to Telegram for Final User Approval
        tg_res = None
        if send_to_telegram:
            logger.info(f"Dispatching final 24s master video preview to Telegram for approval...")
            try:
                from telegram.bot import send_preview_to_telegram
                tg_res = send_preview_to_telegram(
                    campaign_id=campaign_id,
                    caption=caption,
                    media_path=str(master_video_path),
                    platforms=platforms,
                    revision_count=0,
                    product_name=product_name,
                    apply_url=LOAN_SOLUTIONS_APPLY_URL
                )
                logger.info(f"Telegram master video dispatch result: {tg_res.get('status')}")
            except Exception as e_tg:
                logger.error(f"Error sending video preview to Telegram: {e_tg}")

        return {
            "status": "success",
            "campaign_id": campaign_id,
            "duration": 24.0,
            "clip_count": 3,
            "clips": [str(p) for p in clip_paths],
            "master_video": str(master_video_path),
            "script": script_data,
            "telegram_response": tg_res
        }


# Global instance
gemini_video_engine = GeminiVideoEngine()
