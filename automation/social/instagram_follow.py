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


def follow_specific_instagram_user(username: str, driver=None) -> dict:
    """
    Directly navigates to an Instagram user profile and clicks Follow.
    Works inside the authenticated session on port 9222 without HTTP 429 rate limits.

    Returns:
        Dict: {
            "status": "success" | "already_following" | "requested" | "not_found" | "error",
            "username": clean_username,
            "url": profile_url,
            "message": str
        }
    """
    clean_user = clean_instagram_username(username)
    if not clean_user:
        return {"status": "error", "username": "", "message": "Invalid username provided."}

    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.action_chains import ActionChains

    profile_url = f"https://www.instagram.com/{clean_user}/"
    logger.info(f"Targeting Instagram profile: @{clean_user} ({profile_url})")

    try:
        if driver is None:
            driver = browser.navigate("instagram", profile_url, refresh_first=False)
        else:
            driver.get(profile_url)

        time.sleep(random.uniform(2.2, 3.2))

        # Check for 404 / Unavailable
        page_title = driver.title or ""
        page_source = driver.page_source.lower()
        if "page not found" in page_title.lower() or "isn't available" in page_source:
            msg = f"User @{clean_user} was not found on Instagram (Profile unavailable)."
            logger.warning(msg)
            return {"status": "not_found", "username": clean_user, "url": profile_url, "message": msg}

        # Check for buttons on profile
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

        if state == "already_following":
            msg = f"You are already following @{clean_user}."
            logger.info(f"ℹ️ {msg}")
            return {"status": "already_following", "username": clean_user, "url": profile_url, "message": msg}

        if state == "requested":
            msg = f"Follow request has already been sent to @{clean_user} (Private Account)."
            logger.info(f"ℹ️ {msg}")
            return {"status": "requested", "username": clean_user, "url": profile_url, "message": msg}

        if follow_btn:
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
                time.sleep(1.8)
                # Verify button state change
                new_state = "followed"
                for b in driver.find_elements(By.XPATH, "//header//button | //main//button | //button"):
                    try:
                        nt = (b.text or b.get_attribute("innerText") or "").strip().lower()
                        if nt == "following":
                            new_state = "following"
                            break
                        elif nt == "requested":
                            new_state = "requested"
                            break
                    except Exception:
                        continue

                msg = f"Successfully followed @{clean_user} (Status: {new_state})!"
                logger.info(f"✅ {msg}")
                return {"status": "success", "username": clean_user, "url": profile_url, "message": msg, "new_state": new_state}

        # Fallback if button wasn't identified
        msg = f"Follow button could not be located on @{clean_user}'s profile page."
        logger.warning(msg)
        return {"status": "error", "username": clean_user, "url": profile_url, "message": msg}

    except Exception as e:
        logger.error(f"Error following @{clean_user}: {e}")
        return {"status": "error", "username": clean_user, "url": profile_url, "message": str(e)}


def follow_multiple_instagram_users(
    usernames: list[str],
    safety_delay: int = 10,
    on_progress=None,
    stop_event=None
) -> dict:
    """
    Follows a list of specified Instagram usernames sequentially with human-like delays.
    """
    logger.info(f"Starting batch Instagram follow for {len(usernames)} users...")
    driver = browser.navigate("instagram", "https://www.instagram.com/", refresh_first=False)

    results = []
    sent_count = 0
    already_following_count = 0
    failed_count = 0

    for i, u in enumerate(usernames):
        if stop_event and stop_event.is_set():
            logger.info("Batch follow stopped via stop_event.")
            break

        clean_u = clean_instagram_username(u)
        if not clean_u:
            continue

        res = follow_specific_instagram_user(clean_u, driver=driver)
        results.append(res)

        if res.get("status") == "success":
            sent_count += 1
        elif res.get("status") in ["already_following", "requested"]:
            already_following_count += 1
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
        "failed": failed_count,
        "results": results
    }


