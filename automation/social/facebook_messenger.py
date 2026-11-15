"""
Facebook Messenger Personal Messaging & Reel Sharing Engine.
Directly delivers reels, links, and custom messages to Facebook friends' personal inboxes:
1. Native Share Modal for Reels and post links (fast multi-checkbox batch distribution).
2. Direct 1-on-1 Messenger inbox chats for pure custom text messages.
3. Safe limit (capped at 30-35 friends per session) with 8-14s human delays and micro-cooldowns.
4. Action block & restriction detection with instant screenshot alerts.
5. SQLite & PostgreSQL logging (post_shares_log).
"""
import os
import sys
import time
import re
import json
import random
import logging
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
        sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "automation"))

from browser.driver import browser
from config import BASE_DIR
from db_campaigns import record_post_share

logger = logging.getLogger("automation.social.facebook_messenger")

MAX_SAFE_FB_MESSAGES_PER_SESSION = 35
BASE_SAFETY_DELAY_MIN = 8.0
BASE_SAFETY_DELAY_MAX = 14.0
MICRO_COOLDOWN_EVERY = 10
MICRO_COOLDOWN_SECONDS = 30


def detect_facebook_action_block(driver) -> dict:
    """
    Checks if Facebook displayed an action block, rate limit, or security alert dialog.
    Returns: {"blocked": True/False, "reason": str, "screenshot": str}
    """
    from selenium.webdriver.common.by import By
    block_signatures = [
        "you can't send messages right now",
        "temporarily blocked",
        "action blocked",
        "you can't use this feature right now",
        "please try again later",
        "your account is restricted",
        "misusing this feature",
        "going too fast",
        "limit reached",
        "something went wrong"
    ]

    try:
        dialogs = driver.find_elements(By.CSS_SELECTOR, "div[role='dialog'], div[role='alertdialog'], div[data-testid*='alert']")
        for d in dialogs:
            if d.is_displayed():
                txt = (d.text or "").lower()
                for sig in block_signatures:
                    if sig in txt:
                        screenshot_path = str(BASE_DIR / "data" / "media" / f"fb_block_alert_{int(time.time())}.png")
                        try:
                            os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
                            driver.save_screenshot(screenshot_path)
                            logger.error(f"🚨 Facebook action block detected: '{sig}'. Screenshot saved: {screenshot_path}")
                        except Exception:
                            pass
                        return {"blocked": True, "reason": txt[:150], "screenshot": screenshot_path}
    except Exception:
        pass

    return {"blocked": False, "reason": None, "screenshot": None}


