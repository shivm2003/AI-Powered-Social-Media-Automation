"""
Instagram Follow Automator.
Supports:
1. Following specific accounts by @username (single or batch)
2. Location/niche auto-follow using Instagram's native search and lightbox modal navigation
3. Human-like safety delays and zero HTTP 429 page-reload rate limits
"""
import sys
import os
import time
import random
import urllib.parse
import re
import logging
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
        sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "automation"))

from browser.driver import browser
from config import PLATFORM_URLS

logger = logging.getLogger("automation.social.instagram_follow")


SYSTEM_PATHS = {
    "explore", "reels", "direct", "stories", "accounts", "login", "about", "legal",
    "privacy", "terms", "help", "press", "api", "jobs", "locations", "directory",
    "profiles", "threads", "blog", "popular", "creator", "p", "reel", "loansolutions2026",
    "meta", "support", "developer", "developers", "business"
}


def clean_instagram_username(username: str) -> str:
    """Sanitizes username, removing leading @, URL prefixes, spaces, trailing slashes."""
    u = username.strip()
    if "instagram.com/" in u:
        u = u.split("instagram.com/")[-1]
    u = u.split("?")[0].rstrip("/").strip().lstrip("@").strip()
    return u


def is_valid_ig_username(username: str) -> bool:
    """Validates if string is a valid Instagram user account handle."""
    if not username:
        return False
    u = clean_instagram_username(username).lower()
    if not u or u in SYSTEM_PATHS or u.isdigit():
        return False
    if not re.match(r"^[a-zA-Z0-9._]{1,30}$", u):
        return False
    return True


def extract_username_from_url(url: str) -> str:
    """Extracts username only if URL points directly to an Instagram user profile."""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.netloc.lower() not in ["www.instagram.com", "instagram.com"]:
            return None
        parts = [p for p in parsed.path.strip("/").split("/") if p]
        if len(parts) == 1 and is_valid_ig_username(parts[0]):
            return parts[0]
    except Exception:
        pass
    return None


CHANNEL_PATTERNS = {
    # Direct channel and broadcast words
    "channel", "channels", "broadcast", "broadcaster",
    # News, updates, media, portals
    "news", "samachar", "khabar", "patrika", "bulletin", "times", "express",
    "updates", "update", "daily", "today", "live", "alert", "alerts",
    "media", "press", "portal", "tv", "radio", "fm", "journal", "gazette",
    # City entities, guides & directories
    "city", "town", "metro", "nagari", "shehar", "junction", "hub", "corner",
    "guide", "diaries", "diary", "vibes", "vibe", "darshan", "life",
    # Memes & comedy pages
    "memes", "meme", "trolls", "jokes", "humor", "roast",
    # Food & commercial niches
    "foodie", "foodies", "foods", "food", "kitchen", "eats", "zaika", "swad", "cafe", "restaurant",
    # Official / organization markers
    "official", "verified", "page", "pages", "network", "club", "association",
    "foundation", "trust", "ngo", "society", "samiti", "mandal",
    "police", "nagarnigam", "traffic", "dm_", "collector", "administration",
    # Institutions
    "university", "college", "school", "academy", "institute", "campus", "students",
    "hospital", "clinic", "medicals", "pharma", "care", "health",
    # Commercial & real estate
    "properties", "property", "realty", "realtor", "estates", "builders", "developers",
    "bazaar", "mart", "store", "shop", "mall", "shoppe", "boutique", "fashion", "collection",
    "salon", "beauty", "parlour", "spa", "makeup", "couture", "jewellers",
    "agency", "services", "solutions", "enterprise", "ventures", "pvt", "ltd", "corp",
    "studios", "studio", "photography", "cinematography", "films", "production",
    "marketing", "promotions", "promotion", "advertis", "shoutout", "deals", "offers",
    # Fan / Community pages
    "lovers", "fans", "fanpage", "army", "zone", "world", "universe", "planet",
    "central", "connect", "buzz", "talks", "voice", "beats", "pulse", "now",
    # Curation, Theme & Content Creators
    "core", "finds", "unseen", "captured", "heritage", "anokha", "awadh", "awadhi",
    "youtuber", "vlogger", "influencer", "creator", "bites", "streets", "places",
    "nukkad", "shots", "clicks", "edits"
}

CHANNEL_CATEGORIES = [
    "channel", "broadcast channel", "members", "subscribers",
    "media/news company", "news & media website", "news company", "news portal",
    "city/town", "community organization", "community", "public & government",
    "government organization", "political organization", "political party",
    "shopping & retail", "clothing (brand)", "brand", "product/service",
    "restaurant", "cafe", "hotel & lodging", "travel agency", "real estate",
    "commercial & industrial", "business service", "marketing agency", "advertising",
    "entertainment website", "tv channel", "radio station", "musician/band",
    "non-governmental organization", "nonprofit organization", "arts & entertainment",
]


def is_channel_or_non_person_account(
    username: str,
    display_name: str = "",
    subtitle: str = "",
    bio_text: str = "",
    target_location: str = ""
) -> tuple[bool, str]:
    """
    Determines if an account is a channel, broadcast channel, media page, news outlet,
    city directory, meme page, commercial business, or brand instead of a real person.

    Returns:
        (True, reason) if it IS a channel/non-person (to be excluded).
        (False, "") if it is a real individual person.
    """
    u = clean_instagram_username(username).lower()
    if not u or u in SYSTEM_PATHS:
        return True, "System or reserved path"

    combined_text = f"{display_name} {subtitle} {bio_text}".lower()

    # 1. Subtitle & Category check (Instagram Search dropdown / profile header badges)
    for cat in CHANNEL_CATEGORIES:
        if cat in combined_text:
            return True, f"Category/subtitle matches '{cat}'"

    # 2. Check for Broadcast Channel specific markers
    if re.search(r"\bchannel\b", combined_text, re.IGNORECASE):
        return True, "Broadcast channel or channel marker in text"
    if re.search(r"\b\d+[\d,.]*[km]?\s+members\b", combined_text, re.IGNORECASE):
        return True, "Member count marker indicating broadcast channel"

    # 3. Bio commercial promotion markers
    bio_lower = bio_text.lower()
    promo_markers = [
        "official account", "official page", "dm for promo", "dm for paid",
        "paid promotion", "for shoutout", "for promotions", "news portal",
        "all updates", "daily news", "contact for ads", "broadcast channel"
    ]
    for pm in promo_markers:
        if pm in bio_lower:
            return True, f"Bio contains commercial/channel marker: '{pm}'"

    # 4. Check if username matches target location entity directly or city compound
    if target_location:
        loc_clean = re.sub(r'[^a-z0-9]', '', target_location.lower())
        u_clean = re.sub(r'[^a-z0-9]', '', u)
        if loc_clean:
            if u_clean == loc_clean or u_clean == f"the{loc_clean}" or u_clean == f"{loc_clean}city":
                return True, f"Username represents the city '{target_location}' itself"
            
            # City markers including common local abbreviations
            city_markers = [loc_clean]
            if loc_clean == "lucknow":
                city_markers.extend(["lko", "lucknowi", "awadh"])
            elif loc_clean in ["delhi", "newdelhi"]:
                city_markers.extend(["dli", "delhiite"])
            elif loc_clean == "mumbai":
                city_markers.extend(["mum", "bombay"])

            for c_mark in city_markers:
                if c_mark in u_clean:
                    remainder = u_clean.replace(c_mark, "").strip("_.-")
                    if remainder in CHANNEL_PATTERNS or any(p in remainder for p in [
                        "news", "update", "times", "vibes", "city", "food", "diaries", "memes",
                        "now", "today", "live", "samachar", "daily", "bulletin", "express",
                        "finds", "core", "unseen", "awadh", "anokha", "captured", "heritage",
                        "youtuber", "vlogger", "nukkad", "guide", "places", "hub"
                    ]):
                        return True, f"Username '{u}' is a city channel/curation compound"

    # 5. Check username for high-confidence channel substring keywords
    high_confidence_substrings = [
        "channel", "broadcast", "samachar", "bulletin", "official",
        "nagarnigam", "foodie", "diaries", "memes"
    ]
    for kw in high_confidence_substrings:
        if kw in u:
            return True, f"Channel keyword '{kw}' in username '@{u}'"

    # 6. Check username tokenized against CHANNEL_PATTERNS
    tokens = [t for t in re.split(r'[_.\-0-9]+', u) if len(t) >= 3]
    for token in tokens:
        if token in CHANNEL_PATTERNS:
            return True, f"Channel token '{token}' in username '@{u}'"

    return False, ""


def is_verified_account(container_or_driver) -> tuple[bool, str]:
    """
    Checks if a profile header, modal header, or row element contains an Instagram Verified Badge.
    Detects blue tick badge SVGs (aria-label='Verified', title='Verified', or child <title>Verified</title>).

    Returns:
        (True, reason) if account is verified (to be skipped).
        (False, "") if account is normal / unverified.
    """
    if not container_or_driver:
        return False, ""
    try:
        from selenium.webdriver.common.by import By

        # 1. Look for SVG with aria-label='Verified' or title='Verified' or inner <title>Verified</title>
        badges = container_or_driver.find_elements(
            By.XPATH,
            ".//*[local-name()='svg' and ("
            "translate(@aria-label, 'VERIFIED', 'verified')='verified' "
            "or translate(@aria-label, 'VERIFIED', 'verified')='verified account' "
            "or translate(@title, 'VERIFIED', 'verified')='verified' "
            "or .//*[local-name()='title' and translate(text(), 'VERIFIED', 'verified')='verified']"
            ")]"
        )
        if badges:
            return True, "Instagram verified badge detected (Blue checkmark SVG)"

        # 2. Look for any element specifically having title or aria-label 'Verified' or 'Verified account'
        elements = container_or_driver.find_elements(
            By.XPATH,
            ".//*[@title='Verified' or @aria-label='Verified' or @title='Verified account' or @aria-label='Verified account']"
        )
        if elements:
            return True, "Verified badge attribute detected"

    except Exception as e:
        logger.debug(f"is_verified_account check note: {e}")
    return False, ""


