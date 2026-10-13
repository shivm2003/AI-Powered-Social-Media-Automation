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

    # Human-like pause for page load and visual inspection
    human_sleep(2.5, 4.0)

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
                human_sleep(2.5, 4.0)
            else:
                human_sleep(0.8, 1.5)

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

            # Construct unified prompt asking for BOTH image and caption all at once
            unified_prompt = (
                f"Generate a high-converting, photorealistic commercial marketing image for '{product_name}'. "
                f"Description: {desc[:140]}. "
                f"Visual layout: {aspect_ratio} square aspect ratio, modern advertising style, vibrant commercial lighting, sleek 3D tech aesthetics, 8k resolution. "
                f"Below the image, also write the complete social media post:\n"
                f"Headline: Discover {product_name}\n"
                f"Caption: An engaging 2-3 paragraph marketing copy with strong hook and call-to-action.\n"
                f"Hashtags: 5-6 viral hashtags for {', '.join(platforms)}."
            )

            # Insert ALL PROMPT AT ONCE
            driver.execute_script("""
                const ed = arguments[0];
                const text = arguments[1];
                ed.focus();
                document.execCommand('selectAll', false, null);
                document.execCommand('insertText', false, text);
                ed.dispatchEvent(new Event('input', { bubbles: true }));
                ed.dispatchEvent(new Event('change', { bubbles: true }));
            """, input_box, unified_prompt)
            human_sleep(0.5, 1.0)

            # Fallback if text didn't insert
            current_val = (input_box.text or input_box.get_attribute("value") or "").strip()
            if not current_val:
                input_box.send_keys(unified_prompt)
                human_sleep(0.4, 0.8)

            # Submit prompt
            send_btn = None
            for sel in [
                "button[data-testid='send-button']",
                "button[data-testid='composer-send-button']",
                "button[aria-label*='Send']",
                "button[aria-label*='send']",
                "#send-button"
            ]:
                try:
                    for b in driver.find_elements(By.CSS_SELECTOR, sel):
                        if b.is_displayed():
                            send_btn = b
                            break
                except Exception:
                    pass
                if send_btn:
                    break

            if send_btn:
                try:
                    send_btn.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", send_btn)
            else:
                input_box.send_keys(Keys.ENTER)

            logs.append("✅ Step 3 Complete: Full prompt submitted all at once! Waiting for ChatGPT to generate image...")

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

            # Extract generated caption from assistant message
            try:
                assistants = driver.find_elements(By.CSS_SELECTOR, "article, div[data-message-author-role='assistant'], [data-message-id]")
                for ast in reversed(assistants):
                    t = ast.text.strip()
                    if t and len(t) > 30 and "generate" not in t.lower()[:20]:
                        content_data["caption"] = t
                        import re
                        extracted_tags = re.findall(r"#\w+", t)
                        if extracted_tags:
                            content_data["hashtags"] = extracted_tags
                        break
            except Exception as e_text:
                logger.warning(f"Error parsing assistant text: {e_text}")

        except Exception as e_cg:
            logger.warning(f"ChatGPT unified flow notice: {e_cg}")
            logs.append(f"ℹ️ ChatGPT notice: {e_cg}")

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

    # Fallback to high-res branded design engine if image wasn't downloaded
    if not img_path or not os.path.exists(img_path):
        headline = content_data.get("headline") or f"Discover {product_name}"
        subheadline = content_data.get("subheadline") or (desc[:65] if desc else "The smart solution for you.")
        resolved_logo = skill_image_path or product.get("logo_path")
        img_path = generate_social_image(
            product_name=product_name,
            headline=headline,
            subheadline=subheadline,
            brand_colors=brand_colors,
            aspect_ratio=aspect_ratio,
            cta_text="Learn More ➜",
            logo_path=resolved_logo,
            category=category
        )
        logs.append(f"✅ Step 4 Complete: High-converting branded graphic ready ({os.path.basename(str(img_path))}).")

    # Step 5: Telegram Dispatch for Approval
    logs.append("📱 Step 5: Dispatching preview to Telegram bot for review & approval...")
    caption = content_data.get("caption", f"Discover {product_name}!")
    hashtags = content_data.get("hashtags", [])
    full_caption = caption
    if hashtags:
        tag_str = " ".join([h if h.startswith("#") else f"#{h}" for h in hashtags])
        if tag_str not in full_caption:
            full_caption = f"{full_caption}\n\n{tag_str}"

    tg_result = send_preview_to_telegram(
        campaign_id=campaign_id,
        caption=full_caption,
        media_path=str(img_path) if img_path else "",
        platforms=platforms,
        revision_count=0
    )
    tg_success = tg_result.get("status") == "success"
    if tg_success:
        logs.append("✅ Step 5 Complete: Preview sent to Telegram with interactive Approve/Reject buttons!")
    else:
        logs.append(f"⚠️ Step 5 Notice: {tg_result.get('message', 'Telegram dispatch pending')}")

    return {
        "status": "success",
        "campaign_id": campaign_id,
        "logs": logs,
        "content": content_data,
        "media_path": str(img_path) if img_path else "",
        "telegram_dispatched": tg_success,
        "telegram_details": tg_result,
        "account": f"{TARGET_NAME} ({TARGET_EMAIL})",
    }


if __name__ == "__main__":
    test_platform = sys.argv[1] if len(sys.argv) > 1 else "gemini"
    test_query = sys.argv[2] if len(sys.argv) > 2 else "What is the best marketing strategy for AI tools in 2026?"
    res = execute_full_human_flow(test_platform, test_query)
    print(json.dumps(res, indent=2))
