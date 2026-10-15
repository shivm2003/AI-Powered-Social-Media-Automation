"""
Instagram Location-Based Follow Automator.
Finds active user profiles by location tag / keyword search and sends follow requests with human-like delays.
Follows the standard outreach template matching facebook_friends.py.
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


def extract_author_from_post_page(driver) -> tuple[str, str]:
    """
    Extracts the author's username and profile URL from an Instagram post or reel page.
    Uses multi-container XPath and parses the URL path to guarantee accuracy.
    """
    from selenium.webdriver.common.by import By
    try:
        links = driver.find_elements(By.XPATH, "//article//a | //main//a | //div[@role='main']//a | //header//a")
        for l in links:
            h = l.get_attribute("href") or ""
            if h and "instagram.com/" in h and not any(x in h for x in ["/explore", "/direct", "/reels", "/p/", "/stories", "/legal", "/about", "/c/", "#"]):
                parts = [p for p in h.rstrip("/").split("/") if p]
                if len(parts) >= 3 and "instagram.com" in parts[-2]:
                    username = parts[-1]
                    if username and not username.isdigit() and username not in ["accounts", "login", "explore", "reels"]:
                        return username, h
    except Exception as e:
        logger.debug(f"Author extraction note: {e}")

    return None, None


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

        # ── Step 1: Check for visible direct Follow buttons on search page ──
        xpaths = [
            "//div[contains(@class, 'x1i10hfl') and @role='button' and not(@data-bot-sent='true')]",
            "//div[@role='button' and not(@data-bot-sent='true')]",
            "//button[not(@data-bot-sent='true')]"
        ]
        seen_ids = set()
        for xp in xpaths:
            if sent_count >= target_count:
                break
            try:
                for b in driver.find_elements(By.XPATH, xp):
                    if sent_count >= target_count or (stop_event and stop_event.is_set()):
                        break
                    try:
                        inner = (b.get_attribute("innerText") or "").strip().lower()
                        if inner == "follow" and b.id not in seen_ids and b.get_attribute("data-bot-sent") != "true":
                            seen_ids.add(b.id)
                            u_name, u_url = extract_ig_profile_info(b, location)
                            disp = u_name or f"User_{len(processed_users)+1}"
                            if u_name and u_name.lower() in processed_users:
                                continue
                            if u_name:
                                processed_users.add(u_name.lower())

                            driver.execute_script("arguments[0].setAttribute('data-bot-sent', 'true');", b)
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", b)
                            time.sleep(0.6)

                            clicked = False
                            try:
                                ActionChains(driver).move_to_element(b).pause(0.3).click().perform()
                                clicked = True
                            except Exception:
                                pass
                            if not clicked:
                                try:
                                    driver.execute_script("arguments[0].click();", b)
                                    clicked = True
                                except Exception:
                                    pass

                            if clicked:
                                sent_count += 1
                                log_entry = f"✅ Followed #{sent_count}: '@{disp}' ({location})"
                                logs.append(log_entry)
                                logger.info(log_entry)
                                if on_progress:
                                    on_progress(sent_count, target_count, {
                                        "platform": "instagram",
                                        "user": disp,
                                        "url": u_url,
                                        "location": location,
                                        "sent": sent_count,
                                        "target": target_count,
                                    })
                                pause = random.uniform(max(6.0, safety_delay * 0.7), max(9.0, safety_delay * 1.15))
                                time.sleep(pause)
                    except Exception:
                        continue
            except Exception:
                pass

        # ── Step 2: Harvest Location Post Candidates Pool ──
        candidate_queue = []
        scroll_harvests = 0
        while len(candidate_queue) < max(25, target_count * 3) and scroll_harvests < 6:
            post_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/') or contains(@href, '/reel/')]")
            for pl in post_links:
                try:
                    h = pl.get_attribute("href") or ""
                    if h and h not in processed_urls and h not in candidate_queue:
                        candidate_queue.append(h)
                except Exception:
                    continue
            # Scroll down to load more posts
            driver.execute_script("window.scrollBy(0, 800);")
            scroll_harvests += 1
            time.sleep(1.8)

        logs.append(f"📦 Harvested {len(candidate_queue)} location post candidates for '{location}'. Processing follows...")

        # ── Step 3: Process Post Authors Sequentially ──
        for post_href in candidate_queue:
            if sent_count >= target_count:
                break
            if stop_event and stop_event.is_set():
                logs.append("🛑 Instagram follow task stopped by user.")
                logger.info("Instagram follow loop stopped via stop_event.")
                break

            processed_urls.add(post_href)

            try:
                driver.get(post_href)
                time.sleep(random.uniform(2.5, 3.5))

                # Extract author username
                author_name, author_url = extract_author_from_post_page(driver)

                # If author was not identifiable from post page, use unique post slug fallback
                post_id = post_href.rstrip("/").split("/")[-1]
                effective_author = author_name or f"creator_post_{post_id}"

                if effective_author.lower() in processed_users:
                    skipped_count += 1
                    continue

                processed_users.add(effective_author.lower())

                # Check for Follow button on the post/reel page
                post_btns = driver.find_elements(
                    By.XPATH,
                    "//div[contains(@class, 'x1i10hfl') and @role='button'] | //div[@role='button'] | //button"
                )

                post_follow_btn = None
                for cand in post_btns:
                    try:
                        inner = (cand.text or cand.get_attribute("innerText") or "").strip().lower()
                        if inner == "follow" and cand.is_displayed():
                            post_follow_btn = cand
                            break
                        elif inner in ["following", "requested"]:
                            # Already followed or requested
                            post_follow_btn = None
                            break
                    except Exception:
                        continue

                clicked = False
                if post_follow_btn:
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", post_follow_btn)
                        time.sleep(0.5)
                        ActionChains(driver).move_to_element(post_follow_btn).pause(0.3).click().perform()
                        clicked = True
                    except Exception:
                        try:
                            driver.execute_script("arguments[0].click();", post_follow_btn)
                            clicked = True
                        except Exception:
                            pass

                # If post button not found or failed, try visiting their profile directly
                if not clicked and author_name and author_url:
                    try:
                        driver.get(author_url)
                        time.sleep(2.5)
                        profile_btns = driver.find_elements(By.XPATH, "//header//button | //main//button | //button")
                        for pb in profile_btns:
                            t = (pb.text or pb.get_attribute("innerText") or "").strip().lower()
                            if t == "follow" and pb.is_displayed():
                                ActionChains(driver).move_to_element(pb).pause(0.3).click().perform()
                                clicked = True
                                break
                            elif t in ["following", "requested"]:
                                # Already following
                                break
                    except Exception as e_prof:
                        logger.debug(f"Profile follow note: {e_prof}")

                if clicked:
                    sent_count += 1
                    display_tag = author_name or effective_author
                    log_entry = f"✅ Followed #{sent_count}: '@{display_tag}' ({location})"
                    logs.append(log_entry)
                    logger.info(log_entry)

                    if on_progress:
                        try:
                            on_progress(sent_count, target_count, {
                                "platform": "instagram",
                                "user": display_tag,
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
                    logger.info(f"Human safety pause: {current_delay:.1f}s before next follow ({sent_count}/{target_count})...")
                    time.sleep(current_delay)
                else:
                    skipped_count += 1

            except Exception as e_post:
                logger.debug(f"Error processing post {post_href}: {e_post}")
                skipped_count += 1

        status_label = "stopped" if (stop_event and stop_event.is_set()) else ("completed" if sent_count >= target_count else "partial")
        logs.append(f"🏁 Finished Instagram follow session. Total follows: {sent_count}/{target_count} (Skipped: {skipped_count}).")

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
    test_loc = sys.argv[1] if len(sys.argv) > 1 else "Delhi"
    test_num = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    res = send_instagram_follow_requests(location=test_loc, target_count=test_num, safety_delay=6)
    print("\nResult:", res)
