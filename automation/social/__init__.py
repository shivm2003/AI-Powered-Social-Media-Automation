"""
Social media publishing package.
Dispatches posts across Facebook, Instagram, LinkedIn, and WhatsApp.
"""
import logging
from .facebook import post_to_facebook
from .instagram import post_to_instagram
from .linkedin import post_to_linkedin
from .whatsapp import post_to_whatsapp

logger = logging.getLogger("automation.social")

POSTERS = {
    "facebook": post_to_facebook,
    "instagram": post_to_instagram,
    "linkedin": post_to_linkedin,
    "whatsapp": post_to_whatsapp,
}


def publish_to_platform(platform: str, media_path: str = None, caption: str = "") -> dict:
    """Dispatches post to a specific platform."""
    poster = POSTERS.get(platform.lower())
    if not poster:
        raise ValueError(f"Unsupported social platform: {platform}")
    logger.info(f"Publishing to {platform}...")
    return poster(media_path=media_path, caption=caption)


def publish_to_all_platforms(platforms: list, media_path: str = None, caption: str = "") -> dict:
    """Publishes content across multiple selected platforms."""
    results = {}
    for p in platforms:
        try:
            results[p] = publish_to_platform(p, media_path=media_path, caption=caption)
        except Exception as e:
            results[p] = {"status": "error", "message": str(e)}
    return results
