"""
Facebook Friend Requests Manager & Auto-Accept Engine.
Detects pending incoming friend requests, counts them, accepts all or batch with human cadence,
and optionally likes the requester's recent post/photo.
"""
import os
import sys
import time
import random
import logging
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
sys.path.append(str(BASE_DIR / "automation"))

from browser.driver import browser
from config import PLATFORM_URLS

logger = logging.getLogger("automation.social.facebook_accept")

ACTIVE_ACCEPT_TASKS = {}


def get_pending_friend_requests(max_scrolls: int = 4) -> dict:
    """
    Connects to Facebook and retrieves the count and details of pending incoming friend requests.
    """
    logger.info("Scanning Facebook for pending friend requests...")
    try:
        from selenium.webdriver.common.by import By

        driver = browser.navigate("facebook", "https://www.facebook.com/friends/requests", refresh_first=True)

        from social.facebook import is_facebook_login_needed
        if is_facebook_login_needed(driver):
            return {
                "status": "login_required",
                "count": 0,
                "requests": [],
                "message": "Facebook login required. Please verify login in Chrome on port 9222.",
            }

        time.sleep(2.5)

        # Micro-scrolls to trigger initial lazy loading
        for _ in range(max_scrolls):
            driver.execute_script("window.scrollBy(0, 600);")
            time.sleep(0.8)

        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1.0)

        # Find confirm buttons
        confirm_selectors = [
            "//div[@aria-label='Confirm']",
            "//span[text()='Confirm']/ancestor::div[@role='button']",
            "//div[@role='button'][.//span[text()='Confirm']]",
        ]

        confirm_btns = []
        for sel in confirm_selectors:
            found = driver.find_elements(By.XPATH, sel)
            if found:
                confirm_btns = found
                break

        total_found = len(confirm_btns)
        requests = []
        seen_names = set()

        for i, btn in enumerate(confirm_btns):
            try:
                name = ""
                profile_url = ""
                mutual = ""
                time_ago = ""

                # Card container
                card = btn.find_element(By.XPATH, "./ancestor::div[6]")
                card_text = card.text.split("\n")

                if card_text:
                    name = card_text[0].strip()

                for line in card_text[1:]:
                    line_clean = line.strip().lower()
                    if "mutual" in line_clean:
                        mutual = line.strip()
                    elif any(u in line_clean for u in ["m", "h", "d", "w", "y"]) and len(line_clean) <= 5:
                        time_ago = line.strip()

                # Find profile link
                links = card.find_elements(By.TAG_NAME, "a")
                for l in links:
                    href = l.get_attribute("href") or ""
                    if "facebook.com" in href and not any(x in href for x in ["/friends", "/messages", "/notifications"]):
                        profile_url = href.split("?")[0] if "profile.php" not in href else href
                        break

                if name and name not in seen_names and name.lower() not in ["confirm", "delete"]:
                    seen_names.add(name)
                    requests.append({
                        "id": f"req_{i+1}",
                        "name": name,
                        "profile_url": profile_url,
                        "mutual_friends": mutual,
                        "time_ago": time_ago,
                    })
            except Exception as e:
                logger.debug(f"Parsing friend request card error: {e}")

        # Also parse count from page title if available, e.g. "(20+) Friend requests | Facebook"
        title = driver.title or ""
        title_count = ""
        if "(" in title and ")" in title:
            try:
                title_count = title.split("(")[1].split(")")[0]
            except Exception:
                pass

        logger.info(f"Scan complete: Found {len(requests)} parsed requests (buttons: {total_found}, title: {title_count})")
        return {
            "status": "success",
            "count": len(requests) if requests else total_found,
            "title_badge": title_count,
            "requests": requests,
        }

    except Exception as e:
        logger.error(f"Error getting pending friend requests: {e}", exc_info=True)
        return {
            "status": "error",
            "count": 0,
            "requests": [],
            "message": str(e),
        }