def send_facebook_reels_or_post_to_friends(
    post_url: str = None,
    message_text: str = None,
    campaign_id: str = None,
    share_all: bool = False,
    target_count: int = 30,
    safety_delay: int = 8,
    on_progress=None,
    stop_event=None
) -> dict:
    """
    Shares a Reel or published post link to Facebook friends via the native Facebook
    Messenger Share dialog with multi-contact selection.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys

    driver = browser.get_driver("facebook")
    logs = []
    sent_recipients = []
    screenshot_path = None
    effective_target = min(target_count, MAX_SAFE_FB_MESSAGES_PER_SESSION) if not share_all else MAX_SAFE_FB_MESSAGES_PER_SESSION

    target_url = post_url or "https://www.facebook.com/me"
    logs.append(f"📘 Opening Facebook: {target_url} (Target: {effective_target} friends)")
    logger.info(f"Starting Facebook Reel/Post Messenger share | Target: {target_url} | Cap: {effective_target}")

    if on_progress:
        try:
            on_progress(0, effective_target, {"activity": "Opening Facebook and locating target reel/post..."})
        except Exception:
            pass

    try:
        browser.switch_to_platform_tab("facebook", target_url=target_url, driver=driver)
        with browser.tab_focus("facebook", url=target_url) as active_driver:
            driver = active_driver or driver
            time.sleep(random.uniform(2.5, 3.5))

            if browser.is_blank_or_unrendered(driver):
                browser.ensure_healthy_page(driver, "facebook", target_url=target_url)
                time.sleep(2.0)

            # Check for action block immediately
            blk = detect_facebook_action_block(driver)
            if blk.get("blocked"):
                return {"status": "rate_limited", "platform": "facebook", "message": blk.get("reason"), "screenshot": blk.get("screenshot")}

            # Dismiss any leftover modals
            try:
                for _ in range(2):
                    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                    time.sleep(0.3)
            except Exception:
                pass

            # Step 1: Locate and click Share button
            logs.append("🔍 Locating Share button on post/reel...")
            driver.execute_script("window.scrollBy(0, 400);")
            time.sleep(1.5)

            share_clicked = False
            share_selectors = [
                "//div[contains(@aria-label, 'Share, send this to friends') and @role='button']",
                "//div[contains(@aria-label, 'Send this to friends') and @role='button']",
                "//div[@aria-label='Share' and @role='button']",
                "//span[text()='Share']/ancestor::div[@role='button']",
                "//span[text()='Send']/ancestor::div[@role='button']"
            ]
            for sel in share_selectors:
                btns = driver.find_elements(By.XPATH, sel)
                for b in btns:
                    if b.is_displayed():
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", b)
                        share_clicked = True
                        time.sleep(2.0)
                        break
                if share_clicked:
                    break

            if not share_clicked:
                err_msg = "Could not find native Share button on Facebook post/reel."
                logs.append(f"❌ {err_msg}")
                return {"status": "error", "platform": "facebook", "message": err_msg, "logs": logs}

            logs.append("✅ Clicked Share button. Expanding Messenger contacts...")

            # Step 2: Under Send in Messenger, click 'More' button to reveal friend list
            time.sleep(1.5)
            more_clicked = False
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
                        more_clicked = True
                        time.sleep(2.0)
                        break
                if more_clicked:
                    break

            logs.append("✅ Opened Messenger contacts list. Populating friend checkboxes...")

            # Step 3: Wait for contact checkboxes to appear
            checkboxes_found = False
            for _ in range(10):
                cb_count = driver.execute_script("""
                    var dialogs = Array.from(document.querySelectorAll('div[role="dialog"]'));
                    if (!dialogs.length) return 0;
                    var activeDialog = dialogs[dialogs.length - 1];
                    return activeDialog.querySelectorAll('input[type="checkbox"], div[role="checkbox"]').length;
                """)
                if cb_count and cb_count > 0:
                    checkboxes_found = True
                    logs.append(f"📋 Found {cb_count} friends available to message.")
                    break
                time.sleep(0.8)

            if not checkboxes_found:
                err_msg = "Facebook Messenger contacts checkboxes did not render."
                logs.append(f"❌ {err_msg}")
                return {"status": "error", "platform": "facebook", "message": err_msg, "logs": logs}

            # Step 4: Select friend checkboxes up to effective_target (Safe max 35)
            js_select_friends = """
            var dialogs = Array.from(document.querySelectorAll('div[role="dialog"]'));
            if (!dialogs.length) return {selected: [], count: 0};
            var activeDialog = dialogs[dialogs.length - 1];
            var targetLimit = arguments[0];

            var cbs = Array.from(activeDialog.querySelectorAll('input[type="checkbox"], div[role="checkbox"]'));
            var selectedNames = [];

            for (var i = 0; i < cbs.length && selectedNames.length < targetLimit; i++) {
                var cb = cbs[i];
                var parent = cb.closest('div[role="listitem"]') || cb.parentElement;
                var rawName = (parent.innerText || '').trim();
                var name = rawName.split('\\n')[0].replace(/Online status indicator/g, '').replace(/Active/g, '').trim();

                var isChecked = cb.checked || cb.getAttribute('aria-checked') === 'true';
                if (!isChecked) {
                    cb.click();
                    isChecked = cb.checked || cb.getAttribute('aria-checked') === 'true';
                }
                if (isChecked && name) {
                    selectedNames.push(name);
                }
            }
            return {selected: selectedNames, count: selectedNames.length};
            """
            sel_res = driver.execute_script(js_select_friends, effective_target)
            selected_friends = sel_res.get("selected", []) if sel_res else []
            logs.append(f"👥 Selected {len(selected_friends)} friend checkboxes (Limit: {effective_target}).")

            if not selected_friends:
                err_msg = "Could not check any friend checkboxes."
                logs.append(f"⚠️ {err_msg}")
                return {"status": "error", "platform": "facebook", "message": err_msg, "logs": logs}

            # Optional: Input custom message text if composer is available in the modal
            if message_text:
                try:
                    js_type_msg = """
                    var dialogs = Array.from(document.querySelectorAll('div[role="dialog"]'));
                    if (!dialogs.length) return false;
                    var activeDialog = dialogs[dialogs.length - 1];
                    var inp = activeDialog.querySelector('div[contenteditable="true"], textarea, input[type="text"]');
                    if (inp) {
                        inp.focus();
                        document.execCommand('insertText', false, arguments[0]);
                        return true;
                    }
                    return false;
                    """
                    driver.execute_script(js_type_msg, message_text[:200])
                    time.sleep(1.0)
                except Exception:
                    pass

            # Step 5: Click native 'Send separately' or 'Send' button
            js_click_send = """
            var dialogs = Array.from(document.querySelectorAll('div[role="dialog"]'));
            if (!dialogs.length) return false;
            var activeDialog = dialogs[dialogs.length - 1];

            var btns = Array.from(activeDialog.querySelectorAll('div[role="button"], button'));
            for (var b of btns) {
                var txt = (b.innerText || '').trim().toLowerCase();
                var aria = (b.getAttribute('aria-label') || '').toLowerCase();
                if (txt === 'send' || txt === 'send separately' || aria === 'send' || aria === 'send separately') {
                    b.scrollIntoView({block: 'center'});
                    b.click();
                    return true;
                }
            }
            return false;
            """
            send_clicked = driver.execute_script(js_click_send)
            time.sleep(3.0)

            # Check if action block appeared after clicking send
            blk_after = detect_facebook_action_block(driver)
            if blk_after.get("blocked"):
                return {"status": "rate_limited", "platform": "facebook", "message": blk_after.get("reason"), "screenshot": blk_after.get("screenshot")}

            # Capture verification screenshot
            screenshot_path = str(BASE_DIR / "data" / "media" / f"fb_reel_share_{int(time.time())}.png")
            try:
                os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
                driver.save_screenshot(screenshot_path)
            except Exception:
                pass

            # Record each friend in database
            camp_ref = campaign_id or f"cmsg_{int(time.time())}"
            for fname in selected_friends:
                sent_recipients.append(fname)
                record_post_share(
                    campaign_id=camp_ref,
                    platform="facebook",
                    recipient_name=fname,
                    post_url=post_url,
                    content_type="reel" if "reel" in str(post_url).lower() else "message",
                    status="sent",
                    share_mode="messenger_personal"
                )

            logs.append(f"🎉 Successfully sent to {len(sent_recipients)} Facebook friends via Messenger!")
            logger.info(f"Dispatched Facebook Messenger reel/post share to {len(sent_recipients)} friends.")

            return {
                "status": "success",
                "platform": "facebook",
                "mode": "messenger_modal",
                "sent_count": len(sent_recipients),
                "recipients": sent_recipients,
                "screenshot": screenshot_path,
                "logs": logs
            }

    except Exception as e:
        logger.error(f"Error sharing Facebook post to friends: {e}")
        return {"status": "error", "platform": "facebook", "message": str(e), "logs": logs}


def get_recently_messaged_facebook_friends(hours: int = 24) -> set:
    """
    Returns a set of lowercased friend names messaged on Facebook in the last N hours
    to ensure we never repeat messages to the same person.
    """
    import sqlite3
    db_path = BASE_DIR / "data" / "database.sqlite"
    if not db_path.exists():
        return set()
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT LOWER(TRIM(recipient_name))
            FROM post_shares_log
            WHERE platform = 'facebook' AND created_at >= datetime('now', ?)
        """, (f"-{hours} hours",))
        rows = cur.fetchall()
        conn.close()
        return {r[0] for r in rows if r[0]}
    except Exception as e:
        logger.debug(f"Could not read recently messaged friends: {e}")
        return set()


