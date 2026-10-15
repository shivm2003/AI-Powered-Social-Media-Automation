"""
End-to-end Human-Like Workflow:
1. Open Chrome like human & select profile (Shivam Mishra).
2. Open ChatGPT like human.
3. Give prompt for image generation like human (natural typing cadence).
4. Wait for image generation.
5. Download the generated image.
6. Share image and captions for post in Telegram for approval.
"""
import os
import sys
import time
import random
import json
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
    upload_image_to_chatgpt,
    human_type,
    human_sleep,
    TARGET_NAME,
    TARGET_EMAIL,
)
from telegram.bot import send_preview_to_telegram, get_telegram_credentials
from media.image_generator import generate_social_image


def run_chatgpt_human_image_and_telegram(custom_product=None):
    print("=" * 70)
    print("🚀 STARTING HUMAN-LIKE CHATGPT IMAGE GENERATION & TELEGRAM FLOW")
    print("=" * 70)

    # ── Step 1: Open Chrome like human ──
    print("\n🌐 Step 1: Opening Chrome like human...")
    step1_click_and_launch_chrome(target_url="https://chatgpt.com")
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

    # ── Step 3: Open ChatGPT like human ──
    print("\n🤖 Step 3: Navigating to ChatGPT like human...")
    chatgpt_handle = None
    for h in driver.window_handles:
        try:
            driver.switch_to.window(h)
            if "chatgpt.com" in driver.current_url:
                chatgpt_handle = h
                break
        except Exception:
            continue

    if not chatgpt_handle:
        print("Opening new ChatGPT tab...")
        driver.get("https://chatgpt.com")
    else:
        print(f"Switched to active ChatGPT tab ({driver.title})")

    from browser.driver import refresh_and_ensure_fresh
    refresh_and_ensure_fresh(driver, platform_name="ChatGPT")

    # Dismiss any dialogs/banners
    for sel in ["button[aria-label='Close']", "button[data-testid='close-button']", "div[role='dialog'] button"]:
        for btn in driver.find_elements(By.CSS_SELECTOR, sel):
            if btn.is_displayed():
                try:
                    btn.click()
                    human_sleep(0.3, 0.6)
                except Exception:
                    pass

    # ── Step 4: Give prompt for image generation like human ──
    print("\n✍️ Step 4: Locating prompt input and typing prompt like a human...")
    input_box = None
    input_selectors = [
        "div.ProseMirror",
        "div[contenteditable='true']",
        "#prompt-textarea",
        "textarea",
    ]
    for sel in input_selectors:
        for el in driver.find_elements(By.CSS_SELECTOR, sel):
            if el.is_displayed():
                input_box = el
                break
        if input_box:
            break

    if not input_box:
        raise RuntimeError("Could not find ChatGPT input box.")

    # Human click
    try:
        input_box.click()
    except Exception:
        ActionChains(driver).move_to_element(input_box).pause(0.2).click().perform()
    human_sleep(0.5, 1.0)

    # Construct prompt divided into Task 1 and Task 2 given all at once
    product_name = (custom_product or {}).get("name", "Loan Solutions")
    loan_solutions_file = str(BASE_DIR / "Loan Solutions.png")

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

    # ── Step 4A: Verify and ensure prompt is properly pasted FIRST via PromptPasteVerifierAgent ──
    from llm.prompt_paste_verifier_agent import PromptPasteVerifierAgent
    verifier_agent = PromptPasteVerifierAgent(driver)

    print(f"🤖 Step 4: Engaging PromptPasteVerifierAgent to verify & paste prompt properly ({len(prompt_text)} chars)...", flush=True)
    paste_res = verifier_agent.ensure_properly_pasted(
        driver=driver,
        prompt=prompt_text,
        platform="chatgpt",
        required_substrings=[
            "TASK 1",
            "TASK 2",
            "Loan Solutions",
            "₹",
            "https://loansolutions.everythingrental.in/application"
        ]
    )
    print(f"✅ Step 4A Complete: Prompt paste status: {paste_res.status} ({paste_res.similarity_ratio*100:.1f}% match, {paste_res.actual_length} chars). Method: {paste_res.method_used}", flush=True)
    human_sleep(0.5, 1.0)

    # ── Step 4B: Attach reference image to ChatGPT composer safely AFTER prompt is verified in place ──
    if os.path.exists(loan_solutions_file):
        print(f"📎 Attaching reference image to ChatGPT composer: {os.path.basename(loan_solutions_file)}...", flush=True)
        upload_image_to_chatgpt(driver, loan_solutions_file)
        human_sleep(1.0, 1.8)

    # ── Step 4C: Wait for Send button to become ready and click Send ──
    for _ in range(12):
        send_ready, send_details = verifier_agent.inspect_send_button(driver, "chatgpt")
        if send_ready:
            break
        time.sleep(0.5)

    send_success = verifier_agent.click_send(driver=driver, platform="chatgpt")
    if not send_success:
        input_box.send_keys(Keys.ENTER)
    human_sleep(1.0, 1.5)

    # ── Step 5: Wait for image generation like human ──
    print("\n⏳ Step 5: Waiting for ChatGPT to generate image & caption (polling up to 90s)...")
    generated_img_elem = None
    generated_text = ""
    poll_start = time.time()
    max_wait = 90

    while time.time() - poll_start < max_wait:
        time.sleep(3)
        elapsed = int(time.time() - poll_start)
        print(f"  ... observing ChatGPT response stream ({elapsed}s elapsed)")

        # Check for assistant messages
        assistants = driver.find_elements(
            By.CSS_SELECTOR,
            "article, div[data-message-author-role='assistant'], [data-message-id]"
        )
        if assistants:
            last_ast = assistants[-1]
            txt = last_ast.text.strip()
            if txt and len(txt) > 30:
                generated_text = txt

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
                    reader.onloadend = () => callback({ data: reader.result, width: target.naturalWidth, height: target.naturalHeight, alt: target.alt });
                    reader.readAsDataURL(blob);
                })
                .catch(() => {
                    try {
                        const canvas = document.createElement('canvas');
                        canvas.width = target.naturalWidth || 1024;
                        canvas.height = target.naturalHeight || 1024;
                        const ctx = canvas.getContext('2d');
                        ctx.drawImage(target, 0, 0);
                        callback({ data: canvas.toDataURL('image/png'), width: canvas.width, height: canvas.height, alt: target.alt });
                    } catch(e) {
                        callback(null);
                    }
                });
        """)

        if img_info and img_info.get("data"):
            print(f"🎉 Generated image detected ({img_info.get('width')}x{img_info.get('height')}) after {elapsed}s!", flush=True)
            data_b64 = img_info["data"]
            if "base64," in data_b64:
                raw_bytes = base64.b64decode(data_b64.split("base64,")[1])
                output_dir = BASE_DIR / "data" / "media" / "images"
                output_dir.mkdir(parents=True, exist_ok=True)
                filename = f"chatgpt_generated_{int(time.time())}.png"
                target_file = output_dir / filename
                with open(target_file, "wb") as f:
                    f.write(raw_bytes)
                downloaded_path = target_file
                print(f"✅ Successfully downloaded ChatGPT image ({len(raw_bytes):,} bytes) -> {target_file}", flush=True)
                break

        # Check if generation finished with a text-only or limit notice
        for dlg in driver.find_elements(By.CSS_SELECTOR, "div[role='dialog']"):
            if "limit" in dlg.text.lower() or "upgrade" in dlg.text.lower():
                print(f"Notice: ChatGPT daily limit reached: {dlg.text[:80]}")
                break

    # ── Step 6: Verify Downloaded Image ──
    print("\n📥 Step 6: Verifying downloaded image...", flush=True)

    # If ChatGPT had a limit or fallback is needed
    if not downloaded_path or not downloaded_path.exists():
        print("Synthesizing branded high-res visual graphic for post...")
        downloaded_path = generate_social_image(
            product_name=product_name,
            headline=f"Automate Social Media with AI",
            subheadline="Create, Schedule & Publish Across Facebook, Instagram & LinkedIn",
            brand_colors={"primary": "#7C5CFC", "secondary": "#3DD6D0", "accent": "#FFB347"},
            aspect_ratio="1:1",
            cta_text="Get Started Free ➜",
            category="SaaS / AI Tools"
        )
        print(f"✅ High-converting image ready -> {downloaded_path}")

    # If ChatGPT only produced the image and stopped, prompt Task 2 (marketing post)
    if not generated_text or len(generated_text) < 40:
        print("\n✍️ Prompting ChatGPT for Task 2: Writing complete marketing caption & hashtags...")
        try:
            task2_box = None
            for sel in ["div.ProseMirror", "#prompt-textarea", "div[contenteditable='true']", "textarea"]:
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
                    f"Now write the complete social media post for '{product_name}'. "
                    "Include a compelling Headline, an engaging 2-3 paragraph marketing copy with call-to-action, "
                    "and 5-6 viral hashtags."
                )
                driver.execute_script("""
                    const ed = arguments[0];
                    ed.focus();
                    document.execCommand('selectAll', false, null);
                    document.execCommand('insertText', false, arguments[1]);
                    ed.dispatchEvent(new Event('input', { bubbles: true }));
                """, task2_box, task2_text)
                human_sleep(0.4, 0.8)

                send_btn2 = None
                for s in ["button[data-testid='send-button']", "button[aria-label*='Send']"]:
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

                # Wait for ChatGPT to stream caption
                print("Waiting for ChatGPT to write post caption...")
                for _ in range(8):
                    time.sleep(2)
                    asts = driver.find_elements(By.CSS_SELECTOR, "article, div[data-message-author-role='assistant'], [data-message-id]")
                    if asts:
                        lt = asts[-1].text.strip()
                        if lt and len(lt) > 50 and "now write" not in lt.lower()[:30]:
                            generated_text = lt
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

    import uuid
    campaign_id = str(uuid.uuid4())
    tg_res = send_preview_to_telegram(
        campaign_id=campaign_id,
        caption=caption_body,
        media_path=str(downloaded_path) if downloaded_path else "",
        platforms=["Facebook", "Instagram", "LinkedIn"],
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
    run_chatgpt_human_image_and_telegram()
