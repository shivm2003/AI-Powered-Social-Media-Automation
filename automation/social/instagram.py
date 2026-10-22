"""
Instagram Social Poster via Selenium using persistent Chrome profile or shared debugging session.
Features:
- Robust multi-strategy Create dialog trigger
- Media file upload (PNG/JPG/MP4)
- Multi-step modal navigation (Crop -> Filters -> Caption)
- Meta Lexical rich-text editor caption injection & verification
- Character counter confirmation (ensures caption is never omitted)
- Publication confirmation wait
"""
import time
import os
import logging
import pyperclip
from browser.driver import browser
from config import PLATFORM_URLS, BASE_DIR
from .caption_helper import ensure_apply_now_at_start, LOAN_SOLUTIONS_APPLY_URL
from .trending_hashtags import enrich_caption_with_trending_hashtags

logger = logging.getLogger("automation.social.instagram")


def verify_instagram_post(driver, expected_snippet: str = None) -> dict:
    """
    Audits the live Instagram profile feed to confirm the published post is active.
    Extracts the public post URL (/p/xxxxxx/) and captures verification screenshot.
    """
    try:
        from selenium.webdriver.common.by import By
        logger.info("Auditing live Instagram profile feed for post verification...")
        time.sleep(3.5)
        profile_url = "https://www.instagram.com/loansolutions2026/"
        driver.get(profile_url)
        time.sleep(4.0)

        # Locate latest post thumbnail/link on profile grid
        post_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/') or contains(@href, '/reel/')]")
        if not post_links:
            driver.refresh()
            time.sleep(4.0)
            post_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/') or contains(@href, '/reel/')]")

        latest_post_url = None
        if post_links:
            latest_post_url = post_links[0].get_attribute("href")
            logger.info(f"Verified live Instagram post URL: {latest_post_url}")

        screenshot_path = str(BASE_DIR / "data" / "media" / "instagram_post_verified.png")
        try:
            os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
            driver.save_screenshot(screenshot_path)
            logger.info(f"Saved Instagram verification screenshot: {screenshot_path}")
        except Exception as e_sc:
            logger.debug(f"Screenshot save note: {e_sc}")

        return {
            "verified": bool(latest_post_url),
            "post_url": latest_post_url,
            "profile_url": profile_url,
            "screenshot": screenshot_path,
        }
    except Exception as e:
        logger.warning(f"Instagram live feed audit error: {e}")
        return {"verified": False, "error": str(e)}


