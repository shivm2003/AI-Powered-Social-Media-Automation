"""
Robust ChatGPT image downloader & Telegram dispatcher.
Directly targets generated DALL-E/ChatGPT images (including blob: URLs).
"""
import os
import sys
import time
import base64
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = Path(__file__).parent.parent
sys.path.append(str(BASE_DIR / "automation"))

import config
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from telegram.bot import send_preview_to_telegram, get_telegram_credentials


def download_active_chatgpt_image():
    print("Connecting to Chrome on port 9222...", flush=True)
    opts = Options()
    opts.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=opts)

    # Switch to active ChatGPT window
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
        raise RuntimeError("No active ChatGPT tab found in Chrome.")

    print(f"Connected to ChatGPT: {driver.title} ({driver.current_url})", flush=True)

    # JavaScript to locate the actual generated image
    js_extract = """
    const callback = arguments[arguments.length - 1];
    
    // Find candidate images
    const images = Array.from(document.querySelectorAll('img'));
    
    // Specifically match generated images:
    // 1. alt containing 'Generated'
    // 2. Or blob: source with naturalWidth >= 400 (excluding attachments)
    // 3. Or src containing dalle / oaiusercontent
    const target = images.find(img => {
        const alt = (img.alt || '').toLowerCase();
        const src = (img.src || '').toLowerCase();
        const isNotAttachment = !alt.includes('attachment') && !src.includes('avatar');
        const isBig = (img.naturalWidth >= 300 || img.clientWidth >= 250);
        
        if (!isNotAttachment || !isBig) return false;
        
        if (alt.includes('generated')) return true;
        if (src.startsWith('blob:') && img.naturalWidth >= 400) return true;
        if (src.includes('oaidalleapiprodscus') || src.includes('files.oaiusercontent.com')) return true;
        
        return false;
    });

    if (!target) {
        return callback({ status: 'not_found', count: images.length });
    }

    // Extract via fetch / FileReader
    fetch(target.src)
        .then(res => res.blob())
        .then(blob => {
            const reader = new FileReader();
            reader.onloadend = () => {
                callback({
                    status: 'success',
                    src: target.src,
                    alt: target.alt,
                    width: target.naturalWidth,
                    height: target.naturalHeight,
                    data: reader.result
                });
            };
            reader.onerror = () => callback({ status: 'error', message: 'FileReader failed' });
            reader.readAsDataURL(blob);
        })
        .catch(err => {
            // Fallback via Canvas
            try {
                const canvas = document.createElement('canvas');
                canvas.width = target.naturalWidth || 1024;
                canvas.height = target.naturalHeight || 1024;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(target, 0, 0);
                callback({
                    status: 'success',
                    src: target.src,
                    alt: target.alt,
                    width: canvas.width,
                    height: canvas.height,
                    data: canvas.toDataURL('image/png')
                });
            } catch(canvasErr) {
                callback({ status: 'error', message: err.toString() + ' | Canvas: ' + canvasErr.toString() });
            }
        });
    """

    print("Locating and downloading generated image from page DOM...", flush=True)
    res = driver.execute_async_script(js_extract)

    if not res or res.get("status") != "success":
        print(f"Extraction result: {res}", flush=True)
        raise RuntimeError(f"Could not extract image: {res}")

    print(f"Extracted image: {res.get('width')}x{res.get('height')}, Alt: '{res.get('alt')}'", flush=True)

    data_url = res.get("data", "")
    if "base64," not in data_url:
        raise RuntimeError("No base64 image data received.")

    raw_bytes = base64.b64decode(data_url.split("base64,")[1])
    
    out_dir = BASE_DIR / "data" / "media" / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"chatgpt_generated_{int(time.time())}.png"

    with open(out_file, "wb") as f:
        f.write(raw_bytes)

    print(f"✅ Successfully downloaded ChatGPT image! ({len(raw_bytes):,} bytes) -> {out_file}", flush=True)

    # Now send to Telegram
    caption = (
        "🌟 <b>Loan Solutions — Official Social Media Post</b>\n\n"
        "Need financial flexibility? Discover customized Loan Solutions designed for your goals.\n"
        "Fast approvals, transparent terms, and dedicated support every step of the way.\n\n"
        "👉 Apply Now: https://loansolutions.everythingrental.in/application\n\n"
        "#LoanSolutions #PersonalLoans #FinancialFreedom #Fintech #SmartFinancing"
    )

    print("Dispatching real downloaded image to Telegram...", flush=True)
    import uuid
    campaign_id = str(uuid.uuid4())
    tg_res = send_preview_to_telegram(
        campaign_id=campaign_id,
        caption=caption,
        media_path=str(out_file),
        platforms=["Facebook", "Instagram", "LinkedIn"],
        revision_count=0,
        product_name="Loan Solutions",
        apply_url="https://loansolutions.everythingrental.in/application"
    )

    print(f"Telegram dispatch result: {tg_res.get('status')}", flush=True)
    if tg_res.get("status") == "success":
        print(f"🎉 Sent to Telegram chat with approve/reject buttons!", flush=True)

    return str(out_file)


if __name__ == "__main__":
    download_active_chatgpt_image()