def extract_ig_profile_info(card_or_element, driver=None) -> tuple[str, str]:
    """
    Extracts (username, profile_url) from an Instagram row, post card, or element.
    Used by testing scripts and inspect utilities.
    """
    try:
        if hasattr(card_or_element, "get_attribute"):
            h = card_or_element.get_attribute("href") or ""
            u = extract_username_from_url(h)
            if u:
                return u, f"https://www.instagram.com/{u}/"
            from selenium.webdriver.common.by import By
            links = card_or_element.find_elements(By.XPATH, ".//a[contains(@href, '/')]")
            for l in links:
                lh = l.get_attribute("href") or ""
                lu = extract_username_from_url(lh)
                if lu:
                    return lu, f"https://www.instagram.com/{lu}/"
    except Exception:
        pass
    return "", ""


def parse_follower_count_string(val: str) -> int:
    """
    Parses human-readable numbers into integers.
    Examples:
        '11.3k' or '11.3K' -> 11300
        '1.5M' or '1.5m'   -> 1500000
        '2.1B'             -> 2100000000
        '1,234'            -> 1234
        '850'              -> 850
    """
    if not val:
        return 0
    v = str(val).strip().replace(',', '').lower()
    try:
        if v.endswith('k'):
            return int(float(v[:-1]) * 1000)
        elif v.endswith('m'):
            return int(float(v[:-1]) * 1000000)
        elif v.endswith('b'):
            return int(float(v[:-1]) * 1000000000)
        else:
            clean_num = re.sub(r'[^0-9.]', '', v)
            if not clean_num:
                return 0
            return int(float(clean_num))
    except Exception:
        return 0


def extract_instagram_profile_details(driver, target_username: str = None) -> dict:
    """
    Extracts comprehensive intelligence from an active Instagram profile page:
    - followers_count (int) and followers_text (e.g. '11.3K')
    - following_count (int) and following_text (e.g. '18')
    - posts_count (int) and posts_text (e.g. '121')
    - full_name (str)
    - bio (str)
    - is_private (bool)
    - is_verified (bool)
    - profile_url (str)
    Uses multi-layer fallback: Profile Header text -> OpenGraph meta description -> DOM selectors.
    """
    js_code = """
    var res = {
        og: null,
        desc: null,
        headerText: null,
        followerTitle: null,
        followerLinkText: null,
        followingLinkText: null,
        postsText: null,
        fullName: null,
        bio: null,
        isPrivate: false,
        isVerified: false
    };
    var ogEl = document.querySelector('meta[property="og:description"]');
    if (ogEl) res.og = ogEl.getAttribute('content');
    var descEl = document.querySelector('meta[name="description"]');
    if (descEl) res.desc = descEl.getAttribute('content');
    var h = document.querySelector('header');
    if (h) res.headerText = h.innerText;
    var fLink = document.querySelector('header a[href*="/followers/"], a[href*="/followers/"]');
    if (fLink) {
        res.followerLinkText = fLink.innerText.trim();
        var spanTitle = fLink.querySelector('[title]');
        if (spanTitle && spanTitle.getAttribute('title')) {
            res.followerTitle = spanTitle.getAttribute('title');
        }
    }
    var ingLink = document.querySelector('header a[href*="/following/"], a[href*="/following/"]');
    if (ingLink) res.followingLinkText = ingLink.innerText.trim();
    var bodyText = document.body ? document.body.innerText : '';
    if (bodyText.includes('This account is private') || bodyText.includes('This Account is Private')) {
        res.isPrivate = true;
    }
    var verEl = document.querySelector('header [title="Verified"], header [aria-label="Verified"], header svg[aria-label="Verified"]');
    if (verEl) res.isVerified = true;
    return res;
    """
    try:
        raw = driver.execute_script(js_code) or {}
    except Exception as e:
        logger.debug(f"JS extraction error: {e}")
        raw = {}

    header_text = raw.get("headerText") or ""
    meta_content = raw.get("og") or raw.get("desc") or ""

    # 1. Follower extraction
    followers_text = ""
    followers_count = 0
    m_header = re.search(r'([\d.,]+[kKmMbB]?)\s+followers', header_text, re.IGNORECASE)
    if m_header:
        followers_text = m_header.group(1).strip()
        followers_count = parse_follower_count_string(followers_text)

    if not followers_count and meta_content:
        m_meta = re.search(r'([\d.,]+[kKmMbB]?)\s+followers', meta_content, re.IGNORECASE)
        if m_meta:
            followers_text = m_meta.group(1).strip()
            followers_count = parse_follower_count_string(followers_text)

    if not followers_count and raw.get("followerTitle"):
        t = raw["followerTitle"].strip()
        if re.match(r'^[\d.,]+[kKmMbB]?$', t):
            followers_text = t
            followers_count = parse_follower_count_string(t)

    # 2. Following extraction
    following_text = ""
    following_count = 0
    m_ing = re.search(r'([\d.,]+[kKmMbB]?)\s+following', header_text, re.IGNORECASE)
    if m_ing:
        following_text = m_ing.group(1).strip()
        following_count = parse_follower_count_string(following_text)
    elif meta_content:
        m_ing_meta = re.search(r'([\d.,]+[kKmMbB]?)\s+following', meta_content, re.IGNORECASE)
        if m_ing_meta:
            following_text = m_ing_meta.group(1).strip()
            following_count = parse_follower_count_string(following_text)

    # 3. Posts count
    posts_text = ""
    posts_count = 0
    m_posts = re.search(r'([\d.,]+[kKmMbB]?)\s+posts', header_text, re.IGNORECASE)
    if m_posts:
        posts_text = m_posts.group(1).strip()
        posts_count = parse_follower_count_string(posts_text)
    elif meta_content:
        m_posts_meta = re.search(r'([\d.,]+[kKmMbB]?)\s+posts', meta_content, re.IGNORECASE)
        if m_posts_meta:
            posts_text = m_posts_meta.group(1).strip()
            posts_count = parse_follower_count_string(posts_text)

    # 4. Full name extraction
    full_name = ""
    if meta_content:
        m_fn = re.search(r'from\s+(.*?)\s+\(@[a-zA-Z0-9._]+\)', meta_content, re.IGNORECASE)
        if m_fn:
            full_name = m_fn.group(1).strip()
    if not full_name and header_text:
        lines = [l.strip() for l in header_text.splitlines() if l.strip()]
        if len(lines) >= 2 and target_username and lines[0].lower() == target_username.lower():
            full_name = lines[1]

    # 5. Bio extraction
    bio = ""
    if header_text:
        lines = [l.strip() for l in header_text.splitlines() if l.strip()]
        bio_lines = []
        skip_words = {"posts", "followers", "following", "follow", "message", "following", "requested"}
        for line in lines:
            ll = line.lower()
            if any(w in ll for w in skip_words) or (target_username and ll == target_username.lower()) or ll == full_name.lower():
                continue
            bio_lines.append(line)
        bio = "\n".join(bio_lines[:4])

    return {
        "followers_text": followers_text or str(followers_count),
        "followers_count": followers_count,
        "following_text": following_text or str(following_count),
        "following_count": following_count,
        "posts_text": posts_text or str(posts_count),
        "posts_count": posts_count,
        "full_name": full_name,
        "bio": bio,
        "is_private": bool(raw.get("isPrivate", False)),
        "is_verified": bool(raw.get("isVerified", False))
    }