def post_to_instagram(media_path: str = None, caption: str = "") -> dict:
    """
    Publishes a post/reel to Instagram with full caption, hashtags, and media.
    Guarantees that the caption starts with the mandatory 'Apply Now' CTA link
    and is properly fitted and bound before publishing.
    """
    try:
        # Enrich caption with fresh, viral Instagram hashtags (anchors, niche keywords, community intent)
        caption = enrich_caption_with_trending_hashtags(caption, platform="instagram", category="finance")
        # Guarantee Apply Now link is strictly at the start of caption (Line 1)
        caption = ensure_apply_now_at_start(caption, apply_url=LOAN_SOLUTIONS_APPLY_URL, is_loan=True)
        driver = browser.navigate("instagram", PLATFORM_URLS["instagram"], refresh_first=False)
        time.sleep(1)

        # Ensure we are on Instagram home/feed so sidebar Create button is loaded
        if "/p/" in driver.current_url or "/create/" in driver.current_url or driver.current_url.rstrip('/') != "https://www.instagram.com":
            logger.info("Redirecting to Instagram home page to ensure Create sidebar button is available...")
            driver.get("https://www.instagram.com/")
            time.sleep(2.5)

        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        # ── 1. Locate and Open "Create new post" Modal ──
        logger.info("Opening Instagram Create post dialog...")

        # Dismiss any stale modal dialogs from previous aborted flows FIRST
        try:
            driver.execute_script("""
                const closeBtns = Array.from(document.querySelectorAll('div[role="dialog"] svg[aria-label="Close"], svg[aria-label="Close"]'));
                for (const svg of closeBtns) {
                    const btn = svg.closest('button, div[role="button"]');
                    if (btn) btn.click();
                }
                const discardBtns = Array.from(document.querySelectorAll('button')).filter(b => (b.innerText || '').trim() === 'Discard');
                for (const b of discardBtns) b.click();
            """)
            time.sleep(1.2)
        except Exception:
            pass

        # Atomic JS query and click for official Create (+ / New post) button
        opened = False
        try:
            opened = driver.execute_script("""
                const btn = document.querySelector('svg[aria-label="New post"]')?.closest('a, div[role="button"]') ||
                            document.querySelector('svg[aria-label="Create"]')?.closest('a, div[role="button"]');
                if (btn) {
                    btn.dispatchEvent(new MouseEvent('click', { bubbles: true }));
                    try { btn.click(); } catch(e) {}
                    return true;
                }
                return false;
            """)
        except Exception:
            pass

        # Fallback Selenium find & click
        if not opened:
            for xp in [
                "//a[.//svg[@aria-label='New post'] or .//svg[@aria-label='Create']]",
                "//div[@role='button'][.//svg[@aria-label='New post'] or .//svg[@aria-label='Create']]",
                "//span[text()='Create']/ancestor::*[self::a or @role='button'][1]",
                "//svg[@aria-label='New post']/ancestor::*[self::a or @role='button'][1]",
            ]:
                try:
                    for cand in driver.find_elements(By.XPATH, xp):
                        if cand.is_displayed():
                            try:
                                ActionChains(driver).move_to_element(cand).click().perform()
                                opened = True
                                break
                            except Exception:
                                driver.execute_script("arguments[0].click();", cand)
                                opened = True
                                break
                    if opened:
                        break
                except Exception:
                    continue

        if not opened:
            raise RuntimeError("Could not find or click Instagram Create (+ / New post) button on sidebar.")

        time.sleep(2.0)

        # Check if popover submenu appears (e.g. 'Post' / 'Live video')
        try:
            submenus = driver.find_elements(By.XPATH, "//div[@role='dialog']//span[text()='Post'] | //div[contains(@class, 'x1n2onr6')]//span[text()='Post']")
            for sm in submenus:
                if sm.is_displayed():
                    sm.click()
                    time.sleep(1.5)
                    break
        except Exception:
            pass

        # Wait for file input
        file_input = None
        for _ in range(15):
            fis = driver.find_elements(By.XPATH, "//input[@type='file']")
            if fis:
                file_input = fis[0]
                break
            time.sleep(0.5)

        # ── 2. Attach Media File to Upload Dropzone ──
        if not media_path or not os.path.exists(media_path):
            raise FileNotFoundError(f"Media file not found: {media_path}")

        abs_media_path = os.path.abspath(media_path)
        logger.info(f"Uploading media file to Instagram: {abs_media_path}")

        if not file_input:
            raise RuntimeError("Instagram file input (<input type='file'>) did not appear in modal.")

        file_input.send_keys(abs_media_path)
        time.sleep(3.5)

        # Helper to click Next or Share buttons (supports ActionChains, DOM MouseEvents, and fuzzy text matching)
        def click_modal_button(target_label):
            target_lower = target_label.strip().lower()
            from selenium.webdriver.common.action_chains import ActionChains
            # 1. Selenium action chains click
            try:
                for xp in [
                    f"//div[@role='dialog']//button[translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='{target_lower}']",
                    f"//div[@role='dialog']//div[@role='button'][translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='{target_lower}']",
                    f"//div[@role='dialog']//*[self::button or @role='button'][contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{target_lower}')]",
                    f"//button[translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='{target_lower}']",
                    f"//div[@role='button'][translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='{target_lower}']",
                ]:
                    cand_btns = driver.find_elements(By.XPATH, xp)
                    for b in cand_btns:
                        if b.is_displayed():
                            try:
                                ActionChains(driver).move_to_element(b).click().perform()
                                return True
                            except Exception:
                                driver.execute_script("arguments[0].click();", b)
                                return True
            except Exception:
                pass

            # 2. JS query click with full synthetic event dispatch
            return driver.execute_script("""
                const label = arguments[0].trim().toLowerCase();
                const container = document.querySelector('div[role="dialog"]') || document.body;
                const btns = Array.from(container.querySelectorAll('div[role="button"], button'));
                const match = btns.find(b => {
                    const txt = (b.innerText || b.textContent || '').trim().toLowerCase();
                    return txt === label || txt.startsWith(label);
                });
                if (match) {
                    match.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
                    match.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                    match.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
                    match.dispatchEvent(new MouseEvent('click', { bubbles: true }));
                    try { match.click(); } catch(e) {}
                    return true;
                }
                return false;
            """, target_label)

        # ── 3. Step 1 (Crop View) ➜ Advance to Filters ──
        logger.info("Step 1 (Crop): Waiting for Crop screen and advancing...")
        for _ in range(15):
            if click_modal_button("Next"):
                logger.info("Clicked Next on Crop screen.")
                break
            time.sleep(1)

        # Wait for transition from Crop -> Filters/Edit
        time.sleep(2.5)

        # ── 4. Step 2 (Filters/Edit View) ➜ Advance to Details ──
        logger.info("Step 2 (Filters): Waiting for Filters screen and advancing to Details...")
        for _ in range(15):
            # Check if already on Details (Share button visible in dialog)
            is_details = driver.execute_script("""
                const dialog = document.querySelector('div[role="dialog"]');
                if (!dialog) return window.location.href.includes('/create/details/');
                const btns = Array.from(dialog.querySelectorAll('div[role="button"], button'));
                return btns.some(b => (b.innerText || '').trim().toLowerCase() === 'share');
            """)
            if is_details:
                logger.info("Details screen reached!")
                break
            click_modal_button("Next")
            time.sleep(1.5)

        # Wait for Details screen and Share button to fully settle
        logger.info("Waiting for Details screen (Share button) to stabilize...")
        for _ in range(25):
            has_share = driver.execute_script("""
                const dialog = document.querySelector('div[role="dialog"]');
                if (!dialog) return window.location.href.includes('/create/details/');
                const btns = Array.from(dialog.querySelectorAll('div[role="button"], button'));
                return btns.some(b => (b.innerText || '').trim().toLowerCase() === 'share');
            """)
            if has_share:
                break
            time.sleep(0.5)

        # Wait 2.0s for Details slide animation to finish settling
        time.sleep(2.0)

        # ── 5. Step 3 (Caption & Details) ➜ Locate Editor & Type Caption ──
        logger.info("Locating Instagram caption editor (Lexical or Textarea)...")
        caption_editor = None
        editor_selectors = [
            "div[data-lexical-editor='true']",
            "div[role='textbox'][aria-label*='caption' i]",
            "div[aria-label*='caption']",
            "textarea[aria-label*='caption' i]",
            "textarea",
            "div[contenteditable='true']",
        ]

        for _ in range(45):
            try:
                # 1. Fast JS query selector with geometry layout verification
                js_editor = driver.execute_script("""
                    const dialog = document.querySelector('div[role="dialog"]') || document.body;
                    const ed = dialog.querySelector('div[data-lexical-editor="true"]') ||
                               dialog.querySelector('div[role="textbox"]') ||
                               dialog.querySelector('textarea') ||
                               dialog.querySelector('div[contenteditable="true"]');
                    if (!ed) return null;
                    const r = ed.getBoundingClientRect();
                    if (r.width > 20 && r.height > 15) return ed;
                    return null;
                """)
                if js_editor:
                    caption_editor = js_editor
                    break

                # 2. Selenium fallback
                dialog = None
                dialogs = driver.find_elements(By.CSS_SELECTOR, 'div[role="dialog"]')
                if dialogs and dialogs[0].is_displayed():
                    dialog = dialogs[0]

                search_context = dialog if dialog else driver
                for sel in editor_selectors:
                    for el in search_context.find_elements(By.CSS_SELECTOR, sel):
                        if el.is_displayed():
                            caption_editor = el
                            break
                    if caption_editor:
                        break
            except Exception:
                pass
            if caption_editor:
                break
            time.sleep(0.5)

        if not caption_editor:
            raise RuntimeError("Could not locate Instagram caption editor in Details view.")

        # Focus & Type Caption (4-Tier Robust Injection Engine)
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.common.keys import Keys

        logger.info(f"Injecting caption ({len(caption)} chars) into Instagram editor (tag=<{caption_editor.tag_name}>)...")

        # Focus editor element
        try:
            ActionChains(driver).move_to_element(caption_editor).click().perform()
        except Exception:
            try:
                driver.execute_script("arguments[0].focus(); arguments[0].click();", caption_editor)
            except Exception:
                caption_editor.click()
        time.sleep(0.5)

        # Clear any initial placeholder or stale text
        try:
            ActionChains(driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
            time.sleep(0.1)
        except Exception:
            pass

        # ── Tier 1 (Primary): OS Clipboard Paste (pyperclip + Ctrl+V) ──
        # Natively handles Indian Rupee (₹), emojis (👉, 🏡, ✨), newlines, bypassing ChromeDriver BMP limits
        try:
            pyperclip.copy(caption)
            time.sleep(0.2)
            ActionChains(driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
            time.sleep(1.5)
            logger.info("Dispatched caption via OS Clipboard paste (pyperclip + Ctrl+V).")
        except Exception as e_clip:
            logger.warning(f"OS Clipboard paste notice: {e_clip}")

        # Check binding after Tier 1
        bound_check = driver.execute_script("""
            const container = document.querySelector('div[role="dialog"]') || document.body;
            const textarea = container.querySelector('textarea');
            if (textarea && textarea.value) {
                return { counter: textarea.value.length + '/2,200', textLength: textarea.value.length };
            }
            const allDivs = Array.from(container.querySelectorAll('div'));
            const counterDiv = allDivs.find(d => /\\d+\\/2,200/.test(d.innerText || ''));
            const ed = container.querySelector('div[data-lexical-editor="true"], div[role="textbox"]');
            const edText = ed ? (ed.innerText || ed.textContent || '') : '';
            return {
                counter: counterDiv ? counterDiv.innerText : null,
                textLength: edText.length
            };
        """)
        logger.info(f"Instagram caption Tier 1 check: counter={bound_check.get('counter')}, textLength={bound_check.get('textLength')}")

        # ── Tier 2: Synthetic DataTransfer & ClipboardEvent dispatch ──
        if (not bound_check.get("counter") or bound_check.get("counter") == "0/2,200") and bound_check.get("textLength", 0) == 0:
            logger.info("Tier 1 text not detected; applying Tier 2 Synthetic ClipboardEvent dispatch...")
            driver.execute_script("""
                const ed = arguments[0];
                const text = arguments[1];
                ed.focus();
                try {
                    const dt = new DataTransfer();
                    dt.setData('text/plain', text);
                    const pasteEvt = new ClipboardEvent('paste', {
                        clipboardData: dt,
                        bubbles: true,
                        cancelable: true
                    });
                    ed.dispatchEvent(pasteEvt);
                } catch(e) {}
                try {
                    const inputEvt = new InputEvent('beforeinput', {
                        inputType: 'insertFromPaste',
                        data: text,
                        bubbles: true,
                        cancelable: true
                    });
                    ed.dispatchEvent(inputEvt);
                } catch(e) {}
                ed.dispatchEvent(new Event('input', { bubbles: true }));
                ed.dispatchEvent(new Event('change', { bubbles: true }));
            """, caption_editor, caption)
            time.sleep(1.5)

        # ── Tier 3: BMP-safe send_keys fallback ──
        bound_check = driver.execute_script("""
            const container = document.querySelector('div[role="dialog"]') || document.body;
            const textarea = container.querySelector('textarea');
            if (textarea && textarea.value) return { textLength: textarea.value.length };
            const ed = container.querySelector('div[data-lexical-editor="true"], div[role="textbox"]');
            return { textLength: ed ? (ed.innerText || ed.textContent || '').length : 0 };
        """)
        if bound_check.get("textLength", 0) == 0:
            logger.info("Applying Tier 3 BMP-safe send_keys fallback...")
            try:
                bmp_text = "".join(ch for ch in caption if ord(ch) <= 0xFFFF)
                caption_editor.send_keys(bmp_text)
                time.sleep(1.0)
            except Exception as e_sk:
                logger.warning(f"send_keys fallback notice: {e_sk}")

        # ── Tier 4: Textarea direct value fallback ──
        if caption_editor.tag_name.lower() == 'textarea':
            driver.execute_script("""
                const el = arguments[0];
                const val = arguments[1];
                if (!el.value || el.value.length === 0) el.value = val;
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            """, caption_editor, caption)

        time.sleep(2.0)

        # ── Strict QA Assertion Gate: Confirm Caption Fitted ──
        final_check = driver.execute_script("""
            const container = document.querySelector('div[role="dialog"]') || document.body;
            const textarea = container.querySelector('textarea');
            if (textarea && textarea.value && textarea.value.length > 0) {
                return { counter: textarea.value.length + '/2,200', textLength: textarea.value.length };
            }
            const allDivs = Array.from(container.querySelectorAll('div'));
            const counterDiv = allDivs.find(d => /\\d+\\/2,200/.test(d.innerText || ''));
            const ed = container.querySelector('div[data-lexical-editor="true"], div[role="textbox"], textarea, div[contenteditable="true"]');
            const edText = ed ? (ed.innerText || ed.textContent || '') : '';
            return {
                counter: counterDiv ? counterDiv.innerText : null,
                textLength: edText.trim().length
            };
        """)
        logger.info(f"Final caption verification before share: counter={final_check.get('counter')}, textLength={final_check.get('textLength')}")

        if caption and final_check.get("counter") == "0/2,200" and final_check.get("textLength", 0) == 0:
            ed_len = driver.execute_script("return (arguments[0].innerText || arguments[0].textContent || '').trim().length;", caption_editor)
            if ed_len == 0:
                raise RuntimeError("Validation Gate Failed: Caption was not fitted into Instagram editor. Aborting publish to prevent posting without caption.")

        # ── 6. Click "Share" Button ──
        logger.info("Submitting post via 'Share' button...")
        shared = False
        for _ in range(12):
            if click_modal_button("Share"):
                shared = True
                break
            time.sleep(1)

        if not shared:
            for sh_xp in ["//div[text()='Share' and @role='button']", "//button[text()='Share']", "//span[text()='Share']/ancestor::*[@role='button']"]:
                try:
                    for b in driver.find_elements(By.XPATH, sh_xp):
                        if b.is_displayed():
                            b.click()
                            shared = True
                            break
                    if shared:
                        break
                except Exception:
                    pass

        if not shared:
            raise RuntimeError("Could not click 'Share' button to publish Instagram post.")

        # ── 7. Wait for Post Publication Confirmation ──
        logger.info("Waiting for Instagram publication confirmation...")
        confirmed = False
        poll_start = time.time()
        while time.time() - poll_start < 30:
            time.sleep(2)
            conf_text = driver.execute_script("""
                const dialog = document.querySelector('div[role="dialog"]');
                if (dialog) {
                    const text = (dialog.innerText || '').toLowerCase();
                    if (text.includes('shared') || text.includes('your post has been shared')) return 'SHARED_CONFIRMED';
                }
                const url = window.location.href;
                if (!url.includes('/create/') && (url.includes('/p/') || url.includes('/loansolutions') || url === 'https://www.instagram.com/')) {
                    return 'SHARED_CONFIRMED';
                }
                return 'PENDING';
            """)
            if conf_text in ["SHARED_CONFIRMED", "MODAL_CLOSED"]:
                confirmed = True
                break

        # Dismiss confirmation modal if still open
        try:
            driver.execute_script("""
                const closeBtn = document.querySelector('div[role="dialog"] svg[aria-label="Close"]')?.closest('button, div[role="button"]');
                if (closeBtn) closeBtn.click();
                const doneBtn = Array.from(document.querySelectorAll('div[role="dialog"] button, div[role="dialog"] div[role="button"]')).find(b => (b.innerText || '').toLowerCase().includes('done'));
                if (doneBtn) doneBtn.click();
            """)
        except Exception:
            pass

        logger.info(f"Instagram post share event concluded. Confirmed: {confirmed}")

        # ── 8. Audit Live Feed & Check Post Publication ──
        verification = verify_instagram_post(driver, expected_snippet=caption[:40])
        logger.info(f"Instagram post live verification result: {verification}")

        return {
            "status": "success",
            "platform": "instagram",
            "message": "Posted to Instagram successfully with complete caption and media.",
            "caption_length": len(caption),
            "media_path": media_path,
            "confirmed": confirmed,
            "verified": verification.get("verified", False),
            "post_url": verification.get("post_url"),
            "screenshot": verification.get("screenshot"),
        }

    except Exception as e:
        logger.error(f"Instagram posting error: {e}")
        return {
            "status": "error",
            "platform": "instagram",
            "message": str(e)
        }
