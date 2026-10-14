"""
Instagram Location-Based Follow Automator.
Finds active user profiles by location tag / keyword search and sends follow requests with human-like delays.
Follows the standard outreach template matching facebook_friends.py.
"""
import sys
import time
import random
import urllib.parse
import re
import logging
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from browser.driver import browser
from config import PLATFORM_URLS

logger = logging.getLogger("automation.social.instagram_follow")


def extract_ig_profile_info(btn, loc: str = "") -> tuple[str, str]:
    """
    Extracts username and profile URL from ancestors of a follow button.
    Mirrors extract_fb_profile_info for consistency across platforms.
    """
    from selenium.webdriver.common.by import By
    real_name = ""
    real_url = ""
    try:
        for level in range(1, 10):
            card = btn.find_element(By.XPATH, f"./ancestor::div[{level}]")
            links = card.find_elements(By.CSS_SELECTOR, "a[role='link'], a[href*='instagram.com/'], a")
            for l in links:
                ltxt = (l.get_attribute("innerText") or l.text or "").strip().split("\n")[0].strip()
                lhref = l.get_attribute("href") or ""
                # Skip generic Instagram system URLs
                if any(x in lhref.lower() for x in ["/explore", "/direct", "/reels", "/stories", "/legal", "/about", "#"]):
                    continue
                if ltxt and ltxt.lower() not in [
                    "follow", "following", "requested", "message", "see all",
                    "suggested for you", "switch", "profile"
                ] and not ltxt.isdigit():
                    real_name = ltxt.lstrip("@")
                    real_url = lhref.split("?")[0]
                    break
            if real_name:
                break
    except Exception:
        pass

    return real_name, real_url


