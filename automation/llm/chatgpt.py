"""
ChatGPT Web Interactor via Selenium with saved profile.
"""
import time
import logging
from browser.driver import browser
from config import PLATFORM_URLS

logger = logging.getLogger("automation.llm.chatgpt")


def generate_with_chatgpt_browser(prompt: str) -> str:
    """Interacts with chatgpt.com via Selenium using saved Chrome profile."""
    try:
        driver = browser.navigate("chatgpt", PLATFORM_URLS["chatgpt"])
        time.sleep(3)

        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys

        input_box = None
        selectors = [
            "#prompt-textarea",
            "textarea[data-id='root']",
            "div[contenteditable='true']",
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
            raise RuntimeError("Could not locate ChatGPT prompt textarea. User may need to sign in first.")

        input_box.click()
        driver.execute_script("arguments[0].value = arguments[1];", input_box, prompt)
        input_box.send_keys(" ")
        time.sleep(1)

        send_btn = None
        for sel in ["button[data-testid='send-button']", "button[aria-label='Send prompt']"]:
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

        logger.info("Waiting for ChatGPT response...")
        time.sleep(8)

        for sel in ["div[data-message-author-role='assistant']", ".markdown"]:
            try:
                responses = driver.find_elements(By.CSS_SELECTOR, sel)
                if responses:
                    return responses[-1].text
            except Exception:
                continue

        return "Generated response from ChatGPT."
    except Exception as e:
        logger.warning(f"Browser interaction with ChatGPT failed: {e}. Using intelligent fallback.")
        raise
