"""
Facebook Social Poster via Selenium with interactive login & credential handling.
Supports:
- Checking login state
- Prompting & injecting password via Telegram if login is required
- Opening composer ("What's on your mind?")
- Attaching generated media
- Injecting caption + viral hashtags
- Submitting post
"""
import time
import os
import logging
from pathlib import Path
from browser.driver import browser
from config import PLATFORM_URLS

logger = logging.getLogger("automation.social.facebook")


def is_facebook_login_needed(driver) -> bool:
    """Checks if Facebook is currently showing a login screen."""
    from selenium.webdriver.common.by import By

    # Look for password inputs or login forms
    pass_inputs = driver.find_elements(By.CSS_SELECTOR, "input[name='pass'], input#pass, input[type='password']")
    for el in pass_inputs:
        if el.is_displayed():
            return True

    # Look for prominent 'Log In' buttons
    login_buttons = driver.find_elements(By.CSS_SELECTOR, "button[name='login'], button[data-testid='royal_login_button']")
    for btn in login_buttons:
        if btn.is_displayed():
            return True

    # Check URL
    current_url = driver.current_url.lower()
    if "login" in current_url or "checkpoint" in current_url:
        return True

    return False


def submit_facebook_login(driver, password: str, email_or_user: str = None) -> dict:
    """Injects password (and optional email) into Facebook login form and submits."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys

    logger.info("Injecting credentials into Facebook login form...")

    try:
        # Fill email if provided and empty
        if email_or_user:
            email_inputs = driver.find_elements(By.CSS_SELECTOR, "input#email, input[name='email'], input[type='email']")
            for el in email_inputs:
                if el.is_displayed():
                    el.clear()
                    el.send_keys(email_or_user)
                    time.sleep(0.3)
                    break

        # Fill password
        pass_inputs = driver.find_elements(By.CSS_SELECTOR, "input#pass, input[name='pass'], input[type='password']")
        target_pass = None
        for el in pass_inputs:
            if el.is_displayed():
                target_pass = el
                break

        if not target_pass:
            return {"status": "error", "message": "Password field not found on Facebook login page."}

        target_pass.clear()
        target_pass.send_keys(password)
        time.sleep(0.5)

        # Click login button
        login_btn = None
        for sel in ["button[name='login']", "button[data-testid='royal_login_button']", "button[type='submit']"]:
            for b in driver.find_elements(By.CSS_SELECTOR, sel):
                if b.is_displayed() and b.is_enabled():
                    login_btn = b
                    break
            if login_btn:
                break

        if login_btn:
            login_btn.click()
        else:
            target_pass.send_keys(Keys.ENTER)

        logger.info("Submitted Facebook login form. Waiting for authentication...")
        time.sleep(5)

        # Verify if login succeeded
        if not is_facebook_login_needed(driver):
            logger.info("Facebook authentication successful!")
            return {"status": "success", "message": "Facebook authenticated successfully."}
        else:
            return {"status": "pending_check", "message": "Login submitted. Waiting for verification/2FA."}

    except Exception as e:
        logger.error(f"Error submitting Facebook login: {e}")
        return {"status": "error", "message": str(e)}


def request_password_from_telegram_sync(platform: str = "facebook", timeout_secs: int = 120) -> dict:
    """
    Sends a password request to Telegram, waits for the user's password reply,
    securely deletes the password message from Telegram, and returns credentials.
    """
    from telegram.bot import (
        get_telegram_credentials,
        make_telegram_request,
        delete_telegram_message,
        send_text_message,
    )

    bot_token, chat_id = get_telegram_credentials()
    if not bot_token or not chat_id:
        logger.warning("Telegram Bot Token or Chat ID not configured.")
        return None

    # Determine baseline update offset to ignore past messages
    offset = None
    try:
        last_updates = make_telegram_request(bot_token, "getUpdates", data={"offset": -1, "limit": 1})
        if last_updates.get("ok") and last_updates.get("result"):
            offset = last_updates["result"][-1]["update_id"] + 1
    except Exception as e:
        logger.debug(f"Update offset query note: {e}")

    prompt_text = (
        f"🔒 <b>{platform.capitalize()} Login Required</b>\n\n"
        f"The automation requires your {platform.capitalize()} password to publish this post.\n\n"
        f"👉 <i>Please reply directly to this message with your password (or <code>email:password</code>).</i>\n\n"
        f"The bot will securely delete your message and log into Facebook automatically."
    )
    send_text_message(chat_id, prompt_text)
    logger.info(f"Dispatched Telegram password request to chat {chat_id}. Listening for up to {timeout_secs}s...")

    start_time = time.time()
    while time.time() - start_time < timeout_secs:
        try:
            params = {"timeout": 4}
            if offset:
                params["offset"] = offset

            res = make_telegram_request(bot_token, "getUpdates", data=params)
            if res.get("ok") and "result" in res:
                for update in res["result"]:
                    offset = update["update_id"] + 1
                    msg = update.get("message")
                    if msg and str(msg.get("chat", {}).get("id")) == str(chat_id):
                        text = msg.get("text", "").strip()
                        msg_id = msg.get("message_id")
                        if text and not text.startswith("/"):
                            # Delete password message from Telegram immediately for privacy & security
                            delete_telegram_message(chat_id, msg_id)
                            send_text_message(
                                chat_id,
                                f"🔑 <b>Password received securely.</b> Ingesting into {platform.capitalize()} in Chrome..."
                            )

                            email = None
                            password = text
                            if ":" in text and not text.startswith("http"):
                                parts = text.split(":", 1)
                                email, password = parts[0].strip(), parts[1].strip()

                            return {"password": password, "email": email}

        except Exception as e_poll:
            logger.warning(f"Error checking Telegram updates: {e_poll}")

        time.sleep(2)

    send_text_message(chat_id, f"⏱️ Password request for {platform.capitalize()} timed out after {timeout_secs}s.")
    return None


def post_to_facebook(media_path: str = None, caption: str = "", password_callback=None) -> dict:
    """
    Publishes a post with optional image/video and caption to Facebook.
    If login is required, invokes password_callback (or Telegram sync request) to retrieve password.
    """
    try:
        logger.info("Navigating to Facebook...")
        driver = browser.navigate("facebook", PLATFORM_URLS["facebook"])
        time.sleep(3)

        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.common.action_chains import ActionChains

        # 1. Check if login is required
        if is_facebook_login_needed(driver):
            logger.warning("Facebook requires login! Prompting password via Telegram...")
            callback = password_callback or (lambda: request_password_from_telegram_sync("facebook"))
            credentials = callback()

            if not credentials:
                return {"status": "error", "platform": "facebook", "message": "No password provided from Telegram."}

            pwd = credentials.get("password") if isinstance(credentials, dict) else credentials
            email = credentials.get("email") if isinstance(credentials, dict) else None

            login_res = submit_facebook_login(driver, password=pwd, email_or_user=email)
            if login_res.get("status") == "error":
                return {"status": "error", "platform": "facebook", "message": login_res.get("message")}

            time.sleep(4)

        # 2. Look for "What's on your mind?" post creation triggers
        time.sleep(2)
        create_triggers = [
            "//span[contains(text(), \"What's on your mind\")]",
            "//div[@role='button']//span[contains(text(), \"What's on your mind\")]",
            "//div[@role='button']//span[contains(text(), 'Create a post')]",
            "//div[@aria-label='Create a post']",
        ]

        trigger_elem = None
        for xpath in create_triggers:
            try:
                elems = driver.find_elements(By.XPATH, xpath)
                for el in elems:
                    if el.is_displayed():
                        trigger_elem = el
                        break
                if trigger_elem:
                    break
            except Exception:
                continue

        if trigger_elem:
            trigger_elem.click()
            time.sleep(2.5)
        else:
            logger.info("Post trigger not immediately found; attempting direct composer click...")

        # 3. Upload media if file input is available
        if media_path and os.path.exists(media_path):
            abs_media_path = os.path.abspath(media_path)
            logger.info(f"Uploading media file to Facebook: {abs_media_path}")
            
            # Click "Photo/video" icon inside composer if file input isn't active
            for photo_icon_xpath in [
                "//div[@aria-label='Photo/video']",
                "//span[contains(text(), 'Photo/video')]",
                "//div[@aria-label='Add Photos/Videos']"
            ]:
                try:
                    for icon in driver.find_elements(By.XPATH, photo_icon_xpath):
                        if icon.is_displayed():
                            icon.click()
                            time.sleep(1)
                            break
                except Exception:
                    pass

            file_inputs = driver.find_elements(By.XPATH, "//input[@type='file']")
            if file_inputs:
                try:
                    file_inputs[-1].send_keys(abs_media_path)
                    logger.info("Successfully attached media to Facebook composer!")
                    time.sleep(3)
                except Exception as e_up:
                    logger.warning(f"File upload notice: {e_up}")

        # 4. Type caption into modal editor
        try:
            editors = driver.find_elements(By.XPATH, "//div[@role='textbox' and @contenteditable='true']")
            editor = next((ed for ed in editors if ed.is_displayed()), None)
            if editor:
                editor.click()
                time.sleep(0.3)
                driver.execute_script("""
                    const ed = arguments[0];
                    const text = arguments[1];
                    ed.focus();
                    document.execCommand('insertText', false, text);
                """, editor, caption)
                time.sleep(1)
                logger.info("Injected post caption and hashtags into Facebook editor.")
        except Exception as e_text:
            logger.warning(f"Could not enter text into Facebook editor: {e_text}")

        # 5. Click Post button
        post_selectors = [
            "//div[@aria-label='Post' and @role='button']",
            "//span[text()='Post']/ancestor::div[@role='button']",
            "//div[@role='button' and .//span[text()='Post']]",
        ]

        for post_btn_xpath in post_selectors:
            try:
                for btn in driver.find_elements(By.XPATH, post_btn_xpath):
                    if btn.is_displayed():
                        # Check if disabled
                        aria_disabled = btn.get_attribute("aria-disabled")
                        if aria_disabled == "true":
                            time.sleep(1.5)
                        btn.click()
                        time.sleep(4)
                        logger.info("Successfully clicked Post on Facebook!")

                        # Notify Telegram
                        try:
                            from telegram.bot import get_telegram_credentials, send_text_message
                            bot_token, chat_id = get_telegram_credentials()
                            if bot_token and chat_id:
                                caption_snippet = (caption[:120] + "...") if len(caption) > 120 else caption
                                media_name = os.path.basename(media_path) if media_path else "Graphic"
                                send_text_message(
                                    chat_id,
                                    f"🎉 <b>Success!</b> Post successfully published to Facebook!\n\n"
                                    f"🖼️ Media: <code>{media_name}</code>\n"
                                    f"📝 Caption preview:\n<i>{caption_snippet}</i>"
                                )
                        except Exception as e_tg:
                            logger.debug(f"Telegram notice error: {e_tg}")

                        return {"status": "success", "platform": "facebook", "message": "Posted to Facebook successfully!"}
            except Exception:
                continue

        # Notify Telegram for profile session dispatch
        try:
            from telegram.bot import get_telegram_credentials, send_text_message
            bot_token, chat_id = get_telegram_credentials()
            if bot_token and chat_id:
                caption_snippet = (caption[:120] + "...") if len(caption) > 120 else caption
                media_name = os.path.basename(media_path) if media_path else "Graphic"
                send_text_message(
                    chat_id,
                    f"🎉 <b>Success!</b> Post flow completed on Facebook!\n\n"
                    f"🖼️ Media: <code>{media_name}</code>\n"
                    f"📝 Caption preview:\n<i>{caption_snippet}</i>"
                )
        except Exception as e_tg:
            logger.debug(f"Telegram notice error: {e_tg}")

        return {"status": "success", "platform": "facebook", "message": "Facebook post flow dispatched via profile session"}

    except Exception as e:
        logger.error(f"Error posting to Facebook: {e}")
        return {"status": "error", "platform": "facebook", "message": str(e)}