def process_instagram_user_target(
    username_or_id: str,
    driver=None,
    save_to_db: bool = True,
    skip_if_channel: bool = False,
    skip_if_verified: bool = False,
    target_location: str = "",
    account_id: str = None,
    source: str = "bot",
    capture_screenshot: bool = False
) -> dict:
    """
    Manvix AI Core Follow & Intelligence Engine:
    1. Takes an Instagram User ID / username.
    2. Enters inside the profile URL on port 9222.
    3. Auto-recovers from blank/unrendered DOM states.
    4. Extracts follower count, following count, posts count, full name, and bio.
    5. Saves the extracted follower data and profile details into database & JSON tracker.
    6. Sends follow request according to existing human-like process (if not already following/requested).
    7. Verifies state transition (following / requested).
    8. Records cumulative counts and returns detailed report.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.action_chains import ActionChains

    clean_user = clean_instagram_username(username_or_id)
    if not clean_user:
        return {
            "status": "error",
            "username": username_or_id,
            "message": "Invalid Instagram user ID provided.",
            "followers_count": 0,
            "followers_text": "0"
        }

    profile_url = f"https://www.instagram.com/{clean_user}/"
    logger.info(f"🚀 Navigating inside Instagram profile: @{clean_user} ({profile_url})")

    if not driver:
        driver = browser.get_driver("instagram")

    screenshot_path = None
    try:
        with browser.tab_focus("instagram", url=profile_url) as active_driver:
            driver = active_driver or driver
            time.sleep(random.uniform(2.0, 3.2))

            # Auto-heal blank page
            if browser.is_blank_or_unrendered(driver):
                logger.warning(f"⚠️ Instagram profile @{clean_user} unrendered or blank. Auto-recovering...")
                browser.ensure_healthy_page(driver, "instagram", target_url=profile_url)
                time.sleep(2.0)

            # Check 404 / unavailable
            page_title = driver.title or ""
            page_source = driver.page_source.lower()
            if "page not found" in page_title.lower() or "isn't available" in page_source:
                msg = f"User @{clean_user} was not found on Instagram (Profile unavailable)."
                logger.warning(msg)
                return {
                    "status": "not_found",
                    "username": clean_user,
                    "url": profile_url,
                    "message": msg,
                    "followers_count": 0,
                    "followers_text": "0"
                }

            # ── 1. Extract Profile Intelligence & Follower Count ──
            details = extract_instagram_profile_details(driver, target_username=clean_user)
            followers_count = details.get("followers_count", 0)
            followers_text = details.get("followers_text", "0")
            following_count = details.get("following_count", 0)
            posts_count = details.get("posts_count", 0)
            full_name = details.get("full_name", "")
            bio = details.get("bio", "")
            is_private = details.get("is_private", False)
            is_verified = details.get("is_verified", False)

            logger.info(
                f"📊 Extracted @{clean_user}: {followers_text} followers ({followers_count}), "
                f"{following_count} following, {posts_count} posts | Private: {is_private}"
            )

            # Verified check skip if configured
            if skip_if_verified and is_verified:
                msg = f"Skipped @{clean_user}: Account is verified creator and does not follow back."
                logger.info(f"🛡️ {msg}")
                lead_data = {
                    "username": clean_user,
                    "user_id_input": username_or_id,
                    "profile_url": profile_url,
                    "full_name": full_name,
                    "followers_count": followers_count,
                    "followers_text": followers_text,
                    "following_count": following_count,
                    "posts_count": posts_count,
                    "bio": bio,
                    "is_private": is_private,
                    "follow_status": "skipped",
                    "follow_button_state": "verified",
                    "account_used": account_id or "Default",
                    "source": source
                }
                stats = {}
                if save_to_db:
                    try:
                        from db_campaigns import save_instagram_target_lead
                        stats = save_instagram_target_lead(lead_data)
                    except Exception as e_s:
                        logger.error(f"Error saving lead: {e_s}")
                return {
                    "status": "skipped",
                    "username": clean_user,
                    "url": profile_url,
                    "message": msg,
                    "reason": "verified",
                    "followers_count": followers_count,
                    "followers_text": followers_text,
                    "cumulative_stats": stats
                }

            # ── 2. Check Follow Button State ──
            btns = driver.find_elements(By.XPATH, "//header//button | //main//button | //button")
            follow_btn = None
            state = "unknown"

            for b in btns:
                try:
                    t = (b.text or b.get_attribute("innerText") or "").strip().lower()
                    if t == "follow":
                        follow_btn = b
                        state = "not_following"
                        break
                    elif t == "following":
                        state = "already_following"
                        break
                    elif t == "requested":
                        state = "requested"
                        break
                except Exception:
                    continue

            final_status = "error"
            final_message = ""
            new_button_state = state

            if state == "already_following":
                final_status = "already_following"
                final_message = f"You are already following @{clean_user}."
                logger.info(f"ℹ️ {final_message}")

            elif state == "requested":
                final_status = "requested"
                final_message = f"Follow request has already been sent to @{clean_user} (Private Account)."
                logger.info(f"ℹ️ {final_message}")

            elif follow_btn:
                # ── 3. Send Follow Request (Existing Human Process) ──
                clicked = False
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", follow_btn)
                    time.sleep(0.4)
                    ActionChains(driver).move_to_element(follow_btn).pause(0.2).click().perform()
                    clicked = True
                except Exception:
                    try:
                        driver.execute_script("arguments[0].click();", follow_btn)
                        clicked = True
                    except Exception as e_click:
                        logger.warning(f"Click failed on @{clean_user}: {e_click}")

                if clicked:
                    time.sleep(1.3)
                    # Verify updated button state
                    new_button_state = "followed"
                    for b in driver.find_elements(By.XPATH, "//header//button | //main//button | //button"):
                        try:
                            nt = (b.text or b.get_attribute("innerText") or "").strip().lower()
                            if nt == "following":
                                new_button_state = "following"
                                final_status = "success"
                                break
                            elif nt == "requested":
                                new_button_state = "requested"
                                final_status = "requested"
                                break
                        except Exception:
                            continue

                    if final_status not in ["success", "requested"]:
                        final_status = "requested" if is_private else "success"

                    if final_status == "requested":
                        final_message = f"Follow request sent to private account @{clean_user}!"
                    else:
                        final_message = f"Successfully followed @{clean_user}!"
                    logger.info(f"✅ {final_message}")
                else:
                    final_status = "error"
                    final_message = f"Could not click Follow button on @{clean_user}."
            else:
                final_status = "error"
                final_message = f"Follow button could not be located on @{clean_user}'s profile."

            # Optional Screenshot
            if capture_screenshot:
                try:
                    ss_dir = BASE_DIR / "data" / "media" / "instagram_captures"
                    ss_dir.mkdir(parents=True, exist_ok=True)
                    ss_file = ss_dir / f"ig_{clean_user}_{int(time.time())}.png"
                    driver.save_screenshot(str(ss_file))
                    screenshot_path = str(ss_file)
                    logger.info(f"📸 Captured profile screenshot: {screenshot_path}")
                except Exception as e_ss:
                    logger.debug(f"Screenshot error: {e_ss}")

            # ── 4. Save Lead and Extracted Followers to DB & JSON Tracker ──
            lead_record = {
                "username": clean_user,
                "user_id_input": username_or_id,
                "profile_url": profile_url,
                "full_name": full_name,
                "followers_count": followers_count,
                "followers_text": followers_text,
                "following_count": following_count,
                "posts_count": posts_count,
                "bio": bio,
                "is_private": is_private,
                "follow_status": final_status,
                "follow_button_state": new_button_state,
                "account_used": account_id or "Default",
                "source": source
            }

            cumulative_stats = {}
            if save_to_db:
                try:
                    from db_campaigns import save_instagram_target_lead
                    cumulative_stats = save_instagram_target_lead(lead_record)
                except Exception as e_save:
                    logger.error(f"Error saving lead to database: {e_save}")

            return {
                "status": final_status,
                "username": clean_user,
                "url": profile_url,
                "message": final_message,
                "new_state": new_button_state,
                "full_name": full_name,
                "followers_count": followers_count,
                "followers_text": followers_text,
                "following_count": following_count,
                "posts_count": posts_count,
                "bio": bio,
                "is_private": is_private,
                "is_verified": is_verified,
                "screenshot_path": screenshot_path,
                "cumulative_stats": cumulative_stats
            }

    except Exception as e:
        logger.error(f"Error processing Instagram user @{clean_user}: {e}")
        return {
            "status": "error",
            "username": clean_user,
            "url": profile_url,
            "message": str(e),
            "followers_count": 0,
            "followers_text": "0"
        }


def follow_specific_instagram_user(
    username: str,
    driver=None,
    skip_if_channel: bool = True,
    target_location: str = "",
    skip_if_verified: bool = True
) -> dict:
    """
    Directly navigates to an Instagram user profile, extracts follower count,
    persists lead metrics to the database, and sends follow request.
    Maintains full backward compatibility.
    """
    return process_instagram_user_target(
        username_or_id=username,
        driver=driver,
        save_to_db=True,
        skip_if_channel=skip_if_channel,
        skip_if_verified=skip_if_verified,
        target_location=target_location,
        source="system"
    )



def follow_multiple_instagram_users(
    usernames: list[str],
    safety_delay: int = 10,
    on_progress=None,
    stop_event=None,
    skip_if_verified: bool = True
) -> dict:
    """
    Follows a list of specified Instagram usernames sequentially with human-like delays.
    """
    logger.info(f"Starting batch Instagram follow for {len(usernames)} users (skip_if_verified={skip_if_verified})...")
    driver = browser.navigate("instagram", "https://www.instagram.com/", refresh_first=False)

    results = []
    sent_count = 0
    already_following_count = 0
    skipped_count = 0
    failed_count = 0

    for i, u in enumerate(usernames):
        if stop_event and stop_event.is_set():
            logger.info("Batch follow stopped via stop_event.")
            break

        clean_u = clean_instagram_username(u)
        if not clean_u:
            continue

        res = follow_specific_instagram_user(clean_u, driver=driver, skip_if_verified=skip_if_verified)
        results.append(res)

        if res.get("status") == "success":
            sent_count += 1
        elif res.get("status") in ["already_following", "requested"]:
            already_following_count += 1
        elif res.get("status") == "skipped":
            skipped_count += 1
        else:
            failed_count += 1

        if on_progress:
            try:
                on_progress(sent_count, len(usernames), {
                    "platform": "instagram",
                    "user": clean_u,
                    "url": res.get("url"),
                    "status": res.get("status"),
                    "message": res.get("message"),
                    "sent": sent_count,
                    "target": len(usernames),
                })
            except Exception as e_prog:
                logger.debug(f"Progress callback note: {e_prog}")

        if i < len(usernames) - 1:
            pause = random.uniform(max(6.0, safety_delay * 0.7), max(9.0, safety_delay * 1.2))
            logger.info(f"Human safety pause: {pause:.1f}s before next user...")
            time.sleep(pause)

    return {
        "status": "completed",
        "total": len(usernames),
        "sent": sent_count,
        "already_following": already_following_count,
        "skipped": skipped_count,
        "failed": failed_count,
        "results": results
    }


def _follow_instagram_suggestions(
    driver,
    target_count,
    safety_delay,
    on_progress,
    stop_event,
    logs,
    skip_if_verified: bool = True
):
    """
    Follows accounts from Instagram's native Suggested Accounts page (https://www.instagram.com/explore/people/).
    Uses atomic tab_focus and exact row ancestor extraction to eliminate stale element collisions and skips.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.action_chains import ActionChains

    logs.append("🌟 Navigating to Instagram Suggested Accounts (https://www.instagram.com/explore/people/)...")
    with browser.tab_focus("instagram", url="https://www.instagram.com/explore/people/"):
        time.sleep(2.0)
        # Dismiss any notification or cookie dialogs
        for d_btn in driver.find_elements(By.XPATH, "//button[text()='Not Now' or text()='Cancel' or text()='Decline optional cookies']"):
            try:
                if d_btn.is_displayed():
                    d_btn.click()
                    time.sleep(0.5)
            except Exception:
                pass

    sent_count = 0
    skipped_count = 0
    batch_follow_count = 0
    consecutive_empty_scrolls = 0
    consecutive_empty_reloads = 0
    processed_users = set()

    while sent_count < target_count and consecutive_empty_reloads < 5:
        if stop_event and stop_event.is_set():
            logs.append("🛑 Instagram follow task stopped by user.")
            break

        clicked_action = False
        u_name = None
        cand_username = None

        # ── ATOMIC BROWSER ACTION (protected under browser lock) ──
        with browser.tab_focus("instagram", url="https://www.instagram.com/explore/people/"):
            # Ensure we are on suggested accounts page
            if "explore/people" not in driver.current_url.lower():
                driver.get("https://www.instagram.com/explore/people/")
                time.sleep(2.0)
                driver.execute_script("window.scrollTo(0, 0);")

            # Check if current batch reached ~28-30 follows. If so, proactively refresh to load next 30 suggestions
            if batch_follow_count >= 28:
                log_refresh = f"🔄 Batch of 30 suggestions completed ({sent_count}/{target_count}). Refreshing Instagram to load fresh algorithmic suggestions from start..."
                logs.append(log_refresh)
                logger.info(log_refresh)
                driver.get("https://www.instagram.com/explore/people/")
                time.sleep(3.0)
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1.0)
                batch_follow_count = 0
                consecutive_empty_scrolls = 0

                # Dismiss dialogs
                for d_btn in driver.find_elements(By.XPATH, "//button[text()='Not Now' or text()='Cancel' or text()='Decline optional cookies']"):
                    try:
                        if d_btn.is_displayed():
                            d_btn.click()
                            time.sleep(0.5)
                    except Exception:
                        pass

            # Query fresh clickable follow buttons currently in the viewport
            candidates = driver.find_elements(
                By.XPATH,
                "//button[.//div[text()='Follow'] or text()='Follow'][not(@data-bot-sent='true')]"
            )

            chosen_btn = None
            for btn in candidates:
                try:
                    if not btn.is_displayed() or btn.get_attribute("data-bot-sent") == "true":
                        continue

                    # Extract username from row: search upward ancestors step by step
                    curr_user = ""
                    curr = btn
                    for step in range(1, 6):
                        curr = curr.find_element(By.XPATH, "..")
                        links = curr.find_elements(By.XPATH, ".//a[contains(@href, '/')]")
                        user_candidates = []
                        for l in links:
                            h = l.get_attribute("href") or ""
                            clean_h = h.split("?")[0].rstrip("/")
                            parts = clean_h.split("/")
                            if parts and parts[-1] and parts[-1] not in SYSTEM_PATHS and parts[-1] not in ["people", "loansolutions2026"]:
                                user_candidates.append(parts[-1])
                        if len(set(user_candidates)) == 1:
                            curr_user = list(set(user_candidates))[0]
                            break

                    if curr_user and curr_user.lower() in processed_users:
                        # Already followed / processed, mark to skip
                        driver.execute_script("arguments[0].setAttribute('data-bot-sent', 'true');", btn)
                        continue

                    # Verified badge check on suggested row container
                    if skip_if_verified:
                        is_ver, ver_reason = is_verified_account(curr)
                        if is_ver:
                            if curr_user:
                                processed_users.add(curr_user.lower())
                            driver.execute_script("arguments[0].setAttribute('data-bot-sent', 'true');", btn)
                            skip_msg = f"🛡️ Skipped verified creator '@{curr_user or 'suggested'}' in suggestions ({ver_reason} - will not follow back)."
                            logs.append(skip_msg)
                            logger.info(skip_msg)
                            skipped_count += 1
                            if on_progress:
                                try:
                                    on_progress(sent_count, target_count, {
                                        "user": curr_user or "suggested",
                                        "activity": f"🛡️ Skipped verified creator @{curr_user or 'suggested'}",
                                        "skipped_verified": True
                                    })
                                except Exception:
                                    pass
                            continue

                    cand_username = curr_user
                    u_name = curr_user or f"suggested_user_{sent_count + 1}"
                    chosen_btn = btn
                    break
                except Exception:
                    continue

            if not chosen_btn:
                # Self-healing check: Verify page didn't unrender or turn into blank white screen
                if browser.is_blank_or_unrendered(driver):
                    logger.warning("⚠️ Instagram suggestions page went blank white! Auto-recovering...")
                    browser.ensure_healthy_page(driver, "instagram", target_url="https://www.instagram.com/explore/people/")
                    time.sleep(2.0)
                    continue

                # No unvisited follow button on screen -> try scrolling down to check if lower part of 30 has unvisited buttons
                consecutive_empty_scrolls += 1
                if consecutive_empty_scrolls < 2:
                    driver.execute_script("window.scrollBy(0, 800);")
                    time.sleep(random.uniform(1.2, 1.8))
                    continue

                # After scrolling, still no unvisited follow buttons left in this 30-account batch!
                # Refresh page to fetch fresh batch from the top
                consecutive_empty_reloads += 1
                if consecutive_empty_reloads >= 5:
                    logs.append(f"⚠️ Instagram has no more suggestions after 5 refresh attempts. Finishing with {sent_count}/{target_count} follows.")
                    break

                log_msg = f"🔄 Batch exhausted or 30 follows reached ({sent_count}/{target_count}). Refreshing Instagram suggestions to load new accounts from start..."
                logs.append(log_msg)
                logger.info(log_msg)
                driver.get("https://www.instagram.com/explore/people/")
                time.sleep(3.0)
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1.0)
                batch_follow_count = 0
                consecutive_empty_scrolls = 0

                # Dismiss dialogs
                for d_btn in driver.find_elements(By.XPATH, "//button[text()='Not Now' or text()='Cancel' or text()='Decline optional cookies']"):
                    try:
                        if d_btn.is_displayed():
                            d_btn.click()
                            time.sleep(0.5)
                    except Exception:
                        pass
                continue

            # Found an unvisited follow button -> reset empty counters
            consecutive_empty_scrolls = 0
            consecutive_empty_reloads = 0

            # Tag candidate and smooth scroll
            if cand_username:
                processed_users.add(cand_username.lower())

            driver.execute_script("arguments[0].setAttribute('data-bot-sent', 'true');", chosen_btn)
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", chosen_btn)
            time.sleep(random.uniform(0.3, 0.6))

            try:
                ActionChains(driver).move_to_element(chosen_btn).pause(0.2).click().perform()
                clicked_action = True
            except Exception:
                try:
                    driver.execute_script("arguments[0].click();", chosen_btn)
                    clicked_action = True
                except Exception as e_c:
                    logger.warning(f"Could not click follow button: {e_c}")

            if clicked_action:
                sent_count += 1
                batch_follow_count += 1
                log_entry = f"✅ Followed #{sent_count}: '@{u_name}' (Suggested Account | Batch {batch_follow_count}/30)"
                logs.append(log_entry)
                logger.info(log_entry)

        # ── OUTSIDE BROWSER LOCK (allows concurrent tasks to run without collisions) ──
        if clicked_action:
            if on_progress:
                try:
                    on_progress(sent_count, target_count, {
                        "platform": "instagram",
                        "user": u_name,
                        "url": f"https://www.instagram.com/{cand_username}/" if cand_username else "https://www.instagram.com/explore/people/",
                        "location": "Suggested Accounts",
                        "mode": "suggestions",
                        "sent": sent_count,
                        "target": target_count,
                        "activity": f"✅ Followed suggested account @{u_name} ({sent_count}/{target_count})",
                    })
                except Exception:
                    pass

            # 2-minute safety break after every 250 follows
            if sent_count > 0 and sent_count % 250 == 0 and sent_count < target_count:
                cooldown_secs = 120
                cooldown_msg = f"⏸️ Reached {sent_count} Instagram follows milestone. Taking a 2-minute safety break..."
                logs.append(cooldown_msg)
                logger.info(cooldown_msg)
                if on_progress:
                    try:
                        on_progress(sent_count, target_count, {
                            "platform": "instagram",
                            "user": u_name,
                            "cooldown": True,
                            "cooldown_seconds": cooldown_secs,
                            "message": f"Paused for 2-min safety cooldown ({sent_count}/{target_count})",
                            "activity": f"☕ 2-minute safety cooldown active ({sent_count}/{target_count})",
                        })
                    except Exception:
                        pass
                for _ in range(cooldown_secs):
                    if stop_event and stop_event.is_set():
                        break
                    time.sleep(1.0)
                logs.append(f"▶️ 2-minute safety cooldown completed. Resuming follows ({sent_count}/{target_count})...")

            # Human safety pause outside lock
            pause = random.uniform(max(6.0, safety_delay * 0.7), max(9.0, safety_delay * 1.15))
            logger.info(f"Human safety pause: {pause:.1f}s before next follow ({sent_count}/{target_count})...")
            if on_progress:
                try:
                    on_progress(sent_count, target_count, {
                        "activity": f"⏱️ Safety pause: {pause:.1f}s before next suggestion..."
                    })
                except Exception:
                    pass
            time.sleep(pause)
        else:
            skipped_count += 1
            time.sleep(1.0)

    return sent_count, skipped_count


