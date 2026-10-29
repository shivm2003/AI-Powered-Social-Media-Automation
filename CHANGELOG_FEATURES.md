# 📋 Manvix AI: Feature Implementation Log & Revert Guide

This document provides a complete audit trail of features implemented in the local host environment and GitHub repository, detailing each modified file, what was developed, and how the user can instantly revert all changes at once.

---

## 🚀 Summary of Developed Features

### 1. Instagram User ID Follower Extraction & Follow Request System
- **Capability**: Given any Instagram user ID, extracts follower count, saves profile metadata to database, sends follow request adhering to human safety delays, and maintains a cumulative lead counter.
- **Verification**: Tested on live profiles `@badshah_bhai__9186` (11.3k followers, private) and `@prayag_ngari` (106k followers).
- **Files**: `automation/social/instagram_follow.py`, `automation/db_campaigns.py`, `automation/telegram/bot.py`, `automation/telegram/poller.py`.

### 2. Posted Content Gallery (Images & Videos)
- **Capability**: Displays all published marketing posts across Instagram and Facebook in Telegram. Users can view photos, video reels, captions, dates, and friend share metrics with interactive pagination (`[⬅️ Prev]` / `[Next ➡️]`).
- **Files**: `automation/telegram/bot.py`, `automation/telegram/poller.py`, `automation/db_campaigns.py`.

### 3. Human-Touch "Share to All" Friends Automator
- **Capability**: Automatically shares post content to friends across Instagram (via Direct Message Share dialog) and Facebook (via Messenger).
- **"Human Touch" Safety**:
  - Randomized pauses between contact selections (`1.2s – 2.5s`).
  - Realistic typing speed emulated for post copy (`20ms – 50ms` per character).
  - Multi-platform safety breathing delay (`4s – 7s`).
  - Strict batch ceilings (max 25–30 per run) to comply with Meta anti-spam rules.
  - One-click interactive abort button (`[🛑 Stop Sharing Task]`).
- **Files**: `automation/social/post_sharer.py`, `automation/telegram/poller.py`, `automation/telegram/bot.py`.

---

## 📁 File-by-File Changes Detailed

| File Path | Nature of Change | Summary of Changes Made |
| :--- | :--- | :--- |
| `automation/social/post_sharer.py` | **NEW FILE** | Core engine for Instagram Share modal automation, Facebook Messenger post sharing, and multi-platform "Share to All" orchestration. |
| `automation/utils/extract_json.py` | **NEW FILE** | Robust JSON extraction utility handling markdown fences, trailing commas, and LLM output parsing. |
| `revert_changes.bat` | **NEW FILE** | 1-Click interactive Windows utility allowing instant rollback of recent commits and changes. |
| `automation/db_campaigns.py` | **MODIFIED** | Added `init_post_shares_table()`, `record_post_share()`, `get_all_published_posts()`, and `get_post_shares_stats()`. Integrated lead tracking in `save_instagram_target_lead()`. |
| `automation/telegram/bot.py` | **MODIFIED** | Added `send_posted_content_gallery()` with rich media cards and inline buttons; added `send_post_shares_overall_stats_menu()`; added gallery buttons to main `/start` menu and Outreach menu. |
| `automation/telegram/poller.py` | **MODIFIED** | Added callback routes for `post_page:` and `post_shr:`; added text commands `/posts`, `/myposts`, `/gallery`, `/shareall`, `/sharestats`; added async job runner `launch_post_share_task()`. |
| `automation/social/instagram_follow.py` | **MODIFIED** | Upgraded profile detail extraction (`headerText`, `og:description`), follow request dispatching, and follower counter tracking. |
| `automation/browser/driver.py` | **MODIFIED** | Added auto-recovery from blank white screens, active tab synchronization, and thread-safe platform tab switching. |
| `automation/social/facebook.py` | **MODIFIED** | Updated Messenger and post sharing flows. |
| `automation/social/instagram.py` | **MODIFIED** | Refined direct post navigation and thumbnail fallback clicks. |
| `automation/media/gemini_video_engine.py` | **MODIFIED** | 24-second 3-clip video reel generator complying with Indian advertising standards. |

---

## 🔄 How to Revert Changes at Once

If you ever wish to revert all or part of these changes, you can do so immediately using either method below:

### Method 1: 1-Click Script (Recommended for Windows)
Simply double-click or run:
```cmd
revert_changes.bat
```
Choose from the interactive menu:
- **Option 1**: Soft reset (undo commit but keep code in working directory)
- **Option 2**: Hard reset (completely restore codebase back to previous GitHub commit)
- **Option 3**: Selectively revert only the Post-Sharing & Gallery features

### Method 2: Git Terminal Commands
- **To undo the latest commit but keep all modified files**:
  ```bash
  git reset --soft HEAD~1
  ```
- **To completely roll back the codebase to before this update**:
  ```bash
  git reset --hard HEAD~1
  ```
- **To revert a pushed commit cleanly with a new revert commit**:
  ```bash
  git revert HEAD --no-edit
  git push origin main
  ```

---

## 📊 Live Verification Artifacts & Evidence
- Real screenshots captured during live verification runs:
  - `instagram_share_modal_selected.png` (Friends selected in native Instagram Share dialog)
  - `instagram_share_dispatched.png` (Bottom toast confirming post "Sent" on Instagram)
  - `facebook_messenger_share_verified.png` (Post copy and URL preview delivered in Facebook Messenger)
- Log records stored in SQLite database: `data/database.sqlite` (Table: `post_shares_log`).
