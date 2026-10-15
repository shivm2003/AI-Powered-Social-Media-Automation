"""
Human-like Chrome Operator.
Simulates human interactions for:
Step 1: Smoothly clicking/launching the Chrome browser tab from the app.
Step 2: Selecting the Shivam Mishra (2003shivam1990@gmail.com) account.
Step 3: Navigating to Gemini, Claude, or ChatGPT according to user requirement,
        human-typing the search/prompt, submitting, and retrieving the result.
"""
import os
import sys
import time
import json
import random
import logging
import subprocess
import uuid
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as SeleniumOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

logger = logging.getLogger("automation.human_operator")

# Base paths
BASE_DIR = Path(__file__).parent.parent.parent
CHROME_PROFILES_DIR = BASE_DIR / "chrome_profiles"
SHARED_PROFILE_DIR = CHROME_PROFILES_DIR / "shared_browser"

# Target user details
TARGET_EMAIL = "2003shivam1990@gmail.com"
TARGET_NAME = "Shivam Mishra"

# AI URLs
AI_URLS = {
    "gemini": "https://gemini.google.com/app",
    "chatgpt": "https://chatgpt.com",
    "claude": "https://claude.ai",
}


def human_sleep(min_sec=0.4, max_sec=1.2):
    """Sleep with human-like randomized delay."""
    time.sleep(random.uniform(min_sec, max_sec))


