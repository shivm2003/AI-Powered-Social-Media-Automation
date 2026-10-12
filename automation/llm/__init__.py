"""
Unified LLM orchestrator.
Supports Gemini, ChatGPT, and Claude with smart synthesis and fallback.
"""
import json
import logging
from .prompts import build_social_prompt
from .gemini import generate_with_gemini_browser
from .chatgpt import generate_with_chatgpt_browser
from .claude import generate_with_claude_browser

logger = logging.getLogger("automation.llm")


def extract_json_or_fallback(raw_text: str, default_data: dict) -> dict:
    """Tries to extract JSON object from raw response text."""
    try:
        # Check if wrapped in ```json ... ```
        clean_text = raw_text.strip()
        if "```json" in clean_text:
            clean_text = clean_text.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_text:
            clean_text = clean_text.split("```")[1].split("```")[0].strip()

        # Find first { and last }
        start = clean_text.find("{")
        end = clean_text.rfind("}")
        if start != -1 and end != -1:
            return json.loads(clean_text[start : end + 1])
    except Exception as e:
        logger.warning(f"Could not parse JSON from LLM response: {e}")
    return default_data


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
    """
    platforms = platforms or ["facebook", "instagram"]
    product_name = product.get("name", "Innovative Product")
    desc = product.get("description", "Premium quality solution designed for your success.")
    category = product.get("category", "Product")
    audience = product.get("target_audience", "Savvy professionals and creators")
    benefits = product.get("key_benefits", ["Save 10x time", "Increase efficiency", "Top-tier quality"])
    if isinstance(benefits, str):
        try:
            benefits = json.loads(benefits)
        except Exception:
            benefits = [b.strip() for b in benefits.split(",") if b.strip()]

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

    # Standard high-quality fallback template
    benefits_bullet_points = "\n".join([f"✨ {b}" for b in benefits[:4]])
    fallback_data = {
        "caption": f"🚀 Ready to level up with {product_name}?\n\n{desc}\n\nKey Highlights:\n{benefits_bullet_points}\n\n👉 Click the link in bio to learn more and claim your exclusive offer today!",
        "short_caption": f"Supercharge your workflow with {product_name}. Check it out now! 🚀",
        "hashtags": [
            f"#{product_name.replace(' ', '')}",
            "#Innovation",
            "#Productivity",
            "#TechTrends",
            "#SocialMarketing",
            "#Growth"
        ],
        "headline": f"Discover {product_name}",
        "subheadline": "The Ultimate Solution Built For Your Growth",
        "visual_prompt": f"Modern minimalist product hero shot of {product_name}, vibrant dynamic lighting, cinematic depth of field, sleek aesthetic, high-res commercial photography.",
        "video_script_slides": [
            {"slide": 1, "text": f"Struggling to scale efficiently?", "visual": "Problem visualization"},
            {"slide": 2, "text": f"Meet {product_name}.", "visual": "Hero reveal with dramatic lighting"},
            {"slide": 3, "text": f"{benefits[0] if benefits else 'Faster results'}", "visual": "Feature highlight with animated motion graphics"},
            {"slide": 4, "text": "Get started today — link in bio!", "visual": "Branded logo and clear call-to-action"}
        ]
    }

    # Attempt browser-based LLM generation if configured
    try:
        provider_lower = (provider or "gemini").lower()
        logger.info(f"Generating marketing content with {provider_lower} browser...")

        raw_output = None
        if provider_lower == "gemini":
            raw_output = generate_with_gemini_browser(prompt)
        elif provider_lower == "chatgpt":
            raw_output = generate_with_chatgpt_browser(prompt)
        elif provider_lower == "claude":
            raw_output = generate_with_claude_browser(prompt)

        if raw_output:
            parsed = extract_json_or_fallback(raw_output, fallback_data)
            return parsed
    except Exception as e:
        logger.info(f"Using built-in marketing generator engine: {e}")

    return fallback_data