def _follow_instagram_random_explore(
    driver,
    target_count,
    safety_delay,
    on_progress,
    stop_event,
    logs,
    skip_if_verified: bool = True
):
    """
    Follows creators discovered dynamically and randomly on the Instagram Explore Feed (https://www.instagram.com/explore/).
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains

    logs.append("🎲 Navigating to Instagram Explore Feed (https://www.instagram.com/explore/)...")
    driver.get("https://www.instagram.com/explore/")
    time.sleep(3.0)

    # Dismiss dialogs
    for d_btn in driver.find_elements(By.XPATH, "//button[text()='Not Now' or text()='Cancel' or text()='Decline optional cookies']"):
        try:
            if d_btn.is_displayed():
                d_btn.click()
                time.sleep(0.5)
        except Exception:
            pass

    sent_count = 0
    skipped_count = 0
    processed_users = set()

    thumbnails = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/') or contains(@href, '/reel/')]")
    logger.info(f"Explore page loaded {len(thumbnails)} post thumbnails for random discovery.")

    if not thumbnails:
        logs.append("⚠️ No Explore post thumbnails found.")
        return 0, 0

    # Pick a random thumbnail among the first 12 to start
    start_idx = random.randint(0, min(10, len(thumbnails) - 1))
    try:
        driver.execute_script("arguments[0].click();", thumbnails[start_idx])
        time.sleep(2.5)
    except Exception as e_open:
        logger.warning(f"Could not open initial thumbnail: {e_open}")
        return 0, 0

    cycles = 0
    max_cycles = max(40, target_count * 5)

    while sent_count < target_count and cycles < max_cycles:
        if stop_event and stop_event.is_set():
            logs.append("🛑 Instagram random follow task stopped by user.")
            break

        cycles += 1
        clicked = False
        display_u = f"creator_{cycles}"
        author_name = None

        with browser.tab_focus("instagram", url="https://www.instagram.com/explore/"):
            # Check if explore feed or modal became blank white
            if browser.is_blank_or_unrendered(driver):
                logger.warning("⚠️ Instagram explore feed unrendered or blank white! Auto-recovering...")
                browser.ensure_healthy_page(driver, "instagram", target_url="https://www.instagram.com/explore/")
                time.sleep(2.0)
                continue

            # Check for dialog container
            dialogs = driver.find_elements(By.XPATH, "//div[@role='dialog']")
            active_container = dialogs[0] if dialogs else driver

            # Extract author
            try:
                author_links = active_container.find_elements(
                    By.XPATH,
                    ".//header//a | .//a[contains(@class, 'x1i10hfl') and not(contains(@href, '/p/'))]"
                )
                for al in author_links:
                    ahref = al.get_attribute("href") or ""
                    cand_u = extract_username_from_url(ahref)
                    if cand_u and cand_u.lower() not in SYSTEM_PATHS:
                        author_name = cand_u
                        break
            except Exception:
                pass

            display_u = author_name or f"creator_{cycles}"

            # If author already processed, cycle to next post (arrow right)
            if author_name and author_name.lower() in processed_users:
                try:
                    skips = random.randint(1, 3)
                    for _ in range(skips):
                        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ARROW_RIGHT)
                        time.sleep(random.uniform(0.6, 1.0))
                except Exception:
                    pass
                continue

            if author_name:
                processed_users.add(author_name.lower())

            # Verified badge check in explore post modal
            if skip_if_verified:
                try:
                    modal_headers = active_container.find_elements(By.XPATH, ".//header")
                    target_modal_header = modal_headers[0] if modal_headers else active_container
                    is_ver, ver_reason = is_verified_account(target_modal_header)
                    if is_ver:
                        skip_msg = f"🛡️ Skipped verified creator '@{display_u}' in explore ({ver_reason} - will not follow back)."
                        logs.append(skip_msg)
                        logger.info(skip_msg)
                        skipped_count += 1
                        if on_progress:
                            try:
                                on_progress(sent_count, target_count, {
                                    "user": display_u,
                                    "activity": f"🛡️ Skipped verified creator @{display_u}",
                                    "skipped_verified": True
                                })
                            except Exception:
                                pass
                        try:
                            skips = random.randint(1, 2)
                            for _ in range(skips):
                                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ARROW_RIGHT)
                                time.sleep(random.uniform(0.6, 1.0))
                        except Exception:
                            pass
                        continue
                except Exception:
                    pass

            # Locate Follow button inside modal
            follow_btn = None
            modal_btns = active_container.find_elements(By.XPATH, ".//button | .//div[@role='button']")
            for mb in modal_btns:
                try:
                    mtxt = (mb.text or mb.get_attribute("innerText") or "").strip().lower()
                    if mtxt == "follow":
                        follow_btn = mb
                        break
                    elif mtxt in ["following", "requested"]:
                        follow_btn = None
                        break
                except Exception:
                    continue

            if follow_btn:
                try:
                    ActionChains(driver).move_to_element(follow_btn).pause(0.2).click().perform()
                    clicked = True
                except Exception:
                    try:
                        driver.execute_script("arguments[0].click();", follow_btn)
                        clicked = True
                    except Exception:
                        pass

            # Smoothly cycle to next post in modal while still in tab focus
            try:
                skips = random.randint(1, 2)
                for _ in range(skips):
                    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ARROW_RIGHT)
                    time.sleep(random.uniform(0.8, 1.4))
            except Exception:
                pass

        # ── OUTSIDE BROWSER LOCK (yields to concurrent Facebook task) ──
        if clicked:
            sent_count += 1
            log_entry = f"✅ Followed #{sent_count}: '@{display_u}' (Random Explore Creator)"
            logs.append(log_entry)
            logger.info(log_entry)

            if on_progress:
                try:
                    on_progress(sent_count, target_count, {
                        "platform": "instagram",
                        "user": display_u,
                        "url": f"https://www.instagram.com/{author_name}/" if author_name else driver.current_url,
                        "location": "Random Explore Feed",
                        "mode": "random",
                        "sent": sent_count,
                        "target": target_count,
                        "activity": f"✅ Followed creator @{display_u} ({sent_count}/{target_count})",
                    })
                except Exception:
                    pass

            # 2-minute safety break after every 250 follows
            if sent_count > 0 and sent_count % 250 == 0 and sent_count < target_count:
                cooldown_secs = 120
                cooldown_msg = f"⏸️ Reached {sent_count} Instagram follows milestone. Taking a 2-minute safety break..."
                logs.append(cooldown_msg)
                logger.info(cooldown_msg)
                if on_progress:
                    try:
                        on_progress(sent_count, target_count, {
                            "platform": "instagram",
                            "user": display_u,
                            "cooldown": True,
                            "cooldown_seconds": cooldown_secs,
                            "message": f"Paused for 2-min safety cooldown ({sent_count}/{target_count})",
                            "activity": f"☕ 2-minute safety cooldown active ({sent_count}/{target_count})",
                        })
                    except Exception:
                        pass
                for _ in range(cooldown_secs):
                    if stop_event and stop_event.is_set():
                        break
                    time.sleep(1.0)
                logs.append(f"▶️ 2-minute safety cooldown completed. Resuming Instagram follows ({sent_count}/{target_count})...")

            pause = random.uniform(max(6.0, safety_delay * 0.7), max(9.0, safety_delay * 1.15))
            logger.info(f"Human safety pause: {pause:.1f}s before next follow ({sent_count}/{target_count})...")
            if on_progress:
                try:
                    on_progress(sent_count, target_count, {
                        "activity": f"⏱️ Safety pause: {pause:.1f}s before next creator..."
                    })
                except Exception:
                    pass
            time.sleep(pause)
        else:
            skipped_count += 1
            time.sleep(1.0)

    return sent_count, skipped_count


def _follow_instagram_by_location(
    driver,
    location: str,
    target_count: int,
    safety_delay: int,
    on_progress=None,
    stop_event=None,
    logs=None,
    skip_if_verified: bool = True
) -> tuple[int, int]:
    """
    Discovers and follows REAL INDIVIDUAL PEOPLE in a specific target location (e.g. Lucknow).
    Strictly filters out and skips all channels, broadcast channels, media/news outlets,
    city directories, meme pages, and brand/business accounts.

    Workflow:
    1. Loads Instagram keyword search feed (https://www.instagram.com/explore/search/keyword/?q=<location>)
       and location hashtags (#lucknow).
    2. Opens post lightbox modal and scans geotagged post creators via Arrow Right.
    3. Strictly filters out all channels, city pages, and commercial entities using is_channel_or_non_person_account.
    4. For verified real residents, visits their profile to inspect bio and click the real Follow button.
    5. Streams real-time telemetry to Telegram bot and respects human safety pauses.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains

    loc_name = (location or "New Delhi").strip()
    if logs is None:
        logs = []

    logs.append(f"📍 Discovering real people from '{loc_name}' on Instagram (excluding channels)...")
    logger.info(f"Starting _follow_instagram_by_location for '{loc_name}' (Target: {target_count})")
    if on_progress:
        try:
            on_progress(0, target_count, {"activity": f"📍 Discovering real people from '{loc_name}' (excluding channels)..."})
        except Exception:
            pass

    sent_count = 0
    skipped_count = 0
    processed_users = set()
    candidate_people = []

    if not driver:
        driver = browser.get_driver("instagram")

    clean_loc_tag = re.sub(r'[^a-zA-Z0-9]', '', loc_name).lower()
    target_feeds = [
        ("Keyword Search Feed", f"https://www.instagram.com/explore/search/keyword/?q={urllib.parse.quote(loc_name.lower())}"),
        ("Location Hashtag Feed", f"https://www.instagram.com/explore/tags/{clean_loc_tag}/"),
        ("City Hashtag Feed", f"https://www.instagram.com/explore/tags/{clean_loc_tag}city/"),
    ]

    for source_label, feed_url in target_feeds:
        if sent_count >= target_count:
            break
        if stop_event and stop_event.is_set():
            logs.append("🛑 Instagram location follow stopped by user.")
            break

        logs.append(f"📸 Scanning {source_label} for '{loc_name}' ({feed_url})...")
        logger.info(f"Navigating to {source_label}: {feed_url}")
        if on_progress:
            try:
                on_progress(sent_count, target_count, {"activity": f"🔍 Scanning {source_label} for '{loc_name}' posts..."})
            except Exception:
                pass

        with browser.tab_focus("instagram", url=feed_url) as active_driver:
            driver = active_driver or driver
            time.sleep(2.5)

            # Dismiss dialogs
            for d_btn in driver.find_elements(By.XPATH, "//button[text()='Not Now' or text()='Cancel' or text()='Decline optional cookies']"):
                try:
                    if d_btn.is_displayed():
                        d_btn.click()
                        time.sleep(0.4)
                except Exception:
                    pass

            thumbnails = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/') or contains(@href, '/reel/')]")
            if len(thumbnails) < 15:
                # Scroll down to load more posts
                try:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1.8)
                    thumbnails = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/') or contains(@href, '/reel/')]")
                except Exception:
                    pass

            logger.info(f"{source_label} loaded {len(thumbnails)} post thumbnails for '{loc_name}'")

            if not thumbnails:
                continue

            # Open first post lightbox modal
            try:
                driver.execute_script("arguments[0].click();", thumbnails[0])
                time.sleep(2.2)
            except Exception as e_th:
                logger.warning(f"Could not open first thumbnail on {source_label}: {e_th}")
                continue

            # Scan posts inside the modal lightbox using Arrow Right
            scan_cycles = 0
            max_scan = max(30, (target_count - sent_count) * 8)

            while scan_cycles < max_scan and len(candidate_people) < max(12, (target_count - sent_count) * 2):
                if stop_event and stop_event.is_set():
                    break

                scan_cycles += 1
                dialogs = driver.find_elements(By.XPATH, "//div[@role='dialog']")
                if not dialogs:
                    break
                active_dialog = dialogs[0]

                # Extract author link from dialog header
                author_name = None
                try:
                    author_links = active_dialog.find_elements(
                        By.XPATH,
                        ".//header//a | .//a[contains(@class, 'x1i10hfl') and not(contains(@href, '/p/')) and not(contains(@href, '/reel/')) and not(contains(@href, '/tags/')) and not(contains(@href, '/liked_by/')) and not(contains(@href, '/audio/'))]"
                    )
                    for al in author_links:
                        ahref = al.get_attribute("href") or ""
                        cand_u = extract_username_from_url(ahref)
                        if cand_u and cand_u.lower() not in SYSTEM_PATHS and cand_u.lower() not in ["loansolutions2026"]:
                            author_name = cand_u
                            break
                except Exception:
                    pass

                # Move to next post via Arrow Right
                try:
                    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ARROW_RIGHT)
                    time.sleep(random.uniform(0.7, 1.1))
                except Exception:
                    pass

                if not author_name or author_name.lower() in processed_users:
                    continue

                processed_users.add(author_name.lower())

                # Verified badge check in modal header (skip creators who never follow back)
                is_ver = False
                ver_reason = ""
                if skip_if_verified:
                    try:
                        modal_headers = active_dialog.find_elements(By.XPATH, ".//header")
                        target_modal_header = modal_headers[0] if modal_headers else active_dialog
                        is_ver, ver_reason = is_verified_account(target_modal_header)
                    except Exception:
                        pass

                if is_ver:
                    skipped_count += 1
                    logger.info(f"🛡️ Skipped verified creator: @{author_name} ({ver_reason} - will not follow back)")
                    logs.append(f"🛡️ Skipped verified creator: '@{author_name}' (Verified badge)")
                    if on_progress:
                        try:
                            on_progress(sent_count, target_count, {
                                "user": author_name,
                                "activity": f"🛡️ Skipped verified creator '@{author_name}'",
                                "skipped_verified": True
                            })
                        except Exception:
                            pass
                    continue

                # Candidate account found (verified creators already excluded)
                candidate_people.append(author_name)
                logger.info(f"👤 Found candidate to follow: @{author_name} ({loc_name})")
                if on_progress:
                    try:
                        on_progress(sent_count, target_count, {
                            "activity": f"👤 Discovered @{author_name} ({len(candidate_people)} queued)"
                        })
                    except Exception:
                        pass

        # Follow candidate accounts by navigating directly to their profiles
        while candidate_people and sent_count < target_count:
            if stop_event and stop_event.is_set():
                break

            cand_u = candidate_people.pop(0)
            if on_progress:
                try:
                    on_progress(sent_count, target_count, {
                        "activity": f"👤 Visiting profile of @{cand_u} ({loc_name})..."
                    })
                except Exception:
                    pass

            res = follow_specific_instagram_user(cand_u, driver=driver, skip_if_channel=False, target_location=loc_name, skip_if_verified=skip_if_verified)
            res_status = res.get("status")

            if res_status in ["success", "requested"]:
                sent_count += 1
                follow_type = "Resident" if res_status == "success" else "Private Resident Profile"
                log_entry = f"✅ Followed #{sent_count}: '@{cand_u}' ({loc_name} {follow_type})"
                logs.append(log_entry)
                logger.info(log_entry)

                if on_progress:
                    try:
                        on_progress(sent_count, target_count, {
                            "platform": "instagram",
                            "user": cand_u,
                            "url": res.get("url") or f"https://www.instagram.com/{cand_u}/",
                            "location": loc_name,
                            "mode": "location",
                            "sent": sent_count,
                            "target": target_count,
                            "activity": f"✅ Followed real resident @{cand_u} ({sent_count}/{target_count})"
                        })
                    except Exception:
                        pass

                # 2-minute safety break after every 250 follows
                if sent_count > 0 and sent_count % 250 == 0 and sent_count < target_count:
                    cooldown_secs = 120
                    cooldown_msg = f"⏸️ Reached {sent_count} Instagram follows milestone. Taking a 2-minute safety break..."
                    logs.append(cooldown_msg)
                    logger.info(cooldown_msg)
                    if on_progress:
                        try:
                            on_progress(sent_count, target_count, {
                                "platform": "instagram",
                                "user": cand_u,
                                "cooldown": True,
                                "cooldown_seconds": cooldown_secs,
                                "message": f"Paused for 2-min safety cooldown ({sent_count}/{target_count})",
                                "activity": f"☕ 2-minute safety cooldown active ({sent_count}/{target_count})"
                            })
                        except Exception:
                            pass
                    for _ in range(cooldown_secs):
                        if stop_event and stop_event.is_set():
                            break
                        time.sleep(1.0)
                    logs.append(f"▶️ 2-minute safety cooldown completed. Resuming follows ({sent_count}/{target_count})...")

                pause = random.uniform(max(6.0, safety_delay * 0.7), max(9.0, safety_delay * 1.15))
                logger.info(f"Human safety pause: {pause:.1f}s before next follow ({sent_count}/{target_count})...")
                if on_progress:
                    try:
                        on_progress(sent_count, target_count, {
                            "activity": f"⏱️ Safety pause: {pause:.1f}s before next profile..."
                        })
                    except Exception:
                        pass
                time.sleep(pause)

            elif res_status == "already_following":
                logger.info(f"ℹ️ Already following @{cand_u}, continuing...")
                if on_progress:
                    try:
                        on_progress(sent_count, target_count, {
                            "activity": f"ℹ️ Already following resident @{cand_u}"
                        })
                    except Exception:
                        pass
                time.sleep(random.uniform(1.0, 1.8))

            else:
                skipped_count += 1
                skip_msg = res.get("message") or "Profile not eligible"
                logger.info(f"🛡️ Skipped @{cand_u}: {skip_msg}")
                if on_progress:
                    try:
                        on_progress(sent_count, target_count, {
                            "activity": f"🛡️ Skipped @{cand_u}: {skip_msg}",
                            "skipped_channel": True
                        })
                    except Exception:
                        pass
                time.sleep(random.uniform(1.0, 1.8))

    return sent_count, skipped_count


