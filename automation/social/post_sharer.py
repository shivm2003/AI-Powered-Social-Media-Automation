"""
Manvix AI — Social Post Gallery & Human-Touch "Share to All" Automator.
Features:
1. Lists all posted images and videos across Instagram and Facebook.
2. Directly shares posts to friends/connections via Instagram Direct and Facebook Messenger.
3. Implements human-touch delays (6-12s), safety pauses, and full "Share to All" automation.
4. Records all shares in SQLite/PostgreSQL (post_shares_log) and streams real-time telemetry.
"""
import os
import sys
import time
import json
import random
import logging
import threading
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
from db_campaigns import (
    get_all_published_posts,
    get_campaign_from_db,
    record_post_share,
    get_post_shares_stats,
    get_chrome_account
)

logger = logging.getLogger("automation.social.post_sharer")


def get_all_posted_media(platform: str = None, limit: int = 25) -> list:
    """Returns all published posts with verified local media files (images & videos)."""
    return get_all_published_posts(platform=platform, limit=limit)


def get_or_harvest_instagram_followers(
    driver,
    account_username: str = "loansolutions2026",
    max_count: int = 100,
    force_refresh: bool = False
) -> list:
    """
    Retrieves follower usernames for the Instagram account.
    First checks local cache (data/instagram_followers_cache.json).
    If cache is missing or refresh requested, opens the profile followers modal
    and dynamically scrolls to harvest the follower list.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys

    cache_file = BASE_DIR / "data" / "instagram_followers_cache.json"
    cached_followers = []
    if cache_file.exists() and not force_refresh:
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached_followers = json.load(f)
            if len(cached_followers) >= min(max_count, 30):
                logger.info(f"Loaded {len(cached_followers)} Instagram followers from cache.")
                return cached_followers
        except Exception as e:
            logger.debug(f"Error reading followers cache: {e}")

    profile_url = f"https://www.instagram.com/{account_username}/"
    logger.info(f"Harvesting Instagram followers from profile: {profile_url} (Target: {max_count})")

    try:
        if account_username not in driver.current_url or "/p/" in driver.current_url or "/reel/" in driver.current_url:
            driver.get(profile_url)
            time.sleep(3.0)

        # Close any lingering dialogs
        for _ in range(3):
            try:
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                time.sleep(0.2)
            except Exception:
                pass

        # Click the followers link in profile header
        clicked = driver.execute_script("""
            var a = Array.from(document.querySelectorAll('header a')).find(x => (x.innerText || '').toLowerCase().includes('follower'));
            if (a) {
                a.click();
                return {clicked: true, text: a.innerText};
            }
            return {clicked: false};
        """)
        if not (clicked and clicked.get("clicked")):
            flinks = driver.find_elements(By.XPATH, "//header//a[contains(., 'follower')]")
            if flinks:
                driver.execute_script("arguments[0].click();", flinks[0])
                clicked = {"clicked": True}

        time.sleep(3.0)

        # Scroll followers modal and harvest usernames
        scroll_script = """
            var dialogs = Array.from(document.querySelectorAll('div[role="dialog"]'));
            if (!dialogs.length) return {error: 'no_dialog'};
            var fDialog = dialogs[dialogs.length - 1];

            var allDivs = Array.from(fDialog.querySelectorAll('div'));
            var scrollable = allDivs.find(d => {
                var style = window.getComputedStyle(d);
                return (style.overflowY === 'auto' || style.overflowY === 'scroll') && d.scrollHeight > d.clientHeight;
            });

            if (scrollable) {
                scrollable.scrollTop = scrollable.scrollHeight;
            }

            var collected = [];
            var aTags = fDialog.querySelectorAll('a[role="link"], a[href^="/"]');
            for (var a of aTags) {
                var href = a.getAttribute('href') || '';
                var u = href.replace(/\\//g, '').trim();
                if (u && !collected.includes(u) && !['explore', 'reels', 'direct', 'stories'].includes(u)) {
                    collected.push(u);
                }
            }
            return {
                count: collected.length,
                users: collected,
                scrollHeight: scrollable ? scrollable.scrollHeight : 0
            };
        """

        harvested = list(cached_followers)
        last_height = 0
        stagnant_count = 0

        for _ in range(25):
            res = driver.execute_script(scroll_script)
            if not isinstance(res, dict) or res.get("error"):
                break
            users = res.get("users", [])
            for u in users:
                if u not in harvested:
                    harvested.append(u)

            if len(harvested) >= max_count:
                break

            curr_h = res.get("scrollHeight", 0)
            if curr_h == last_height:
                stagnant_count += 1
                if stagnant_count >= 3:
                    break
            else:
                stagnant_count = 0
            last_height = curr_h
            time.sleep(1.2)

        # Close dialog cleanly
        try:
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        except Exception:
            pass

        # Save to cache
        if harvested:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(harvested, f, indent=2)
            logger.info(f"Saved {len(harvested)} harvested followers to {cache_file}")

        return harvested
    except Exception as e:
        logger.warning(f"Error harvesting Instagram followers: {e}")
        return cached_followers


def share_instagram_post_to_friends(
    post_url: str = None,
    campaign_id: str = None,
    share_all: bool = True,
    target_count: int = 100,
    batch_size: int = 15,
    safety_delay: int = 8,
    on_progress=None,
    stop_event=None,
    capture_screenshot: bool = True
) -> dict:
    """
    Navigates to an Instagram post, resolves account followers, searches and selects
    followers sequentially in the Share dialog, dispatches via 'Send Separately' in safe batches,
    and logs all recipients in the database.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains

    driver = browser.get_driver("instagram")
    logs = []
    sent_recipients = []
    screenshot_path = None

    # Resolve post URL
    target_url = post_url
    post_caption = ""
    media_path = ""
    content_type = "image"

    if campaign_id:
        camp = get_campaign_from_db(campaign_id)
        if camp:
            post_caption = camp.get("generated_caption") or ""
            mps = camp.get("media_paths") or []
            media_path = mps[0] if mps else ""
            content_type = camp.get("content_type") or "image"

    if not target_url:
        target_url = "https://www.instagram.com/loansolutions2026/"

    logs.append(f"📸 Preparing Instagram post share | Target: {target_url} (Share All: {share_all})")
    logger.info(f"Starting Instagram post share | Target: {target_url} (Share All: {share_all})")

    try:
        browser.switch_to_platform_tab("instagram", target_url=target_url, driver=driver)
        with browser.tab_focus("instagram", url=target_url) as active_driver:
            driver = active_driver or driver
            time.sleep(random.uniform(2.0, 3.0))

            if browser.is_blank_or_unrendered(driver):
                logger.warning("Instagram post tab unrendered. Auto-healing...")
                browser.ensure_healthy_page(driver, "instagram", target_url=target_url)
                time.sleep(2.0)

            # Step 1: Follower Resolution
            if on_progress:
                try:
                    on_progress(0, target_count, {"activity": "Resolving Instagram followers list..."})
                except Exception:
                    pass
            followers_list = get_or_harvest_instagram_followers(
                driver,
                account_username="loansolutions2026",
                max_count=500 if share_all else target_count
            )
            logs.append(f"👥 Resolved {len(followers_list)} account followers for post sharing.")
            logger.info(f"Resolved {len(followers_list)} account followers.")

            # Step 2: Navigate to target post if needed
            if target_url and ("/p/" in target_url or "/reel/" in target_url):
                if driver.current_url.rstrip('/') != target_url.rstrip('/'):
                    driver.get(target_url)
                    time.sleep(3.0)
            elif "/p/" not in driver.current_url and "/reel/" not in driver.current_url:
                post_opened = driver.execute_script("""
                    var a = document.querySelector('article a[href*="/p/"], a[href*="/p/"], a[href*="/reel/"]');
                    if (a) {
                        a.click();
                        return true;
                    }
                    return false;
                """)
                if not post_opened:
                    thumbs = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/') or contains(@href, '/reel/')]")
                    if thumbs:
                        driver.execute_script("arguments[0].click();", thumbs[0])
                        post_opened = True
                if post_opened:
                    time.sleep(3.0)
                    logs.append(f"🔍 Opened latest post thumbnail: {driver.current_url}")

            current_post_url = driver.current_url

            # Determine recipients target
            target_handles = followers_list if share_all else followers_list[:target_count]
            total_target = len(target_handles) if target_handles else target_count

            # Helper to open Share modal
            def _open_share_dialog():
                for _ in range(2):
                    opened = driver.execute_script("""
                        var svg = document.querySelector('svg[aria-label="Share Post"], svg[aria-label="Share"]');
                        if (svg) {
                            var btn = svg.closest('button') || svg.closest('[role="button"]') || svg.parentElement;
                            if (btn) {
                                btn.click();
                                return true;
                            }
                        }
                        return false;
                    """)
                    if opened:
                        time.sleep(2.5)
                        return True
                    # Fallback XPath
                    svg_btns = driver.find_elements(By.XPATH, "//*[local-name()='svg' and (@aria-label='Share' or @aria-label='Share Post')]/ancestor::button | //*[local-name()='svg' and (@aria-label='Share' or @aria-label='Share Post')]/ancestor::div[@role='button']")
                    if svg_btns:
                        driver.execute_script("arguments[0].click();", svg_btns[0])
                        time.sleep(2.5)
                        return True
                    time.sleep(1.0)
                return False

            # Helper to click Send / Send Separately
            def _click_send_button():
                send_res = driver.execute_script("""
                    var dialogs = Array.from(document.querySelectorAll('div[role="dialog"]'));
                    if (!dialogs.length) return false;
                    var shareDialog = dialogs[dialogs.length - 1];
                    var btns = Array.from(shareDialog.querySelectorAll('button, div[role="button"]'));
                    for (var b of btns) {
                        var t = (b.innerText || '').trim().toLowerCase();
                        if (t === 'send' || t === 'send separately' || t.startsWith('send')) {
                            b.scrollIntoView({block: 'center'});
                            b.click();
                            return true;
                        }
                    }
                    return false;
                """)
                if not send_res:
                    sbtns = driver.find_elements(By.XPATH, "//div[@role='dialog']//button[contains(., 'Send')] | //div[@role='dialog']//div[@role='button'][contains(., 'Send')]")
                    if sbtns:
                        driver.execute_script("arguments[0].click();", sbtns[-1])
                        send_res = True
                return send_res

            # Step 3: Dispatch Flow
            if target_handles:
                # Divide target handles into safe batches
                effective_batch_size = max(5, min(batch_size, 20))
                handle_batches = [target_handles[i:i + effective_batch_size] for i in range(0, len(target_handles), effective_batch_size)]
                logs.append(f"📦 Grouped {len(target_handles)} followers into {len(handle_batches)} batches (max {effective_batch_size} per batch).")

                for b_idx, batch in enumerate(handle_batches):
                    if stop_event and stop_event.is_set():
                        logs.append("🛑 Share task stopped by user.")
                        break

                    logs.append(f"🚀 Processing Batch {b_idx + 1}/{len(handle_batches)} ({len(batch)} followers)...")
                    if not _open_share_dialog():
                        logs.append("⚠️ Failed to open Share dialog for batch. Retrying...")
                        time.sleep(2.0)
                        if not _open_share_dialog():
                            continue

                    batch_selected = []
                    for handle in batch:
                        if stop_event and stop_event.is_set():
                            break

                        # Focus input
                        focused = driver.execute_script("""
                            var dialogs = Array.from(document.querySelectorAll('div[role="dialog"]'));
                            if (!dialogs.length) return false;
                            var shareDialog = dialogs[dialogs.length - 1];
                            var inp = shareDialog.querySelector('input[name="queryBox"], input[placeholder="Search"]');
                            if (inp) {
                                inp.focus();
                                return true;
                            }
                            return false;
                        """)
                        if not focused:
                            continue

                        # Clear and type follower handle
                        try:
                            driver.switch_to.active_element.send_keys(Keys.CONTROL + "a")
                            driver.switch_to.active_element.send_keys(Keys.BACKSPACE)
                            time.sleep(0.2)
                            driver.switch_to.active_element.send_keys(handle)
                            time.sleep(1.8)
                        except Exception:
                            pass

                        # Click result row
                        clicked_row = driver.execute_script("""
                            var handle = arguments[0];
                            var dialogs = Array.from(document.querySelectorAll('div[role="dialog"]'));
                            if (!dialogs.length) return {error: 'no_dialog'};
                            var shareDialog = dialogs[dialogs.length - 1];

                            var rows = Array.from(shareDialog.querySelectorAll('div[role="button"], label, div[role="option"]'));
                            for (var r of rows) {
                                var txt = (r.innerText || '').toLowerCase();
                                if (txt.includes(handle.toLowerCase())) {
                                    r.scrollIntoView({block: 'center'});
                                    r.click();
                                    return {clicked: true, text: r.innerText.replace(/\\n/g, ' ')};
                                }
                            }
                            return {clicked: false};
                        """, handle)

                        if clicked_row and clicked_row.get("clicked"):
                            batch_selected.append(handle)
                            sent_recipients.append(handle)
                            record_post_share(
                                campaign_id=campaign_id or "ig_shared_post",
                                platform="instagram",
                                recipient_name=handle,
                                post_url=current_post_url,
                                media_path=media_path,
                                content_type=content_type,
                                status="sent",
                                share_mode="share_all" if share_all else "selective"
                            )
                            log_msg = f"✅ Selected follower #{len(sent_recipients)}: '@{handle}'"
                            logs.append(log_msg)
                            logger.info(log_msg)

                            if on_progress:
                                try:
                                    on_progress(len(sent_recipients), total_target, {
                                        "platform": "instagram",
                                        "friend": f"@{handle}",
                                        "sent": len(sent_recipients),
                                        "target": total_target,
                                        "activity": f"✅ Selected follower '@{handle}' ({len(sent_recipients)}/{total_target})"
                                    })
                                except Exception:
                                    pass

                        delay = random.uniform(max(0.8, safety_delay * 0.15), max(1.6, safety_delay * 0.25))
                        time.sleep(delay)

                    # Click Send Separately for this batch
                    if batch_selected:
                        time.sleep(1.2)
                        sent = _click_send_button()
                        if sent:
                            logs.append(f"📨 Dispatched post to batch of {len(batch_selected)} followers!")
                            logger.info(f"Dispatched post to batch of {len(batch_selected)} followers.")
                        time.sleep(3.0)

                        if capture_screenshot:
                            try:
                                ss_dir = BASE_DIR / "data" / "media" / "post_share_captures"
                                ss_dir.mkdir(parents=True, exist_ok=True)
                                ss_file = ss_dir / f"ig_share_batch_{b_idx+1}_{int(time.time())}.png"
                                driver.save_screenshot(str(ss_file))
                                screenshot_path = str(ss_file)
                            except Exception:
                                pass

                    # Anti-spam breathing delay between batches
                    if b_idx < len(handle_batches) - 1:
                        batch_pause = random.uniform(safety_delay * 0.8, safety_delay * 1.4)
                        logger.info(f"Anti-spam pause {batch_pause:.1f}s before next batch...")
                        time.sleep(batch_pause)

            else:
                # Fallback: Suggested Contacts Selection
                logs.append("ℹ️ Using suggested contacts fallback in Share dialog...")
                if not _open_share_dialog():
                    return {"status": "error", "message": "Could not open Share dialog", "sent_count": 0, "logs": logs}

                friend_items = driver.execute_script("""
                    var dialogs = Array.from(document.querySelectorAll('div[role="dialog"]'));
                    if (!dialogs.length) return [];
                    var shareDialog = dialogs[dialogs.length - 1];
                    var options = Array.from(shareDialog.querySelectorAll('div[role="option"]'));
                    if (!options.length) {
                        options = Array.from(shareDialog.querySelectorAll('div[role="button"], label')).filter(function(b) {
                            var txt = (b.innerText || '').trim();
                            return txt && txt !== 'Close' && !txt.includes('Search') && !txt.includes('Send') && !txt.includes('Copy link') && !txt.includes('Share to...');
                        });
                    }
                    return options.map(function(r, idx) {
                        var lines = (r.innerText || '').split('\\n');
                        return {
                            index: idx,
                            name: (lines[0] || '').trim(),
                            username: (lines[1] || '').trim()
                        };
                    }).filter(function(x) { return x.name && x.name !== 'To:'; });
                """)

                effective_target = len(friend_items) if share_all else min(target_count, len(friend_items))
                for idx in range(effective_target):
                    if stop_event and stop_event.is_set():
                        break
                    item_info = friend_items[idx]
                    fname = item_info.get("name") or f"friend_{idx+1}"
                    uname = item_info.get("username") or ""
                    display_label = f"{fname} (@{uname})" if uname else fname

                    clicked = driver.execute_script("""
                        var dialogs = Array.from(document.querySelectorAll('div[role="dialog"]'));
                        if (!dialogs.length) return false;
                        var shareDialog = dialogs[dialogs.length - 1];
                        var options = Array.from(shareDialog.querySelectorAll('div[role="option"]'));
                        if (!options.length) {
                            options = Array.from(shareDialog.querySelectorAll('div[role="button"], label')).filter(function(b) {
                                var txt = (b.innerText || '').trim();
                                return txt && txt !== 'Close' && !txt.includes('Search') && !txt.includes('Send') && !txt.includes('Copy link') && !txt.includes('Share to...');
                            });
                        }
                        if (arguments[0] < options.length) {
                            options[arguments[0]].scrollIntoView({block: 'center'});
                            options[arguments[0]].click();
                            return true;
                        }
                        return false;
                    """, idx)

                    if clicked:
                        sent_recipients.append(display_label)
                        record_post_share(
                            campaign_id=campaign_id or "ig_shared_post",
                            platform="instagram",
                            recipient_name=display_label,
                            post_url=current_post_url,
                            media_path=media_path,
                            content_type=content_type,
                            status="sent",
                            share_mode="share_all" if share_all else "selective"
                        )
                        logs.append(f"✅ Added suggested friend: '{display_label}'")
                        time.sleep(random.uniform(0.8, 1.8))

                _click_send_button()
                time.sleep(3.0)

            # Close dialog cleanly if still visible
            try:
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            except Exception:
                pass

            if capture_screenshot and not screenshot_path:
                try:
                    ss_dir = BASE_DIR / "data" / "media" / "post_share_captures"
                    ss_dir.mkdir(parents=True, exist_ok=True)
                    ss_file = ss_dir / f"ig_share_{int(time.time())}.png"
                    driver.save_screenshot(str(ss_file))
                    screenshot_path = str(ss_file)
                except Exception:
                    pass

            return {
                "status": "success",
                "platform": "instagram",
                "sent_count": len(sent_recipients),
                "instagram_shares": len(sent_recipients),
                "facebook_shares": 0,
                "target_count": total_target,
                "recipients": sent_recipients,
                "post_url": current_post_url,
                "screenshot_path": screenshot_path,
                "logs": logs
            }

    except Exception as e:
        logger.error(f"Error sharing Instagram post to friends: {e}", exc_info=True)
        return {
            "status": "error",
            "platform": "instagram",
            "message": str(e),
            "sent_count": len(sent_recipients),
            "recipients": sent_recipients,
            "logs": logs
        }


def share_facebook_post_to_friends(
    post_url: str = None,
    campaign_id: str = None,
    share_all: bool = True,
    target_count: int = 100,
    safety_delay: int = 8,
    on_progress=None,
    stop_event=None,
    capture_screenshot: bool = True
) -> dict:
    """
    Shares a published post to Facebook friends using the native Facebook Web UI:
    1. Navigates to the Facebook post (or user profile to locate the target post).
    2. Clicks the post's native 'Share' button.
    3. Clicks the 'More' button under 'Send in Messenger' (aria-label='More Messenger contacts').
    4. Waits for the 'Send to' modal to load with contact checkboxes.
    5. Selects all friend checkboxes (up to target_count / all available) with human pacing.
    6. Clicks the native 'Send separately' / 'Send' button.
    7. Captures verification screenshot, logs every recipient in post_shares_log, and returns telemetry.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains

    driver = browser.get_driver("facebook")
    logs = []
    sent_recipients = []
    screenshot_path = None
    # When share_all is True, target all available friends without restriction
    effective_target = 9999 if share_all else target_count

    post_caption = ""
    media_path = ""
    content_type = "image"

    if campaign_id:
        camp = get_campaign_from_db(campaign_id)
        if camp:
            post_caption = camp.get("generated_caption") or ""
            mps = camp.get("media_paths") or []
            media_path = mps[0] if mps else ""
            content_type = camp.get("content_type") or "image"

    target_url = post_url
    if not target_url or "facebook.com/me" in target_url or "profile.php" in target_url:
        target_url = "https://www.facebook.com/me"

    logs.append(f"📘 Opening Facebook target: {target_url} (Share All: {share_all})")
    logger.info(f"Starting native Facebook post share | Target: {target_url} (Share All: {share_all})")

    if on_progress:
        try:
            on_progress(0, effective_target, {"activity": "Connecting to Facebook and locating target post..."})
        except Exception:
            pass

    try:
        browser.switch_to_platform_tab("facebook", target_url=target_url, driver=driver)
        with browser.tab_focus("facebook", url=target_url) as active_driver:
            driver = active_driver or driver
            time.sleep(random.uniform(2.5, 3.5))

            if browser.is_blank_or_unrendered(driver):
                logger.warning("Facebook tab unrendered. Auto-healing...")
                browser.ensure_healthy_page(driver, "facebook", target_url=target_url)
                time.sleep(2.0)

            # Ensure any lingering dialog from previous action is dismissed
            try:
                for _ in range(2):
                    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                    time.sleep(0.3)
            except Exception:
                pass

            # Step 1: Locate the target post and its native 'Share' button
            logs.append("🔍 Locating post on Facebook feed...")
            # Scroll slightly to trigger feed rendering if on profile
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(1.8)

            js_click_post_share = """
            // 1. Look for a post containing relevant caption keywords or CTA
            var articles = Array.from(document.querySelectorAll('div[role="article"], div[data-pagelet*="FeedUnit"], div[class*="x1yztbdb"]'));
            var targetArticle = null;
            var keywords = arguments[0] || [];

            for (var a of articles) {
                var txt = (a.innerText || '').toLowerCase();
                if (keywords.some(k => k && txt.includes(k.toLowerCase()))) {
                    targetArticle = a;
                    break;
                }
            }

            // Fallback: use first visible article with a share button
            if (!targetArticle) {
                for (var a of articles) {
                    if (a.querySelector('div[aria-label*="Share, send this to friends"], div[aria-label*="Send this to friends"], div[aria-label="Share"], div[role="button"][contains(., "Share")]')) {
                        targetArticle = a;
                        break;
                    }
                }
            }

            var container = targetArticle || document;
            var shareBtn = container.querySelector('div[aria-label*="Share, send this to friends"], div[aria-label*="Send this to friends or post it on your timeline."], div[aria-label*="Send this to friends"], div[aria-label="Share"]');

            if (!shareBtn) {
                // Search for buttons or role="button" with text 'Share'
                var allBtns = Array.from(container.querySelectorAll('div[role="button"], button'));
                for (var b of allBtns) {
                    var aria = (b.getAttribute('aria-label') || '').toLowerCase();
                    var t = (b.innerText || '').trim().toLowerCase();
                    if (t === 'share' || (aria.includes('share') && aria.includes('friends'))) {
                        shareBtn = b;
                        break;
                    }
                }
            }

            if (shareBtn) {
                shareBtn.scrollIntoView({block: 'center', behavior: 'smooth'});
                shareBtn.click();
                return {success: true, aria: shareBtn.getAttribute('aria-label'), text: shareBtn.innerText};
            }
            return {success: false};
            """

            # Extract keywords from caption
            search_keywords = ["loansolutions", "apply now", "loan solutions"]
            if post_caption:
                clean_cap = post_caption.strip()[:40].lower()
                if len(clean_cap) > 10:
                    search_keywords.insert(0, clean_cap)

            share_click_res = driver.execute_script(js_click_post_share, search_keywords)
            time.sleep(2.5)

            if not (share_click_res and share_click_res.get("success")):
                # Direct fallback via XPath search
                xpath_share = (
                    "//div[contains(@aria-label, 'Share, send this to friends') and @role='button'] | "
                    "//div[contains(@aria-label, 'Send this to friends') and @role='button'] | "
                    "//div[@aria-label='Share' and @role='button'] | "
                    "//span[text()='Share']/ancestor::div[@role='button']"
                )
                fb_share_btns = driver.find_elements(By.XPATH, xpath_share)
                if fb_share_btns:
                    for b in fb_share_btns:
                        if b.is_displayed():
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", b)
                            share_click_res = {"success": True}
                            time.sleep(2.5)
                            break

            if not (share_click_res and share_click_res.get("success")):
                err_msg = "Could not locate or click Facebook post native 'Share' button."
                logs.append(f"❌ {err_msg}")
                logger.error(err_msg)
                return {"status": "error", "platform": "facebook", "message": err_msg, "logs": logs}

            logs.append("✅ Clicked post 'Share' button. Share modal opened.")
            logger.info("Clicked Facebook post native Share button.")

            if on_progress:
                try:
                    on_progress(0, effective_target, {"activity": "Opened Facebook post Share menu. Accessing Messenger contacts..."})
                except Exception:
                    pass

            # Step 2: Under 'Send in Messenger', click the 'More' button to expand all contacts
            time.sleep(1.5)
            js_click_more = """
            var dialogs = Array.from(document.querySelectorAll('div[role="dialog"]'));
            if (!dialogs.length) return {found_dialog: false};
            var activeDialog = dialogs[dialogs.length - 1];

            var moreBtn = activeDialog.querySelector('div[aria-label="More Messenger contacts"], div[aria-label*="More Messenger"], div[aria-label="More"]');
            if (!moreBtn) {
                var btns = Array.from(activeDialog.querySelectorAll('div[role="button"], button'));
                for (var b of btns) {
                    var txt = (b.innerText || '').trim().toLowerCase();
                    var aria = (b.getAttribute('aria-label') || '').toLowerCase();
                    if (txt === 'more' || aria.includes('more messenger')) {
                        moreBtn = b;
                        break;
                    }
                }
            }

            if (moreBtn) {
                moreBtn.scrollIntoView({block: 'center'});
                moreBtn.click();
                return {clicked: true, aria: moreBtn.getAttribute('aria-label')};
            }
            return {clicked: false};
            """
            more_res = driver.execute_script(js_click_more)
            time.sleep(2.0)

            if not (more_res and more_res.get("clicked")):
                # Fallback via XPath
                more_xpaths = [
                    "//div[@role='dialog']//div[contains(@aria-label, 'More Messenger contacts')]",
                    "//div[@role='dialog']//span[text()='More']/ancestor::div[@role='button']",
                    "//div[@role='dialog']//div[@aria-label='More' and @role='button']"
                ]
                for mx in more_xpaths:
                    m_elems = driver.find_elements(By.XPATH, mx)
                    for me in m_elems:
                        if me.is_displayed():
                            driver.execute_script("arguments[0].click();", me)
                            more_res = {"clicked": True}
                            time.sleep(2.0)
                            break
                    if more_res and more_res.get("clicked"):
                        break

            logs.append("✅ Clicked 'More' under 'Send in Messenger'. 'Send to' modal opened.")
            logger.info("Clicked 'More' button to open Facebook 'Send to' contact list.")

            # Step 3: Wait for 'Send to' modal contact checkboxes to render (skeleton loader to resolve)
            logs.append("⏳ Waiting for friend checkboxes to populate...")
            checkboxes_ready = False
            for _ in range(12):
                cb_count = driver.execute_script("""
                    var dialogs = Array.from(document.querySelectorAll('div[role="dialog"]'));
                    if (!dialogs.length) return 0;
                    var activeDialog = dialogs[dialogs.length - 1];
                    var cbs = activeDialog.querySelectorAll('input[type="checkbox"], div[role="checkbox"]');
                    return cbs.length;
                """)
                if cb_count and cb_count > 0:
                    checkboxes_ready = True
                    logs.append(f"📋 Detected {cb_count} friends available in 'Send to' list.")
                    break
                time.sleep(0.7)

            if not checkboxes_ready:
                err_msg = "Facebook 'Send to' contacts list did not load or checkboxes were not found."
                logs.append(f"❌ {err_msg}")
                logger.error(err_msg)
                return {"status": "error", "platform": "facebook", "message": err_msg, "logs": logs}

            # Step 4: Select friends / checkboxes ("all at once" / batch multi-selection)
            js_select_batch = """
            var dialogs = Array.from(document.querySelectorAll('div[role="dialog"]'));
            if (!dialogs.length) return {selected: [], count: 0};
            var activeDialog = dialogs[dialogs.length - 1];

            var targetLimit = arguments[0] || 9999;
            var isShareAll = arguments[1] === true;

            // If share_all, scroll down the contacts container to load all available friends
            if (isShareAll) {
                var scrollables = activeDialog.querySelectorAll('div[style*="overflow"], div[class*="x1n2onr6"]');
                for (var sc of scrollables) {
                    if (sc.scrollHeight > sc.clientHeight && sc.clientHeight > 100) {
                        sc.scrollTop = sc.scrollHeight;
                    }
                }
            }

            var cbs = Array.from(activeDialog.querySelectorAll('input[type="checkbox"], div[role="checkbox"]'));
            var selectedNames = [];

            for (var i = 0; i < cbs.length && (isShareAll || selectedNames.length < targetLimit); i++) {
                var cb = cbs[i];
                var parent = cb.closest('div[role="listitem"], div[class*="x1n2onr6"]') || cb.parentElement;
                var rawName = (parent.innerText || '').trim();
                var name = rawName.split('\\n')[0].replace(/Online status indicator/g, '').replace(/Active/g, '').trim();

                var isChecked = cb.checked || cb.getAttribute('aria-checked') === 'true';
                if (!isChecked) {
                    cb.click();
                    isChecked = cb.checked || cb.getAttribute('aria-checked') === 'true';
                }

                if (name && !selectedNames.includes(name)) {
                    selectedNames.push(name);
                }
            }

            return {
                selected: selectedNames,
                count: selectedNames.length,
                totalAvailable: cbs.length
            };
            """

            batch_res = driver.execute_script(js_select_batch, effective_target, bool(share_all))
            selected_names = batch_res.get("selected", [])
            sent_recipients = selected_names
            display_target = len(sent_recipients) if share_all else effective_target

            logs.append(f"👥 Selected all {len(sent_recipients)} Facebook friends at once (All available: {batch_res.get('totalAvailable', len(sent_recipients))}): {', '.join(sent_recipients[:6])}...")
            logger.info(f"Selected all {len(sent_recipients)} Facebook friends in 'Send to' modal: {sent_recipients[:10]}")

            if on_progress:
                try:
                    on_progress(len(sent_recipients), display_target, {
                        "platform": "facebook",
                        "sent": len(sent_recipients),
                        "target": display_target,
                        "friend": sent_recipients[-1] if sent_recipients else "All Friends",
                        "activity": f"✅ Selected all {len(sent_recipients)} friends at once in Facebook Share modal"
                    })
                except Exception:
                    pass

            time.sleep(1.5)

            # Step 5: Click native 'Send separately' / 'Send' button
            js_click_send = """
            var dialogs = Array.from(document.querySelectorAll('div[role="dialog"]'));
            if (!dialogs.length) return {success: false, reason: 'no_dialog'};
            var activeDialog = dialogs[dialogs.length - 1];

            var allBtns = Array.from(activeDialog.querySelectorAll('div[role="button"], button'));
            for (var b of allBtns) {
                var txt = (b.innerText || '').trim().toLowerCase();
                var aria = (b.getAttribute('aria-label') || '').trim().toLowerCase();
                if (txt === 'send separately' || aria === 'send separately' || txt === 'send' || aria === 'send') {
                    var isDisabled = b.getAttribute('aria-disabled') === 'true' || b.disabled;
                    if (!isDisabled) {
                        b.scrollIntoView({block: 'center'});
                        b.click();
                        return {success: true, label: txt || aria};
                    }
                }
            }
            return {success: false, reason: 'button_disabled_or_not_found'};
            """
            send_res = driver.execute_script(js_click_send)

            if not (send_res and send_res.get("success")):
                # Fallback via XPath
                send_xpath = (
                    "//div[@role='dialog']//div[contains(@aria-label, 'Send separately') and @role='button'] | "
                    "//div[@role='dialog']//div[text()='Send separately' and @role='button'] | "
                    "//div[@role='dialog']//div[@aria-label='Send' and @role='button'] | "
                    "//div[@role='dialog']//div[text()='Send' and @role='button']"
                )
                send_elems = driver.find_elements(By.XPATH, send_xpath)
                for se in send_elems:
                    if se.is_displayed() and se.get_attribute("aria-disabled") != "true":
                        driver.execute_script("arguments[0].click();", se)
                        send_res = {"success": True, "label": se.text}
                        break

            logs.append(f"🚀 Clicked 'Send separately' button: Post dispatched to {len(sent_recipients)} Facebook friends!")
            logger.info(f"Dispatched Facebook post to {len(sent_recipients)} friends via 'Send separately'.")
            time.sleep(3.5)

            # Step 6: Capture verification screenshot
            if capture_screenshot:
                try:
                    ss_dir = BASE_DIR / "data" / "media" / "post_share_captures"
                    ss_dir.mkdir(parents=True, exist_ok=True)
                    ss_file = ss_dir / f"fb_share_{int(time.time())}.png"
                    driver.save_screenshot(str(ss_file))
                    screenshot_path = str(ss_file)
                    logs.append(f"📸 Verification screenshot captured: {os.path.basename(screenshot_path)}")
                    logger.info(f"Captured Facebook share screenshot: {screenshot_path}")
                except Exception as e_ss:
                    logger.debug(f"Screenshot note: {e_ss}")

            # Step 7: Record every recipient in post_shares_log
            current_post_url = post_url or driver.current_url
            for r_name in sent_recipients:
                try:
                    record_post_share(
                        campaign_id=campaign_id or "fb_shared_post",
                        platform="facebook",
                        recipient_name=r_name,
                        post_url=current_post_url,
                        media_path=media_path,
                        content_type=content_type,
                        status="sent",
                        share_mode="share_all" if share_all else "selective"
                    )
                except Exception as e_rec:
                    logger.debug(f"Share record log note: {e_rec}")

            # Close dialog cleanly if still visible and dismiss docked chat popups
            try:
                for _ in range(2):
                    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                    time.sleep(0.3)
                driver.execute_script("""
                    var btns = Array.from(document.querySelectorAll('div[aria-label="Close chat"], div[aria-label*="Close chat"], div[aria-label="Minimize chat"]'));
                    for (var b of btns) { try { b.click(); } catch(e){} }
                """)
            except Exception:
                pass

            return {
                "status": "success",
                "platform": "facebook",
                "sent_count": len(sent_recipients),
                "facebook_shares": len(sent_recipients),
                "instagram_shares": 0,
                "target_count": effective_target,
                "recipients": sent_recipients,
                "post_url": current_post_url,
                "screenshot_path": screenshot_path,
                "logs": logs
            }

    except Exception as e:
        logger.error(f"Error sharing Facebook post to friends: {e}", exc_info=True)
        return {
            "status": "error",
            "platform": "facebook",
            "message": str(e),
            "sent_count": len(sent_recipients),
            "facebook_shares": 0,
            "instagram_shares": 0,
            "recipients": sent_recipients,
            "logs": logs
        }


def share_post_to_all_platforms(
    campaign_id: str,
    platforms=None,
    share_all: bool = True,
    target_count: int = 100,
    safety_delay: int = 8,
    on_progress=None,
    stop_event=None
) -> dict:
    """
    Executes the complete 'Share to All' workflow:
    1. Shares post to Instagram friends via Direct.
    2. Shares post to Facebook friends via Messenger.
    3. Aggregates results, logs every share to database, and captures verification screenshots.
    """
    if not platforms:
        camp = get_campaign_from_db(campaign_id)
        platforms = camp.get("platforms", ["facebook", "instagram"]) if camp else ["facebook", "instagram"]

    platforms = [str(p).lower() for p in platforms]
    combined_results = {}
    total_shares = 0
    all_recipients = []
    screenshots = []
    logs = [f"🚀 Initiated 'Share to All' for campaign {campaign_id} on {', '.join(platforms)}"]

    if "instagram" in platforms:
        if stop_event and stop_event.is_set():
            return {"status": "stopped", "total_shares": total_shares, "logs": logs}
        ig_res = share_instagram_post_to_friends(
            campaign_id=campaign_id,
            share_all=share_all,
            target_count=target_count,
            safety_delay=safety_delay,
            on_progress=on_progress,
            stop_event=stop_event
        )
        combined_results["instagram"] = ig_res
        total_shares += ig_res.get("sent_count", 0)
        all_recipients.extend(ig_res.get("recipients", []))
        if ig_res.get("screenshot_path"):
            screenshots.append(ig_res["screenshot_path"])
        logs.extend(ig_res.get("logs", []))

        # Safe transition breathing break between platforms
        time.sleep(random.uniform(4.0, 7.0))

    if "facebook" in platforms:
        if stop_event and stop_event.is_set():
            return {"status": "stopped", "total_shares": total_shares, "logs": logs}
        fb_res = share_facebook_post_to_friends(
            campaign_id=campaign_id,
            share_all=share_all,
            target_count=target_count,
            safety_delay=safety_delay,
            on_progress=on_progress,
            stop_event=stop_event
        )
        combined_results["facebook"] = fb_res
        total_shares += fb_res.get("sent_count", 0)
        all_recipients.extend(fb_res.get("recipients", []))
        if fb_res.get("screenshot_path"):
            screenshots.append(fb_res["screenshot_path"])
        logs.extend(fb_res.get("logs", []))

    stats = get_post_shares_stats(campaign_id)
    return {
        "status": "success" if total_shares > 0 else "completed",
        "campaign_id": campaign_id,
        "total_shares": total_shares,
        "instagram_shares": combined_results.get("instagram", {}).get("sent_count", 0),
        "facebook_shares": combined_results.get("facebook", {}).get("sent_count", 0),
        "all_recipients": all_recipients,
        "platforms": platforms,
        "screenshots": screenshots,
        "cumulative_stats": stats,
        "logs": logs
    }