def send_instagram_follow_requests(
    location: str,
    target_count: int = 10,
    safety_delay: int = 15,
    on_progress=None,
    stop_event=None
) -> dict:
    """
    Searches for active profiles by location on Instagram and sends follow requests like a human.

    Args:
        location: Target location (e.g., 'New Delhi', 'Mumbai', 'New York').
        target_count: Number of follow requests to send.
        safety_delay: Baseline seconds delay between requests (randomized +-30%).
        on_progress: Optional callback function(sent_count, target_count, details).
        stop_event: Optional threading.Event to signal early cancellation.

    Returns:
        Dict with status, count of sent requests, and activity logs.
    """
    logger.info(f"Starting Instagram follow requests for location: '{location}' (Target: {target_count})...")
    logs = []
    sent_count = 0
    skipped_count = 0
    processed_users = set()
    processed_urls = set()

    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains

    try:
        # Build clean tag and keyword query URLs
        clean_tag = re.sub(r"[^a-zA-Z0-9]", "", location).lower()
        tag_url = f"https://www.instagram.com/explore/tags/{clean_tag}/"
        keyword_url = f"https://www.instagram.com/explore/search/keyword/?q={urllib.parse.quote(location)}"

        driver = browser.navigate("instagram", keyword_url, refresh_first=True)
        logs.append(f"🔄 Instagram search refreshed - loading fresh posts and accounts for '{location}'")

        # Check if redirected to login
        current_url = driver.current_url.lower()
        if "accounts/login" in current_url:
            msg = "Instagram login required. Please verify login in Chrome."
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

        time.sleep(random.uniform(2.5, 3.8))

        scroll_attempts = 0
        max_scroll_attempts = 25

        while sent_count < target_count and scroll_attempts < max_scroll_attempts:
            if stop_event and stop_event.is_set():
                logs.append("🛑 Instagram follow task stopped by user.")
                logger.info("Instagram follow loop stopped via stop_event.")
                break

            # ── Strategy 1: Check for visible direct Follow buttons on screen ──
            xpaths = [
                "//div[contains(@class, 'x1i10hfl') and @role='button' and not(@data-bot-sent='true')]",
                "//div[@role='button' and not(@data-bot-sent='true')]",
                "//button[not(@data-bot-sent='true')]"
            ]

            follow_buttons = []
            seen_ids = set()
            for xp in xpaths:
                try:
                    for b in driver.find_elements(By.XPATH, xp):
                        try:
                            inner = (b.get_attribute("innerText") or "").strip().lower()
                            if inner == "follow" and b.id not in seen_ids and b.get_attribute("data-bot-sent") != "true":
                                seen_ids.add(b.id)
                                follow_buttons.append(b)
                        except Exception:
                            continue
                except Exception:
                    continue

            if follow_buttons:
                for btn in follow_buttons:
                    if stop_event and stop_event.is_set() or sent_count >= target_count:
                        break

                    try:
                        if btn.get_attribute("data-bot-sent") == "true":
                            continue

                        # Extract profile name and URL
                        user_name, user_url = extract_ig_profile_info(btn, location)
                        display_name = user_name if user_name else f"Creator in {location}"

                        if user_name and user_name.lower() in processed_users:
                            continue
                        if user_url and user_url in processed_urls:
                            continue

                        if user_name:
                            processed_users.add(user_name.lower())
                        if user_url:
                            processed_urls.add(user_url)

                        # Tag in DOM so we never click again
                        driver.execute_script("arguments[0].setAttribute('data-bot-sent', 'true');", btn)
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", btn)
                        time.sleep(random.uniform(0.6, 1.2))

                        clicked = False
                        try:
                            ActionChains(driver).move_to_element(btn).pause(0.3).click().perform()
                            clicked = True
                        except Exception:
                            pass

                        if not clicked:
                            try:
                                driver.execute_script("arguments[0].click();", btn)
                                clicked = True
                            except Exception:
                                pass

                        if not clicked:
                            skipped_count += 1
                            continue

                        sent_count += 1
                        log_entry = f"✅ Followed #{sent_count}: '@{display_name}' ({location})"
                        logs.append(log_entry)
                        logger.info(log_entry)

                        if on_progress:
                            try:
                                on_progress(sent_count, target_count, {
                                    "platform": "instagram",
                                    "user": display_name,
                                    "url": user_url,
                                    "location": location,
                                    "sent": sent_count,
                                    "target": target_count,
                                })
                            except Exception as e_cb:
                                logger.debug(f"Progress callback note: {e_cb}")

                        if sent_count >= target_count:
                            break

                        current_delay = random.uniform(max(6.0, safety_delay * 0.7), max(9.0, safety_delay * 1.15))
                        logger.info(f"Human safety pause: {current_delay:.1f}s before next follow ({sent_count}/{target_count})...")
                        time.sleep(current_delay)

                    except Exception as e_f:
                        skipped_count += 1
                        logger.debug(f"Direct follow button click error: {e_f}")

            # ── Strategy 2: Location-Based Posts author follow ──
            if sent_count < target_count:
                post_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/') or contains(@href, '/reel/')]")
                valid_posts = []
                for pl in post_links:
                    try:
                        href = pl.get_attribute("href") or ""
                        if href and href not in processed_urls:
                            valid_posts.append(href)
                    except Exception:
                        continue

                for post_href in valid_posts[:6]:
                    if stop_event and stop_event.is_set() or sent_count >= target_count:
                        break

                    processed_urls.add(post_href)

                    try:
                        # Navigate directly to the post to inspect author
                        driver.get(post_href)
                        time.sleep(random.uniform(2.5, 3.5))

                        # Look for Follow button in the post header
                        post_follow_candidates = driver.find_elements(
                            By.XPATH,
                            "//div[contains(@class, 'x1i10hfl') and @role='button'] | //div[@role='button'] | //button"
                        )

                        post_btn = None
                        for cand in post_follow_candidates:
                            try:
                                inner = (cand.get_attribute("innerText") or "").strip().lower()
                                if inner == "follow" and cand.is_displayed():
                                    post_btn = cand
                                    break
                            except Exception:
                                continue

                        if post_btn:
                            # Extract author username
                            author_name = "Creator in " + location
                            author_url = ""
                            try:
                                author_links = driver.find_elements(By.XPATH, "//header//a | //div[contains(@class, 'x1i10hfl')]//a")
                                for al in author_links:
                                    h = al.get_attribute("href") or ""
                                    t = (al.get_attribute("innerText") or al.text or "").strip()
                                    if h and not any(x in h for x in ["/explore", "/direct", "/reels", "/p/"]):
                                        author_name = t or h.rstrip("/").split("/")[-1]
                                        author_url = h
                                        break
                            except Exception:
                                pass

                            if author_name.lower() in processed_users:
                                continue
                            processed_users.add(author_name.lower())

                            # Click follow on author
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", post_btn)
                            time.sleep(0.5)

                            clicked = False
                            try:
                                ActionChains(driver).move_to_element(post_btn).pause(0.3).click().perform()
                                clicked = True
                            except Exception:
                                pass

                            if not clicked:
                                try:
                                    driver.execute_script("arguments[0].click();", post_btn)
                                    clicked = True
                                except Exception:
                                    pass

                            if clicked:
                                sent_count += 1
                                log_entry = f"✅ Followed #{sent_count}: '@{author_name}' ({location})"
                                logs.append(log_entry)
                                logger.info(log_entry)

                                if on_progress:
                                    try:
                                        on_progress(sent_count, target_count, {
                                            "platform": "instagram",
                                            "user": author_name,
                                            "url": author_url or post_href,
                                            "location": location,
                                            "sent": sent_count,
                                            "target": target_count,
                                        })
                                    except Exception as e_cb:
                                        logger.debug(f"Progress callback note: {e_cb}")

                                if sent_count >= target_count:
                                    break

                                current_delay = random.uniform(max(6.0, safety_delay * 0.7), max(9.0, safety_delay * 1.15))
                                logger.info(f"Human safety pause: {current_delay:.1f}s before next follow...")
                                time.sleep(current_delay)
                            else:
                                skipped_count += 1

                    except Exception as e_post:
                        logger.debug(f"Post navigation error: {e_post}")
                        skipped_count += 1

                # If still under target, return to the keyword search page to scroll down
                if sent_count < target_count:
                    try:
                        driver.get(keyword_url)
                        time.sleep(2.0)
                    except Exception:
                        pass

            # Scroll down to load more content
            scroll_attempts += 1
            scroll_y = random.randint(500, 900)
            driver.execute_script(f"window.scrollBy(0, {scroll_y});")
            time.sleep(random.uniform(2.0, 3.5))

        status_label = "stopped" if (stop_event and stop_event.is_set()) else ("completed" if sent_count >= target_count else "partial")
        logs.append(f"🏁 Finished Instagram follow session. Total follows: {sent_count}/{target_count}.")

        return {
            "status": status_label,
            "platform": "instagram",
            "location": location,
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
            "location": location,
            "sent": sent_count,
            "target": target_count,
            "error": str(e),
            "logs": logs,
        }


if __name__ == "__main__":
    import sys
    test_loc = sys.argv[1] if len(sys.argv) > 1 else "Mumbai"
    test_num = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    res = send_instagram_follow_requests(location=test_loc, target_count=test_num, safety_delay=8)
    print("\nResult:", res)
