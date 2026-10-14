"""
AI Social Media Automation — Configuration
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env.local")
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

# Direct fallback parser for .env.local and .env
for env_name in [".env.local", ".env"]:
    env_file = BASE_DIR / env_name
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k not in os.environ:
                        os.environ[k] = v
        except Exception:
            pass

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Chrome profiles directory
CHROME_PROFILES_DIR = BASE_DIR / "chrome_profiles"

# Media output directory
MEDIA_OUTPUT_DIR = BASE_DIR / "data" / "media"
IMAGES_DIR = MEDIA_OUTPUT_DIR / "images"
VIDEOS_DIR = MEDIA_OUTPUT_DIR / "videos"

# Database path
DATABASE_PATH = BASE_DIR / "data" / "database.sqlite"

# Logs directory
LOGS_DIR = BASE_DIR / "logs"

# Create directories if they don't exist
for directory in [CHROME_PROFILES_DIR, IMAGES_DIR, VIDEOS_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Platform Chrome profile paths
PLATFORM_PROFILES = {
    "facebook": CHROME_PROFILES_DIR / "facebook",
    "instagram": CHROME_PROFILES_DIR / "instagram",
    "linkedin": CHROME_PROFILES_DIR / "linkedin",
    "whatsapp": CHROME_PROFILES_DIR / "whatsapp",
    "gemini": CHROME_PROFILES_DIR / "gemini",
    "chatgpt": CHROME_PROFILES_DIR / "chatgpt",
    "claude": CHROME_PROFILES_DIR / "claude",
}

# Platform URLs
PLATFORM_URLS = {
    "facebook": "https://www.facebook.com",
    "instagram": "https://www.instagram.com",
    "linkedin": "https://www.linkedin.com",
    "whatsapp": "https://web.whatsapp.com",
    "gemini": "https://gemini.google.com",
    "chatgpt": "https://chatgpt.com",
    "claude": "https://claude.ai",
}

# Browser settings
CHROME_OPTIONS = {
    "headless": False,  # Must be visible for MFA and login
    "window_size": (1366, 768),
    "user_agent": None,  # Let undetected-chromedriver handle this
}

# Timeouts (seconds)
TIMEOUTS = {
    "page_load": 30,
    "element_wait": 15,
    "llm_response": 120,  # LLMs can take a while
    "upload": 60,
    "post_confirm": 30,
}

# Human-like delay range (min, max) in seconds
HUMAN_DELAY = {
    "typing": (0.03, 0.08),  # Between keystrokes
    "action": (0.5, 2.0),    # Between actions
    "page": (2.0, 5.0),      # After page load
}
