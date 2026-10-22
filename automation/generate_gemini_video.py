"""
Standalone CLI & Runner for 24-Second Gemini AI Video Pipeline (Indian Standard).

Usage:
    python automation/generate_gemini_video.py
    python automation/generate_gemini_video.py --prompt "Loan Solutions instant approval ₹5 Lakhs" --send-telegram
"""
import sys
import os
import argparse
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# Add automation dir to sys.path
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from media.gemini_video_engine import gemini_video_engine


def main():
    parser = argparse.ArgumentParser(description="24-Second Gemini Video Generation Pipeline (Indian Standard)")
    parser.add_argument(
        "--prompt",
        type=str,
        default="Loan Solutions Instant Personal & Business Finance in Indian Rupees",
        help="Marketing prompt for video"
    )
    parser.add_argument(
        "--product",
        type=str,
        default="Loan Solutions",
        help="Product name (defaults to Loan Solutions)"
    )
    parser.add_argument(
        "--category",
        type=str,
        default="Finance",
        help="Product category"
    )
    parser.add_argument(
        "--no-telegram",
        action="store_true",
        help="Skip dispatching preview to Telegram"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("🎬 24-SECOND GEMINI AI VIDEO PIPELINE (INDIAN STANDARD)")
    print(f"Product: {args.product}")
    print(f"Prompt: {args.prompt}")
    print(f"Dispatch to Telegram: {not args.no_telegram}")
    print("=" * 70)

    result = gemini_video_engine.run_full_24s_pipeline(
        prompt=args.prompt,
        product_name=args.product,
        product_category=args.category,
        platforms=["facebook", "instagram"],
        send_to_telegram=not args.no_telegram
    )

    print("\n✅ PIPELINE COMPLETED SUCCESSFULLY!")
    print(f"Campaign ID: {result.get('campaign_id')}")
    print(f"Total Duration: {result.get('duration')} seconds")
    print(f"Clips Generated: {len(result.get('clips', []))}")
    for idx, cpath in enumerate(result.get('clips', [])):
        print(f"  • Clip #{idx+1} (8s): {cpath}")
    print(f"Master 24s Video: {result.get('master_video')}")

    tg_info = result.get("telegram_response")
    if tg_info:
        print(f"Telegram Preview Dispatch Status: {tg_info.get('status')}")


if __name__ == "__main__":
    main()