def accept_facebook_friend_requests(
    target_count: int = None,
    like_recent: bool = False,
    safety_delay: int = 3,
    on_progress=None,
    stop_event=None,
    campaign_id: str = None,
) -> dict:
    """
    Accepts pending incoming friend requests on Facebook with human-like cadence.
    Optionally visits the requester profile and likes their recent post.
    """
    logger.info(f"Starting accept_facebook_friend_requests: target={target_count}, like_recent={like_recent}, delay={safety_delay}s")
    logs = []
    accepted_count = 0
    liked_count = 0
    accepted_people = []

    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.action_chains import ActionChains

    try:
        driver = browser.navigate("facebook", "https://www.facebook.com/friends/requests", refresh_first=True)
        logs.append("🌐 Navigated to Facebook Friend Requests page")

        from social.facebook import is_facebook_login_needed
        if is_facebook_login_needed(driver):
            msg = "Facebook login required. Please verify login in Chrome on port 9222."
            logs.append(f"⚠️ {msg}")
            return {"status": "login_required", "accepted": 0, "logs": logs}

        time.sleep(random.uniform(2.0, 3.5))

        # Main processing loop
        max_scroll_tries = 15
        scroll_try = 0

        while True:
            # Check stop flag
            if stop_event and stop_event.is_set():
                logs.append("🛑 Accept task stopped by user.")
                break

            if campaign_id:
                flag_file = BASE_DIR / "data" / f"stop_{campaign_id}.flag"
                if flag_file.exists():
                    logs.append("🛑 Stop flag detected on disk. Stopping task gracefully.")
                    break

            if target_count and target_count > 0 and accepted_count >= target_count:
                logs.append(f"🎯 Target limit of {target_count} requests reached.")
                break

            # Find visible Confirm buttons
            confirm_btns = driver.find_elements(
                By.XPATH,
                "//div[@aria-label='Confirm'] | //div[@role='button'][.//span[text()='Confirm']]"
            )

            # Filter out stale or already processed buttons
            valid_btns = []
            for b in confirm_btns:
                try:
                    if b.is_displayed():
                        valid_btns.append(b)
                except Exception:
                    pass

            if not valid_btns:
                if scroll_try < max_scroll_tries:
                    scroll_try += 1
                    driver.execute_script("window.scrollBy(0, 700);")
                    time.sleep(1.8)
                    continue
                else:
                    logs.append("✨ All pending friend requests processed!")
                    break

            # Reset scroll count since buttons were found
            scroll_try = 0
            btn = valid_btns[0]

            # Extract requester name and profile URL before clicking Confirm
            name = "Facebook User"
            profile_url = ""
            try:
                card = btn.find_element(By.XPATH, "./ancestor::div[6]")
                card_text = card.text.split("\n")
                if card_text and card_text[0].strip().lower() not in ["confirm", "delete"]:
                    name = card_text[0].strip()

                for l in card.find_elements(By.TAG_NAME, "a"):
                    h = l.get_attribute("href") or ""
                    if "facebook.com" in h and not any(x in h for x in ["/friends", "/messages", "/notifications"]):
                        profile_url = h.split("?")[0] if "profile.php" not in h else h
                        break
            except Exception:
                pass

            # Scroll button into center view
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", btn)
                time.sleep(random.uniform(0.5, 0.9))
            except Exception:
                pass

            # Human-like click
            clicked = False
            try:
                ActionChains(driver).move_to_element(btn).pause(random.uniform(0.2, 0.4)).click().perform()
                clicked = True
            except Exception:
                try:
                    driver.execute_script("arguments[0].click();", btn)
                    clicked = True
                except Exception as e_clk:
                    logs.append(f"⚠️ Click failed for {name}: {e_clk}")

            if clicked:
                accepted_count += 1
                accepted_people.append({"name": name, "profile_url": profile_url})
                msg = f"✅ Accepted friend request from <b>{name}</b>"
                logs.append(msg)
                logger.info(f"Accepted friend request #{accepted_count}: {name}")

                # Optional: Like recent post on requester profile
                if like_recent and profile_url:
                    try:
                        time.sleep(random.uniform(1.2, 1.8))
                        # Open profile in a background tab
                        original_window = driver.current_window_handle
                        driver.execute_script("window.open(arguments[0], '_blank');", profile_url)
                        time.sleep(2.0)

                        new_window = [w for w in driver.window_handles if w != original_window][-1]
                        driver.switch_to.window(new_window)
                        time.sleep(random.uniform(2.0, 3.0))

                        # Look for like buttons on their recent post
                        driver.execute_script("window.scrollBy(0, 400);")
                        time.sleep(1.2)

                        like_btns = driver.find_elements(
                            By.XPATH,
                            "//div[@aria-label='Like'][@role='button'] | //div[@role='button'][.//span[text()='Like']]"
                        )

                        for lb in like_btns:
                            try:
                                if lb.is_displayed():
                                    aria_lbl = lb.get_attribute("aria-label") or ""
                                    if "remove like" not in aria_lbl.lower():
                                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", lb)
                                        time.sleep(0.6)
                                        ActionChains(driver).move_to_element(lb).click().perform()
                                        liked_count += 1
                                        logs.append(f"👍 Liked recent post for {name}")
                                        break
                            except Exception:
                                continue

                        driver.close()
                        driver.switch_to.window(original_window)
                    except Exception as e_like:
                        logger.debug(f"Like recent post note for {name}: {e_like}")
                        try:
                            if original_window in driver.window_handles:
                                driver.switch_to.window(original_window)
                        except Exception:
                            pass

                # Progress callback
                if on_progress:
                    on_progress(accepted_count, target_count or 0, name)

                # Human safety delay between accepts
                delay = random.uniform(max(1.5, safety_delay * 0.8), safety_delay * 1.3)
                time.sleep(delay)

        logs.append(f"🎉 Complete! Accepted {accepted_count} friend requests. Liked {liked_count} posts.")
        return {
            "status": "success",
            "accepted_count": accepted_count,
            "liked_count": liked_count,
            "accepted_people": accepted_people,
            "logs": logs,
        }

    except Exception as e:
        logger.error(f"Error accepting Facebook friend requests: {e}", exc_info=True)
        logs.append(f"❌ Error: {str(e)}")
        return {
            "status": "error",
            "accepted_count": accepted_count,
            "liked_count": liked_count,
            "logs": logs,
            "message": str(e),
        }
