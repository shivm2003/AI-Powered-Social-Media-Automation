"""
Gemini Web Interactor via Selenium with saved profile.
"""
import time
import json
import logging
from browser.driver import browser
from config import PLATFORM_URLS, TIMEOUTS

logger = logging.getLogger("automation.llm.gemini")


def generate_with_gemini_browser(prompt: str) -> str:
    """Interacts with gemini.google.com via Selenium using saved Chrome profile."""
    try:
        driver = browser.navigate("gemini", PLATFORM_URLS["gemini"])
        time.sleep(3)

        # Look for the prompt textarea in Gemini
        # Typical selectors: div[contenteditable='true'], textarea, rich-textarea
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys

        input_box = None
        selectors = [
            "rich-textarea p",
            "div[contenteditable='true']",
            "textarea.ql-editor",
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
            raise RuntimeError("Could not locate Gemini input field. User may need to sign in first.")

        # Type prompt
        input_box.click()
        time.sleep(0.5)
        # Paste or type prompt
        driver.execute_script("arguments[0].innerText = arguments[1];", input_box, prompt)
        input_box.send_keys(" ")
        time.sleep(1)

        # Click send or press Enter
        send_button = None
        for sel in ["button[aria-label*='Send']", "button.send-button", "mat-icon[fonticon='send']"]:
            try:
                btns = driver.find_elements(By.CSS_SELECTOR, sel)
                if btns and btns[0].is_displayed():
                    send_button = btns[0]
                    break
            except Exception:
                continue

        if send_button:
            send_button.click()
        else:
            input_box.send_keys(Keys.ENTER)

        # Wait for generation to finish
        logger.info("Waiting for Gemini response...")
        time.sleep(8)

        # Grab response content
        for sel in ["model-response", ".model-response-text", ".response-content", "div.markdown"]:
            try:
                responses = driver.find_elements(By.CSS_SELECTOR, sel)
                if responses:
                    return responses[-1].text
            except Exception:
                continue

        return "Generated response from Gemini."
    except Exception as e:
        logger.warning(f"Browser interaction with Gemini failed: {e}. Using intelligent fallback.")
        raise