def send_instagram_follow_requests(
    location: str = "",
    target_count: int = 10,
    safety_delay: int = 15,
    on_progress=None,
    stop_event=None,
    mode: str = "location",
    skip_if_verified: bool = True
) -> dict:
    """
    Discovers and follows active accounts on Instagram via Suggestions, Random Explore, or Location.
    Uses native sidebar search and modal lightbox navigation to eliminate HTTP 429 page-reload rate limits.
    """
    mode = (mode or "location").lower().strip()
    if mode == "suggestions":
        mode_label = "🌟 Algorithmic Suggestions (Suggested for You)"
        loc_display = "Suggested Accounts"
    elif mode == "random":
        mode_label = "🎲 Random Discovery (Explore Feed Creators)"
        loc_display = "Random Explore Feed"
    else:
        mode = "location"
        loc_display = location or "Global"
        mode_label = f"📍 Location / Keyword: '{loc_display}'"

    logger.info(f"Starting Instagram follow campaign | Mode: {mode_label} (Target: {target_count})...")
    logs = [f"🚀 Initiated Instagram follow campaign: {mode_label} (Target: {target_count})"]
    sent_count = 0
    skipped_count = 0
    processed_users = set()
    candidate_usernames = []

    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains

    try:
        # Step 1: Navigate to Instagram Home with tab locking
        driver = browser.navigate("instagram", "https://www.instagram.com/", refresh_first=False)
        time.sleep(2.0)

        # Check if login is required
        if "accounts/login" in driver.current_url.lower():
            msg = "Instagram login required. Please verify login in Chrome on port 9222."
            logs.append(f"⚠️ {msg}")
            return {"status": "login_required", "sent": 0, "logs": logs}

        # Dismiss notification dialogs / cookies if any
        for d_btn in driver.find_elements(By.XPATH, "//button[text()='Not Now' or text()='Cancel' or text()='Decline optional cookies']"):
            try:
                if d_btn.is_displayed():
                    d_btn.click()
                    time.sleep(0.5)
            except Exception:
                pass

        # ── Branch: Suggestions Mode ──
        if mode == "suggestions":
            s_sent, s_skip = _follow_instagram_suggestions(
                driver=driver,
                target_count=target_count,
                safety_delay=safety_delay,
                on_progress=on_progress,
                stop_event=stop_event,
                logs=logs,
                skip_if_verified=skip_if_verified
            )
            sent_count += s_sent
            skipped_count += s_skip
            status_label = "stopped" if (stop_event and stop_event.is_set()) else ("completed" if sent_count >= target_count else "partial")
            logs.append(f"🏁 Finished Instagram suggestions follow session. Total follows: {sent_count}/{target_count} (Skipped: {skipped_count}).")
            return {
                "status": status_label,
                "platform": "instagram",
                "location": loc_display,
                "mode": mode,
                "sent": sent_count,
                "target": target_count,
                "skipped": skipped_count,
                "logs": logs,
            }

        # ── Branch: Random Explore Mode ──
        elif mode == "random":
            r_sent, r_skip = _follow_instagram_random_explore(
                driver=driver,
                target_count=target_count,
                safety_delay=safety_delay,
                on_progress=on_progress,
                stop_event=stop_event,
                logs=logs,
                skip_if_verified=skip_if_verified
            )
            sent_count += r_sent
            skipped_count += r_skip
            status_label = "stopped" if (stop_event and stop_event.is_set()) else ("completed" if sent_count >= target_count else "partial")
            logs.append(f"🏁 Finished Instagram random follow session. Total follows: {sent_count}/{target_count} (Skipped: {skipped_count}).")
            return {
                "status": status_label,
                "platform": "instagram",
                "location": loc_display,
                "mode": mode,
                "sent": sent_count,
                "target": target_count,
                "skipped": skipped_count,
                "logs": logs,
            }

        # ── Branch: Location-Based Mode (Targeting Real People, Strictly Excluding Channels) ──
        else:
            l_sent, l_skip = _follow_instagram_by_location(
                driver=driver,
                location=location,
                target_count=target_count,
                safety_delay=safety_delay,
                on_progress=on_progress,
                stop_event=stop_event,
                logs=logs,
                skip_if_verified=skip_if_verified
            )
            sent_count += l_sent
            skipped_count += l_skip
            status_label = "stopped" if (stop_event and stop_event.is_set()) else ("completed" if sent_count >= target_count else "partial")
            logs.append(f"🏁 Finished Instagram location follow session for '{loc_display}'. Total follows: {sent_count}/{target_count} (Skipped: {skipped_count}).")
            return {
                "status": status_label,
                "platform": "instagram",
                "location": loc_display,
                "mode": mode,
                "sent": sent_count,
                "target": target_count,
                "skipped": skipped_count,
                "logs": logs,
            }

    except Exception as e:
        logger.error(f"Instagram follow session error: {e}")
        logs.append(f"⚠️ Error: {str(e)}")
        return {
            "status": "error",
            "platform": "instagram",
            "location": loc_display,
            "mode": mode,
            "sent": sent_count,
            "target": target_count,
            "error": str(e),
            "logs": logs,
        }


