"""
ChatGPT Web Interactor via Selenium with saved profile or connected browser.
Supports:
- Marketing copy generation
- Image generation via DALL-E / ChatGPT image tool
- Selecting & uploading skill/product reference images
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

logger = logging.getLogger("automation.llm.chatgpt")


def generate_with_chatgpt_browser(prompt: str) -> str:
    """Interacts with chatgpt.com via Selenium to generate text content."""
    try:
        driver = browser.navigate("chatgpt", PLATFORM_URLS["chatgpt"])
        time.sleep(3)

        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys

        # Dismiss any simple onboarding/cookie dialogs
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
            "#prompt-textarea",
            "textarea[data-id='root']",
            "div[contenteditable='true']",
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
            raise RuntimeError("Could not locate ChatGPT prompt textarea. User may need to sign in first.")

        # Verify and paste prompt via PromptPasteVerifierAgent
        from .prompt_paste_verifier_agent import PromptPasteVerifierAgent
        verifier_agent = PromptPasteVerifierAgent(driver)
        paste_res = verifier_agent.ensure_properly_pasted(
            driver=driver,
            prompt=prompt,
            platform="chatgpt"
        )
        logger.info(f"ChatGPT prompt paste verification status: {paste_res.status} ({paste_res.similarity_ratio*100:.1f}%)")
        time.sleep(0.5)

        # Click send or press Enter via agent
        verifier_agent.click_send(driver=driver, platform="chatgpt")

        logger.info("Waiting for ChatGPT response...")
        time.sleep(8)

        for sel in ["div[data-message-author-role='assistant']", ".markdown", "article"]:
            try:
                responses = driver.find_elements(By.CSS_SELECTOR, sel)
                if responses:
                    return responses[-1].text
            except Exception:
                continue

        return "Generated response from ChatGPT."
    except Exception as e:
        logger.warning(f"Browser interaction with ChatGPT text generation notice: {e}")
        raise


def generate_image_with_chatgpt_browser(
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
    Automates ChatGPT in the browser via Selenium to:
    1. Open ChatGPT (https://chatgpt.com) visibly on screen.
    2. Attach/select skill image if provided.
    3. Invoke image generation skill/tool.
    4. Type detailed prompt for DALL-E / ChatGPT.
    5. Submit prompt and observe image generation.
    6. Select/click the generated image in ChatGPT and download/save it.
    7. Fallback smoothly to high-res Pillow compositing if ChatGPT requires login or times out.
    """
    logger.info(f"Opening ChatGPT in browser to generate social marketing image for '{product_name}'...")
    driver = None
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys

        driver = browser.navigate("chatgpt", PLATFORM_URLS["chatgpt"])
        time.sleep(3)

        # 1. Dismiss any overlay popups/dialogs
        for sel in ["button[aria-label='Close']", "button[data-testid='close-button']", "div[role='dialog'] button"]:
            for btn in driver.find_elements(By.CSS_SELECTOR, sel):
                if btn.is_displayed():
                    try:
                        btn.click()
                        time.sleep(0.5)
                    except Exception:
                        pass

        # 2. Construct high-impact image generation prompt
        ar_descriptions = {
            "1:1": "Square aspect ratio (1:1)",
            "4:5": "Vertical portrait aspect ratio (4:5)",
            "9:16": "Vertical full screen Story/Reel format (9:16)",
            "16:9": "Wide landscape banner format (16:9)",
        }
        scale_desc = ar_descriptions.get(aspect_ratio, f"Aspect ratio {aspect_ratio}")

        prompt_parts = [
            f"Create an image: A stunning, professional commercial social media marketing graphic for '{product_name}'.",
            f"Headline text: '{headline}'.",
        ]
        if subheadline:
            prompt_parts.append(f"Subheadline: '{subheadline}'.")
        if visual_style:
            prompt_parts.append(f"Style: {visual_style} aesthetic.")
        prompt_parts.append(f"Scale: {scale_desc}.")
        if cta_text:
            prompt_parts.append(f"Call to action: '{cta_text}'.")
        if skill_image_path:
            prompt_parts.append("Incorporate the visual elements, color scheme, and branding from the attached skill reference image.")
        if custom_instructions:
            prompt_parts.append(f"Details: {custom_instructions}.")
        prompt_parts.append("Photorealistic commercial quality, 8k resolution, vibrant lighting, modern advertising layout.")

        image_prompt = " ".join(prompt_parts)

        # 3. Locate textarea and paste/verify prompt FIRST
        textarea = None
        for sel in ["#prompt-textarea", "textarea", "div[contenteditable='true']"]:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            if elems and elems[0].is_displayed():
                textarea = elems[0]
                break

        if not textarea:
            raise RuntimeError("ChatGPT prompt textarea not found.")

        # Focus and verify/paste prompt via PromptPasteVerifierAgent
        from .prompt_paste_verifier_agent import PromptPasteVerifierAgent
        verifier_agent = PromptPasteVerifierAgent(driver)
        paste_res = verifier_agent.ensure_properly_pasted(
            driver=driver,
            prompt=image_prompt,
            platform="chatgpt",
            required_substrings=[product_name]
        )
        logger.info(f"ChatGPT image prompt paste status: {paste_res.status} ({paste_res.similarity_ratio*100:.1f}%)")
        time.sleep(0.5)

        # 4. If skill/product reference image is provided, upload it safely AFTER prompt is in place
        if skill_image_path and os.path.exists(skill_image_path):
            abs_image_path = os.path.abspath(skill_image_path)
            logger.info(f"Selecting and attaching skill image to ChatGPT: {abs_image_path}")
            try:
                from browser.human_operator import upload_image_to_chatgpt
                upload_image_to_chatgpt(driver, abs_image_path, logger=logger)
                time.sleep(1.5)
            except Exception as e_upload:
                logger.warning(f"Could not attach skill image to ChatGPT file input: {e_upload}")

        # 5. Wait for Send button to be ready and click Send
        for _ in range(12):
            send_ready, send_details = verifier_agent.inspect_send_button(driver, "chatgpt")
            if send_ready:
                break
            time.sleep(0.5)

        send_success = verifier_agent.click_send(driver=driver, platform="chatgpt")
        if not send_success:
            textarea.send_keys(Keys.ENTER)
        logger.info("Sent image generation prompt and image to ChatGPT! Waiting for generation to complete...")

        # 6. Wait for ChatGPT to generate the image (polling up to 20 seconds)
        generated_img_elem = None
        login_required = False

        for sec in range(20):
            time.sleep(1)

            # Fast check if login modal or message appeared
            for dlg in driver.find_elements(By.CSS_SELECTOR, "div[role='dialog'], [data-state='open']"):
                if dlg.is_displayed() and ("log in" in dlg.text.lower() or "sign up" in dlg.text.lower()):
                    login_required = True
                    break

            if login_required:
                logger.warning("ChatGPT indicated that login is required to generate images via DALL-E.")
                break

            assistants = driver.find_elements(By.CSS_SELECTOR, "div[data-message-author-role='assistant'], article, [data-message-id]")
            for ast in assistants:
                txt = ast.text.lower()
                if "log in" in txt and ("image" in txt or "create" in txt):
                    login_required = True
                    break
            if login_required:
                logger.warning("ChatGPT indicated that login is required to generate images via DALL-E.")
                break

            # Check for generated image via JS detection that handles blob:, DALL-E, and new ChatGPT DOM
            img_info = driver.execute_async_script("""
                const callback = arguments[arguments.length - 1];
                const images = Array.from(document.querySelectorAll('img'));
                const target = images.find(img => {
                    const alt = (img.alt || '').toLowerCase();
                    const src = (img.src || '').toLowerCase();
                    const isNotAttachment = !alt.includes('attachment') && !src.includes('avatar') && !src.includes('auth0');
                    const isBig = (img.naturalWidth >= 300 || img.clientWidth >= 250);
                    if (!isNotAttachment || !isBig) return false;
                    if (alt.includes('generated')) return true;
                    if (src.startsWith('blob:') && img.naturalWidth >= 400) return true;
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
            """)

            if img_info and img_info.get("data"):
                data_b64 = img_info["data"]
                if "base64," in data_b64:
                    raw_bytes = base64.b64decode(data_b64.split("base64,")[1])
                    ar_slug = aspect_ratio.replace(":", "x")
                    filename = f"chatgpt_{uuid.uuid4().hex[:8]}_{ar_slug}.png"
                    output_path = IMAGES_DIR / filename
                    with open(output_path, "wb") as f:
                        f.write(raw_bytes)
                    logger.info(f"Successfully downloaded and saved ChatGPT generated image ({len(raw_bytes):,} bytes): {output_path}")
                    return output_path

        if login_required:
            logger.info("Notice: ChatGPT browser window remains open so you can log in once. Using branded design engine for this draft.")

    except Exception as e:
        logger.warning(f"ChatGPT browser image generation notice: {e}")

    # Fallback: high-res Pillow template engine with skill_image_path / logo compositing
    logger.info("Generating high-converting social marketing image with design composer...")
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
