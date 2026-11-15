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


def send_facebook_direct_text_messages(
    message_text: str,
    target_count: int = 25,
    on_progress=None,
    stop_event=None
) -> dict:
    """
    Sends custom text messages (including non-Facebook URLs like Instagram links)
    directly into 1-on-1 Messenger chat inboxes via facebook.com/messages/t/.
    Includes human typing delays, 8-14s inter-friend pauses, and anti-spam detection.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys

    driver = browser.get_driver("facebook")
    logs = []
    sent_recipients = []
    screenshot_path = None
    effective_target = min(target_count, MAX_SAFE_FB_MESSAGES_PER_SESSION)

    logs.append(f"📘 Starting Messenger direct outreach (Target: {effective_target} friends)")
    logger.info(f"Starting 1-on-1 Facebook Messenger outreach | Target: {effective_target} friends")

    if on_progress:
        try:
            on_progress(0, effective_target, {"activity": "Opening Facebook Messenger..."})
        except Exception:
            pass

    try:
        # ── Strategy: Use Messenger's own chat list to find recent contacts ──
        messenger_url = "https://www.facebook.com/messages/t/"
        browser.switch_to_platform_tab("facebook", target_url=messenger_url, driver=driver)
        with browser.tab_focus("facebook", url=messenger_url) as active_driver:
            driver = active_driver or driver
            time.sleep(random.uniform(3.5, 5.0))

            # Check action block
            blk = detect_facebook_action_block(driver)
            if blk.get("blocked"):
                return {"status": "rate_limited", "platform": "facebook", "message": blk.get("reason"), "screenshot": blk.get("screenshot")}

            # ── Harvest friend chat threads from Messenger sidebar ──
            # Scroll the Messenger chat list sidebar to load more conversations
            for scroll_pass in range(5):
                driver.execute_script("""
                    var sidebar = document.querySelector('div[aria-label="Chats"]') ||
                                  document.querySelector('nav[aria-label="Chats"]') ||
                                  document.querySelector('div[role="navigation"]');
                    if (sidebar) {
                        sidebar.scrollTop = sidebar.scrollTop + 600;
                    } else {
                        window.scrollBy(0, 600);
                    }
                """)
                time.sleep(1.0)

            time.sleep(1.5)

            # Extract chat threads from Messenger sidebar
            js_get_messenger_chats = """
            var results = [];
            var seen = new Set();

            // Strategy 1: Messenger sidebar chat links
            var chatLinks = Array.from(document.querySelectorAll('a[href*="/messages/t/"], a[href*="messenger.com/t/"]'));
            for (var a of chatLinks) {
                var href = a.href || '';
                var name = '';

                // Get the visible name from the chat entry
                var spans = a.querySelectorAll('span');
                for (var s of spans) {
                    var txt = (s.innerText || '').trim();
                    if (txt.length > 1 && txt.length < 50 && !txt.match(/^\\d/) && txt !== 'You' && !txt.includes('sent') && !txt.includes('ago') && !txt.includes('Active')) {
                        name = txt;
                        break;
                    }
                }
                if (!name) {
                    name = (a.getAttribute('aria-label') || '').replace(/^Chat with /, '').replace(/, .*/, '').trim();
                }

                if (name && name.length > 1 && !seen.has(name)) {
                    seen.add(name);
                    results.push({name: name, url: href});
                }
            }

            // Strategy 2: Chat list items with role="row" or role="listitem"
            if (results.length < 5) {
                var rows = Array.from(document.querySelectorAll('div[role="row"], div[role="listitem"], div[data-testid*="mwthreadlist"]'));
                for (var r of rows) {
                    var link = r.querySelector('a[href*="/messages/"], a[href*="/t/"]');
                    if (!link) continue;
                    var href = link.href || '';
                    var name = '';
                    var nameSpans = r.querySelectorAll('span[dir="auto"]');
                    for (var ns of nameSpans) {
                        var t = (ns.innerText || '').trim();
                        if (t.length > 1 && t.length < 50 && !t.match(/^\\d/) && t !== 'You') {
                            name = t;
                            break;
                        }
                    }
                    if (name && !seen.has(name)) {
                        seen.add(name);
                        results.push({name: name, url: href});
                    }
                }
            }

            return results;
            """
            friend_candidates = driver.execute_script(js_get_messenger_chats) or []
            logs.append(f"📋 Found {len(friend_candidates)} Messenger chat threads.")
            logger.info(f"Harvested {len(friend_candidates)} Messenger chat threads from sidebar.")

            # ── Fallback: if Messenger sidebar yielded nothing, try friends list ──
            if len(friend_candidates) < 3:
                logs.append("ℹ️ Messenger sidebar yield low. Trying Facebook friends list as fallback...")
                friends_url = "https://www.facebook.com/me/friends"
                driver.get(friends_url)
                time.sleep(random.uniform(3.0, 4.5))

                # Scroll multiple times to render more friends
                for _ in range(6):
                    driver.execute_script("window.scrollBy(0, 800);")
                    time.sleep(1.2)

                js_get_friends_fallback = """
                var results = [];
                var seen = new Set();
                var links = Array.from(document.querySelectorAll('a'));
                for (var a of links) {
                    var href = a.href || '';
                    var txt = (a.innerText || '').trim();
                    // Match friend profile links but exclude navigation/utility links
                    if (href.includes('facebook.com/') &&
                        !href.includes('/friends') && !href.includes('/groups') &&
                        !href.includes('/photo') && !href.includes('/hashtag') &&
                        !href.includes('/events') && !href.includes('/pages') &&
                        !href.includes('/marketplace') && !href.includes('/gaming') &&
                        !href.includes('/watch') && !href.includes('/settings') &&
                        !href.includes('/notifications') && !href.includes('/bookmarks') &&
                        !href.includes('?') &&
                        txt.length > 2 && txt.length < 50 &&
                        !txt.includes('\\n') && !txt.match(/^\\d/)) {
                        if (!seen.has(href)) {
                            seen.add(href);
                            results.push({name: txt, url: href, source: 'friends_list'});
                        }
                    }
                }
                return results;
                """
                fallback_friends = driver.execute_script(js_get_friends_fallback) or []
                logs.append(f"📋 Fallback: detected {len(fallback_friends)} friend profiles from /me/friends.")

                # Merge but deduplicate by name
                existing_names = {f.get("name", "").lower() for f in friend_candidates}
                for ff in fallback_friends:
                    if ff.get("name", "").lower() not in existing_names:
                        friend_candidates.append(ff)
                        existing_names.add(ff.get("name", "").lower())

            if not friend_candidates:
                err_msg = "Could not find any friends/chat threads to message. Please ensure you're logged into Facebook."
                logs.append(f"❌ {err_msg}")
                logger.warning(err_msg)
                return {"status": "error", "platform": "facebook", "message": err_msg, "sent_count": 0, "recipients": [], "logs": logs}

            logs.append(f"📋 Total unique candidates for messaging: {len(friend_candidates)}")

            # ── Send messages one by one ──
            count = 0
            for item in friend_candidates:
                if stop_event and stop_event.is_set():
                    logs.append("🛑 Operation cancelled by user.")
                    break
                if count >= effective_target:
                    break

                fname = item.get("name", "Friend")
                furl = item.get("url", "")
                source = item.get("source", "messenger")
                logs.append(f"💬 [{count+1}/{effective_target}] Messaging: {fname}...")

                if on_progress:
                    try:
                        on_progress(count, effective_target, {"activity": f"Messaging {fname}...", "friend": fname})
                    except Exception:
                        pass

                try:
                    # ── Route A: Direct Messenger thread URL ──
                    if "/messages/t/" in furl or "messenger.com/t/" in furl:
                        driver.get(furl)
                        time.sleep(random.uniform(2.5, 4.0))

                        # Find the message composer
                        composer_found = False
                        for comp_sel in [
                            "div[aria-label='Message'][role='textbox']",
                            "div[aria-label='Message'][contenteditable='true']",
                            "div[role='textbox'][contenteditable='true']",
                            "div[contenteditable='true']",
                            "p[data-lexical-text='true']"
                        ]:
                            boxes = driver.find_elements(By.CSS_SELECTOR, comp_sel)
                            active_boxes = [b for b in boxes if b.is_displayed()]
                            if active_boxes:
                                target_box = active_boxes[-1]
                                target_box.click()
                                time.sleep(0.5)

                                # Type the message using execCommand for contenteditable
                                driver.execute_script("""
                                    const ed = arguments[0];
                                    ed.focus();
                                    document.execCommand('selectAll', false, null);
                                    document.execCommand('delete', false, null);
                                    document.execCommand('insertText', false, arguments[1]);
                                    ed.dispatchEvent(new Event('input', { bubbles: true }));
                                """, target_box, message_text)
                                time.sleep(random.uniform(0.8, 1.5))

                                # Hit Enter to send
                                target_box.send_keys(Keys.ENTER)
                                composer_found = True
                                time.sleep(1.5)
                                break

                        if composer_found:
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
                        else:
                            logs.append(f"⚠️ Could not find message composer for {fname}. Skipping.")
                            continue

                    # ── Route B: Friend profile URL → click Message button → type & send ──
                    else:
                        driver.get(furl)
                        time.sleep(random.uniform(2.5, 3.5))

                        # Click 'Message' button on profile
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
                            logs.append(f"⚠️ No Message button on {fname}'s profile. Skipping.")
                            continue

                        driver.execute_script("arguments[0].click();", msg_btn)
                        time.sleep(random.uniform(2.0, 3.0))

                        # Locate chat composer input
                        composer_found = False
                        for comp_sel in [
                            "div[aria-label='Message'][role='textbox']",
                            "div[aria-label='Message'][contenteditable='true']",
                            "div[role='textbox'][contenteditable='true']",
                            "div[contenteditable='true']"
                        ]:
                            boxes = driver.find_elements(By.CSS_SELECTOR, comp_sel)
                            active_boxes = [b for b in boxes if b.is_displayed()]
                            if active_boxes:
                                target_box = active_boxes[-1]
                                target_box.click()
                                time.sleep(0.5)

                                # Human typing
                                driver.execute_script("""
                                    const ed = arguments[0];
                                    ed.focus();
                                    document.execCommand('selectAll', false, null);
                                    document.execCommand('delete', false, null);
                                    document.execCommand('insertText', false, arguments[1]);
                                    ed.dispatchEvent(new Event('input', { bubbles: true }));
                                """, target_box, message_text)
                                time.sleep(random.uniform(0.8, 1.2))

                                # Hit Enter to send
                                target_box.send_keys(Keys.ENTER)
                                composer_found = True
                                time.sleep(1.5)
                                break

                        if composer_found:
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
                        else:
                            logs.append(f"⚠️ Could not find composer for {fname}. Skipping.")
                            continue

                    # Check for action block after each successful send
                    blk_now = detect_facebook_action_block(driver)
                    if blk_now.get("blocked"):
                        return {"status": "rate_limited", "platform": "facebook", "message": blk_now.get("reason"), "sent_count": count, "recipients": sent_recipients, "screenshot": blk_now.get("screenshot")}

                    # Micro-cooldown pause every 10 messages
                    if count % MICRO_COOLDOWN_EVERY == 0 and count < effective_target:
                        logs.append(f"☕ Safety pause for {MICRO_COOLDOWN_SECONDS}s to keep Facebook account safe...")
                        time.sleep(MICRO_COOLDOWN_SECONDS)
                    else:
                        # Normal human safety delay (8-14s)
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
    """
    # Extract any URL from message
    extracted_link = reel_url
    if not extracted_link and message_text:
        urls = re.findall(r'https?://[^\s]+', message_text)
        if urls:
            extracted_link = urls[0].rstrip('.,;!?')

    has_link = bool(extracted_link)

    # Only use native Facebook Share modal for Facebook-native URLs
    if has_link and extracted_link and _is_facebook_native_url(extracted_link):
        logger.info(f"Hybrid Mode: Facebook-native link detected ({extracted_link[:60]}). Using Native Messenger Share modal.")
        return send_facebook_reels_or_post_to_friends(
            post_url=extracted_link,
            message_text=message_text,
            campaign_id=campaign_id,
            share_all=share_all,
            target_count=target_count,
            on_progress=on_progress,
            stop_event=stop_event
        )
    else:
        # For non-Facebook URLs (Instagram, YouTube, etc.) or pure text:
        # Send the full message (including any link) via direct 1-on-1 Messenger chats
        full_message = message_text or ""
        if not full_message and extracted_link:
            full_message = extracted_link
        elif extracted_link and extracted_link not in (full_message or ""):
            full_message = f"{full_message}\n{extracted_link}" if full_message else extracted_link

        mode_desc = "non-Facebook URL" if has_link else "pure text"
        logger.info(f"Hybrid Mode: {mode_desc} detected. Using 1-on-1 Messenger Inbox Chats for direct delivery.")
        return send_facebook_direct_text_messages(
            message_text=full_message or "Hello! Wishing you a wonderful day.",
            target_count=target_count,
            on_progress=on_progress,
            stop_event=stop_event
        )

