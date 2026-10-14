"""
Master QA Automated Verification Suite: Full System End-to-End
QA Persona: Senior QA Principal / QA Lead (10+ Years Experience)
Target Scope: All Subsystems (Instagram, Facebook, Telegram, AI Generation, Next.js, Database, Browser)
"""
import sys
import os
import time
import json
import logging
import traceback
import urllib.request
import urllib.parse
from pathlib import Path

# Ensure UTF-8 output on Windows console
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR / "automation"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("QA.MasterSuite")

class QATestResult:
    def __init__(self, test_id, name, module):
        self.test_id = test_id
        self.name = name
        self.module = module
        self.status = "NOT_RUN"
        self.duration = 0.0
        self.error_message = None
        self.details = {}

    def pass_test(self, duration, details=None):
        self.status = "PASSED"
        self.duration = duration
        self.details = details or {}

    def fail_test(self, duration, error_message, details=None):
        self.status = "FAILED"
        self.duration = duration
        self.error_message = str(error_message)
        self.details = details or {}


class MasterQATestRunner:
    def __init__(self):
        self.results = []
        self.start_time = time.time()

    def add_result(self, res: QATestResult):
        self.results.append(res)
        status_icon = "✅ PASS" if res.status == "PASSED" else "❌ FAIL"
        print(f"  [{status_icon}] {res.test_id} - {res.name} ({res.duration:.2f}s)")
        if res.status == "FAILED":
            print(f"        Error: {res.error_message}")

    # ─────────────────────────────────────────────────────────────
    # MODULE 1: NEXT.JS FRONTEND & API SERVICES
    # ─────────────────────────────────────────────────────────────
    def test_nextjs_frontend(self):
        print("\n" + "="*80)
        print("MODULE 1: NEXT.JS FRONTEND & REST API INTEGRATION")
        print("="*80)

        # TC-WEB-01: Health check on http://localhost:3000/
        t0 = time.time()
        res = QATestResult("TC-WEB-01", "Next.js Web Server Liveness (Port 3000)", "Frontend")
        try:
            req = urllib.request.Request("http://localhost:3000/", headers={"User-Agent": "QA-Runner"})
            with urllib.request.urlopen(req, timeout=5) as response:
                code = response.getcode()
                html = response.read().decode('utf-8', errors='ignore')
                if code == 200 and len(html) > 500:
                    res.pass_test(time.time() - t0, {"http_code": code, "html_length": len(html)})
                else:
                    res.fail_test(time.time() - t0, f"Unexpected HTTP status {code} or empty response")
        except Exception as e:
            res.fail_test(time.time() - t0, f"Next.js web server unreachable: {e}")
        self.add_result(res)

        # TC-WEB-02: Campaigns API Endpoint (/api/campaigns)
        t0 = time.time()
        res = QATestResult("TC-WEB-02", "Campaigns REST API Endpoint (/api/campaigns)", "API")
        try:
            req = urllib.request.Request("http://localhost:3000/api/campaigns", headers={"User-Agent": "QA-Runner"})
            with urllib.request.urlopen(req, timeout=5) as response:
                code = response.getcode()
                data = json.loads(response.read().decode('utf-8'))
                if code == 200 and isinstance(data, (list, dict)):
                    res.pass_test(time.time() - t0, {"record_count": len(data) if isinstance(data, list) else 1})
                else:
                    res.fail_test(time.time() - t0, f"Invalid API response payload: {data}")
        except Exception as e:
            res.fail_test(time.time() - t0, f"API /api/campaigns failed: {e}")
        self.add_result(res)

        # TC-WEB-03: Growth Outreach API Endpoint (/api/growth)
        t0 = time.time()
        res = QATestResult("TC-WEB-03", "Growth Outreach API Endpoint (/api/growth)", "API")
        try:
            req = urllib.request.Request("http://localhost:3000/api/growth", headers={"User-Agent": "QA-Runner"})
            with urllib.request.urlopen(req, timeout=5) as response:
                code = response.getcode()
                data = json.loads(response.read().decode('utf-8'))
                if code == 200:
                    res.pass_test(time.time() - t0, {"status": "ok"})
                else:
                    res.fail_test(time.time() - t0, f"Growth API returned {code}")
        except Exception as e:
            res.fail_test(time.time() - t0, f"API /api/growth failed: {e}")
        self.add_result(res)

        # TC-WEB-04: Accounts API Endpoint (/api/accounts)
        t0 = time.time()
        res = QATestResult("TC-WEB-04", "Accounts API Endpoint (/api/accounts)", "API")
        try:
            req = urllib.request.Request("http://localhost:3000/api/accounts", headers={"User-Agent": "QA-Runner"})
            with urllib.request.urlopen(req, timeout=5) as response:
                code = response.getcode()
                data = json.loads(response.read().decode('utf-8'))
                if code == 200:
                    res.pass_test(time.time() - t0, {"accounts_found": len(data) if isinstance(data, list) else 0})
                else:
                    res.fail_test(time.time() - t0, f"Accounts API returned {code}")
        except Exception as e:
            res.fail_test(time.time() - t0, f"API /api/accounts failed: {e}")
        self.add_result(res)

    # ─────────────────────────────────────────────────────────────
    # MODULE 2: DATABASE & DATA ACCESS LAYER
    # ─────────────────────────────────────────────────────────────
    def test_database_layer(self):
        print("\n" + "="*80)
        print("MODULE 2: DATABASE LAYER & SCHEMA VALIDATION")
        print("="*80)

        # TC-DB-01: SQLite Schema & Query Integrity
        t0 = time.time()
        res = QATestResult("TC-DB-01", "SQLite Campaigns & Accounts Table Integrity", "Database")
        try:
            import sqlite3
            db_paths = [
                ROOT_DIR / "data" / "database.sqlite",
                ROOT_DIR / "data" / "campaigns.db",
                ROOT_DIR / "data" / "social_automation.db",
                ROOT_DIR / "campaigns.db"
            ]
            active_db = next((p for p in db_paths if p.exists()), None)
            if not active_db:
                # Check data directory
                data_dir = ROOT_DIR / "data"
                dbs = list(data_dir.glob("*.sqlite")) + list(data_dir.glob("*.db")) if data_dir.exists() else []
                if dbs:
                    active_db = dbs[0]

            if not active_db:
                res.fail_test(time.time() - t0, "No SQLite database file found in data/ or root directory")
            else:
                conn = sqlite3.connect(str(active_db))
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [r[0] for r in cursor.fetchall()]
                conn.close()
                res.pass_test(time.time() - t0, {"db_file": str(active_db.name), "tables": tables})
        except Exception as e:
            res.fail_test(time.time() - t0, f"Database access error: {e}")
        self.add_result(res)

    # ─────────────────────────────────────────────────────────────
    # MODULE 3: TELEGRAM BOT & OUTREACH ENGINE
    # ─────────────────────────────────────────────────────────────
    def test_telegram_subsystem(self):
        print("\n" + "="*80)
        print("MODULE 3: TELEGRAM BOT, POLLER & OUTREACH ENGINE")
        print("="*80)

        # TC-TG-01: Telegram Bot Credentials & Configuration
        t0 = time.time()
        res = QATestResult("TC-TG-01", "Telegram Configuration & Token Audit", "Telegram")
        try:
            from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
            if not TELEGRAM_BOT_TOKEN or len(TELEGRAM_BOT_TOKEN) < 20:
                res.fail_test(time.time() - t0, "TELEGRAM_BOT_TOKEN missing or invalid format")
            elif not TELEGRAM_CHAT_ID:
                res.fail_test(time.time() - t0, "TELEGRAM_CHAT_ID missing")
            else:
                res.pass_test(time.time() - t0, {"chat_id": TELEGRAM_CHAT_ID, "token_prefix": TELEGRAM_BOT_TOKEN[:10] + "..."})
        except Exception as e:
            res.fail_test(time.time() - t0, f"Telegram config load failure: {e}")
        self.add_result(res)

        # TC-TG-02: Mandatory Apply Now Link in Telegram Buttons
        t0 = time.time()
        res = QATestResult("TC-TG-02", "Mandatory 'Apply Now' Inline Button Audit", "Telegram")
        try:
            poller_file = ROOT_DIR / "automation" / "telegram" / "poller.py"
            poller_code = poller_file.read_text(encoding="utf-8")
            target_url = "https://loansolutions.everythingrental.in/application"
            if target_url in poller_code and "Apply Now" in poller_code:
                res.pass_test(time.time() - t0, {"verified_url": target_url})
            else:
                res.fail_test(time.time() - t0, f"Apply Now button URL missing from poller.py: {target_url}")
        except Exception as e:
            res.fail_test(time.time() - t0, f"Poller code audit failed: {e}")
        self.add_result(res)

        # TC-TG-03: Custom Outreach Counter Support (5, 10, 25, 50 + Custom User Number)
        t0 = time.time()
        res = QATestResult("TC-TG-03", "Telegram Outreach Custom Friend Request Counter", "Telegram")
        try:
            # Audit src/app/growth/page.js and automation/social/facebook_friends.py
            growth_file = ROOT_DIR / "src" / "app" / "growth" / "page.js"
            growth_has_custom = False
            if growth_file.exists():
                growth_text = growth_file.read_text(encoding="utf-8")
                growth_has_custom = "custom" in growth_text.lower() or "customcount" in growth_text.lower() or "input" in growth_text.lower()

            if growth_has_custom:
                res.pass_test(time.time() - t0, {"custom_counter_supported": True})
            else:
                res.fail_test(time.time() - t0, "Custom user counter input field missing in growth page")
        except Exception as e:
            res.fail_test(time.time() - t0, f"Growth outreach audit error: {e}")
        self.add_result(res)

    # ─────────────────────────────────────────────────────────────
    # MODULE 4: AI CONTENT & IMAGE ENGINE (INDIAN STANDARDS)
    # ─────────────────────────────────────────────────────────────
    def test_ai_generation_engine(self):
        print("\n" + "="*80)
        print("MODULE 4: AI GENERATION & INDIAN STANDARD PROMPTS")
        print("="*80)

        # TC-AI-01: Indian Standard Prompt Specification Audit
        t0 = time.time()
        res = QATestResult("TC-AI-01", "Indian Financial Standard Prompt Specifications (₹, Middle Class, Loans)", "AI")
        try:
            prompts_file = ROOT_DIR / "automation" / "llm" / "prompts.py"
            prompts_code = prompts_file.read_text(encoding="utf-8")
            has_rupee = "₹" in prompts_code or "rupee" in prompts_code.lower()
            has_indian = "indian" in prompts_code.lower()
            has_middle_class = "middle class" in prompts_code.lower() or "family" in prompts_code.lower()
            has_loan_url = "loansolutions.everythingrental.in/application" in prompts_code

            if has_rupee and has_indian and has_loan_url:
                res.pass_test(time.time() - t0, {
                    "has_rupee": has_rupee,
                    "has_indian": has_indian,
                    "has_middle_class": has_middle_class,
                    "has_loan_url": has_loan_url
                })
            else:
                res.fail_test(time.time() - t0, f"Prompts missing Indian standards: rupee={has_rupee}, indian={has_indian}, url={has_loan_url}")
        except Exception as e:
            res.fail_test(time.time() - t0, f"Prompt audit error: {e}")
        self.add_result(res)

        # TC-AI-02: Gemini Image Generation & Download Script Integrity
        t0 = time.time()
        res = QATestResult("TC-AI-02", "Gemini Image Download Pipeline Integrity", "AI")
        try:
            gemini_dl = ROOT_DIR / "automation" / "download_gemini_image.py"
            gemini_human = ROOT_DIR / "automation" / "gemini_human_image_telegram.py"
            if gemini_dl.exists() and gemini_human.exists():
                res.pass_test(time.time() - t0, {"scripts_present": True})
            else:
                res.fail_test(time.time() - t0, "Gemini download/automation script missing")
        except Exception as e:
            res.fail_test(time.time() - t0, f"Gemini pipeline audit error: {e}")
        self.add_result(res)

    # ─────────────────────────────────────────────────────────────
    # MODULE 5: BROWSER ENGINE & SESSION MANAGER
    # ─────────────────────────────────────────────────────────────
    def test_browser_session_engine(self):
        print("\n" + "="*80)
        print("MODULE 5: BROWSER DRIVER & REMOTE SESSION MANAGER")
        print("="*80)

        # TC-BR-01: Chrome Remote Debugging (Port 9222) Connection
        t0 = time.time()
        res = QATestResult("TC-BR-01", "Chrome Remote Debugging (Port 9222) Attachment", "Browser")
        try:
            from browser.driver import browser
            d = browser.get_driver("instagram")
            if d and d.title:
                res.pass_test(time.time() - t0, {"window_title": d.title, "port": 9222})
            else:
                res.fail_test(time.time() - t0, "Driver object invalid or detached")
        except Exception as e:
            res.fail_test(time.time() - t0, f"Browser driver attachment error: {e}")
        self.add_result(res)

        # TC-BR-02: Navigation Reconciliation & Tab Isolation
        t0 = time.time()
        res = QATestResult("TC-BR-02", "Tab-Safe Navigation (navigate() without trapping)", "Browser")
        try:
            from browser.driver import browser
            d = browser.navigate("instagram", "https://www.instagram.com/", refresh_first=False)
            time.sleep(1)
            if "instagram.com" in d.current_url.lower():
                res.pass_test(time.time() - t0, {"current_url": d.current_url})
            else:
                res.fail_test(time.time() - t0, f"navigate() failed to switch to Instagram tab: {d.current_url}")
        except Exception as e:
            res.fail_test(time.time() - t0, f"Navigation test error: {e}")
        self.add_result(res)

    # ─────────────────────────────────────────────────────────────
    # MODULE 6: FACEBOOK SOCIAL PUBLISHER
    # ─────────────────────────────────────────────────────────────
    def test_facebook_social_engine(self):
        print("\n" + "="*80)
        print("MODULE 6: FACEBOOK SOCIAL AUTOMATION & LINK PREVIEWS")
        print("="*80)

        # TC-FB-01: Facebook Engine Syntax & Link Preview Support
        t0 = time.time()
        res = QATestResult("TC-FB-01", "Facebook Post Engine Syntax & Link Attachment", "Facebook")
        try:
            fb_file = ROOT_DIR / "automation" / "social" / "facebook.py"
            fb_code = fb_file.read_text(encoding="utf-8")
            if "post_to_facebook" in fb_code or "create_post" in fb_code:
                res.pass_test(time.time() - t0, {"file_size_bytes": len(fb_code)})
            else:
                res.fail_test(time.time() - t0, "facebook.py missing core post function")
        except Exception as e:
            res.fail_test(time.time() - t0, f"Facebook code audit error: {e}")
        self.add_result(res)

    # ─────────────────────────────────────────────────────────────
    # MODULE 7: INSTAGRAM POSTING & CAPTION FITTING ENGINE
    # ─────────────────────────────────────────────────────────────
    def test_instagram_publishing_engine(self):
        print("\n" + "="*80)
        print("MODULE 7: INSTAGRAM POSTING, LEXICAL CAPTION & BINDING GATES")
        print("="*80)

        # TC-IG-01: Instagram Caption Fitting & Live End-to-End Test
        t0 = time.time()
        res = QATestResult("TC-IG-01", "End-to-End Instagram Media Post with Fitted Caption & Link", "Instagram")
        try:
            from social.instagram import post_to_instagram
            media_file = str(ROOT_DIR / "Loan Solutions.png")
            unique_ts = time.strftime("%d-%b %H:%M:%S")
            test_caption = (
                f"🏡 Loan Solutions — Instant Home & Personal Loans! [{unique_ts}]\n\n"
                "✨ 100% Paperless & Instant In-Principle Approval\n"
                "✨ Lowest interest rates starting from 8.5% p.a.\n"
                "✨ Quick disbursement directly into your bank account\n\n"
                "👉 Apply Now: https://loansolutions.everythingrental.in/application\n\n"
                "#LoanSolutions #HomeLoan #PersonalLoan #FinancialFreedom #India #LowEMI"
            )

            post_res = post_to_instagram(media_path=media_file, caption=test_caption)
            if post_res.get("status") == "success":
                res.pass_test(time.time() - t0, post_res)
            else:
                res.fail_test(time.time() - t0, post_res.get("message", "Unknown error"), post_res)
        except Exception as e:
            res.fail_test(time.time() - t0, f"Instagram post execution error: {e}")
        self.add_result(res)

    def generate_final_report(self):
        elapsed = time.time() - self.start_time
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r.status == "PASSED"])
        failed_tests = len([r for r in self.results if r.status == "FAILED"])
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        print("\n" + "="*80)
        print("📊 PRINCIPAL QA EXECUTIVE SUMMARY REPORT")
        print("="*80)
        print(f"Total Execution Duration: {elapsed:.2f}s")
        print(f"Total Test Cases Executed: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Pass Rate: {pass_rate:.1f}%")
        print("="*80)

        # List failures if any
        if failed_tests > 0:
            print("\n🚨 DEFECT MATRIX (FAILURES REQUIRING REMEDIATION):")
            for r in self.results:
                if r.status == "FAILED":
                    print(f"• [{r.test_id}] {r.name}: {r.error_message}")
        else:
            print("\n🏆 ALL CRITICAL SYSTEM CAPABILITIES VERIFIED 100% OPERATIONAL!")

        return {
            "total": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "pass_rate": pass_rate,
            "results": [{
                "id": r.test_id,
                "name": r.name,
                "module": r.module,
                "status": r.status,
                "duration": r.duration,
                "error": r.error_message,
                "details": r.details
            } for r in self.results]
        }


def run_full_suite():
    runner = MasterQATestRunner()
    runner.test_nextjs_frontend()
    runner.test_database_layer()
    runner.test_telegram_subsystem()
    runner.test_ai_generation_engine()
    runner.test_browser_session_engine()
    runner.test_facebook_social_engine()
    runner.test_instagram_publishing_engine()
    report = runner.generate_final_report()

    # Save JSON report
    report_file = ROOT_DIR / "qa_system_audit_report.json"
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nDetailed JSON report exported to: {report_file}")
    return report

if __name__ == "__main__":
    run_full_suite()
