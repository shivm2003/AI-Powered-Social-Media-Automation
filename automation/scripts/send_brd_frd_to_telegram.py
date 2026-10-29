import os
import sys
import time
from pathlib import Path

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(r"c:\Users\shivam\Desktop\For marketing\AI-Powered-Social-Media-Automation")
sys.path.insert(0, str(BASE_DIR / "automation"))

from telegram.bot import send_telegram_document, get_telegram_credentials

_, chat_id = get_telegram_credentials()
target_chat = chat_id or "6543226262"
print(f"Target Telegram Chat ID: {target_chat}")

brd_file = BASE_DIR / "data" / "documents" / "Manvix_AI_Full_Project_BRD.docx"
frd_file = BASE_DIR / "data" / "documents" / "Manvix_AI_Full_Project_FRD.docx"

print("\n1. Dispatching Business Requirements Document (BRD) to Telegram...")
caption_brd = (
    "📄 <b>MANVIX AI — BUSINESS REQUIREMENTS DOCUMENT (BRD)</b>\n\n"
    "🏢 <b>Project:</b> Loan Solutions & Social Media Automation\n"
    "📦 <b>Coverage:</b> 100% Complete Project Scope\n"
    "🎯 <b>Highlights:</b> Commercial Vision, ROI Models, User Personas, Cultural Indian Copy Guidelines, Meta Anti-Spam Framework & 1-Click Rollback Policy.\n\n"
    "📥 <i>Delivered in Microsoft Word (.docx) Format</i>"
)
res_brd = send_telegram_document(target_chat, str(brd_file), caption=caption_brd)
print("BRD Telegram Dispatch Status:", res_brd.get("status"))
if res_brd.get("response", {}).get("result"):
    msg = res_brd["response"]["result"]
    print(f"  ✅ BRD Message ID: {msg.get('message_id')} | Doc Name: {msg.get('document', {}).get('file_name')} ({msg.get('document', {}).get('file_size')} bytes)")
else:
    print("  BRD Response:", res_brd)

time.sleep(2.5)

print("\n2. Dispatching Functional Requirements Document (FRD) to Telegram...")
caption_frd = (
    "📘 <b>MANVIX AI — FUNCTIONAL REQUIREMENTS DOCUMENT (FRD)</b>\n\n"
    "⚙️ <b>Architecture:</b> Next.js + Python Core + Selenium Port 9222 + Telegram Daemon\n"
    "📊 <b>Coverage:</b> Technical Specifications FR-01 to FR-12, Database Schemas (PG & SQLite), REST API Specifications, DOM Selector Mechanics & RTM Matrix.\n\n"
    "📥 <i>Delivered in Microsoft Word (.docx) Format</i>"
)
res_frd = send_telegram_document(target_chat, str(frd_file), caption=caption_frd)
print("FRD Telegram Dispatch Status:", res_frd.get("status"))
if res_frd.get("response", {}).get("result"):
    msg = res_frd["response"]["result"]
    print(f"  ✅ FRD Message ID: {msg.get('message_id')} | Doc Name: {msg.get('document', {}).get('file_name')} ({msg.get('document', {}).get('file_size')} bytes)")
else:
    print("  FRD Response:", res_frd)