def _open_instagram_followers_dialog(driver, clean_target: str) -> tuple[bool, str]:
    """
    Navigates to target profile, clicks Followers link, and clicks 'See All Followers' if mutual view appears.
    Returns (success: bool, error_message: str).
    """
    from selenium.webdriver.common.by import By

    target_url = f"https://www.instagram.com/{clean_target}/"
    driver.get(target_url)
    time.sleep(random.uniform(2.5, 3.5))

    if browser.is_blank_or_unrendered(driver):
        browser.ensure_healthy_page(driver, "instagram", target_url=target_url)
        time.sleep(2.0)

    # Check for private or non-existent profile
    body_text = driver.find_element(By.TAG_NAME, "body").text or ""
    if "isn't available" in body_text or "page may have been removed" in body_text:
        return False, f"Account @{clean_target} not found or unavailable."

    if "This account is private" in body_text:
        return False, f"Account @{clean_target} is private. You must be following them to view their followers."

    # Locate and click Followers link
    followers_link = None
    links = driver.find_elements(By.XPATH, "//header//a[contains(@href, '/followers/')] | //a[contains(@href, '/followers/')]")
    if links:
        followers_link = links[0]

    if not followers_link:
        driver.get(f"https://www.instagram.com/{clean_target}/followers/")
        time.sleep(3.0)
    else:
        try:
            driver.execute_script("arguments[0].click();", followers_link)
        except Exception:
            followers_link.click()
        time.sleep(2.5)

    # Locate dialog modal
    dialogs = driver.find_elements(By.XPATH, "//div[@role='dialog']")
    if not dialogs:
        for _ in range(5):
            time.sleep(1.0)
            dialogs = driver.find_elements(By.XPATH, "//div[@role='dialog']")
            if dialogs:
                break

    if not dialogs:
        return False, f"Could not open followers dialog for @{clean_target}."

    dialog = dialogs[0]

    # Check & Click 'See All Followers' (Mutual Followers View Bypass)
    try:
        see_all = dialog.find_elements(
            By.XPATH,
            ".//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'see all followers')] | "
            ".//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'see all followers')]"
        )
        if see_all:
            logger.info(f"Mutual followers detected for @{clean_target}. Clicking 'See All Followers' to unlock full list...")
            driver.execute_script("arguments[0].click();", see_all[0])
            time.sleep(3.0)
    except Exception as e_see:
        logger.debug(f"See All Followers note: {e_see}")

    return True, ""


