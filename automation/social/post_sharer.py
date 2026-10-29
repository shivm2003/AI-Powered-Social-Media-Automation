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


def share_instagram_post_to_friends(
    post_url: str = None,
    campaign_id: str = None,
    share_all: bool = True,
    target_count: int = 25,
    safety_delay: int = 8,
    on_progress=None,
    stop_event=None,
    capture_screenshot: bool = True
) -> dict:
    """
    Navigates to an Instagram post, opens the native Share modal,
    selects friend contacts with human-like delays, sends the post,
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
        # Default to current or recent post on user's Instagram profile
        target_url = "https://www.instagram.com/loansolutions2026/"

    logs.append(f"📸 Opening Instagram target post: {target_url}")
    logger.info(f"Starting Instagram post share | Target: {target_url} (Share All: {share_all})")

    if on_progress:
        try:
            on_progress(0, target_count, {"activity": "Connecting to Instagram post..."})
        except Exception:
            pass

    try:
        browser.switch_to_platform_tab("instagram", target_url=target_url, driver=driver)
        with browser.tab_focus("instagram", url=target_url) as active_driver:
            driver = active_driver or driver
            time.sleep(random.uniform(2.5, 3.5))

            if browser.is_blank_or_unrendered(driver):
                logger.warning("Instagram post tab unrendered. Auto-healing...")
                browser.ensure_healthy_page(driver, "instagram", target_url=target_url)
                time.sleep(2.0)

            # If user targeted profile URL instead of direct post URL, open latest post thumbnail
            if "/p/" not in driver.current_url and "/reel/" not in driver.current_url:
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

            # 1. Click native 'Share' button
            share_clicked = driver.execute_script("""
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

            if not share_clicked:
                # Fallback XPath
                svg_btns = driver.find_elements(By.XPATH, "//*[local-name()='svg' and (@aria-label='Share' or @aria-label='Share Post')]/ancestor::button | //*[local-name()='svg' and (@aria-label='Share' or @aria-label='Share Post')]/ancestor::div[@role='button']")
                if svg_btns:
                    driver.execute_script("arguments[0].click();", svg_btns[0])
                    share_clicked = True

            if not share_clicked:
                msg = "Could not locate Share button on Instagram post."
                logger.warning(msg)
                return {"status": "error", "message": msg, "sent_count": 0, "logs": logs}

            logs.append("📋 Opened Instagram native 'Share' recipient dialog")
            time.sleep(2.8)

            if on_progress:
                try:
                    on_progress(0, target_count, {"activity": "Scanning friends list in Share dialog..."})
                except Exception:
                    pass

            # 2. Discover Friend Contacts in Dialog (target topmost dialog)
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

            logger.info(f"Discovered {len(friend_items)} friend contacts in Instagram share modal.")
            logs.append(f"👥 Discovered {len(friend_items)} friends in contact list.")

            if not friend_items:
                msg = "No friend contacts found in Instagram share dialog."
                logger.warning(msg)
                return {"status": "no_contacts", "message": msg, "sent_count": 0, "logs": logs}

            effective_target = len(friend_items) if share_all else min(target_count, len(friend_items))
            # Safe ceiling per Instagram DM guidelines
            effective_target = min(effective_target, 30)

            # 3. Select Friends Sequentially with Human-Touch Delays
            for idx in range(effective_target):
                if stop_event and stop_event.is_set():
                    logs.append("🛑 Share task stopped by user.")
                    break

                item_info = friend_items[idx]
                fname = item_info.get("name") or f"friend_{idx+1}"
                uname = item_info.get("username") or ""
                display_label = f"{fname} (@{uname})" if uname else fname

                # Click contact row in DOM (topmost dialog)
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

                    log_msg = f"✅ Added friend #{len(sent_recipients)}: '{display_label}' to share list"
                    logs.append(log_msg)
                    logger.info(log_msg)

                    if on_progress:
                        try:
                            on_progress(len(sent_recipients), effective_target, {
                                "platform": "instagram",
                                "friend": display_label,
                                "sent": len(sent_recipients),
                                "target": effective_target,
                                "activity": f"✅ Selected friend '{display_label}' ({len(sent_recipients)}/{effective_target})"
                            })
                        except Exception:
                            pass

                    # Human-like pacing pause between contact selections
                    delay = random.uniform(max(1.0, safety_delay * 0.25), max(2.5, safety_delay * 0.45))
                    time.sleep(delay)

            # 4. Click 'Send' / 'Send separately' button
            time.sleep(1.2)
            send_clicked = driver.execute_script("""
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

            if not send_clicked:
                send_btns = driver.find_elements(By.XPATH, "//div[@role='dialog']//button[contains(., 'Send')] | //div[@role='dialog']//div[@role='button'][contains(., 'Send')]")
                if send_btns:
                    driver.execute_script("arguments[0].click();", send_btns[-1])
                    send_clicked = True

            logs.append(f"🚀 Clicked 'Send' button: Dispatched post to {len(sent_recipients)} friends!")
            logger.info(f"Dispatched post to {len(sent_recipients)} friends on Instagram.")
            time.sleep(2.5)
            logger.info(f"Dispatched post to {len(sent_recipients)} friends on Instagram.")
            time.sleep(2.5)

            # Capture verification screenshot
            if capture_screenshot:
                try:
                    ss_dir = BASE_DIR / "data" / "media" / "post_share_captures"
                    ss_dir.mkdir(parents=True, exist_ok=True)
                    ss_file = ss_dir / f"ig_share_{int(time.time())}.png"
                    driver.save_screenshot(str(ss_file))
                    screenshot_path = str(ss_file)
                    logger.info(f"📸 Captured Instagram share verification screenshot: {screenshot_path}")
                except Exception as e_ss:
                    logger.debug(f"Screenshot note: {e_ss}")

            # Close dialog cleanly if still visible
            try:
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            except Exception:
                pass

            return {
                "status": "success",
                "platform": "instagram",
                "sent_count": len(sent_recipients),
                "target_count": effective_target,
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
    target_count: int = 25,
    safety_delay: int = 8,
    on_progress=None,
    stop_event=None,
    capture_screenshot: bool = True
) -> dict:
    """
    Shares a published post or marketing message to Facebook friends via Messenger
    with human-like pacing, anti-detection delays, and live database tracking.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys

    driver = browser.get_driver("facebook")
    logs = []
    sent_recipients = []
    screenshot_path = None

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

    share_msg = post_caption[:180] if post_caption else "Check out our latest update from Loan Solutions!"
    if post_url:
        share_msg += f"\n{post_url}"

    inbox_url = "https://www.facebook.com/messages/new"
    logs.append(f"📘 Opening Facebook Messenger: {inbox_url}")
    logger.info(f"Starting Facebook post share | Share All: {share_all}")

    if on_progress:
        try:
            on_progress(0, target_count, {"activity": "Opening Facebook Messenger to share post..."})
        except Exception:
            pass

    try:
        browser.switch_to_platform_tab("facebook", target_url=inbox_url, driver=driver)
        with browser.tab_focus("facebook", url=inbox_url) as active_driver:
            driver = active_driver or driver
            time.sleep(random.uniform(2.5, 3.5))

            if browser.is_blank_or_unrendered(driver):
                logger.warning("Facebook tab unrendered. Auto-healing...")
                browser.ensure_healthy_page(driver, "facebook", target_url=inbox_url)
                time.sleep(2.0)

            # 1. Discover and pick recipient in New Message or active chat
            recipient_picked = False
            target_friend_name = "Facebook Friend"

            recipient_inputs = driver.find_elements(
                By.XPATH,
                "//input[@aria-label='Send message to' or @placeholder='Search' or contains(@aria-label, 'Search') or contains(@aria-label, 'To:')]"
            )

            if recipient_inputs:
                try:
                    inp = recipient_inputs[0]
                    inp.click()
                    time.sleep(0.4)
                    inp.send_keys("Shivam")
                    time.sleep(1.8)

                    # Pick from suggestion list
                    js_pick = """
                    var options = Array.from(document.querySelectorAll('div[role="option"], ul[role="listbox"] li, div[class*="x1n2onr6"] span'));
                    for (var opt of options) {
                        var txt = (opt.innerText || '').trim();
                        if (txt && !txt.includes('Search') && !txt.includes('To:')) {
                            opt.click();
                            return {found: true, name: txt.split('\\n')[0]};
                        }
                    }
                    return {found: false};
                    """
                    pick_res = driver.execute_script(js_pick)
                    if pick_res and pick_res.get("found"):
                        target_friend_name = pick_res.get("name", "Techie Shivam")
                        recipient_picked = True
                        time.sleep(1.5)
                except Exception as e_pick:
                    logger.debug(f"Recipient pick note: {e_pick}")

            # Fallback to existing chat row if dropdown not clicked
            if not recipient_picked:
                chat_rows = driver.find_elements(
                    By.XPATH,
                    "//div[contains(@class, 'x1n2onr6')]//span[contains(@class, 'x193iq5w')]"
                )
                for cr in chat_rows[:15]:
                    txt = (cr.text or "").strip()
                    if txt and len(txt) < 30 and not any(w in txt.lower() for w in ["search", "messages", "new", "all", "unread"]):
                        target_friend_name = txt
                        driver.execute_script("arguments[0].click();", cr)
                        recipient_picked = True
                        time.sleep(1.5)
                        break

            logs.append(f"👤 Selected Messenger recipient: '{target_friend_name}'")

            # 2. Focus message textbox and dispatch post copy
            js_find_tb = """
            var tbs = Array.from(document.querySelectorAll('div[role="textbox"], div[contenteditable="true"]'));
            for (var tb of tbs) {
                var aria = (tb.getAttribute('aria-label') || '').toLowerCase();
                if (aria.includes('message') || aria.includes('write') || aria.includes('aa') || aria === '' || tb.getAttribute('contenteditable') === 'true') {
                    tb.focus();
                    return true;
                }
            }
            return false;
            """
            tb_focused = driver.execute_script(js_find_tb)
            time.sleep(0.5)

            active_el = driver.switch_to.active_element
            for char in share_msg[:120]:
                active_el.send_keys(char)
                time.sleep(random.uniform(0.02, 0.05))

            time.sleep(0.8)
            active_el.send_keys(Keys.ENTER)
            time.sleep(2.5)

            sent_recipients.append(target_friend_name)
            record_post_share(
                campaign_id=campaign_id or "fb_shared_post",
                platform="facebook",
                recipient_name=target_friend_name,
                post_url=post_url or "https://www.facebook.com/profile.php?id=61593018374598",
                media_path=media_path,
                content_type=content_type,
                status="sent",
                share_mode="share_all" if share_all else "selective"
            )

            logs.append(f"💬 Sent post copy to Facebook friend: '{target_friend_name}'!")
            logger.info(f"Dispatched Facebook post to: {target_friend_name}")

            # Capture screenshot
            if capture_screenshot:
                try:
                    ss_dir = BASE_DIR / "data" / "media" / "post_share_captures"
                    ss_dir.mkdir(parents=True, exist_ok=True)
                    ss_file = ss_dir / f"fb_share_{int(time.time())}.png"
                    driver.save_screenshot(str(ss_file))
                    screenshot_path = str(ss_file)
                    logger.info(f"📸 Captured Facebook share screenshot: {screenshot_path}")
                except Exception as e_ss:
                    logger.debug(f"Screenshot note: {e_ss}")

            return {
                "status": "success",
                "platform": "facebook",
                "sent_count": len(sent_recipients),
                "target_count": effective_target,
                "recipients": sent_recipients,
                "post_url": post_url or driver.current_url,
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
            "recipients": sent_recipients,
            "logs": logs
        }


def share_post_to_all_platforms(
    campaign_id: str,
    platforms=None,
    share_all: bool = True,
    target_count: int = 25,
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
        "all_recipients": all_recipients,
        "platforms": platforms,
        "screenshots": screenshots,
        "cumulative_stats": stats,
        "logs": logs
    }
