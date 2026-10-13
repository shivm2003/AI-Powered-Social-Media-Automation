# Graph Report - AI Powered Social Media  (2026-10-13)

## Corpus Check
- 63 files · ~43,544 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: (none) 2, .css 2, .example 1)

## Summary
- 491 nodes · 967 edges · 25 communities (17 shown, 8 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 42 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f1b32fdc`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- db.js
- human_operator.py
- constants.js
- llm/__init__.py
- BrowserDriver
- package.json
- time
- generate_social_image
- bot.py
- encryption.py
- AccountsPage
- AI-Powered Social Media Automation — Full Project Plan
- layout.js
- browser/route.js
- driver.py
- ProductsPage
- config.py
- compilerOptions
- next.config.mjs
- post_to_facebook
- README.md
- AGENTS.md

## God Nodes (most connected - your core abstractions)
1. `query()` - 26 edges
2. `next` - 20 edges
3. `handle_command()` - 16 edges
4. `generate_social_image()` - 16 edges
5. `AccountsPage()` - 16 edges
6. `execute_human_generation_and_telegram_flow()` - 14 edges
7. `BrowserDriver` - 13 edges
8. `generate_marketing_content()` - 12 edges
9. `AI-Powered Social Media Automation — Full Project Plan` - 12 edges
10. `step1_click_and_launch_chrome()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `generate_marketing_content()` --calls--> `is_debugging_port_open()`  [INFERRED]
  automation/llm/__init__.py → automation/browser/driver.py
- `execute_human_generation_and_telegram_flow()` --calls--> `extract_json_or_fallback()`  [INFERRED]
  automation/browser/human_operator.py → automation/llm/__init__.py
- `execute_human_generation_and_telegram_flow()` --calls--> `generate_smart_marketing_copy()`  [INFERRED]
  automation/browser/human_operator.py → automation/llm/__init__.py
- `execute_human_generation_and_telegram_flow()` --calls--> `build_social_prompt()`  [INFERRED]
  automation/browser/human_operator.py → automation/llm/prompts.py
- `execute_human_generation_and_telegram_flow()` --calls--> `generate_social_image()`  [INFERRED]
  automation/browser/human_operator.py → automation/media/image_generator.py

## Import Cycles
- None detected.

## Communities (25 total, 8 thin omitted)

### Community 0 - "db.js"
Cohesion: 0.07
Nodes (54): next, uuid, DELETE(), GET(), POST(), POST(), POST(), DELETE() (+46 more)

### Community 1 - "human_operator.py"
Cohesion: 0.07
Nodes (17): ensure_profile_ready(), execute_full_human_flow(), execute_human_generation_and_telegram_flow(), find_chrome_executable(), get_real_chrome_user_data_dir(), human_sleep(), human_type(), is_port_open() (+9 more)

### Community 2 - "constants.js"
Cohesion: 0.08
Nodes (25): react, ALL_AUTOMATION_PLATFORMS, ALL_PLATFORMS_MAP, CampaignsPage(), fetchCampaigns(), handleApprove(), handleDelete(), getMediaUrl() (+17 more)

### Community 3 - "llm/__init__.py"
Cohesion: 0.13
Nodes (8): generate_with_chatgpt_browser(), generate_with_claude_browser(), generate_with_gemini_browser(), extract_json_or_fallback(), generate_marketing_content(), generate_smart_marketing_copy(), generate_with_gemini_api(), build_social_prompt()

### Community 5 - "package.json"
Cohesion: 0.08
Nodes (25): eslintConfig, dependencies, better-sqlite3, next, pg, react, react-dom, uuid (+17 more)

### Community 6 - "time"
Cohesion: 0.18
Nodes (5): publish_to_all_platforms(), publish_to_platform(), post_to_instagram(), post_to_linkedin(), post_to_whatsapp()

### Community 7 - "generate_social_image"
Cohesion: 0.12
Nodes (6): generate_image_with_chatgpt_browser(), generate_image_with_gemini_browser(), create_gradient_canvas(), generate_social_image(), hex_to_rgb(), generate_promo_video()

### Community 8 - "bot.py"
Cohesion: 0.13
Nodes (11): answer_callback_query(), delete_telegram_message(), get_telegram_credentials(), make_telegram_request(), send_password_request_prompt(), send_platform_selection_menu(), send_preview_to_telegram(), send_text_message() (+3 more)

### Community 9 - "encryption.py"
Cohesion: 0.15
Nodes (5): download_active_chatgpt_image(), decrypt_password(), encrypt_password(), get_master_secret(), test_roundtrip()

### Community 10 - "AccountsPage"
Cohesion: 0.20
Nodes (11): AccountsPage(), checkBrowserStatus(), fetchAccounts(), fetchChromeProfiles(), handleCloneChromeProfile(), handleLaunchBrowser(), handleRunHumanFlow(), saveAllAccounts() (+3 more)

### Community 11 - "AI-Powered Social Media Automation — Full Project Plan"
Cohesion: 0.04
Nodes (45): 10. Key Design Decisions, 11. Risk Mitigation, 1. High-Level Architecture, 2. Technology Stack, 3.1 Page Structure, 3.2 Dashboard Home (`/`), 3.3 Product Manager (`/products`), 3.4 Social Account Manager (`/accounts`) (+37 more)

### Community 12 - "layout.js"
Cohesion: 0.25
Nodes (8): inter, metadata, RootLayout(), Header(), checkBrowserStatus(), handleLaunchBrowser(), navItems, Sidebar()

### Community 13 - "browser/route.js"
Cohesion: 0.17
Nodes (15): checkPort(), findChromePath(), GET(), getChromeUserDataDir(), getProfileDetails(), POST(), syncProfileToSharedDir(), copyDirClean() (+7 more)

### Community 14 - "driver.py"
Cohesion: 0.18
Nodes (3): ensure_debugging_browser(), get_chrome_version_main(), is_debugging_port_open()

### Community 15 - "ProductsPage"
Cohesion: 0.32
Nodes (4): ProductsPage(), fetchProducts(), handleDelete(), handleSave()

### Community 22 - "post_to_facebook"
Cohesion: 0.24
Nodes (5): is_facebook_login_needed(), post_to_facebook(), submit_facebook_login(), handle_text_message(), start_polling()

### Community 23 - "README.md"
Cohesion: 0.29
Nodes (6): Check Lines of Code, Codebase Statistics, Deploy on Vercel, Getting Started, Language Breakdown, Learn More

## Knowledge Gaps
- **2 isolated node(s):** `better-sqlite3`, `react-dom`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 214 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `next` connect `db.js` to `browser/route.js`, `constants.js`, `layout.js`, `package.json`?**
  _High betweenness centrality (0.082) - this node is a cross-community bridge._
- **What connects `better-sqlite3`, `react-dom` to the rest of the system?**
  _2 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `db.js` be split into smaller, more focused modules?**
  _Cohesion score 0.06912280701754386 - nodes in this community are weakly interconnected._
- **Why does `react` connect `constants.js` to `package.json`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Should `human_operator.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06693877551020408 - nodes in this community are weakly interconnected._
- **Why does `BrowserDriver` connect `BrowserDriver` to `driver.py`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Should `constants.js` be split into smaller, more focused modules?**
  _Cohesion score 0.08130081300813008 - nodes in this community are weakly interconnected._