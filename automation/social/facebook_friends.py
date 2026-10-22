"""
Facebook Location-Based Friend Request Automator.
Finds people by target location and sends friend requests with human-like delays and safety limits.
"""
import time
import random
import urllib.parse
import logging
from pathlib import Path
from browser.driver import browser
from config import PLATFORM_URLS

logger = logging.getLogger("automation.social.facebook_friends")


def send_facebook_friend_requests(
    location: str = "",
    target_count: int = 10,
    safety_delay: int = 15,
    on_progress=None,
    stop_event=None,
    mode: str = "location"
) -> dict:
    """
    Searches for people or navigates to suggestions on Facebook and sends friend requests like a human.

    Args:
        location: Target location (e.g., 'New Delhi', 'Mumbai') if mode is 'location'.
        target_count: Number of friend requests to send.
        safety_delay: Baseline seconds delay between requests (randomized +-30%).
        on_progress: Optional callback function(sent_count, target_count, details).
        stop_event: Optional threading.Event to signal early cancellation.
        mode: Discovery mode - 'location' (default), 'suggestions' (PYMK), or 'random' (shuffled PYMK).

    Returns:
        Dict with status, count of sent requests, and activity logs.
    """
    mode = (mode or "location").lower().strip()
    if mode == "suggestions":
        mode_label = "🌟 Algorithmic Suggestions (People You May Know)"
        search_url = "https://www.facebook.com/friends/suggestions"
        loc_display = "Suggested Friends"
    elif mode == "random":
        mode_label = "🎲 Random Discovery (Shuffled Recommendations)"
        search_url = "https://www.facebook.com/friends/suggestions"
        loc_display = "Random Discovery"
    else:
        mode = "location"
        loc_display = location or "New Delhi"
        mode_label = f"📍 Location Search: '{loc_display}'"
        encoded_query = urllib.parse.quote(loc_display)
        search_url = f"https://www.facebook.com/search/people/?q={encoded_query}"

    logger.info(f"Starting Facebook friend requests | Mode: {mode_label} (Target: {target_count})...")
    logs = [f"🚀 Initiated Facebook outreach: {mode_label} (Target: {target_count})"]
    sent_count = 0
    skipped_count = 0
    processed_urls = set()
    processed_names = set()
    processed_elements = set()

    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.common.keys import Keys

    def extract_fb_profile_info(btn, loc: str) -> tuple[str, str]:
        real_name = ""
        real_url = ""
        try:
            for level in range(1, 10):
                card = btn.find_element(By.XPATH, f"./ancestor::div[{level}]")
                links = card.find_elements(By.CSS_SELECTOR, "a[role='link'], a[href*='facebook.com/'], a[href*='profile.php']")
                for l in links:
                    ltxt = l.text.strip().split("\n")[0].strip() if l.text else ""
                    lhref = l.get_attribute("href") or ""
                    # Skip generic Facebook system URLs
                    if any(x in lhref.lower() for x in ["/friends", "/messages", "/notifications", "/search", "/home", "/watch", "/marketplace", "/groups"]):
                        continue
                    if ltxt and ltxt.lower() not in [
                        "add friend", "friend", "friends", "message", "cancel request",
                        "request sent", "mutual friends", "see all", "remove", "follow"
                    ] and not ltxt.isdigit():
                        real_name = ltxt
                        real_url = lhref.split("?")[0] if "profile.php" not in lhref else lhref
                        break
                if real_name:
                    break
        except Exception:
            pass

        return real_name, real_url

    try:
        # Navigate to target Facebook URL with fresh page content
        driver = browser.navigate("facebook", search_url, refresh_first=True)
        logs.append(f"🔄 Navigated to {search_url} (Fresh page state ensured)")

        # Check if redirected to login
        from social.facebook import is_facebook_login_needed
        if is_facebook_login_needed(driver):
            msg = "Facebook login required. Please verify login in Chrome on port 9222."
            logs.append(f"⚠️ {msg}")
            return {"status": "login_required", "sent": 0, "logs": logs}

        # Human-like initial observation
        time.sleep(random.uniform(2.0, 3.5))

        # Main pagination / scroll loop
        scroll_attempts = 0
        max_scroll_attempts = max(100, int((target_count / 3) + 30))

        while sent_count < target_count and scroll_attempts < max_scroll_attempts:
            if stop_event and stop_event.is_set():
                logs.append("🛑 Friend request task stopped by user.")
                logger.info("Facebook friend request loop stopped via stop_event.")
                break

            # Tab isolation: Ensure active window is locked to Facebook before querying DOM
            browser.switch_to_platform_tab("facebook", driver=driver)

            # Find 'Add friend' buttons on the page using comprehensive selectors
            add_buttons = []
            seen_ids = set()
            xpaths = [
                "//div[@role='button'][contains(translate(@aria-label, 'AD', 'ad'), 'add friend') and not(@data-bot-sent='true')]",
                "//div[contains(translate(@aria-label, 'AD', 'ad'), 'add friend') and not(@data-bot-sent='true')]",
                "//span[contains(translate(text(), 'AD', 'ad'), 'add friend') and not(ancestor::div[@data-bot-sent='true'])]/ancestor::div[@role='button'][1]",
                "//span[contains(translate(text(), 'AD', 'ad'), 'add friend') and not(ancestor::div[@data-bot-sent='true'])]/ancestor::div[1]",
            ]

            for xp in xpaths:
                try:
                    candidates = driver.find_elements(By.XPATH, xp)
                    for cand in candidates:
                        try:
                            if not cand.is_displayed():
                                continue
                            if cand.get_attribute("data-bot-sent") == "true":
                                continue
                            if cand.id not in seen_ids and cand.id not in processed_elements:
                                seen_ids.add(cand.id)
                                add_buttons.append(cand)
                        except Exception:
                            continue
                except Exception:
                    continue

            logger.info(f"Discovered {len(add_buttons)} candidate Add Friend buttons on screen (Sent so far: {sent_count}/{target_count}).")

            # In random mode, shuffle candidate buttons for organic non-linear selection
            if mode == "random" and len(add_buttons) > 1:
                random.shuffle(add_buttons)

            # Process candidates found on current screen
            for btn in add_buttons:
                if stop_event and stop_event.is_set() or sent_count >= target_count:
                    break

                try:
                    if not btn.is_displayed() or btn.get_attribute("data-bot-sent") == "true":
                        continue

                    # Tab check: Ensure focus before clicking
                    browser.switch_to_platform_tab("facebook", driver=driver)

                    # Extract actual profile name and profile URL
                    profile_name, profile_url = extract_fb_profile_info(btn, loc_display)
                    fallback_label = f"Suggested Contact #{sent_count + 1}" if mode != "location" else f"Person in {loc_display}"
                    display_name = profile_name if profile_name else fallback_label

                    # Deduplication checks
                    if profile_url and profile_url in processed_urls:
                        continue
                    if profile_name and profile_name.lower() in processed_names:
                        continue

                    # Record in tracking sets
                    processed_elements.add(btn.id)
                    if profile_url:
                        processed_urls.add(profile_url)
                    if profile_name:
                        processed_names.add(profile_name.lower())

                    # Tag in DOM to ensure no duplicate clicks across scrolls
                    driver.execute_script("arguments[0].setAttribute('data-bot-sent', 'true');", btn)

                    # Smooth scroll button into view
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", btn)
                    time.sleep(random.uniform(0.6, 1.2))

                    # Move mouse like human & click
                    clicked = False
                    try:
                        ActionChains(driver).move_to_element(btn).pause(random.uniform(0.2, 0.4)).click().perform()
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
                    log_entry = f"✅ Sent friend request #{sent_count} to '{display_name}' ({loc_display})"
                    logs.append(log_entry)
                    logger.info(log_entry)

                    # Dismiss any unexpected modal/overlay by sending ESCAPE to body
                    time.sleep(random.uniform(0.4, 0.8))
                    try:
                        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                    except Exception:
                        pass

                    if on_progress:
                        try:
                            on_progress(sent_count, target_count, {
                                "platform": "facebook",
                                "user": display_name,
                                "location": loc_display,
                                "mode": mode,
                                "sent": sent_count,
                                "target": target_count,
                            })
                        except Exception as e_cb:
                            logger.debug(f"Progress callback note: {e_cb}")

                    # If reached target, break immediately without waiting for delay
                    if sent_count >= target_count:
                        break

                    # Mandatory 2-minute (120s) safety break after every 250 sent requests
                    if sent_count > 0 and sent_count % 250 == 0:
                        cooldown_secs = 120
                        cooldown_msg = f"⏸️ Reached {sent_count} friend requests milestone. Taking a 2-minute safety break to protect account health..."
                        logs.append(cooldown_msg)
                        logger.info(cooldown_msg)
                        if on_progress:
                            try:
                                on_progress(sent_count, target_count, {
                                    "platform": "facebook",
                                    "user": display_name,
                                    "cooldown": True,
                                    "cooldown_seconds": cooldown_secs,
                                    "message": f"Paused for 2-min safety cooldown ({sent_count}/{target_count})",
                                })
                            except Exception as e_cb:
                                logger.debug(f"Progress cooldown note: {e_cb}")
                        for _ in range(cooldown_secs):
                            if stop_event and stop_event.is_set():
                                break
                            time.sleep(1.0)
                        logs.append(f"▶️ 2-minute safety cooldown completed. Resuming friend requests ({sent_count}/{target_count})...")
                        logger.info("Resuming friend requests after 2-minute safety break.")

                    # Anti-detection human delay before next action
                    current_delay = random.uniform(max(6.0, safety_delay * 0.5), max(8.0, safety_delay * 0.85))
                    logger.info(f"Human safety pause: {current_delay:.1f}s before next request ({sent_count}/{target_count})...")
                    time.sleep(current_delay)

                except Exception as e_click:
                    skipped_count += 1
                    logger.debug(f"Error clicking Add friend candidate: {e_click}")
                    continue

            # If reached target count, exit scroll loop immediately
            if sent_count >= target_count:
                break

            # Scroll down to load more people
            scroll_attempts += 1
            scroll_y = random.randint(550, 850)
            driver.execute_script(f"window.scrollBy(0, {scroll_y});")
            time.sleep(random.uniform(2.0, 3.2))

        status_label = "stopped" if (stop_event and stop_event.is_set()) else ("completed" if sent_count >= target_count else "partial")
        logs.append(f"🏁 Finished Facebook friend request session. Total sent: {sent_count}/{target_count}.")

        return {
            "status": status_label,
            "platform": "facebook",
            "location": loc_display,
            "mode": mode,
            "sent": sent_count,
            "target": target_count,
            "skipped": skipped_count,
            "logs": logs,
        }

    except Exception as e:
        logger.error(f"Facebook friend request session error: {e}")
        logs.append(f"⚠️ Error: {str(e)}")
        return {
            "status": "error",
            "platform": "facebook",
            "location": loc_display,
            "mode": mode,
            "sent": sent_count,
            "target": target_count,
            "error": str(e),
            "logs": logs,
        }


if __name__ == "__main__":
    import sys
    test_loc = sys.argv[1] if len(sys.argv) > 1 else "New Delhi"
    test_num = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    res = send_facebook_friend_requests(location=test_loc, target_count=test_num, safety_delay=8)
    print(res)
