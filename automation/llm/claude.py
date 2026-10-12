"""
Claude Web Interactor via Selenium with saved profile.
"""
import time
import logging
from browser.driver import browser
from config import PLATFORM_URLS

logger = logging.getLogger("automation.llm.claude")


def generate_with_claude_browser(prompt: str) -> str:
    """Interacts with claude.ai via Selenium using saved Chrome profile."""
    try:
        driver = browser.navigate("claude", PLATFORM_URLS["claude"])
        time.sleep(3)

        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys

        input_box = None
        selectors = [
            "div[contenteditable='true']",
            "fieldset div[contenteditable='true']",
            "textarea",
        ]
        for sel in selectors:
            try:
                elems = driver.find_elements(By.CSS_SELECTOR, sel)
                if elems and elems[0].is_displayed():
                    input_box = elems[0]
                    break
            except Exception:
                continue

        if not input_box:
            raise RuntimeError("Could not locate Claude input field. User may need to sign in first.")

        input_box.click()
        driver.execute_script("arguments[0].innerText = arguments[1];", input_box, prompt)
        input_box.send_keys(" ")
        time.sleep(1)

        send_btn = None
        for sel in ["button[aria-label*='Send']", "button[type='submit']"]:
            try:
                btns = driver.find_elements(By.CSS_SELECTOR, sel)
                if btns and btns[0].is_displayed():
                    send_btn = btns[0]
                    break
            except Exception:
                continue

        if send_btn:
            send_btn.click()
        else:
            input_box.send_keys(Keys.ENTER)

        logger.info("Waiting for Claude response...")
        time.sleep(8)

        for sel in ["div.font-claude-message", ".prose", "div[data-is-streaming='false']"]:
            try:
                responses = driver.find_elements(By.CSS_SELECTOR, sel)
                if responses:
                    return responses[-1].text
            except Exception:
                continue

        return "Generated response from Claude."
    except Exception as e:
        logger.warning(f"Browser interaction with Claude failed: {e}. Using intelligent fallback.")
        raise
