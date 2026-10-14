"""
End-to-end Human-Like Workflow for Google Gemini:
1. Open Chrome like human & select profile (Shivam Mishra - 2003shivam1990@gmail.com).
2. Open Google Gemini (gemini.google.com/app) like human.
3. Give prompt divided into Task 1 (Image) and Task 2 (Post Copy) ALL AT ONCE.
4. Wait for Gemini Imagen image generation and marketing copy.
5. Download the generated image cleanly to disk.
6. Share image and captions for post in Telegram with interactive approval buttons.
"""
import os
import sys
import time
import random
import json
import uuid
import base64
import urllib.request
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add automation directory to path
BASE_DIR = Path(__file__).parent.parent
sys.path.append(str(BASE_DIR / "automation"))

import config
from browser.human_operator import (
    step1_click_and_launch_chrome,
    step2_select_shivam_account,
    human_type,
    human_sleep,
    TARGET_NAME,
    TARGET_EMAIL,
)
from telegram.bot import send_preview_to_telegram, get_telegram_credentials
from media.image_generator import generate_social_image


def run_gemini_human_image_and_telegram(custom_product=None):
    print("=" * 70)
    print("🚀 STARTING HUMAN-LIKE GEMINI IMAGE GENERATION & TELEGRAM FLOW")
    print("=" * 70)

    # ── Step 1: Open Chrome like human ──
    print("\n🌐 Step 1: Opening Chrome like human...")
    step1_click_and_launch_chrome(target_url="https://gemini.google.com/app")
    print("✅ Step 1 Complete: Chrome is open and connected on port 9222.")

    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as SeleniumOptions
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains

    opts = SeleniumOptions()
    opts.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=opts)

    # ── Step 2: Select profile ──
    print(f"\n👤 Step 2: Selecting profile {TARGET_NAME} ({TARGET_EMAIL})...")
    step2_select_shivam_account(driver)
    print(f"✅ Step 2 Complete: Profile confirmed ({TARGET_NAME}).")

    # ── Step 3: Open Gemini like human ──
    print("\n♊ Step 3: Navigating to Google Gemini like human...")
    gemini_handle = None
    for h in driver.window_handles:
        try:
            driver.switch_to.window(h)
            if "gemini.google.com" in driver.current_url:
                gemini_handle = h
                break
        except Exception:
            continue

    if not gemini_handle:
        print("Opening new Gemini tab...")
        driver.get("https://gemini.google.com/app")
    else:
        print(f"Switched to active Gemini tab ({driver.title})")

    from browser.driver import refresh_and_ensure_fresh
    refresh_and_ensure_fresh(driver, platform_name="Gemini")

    # Dismiss any dialogs/banners
    for sel in [
        "button[aria-label='Close']",
        "button[data-testid='close-button']",
        "button[aria-label='Dismiss']",
        "div[role='dialog'] button"
    ]:
        for btn in driver.find_elements(By.CSS_SELECTOR, sel):
            if btn.is_displayed():
                try:
                    btn.click()
                    human_sleep(0.3, 0.6)
                except Exception:
                    pass

    # ── Step 4: Locate input box & Give prompt divided into Task 1 & Task 2 ALL AT ONCE ──
    print("\n✍️ Step 4: Locating Gemini prompt input...")
    input_box = None
    input_selectors = [
        "div.ql-editor",
        "rich-textarea p",
        "rich-textarea div[contenteditable='true']",
        "div[contenteditable='true']",
        "textarea.ql-editor",
        "textarea",
    ]
    for _ in range(12):
        for sel in input_selectors:
            for el in driver.find_elements(By.CSS_SELECTOR, sel):
                if el.is_displayed():
                    input_box = el
                    break
            if input_box:
                break
        if input_box:
            break
        time.sleep(1)

    if not input_box:
        raise RuntimeError("Could not find Gemini prompt editor. Please verify login.")

    # Human click to focus
    try:
        input_box.click()
    except Exception:
        ActionChains(driver).move_to_element(input_box).pause(0.2).click().perform()
    human_sleep(0.5, 1.0)

    # Record existing images before submitting
    existing_imgs = driver.execute_script("""
        return Array.from(document.querySelectorAll('img'))
            .filter(img => (img.naturalWidth >= 200 || img.clientWidth >= 200))
            .map(img => img.src);
    """) or []

    # Construct prompt: Divided into Task 1 and Task 2, same as ChatGPT, given at once
    product_name = (custom_product or {}).get("name", "Loan Solutions")
    loan_solutions_file = str(BASE_DIR / "Loan Solutions.png")

    # If reference image exists (Loan Solutions), attach it to Gemini composer like human
    if os.path.exists(loan_solutions_file):
        from browser.human_operator import upload_image_to_gemini
        uploaded = upload_image_to_gemini(driver, loan_solutions_file)
        if uploaded:
            print(f"📎 Uploaded reference image to Gemini composer: {os.path.basename(loan_solutions_file)}", flush=True)
        else:
            print("⚠️ Could not attach reference image to Gemini composer", flush=True)

    prompt_text = (
        f"--- TASK 1: CLEAN VISUAL ARTWORK (IMAGE GENERATION) ---\n"
        f"Generate a clean, high-converting commercial marketing image for '{product_name}'.\n"
        "A warm, authentic, happy Indian middle-class family (smiling parents and child) sitting together joyfully on a comfortable sofa in their modern, tasteful Indian apartment living room, celebrating their new home loan approval with genuine relief and pride. "
        "Subtle glowing Indian Rupee symbol (₹) and trusted digital verification checkmark in the background, warm sunlit daylight, 1:1 square aspect ratio, 8k commercial photography resolution.\n"
        "CRITICAL RULES:\n"
        "1. Strictly use Indian Rupee (₹) standards for any currency representation. NEVER use dollar signs ($) or foreign currency.\n"
        "2. Authentic Indian demographic and relatable Indian middle-class family setting.\n"
        "3. Do NOT paint hashtags (#...), paragraphs, or long text inside the image. Keep artwork 100% clean visual art.\n\n"
        "--- TASK 2: SOCIAL MEDIA POST (IN CHAT TEXT BELOW THE IMAGE ONLY) ---\n"
        "In your chat text reply below the image only, write the complete social media post tailored for an Indian middle-class audience:\n"
        f"• Headline: A compelling, emotional hook for {product_name} celebrating family dreams, financial security, and easy approvals\n"
        "• Caption: An engaging 2-3 paragraph marketing copy highlighting trust, transparent process, low monthly EMIs in Indian Rupees (₹), quick disbursal, and a clear call-to-action.\n"
        "• Mandatory Link: End the caption with this exact application link: 👉 Apply Now: https://loansolutions.everythingrental.in/application\n"
        "• Hashtags: 5-6 viral India-relevant hashtags (e.g. #LoanSolutions #HomeLoanIndia #PersonalLoan #LowEMI #ApnaGhar #FinancialFreedom - written ONLY here in chat text, NEVER painted inside the image)."
    )

    print(f"⚡ Inserting full prompt divided into Task 1 & Task 2 ALL AT ONCE ({len(prompt_text)} chars)...", flush=True)
    driver.execute_script("""
        const ed = arguments[0];
        const text = arguments[1];
        ed.focus();
        document.execCommand('selectAll', false, null);
        document.execCommand('insertText', false, text);
        ed.dispatchEvent(new Event('input', { bubbles: true }));
        ed.dispatchEvent(new Event('change', { bubbles: true }));
    """, input_box, prompt_text)
    human_sleep(0.5, 1.0)

    # Fallback if text didn't insert via execCommand
    current_val = (input_box.text or input_box.get_attribute("innerText") or "").strip()
    if not current_val:
        try:
            driver.execute_script("arguments[0].innerText = arguments[1];", input_box, prompt_text)
            input_box.send_keys(" ")
        except Exception:
            input_box.send_keys(prompt_text)
        human_sleep(0.4, 0.8)

    # Click send button
    send_btn = None
    for sel in [
        "button[aria-label*='Send']",
        "button.send-button",
        "mat-icon[fonticon='send']",
        "[data-test-id='send-button']",
        "button[aria-label*='Submit']",
        "button[data-testid='send-button']",
    ]:
        for b in driver.find_elements(By.CSS_SELECTOR, sel):
            if b.is_displayed():
                send_btn = b
                break
        if send_btn:
            break

    if send_btn:
        try:
            send_btn.click()
        except Exception:
            driver.execute_script("arguments[0].click();", send_btn)
        print("Clicked Send button in Gemini!", flush=True)
    else:
        input_box.send_keys(Keys.ENTER)
        print("Submitted via Enter key in Gemini!", flush=True)

    # ── Step 5: Wait for Gemini to generate image and caption ──
    print("\n⏳ Step 5: Waiting for Gemini to generate image & caption (polling up to 90s)...")
    downloaded_path = None
    generated_text = ""
    poll_start = time.time()
    max_wait = 90

    while time.time() - poll_start < max_wait:
        time.sleep(3)
        elapsed = int(time.time() - poll_start)
        print(f"  ... observing Gemini response stream ({elapsed}s elapsed)")

        # Check for model text response
        for sel in ["model-response", ".model-response-text", ".response-content", "div.markdown"]:
            responses = driver.find_elements(By.CSS_SELECTOR, sel)
            if responses:
                last_txt = responses[-1].text.strip()
                if last_txt and len(last_txt) > 50 and "task 1" not in last_txt.lower()[:30]:
                    generated_text = last_txt
                    break

        # Check for generated image via JS detection handling Google Imagen
        img_info = driver.execute_async_script("""
            const existing = arguments[0] || [];
            const callback = arguments[arguments.length - 1];

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

            // Canvas-first extraction
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
            data_b64 = img_info["data"]
            if "base64," in data_b64:
                raw_bytes = base64.b64decode(data_b64.split("base64,")[1])
                is_valid = (
                    raw_bytes.startswith(b"\x89PNG") or
                    raw_bytes.startswith(b"\xff\xd8") or
                    (raw_bytes.startswith(b"RIFF") and b"WEBP" in raw_bytes[:16])
                )
                if is_valid and len(raw_bytes) > 20000:
                    output_dir = BASE_DIR / "data" / "media" / "images"
                    output_dir.mkdir(parents=True, exist_ok=True)
                    filename = f"gemini_generated_{int(time.time())}.png"
                    target_file = output_dir / filename
                    with open(target_file, "wb") as f:
                        f.write(raw_bytes)
                    downloaded_path = target_file
                    print(f"✅ Successfully downloaded Gemini image ({len(raw_bytes):,} bytes) -> {target_file}", flush=True)
                    break
                else:
                    print(f"⚠️ Extracted data was not valid image bytes (len={len(raw_bytes)}), continuing wait...", flush=True)

    # ── Step 6: Verify Downloaded Image & Prompt Task 2 if Needed ──
    print("\n📥 Step 6: Verifying downloaded image & marketing copy...", flush=True)

    # Fallback image synthesis if Gemini did not generate
    if not downloaded_path or not downloaded_path.exists():
        print("Synthesizing branded high-res visual graphic for post...")
        downloaded_path = generate_social_image(
            product_name=product_name,
            headline=f"Automate Social Media with Gemini AI",
            subheadline="Create, Schedule & Publish Across Facebook & Instagram",
            brand_colors={"primary": "#1A73E8", "secondary": "#8AB4F8", "accent": "#EA4335"},
            aspect_ratio="1:1",
            cta_text="Get Started Free ➜",
            logo_path=loan_solutions_file if os.path.exists(loan_solutions_file) else None,
            category="SaaS / AI Tools"
        )
        print(f"✅ High-converting image ready -> {downloaded_path}")

    # If Gemini produced the image and stopped without caption, prompt Task 2 in the same chat
    if not generated_text or len(generated_text) < 40:
        print("\n✍️ Prompting Gemini for Task 2: Writing complete marketing caption & hashtags...")
        try:
            task2_box = None
            for sel in input_selectors:
                for el in driver.find_elements(By.CSS_SELECTOR, sel):
                    if el.is_displayed():
                        task2_box = el
                        break
                if task2_box:
                    break

            if task2_box:
                task2_box.click()
                human_sleep(0.3, 0.6)
                task2_text = (
                    f"Now complete Task 2 for this image: Write the complete social media post for '{product_name}'. "
                    "Include a compelling Headline, an engaging 2-3 paragraph marketing copy with call-to-action, "
                    "and 5-6 viral hashtags."
                )
                driver.execute_script("""
                    const ed = arguments[0];
                    ed.focus();
                    document.execCommand('selectAll', false, null);
                    document.execCommand('insertText', false, arguments[1]);
                    ed.dispatchEvent(new Event('input', { bubbles: true }));
                    ed.dispatchEvent(new Event('change', { bubbles: true }));
                """, task2_box, task2_text)
                human_sleep(0.4, 0.8)

                send_btn2 = None
                for s in [
                    "button[aria-label*='Send']",
                    "button.send-button",
                    "mat-icon[fonticon='send']",
                    "[data-test-id='send-button']"
                ]:
                    for b in driver.find_elements(By.CSS_SELECTOR, s):
                        if b.is_displayed():
                            send_btn2 = b
                            break
                    if send_btn2:
                        break

                if send_btn2:
                    send_btn2.click()
                else:
                    task2_box.send_keys(Keys.ENTER)

                # Wait for Gemini text stream
                print("Waiting for Gemini to write post caption...")
                for _ in range(8):
                    time.sleep(2)
                    for sel in ["model-response", ".model-response-text", ".response-content", "div.markdown"]:
                        responses = driver.find_elements(By.CSS_SELECTOR, sel)
                        if responses:
                            lt = responses[-1].text.strip()
                            if lt and len(lt) > 50 and "complete task 2" not in lt.lower()[:30]:
                                generated_text = lt
                                break
                    if generated_text:
                        break
        except Exception as e_t2:
            print(f"Notice on Task 2 follow-up: {e_t2}")

    # Build clean caption
    caption_body = generated_text if len(generated_text) > 40 else (
        f"🏡 Ab har sapna hoga poora with {product_name}! 🚀\n\n"
        "Get instant loan approvals with minimal paperwork, transparent terms, and lowest monthly EMIs in Indian Rupees (₹). Whether it's your dream home, personal finance, or education, your trusted financial partner is here for your family.\n\n"
        "👉 Apply Now: https://loansolutions.everythingrental.in/application\n\n"
        "#LoanSolutions #HomeLoanIndia #PersonalLoan #LowEMI #ApnaGhar #FinancialFreedom"
    )

    # ── Step 7: Share image and captions for post in Telegram for approval ──
    print("\n📱 Step 7: Sharing image and caption to Telegram for approval...")
    bot_token, chat_id = get_telegram_credentials()
    print(f"Telegram Config: Bot Token {'Configured' if bot_token else 'Missing'}, Chat ID: {chat_id}")

    campaign_id = str(uuid.uuid4())
    tg_res = send_preview_to_telegram(
        campaign_id=campaign_id,
        caption=caption_body,
        media_path=str(downloaded_path) if downloaded_path else "",
        platforms=["Facebook", "Instagram"],
        revision_count=0,
        product_name=product_name,
        apply_url="https://loansolutions.everythingrental.in/application"
    )

    print("\n" + "=" * 70)
    if tg_res.get("status") == "success":
        print("🎉 SUCCESS! Image and captions successfully sent to Telegram!")
        print(f"Campaign ID: {campaign_id}")
        print(f"Media Path: {downloaded_path}")
        print(f"Check Telegram chat ID {chat_id} for the approval message with buttons:")
        print("  [✅ Approve & Post]  [✏️ Suggest Revision]  [📝 Apply Now 🔗]  [❌ Reject / Cancel]")
        print("  🔗 Direct Link: https://loansolutions.everythingrental.in/application")
    else:
        print(f"⚠️ Telegram notice: {tg_res}")
    print("=" * 70)

    return {
        "status": "success",
        "campaign_id": campaign_id,
        "image_path": str(downloaded_path),
        "caption": caption_body,
        "telegram_response": tg_res
    }


if __name__ == "__main__":
    run_gemini_human_image_and_telegram()