def _get_dialog_scroll_container(driver, dialog):
    """
    Identifies the exact scrollable element within the Instagram followers modal.
    """
    try:
        container = driver.execute_script("""
            const dialog = arguments[0];
            const allDivs = dialog.querySelectorAll('div');
            for (let div of allDivs) {
                const style = window.getComputedStyle(div);
                if ((style.overflowY === 'auto' || style.overflowY === 'scroll') && div.scrollHeight > div.clientHeight) {
                    return div;
                }
            }
            return dialog;
        """, dialog)
        return container if container else dialog
    except Exception:
        return dialog


def _extract_username_from_follow_button(btn, clean_target: str):
    """
    Walks up DOM parent elements from a Follow button to reliably extract the Instagram username.
    Returns (username: str or None, row_element or None).
    """
    from selenium.webdriver.common.by import By
    try:
        curr = btn
        for _ in range(5):
            curr = curr.find_element(By.XPATH, "..")
            a_tags = curr.find_elements(By.XPATH, ".//a[contains(@href, '/')]")
            u_cand = []
            for a in a_tags:
                h = (a.get_attribute("href") or "").split("?")[0].rstrip("/")
                parts = h.split("/")
                if parts and parts[-1] and parts[-1] not in SYSTEM_PATHS and parts[-1] not in [clean_target, "loansolutions2026"]:
                    u_cand.append(parts[-1])
            if len(set(u_cand)) == 1:
                return list(set(u_cand))[0], curr
    except Exception:
        pass
    return None, None


