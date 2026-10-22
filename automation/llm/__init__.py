"""
Unified LLM orchestrator.
Supports Gemini API, OpenAI API, active browser automation (port 9222), and ultra-fast dynamic marketing copy synthesis.
"""
import os
import json
import logging
import urllib.request
import urllib.parse
from .prompts import build_social_prompt
from browser.driver import is_debugging_port_open

logger = logging.getLogger("automation.llm")


def extract_json_or_fallback(raw_text: str, default_data: dict) -> dict:
    """Tries to extract JSON object from raw response text."""
    try:
        clean_text = raw_text.strip()
        if "```json" in clean_text:
            clean_text = clean_text.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_text:
            clean_text = clean_text.split("```")[1].split("```")[0].strip()

        start = clean_text.find("{")
        end = clean_text.rfind("}")
        if start != -1 and end != -1:
            return json.loads(clean_text[start : end + 1])
    except Exception as e:
        logger.warning(f"Could not parse JSON from LLM response: {e}")
    return default_data


def generate_with_gemini_api(prompt: str, api_key: str) -> str:
    """Direct Google Gemini REST API call for instant, high-quality generation."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024}
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=15) as res:
        res_json = json.loads(res.read().decode("utf-8"))
        candidates = res_json.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "")
    return ""


def generate_smart_marketing_copy(
    product_name: str,
    desc: str,
    category: str,
    audience: str,
    benefits: list,
    tone: str,
    language: str,
    cta: str,
    platforms: list
) -> dict:
    """Generates rich, tailored, viral marketing copy dynamically in milliseconds."""
    cta_labels = {
        "learn_more": "Learn More & Get Started",
        "shop_now": "Shop Now — Limited Time Offer",
        "sign_up": "Sign Up Free Today",
        "contact_us": "Contact Our Team Today",
        "book_demo": "Book a Free 1-on-1 Demo",
        "get_offer": "Claim Your Exclusive Offer Now",
        "download": "Download Today for Free",
    }
    action_cta = cta_labels.get(cta, "Discover More Today")

    # Hashtags with Indian market relevance and algorithmic virality
    clean_name = "".join(ch for ch in product_name.title() if ch.isalnum())
    clean_cat = "".join(ch for ch in category.title() if ch.isalnum())
    is_finance = "loan" in product_name.lower() or "loan" in desc.lower() or "finance" in category.lower()
    
    from social.trending_hashtags import get_fresh_trending_hashtags
    hashtags = get_fresh_trending_hashtags(
        platform="instagram",
        category="finance" if is_finance else "general"
    )

    if is_finance:
        default_bullets = (
            "✅ Fast Disbursal directly to bank account\n"
            "✅ Easy EMIs starting at low monthly rates in ₹\n"
            "✅ Minimal paperwork & zero hidden charges\n"
            "✅ Trusted financial partner for your family's dreams"
        )
    else:
        default_bullets = f"✅ Fast & reliable\n✅ Designed for {audience or 'Indian families'}\n✅ 100% transparent and hassle-free experience"

    # Benefits formatted
    bullet_points = ""
    if benefits and len(benefits) > 0:
        bullet_points = "\n".join([f"✅ {b}" for b in benefits[:4]])
    else:
        bullet_points = default_bullets

    # Tone adjustments for Indian middle-class audience
    if is_finance:
        if tone.lower() == "urgency":
            hook = f"⏳ Don't let financial worries pause your dreams! Secure easy loans with {product_name} today."
        elif tone.lower() == "inspirational":
            hook = f"✨ Apne sapno ko dein ek nayi udaan! Turn every family aspiration into reality with {product_name}."
        elif tone.lower() == "casual":
            hook = f"👋 Need quick funds with low monthly EMIs? {product_name} makes borrowing completely hassle-free!"
        else:
            hook = f"🏡 Ab har sapna hoga poora — Quick, transparent, and trusted financial solutions with {product_name}!"
    else:
        if tone.lower() == "urgency":
            hook = f"⏳ Don't wait! Transform your results with {product_name} today."
        elif tone.lower() == "inspirational":
            hook = f"✨ Unlock your family's full potential with {product_name}."
        elif tone.lower() == "casual":
            hook = f"👋 Check this out — {product_name} is a game changer for you and your family!"
        else:
            hook = f"🚀 Ready to take the next big step with {product_name}?"

    if is_finance:
        action_cta = "Apply Now"
        cta_line = "👉 Apply Now: https://loansolutions.everythingrental.in/application"
        caption = (
            f"{cta_line}\n\n"
            f"{hook}\n\n"
            f"{desc}\n\n"
            f"Key Highlights:\n"
            f"{bullet_points}\n\n"
            f"{' '.join(hashtags)}"
        )
    else:
        cta_line = f"👉 Click below to {action_cta.lower()}!"
        caption = (
            f"{hook}\n\n"
            f"{desc}\n\n"
            f"Key Highlights:\n"
            f"{bullet_points}\n\n"
            f"{cta_line}\n\n"
            f"{' '.join(hashtags)}"
        )

    if is_finance:
        short_caption = f"Level up with {product_name}! {desc[:80]}... 👉 Apply Now: https://loansolutions.everythingrental.in/application"
    else:
        short_caption = f"Level up with {product_name}! {desc[:80]}... 👉 {action_cta} 🚀"
    headline = f"Apne Sapne Sach Karein — {product_name}" if is_finance else f"Discover {product_name}"
    subheadline = desc[:65] if desc else "Trusted financial solutions for Indian middle-class families."

    video_slides = [
        {"slide": 1, "text": f"Need reliable financial support?", "visual": f"Indian family planning their dreams with {product_name}"},
        {"slide": 2, "text": f"Meet {product_name}", "visual": "Warm home reveal with glowing Indian Rupee (₹) symbol"},
        {"slide": 3, "text": f"{benefits[0] if benefits else 'Low EMIs in ₹ & Fast Disbursal'}", "visual": "Checkmark approval on Indian digital banking screen"},
        {"slide": 4, "text": f"{action_cta}!", "visual": "Logo and clear call to action"}
    ]

    return {
        "caption": caption,
        "short_caption": short_caption,
        "hashtags": hashtags,
        "headline": headline,
        "subheadline": subheadline,
        "visual_prompt": f"A warm, authentic, happy Indian middle-class family celebrating loan approval in a modern Indian living room, glowing Indian Rupee symbol (₹), clean 8k commercial advertising photography.",
        "video_script_slides": video_slides,
    }


def generate_marketing_content(
    product: dict,
    provider: str = "gemini",
    platforms: list = None,
    content_type: str = "image",
    language: str = "english",
    tone: str = "professional",
    cta: str = "learn_more",
    custom_instructions: str = ""
) -> dict:
    """
    Main generator function for captions, hashtags, graphic headlines, and video scripts.
    Guarantees fast, robust delivery without freezing.
    """
    platforms = platforms or ["facebook", "instagram"]
    product_name = (product.get("name") or "Featured Product").strip()
    desc = (product.get("description") or "Premium quality solution designed for your success.").strip()
    category = product.get("category", "Product")
    audience = product.get("target_audience", "Customers and clients")
    benefits = product.get("key_benefits", [])
    if isinstance(benefits, str):
        try:
            benefits = json.loads(benefits)
        except Exception:
            benefits = [b.strip() for b in benefits.split(",") if b.strip()]

    # Baseline rich dynamic content (instant fallback)
    fallback_data = generate_smart_marketing_copy(
        product_name=product_name,
        desc=desc,
        category=category,
        audience=audience,
        benefits=benefits,
        tone=tone,
        language=language,
        cta=cta,
        platforms=platforms
    )

    prompt = build_social_prompt(
        product_name=product_name,
        description=desc,
        category=category,
        target_audience=audience,
        key_benefits=benefits,
        tone=tone,
        language=language,
        cta=cta,
        platforms=platforms,
        content_type=content_type,
        custom_instructions=custom_instructions
    )

    provider_lower = (provider or "gemini").lower()
    raw_output_data = None

    # ── 1. Check for Direct API Keys (super fast, ~1-2s) ──
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if provider_lower == "gemini" and gemini_key:
        try:
            logger.info("Generating marketing content with Google Gemini API...")
            raw_text = generate_with_gemini_api(prompt, gemini_key)
            if raw_text:
                raw_output_data = extract_json_or_fallback(raw_text, fallback_data)
        except Exception as e:
            logger.warning(f"Gemini API request notice: {e}")

    # ── 2. Check browser interaction (port 9222 or dedicated profile) ──
    if not raw_output_data:
        try:
            if is_debugging_port_open(9222) or provider_lower == "chatgpt":
                logger.info(f"Generating content with browser automation ({provider_lower})...")
                raw_output = None
                if provider_lower == "gemini":
                    from .gemini import generate_with_gemini_browser
                    raw_output = generate_with_gemini_browser(prompt)
                elif provider_lower == "chatgpt":
                    from .chatgpt import generate_with_chatgpt_browser
                    raw_output = generate_with_chatgpt_browser(prompt)

                if raw_output:
                    raw_output_data = extract_json_or_fallback(raw_output, fallback_data)
        except Exception as e:
            logger.info(f"Browser interaction note: {e}. Using smart copy synthesizer.")

    final_data = raw_output_data if raw_output_data else fallback_data

    # Guarantee fresh viral hashtags & Line 1 Apply Now link across all generation paths
    is_finance = "loan" in product_name.lower() or "loan" in desc.lower() or "finance" in category.lower()
    from social.trending_hashtags import enrich_caption_with_trending_hashtags
    final_data["caption"] = enrich_caption_with_trending_hashtags(
        final_data.get("caption", ""),
        platform="instagram",
        category="finance" if is_finance else "general"
    )

    if is_finance:
        from social.caption_helper import ensure_apply_now_at_start, LOAN_SOLUTIONS_APPLY_URL
        final_data["caption"] = ensure_apply_now_at_start(
            final_data.get("caption", ""),
            apply_url=LOAN_SOLUTIONS_APPLY_URL,
            is_loan=True
        )

    return final_data


from .prompt_paste_verifier_agent import (
    PromptPasteVerifierAgent,
    prompt_verifier_agent,
    PromptVerificationResult,
)