def send_facebook_direct_text_messages(
    message_text: str,
    target_count: int = 25,
    on_progress=None,
    stop_event=None
) -> dict:
    """
    Sends custom text messages directly into 1-on-1 Messenger chat inboxes by harvesting
    DISTINCT Facebook friends from the user's friends list (https://www.facebook.com/me/friends).
    
    Guarantees:
    1. Every recipient is a distinct Facebook friend (never repeats the same friend).
    2. Excludes friends messaged within the past 24 hours.
    3. Excludes self-profile and non-profile links.
    4. Opens the friend profile, clicks Message, types into the chat dock, and closes the dock cleanly.
    5. Anti-action-block human delays (8-14s) and micro-cooldowns.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys

    driver = browser.get_driver("facebook")
    logs = []
    sent_recipients = []
    screenshot_path = None
    effective_target = min(target_count, MAX_SAFE_FB_MESSAGES_PER_SESSION)

    logs.append(f"📘 Starting Facebook distinct friends outreach (Target: {effective_target} friends)")
    logger.info(f"Starting 1-on-1 Facebook Messenger outreach | Target: {effective_target} friends")

    if on_progress:
        try:
            on_progress(0, effective_target, {"activity": "Opening Facebook Friends directory..."})
        except Exception:
            pass

    try:
        friends_url = "https://www.facebook.com/me/friends"
        browser.switch_to_platform_tab("facebook", target_url=friends_url, driver=driver)
        with browser.tab_focus("facebook", url=friends_url) as active_driver:
            driver = active_driver or driver
            time.sleep(random.uniform(3.5, 4.5))

            # Check action block
            blk = detect_facebook_action_block(driver)
            if blk.get("blocked"):
                return {"status": "rate_limited", "platform": "facebook", "message": blk.get("reason"), "screenshot": blk.get("screenshot")}

            # Identify self profile to exclude self
            current_url = driver.current_url
            self_id = None
            if "id=" in current_url:
                match = re.search(r'id=(\d+)', current_url)
                if match:
                    self_id = match.group(1)

            # ── Step 1: Dynamically scroll friends directory to load a large friend pool ──
            # For 10 friends, scroll ~4-5 times; for 25-35 friends, scroll ~10-12 times.
            num_scrolls = max(5, int(effective_target * 0.5) + 3)
            logs.append(f"🔍 Loading friends list (Scrolling {num_scrolls} times for deep candidate pool)...")
            
            for s in range(num_scrolls):
                driver.execute_script("window.scrollBy(0, 1200);")
                time.sleep(1.2)

            time.sleep(1.5)

            # ── Step 2: Harvest clean, distinct friend profiles via JavaScript ──
            js_harvest_friends = """
            var links = Array.from(document.querySelectorAll('a'));
            var friends = [];
            var seen = new Set();

            var excludedWords = [
                'friends', 'friend', 'mutual', 'about', 'photos', 'reels', 'following', 
                'followers', 'edit profile', 'add to story', 'settings', 'notifications',
                'marketplace', 'gaming', 'groups', 'events', 'bookmarks', 'saved', 'all',
                'recently added', 'birthdays', 'manage', 'privacy', 'terms', 'cookies'
            ];

            for (var a of links) {
                var href = a.href || '';
                var text = (a.innerText || '').trim();
                
                // Must have non-empty text and not multi-line
                if (!text || text.includes('\\n') || text.length < 2 || text.length > 50) continue;
                
                // Check if text is excluded
                var lower = text.toLowerCase();
                if (excludedWords.some(function(w) { return lower === w || lower.includes('mutual friend') || lower.includes('friends'); })) {
                    continue;
                }
                
                // Must be a Facebook profile link
                var isProfile = false;
                if (href.includes('/profile.php?id=')) {
                    isProfile = true;
                } else if (href.includes('facebook.com/') && !href.includes('/friends') && !href.includes('/stories') && !href.includes('/groups') && !href.includes('/hashtag')) {
                    var path = href.split('facebook.com/')[1].split('/')[0].split('?')[0];
                    if (path && path.length > 1 && !excludedWords.includes(path.toLowerCase())) {
                        isProfile = true;
                    }
                }
                
                // Clean href to remove query params except id
                var cleanUrl = href;
                if (href.includes('/profile.php?id=')) {
                    var match = href.match(/id=\\d+/);
                    if (match) cleanUrl = 'https://www.facebook.com/profile.php?' + match[0];
                } else {
                    cleanUrl = href.split('?')[0];
                }
                
                if (isProfile && !seen.has(text.toLowerCase()) && !seen.has(cleanUrl)) {
                    seen.add(text.toLowerCase());
                    seen.add(cleanUrl);
                    friends.push({name: text, url: cleanUrl});
                }
            }
            return friends;
            """
            raw_candidates = driver.execute_script(js_harvest_friends) or []
            logs.append(f"📋 Discovered {len(raw_candidates)} distinct friend profiles from friends directory.")
            logger.info(f"Discovered {len(raw_candidates)} distinct friend profiles from Facebook friends page.")

            # ── Step 3: De-duplicate and filter candidates ──
            recently_messaged = get_recently_messaged_facebook_friends(hours=24)
            filtered_candidates = []
            seen_names = set()
            seen_urls = set()

            for cand in raw_candidates:
                cname = cand.get("name", "").strip()
                curl = cand.get("url", "").strip()
                cname_lower = cname.lower()

                # Exclude self profile
                if self_id and f"id={self_id}" in curl:
                    continue
                if "techie shivam" in cname_lower:
                    continue

                # Exclude already processed in this batch
                if cname_lower in seen_names or curl in seen_urls:
                    continue

                # Exclude friends messaged in the past 24 hours
                if cname_lower in recently_messaged:
                    continue

                seen_names.add(cname_lower)
                seen_urls.add(curl)
                filtered_candidates.append(cand)

            logs.append(f"✨ Filtered to {len(filtered_candidates)} fresh, unique friends (excluding already messaged).")
            logger.info(f"Fresh candidate pool: {len(filtered_candidates)} distinct friends.")

            if not filtered_candidates:
                err_msg = "Could not find any new friends to message. All visible friends may have already been contacted today."
                logs.append(f"⚠️ {err_msg}")
                logger.warning(err_msg)
                return {"status": "error", "platform": "facebook", "message": err_msg, "sent_count": 0, "recipients": [], "logs": logs}

            # ── Step 4: Dispatch messages to distinct friends one by one ──
            count = 0
            for item in filtered_candidates:
                if stop_event and stop_event.is_set():
                    logs.append("🛑 Operation cancelled by user.")
                    break
                if count >= effective_target:
                    break

                fname = item.get("name", "Friend")
                furl = item.get("url", "")
                logs.append(f"💬 [{count+1}/{effective_target}] Messaging friend: {fname}...")

                if on_progress:
                    try:
                        on_progress(count, effective_target, {"activity": f"Messaging {fname}...", "friend": fname})
                    except Exception:
                        pass

                try:
                    driver.get(furl)
                    time.sleep(random.uniform(2.5, 3.5))

                    # Check for action block immediately on friend's page
                    blk_chk = detect_facebook_action_block(driver)
                    if blk_chk.get("blocked"):
                        return {"status": "rate_limited", "platform": "facebook", "message": blk_chk.get("reason"), "sent_count": count, "recipients": sent_recipients, "screenshot": blk_chk.get("screenshot")}

                    # Locate 'Message' button on profile
                    msg_btn = None
                    for sel in [
                        "//div[@aria-label='Message' and @role='button']",
                        "//span[text()='Message']/ancestor::div[@role='button']",
                        "//div[contains(@aria-label, 'Message') and @role='button']",
                        "//a[contains(@aria-label, 'Message')]"
                    ]:
                        elems = driver.find_elements(By.XPATH, sel)
                        for el in elems:
                            if el.is_displayed():
                                msg_btn = el
                                break
                        if msg_btn:
                            break

                    if not msg_btn:
                        logs.append(f"⚠️ No Message button on {fname}'s profile. Skipping to next friend.")
                        continue

                    # Click 'Message' button to open chat dock
                    driver.execute_script("arguments[0].click();", msg_btn)
                    time.sleep(random.uniform(2.0, 2.8))

                    # Locate the popup chat dock composer textbox
                    js_find_chat_box = """
                    var targetBox = null;
                    var candidates = Array.from(document.querySelectorAll('div[role="textbox"][contenteditable="true"]'));
                    for (var c of candidates) {
                        var aria = (c.getAttribute('aria-label') || '').toLowerCase();
                        if (aria.includes('comment') || aria.includes('search') || aria.includes('post')) continue;
                        if (aria.includes('write to') || aria.includes('message') || c.closest('div[data-pagelet*="ChatTab"]') || c.closest('div[role="region"]')) {
                            targetBox = c;
                            break;
                        }
                    }
                    if (!targetBox && candidates.length > 0) {
                        targetBox = candidates[candidates.length - 1];
                    }
                    if (targetBox) {
                        targetBox.focus();
                        return true;
                    }
                    return false;
                    """
                    box_ready = driver.execute_script(js_find_chat_box)
                    if not box_ready:
                        logs.append(f"⚠️ Could not locate chat composer for {fname}. Skipping.")
                        continue

                    # Type the message using human execCommand & dispatch event
                    js_type_in_box = """
                    var candidates = Array.from(document.querySelectorAll('div[role="textbox"][contenteditable="true"]'));
                    var box = null;
                    for (var c of candidates) {
                        var aria = (c.getAttribute('aria-label') || '').toLowerCase();
                        if (aria.includes('comment') || aria.includes('search') || aria.includes('post')) continue;
                        if (aria.includes('write to') || aria.includes('message') || c.closest('div[data-pagelet*="ChatTab"]')) {
                            box = c;
                            break;
                        }
                    }
                    if (!box && candidates.length > 0) box = candidates[candidates.length - 1];
                    if (box) {
                        box.focus();
                        document.execCommand('selectAll', false, null);
                        document.execCommand('delete', false, null);
                        document.execCommand('insertText', false, arguments[0]);
                        box.dispatchEvent(new Event('input', { bubbles: true }));
                        return true;
                    }
                    return false;
                    """
                    driver.execute_script(js_type_in_box, message_text)
                    time.sleep(random.uniform(0.8, 1.4))

                    # Send Keys.ENTER via selenium on the active focused element
                    active_el = driver.switch_to.active_element
                    active_el.send_keys(Keys.ENTER)
                    time.sleep(1.8)

                    # Close the chat dock tab to keep DOM clean and prevent overlapping tabs
                    js_close_tab = """
                    var closeBtns = Array.from(document.querySelectorAll('div[aria-label="Close chat"], div[aria-label="Close"], div[aria-label*="close" i]'));
                    for (var b of closeBtns) {
                        if (b.offsetParent !== null) {
                            b.click();
                            return true;
                        }
                    }
                    return false;
                    """
                    driver.execute_script(js_close_tab)
                    time.sleep(0.5)

                    count += 1
                    sent_recipients.append(fname)
                    record_post_share(
                        campaign_id=f"cmsg_txt_{int(time.time())}",
                        platform="facebook",
                        recipient_name=fname,
                        post_url=furl,
                        content_type="message",
                        status="sent",
                        share_mode="messenger_1on1"
                    )
                    logs.append(f"✅ Delivered to {fname} ({count}/{effective_target}).")

                    # Check for action block immediately after sending
                    blk_now = detect_facebook_action_block(driver)
                    if blk_now.get("blocked"):
                        return {
                            "status": "rate_limited",
                            "platform": "facebook",
                            "message": blk_now.get("reason"),
                            "sent_count": count,
                            "recipients": sent_recipients,
                            "screenshot": blk_now.get("screenshot")
                        }

                    # Micro-cooldown pause every 10 messages
                    if count % MICRO_COOLDOWN_EVERY == 0 and count < effective_target:
                        logs.append(f"☕ Safety pause for {MICRO_COOLDOWN_SECONDS}s to keep Facebook account safe...")
                        time.sleep(MICRO_COOLDOWN_SECONDS)
                    else:
                        pause = random.uniform(BASE_SAFETY_DELAY_MIN, BASE_SAFETY_DELAY_MAX)
                        time.sleep(pause)

                except Exception as e_fr:
                    logger.warning(f"Could not message friend {fname}: {e_fr}")
                    logs.append(f"⚠️ Error messaging {fname}: {str(e_fr)[:80]}")
                    continue

            # Capture completion screenshot
            screenshot_path = str(BASE_DIR / "data" / "media" / f"fb_direct_outreach_{int(time.time())}.png")
            try:
                os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
                driver.save_screenshot(screenshot_path)
            except Exception:
                pass

            if on_progress:
                try:
                    on_progress(count, effective_target, {"activity": "Completed Facebook Messenger outreach!"})
                except Exception:
                    pass

            return {
                "status": "success",
                "platform": "facebook",
                "mode": "messenger_1on1",
                "sent_count": len(sent_recipients),
                "recipients": sent_recipients,
                "screenshot": screenshot_path,
                "logs": logs
            }

    except Exception as e:
        logger.error(f"Error in direct Facebook Messenger outreach: {e}")
        return {"status": "error", "platform": "facebook", "message": str(e), "logs": logs}


def _is_facebook_native_url(url: str) -> bool:
    """Check if a URL is a Facebook-native link that can use the Share modal."""
    if not url:
        return False
    url_lower = url.lower().strip()
    fb_domains = ["facebook.com", "fb.com", "fb.watch", "m.facebook.com"]
    return any(domain in url_lower for domain in fb_domains)


def send_facebook_friends_outreach(
    message_text: str = None,
    reel_url: str = None,
    campaign_id: str = None,
    target_count: int = 30,
    share_all: bool = False,
    on_progress=None,
    stop_event=None
) -> dict:
    """
    Unified Hybrid Dispatcher:
    - If a Facebook Reel or Facebook post link is present: uses the native Messenger Share dialog.
    - If non-Facebook URL (Instagram, YouTube, etc.) or pure text: uses 1-on-1 Messenger chat delivery.
    - Automatic graceful fallback: If native Share dialog encounters an issue, automatically falls back
      to 1-on-1 Messenger delivery to ensure message is delivered.
    """
    extracted_link = reel_url
    if not extracted_link and message_text:
        urls = re.findall(r'https?://[^\s]+', message_text)
        if urls:
            extracted_link = urls[0].rstrip('.,;!?')

    has_link = bool(extracted_link)

    # Prepare combined message
    full_message = message_text or ""
    if not full_message and extracted_link:
        full_message = extracted_link
    elif extracted_link and extracted_link not in (full_message or ""):
        full_message = f"{full_message}\n{extracted_link}" if full_message else extracted_link

    # Attempt native Share modal for Facebook-native URLs
    if has_link and extracted_link and _is_facebook_native_url(extracted_link):
        logger.info(f"Hybrid Mode: Facebook-native link detected ({extracted_link[:60]}). Using Native Messenger Share modal.")
        res = send_facebook_reels_or_post_to_friends(
            post_url=extracted_link,
            message_text=message_text,
            campaign_id=campaign_id,
            share_all=share_all,
            target_count=target_count,
            on_progress=on_progress,
            stop_event=stop_event
        )
        if res.get("status") == "success" and res.get("sent_count", 0) > 0:
            return res
        logger.warning("Facebook Native Share modal could not deliver. Gracefully falling back to 1-on-1 Messenger delivery...")

    # For non-Facebook URLs (Instagram, YouTube, etc.) or fallback:
    mode_desc = "non-Facebook URL" if has_link else "pure text"
    logger.info(f"Hybrid Mode: {mode_desc} detected. Using 1-on-1 Messenger Inbox Chats for distinct friend delivery.")
    return send_facebook_direct_text_messages(
        message_text=full_message or "Hello! Wishing you a wonderful day.",
        target_count=target_count,
        on_progress=on_progress,
        stop_event=stop_event
    )