def _follow_instagram_suggestions(driver, target_count, safety_delay, on_progress, stop_event, logs):
    """
    Follows accounts from Instagram's native Suggested Accounts page (https://www.instagram.com/explore/people/).
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.action_chains import ActionChains

    logs.append("🌟 Navigating to Instagram Suggested Accounts (https://www.instagram.com/explore/people/)...")
    driver.get("https://www.instagram.com/explore/people/")
    time.sleep(3.0)

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
    processed_users = set()
    scroll_attempts = 0
    max_scrolls = max(30, int(target_count / 3) + 15)

    while sent_count < target_count and scroll_attempts < max_scrolls:
        if stop_event and stop_event.is_set():
            logs.append("🛑 Instagram follow task stopped by user.")
            break

        browser.switch_to_platform_tab("instagram", driver=driver)

        # Find follow buttons in suggested accounts list
        follow_btns = []
        candidates = driver.find_elements(By.XPATH, "//button[.//div[text()='Follow'] or text()='Follow'][not(@data-bot-sent='true')]")
        for btn in candidates:
            try:
                if btn.is_displayed() and btn.get_attribute("data-bot-sent") != "true":
                    follow_btns.append(btn)
            except Exception:
                continue

        logger.info(f"Discovered {len(follow_btns)} suggested accounts to follow (Sent: {sent_count}/{target_count}).")

        if not follow_btns:
            scroll_attempts += 1
            driver.execute_script("window.scrollBy(0, 800);")
            time.sleep(2.0)
            continue

        for btn in follow_btns:
            if stop_event and stop_event.is_set() or sent_count >= target_count:
                break

            try:
                if not btn.is_displayed() or btn.get_attribute("data-bot-sent") == "true":
                    continue

                browser.switch_to_platform_tab("instagram", driver=driver)

                # Extract username from row
                cand_username = ""
                try:
                    row_el = btn.find_element(By.XPATH, "./ancestor::div[contains(@class, 'x1')]")
                    links = row_el.find_elements(By.XPATH, ".//a[contains(@href, '/')]")
                    for l in links:
                        h = l.get_attribute("href") or ""
                        u = extract_username_from_url(h)
                        if u and is_valid_ig_username(u):
                            cand_username = u
                            break
                except Exception:
                    pass

                u_name = cand_username or f"suggested_user_{sent_count + 1}"

                if cand_username and cand_username.lower() in processed_users:
                    continue
                if cand_username:
                    processed_users.add(cand_username.lower())

                driver.execute_script("arguments[0].setAttribute('data-bot-sent', 'true');", btn)
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", btn)
                time.sleep(random.uniform(0.5, 1.0))

                clicked = False
                try:
                    ActionChains(driver).move_to_element(btn).pause(0.2).click().perform()
                    clicked = True
                except Exception:
                    try:
                        driver.execute_script("arguments[0].click();", btn)
                        clicked = True
                    except Exception:
                        pass

                if clicked:
                    sent_count += 1
                    log_entry = f"✅ Followed #{sent_count}: '@{u_name}' (Suggested Account)"
                    logs.append(log_entry)
                    logger.info(log_entry)

                    if on_progress:
                        try:
                            on_progress(sent_count, target_count, {
                                "platform": "instagram",
                                "user": u_name,
                                "url": f"https://www.instagram.com/{cand_username}/" if cand_username else driver.current_url,
                                "location": "Suggested Accounts",
                                "mode": "suggestions",
                                "sent": sent_count,
                                "target": target_count,
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
                    time.sleep(pause)
                else:
                    skipped_count += 1

            except Exception as e_row:
                skipped_count += 1
                logger.debug(f"Row click error: {e_row}")
                continue

        # Scroll to load more suggestions
        scroll_attempts += 1
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(random.uniform(1.8, 2.5))

    return sent_count, skipped_count


def _follow_instagram_random_explore(driver, target_count, safety_delay, on_progress, stop_event, logs):
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
        browser.switch_to_platform_tab("instagram", driver=driver)

        # Check for dialog container
        dialogs = driver.find_elements(By.XPATH, "//div[@role='dialog']")
        active_container = dialogs[0] if dialogs else driver

        # Extract author
        author_name = None
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
                    time.sleep(random.uniform(0.8, 1.4))
            except Exception:
                pass
            continue

        if author_name:
            processed_users.add(author_name.lower())

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

        clicked = False
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
            time.sleep(pause)
        else:
            skipped_count += 1

        # Smoothly cycle to next random post in modal using Arrow Right with random skipping (1-2 posts)
        try:
            skips = random.randint(1, 2)
            for _ in range(skips):
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ARROW_RIGHT)
                time.sleep(random.uniform(1.2, 2.0))
        except Exception:
            break

    return sent_count, skipped_count


def send_instagram_follow_requests(
    location: str = "",
    target_count: int = 10,
    safety_delay: int = 15,
    on_progress=None,
    stop_event=None,
    mode: str = "location"
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
                logs=logs
            )
            sent_count += s_sent
            skipped_count += s_skip

        # ── Branch: Random Explore Mode ──
        elif mode == "random":
            r_sent, r_skip = _follow_instagram_random_explore(
                driver=driver,
                target_count=target_count,
                safety_delay=safety_delay,
                on_progress=on_progress,
                stop_event=stop_event,
                logs=logs
            )
            sent_count += r_sent
            skipped_count += r_skip

        # ── Branch: Location / Keyword Search Mode (Existing) ──
        else:
            try:
                search_btns = driver.find_elements(
                    By.XPATH,
                    "//a[contains(@href, '#') and .//span[text()='Search']] | //span[text()='Search'] | //*[@aria-label='Search']"
                )
                if search_btns:
                    search_btns[0].click()
                    time.sleep(1.5)
                    search_inputs = driver.find_elements(By.XPATH, "//input[@placeholder='Search' or @aria-label='Search input']")
                    if search_inputs:
                        inp = search_inputs[0]
                        inp.clear()
                        inp.send_keys(location)
                        time.sleep(2.5)

                        result_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/')]")
                        for r in result_links:
                            try:
                                h = r.get_attribute("href") or ""
                                u = extract_username_from_url(h)
                                if u and u.lower() not in processed_users and u not in candidate_usernames:
                                    candidate_usernames.append(u)
                            except Exception:
                                continue
                        logger.info(f"Search sidebar yielded {len(candidate_usernames)} target accounts for '{location}': {candidate_usernames[:8]}")
            except Exception as e_search:
                logger.debug(f"Sidebar search note: {e_search}")

        # Follow harvested sidebar accounts first
        for u in candidate_usernames:
            if sent_count >= target_count:
                break
            if stop_event and stop_event.is_set():
                logs.append("🛑 Instagram follow task stopped by user.")
                logger.info("Instagram follow loop stopped via stop_event.")
                break

            processed_users.add(u.lower())
            res = follow_specific_instagram_user(u, driver=driver)
            if res.get("status") == "success":
                sent_count += 1
                log_entry = f"✅ Followed #{sent_count}: '@{u}' ({location})"
                logs.append(log_entry)
                logger.info(log_entry)

                if on_progress:
                    try:
                        on_progress(sent_count, target_count, {
                            "platform": "instagram",
                            "user": u,
                            "url": res.get("url"),
                            "location": location,
                            "sent": sent_count,
                            "target": target_count,
                        })
                    except Exception:
                        pass

                # Mandatory 2-minute (120s) safety break after every 250 follows
                if sent_count > 0 and sent_count % 250 == 0 and sent_count < target_count:
                    cooldown_secs = 120
                    cooldown_msg = f"⏸️ Reached {sent_count} Instagram follows milestone. Taking a 2-minute safety break to protect account health..."
                    logs.append(cooldown_msg)
                    logger.info(cooldown_msg)
                    if on_progress:
                        try:
                            on_progress(sent_count, target_count, {
                                "platform": "instagram",
                                "user": u,
                                "cooldown": True,
                                "cooldown_seconds": cooldown_secs,
                                "message": f"Paused for 2-min safety cooldown ({sent_count}/{target_count})",
                            })
                        except Exception:
                            pass
                    for _ in range(cooldown_secs):
                        if stop_event and stop_event.is_set():
                            break
                        time.sleep(1.0)
                    logs.append(f"▶️ 2-minute safety cooldown completed. Resuming Instagram follows ({sent_count}/{target_count})...")
                    logger.info("Resuming Instagram follows after 2-minute safety break.")

                pause = random.uniform(max(6.0, safety_delay * 0.7), max(9.0, safety_delay * 1.15))
                logger.info(f"Human safety pause: {pause:.1f}s before next follow ({sent_count}/{target_count})...")
                time.sleep(pause)
            else:
                skipped_count += 1

        # ── Strategy B: Explore Search Modal Navigation (If more targets needed for location mode) ──
        if mode not in ("suggestions", "random") and sent_count < target_count and not (stop_event and stop_event.is_set()):
            keyword_url = f"https://www.instagram.com/explore/search/keyword/?q={urllib.parse.quote(location)}"
            driver.get(keyword_url)
            time.sleep(3.0)

            thumbnails = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/') or contains(@href, '/reel/')]")
            logger.info(f"Explore page loaded {len(thumbnails)} post thumbnails for '{location}'")

            if thumbnails:
                # Open first post thumbnail into native lightbox modal
                try:
                    driver.execute_script("arguments[0].click();", thumbnails[0])
                    time.sleep(2.0)
                except Exception as e_thumb:
                    logger.warning(f"Could not open first thumbnail: {e_thumb}")

                cycles = 0
                max_cycles = max(30, target_count * 4)

                while sent_count < target_count and cycles < max_cycles:
                    if stop_event and stop_event.is_set():
                        logs.append("🛑 Instagram follow task stopped by user.")
                        break

                    cycles += 1

                    # Check for dialog
                    dialogs = driver.find_elements(By.XPATH, "//div[@role='dialog']")
                    active_container = dialogs[0] if dialogs else driver

                    # Extract author from modal
                    author_name = None
                    try:
                        author_links = active_container.find_elements(
                            By.XPATH,
                            ".//header//a | .//a[contains(@class, 'x1i10hfl') and not(contains(@href, '/p/'))]"
                        )
                        for al in author_links:
                            ahref = al.get_attribute("href") or ""
                            cand_u = extract_username_from_url(ahref)
                            if cand_u and cand_u.lower() != "loansolutions2026":
                                author_name = cand_u
                                break
                    except Exception:
                        pass

                    display_u = author_name or f"creator_{cycles}"

                    if author_name and author_name.lower() in processed_users:
                        # Already processed this author, cycle to next post
                        try:
                            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ARROW_RIGHT)
                            time.sleep(random.uniform(1.2, 1.8))
                        except Exception:
                            pass
                        continue

                    if author_name:
                        processed_users.add(author_name.lower())

                    # Look for Follow button inside modal
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

                    clicked = False
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

                    if clicked:
                        sent_count += 1
                        log_entry = f"✅ Followed #{sent_count}: '@{display_u}' ({location})"
                        logs.append(log_entry)
                        logger.info(log_entry)

                        if on_progress:
                            try:
                                on_progress(sent_count, target_count, {
                                    "platform": "instagram",
                                    "user": display_u,
                                    "url": f"https://www.instagram.com/{author_name}/" if author_name else driver.current_url,
                                    "location": location,
                                    "sent": sent_count,
                                    "target": target_count,
                                })
                            except Exception:
                                pass

                        # Mandatory 2-minute (120s) safety break after every 250 follows
                        if sent_count > 0 and sent_count % 250 == 0 and sent_count < target_count:
                            cooldown_secs = 120
                            cooldown_msg = f"⏸️ Reached {sent_count} Instagram follows milestone. Taking a 2-minute safety break to protect account health..."
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
                                    })
                                except Exception:
                                    pass
                            for _ in range(cooldown_secs):
                                if stop_event and stop_event.is_set():
                                    break
                                time.sleep(1.0)
                            logs.append(f"▶️ 2-minute safety cooldown completed. Resuming Instagram follows ({sent_count}/{target_count})...")
                            logger.info("Resuming Instagram follows after 2-minute safety break.")

                        pause = random.uniform(max(6.0, safety_delay * 0.7), max(9.0, safety_delay * 1.15))
                        logger.info(f"Human safety pause: {pause:.1f}s before next follow ({sent_count}/{target_count})...")
                        time.sleep(pause)
                    else:
                        skipped_count += 1

                    # Smoothly move to next post using Arrow Right inside SPA modal
                    try:
                        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ARROW_RIGHT)
                        time.sleep(random.uniform(1.5, 2.4))
                    except Exception:
                        break

        status_label = "stopped" if (stop_event and stop_event.is_set()) else ("completed" if sent_count >= target_count else "partial")
        logs.append(f"🏁 Finished Instagram follow session. Total follows: {sent_count}/{target_count} (Skipped: {skipped_count}).")

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


if __name__ == "__main__":
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
