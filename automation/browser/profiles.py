"""
Chrome Profiles Management.
Manages persistent browser profiles per platform so that users log in and complete MFA
only once, and all subsequent sessions reuse the saved state.
"""
from pathlib import Path
import logging
from config import PLATFORM_PROFILES, PLATFORM_URLS

logger = logging.getLogger("automation.profiles")


def get_profile_dir(platform: str) -> Path:
    """Get the profile directory for a given platform and ensure it exists."""
    profile_dir = PLATFORM_PROFILES.get(platform.lower())
    if not profile_dir:
        raise ValueError(f"Unknown platform: {platform}")
    profile_dir.mkdir(parents=True, exist_ok=True)
    return profile_dir


def is_profile_initialized(platform: str) -> bool:
    """Check if the platform profile directory contains Chrome session data."""
    profile_dir = PLATFORM_PROFILES.get(platform.lower())
    if not profile_dir or not profile_dir.exists():
        return False
    # Check for Default profile directory or Network/Cookies file
    default_dir = profile_dir / "Default"
    if default_dir.exists():
        cookies_file = default_dir / "Network" / "Cookies"
        preferences = default_dir / "Preferences"
        return cookies_file.exists() or preferences.exists()
    return False


def get_target_url(platform: str) -> str:
    """Get the default login/home URL for a platform."""
    return PLATFORM_URLS.get(platform.lower(), "https://www.google.com")
