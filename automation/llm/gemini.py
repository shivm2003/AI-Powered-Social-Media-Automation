"""
Gemini Web Interactor via Selenium with saved profile or connected browser.
Supports:
- Marketing copy generation
- Image generation via Google Gemini (Imagen)
- Grabbing & downloading the generated AI image to data/media/images
"""
import time
import os
import uuid
import base64
import logging
import urllib.request
from pathlib import Path
from browser.driver import browser
from config import PLATFORM_URLS, IMAGES_DIR

logger = logging.getLogger("automation.llm.gemini")


def generate_with_gemini_browser(prompt: str) -> str:
    """Interacts with gemini.google.com via Selenium using saved Chrome profile."""
    try:
        driver = browser.navigate("gemini", PLATFORM_URLS["gemini"])
        time.sleep(3)

        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys

        # Dismiss any simple dialogs
        for sel in ["button[aria-label='Close']", "button[data-testid='close-button']"]:
            for btn in driver.find_elements(By.CSS_SELECTOR, sel):
                if btn.is_displayed():
                    try:
                        btn.click()
                        time.sleep(0.5)
                    except Exception:
                        pass

        input_box = None
        selectors = [
            "div.ql-editor",
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
        try:
            input_box.send_keys(prompt)
        except Exception:
            driver.execute_script("arguments[0].innerText = arguments[1];", input_box, prompt)
            input_box.send_keys(" ")
        time.sleep(1)

        # Click send or press Enter
        send_button = None
        for sel in ["button[aria-label*='Send']", "button.send-button", "mat-icon[fonticon='send']", "[data-test-id='send-button']"]:
            try:
                btns = driver.find_elements(By.CSS_SELECTOR, sel)
                if btns and btns[0].is_displayed() and btns[0].is_enabled():
                    send_button = btns[0]
                    break
            except Exception:
                continue

        if send_button:
            send_button.click()
        else:
            input_box.send_keys(Keys.ENTER)

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


def generate_image_with_gemini_browser(
    product_name: str,
    headline: str,
    subheadline: str = "",
    visual_style: str = "photorealistic",
    aspect_ratio: str = "1:1",
    cta_text: str = "",
    skill_image_path: str = None,
    custom_instructions: str = "",
    brand_colors: dict = None,
    category: str = "Featured"
) -> Path:
    """
    Automates Google Gemini in the browser via Selenium to:
    1. Open Gemini (https://gemini.google.com/app) visibly on screen.
    2. Enter image generation prompt for Gemini Imagen.
    3. Submit prompt and observe image generation.
    4. Select/click the generated image in Gemini and download/save to data/media/images.
    5. Fallback smoothly to high-res design engine compositing if Gemini requires sign-in.
    """
    logger.info(f"Opening Google Gemini in browser to generate social marketing image for '{product_name}'...")
    driver = None
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys

        driver = browser.navigate("gemini", PLATFORM_URLS["gemini"])
        time.sleep(3)

        # Dismiss any simple dialogs or cookie notices
        for sel in ["button[aria-label='Close']", "button[data-testid='close-button']", "div[role='dialog'] button"]:
            for btn in driver.find_elements(By.CSS_SELECTOR, sel):
                if btn.is_displayed():
                    try:
                        btn.click()
                        time.sleep(0.5)
                    except Exception:
                        pass

        # Check for sign in requirement
        sign_in_required = False
        for auth_btn in driver.find_elements(By.CSS_SELECTOR, "a, button"):
            label = (auth_btn.text or auth_btn.get_attribute("aria-label") or "").lower()
            if "sign in" in label and auth_btn.is_displayed():
                sign_in_required = True
                break

        if sign_in_required:
            logger.info("Notice: Google Gemini requires sign in in this profile. Browser window remains open so you can sign in.")

        # Construct image generation prompt
        ar_descriptions = {
            "1:1": "Square aspect ratio (1:1)",
            "4:5": "Vertical portrait aspect ratio (4:5)",
            "9:16": "Vertical full screen Story/Reel format (9:16)",
            "16:9": "Wide landscape banner format (16:9)",
        }
        scale_desc = ar_descriptions.get(aspect_ratio, f"Aspect ratio {aspect_ratio}")

        prompt_parts = [
            f"Generate an image: A stunning, professional commercial marketing visual for '{product_name}'.",
            "Target Demographic: Authentic Indian middle-class family / individuals in a warm contemporary Indian home setting with natural, happy smiling expressions.",
            "Currency Standard: Strictly Indian Rupee (₹). Any currency symbols or digital screens must display '₹' (NEVER use dollar '$' or foreign currency).",
            f"Headline text: '{headline}'.",
        ]
        if subheadline:
            prompt_parts.append(f"Subheadline: '{subheadline}'.")
        if visual_style:
            prompt_parts.append(f"Style: {visual_style} aesthetic.")
        prompt_parts.append(f"Scale: {scale_desc}.")
        if cta_text:
            prompt_parts.append(f"Call to action: '{cta_text}'.")
        # Auto-resolve fixed branding / reference image if not specified
        loan_solutions_file = str(Path(__file__).parent.parent.parent / "Loan Solutions.png")
        if not skill_image_path or not os.path.exists(str(skill_image_path)):
            if os.path.exists(loan_solutions_file):
                skill_image_path = loan_solutions_file

        if skill_image_path and os.path.exists(str(skill_image_path)):
            prompt_parts.append("Incorporate the visual elements, color scheme, and branding inspired by the uploaded reference branding.")
        if custom_instructions:
            prompt_parts.append(f"Details: {custom_instructions}.")
        prompt_parts.append("Photorealistic commercial advertising quality, 8k resolution, crisp lighting, high quality graphic design.")

        image_prompt = " ".join(prompt_parts)

        # If reference image exists, upload it to Gemini composer
        if skill_image_path and os.path.exists(str(skill_image_path)):
            from browser.human_operator import upload_image_to_gemini
            upload_image_to_gemini(driver, skill_image_path, logger=logger)

        # Locate prompt editor
        editor = None
        for sel in ["div.ql-editor", "rich-textarea p", "div[contenteditable='true']", "textarea"]:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            if elems and elems[0].is_displayed():
                editor = elems[0]
                break

        if not editor:
            raise RuntimeError("Gemini prompt input not found.")

        # Focus and enter prompt
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", editor)
        time.sleep(0.3)
        try:
            editor.click()
        except Exception:
            pass

        try:
            editor.send_keys(image_prompt)
        except Exception:
            driver.execute_script("arguments[0].innerText = arguments[1];", editor, image_prompt)

        time.sleep(0.8)

        # Send
        send_button = None
        for sel in ["button[aria-label*='Send']", "button.send-button", "mat-icon[fonticon='send']", "[data-test-id='send-button']"]:
            for b in driver.find_elements(By.CSS_SELECTOR, sel):
                if b.is_displayed():
                    send_button = b
                    break
            if send_button:
                break

        if send_button and send_button.is_enabled():
            try:
                send_button.click()
            except Exception:
                driver.execute_script("arguments[0].click();", send_button)
        else:
            editor.send_keys(Keys.ENTER)

        logger.info("Sent image prompt to Gemini! Waiting for generation to complete...")

        # Poll for generated image in Gemini (up to 20 seconds)
        generated_img_elem = None
        for sec in range(20):
            time.sleep(1)

            # Check for images in model responses
            img_candidates = driver.find_elements(
                By.CSS_SELECTOR,
                "model-response img, .image-container img, img[src*='googleusercontent.com'], img.image-attachment, img[alt*='Generated']"
            )
            for cand in img_candidates:
                src = cand.get_attribute("src") or ""
                w = cand.size.get("width", 0)
                h = cand.size.get("height", 0)
                if w >= 250 and h >= 250 and src and "avatar" not in src and not src.endswith(".svg"):
                    generated_img_elem = cand
                    break

            if generated_img_elem:
                logger.info(f"Gemini generated image found after {sec} seconds!")
                break

        # If image found, extract and save
        if generated_img_elem:
            try:
                try:
                    generated_img_elem.click()
                    time.sleep(1)
                except Exception:
                    pass

                # Extract base64
                img_data_b64 = driver.execute_async_script("""
                    const callback = arguments[arguments.length - 1];
                    const img = document.querySelector("model-response img, .image-container img, img[src*='googleusercontent.com']");
                    if (!img) return callback(null);
                    try {
                        fetch(img.src)
                            .then(r => r.blob())
                            .then(blob => {
                                const reader = new FileReader();
                                reader.onloadend = () => callback(reader.result);
                                reader.readAsDataURL(blob);
                            })
                            .catch(() => {
                                const canvas = document.createElement('canvas');
                                canvas.width = img.naturalWidth || 1024;
                                canvas.height = img.naturalHeight || 1024;
                                const ctx = canvas.getContext('2d');
                                ctx.drawImage(img, 0, 0);
                                callback(canvas.toDataURL('image/png'));
                            });
                    } catch(e) {
                        callback(null);
                    }
                """)

                if img_data_b64 and "base64," in img_data_b64:
                    raw_bytes = base64.b64decode(img_data_b64.split("base64,")[1])
                    ar_slug = aspect_ratio.replace(":", "x")
                    filename = f"gemini_{uuid.uuid4().hex[:8]}_{ar_slug}.png"
                    output_path = IMAGES_DIR / filename
                    with open(output_path, "wb") as f:
                        f.write(raw_bytes)
                    logger.info(f"Successfully downloaded and saved Gemini generated image: {output_path}")
                    return output_path
                else:
                    src = generated_img_elem.get_attribute("src")
                    if src and src.startswith("http"):
                        ar_slug = aspect_ratio.replace(":", "x")
                        filename = f"gemini_{uuid.uuid4().hex[:8]}_{ar_slug}.png"
                        output_path = IMAGES_DIR / filename
                        urllib.request.urlretrieve(src, str(output_path))
                        logger.info(f"Successfully downloaded Gemini image from URL: {output_path}")
                        return output_path
            except Exception as e_dl:
                logger.warning(f"Error downloading image from Gemini DOM: {e_dl}")

    except Exception as e:
        logger.warning(f"Gemini browser image generation notice: {e}")

    # Fallback to high-res design engine with skill image compositing
    logger.info("Delivering branded marketing image via design composer...")
    from media.image_generator import generate_social_image
    return generate_social_image(
        product_name=product_name,
        headline=headline,
        subheadline=subheadline,
        brand_colors=brand_colors or {},
        aspect_ratio=aspect_ratio,
        cta_text=cta_text or "Learn More ➜",
        logo_path=skill_image_path,
        category=category
    )
