import sys
import os
import json
import sqlite3
import shutil
import tempfile

def scan_profile_cookies(profile_dir):
    detected = set()

    # 1. Try reading Cookies via temp copy (safely handles locked files if readable)
    cookie_path = os.path.join(profile_dir, "Network", "Cookies")
    if os.path.exists(cookie_path):
        tmp_cookie = tempfile.mktemp(suffix=".db")
        try:
            shutil.copy2(cookie_path, tmp_cookie)
            conn = sqlite3.connect(tmp_cookie)
            cur = conn.cursor()
            cur.execute("SELECT host_key FROM cookies")
            for (h,) in cur.fetchall():
                h_low = (h or "").lower()
                if "chatgpt" in h_low or "openai" in h_low: detected.add("chatgpt")
                if "gemini" in h_low: detected.add("gemini")
                if "claude" in h_low: detected.add("claude")
                if "linkedin" in h_low: detected.add("linkedin")
                if "instagram" in h_low: detected.add("instagram")
                if "facebook" in h_low: detected.add("facebook")
                if "whatsapp" in h_low: detected.add("whatsapp")
            conn.close()
        except Exception:
            pass
        finally:
            if os.path.exists(tmp_cookie):
                try: os.remove(tmp_cookie)
                except Exception: pass

    # 2. Check History (always readable via copy, accurately shows services user actively visits)
    history_path = os.path.join(profile_dir, "History")
    if os.path.exists(history_path):
        tmp_hist = tempfile.mktemp(suffix=".db")
        try:
            shutil.copy2(history_path, tmp_hist)
            conn = sqlite3.connect(tmp_hist)
            cur = conn.cursor()
            cur.execute(
                "SELECT url FROM urls WHERE "
                "url LIKE '%chatgpt.com%' OR url LIKE '%openai.com%' OR "
                "url LIKE '%gemini.google.com%' OR url LIKE '%claude.ai%' OR "
                "url LIKE '%linkedin.com%' OR url LIKE '%instagram.com%' OR "
                "url LIKE '%facebook.com%' OR url LIKE '%web.whatsapp.com%'"
            )
            for (u,) in cur.fetchall():
                u_low = (u or "").lower()
                if "chatgpt.com" in u_low or "openai.com" in u_low: detected.add("chatgpt")
                if "gemini.google.com" in u_low or "gemini" in u_low: detected.add("gemini")
                if "claude.ai" in u_low: detected.add("claude")
                if "linkedin.com" in u_low: detected.add("linkedin")
                if "instagram.com" in u_low: detected.add("instagram")
                if "facebook.com" in u_low: detected.add("facebook")
                if "web.whatsapp.com" in u_low: detected.add("whatsapp")
            conn.close()
        except Exception:
            pass
        finally:
            if os.path.exists(tmp_hist):
                try: os.remove(tmp_hist)
                except Exception: pass

    # 3. Check Login Data for stored accounts/credentials
    login_path = os.path.join(profile_dir, "Login Data")
    if os.path.exists(login_path):
        tmp_login = tempfile.mktemp(suffix=".db")
        try:
            shutil.copy2(login_path, tmp_login)
            conn = sqlite3.connect(tmp_login)
            cur = conn.cursor()
            cur.execute("SELECT origin_url FROM logins")
            for (u,) in cur.fetchall():
                u_low = (u or "").lower()
                if "chatgpt" in u_low or "openai" in u_low: detected.add("chatgpt")
                if "gemini" in u_low: detected.add("gemini")
                if "claude" in u_low: detected.add("claude")
                if "linkedin" in u_low: detected.add("linkedin")
                if "instagram" in u_low: detected.add("instagram")
                if "facebook" in u_low: detected.add("facebook")
                if "whatsapp" in u_low: detected.add("whatsapp")
            conn.close()
        except Exception:
            pass
        finally:
            if os.path.exists(tmp_login):
                try: os.remove(tmp_login)
                except Exception: pass

    order = ["chatgpt", "gemini", "claude", "linkedin", "instagram", "facebook", "whatsapp"]
    return [p for p in order if p in detected]

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = sys.argv[1]
        results = scan_profile_cookies(target)
        print(json.dumps(results))
    else:
        print(json.dumps([]))