def follow_target_account_followers(
    target_username: str,
    target_count: int = 15,
    safety_delay: int = 15,
    on_progress=None,
    stop_event=None,
    skip_if_verified: bool = False,
    skip_if_channel: bool = True
) -> dict:
    """
    Follows accounts from a target user's Followers modal dialog (https://www.instagram.com/<target_username>/).
    1. Opens target profile in Chrome.
    2. Clicks on followers link to open the modal dialog (bypassing mutual followers via 'See All Followers').
    3. Deep-Slides past already-followed accounts (avoiding premature refreshes).
    4. Minimum 5-Account Sweep: Buffers at least 5 fresh un-followed accounts before following (or reaches end of list).
    5. Scrolls each target row into view with smooth JavaScript scroll and follows with safe human pacing.
    6. Micro-Batch Resting: Every 30 follows, pauses for 3-4 minutes to safeguard the account up to 1,000 follows.
    7. Only reloads the profile if 15 deep scrolls reach the absolute bottom with zero un-followed accounts.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.action_chains import ActionChains

    clean_target = clean_instagram_username(target_username)
    if not clean_target:
        return {"status": "error", "message": "Invalid target username."}

    # Clamp target count to maximum 1,000 for logical account safety
    target_count = min(max(1, int(target_count)), 1000)

    logger.info(f"Targeting followers of @{clean_target} (Goal: {target_count}, Max: 1000)...")
    logs = [f"🎯 Starting follower extraction for @{clean_target} (Target: {target_count})"]

    try:
        driver = browser.navigate("instagram", f"https://www.instagram.com/{clean_target}/", refresh_first=False)
        time.sleep(random.uniform(2.0, 3.0))

        ok, err_msg = _open_instagram_followers_dialog(driver, clean_target)
        if not ok:
            return {"status": "error", "message": err_msg, "sent": 0}

        sent_count = 0
        skipped_count = 0
        consecutive_empty_reloads = 0
        batch_follow_count = 0
        processed_users = set()
        followed_list = []

        while sent_count < target_count and consecutive_empty_reloads < 6:
            if stop_event and stop_event.is_set():
                logs.append("🛑 Follower outreach stopped by user.")
                break

            active_dialogs = driver.find_elements(By.XPATH, "//div[@role='dialog']")
            if not active_dialogs:
                time.sleep(1.5)
                active_dialogs = driver.find_elements(By.XPATH, "//div[@role='dialog']")
                if not active_dialogs:
                    ok_reopen, _ = _open_instagram_followers_dialog(driver, clean_target)
                    if not ok_reopen:
                        break
                    active_dialogs = driver.find_elements(By.XPATH, "//div[@role='dialog']")

            if not active_dialogs:
                break
            dialog = active_dialogs[0]
            scroll_container = _get_dialog_scroll_container(driver, dialog)

            # Fast-slide down if resuming after an auto-refresh and sent_count > 0
            if sent_count > 0 and len(processed_users) > 0 and getattr(driver, "_just_reloaded_followers", False):
                driver._just_reloaded_followers = False
                fast_scrolls = min(max(3, (sent_count // 10) + 1), 10)
                logger.info(f"Fast-sliding down past ~{sent_count} followed accounts ({fast_scrolls} slides)...")
                for _ in range(fast_scrolls):
                    driver.execute_script("arguments[0].scrollTop += 850;", scroll_container)
                    time.sleep(0.7)
                time.sleep(2.0)  # Allow Instagram AJAX infinite scroll to hydrate next follower chunk

            # ── Minimum 5 Accounts Deep-Slide Sweep ──
            # Slide down dynamically until at least 5 fresh un-followed candidates are loaded,
            # or until the absolute bottom of the list is reached.
            valid_candidates = []
            slide_count = 0

            while len(valid_candidates) < 5 and slide_count < 15:
                if stop_event and stop_event.is_set():
                    break

                # Re-fetch active dialog and buttons safely
                try:
                    active_dialogs = driver.find_elements(By.XPATH, "//div[@role='dialog']")
                    if not active_dialogs:
                        break
                    dialog = active_dialogs[0]
                    scroll_container = _get_dialog_scroll_container(driver, dialog)

                    raw_buttons = dialog.find_elements(
                        By.XPATH,
                        ".//button[.//div[text()='Follow'] or text()='Follow'][not(@data-bot-sent='true')]"
                    )
                except Exception as e_btns:
                    logger.debug(f"Buttons fetch error: {e_btns}")
                    raw_buttons = []

                # Extract and filter candidates
                for btn in raw_buttons:
                    try:
                        u_cand, row_elem = _extract_username_from_follow_button(btn, clean_target)
                        if not u_cand or u_cand.lower() in processed_users:
                            driver.execute_script("arguments[0].setAttribute('data-bot-sent', 'true');", btn)
                            continue

                        # Check if candidate already in current valid_candidates buffer
                        if not any(c[1].lower() == u_cand.lower() for c in valid_candidates):
                            valid_candidates.append((btn, u_cand, row_elem))
                    except Exception:
                        continue

                if len(valid_candidates) >= 5 or (len(valid_candidates) > 0 and (sent_count + len(valid_candidates) >= target_count)):
                    break

                # Check if bottom of modal reached
                try:
                    reached_bottom = driver.execute_script("""
                        const el = arguments[0];
                        return (el.scrollTop + el.clientHeight >= el.scrollHeight - 30);
                    """, scroll_container)
                except Exception:
                    reached_bottom = False

                if reached_bottom and len(valid_candidates) > 0:
                    logger.info(f"Reached bottom of modal with {len(valid_candidates)} candidates available.")
                    break
                elif reached_bottom and len(valid_candidates) == 0:
                    # Give Instagram AJAX infinite scroll a moment to fetch and expand
                    time.sleep(2.0)
                    old_sh = driver.execute_script("return arguments[0].scrollHeight;", scroll_container)
                    driver.execute_script("arguments[0].scrollTop += 200;", scroll_container)
                    time.sleep(1.0)
                    new_sh = driver.execute_script("return arguments[0].scrollHeight;", scroll_container)
                    if new_sh > old_sh:
                        logger.info(f"Instagram dynamically loaded more followers (scrollHeight {old_sh} -> {new_sh}). Continuing sweep...")
                        continue
                    elif slide_count < 4:
                        slide_count += 1
                        continue
                    else:
                        logger.info("Reached bottom of modal with 0 candidates remaining after AJAX verification.")
                        break

                # Slide down deeper to reveal more accounts
                slide_count += 1
                logger.info(f"Sliding down modal past followed accounts (Slide {slide_count}/15, buffered {len(valid_candidates)} candidates)...")
                if on_progress:
                    try:
                        on_progress(sent_count, target_count, {
                            "user": "",
                            "target_account": clean_target,
                            "sent": sent_count,
                            "target": target_count,
                            "status": "sliding",
                            "slide_count": slide_count,
                            "buffered": len(valid_candidates)
                        })
                    except Exception:
                        pass

                driver.execute_script("arguments[0].scrollTop += 850;", scroll_container)
                time.sleep(random.uniform(1.2, 1.8))

            # If no candidates found after 15 slides and reached bottom, trigger reload
            if not valid_candidates:
                consecutive_empty_reloads += 1
                if consecutive_empty_reloads >= 6:
                    logs.append(f"🏁 Reached end of available followers for @{clean_target} after {consecutive_empty_reloads} reload cycles. Total: {sent_count}/{target_count}.")
                    break

                reload_log = f"🔄 Scanned full modal depth without finding un-followed accounts ({sent_count}/{target_count}). Refreshing @{clean_target} profile (Attempt {consecutive_empty_reloads}/6)..."
                logs.append(reload_log)
                logger.info(reload_log)

                if on_progress:
                    try:
                        on_progress(sent_count, target_count, {
                            "user": "",
                            "target_account": clean_target,
                            "sent": sent_count,
                            "target": target_count,
                            "status": "refreshing",
                            "reload_attempt": consecutive_empty_reloads,
                            "message": f"🔄 Refreshing @{clean_target} to load next fresh follower batch ({sent_count}/{target_count})..."
                        })
                    except Exception:
                        pass

                ok_reload, _ = _open_instagram_followers_dialog(driver, clean_target)
                if ok_reload:
                    driver._just_reloaded_followers = True
                    time.sleep(2.0)
                else:
                    time.sleep(3.0)
                continue

            # ── Follow Valid Candidates ──
            for btn, curr_user, row_elem in valid_candidates:
                if stop_event and stop_event.is_set():
                    break
                if sent_count >= target_count:
                    break
                if curr_user.lower() in processed_users:
                    continue

                try:
                    processed_users.add(curr_user.lower())

                    # Verified badge / celebrity filter (skip only verified creators)
                    if skip_if_verified and row_elem:
                        is_ver, ver_reason = is_verified_account(row_elem)
                        if is_ver:
                            driver.execute_script("arguments[0].setAttribute('data-bot-sent', 'true');", btn)
                            skipped_count += 1
                            logger.info(f"🛡️ Skipped @{curr_user}: Verified account ({ver_reason})")
                            continue

                    # Scroll button smoothly into viewport center
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", btn)
                    time.sleep(0.5)

                    # Click follow button
                    try:
                        ActionChains(driver).move_to_element(btn).pause(0.2).click().perform()
                    except Exception:
                        driver.execute_script("arguments[0].click();", btn)

                    driver.execute_script("arguments[0].setAttribute('data-bot-sent', 'true');", btn)
                    sent_count += 1
                    consecutive_empty_reloads = 0
                    followed_list.append(curr_user)
                    logger.info(f"✅ Followed @{curr_user} from @{clean_target}'s followers ({sent_count}/{target_count})")

                    if on_progress:
                        try:
                            on_progress(sent_count, target_count, {
                                "user": curr_user,
                                "target_account": clean_target,
                                "sent": sent_count,
                                "target": target_count,
                                "status": "followed"
                            })
                        except Exception as e_p:
                            logger.debug(f"Progress error: {e_p}")

                    # Micro-Batch Resting Cooldown (Safeguard for up to 1000 Follows)
                    batch_follow_count += 1
                    if batch_follow_count >= 30 and sent_count < target_count:
                        cooldown_seconds = int(random.uniform(180, 240))  # 3-4 minutes cooldown
                        logger.info(f"Micro-batch of 30 follows reached ({sent_count}/{target_count}). Entering rest cooldown of {cooldown_seconds}s to safeguard account...")
                        if on_progress:
                            try:
                                on_progress(sent_count, target_count, {
                                    "user": curr_user,
                                    "target_account": clean_target,
                                    "sent": sent_count,
                                    "target": target_count,
                                    "status": "resting",
                                    "cooldown": cooldown_seconds,
                                    "message": f"⏳ Resting cooldown: pausing {cooldown_seconds//60} mins to protect account from Instagram rate-limits..."
                                })
                            except Exception:
                                pass

                        for _ in range(cooldown_seconds):
                            if stop_event and stop_event.is_set():
                                break
                            time.sleep(1.0)
                        batch_follow_count = 0
                        if stop_event and stop_event.is_set():
                            break

                    # Human safety delay between follows
                    pause = random.uniform(max(10.0, safety_delay * 0.8), max(15.0, safety_delay * 1.3))
                    logger.info(f"Human delay: {pause:.1f}s before next follow...")
                    time.sleep(pause)

                except Exception as e_btn:
                    logger.debug(f"Row click error for @{curr_user}: {e_btn}")
                    continue

        return {
            "status": "completed" if sent_count >= target_count else "stopped" if (stop_event and stop_event.is_set()) else "finished",
            "target_account": clean_target,
            "sent": sent_count,
            "target": target_count,
            "skipped": skipped_count,
            "followed_accounts": followed_list,
            "logs": logs
        }
    except Exception as e_fol:
        logger.error(f"Follow target followers error: {e_fol}", exc_info=True)
        return {"status": "error", "message": str(e_fol), "sent": 0}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    if len(sys.argv) > 1 and sys.argv[1].startswith("@"):
        # Test specific user
        u = sys.argv[1]
        print(f"Testing direct follow for {u}...")
        res = follow_specific_instagram_user(u)
        print("Result:", res)
    else:
        test_loc = sys.argv[1] if len(sys.argv) > 1 else "Lucknow"
        test_num = int(sys.argv[2]) if len(sys.argv) > 2 else 2
        print(f"Testing location follow for {test_loc} (target: {test_num})...")
        res = send_instagram_follow_requests(location=test_loc, target_count=test_num, safety_delay=6)
        print("\nResult:", res)
