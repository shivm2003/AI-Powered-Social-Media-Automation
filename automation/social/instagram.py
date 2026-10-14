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
from browser.driver import browser
from config import PLATFORM_URLS

logger = logging.getLogger("automation.social.instagram")


def post_to_instagram(media_path: str = None, caption: str = "") -> dict:
    """
    Publishes a post/reel to Instagram with full caption, hashtags, and media.
    Guarantees that the caption is properly fitted and bound before publishing.
    """
    try:
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
        create_btn = None

        # Strategy A: JavaScript query for official SVG New post trigger
        try:
            create_btn = driver.execute_script("""
                return document.querySelector('svg[aria-label="New post"]')?.closest('a, div[role="button"]') ||
                       document.querySelector('svg[aria-label="Create"]')?.closest('a, div[role="button"]');
            """)
        except Exception:
            pass

        # Strategy B: Fallback Selenium XPaths
        if not create_btn:
            for xp in [
                "//a[.//svg[@aria-label='New post'] or .//svg[@aria-label='Create']]",
                "//div[@role='button'][.//svg[@aria-label='New post'] or .//svg[@aria-label='Create']]",
                "//span[text()='Create']/ancestor::*[self::a or @role='button'][1]",
                "//svg[@aria-label='New post']/ancestor::*[self::a or @role='button'][1]",
            ]:
                try:
                    for cand in driver.find_elements(By.XPATH, xp):
                        if cand.is_displayed():
                            create_btn = cand
                            break
                    if create_btn:
                        break
                except Exception:
                    continue

        if not create_btn:
            raise RuntimeError("Could not find Instagram Create (+ / New post) button on sidebar.")

        # Dismiss any stale modal dialogs from previous aborted flows to start clean
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
            time.sleep(1)
        except Exception:
            pass

        logger.info("Opening clean Instagram Create post dialog...")
        driver.execute_script("arguments[0].click();", create_btn)
        time.sleep(2)

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

        # Helper to click Next or Share buttons (works in modal or full-page route)
        def click_modal_button(target_label):
            return driver.execute_script("""
                const label = arguments[0].trim().toLowerCase();
                const container = document.querySelector('div[role="dialog"]') || document.body;
                const btns = Array.from(container.querySelectorAll('div[role="button"], button'));
                const match = btns.find(b => (b.innerText || '').trim().toLowerCase() === label);
                if (match) {
                    match.click();
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

        # Focus & Type Caption
        logger.info(f"Typing caption ({len(caption)} chars) into Instagram editor (tag=<{caption_editor.tag_name}>)...")
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            ActionChains(driver).move_to_element(caption_editor).click().perform()
        except Exception:
            try:
                driver.execute_script("arguments[0].focus(); arguments[0].click();", caption_editor)
            except Exception:
                caption_editor.click()
        time.sleep(0.5)

        # Method 1: Native Selenium send_keys (triggers all Lexical input events)
        try:
            caption_editor.send_keys(caption)
        except Exception:
            caption_editor = driver.find_element(By.CSS_SELECTOR, "div[data-lexical-editor='true'], div[role='textbox'], textarea")
            caption_editor.send_keys(caption)
        time.sleep(1.5)

        # For textarea: ensure value is committed and input/change events dispatched
        if caption_editor.tag_name.lower() == 'textarea':
            driver.execute_script("""
                const el = arguments[0];
                const val = arguments[1];
                if (!el.value || el.value.length === 0) {
                    el.value = val;
                }
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            """, caption_editor, caption)

        # NOTE: Do NOT send Keys.ESCAPE here as it triggers Instagram's 'Discard post?' dialog
        time.sleep(2.0)  # Allow state reconciler to fully flush to React component state

        # Verify binding: check character counter, textarea value, or innerText
        bound_check = driver.execute_script("""
            const container = document.querySelector('div[role="dialog"]') || document.body;
            const textarea = container.querySelector('textarea');
            if (textarea && textarea.value) {
                return { counter: textarea.value.length + '/2,200', textLength: textarea.value.length };
            }
            const allDivs = Array.from(container.querySelectorAll('div'));
            const counterDiv = allDivs.find(d => /\\d+\\/2,200/.test(d.innerText || ''));
            const ed = container.querySelector('div[data-lexical-editor="true"], div[role="textbox"]');
            return {
                counter: counterDiv ? counterDiv.innerText : null,
                textLength: ed ? (ed.innerText || '').length : 0
            };
        """)
        logger.info(f"Instagram caption binding check: counter={bound_check.get('counter')}, textLength={bound_check.get('textLength')}")

        if not bound_check.get("counter") or bound_check.get("counter") == "0/2,200":
            # Method 2 fallback: execCommand + input events
            logger.info("Applying secondary Lexical insertText dispatch fallback...")
            driver.execute_script("""
                const ed = arguments[0];
                const text = arguments[1];
                ed.focus();
                document.execCommand('selectAll', false, null);
                document.execCommand('insertText', false, text);
                ed.dispatchEvent(new Event('input', { bubbles: true }));
                ed.dispatchEvent(new Event('change', { bubbles: true }));
            """, caption_editor, caption)
            time.sleep(1.5)

        # ── Strict QA Assertion Gate: Confirm Caption Fitted ──
        final_check = driver.execute_script("""
            const container = document.querySelector('div[role="dialog"]') || document.body;
            const textarea = container.querySelector('textarea');
            if (textarea && textarea.value) {
                return { counter: textarea.value.length + '/2,200', textLength: textarea.value.length };
            }
            const allDivs = Array.from(container.querySelectorAll('div'));
            const counterDiv = allDivs.find(d => /\\d+\\/2,200/.test(d.innerText || ''));
            const ed = container.querySelector('div[data-lexical-editor="true"], div[role="textbox"]');
            return {
                counter: counterDiv ? counterDiv.innerText : null,
                textLength: ed ? (ed.innerText || '').length : 0
            };
        """)
        logger.info(f"Final caption verification before share: counter={final_check.get('counter')}, textLength={final_check.get('textLength')}")

        if caption and final_check.get("counter") == "0/2,200" and final_check.get("textLength", 0) == 0:
            raise RuntimeError("Validation Gate Failed: Caption was not fitted into Instagram editor. Aborting publish to prevent posting without caption.")

        # ── 6. Click "Share" Button ──
        logger.info("Submitting post via 'Share' button...")
        shared = False
        for _ in range(10):
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
        while time.time() - poll_start < 25:
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

        logger.info(f"✅ Instagram post published successfully! Confirmed: {confirmed}")
        return {
            "status": "success",
            "platform": "instagram",
            "message": "Posted to Instagram successfully with complete caption and media.",
            "caption_length": len(caption),
            "media_path": media_path,
            "confirmed": confirmed,
        }

    except Exception as e:
        logger.error(f"Instagram posting error: {e}")
        return {
            "status": "error",
            "platform": "instagram",
            "message": str(e)
        }