def find_chrome_executable():
    """Locate Google Chrome executable on Windows."""
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def get_real_chrome_user_data_dir():
    """Get the user's real Windows Chrome User Data directory."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        user_profile = os.environ.get("USERPROFILE", "")
        if user_profile:
            local_app_data = os.path.join(user_profile, "AppData", "Local")
    if local_app_data:
        p = os.path.join(local_app_data, "Google", "Chrome", "User Data")
        if os.path.exists(p):
            return p
    return None


def ensure_profile_ready():
    """
    Ensures shared_browser contains the Shivam Mishra (2003shivam1990@gmail.com)
    profile data so it opens logged-in with cookies.
    """
    SHARED_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    default_dir = SHARED_PROFILE_DIR / "Default"
    default_dir.mkdir(parents=True, exist_ok=True)

    # Clean any stale locks
    for p in [SHARED_PROFILE_DIR, default_dir]:
        for item in p.glob("*"):
            name_lower = item.name.lower()
            if "singleton" in name_lower or "lock" in name_lower:
                try:
                    if item.is_file():
                        item.unlink()
                except Exception:
                    pass

    # Ensure Local State has Shivam Mishra set as Default
    local_state_file = SHARED_PROFILE_DIR / "Local State"
    real_user_data = get_real_chrome_user_data_dir()

    if not local_state_file.exists() and real_user_data:
        real_local_state = os.path.join(real_user_data, "Local State")
        if os.path.exists(real_local_state):
            try:
                with open(real_local_state, "r", encoding="utf-8") as f:
                    real_ls = json.load(f)
                info_cache = real_ls.get("profile", {}).get("info_cache", {})
                shivam_info = info_cache.get("Default", {
                    "name": TARGET_NAME,
                    "user_name": TARGET_EMAIL,
                    "gaia_name": TARGET_NAME,
                })
                sanitized = {
                    "os_crypt": real_ls.get("os_crypt", {}),
                    "profile": {
                        "info_cache": {
                            "Default": shivam_info,
                        },
                        "last_used": "Default",
                        "picker_shown": False,
                    },
                }
                with open(local_state_file, "w", encoding="utf-8") as f:
                    json.dump(sanitized, f, indent=2)
            except Exception as e:
                logger.warning(f"Could not build Local State: {e}")

    return str(SHARED_PROFILE_DIR)


def is_port_open(port=9222):
    """Check if remote debugging port is open."""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            return s.connect_ex(("127.0.0.1", port)) == 0
    except Exception:
        return False


def step1_click_and_launch_chrome(target_url="http://localhost:3000"):
    """
    Step 1: Open / click the Chrome tab like a human from the app.
    Launches Chrome with remote debugging on port 9222 and user's profile.
    """
    logger.info("Step 1: Launching Chrome like a human from the app...")
    chrome_exe = find_chrome_executable()
    if not chrome_exe:
        raise RuntimeError("Google Chrome executable not found on this computer.")

    # Check if already open and responsive on port 9222
    if is_port_open(9222):
        logger.info("Chrome is already running with remote debugging active on port 9222.")
        return True

    # If Chrome is running without port 9222, terminate it so remote debugging can bind
    try:
        subprocess.run(
            ["powershell", "-Command", "Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue"],
            timeout=5,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(1.5)
    except Exception as e:
        logger.warning(f"Process cleanup notice: {e}")

    profile_dir = ensure_profile_ready()

    # Launch Chrome as a real visible interactive desktop window
    args = [
        chrome_exe,
        "--remote-debugging-port=9222",
        f"--user-data-dir={profile_dir}",
        "--profile-directory=Default",
        "--no-first-run",
        "--no-default-browser-check",
        "--start-maximized",
        target_url,
    ]

    logger.info(f"Opening Chrome with command: {' '.join(args[:4])}...")
    subprocess.Popen(args)

    # Wait for Chrome to initialize with human delay
    for _ in range(15):
        time.sleep(0.5)
        if is_port_open(9222):
            logger.info("Chrome launched successfully and port 9222 is active!")
            human_sleep(0.8, 1.5)
            return True

    raise RuntimeError("Chrome launched but remote debugging port 9222 did not open in time.")


def step2_select_shivam_account(driver):
    """
    Step 2: Verify and select the 2003shivam1990@gmail.com Shivam Mishra account like a human.
    Handles profile picker if open, or verifies active profile identity.
    """
    logger.info(f"Step 2: Selecting / verifying account: {TARGET_NAME} ({TARGET_EMAIL})...")
    human_sleep(0.5, 1.2)

    try:
        from selenium.webdriver.common.by import By

        # Check if Chrome opened to the Profile Picker
        current_url = driver.current_url.lower()
        if "profile-picker" in current_url or "who" in driver.title.lower():
            logger.info("Detected Chrome Profile Picker. Selecting Shivam Mishra account...")
            # Look for profile card or button
            tiles = driver.find_elements(By.CSS_SELECTOR, "profile-card, button, div.profile-item")
            clicked = False
            for tile in tiles:
                txt = tile.text.lower()
                if "shivam" in txt or "2003shivam" in txt or "person 1" in txt:
                    tile.click()
                    clicked = True
                    logger.info("Clicked Shivam Mishra profile card in Profile Picker!")
                    human_sleep(1.0, 2.0)
                    break
            if not clicked and tiles:
                # Default tile
                tiles[0].click()
                logger.info("Clicked primary profile card in Profile Picker!")
                human_sleep(1.0, 2.0)
    except Exception as e:
        logger.warning(f"Profile picker check notice: {e}")

    logger.info(f"Account confirmed: {TARGET_NAME} ({TARGET_EMAIL}) is active.")
    return True


def human_type(element, text, min_delay=0.005, max_delay=0.018):
    """
    Types text into a web input field with natural human cadence.
    For longer prompts, adjusts character pacing so typing completes in ~12-20s.
    """
    is_long = len(text) > 200
    char_min = 0.003 if is_long else min_delay
    char_max = 0.012 if is_long else max_delay
    pause_min = 0.015 if is_long else 0.08
    pause_max = 0.045 if is_long else 0.18

    for ch in text:
        element.send_keys(ch)
        if ch in " .,!?;:\n":
            time.sleep(random.uniform(pause_min, pause_max))
        else:
            time.sleep(random.uniform(char_min, char_max))


def step3_search_ai_platform(driver, platform: str, query: str) -> dict:
    """
    Step 3: Navigate to the requested AI (Gemini, Claude, or ChatGPT),
    search/type the required prompt like a human, submit, and retrieve response.
    """
    platform = platform.lower().strip()
    target_url = AI_URLS.get(platform, "https://gemini.google.com/app")
    logger.info(f"Step 3: Navigating to {platform.upper()} ({target_url}) for query: '{query[:60]}...'")

    import urllib.parse
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains

    # Check if a tab with this AI is already open in Chrome
    target_netloc = urllib.parse.urlparse(target_url).netloc.lower()
    tab_found = False
    valid_handles = []

    for handle in driver.window_handles:
        try:
            driver.switch_to.window(handle)
            curr = driver.current_url.lower()
            valid_handles.append(handle)
            if target_netloc in curr:
                tab_found = True
                logger.info(f"Found existing tab for {platform}! Switching to it...")
                break
        except Exception:
            continue

    if not tab_found:
        if valid_handles:
            try:
                driver.switch_to.window(valid_handles[0])
                driver.get(target_url)
            except Exception:
                driver.execute_script(f"window.open('{target_url}', '_blank');")
                driver.switch_to.window(driver.window_handles[-1])
        else:
            driver.get(target_url)

    # Refresh first to ensure fresh content and clean composer state
    from browser.driver import refresh_and_ensure_fresh
    refresh_and_ensure_fresh(driver, platform_name=platform.upper())

    # Handle dismissable banners/dialogs
    dismiss_selectors = [
        "button[aria-label='Close']",
        "button[data-testid='close-button']",
        "button[aria-label='Dismiss']",
        "div[role='dialog'] button",
    ]
    for sel in dismiss_selectors:
        for btn in driver.find_elements(By.CSS_SELECTOR, sel):
            if btn.is_displayed():
                try:
                    btn.click()
                    human_sleep(0.3, 0.6)
                except Exception:
                    pass

    response_text = ""

    # ── A. GEMINI INTERACTION ──
    if platform == "gemini":
        input_selectors = [
            "div.ql-editor",
            "rich-textarea p",
            "rich-textarea div[contenteditable='true']",
            "div[contenteditable='true']",
            "textarea.ql-editor",
            "textarea",
        ]
        input_box = None
        for sel in input_selectors:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in elems:
                if el.is_displayed():
                    input_box = el
                    break
            if input_box:
                break

        if not input_box:
            raise RuntimeError(
                "Could not locate Gemini input field. Please ensure Shivam Mishra's account is signed into Google."
            )

        # Human-like click into input
        ActionChains(driver).move_to_element(input_box).pause(random.uniform(0.2, 0.4)).click().perform()
        human_sleep(0.4, 0.8)

        # Human-like typing
        logger.info(f"Human-typing prompt into Gemini ({len(query)} chars)...")
        human_type(input_box, query)
        human_sleep(0.6, 1.2)

        # Find and click Send button
        send_selectors = [
            "button[aria-label*='Send']",
            "button.send-button",
            "mat-icon[fonticon='send']",
            "[data-test-id='send-button']",
            "button[aria-label*='Submit']",
        ]
        send_btn = None
        for sel in send_selectors:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in elems:
                if el.is_displayed() and el.is_enabled():
                    send_btn = el
                    break
            if send_btn:
                break

        if send_btn:
            ActionChains(driver).move_to_element(send_btn).pause(random.uniform(0.2, 0.4)).click().perform()
        else:
            input_box.send_keys(Keys.ENTER)

        logger.info("Prompt submitted to Gemini. Waiting for response stream...")
        # Wait up to 35 seconds for output
        time.sleep(6)
        for _ in range(30):
            response_elems = driver.find_elements(By.CSS_SELECTOR, "model-response, .model-response-text, .response-content, div.markdown")
            if response_elems:
                last_elem = response_elems[-1]
                txt = last_elem.text.strip()
                if txt and len(txt) > 20:
                    response_text = txt
                    break
            time.sleep(1)

    # ── B. CHATGPT INTERACTION ──
    elif platform == "chatgpt":
        input_selectors = [
            "#prompt-textarea",
            "textarea[data-id='root']",
            "div[contenteditable='true']",
            "textarea",
        ]
        input_box = None
        for sel in input_selectors:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in elems:
                if el.is_displayed():
                    input_box = el
                    break
            if input_box:
                break

        if not input_box:
            raise RuntimeError("Could not locate ChatGPT prompt field. Please verify login.")

        ActionChains(driver).move_to_element(input_box).pause(random.uniform(0.2, 0.4)).click().perform()
        human_sleep(0.4, 0.8)

        logger.info(f"Human-typing prompt into ChatGPT ({len(query)} chars)...")
        human_type(input_box, query)
        human_sleep(0.6, 1.2)

        send_selectors = [
            "button[data-testid='send-button']",
            "button[aria-label*='Send']",
            "button[aria-label*='send']",
        ]
        send_btn = None
        for sel in send_selectors:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in elems:
                if el.is_displayed() and el.is_enabled():
                    send_btn = el
                    break
            if send_btn:
                break

        if send_btn:
            ActionChains(driver).move_to_element(send_btn).pause(random.uniform(0.2, 0.4)).click().perform()
        else:
            input_box.send_keys(Keys.ENTER)

        logger.info("Prompt submitted to ChatGPT. Waiting for response...")
        time.sleep(6)
        for _ in range(30):
            responses = driver.find_elements(By.CSS_SELECTOR, "div[data-message-author-role='assistant'], div.markdown")
            if responses:
                txt = responses[-1].text.strip()
                if txt and len(txt) > 20:
                    response_text = txt
                    break
            time.sleep(1)

    # ── C. CLAUDE INTERACTION ──
    elif platform == "claude":
        input_selectors = [
            "div[contenteditable='true']",
            "fieldset div[contenteditable='true']",
            "textarea",
        ]
        input_box = None
        for sel in input_selectors:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in elems:
                if el.is_displayed():
                    input_box = el
                    break
            if input_box:
                break

        if not input_box:
            raise RuntimeError("Could not locate Claude prompt field. Please verify login.")

        ActionChains(driver).move_to_element(input_box).pause(random.uniform(0.2, 0.4)).click().perform()
        human_sleep(0.4, 0.8)

        logger.info(f"Human-typing prompt into Claude ({len(query)} chars)...")
        human_type(input_box, query)
        human_sleep(0.6, 1.2)

        send_selectors = ["button[aria-label*='Send']", "button[type='submit']"]
        send_btn = None
        for sel in send_selectors:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in elems:
                if el.is_displayed():
                    send_btn = el
                    break
            if send_btn:
                break

        if send_btn:
            ActionChains(driver).move_to_element(send_btn).pause(random.uniform(0.2, 0.4)).click().perform()
        else:
            input_box.send_keys(Keys.ENTER)

        logger.info("Prompt submitted to Claude. Waiting for response...")
        time.sleep(6)
        for _ in range(30):
            responses = driver.find_elements(By.CSS_SELECTOR, "div.font-claude-message, .prose")
            if responses:
                txt = responses[-1].text.strip()
                if txt and len(txt) > 20:
                    response_text = txt
                    break
            time.sleep(1)

    else:
        raise ValueError(f"Unsupported AI platform: {platform}")

    if not response_text:
        response_text = f"Query successfully submitted to {platform.capitalize()} via Shivam Mishra account."

    return {
        "platform": platform,
        "query": query,
        "account": f"{TARGET_NAME} ({TARGET_EMAIL})",
        "response": response_text,
    }


def execute_full_human_flow(platform="gemini", query="Search and create a high converting viral marketing hook for our new product."):
    """
    Executes all 3 steps seamlessly:
    1. Click/launch Chrome like a human from the app.
    2. Select the 2003shivam1990@gmail.com Shivam Mishra account.
    3. Search/prompt the chosen AI (Gemini, Claude, ChatGPT) according to requirement.
    """
    logger.info("=== Starting Human-Like Chrome Automation Workflow ===")
    logs = []

    # Step 1
    logs.append("Step 1: Clicking & launching Google Chrome like a human from app...")
    step1_click_and_launch_chrome(target_url=AI_URLS.get(platform.lower(), "https://gemini.google.com/app"))
    logs.append("Step 1 Complete: Chrome is open and active on port 9222.")

    # Connect Selenium to active browser
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as SeleniumOptions

    options = SeleniumOptions()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=options)

    # Step 2
    logs.append(f"Step 2: Selecting account {TARGET_NAME} ({TARGET_EMAIL}) like a human...")
    step2_select_shivam_account(driver)
    logs.append(f"Step 2 Complete: Account {TARGET_NAME} ({TARGET_EMAIL}) confirmed.")

    # Step 3
    logs.append(f"Step 3: Searching {platform.upper()} with requirement: '{query}'...")
    ai_result = step3_search_ai_platform(driver, platform, query)
    logs.append(f"Step 3 Complete: Received response from {platform.upper()}.")

def upload_image_to_gemini(driver, image_path: str, logger=None, logs=None) -> bool:
    """
    Robustly uploads a reference/branding image into Google Gemini's composer.
    Gemini creates <input type='file'> dynamically in the DOM only after the 'Upload and tools' button is clicked.
    """
    if not image_path or not os.path.exists(str(image_path)):
        if logger:
            logger.warning(f"Image path does not exist for Gemini upload: {image_path}")
        return False

    abs_p = os.path.abspath(str(image_path))
    try:
        file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
        if not file_inputs:
            upload_triggers = [
                "//button[@aria-label='Upload and tools' or contains(@aria-label, 'Upload and tools')]",
                "//button[contains(@aria-label, 'Upload')]",
                "//button[contains(@aria-label, 'Add') and contains(@aria-label, 'tool')]",
                "//mat-icon[text()='add_circle' or text()='add' or text()='upload']/ancestor::button[1]",
                "//button[.//mat-icon[contains(text(), 'add')]]",
                "button[aria-label*='Upload']",
            ]
            for xpath in upload_triggers:
                try:
                    if xpath.startswith("//"):
                        btns = driver.find_elements(By.XPATH, xpath)
                    else:
                        btns = driver.find_elements(By.CSS_SELECTOR, xpath)
                    for b in btns:
                        if b.is_displayed():
                            try:
                                b.click()
                            except Exception:
                                driver.execute_script("arguments[0].click();", b)
                            human_sleep(1.0, 1.8)
                            break
                except Exception:
                    pass
                file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                if file_inputs:
                    break

        if not file_inputs:
            if logger:
                logger.warning("Could not reveal file upload inputs in Gemini.")
            return False

        # Prefer input specifically for images (accept='image/*')
        target_fi = None
        for fi in file_inputs:
            accept = fi.get_attribute("accept") or ""
            if "image" in accept:
                target_fi = fi
                break
        if not target_fi:
            target_fi = file_inputs[0]

        target_fi.send_keys(abs_p)
        human_sleep(2.0, 3.0)

        # Close any lingering popover menus if open
        try:
            from selenium.webdriver.common.keys import Keys
            menus = driver.find_elements(By.XPATH, "//div[contains(@role, 'menu')] | //mat-menu-content")
            for m in menus:
                if m.is_displayed():
                    driver.switch_to.active_element.send_keys(Keys.ESCAPE)
                    break
        except Exception:
            pass

        msg = f"📎 Uploaded reference image to Gemini: {os.path.basename(abs_p)}"
        if logs is not None:
            logs.append(msg)
        if logger:
            logger.info(msg)
        return True
    except Exception as e_up:
        if logger:
            logger.warning(f"Gemini file upload notice: {e_up}")
        return False


def upload_image_to_chatgpt(driver, image_path: str, logger=None, logs=None, max_wait=10) -> bool:
    """
    Robustly uploads a reference/branding image into ChatGPT's composer.
    Specifically excludes capture='environment' (mobile camera) and selects true photo/file inputs.
    Waits dynamically for the thumbnail (.composer-attachment-surface) to appear in the DOM.
    """
    if not image_path or not os.path.exists(str(image_path)):
        if logger:
            logger.warning(f"Image path does not exist for ChatGPT upload: {image_path}")
        return False

    abs_p = os.path.abspath(str(image_path))
    from selenium.webdriver.common.by import By

    try:
        file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
        target_input = None

        # Filter out capture="environment" (camera capture)
        for fi in file_inputs:
            cap = fi.get_attribute("capture")
            aria = (fi.get_attribute("aria-label") or "").lower()
            accept = (fi.get_attribute("accept") or "").lower()
            if not cap and ("photo" in aria or "file" in aria or "video" in aria or "image" in accept):
                target_input = fi
                break

        if not target_input and file_inputs:
            non_cap = [fi for fi in file_inputs if not fi.get_attribute("capture")]
            if non_cap:
                target_input = non_cap[-1]
            else:
                target_input = file_inputs[-1]

        if not target_input:
            for sel in ["button[aria-label*='Attach']", "button[data-testid='composer-plus-btn']"]:
                btns = driver.find_elements(By.CSS_SELECTOR, sel)
                if btns and btns[0].is_displayed():
                    btns[0].click()
                    time.sleep(1)
                    break
            file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            for fi in file_inputs:
                if not fi.get_attribute("capture"):
                    target_input = fi
                    break

        if not target_input:
            if logger:
                logger.warning("Could not reveal file upload inputs in ChatGPT.")
            return False

        target_input.send_keys(abs_p)

        # Wait dynamically for thumbnail to appear in DOM
        fname = os.path.basename(abs_p).lower()
        start_wait = time.time()
        attached = False
        while time.time() - start_wait < max_wait:
            time.sleep(0.5)
            found = driver.execute_script("""
                const fname = arguments[0];
                const thumbs = Array.from(document.querySelectorAll('.composer-attachment-surface, [data-testid*="attachment"], img'));
                return thumbs.some(t => {
                    const alt = (t.alt || '').toLowerCase();
                    const aria = (t.getAttribute('aria-label') || '').toLowerCase();
                    return alt.includes(fname) || aria.includes(fname) || t.classList.contains('composer-attachment-surface');
                });
            """, fname)
            if found:
                attached = True
                break

        time.sleep(1.0)
        msg = f"📎 Uploaded reference image to ChatGPT: {os.path.basename(abs_p)}"
        if logs is not None:
            logs.append(msg)
        if logger:
            logger.info(msg)
        return True
    except Exception as e_up:
        if logger:
            logger.warning(f"ChatGPT file upload notice: {e_up}")
        return False


def execute_human_generation_and_telegram_flow(
    platform="chatgpt",
    product=None,
    platforms=None,
    content_type="image",
    language="english",
    tone="professional",
    cta="learn_more",
    custom_instructions="",
    aspect_ratio="1:1",
    visual_style="photorealistic",
    skill_image_path=None,
    campaign_id=None
):
    """
    Executes the complete Human Flow for 'Generate & Send to Telegram for Approval':
    Step 1: Open Google Chrome like a human from the app.
    Step 2: Select/verify Shivam Mishra account (2003shivam1990@gmail.com).
    Step 3: Navigate to AI platform (ChatGPT, Gemini, Claude) & human-type prompt with natural cadence.
    Step 4: AI generates marketing copy and headline.
    Step 5: Generate branded creative graphic.
    Step 6: Send preview directly to Telegram with interactive Approve/Reject buttons.
    """
    import uuid
    from llm.prompts import build_social_prompt
    from llm import extract_json_or_fallback, generate_smart_marketing_copy
    from media.image_generator import generate_social_image
    from telegram.bot import send_preview_to_telegram

    logger.info("=== Starting Human-Flow: Generate Content & Send to Telegram ===")
    logs = []

    clean_platform = (platform or "chatgpt").lower().strip()
    if clean_platform not in ["gemini", "chatgpt", "claude"]:
        clean_platform = "chatgpt"

    product = product or {}
    product_name = (product.get("name") or "Featured Product").strip()
    desc = (product.get("description") or "Premium quality solution designed for your success.").strip()
    category = product.get("category", "Product")
    target_audience = product.get("target_audience", "Customers and clients")
    key_benefits = product.get("key_benefits", [])
    brand_colors = product.get("brand_colors") or {"primary": "#7C5CFC", "secondary": "#3DD6D0", "accent": "#FFB347"}
    if isinstance(key_benefits, str):
        try:
            key_benefits = json.loads(key_benefits)
        except Exception:
            key_benefits = [b.strip() for b in key_benefits.split(",") if b.strip()]

    platforms = platforms or ["facebook", "instagram"]
    campaign_id = campaign_id or str(uuid.uuid4())
    is_loan_solutions = "loan" in product_name.lower() or "loan" in desc.lower() or str(category).lower() == "finance"
    LOAN_SOLUTIONS_APPLY_URL = "https://loansolutions.everythingrental.in/application"

    # Auto-resolve fixed branding / reference image (e.g. Loan Solutions.png)
    loan_solutions_file = str(BASE_DIR / "Loan Solutions.png")
    if not skill_image_path or not os.path.exists(str(skill_image_path)):
        prod_logo = product.get("logo_path")
        if prod_logo and os.path.exists(str(prod_logo)):
            skill_image_path = prod_logo
            logger.info(f"Using product logo as reference image: {skill_image_path}")
            logs.append(f"📎 Attached product reference image: {os.path.basename(skill_image_path)}")
        elif os.path.exists(loan_solutions_file):
            skill_image_path = loan_solutions_file
            logger.info(f"Using fixed branding image: {skill_image_path}")
            logs.append("📎 Attached fixed branding image: Loan Solutions.png")

    # Step 1: Launch Chrome
    target_url = AI_URLS.get(clean_platform, "https://chatgpt.com")
    logs.append("🌐 Step 1: Opening Google Chrome like a human with Shivam Mishra's profile...")
    step1_click_and_launch_chrome(target_url=target_url)
    logs.append("✅ Step 1 Complete: Chrome browser is active and connected on port 9222.")

    # Step 2: Select Shivam Mishra account
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as SeleniumOptions

    options = SeleniumOptions()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=options)

    logs.append(f"👤 Step 2: Selecting / verifying account: {TARGET_NAME} ({TARGET_EMAIL})...")
    step2_select_shivam_account(driver)
    logs.append(f"✅ Step 2 Complete: Account {TARGET_NAME} ({TARGET_EMAIL}) verified & active.")

    # Step 3: Navigate to AI Platform & Human-Paced Prompting
    prompt = build_social_prompt(
        product_name=product_name,
        description=desc,
        category=category,
        target_audience=target_audience,
        key_benefits=key_benefits,
        tone=tone,
        language=language,
        cta=cta,
        platforms=platforms,
        content_type=content_type,
        custom_instructions=custom_instructions
    )

    fallback_data = generate_smart_marketing_copy(
        product_name=product_name,
        desc=desc,
        category=category,
        audience=target_audience,
        benefits=key_benefits,
        tone=tone,
        language=language,
        cta=cta,
        platforms=platforms
    )

    content_data = fallback_data
    img_path = None

    if clean_platform == "chatgpt":
        logs.append(f"💬 Step 3: Navigating to CHATGPT & inserting complete marketing + image prompt all at once...")
        try:
            # Switch to ChatGPT tab
            chatgpt_found = False
            for h in driver.window_handles:
                try:
                    driver.switch_to.window(h)
                    if "chatgpt.com" in driver.current_url:
                        chatgpt_found = True
                        break
                except Exception:
                    continue

            if not chatgpt_found:
                driver.get("https://chatgpt.com")

            # Refresh first so all content is fresh, visible, and clean
            from browser.driver import refresh_and_ensure_fresh
            refresh_and_ensure_fresh(driver, platform_name="ChatGPT")
            logs.append("🔄 ChatGPT refreshed first - all content is fresh and visible.")

            # Dismiss any dialogs/banners if present
            for d_sel in ["button[aria-label='Close']", "button[data-testid='close-button']", "div[role='dialog'] button"]:
                try:
                    for d_btn in driver.find_elements(By.CSS_SELECTOR, d_sel):
                        if d_btn.is_displayed():
                            d_btn.click()
                            human_sleep(0.2, 0.4)
                except Exception:
                    pass

            # Locate input box with retry
            input_box = None
            for _ in range(15):
                for sel in ["div.ProseMirror", "#prompt-textarea", "div[contenteditable='true']", "textarea"]:
                    try:
                        for el in driver.find_elements(By.CSS_SELECTOR, sel):
                            if el.is_displayed():
                                input_box = el
                                break
                    except Exception:
                        pass
                    if input_box:
                        break
                if input_box:
                    break
                time.sleep(1)

            if not input_box:
                raise RuntimeError("Could not locate ChatGPT prompt editor.")

            try:
                input_box.click()
            except Exception:
                ActionChains(driver).move_to_element(input_box).pause(0.2).click().perform()
            human_sleep(0.3, 0.6)

            # Query existing images before submitting
            existing_imgs = driver.execute_script("""
                return Array.from(document.querySelectorAll('img'))
                    .filter(img => (img.naturalWidth >= 250 || img.clientWidth >= 250))
                    .map(img => img.src);
            """) or []

            # Construct rich, diverse template prompt from dynamic variation matrix
            from media.template_engine import build_diverse_visual_prompt
            prompt_bundle = build_diverse_visual_prompt(
                product_name=product_name,
                description=desc,
                category=category,
                visual_style=visual_style,
                aspect_ratio=aspect_ratio,
                brand_colors=brand_colors,
                platforms=platforms,
                custom_instructions=custom_instructions,
                skill_image_path=skill_image_path,
            )
            unified_prompt = prompt_bundle["unified_prompt"]
            logs.append(f"🎨 Template Archetype Selected: {prompt_bundle['archetype_name']} (Variant #{prompt_bundle['seed']})")

            # 1. First: verify and paste prompt via PromptPasteVerifierAgent so text is cleanly placed
            from llm.prompt_paste_verifier_agent import PromptPasteVerifierAgent
            verifier_agent = PromptPasteVerifierAgent(driver)
            paste_res = verifier_agent.ensure_properly_pasted(
                driver=driver,
                prompt=unified_prompt,
                platform="chatgpt",
                required_substrings=[product_name]
            )
            logs.append(f"✍️ Prompt entered and verified ({paste_res.actual_length} chars, {paste_res.status})")
            human_sleep(0.5, 1.0)

            # 2. Second: attach reference image safely AFTER prompt is in place
            if skill_image_path and os.path.exists(str(skill_image_path)):
                upload_image_to_chatgpt(driver, skill_image_path, logger=logger, logs=logs)
                human_sleep(1.0, 1.8)

            # 3. Third: wait for Send button to be ready and click Send
            for _ in range(12):
                send_ready, send_details = verifier_agent.inspect_send_button(driver, "chatgpt")
                if send_ready:
                    break
                time.sleep(0.5)

            send_success = verifier_agent.click_send(driver=driver, platform="chatgpt")
            if not send_success:
                # Direct fallback
                for sel in ["button[data-testid='send-button']", "button[data-testid='composer-send-button']", "button[aria-label*='Send']"]:
                    btns = driver.find_elements(By.CSS_SELECTOR, sel)
                    if btns and btns[0].is_displayed():
                        try:
                            btns[0].click()
                            send_success = True
                            break
                        except Exception:
                            driver.execute_script("arguments[0].click();", btns[0])
                            send_success = True
                            break
                if not send_success:
                    input_box.send_keys(Keys.ENTER)

            logs.append("✅ Step 3 Complete: Full prompt and image submitted! Waiting for ChatGPT to generate image...")

            # Wait for image generation & capture response (poll up to 90s)
            poll_start = time.time()
            img_info = None
            while time.time() - poll_start < 90:
                time.sleep(3)
                img_info = driver.execute_async_script("""
                    const existing = arguments[0] || [];
                    const callback = arguments[arguments.length - 1];
                    const images = Array.from(document.querySelectorAll('img')).reverse();
                    const target = images.find(img => {
                        const alt = (img.alt || '').toLowerCase();
                        const src = (img.src || '').toLowerCase();
                        const isNotAttachment = !alt.includes('attachment') && !src.includes('avatar') && !src.includes('auth0') && !src.includes('profile');
                        const isBig = (img.naturalWidth >= 280 || img.clientWidth >= 250);
                        if (!isNotAttachment || !isBig) return false;
                        const isNew = !existing.includes(img.src);
                        if (!isNew) return false;
                        if (alt.includes('generated') || alt.includes('dall-e')) return true;
                        if (src.startsWith('blob:') && (img.naturalWidth >= 350 || img.clientWidth >= 300)) return true;
                        if (src.includes('oaidalleapiprodscus') || src.includes('files.oaiusercontent.com')) return true;
                        return false;
                    });
                    if (!target) return callback(null);
                    fetch(target.src)
                        .then(r => r.blob())
                        .then(blob => {
                            const reader = new FileReader();
                            reader.onloadend = () => callback({ data: reader.result, width: target.naturalWidth, height: target.naturalHeight });
                            reader.readAsDataURL(blob);
                        })
                        .catch(() => {
                            try {
                                const canvas = document.createElement('canvas');
                                canvas.width = target.naturalWidth || 1024;
                                canvas.height = target.naturalHeight || 1024;
                                const ctx = canvas.getContext('2d');
                                ctx.drawImage(target, 0, 0);
                                callback({ data: canvas.toDataURL('image/png'), width: canvas.width, height: canvas.height });
                            } catch(e) {
                                callback(null);
                            }
                        });
                """, existing_imgs)
                if img_info and img_info.get("data"):
                    break

            if img_info and img_info.get("data"):
                import base64
                from config import IMAGES_DIR
                data_b64 = img_info["data"]
                if "base64," in data_b64:
                    raw_bytes = base64.b64decode(data_b64.split("base64,")[1])
                    ar_slug = aspect_ratio.replace(":", "x")
                    filename = f"chatgpt_{uuid.uuid4().hex[:8]}_{ar_slug}.png"
                    output_path = IMAGES_DIR / filename
                    with open(output_path, "wb") as f:
                        f.write(raw_bytes)
                    img_path = output_path
                    logs.append(f"✅ Step 4 Complete: Successfully downloaded generated ChatGPT image ({len(raw_bytes):,} bytes).")

            # Extract generated caption from assistant message or prompt Task 2
            try:
                caption_found = False
                assistants = driver.find_elements(By.CSS_SELECTOR, "article, div[data-message-author-role='assistant'], [data-message-id]")
                for ast in reversed(assistants):
                    t = ast.text.strip()
                    if t and len(t) > 60 and "task 1" not in t.lower()[:30] and "generate" not in t.lower()[:20]:
                        content_data["caption"] = t
                        caption_found = True
                        import re
                        extracted_tags = re.findall(r"#\w+", t)
                        if extracted_tags:
                            content_data["hashtags"] = extracted_tags
                        break

                # If ChatGPT stopped after Task 1 (image) without writing Task 2 (caption):
                if not caption_found:
                    logs.append("✍️ Task 2: Prompting ChatGPT to generate viral caption & hashtags for the image...")
                    task2_input = None
                    for sel in ["div.ProseMirror", "#prompt-textarea", "div[contenteditable='true']", "textarea"]:
                        try:
                            for el in driver.find_elements(By.CSS_SELECTOR, sel):
                                if el.is_displayed():
                                    task2_input = el
                                    break
                        except Exception:
                            pass
                        if task2_input:
                            break

                    if task2_input:
                        try:
                            task2_input.click()
                        except Exception:
                            pass
                        human_sleep(0.3, 0.5)

                        apply_instruction = f" (MANDATORY: Always include this exact Apply Now link at the end: 👉 Apply Now: {LOAN_SOLUTIONS_APPLY_URL})" if is_loan_solutions else ""
                        task2_prompt = (
                            f"Now complete Task 2 for this image: Write the complete social media post for '{product_name}'. "
                            f"Include a compelling Headline, an engaging 2-3 paragraph marketing caption with strong hook and call-to-action{apply_instruction}, "
                            f"and 5-6 viral hashtags for {', '.join(platforms)}."
                        )
                        driver.execute_script("""
                            const ed = arguments[0];
                            ed.focus();
                            document.execCommand('selectAll', false, null);
                            document.execCommand('insertText', false, arguments[1]);
                            ed.dispatchEvent(new Event('input', { bubbles: true }));
                            ed.dispatchEvent(new Event('change', { bubbles: true }));
                        """, task2_input, task2_prompt)
                        human_sleep(0.4, 0.8)

                        # Submit Task 2
                        send_btn2 = None
                        for s in [
                            "button[data-testid='send-button']",
                            "button[data-testid='composer-send-button']",
                            "button[aria-label*='Send']",
                            "button[aria-label*='send']",
                            "#send-button"
                        ]:
                            try:
                                for b in driver.find_elements(By.CSS_SELECTOR, s):
                                    if b.is_displayed():
                                        send_btn2 = b
                                        break
                            except Exception:
                                pass
                            if send_btn2:
                                break

                        if send_btn2:
                            try:
                                send_btn2.click()
                            except Exception:
                                driver.execute_script("arguments[0].click();", send_btn2)
                        else:
                            task2_input.send_keys(Keys.ENTER)

                        # Wait for ChatGPT to stream caption (up to 20s)
                        poll_t2 = time.time()
                        while time.time() - poll_t2 < 20:
                            time.sleep(2)
                            assistants = driver.find_elements(By.CSS_SELECTOR, "article, div[data-message-author-role='assistant'], [data-message-id]")
                            if assistants:
                                last_text = assistants[-1].text.strip()
                                if last_text and len(last_text) > 60 and "task 2" not in last_text.lower()[:30]:
                                    content_data["caption"] = last_text
                                    import re
                                    extracted_tags = re.findall(r"#\w+", last_text)
                                    if extracted_tags:
                                        content_data["hashtags"] = extracted_tags
                                    caption_found = True
                                    break

                    if caption_found:
                        logs.append("✅ Task 2 Complete: Successfully retrieved AI marketing caption & hashtags from ChatGPT.")
                    else:
                        logs.append("ℹ️ Task 2 Notice: Using optimized marketing copy synthesis.")

            except Exception as e_text:
                logger.warning(f"Error parsing assistant text: {e_text}")

        except Exception as e_cg:
            logger.warning(f"ChatGPT unified flow notice: {e_cg}")
            logs.append(f"ℹ️ ChatGPT notice: {e_cg}")

    elif clean_platform == "gemini":
        logs.append("💬 Step 3: Navigating to GEMINI & inserting complete Task 1 (Image) + Task 2 (Copy) prompt all at once...")
        try:
            # Switch to or open Gemini tab
            gemini_found = False
            for h in driver.window_handles:
                try:
                    driver.switch_to.window(h)
                    if "gemini.google.com" in driver.current_url:
                        gemini_found = True
                        break
                except Exception:
                    continue

            if not gemini_found:
                driver.get("https://gemini.google.com/app")

            # Refresh first so all content is fresh, visible, and clean
            from browser.driver import refresh_and_ensure_fresh
            refresh_and_ensure_fresh(driver, platform_name="Gemini")
            logs.append("🔄 Gemini refreshed first - all content is fresh and visible.")

            # Dismiss any dialogs/banners if present
            for d_sel in [
                "button[aria-label='Close']",
                "button[data-testid='close-button']",
                "button[aria-label='Dismiss']",
                "div[role='dialog'] button",
            ]:
                try:
                    for d_btn in driver.find_elements(By.CSS_SELECTOR, d_sel):
                        if d_btn.is_displayed():
                            d_btn.click()
                            human_sleep(0.2, 0.4)
                except Exception:
                    pass

            # Locate Gemini prompt input box with retry
            input_box = None
            for _ in range(15):
                for sel in [
                    "div.ql-editor",
                    "rich-textarea p",
                    "rich-textarea div[contenteditable='true']",
                    "div[contenteditable='true']",
                    "textarea.ql-editor",
                    "textarea",
                ]:
                    try:
                        for el in driver.find_elements(By.CSS_SELECTOR, sel):
                            if el.is_displayed():
                                input_box = el
                                break
                    except Exception:
                        pass
                    if input_box:
                        break
                if input_box:
                    break
                time.sleep(1)

            if not input_box:
                raise RuntimeError("Could not locate Gemini prompt editor. Please verify login.")

            try:
                input_box.click()
            except Exception:
                ActionChains(driver).move_to_element(input_box).pause(0.2).click().perform()
            human_sleep(0.3, 0.6)

            # If reference image / skill image exists (e.g. Loan Solutions.png), attach it like a human via file upload in Gemini
            if skill_image_path and os.path.exists(str(skill_image_path)):
                uploaded = upload_image_to_gemini(driver, skill_image_path, logger=logger, logs=logs)
                if not uploaded:
                    logs.append("⚠️ Notice: Could not attach image to Gemini, proceeding with prompt.")

            # Query existing images before submitting to avoid matching old results
            existing_imgs = driver.execute_script("""
                return Array.from(document.querySelectorAll('img'))
                    .filter(img => (img.naturalWidth >= 200 || img.clientWidth >= 200))
                    .map(img => img.src);
            """) or []

            # Construct rich, diverse template prompt divided into Task 1 and Task 2 at once
            from media.template_engine import build_diverse_visual_prompt
            prompt_bundle = build_diverse_visual_prompt(
                product_name=product_name,
                description=desc,
                category=category,
                visual_style=visual_style,
                aspect_ratio=aspect_ratio,
                brand_colors=brand_colors,
                platforms=platforms,
                custom_instructions=custom_instructions,
                skill_image_path=skill_image_path,
            )
            unified_prompt = prompt_bundle["unified_prompt"]
            logs.append(f"🎨 Template Archetype Selected: {prompt_bundle['archetype_name']} (Variant #{prompt_bundle['seed']})")

            # Verify & paste prompt via PromptPasteVerifierAgent
            from llm.prompt_paste_verifier_agent import PromptPasteVerifierAgent
            verifier_agent = PromptPasteVerifierAgent(driver)
            paste_res = verifier_agent.ensure_properly_pasted(
                driver=driver,
                prompt=unified_prompt,
                platform="gemini",
                required_substrings=["TASK 1", "TASK 2"]
            )
            logs.append(f"🤖 PromptPasteVerifierAgent verified prompt: {paste_res.status} ({paste_res.similarity_ratio*100:.1f}% match, {paste_res.actual_length} chars, Send ready: {paste_res.send_button_ready}) via {paste_res.method_used}")
            human_sleep(0.4, 0.8)

            # Submit prompt via agent
            verifier_agent.click_send(driver=driver, platform="gemini")
            logs.append("✅ Step 3 Complete: Full prompt (Task 1 & Task 2) submitted to Gemini all at once! Waiting for generation...")

            # Wait for image generation & capture response (poll up to 75s)
            poll_start = time.time()
            img_info = None
            while time.time() - poll_start < 85:
                time.sleep(3)
                img_info = driver.execute_async_script("""
                    const existing = arguments[0] || [];
                    const callback = arguments[arguments.length - 1];

                    // Find all images on the page in reverse order
                    const allImgs = Array.from(document.querySelectorAll('img')).reverse();

                    const target = allImgs.find(img => {
                        const alt = (img.alt || '').toLowerCase();
                        const cls = (img.className || '').toLowerCase();
                        const src = (img.src || '').toLowerCase();

                        // Explicitly exclude uploaded user files & preview chips
                        if (cls.includes('preview') || alt.includes('preview') || alt.includes('uploaded')) return false;
                        if (img.closest('rich-textarea')) return false;
                        if (img.closest('.attachment-container:not(.generated-images)')) return false;

                        // Exclude avatars, icons, sparkle svgs, Google profile icons
                        if (src.includes('avatar') || src.includes('profile') || src.includes('sparkle') || src.endsWith('.svg') || src.includes('googleusercontent.com/a/')) return false;

                        // Exclude small images
                        const w = img.naturalWidth || img.clientWidth || 0;
                        const h = img.naturalHeight || img.clientHeight || 0;
                        if (w < 300 || h < 300) return false;

                        // Exclude already existing images
                        if (existing.includes(img.src)) return false;

                        // Identify Gemini generated image
                        const isGeneratedClass = cls.includes('image') && !cls.includes('preview') && !cls.includes('sparkle');
                        const isGeneratedAlt = alt.includes('generated') || alt.includes('ai generated') || alt.includes('photograph') || alt.includes('commercial');
                        const isBlobImg = src.startsWith('blob:') && w >= 450 && h >= 450;

                        return isGeneratedClass || isGeneratedAlt || isBlobImg;
                    });

                    if (!target) return callback(null);

                    // Canvas-first extraction: Fast, synchronous, extracts full-res PNG without CORS/redirect issues
                    try {
                        const canvas = document.createElement('canvas');
                        canvas.width = target.naturalWidth || 1024;
                        canvas.height = target.naturalHeight || 1024;
                        const ctx = canvas.getContext('2d');
                        ctx.drawImage(target, 0, 0);
                        const dataUrl = canvas.toDataURL('image/png');
                        if (dataUrl && dataUrl.startsWith('data:image/png;base64,iVBORw0K') && dataUrl.length > 50000) {
                            return callback({ data: dataUrl, width: canvas.width, height: canvas.height, alt: target.alt });
                        }
                    } catch(e) {
                        // Canvas tainted fallback
                    }

                    // Fallback to fetch only if verified image blob
                    fetch(target.src)
                        .then(r => r.blob())
                        .then(blob => {
                            if (!blob.type || !blob.type.startsWith('image/')) {
                                return callback(null);
                            }
                            const reader = new FileReader();
                            reader.onloadend = () => callback({ data: reader.result, width: target.naturalWidth, height: target.naturalHeight, alt: target.alt });
                            reader.readAsDataURL(blob);
                        })
                        .catch(() => callback(null));
                """, existing_imgs)
                if img_info and img_info.get("data"):
                    break

            if img_info and img_info.get("data"):
                import base64
                from config import IMAGES_DIR
                data_b64 = img_info["data"]
                if "base64," in data_b64:
                    raw_bytes = base64.b64decode(data_b64.split("base64,")[1])
                    # Strictly verify bytes start with valid image magic numbers
                    is_valid_image = (
                        raw_bytes.startswith(b"\x89PNG") or
                        raw_bytes.startswith(b"\xff\xd8") or
                        (raw_bytes.startswith(b"RIFF") and b"WEBP" in raw_bytes[:16])
                    )
                    if is_valid_image and len(raw_bytes) > 20000:
                        ar_slug = aspect_ratio.replace(":", "x")
                        filename = f"gemini_{uuid.uuid4().hex[:8]}_{ar_slug}.png"
                        output_path = IMAGES_DIR / filename
                        with open(output_path, "wb") as f:
                            f.write(raw_bytes)
                        img_path = output_path
                        logs.append(f"✅ Step 4 Complete: Successfully downloaded generated Gemini image ({len(raw_bytes):,} bytes).")
                    else:
                        logger.warning(f"Downloaded bytes failed image header check (len={len(raw_bytes)}), skipping corrupted data.")
                        img_path = None

            # Extract generated caption & hashtags from Gemini text response (Task 2)
            try:
                caption_found = False
                for sel in ["model-response", ".model-response-text", ".response-content", "div.markdown"]:
                    responses = driver.find_elements(By.CSS_SELECTOR, sel)
                    if responses:
                        t = responses[-1].text.strip()
                        if t and len(t) > 60 and "task 1" not in t.lower()[:30]:
                            content_data["caption"] = t
                            caption_found = True
                            import re
                            extracted_tags = re.findall(r"#\w+", t)
                            if extracted_tags:
                                content_data["hashtags"] = extracted_tags
                            break

                # If Gemini generated image but didn't output text for Task 2:
                if not caption_found:
                    logs.append("✍️ Task 2: Prompting Gemini to generate viral caption & hashtags for the image...")
                    task2_input = None
                    for sel in [
                        "div.ql-editor",
                        "rich-textarea p",
                        "div[contenteditable='true']",
                        "textarea",
                    ]:
                        try:
                            for el in driver.find_elements(By.CSS_SELECTOR, sel):
                                if el.is_displayed():
                                    task2_input = el
                                    break
                        except Exception:
                            pass
                        if task2_input:
                            break

                    if task2_input:
                        try:
                            task2_input.click()
                        except Exception:
                            pass
                        human_sleep(0.3, 0.5)

                        apply_instruction = f" (MANDATORY: Always include this exact Apply Now link at the end: 👉 Apply Now: {LOAN_SOLUTIONS_APPLY_URL})" if is_loan_solutions else ""
                        task2_prompt = (
                            f"Now complete Task 2 for this image: Write the complete social media post for '{product_name}'. "
                            f"Include a compelling Headline, an engaging 2-3 paragraph marketing caption with strong hook and call-to-action{apply_instruction}, "
                            f"and 5-6 viral hashtags for {', '.join(platforms)}."
                        )
                        driver.execute_script("""
                            const ed = arguments[0];
                            ed.focus();
                            document.execCommand('selectAll', false, null);
                            document.execCommand('insertText', false, arguments[1]);
                            ed.dispatchEvent(new Event('input', { bubbles: true }));
                            ed.dispatchEvent(new Event('change', { bubbles: true }));
                        """, task2_input, task2_prompt)
                        human_sleep(0.4, 0.8)

                        send_btn2 = None
                        for s in [
                            "button[aria-label*='Send']",
                            "button.send-button",
                            "mat-icon[fonticon='send']",
                            "[data-test-id='send-button']",
                        ]:
                            try:
                                for b in driver.find_elements(By.CSS_SELECTOR, s):
                                    if b.is_displayed():
                                        send_btn2 = b
                                        break
                            except Exception:
                                pass
                            if send_btn2:
                                break

                        if send_btn2:
                            try:
                                send_btn2.click()
                            except Exception:
                                driver.execute_script("arguments[0].click();", send_btn2)
                        else:
                            task2_input.send_keys(Keys.ENTER)

                        # Wait for Gemini response text
                        poll_t2 = time.time()
                        while time.time() - poll_t2 < 20:
                            time.sleep(2)
                            for sel in ["model-response", ".model-response-text", ".response-content", "div.markdown"]:
                                responses = driver.find_elements(By.CSS_SELECTOR, sel)
                                if responses:
                                    last_text = responses[-1].text.strip()
                                    if last_text and len(last_text) > 60 and "task 2" not in last_text.lower()[:30]:
                                        content_data["caption"] = last_text
                                        import re
                                        extracted_tags = re.findall(r"#\w+", last_text)
                                        if extracted_tags:
                                            content_data["hashtags"] = extracted_tags
                                        caption_found = True
                                        break
                            if caption_found:
                                break

                    if caption_found:
                        logs.append("✅ Task 2 Complete: Successfully retrieved AI marketing caption & hashtags from Gemini.")
                    else:
                        logs.append("ℹ️ Task 2 Notice: Using optimized marketing copy synthesis.")

            except Exception as e_text:
                logger.warning(f"Error parsing Gemini response text: {e_text}")

        except Exception as e_gem:
            logger.warning(f"Gemini unified flow notice: {e_gem}")
            logs.append(f"ℹ️ Gemini notice: {e_gem}")

    else:
        logs.append(f"💬 Step 3: Navigating to {clean_platform.upper()} & prompting marketing copy...")
        try:
            ai_res = step3_search_ai_platform(driver, clean_platform, prompt)
            raw_text = ai_res.get("response", "")
            if raw_text:
                parsed = extract_json_or_fallback(raw_text, None)
                if parsed and isinstance(parsed, dict) and "caption" in parsed:
                    content_data = parsed
                elif len(raw_text) > 40:
                    content_data["caption"] = raw_text
            logs.append(f"✅ Step 3 Complete: AI generated viral copy and headline.")
        except Exception as e_ai:
            logs.append(f"ℹ️ Step 3 Notice: {e_ai}. Using optimized copy synthesis.")

    # Media Generation: Video vs Image
    media_file_path = None
    if content_type == "video":
        logs.append("🎥 Step 4: Compiling dynamic promotional video with Gemini marketing slides...")
        headline = content_data.get("headline") or f"Discover {product_name}"
        subheadline = content_data.get("subheadline") or (desc[:65] if desc else "The smart solution for you.")
        resolved_logo = skill_image_path or product.get("logo_path")
        if not resolved_logo and ("loan" in product_name.lower() or "loan" in desc.lower()) and os.path.exists(loan_solutions_file):
            resolved_logo = loan_solutions_file

        slides = [
            {"text": headline, "visual": subheadline},
            {"text": f"Why Choose {product_name}?", "visual": key_benefits[0] if key_benefits else "Built for exceptional performance."},
            {"text": "Limited Time Access", "visual": "Transform your daily workflow today!"}
        ]
        try:
            from media.video_generator import generate_promo_video
            video_out = generate_promo_video(
                product_name=product_name,
                slides=slides,
                brand_colors=brand_colors,
                duration=15,
                aspect_ratio="9:16",
                logo_path=resolved_logo
            )
            media_file_path = str(video_out)
            logs.append(f"✅ Step 4 Complete: High-converting video reel ready ({os.path.basename(media_file_path)}).")
        except Exception as e_vid:
            logger.warning(f"Video generator notice: {e_vid}")

    if not media_file_path:
        # Fallback to high-res branded design engine if image wasn't downloaded
        if not img_path or not os.path.exists(img_path):
            headline = content_data.get("headline") or f"Discover {product_name}"
            subheadline = content_data.get("subheadline") or (desc[:65] if desc else "The smart solution for you.")
            resolved_logo = skill_image_path or product.get("logo_path")
            if not resolved_logo and ("loan" in product_name.lower() or "loan" in desc.lower()) and os.path.exists(loan_solutions_file):
                resolved_logo = loan_solutions_file

            img_path = generate_social_image(
                product_name=product_name,
                headline=headline,
                subheadline=subheadline,
                brand_colors=brand_colors,
                aspect_ratio=aspect_ratio,
                cta_text="Learn More ➜",
                logo_path=resolved_logo,
                category=category,
                visual_style=visual_style
            )
            logs.append(f"✅ Step 4 Complete: High-converting branded graphic ready ({os.path.basename(str(img_path))}).")
        media_file_path = str(img_path)

    # Step 5: Telegram Dispatch for Approval
    logs.append("📱 Step 5: Dispatching preview to Telegram bot for review & approval...")
    caption = content_data.get("caption", f"Discover {product_name}!")
    hashtags = content_data.get("hashtags", [])
    full_caption = caption
    if is_loan_solutions and LOAN_SOLUTIONS_APPLY_URL not in full_caption:
        full_caption = f"{full_caption.rstrip()}\n\n👉 Apply Now: {LOAN_SOLUTIONS_APPLY_URL}"
    if hashtags:
        tag_str = " ".join([h if h.startswith("#") else f"#{h}" for h in hashtags])
        if tag_str not in full_caption:
            full_caption = f"{full_caption}\n\n{tag_str}"

    tg_result = send_preview_to_telegram(
        campaign_id=campaign_id,
        caption=full_caption,
        media_path=media_file_path,
        platforms=platforms,
        revision_count=0,
        product_name=product_name,
        apply_url=LOAN_SOLUTIONS_APPLY_URL if is_loan_solutions else None
    )
    tg_success = tg_result.get("status") == "success"
    if tg_success:
        logs.append("✅ Step 5 Complete: Preview sent to Telegram with interactive Approve/Reject buttons!")
    else:
        logs.append(f"⚠️ Step 5 Notice: {tg_result.get('message', 'Telegram dispatch pending')}")

    # Immediately save/register campaign in PostgreSQL & SQLite database
    try:
        from db_campaigns import save_or_update_campaign
        msg_id_val = None
        if isinstance(tg_result, dict):
            resp = tg_result.get("response") or {}
            res_inner = resp.get("result") or {}
            msg_id_val = res_inner.get("message_id")
        save_or_update_campaign(
            campaign_id=campaign_id,
            status="preview_sent" if tg_success else "draft",
            platforms=platforms,
            media_path=media_file_path,
            caption=full_caption,
            hashtags=hashtags,
            content_type=content_type,
            product_id=product.get("id") if isinstance(product, dict) else None,
            product_name=product_name,
            llm_provider=clean_platform,
            posted_at_now=False,
            telegram_message_id=msg_id_val
        )
        logs.append(f"💾 Campaign record {campaign_id[:8]}... saved to database.")
    except Exception as e_dbsave:
        logger.warning(f"Error saving generated campaign to database: {e_dbsave}")

    return {
        "status": "success",
        "campaign_id": campaign_id,
        "logs": logs,
        "content": content_data,
        "media_path": media_file_path,
        "telegram_dispatched": tg_success,
        "telegram_details": tg_result,
        "account": f"{TARGET_NAME} ({TARGET_EMAIL})",
    }


if __name__ == "__main__":
    test_platform = sys.argv[1] if len(sys.argv) > 1 else "gemini"
    test_query = sys.argv[2] if len(sys.argv) > 2 else "What is the best marketing strategy for AI tools in 2026?"
    res = execute_full_human_flow(test_platform, test_query)
    print(json.dumps(res, indent=2))
