"""
Robust Google Gemini image downloader & Telegram dispatcher.
Directly targets generated Gemini Imagen images from active Chrome tab.
"""
import os
import sys
import time
import base64
import uuid
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


def download_active_gemini_image():
    print("Connecting to Chrome on port 9222...", flush=True)
    opts = Options()
    opts.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=opts)

    # Switch to active Gemini window
    gemini_found = False
    for h in driver.window_handles:
        try:
            driver.switch_to.window(h)
            if "gemini.google.com" in driver.current_url:
                gemini_found = True
                break
        except Exception:
            continue

    if not gemini_found:
        raise RuntimeError("No active Google Gemini tab found in Chrome.")

    print(f"Connected to Google Gemini: {driver.title} ({driver.current_url})", flush=True)

    # JavaScript to locate the actual generated image
    js_extract = """
    const callback = arguments[arguments.length - 1];
    
    // Find all images on the page in reverse order
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

        // Identify Gemini generated image
        const isGeneratedClass = cls.includes('image') && !cls.includes('preview') && !cls.includes('sparkle');
        const isGeneratedAlt = alt.includes('generated') || alt.includes('ai generated') || alt.includes('photograph') || alt.includes('commercial');
        const isBlobImg = src.startsWith('blob:') && w >= 450 && h >= 450;

        return isGeneratedClass || isGeneratedAlt || isBlobImg;
    });

    if (!target) {
        return callback({ status: 'not_found', count: allImgs.length });
    }

    // Canvas-first extraction
    try {
        const canvas = document.createElement('canvas');
        canvas.width = target.naturalWidth || 1024;
        canvas.height = target.naturalHeight || 1024;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(target, 0, 0);
        const dataUrl = canvas.toDataURL('image/png');
        if (dataUrl && dataUrl.startsWith('data:image/png;base64,iVBORw0K') && dataUrl.length > 50000) {
            return callback({
                status: 'success',
                src: target.src,
                alt: target.alt,
                width: canvas.width,
                height: canvas.height,
                data: dataUrl
            });
        }
    } catch(canvasErr) {
        // Fallback to fetch
    }

    // Extract via fetch / FileReader only if verified image blob
    fetch(target.src)
        .then(res => res.blob())
        .then(blob => {
            if (!blob.type || !blob.type.startsWith('image/')) {
                return callback({ status: 'error', message: 'Not an image: ' + blob.type });
            }
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
        .catch(err => callback({ status: 'error', message: err.toString() }));
    """

    print("Locating and downloading generated Gemini image from page DOM...", flush=True)
    res = driver.execute_async_script(js_extract)

    if not res or res.get("status") != "success":
        print(f"Extraction result: {res}", flush=True)
        raise RuntimeError(f"Could not extract Gemini image: {res}")

    print(f"Extracted image: {res.get('width')}x{res.get('height')}, Alt: '{res.get('alt')}'", flush=True)

    data_url = res.get("data", "")
    if "base64," not in data_url:
        raise RuntimeError("No base64 image data received.")

    raw_bytes = base64.b64decode(data_url.split("base64,")[1])
    is_valid = (
        raw_bytes.startswith(b"\x89PNG") or
        raw_bytes.startswith(b"\xff\xd8") or
        (raw_bytes.startswith(b"RIFF") and b"WEBP" in raw_bytes[:16])
    )
    if not is_valid or len(raw_bytes) < 20000:
        raise RuntimeError(f"Extracted payload was not valid image bytes (len={len(raw_bytes)}).")

    out_dir = BASE_DIR / "data" / "media" / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"gemini_generated_{int(time.time())}.png"

    with open(out_file, "wb") as f:
        f.write(raw_bytes)

    print(f"✅ Successfully downloaded Gemini image! ({len(raw_bytes):,} bytes) -> {out_file}", flush=True)

    # Now send to Telegram
    caption = (
        "♊ <b>AI-Powered Social Media Automation — Official Post</b>\n\n"
        "Transform your marketing pipeline with Google Gemini AI intelligence.\n"
        "Generate viral campaigns, professional visuals, and publish seamlessly.\n\n"
        "👉 <i>Get started today!</i>\n\n"
        "#GeminiAI #MarketingAutomation #SocialMediaGrowth #ContentMarketing #SmartTech"
    )

    print("Dispatching downloaded Gemini image to Telegram...", flush=True)
    campaign_id = str(uuid.uuid4())
    tg_res = send_preview_to_telegram(
        campaign_id=campaign_id,
        caption=caption,
        media_path=str(out_file),
        platforms=["Facebook", "Instagram"],
        revision_count=0
    )

    print(f"Telegram dispatch result: {tg_res.get('status')}", flush=True)
    if tg_res.get("status") == "success":
        print("🎉 Sent to Telegram chat with approve/reject buttons!", flush=True)

    return str(out_file)


if __name__ == "__main__":
    download_active_gemini_image()
