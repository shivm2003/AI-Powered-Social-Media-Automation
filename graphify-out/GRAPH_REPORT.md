# Graph Report - AI Powered Social Media  (2026-10-13)

## Corpus Check
- 64 files · ~48,384 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: (none) 2, .css 2, .example 1)

## Summary
- 508 nodes · 1017 edges · 21 communities (14 shown, 7 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 59 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b2583202`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- db.js
- human_operator.py
- constants.js
- bot.py
- BrowserDriver
- package.json
- time
- image_generator.py
- encryption.py
- AccountsPage
- AI-Powered Social Media Automation — Full Project Plan
- layout.js
- browser/route.js
- ProductsPage
- compilerOptions
- next.config.mjs
- README.md
- AGENTS.md

## God Nodes (most connected - your core abstractions)
1. `query()` - 26 edges
2. `generate_social_image()` - 20 edges
3. `next` - 20 edges
4. `execute_human_generation_and_telegram_flow()` - 16 edges
5. `handle_command()` - 16 edges
6. `AccountsPage()` - 16 edges
7. `BrowserDriver` - 13 edges
8. `handle_callback_query()` - 13 edges
9. `generate_marketing_content()` - 12 edges
10. `get_telegram_credentials()` - 12 edges

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

## Communities (21 total, 7 thin omitted)

### Community 0 - "db.js"
Cohesion: 0.06
Nodes (60): next, DELETE(), GET(), POST(), POST(), POST(), DELETE(), GET() (+52 more)

### Community 1 - "human_operator.py"
Cohesion: 0.07
Nodes (18): ensure_profile_ready(), execute_full_human_flow(), execute_human_generation_and_telegram_flow(), find_chrome_executable(), get_real_chrome_user_data_dir(), human_sleep(), human_type(), is_port_open() (+10 more)

### Community 2 - "constants.js"
Cohesion: 0.08
Nodes (25): react, ALL_AUTOMATION_PLATFORMS, ALL_PLATFORMS_MAP, CampaignsPage(), fetchCampaigns(), handleApprove(), handleDelete(), getMediaUrl() (+17 more)

### Community 3 - "bot.py"
Cohesion: 0.07
Nodes (17): generate_with_chatgpt_browser(), generate_with_claude_browser(), generate_with_gemini_browser(), extract_json_or_fallback(), generate_marketing_content(), generate_smart_marketing_copy(), generate_with_gemini_api(), build_social_prompt() (+9 more)

### Community 5 - "package.json"
Cohesion: 0.07
Nodes (26): eslintConfig, dependencies, better-sqlite3, next, pg, react, react-dom, uuid (+18 more)

### Community 6 - "time"
Cohesion: 0.07
Nodes (18): ensure_debugging_browser(), get_chrome_version_main(), is_debugging_port_open(), is_facebook_login_needed(), post_to_facebook(), submit_facebook_login(), publish_to_all_platforms(), publish_to_platform() (+10 more)

### Community 7 - "image_generator.py"
Cohesion: 0.07
Nodes (16): get_target_url(), is_profile_initialized(), download_active_chatgpt_image(), generate_image_with_chatgpt_browser(), generate_image_with_gemini_browser(), generate_social_image(), get_font(), hex_to_rgb() (+8 more)

### Community 9 - "encryption.py"
Cohesion: 0.15
Nodes (5): scan_profile_cookies(), decrypt_password(), encrypt_password(), get_master_secret(), test_roundtrip()

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
Cohesion: 0.36
Nodes (8): checkPort(), findChromePath(), GET(), getChromeUserDataDir(), getProfileDetails(), POST(), syncProfileToSharedDir(), copyDirClean()

### Community 15 - "ProductsPage"
Cohesion: 0.32
Nodes (4): ProductsPage(), fetchProducts(), handleDelete(), handleSave()

### Community 23 - "README.md"
Cohesion: 0.29
Nodes (6): Check Lines of Code, Codebase Statistics, Deploy on Vercel, Getting Started, Language Breakdown, Learn More

## Knowledge Gaps
- **2 isolated node(s):** `better-sqlite3`, `react-dom`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 218 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `next` connect `db.js` to `browser/route.js`, `constants.js`, `layout.js`, `package.json`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `generate_social_image()` (e.g. with `execute_human_generation_and_telegram_flow()` and `run_chatgpt_human_image_and_telegram()`) actually correct?**
  _`generate_social_image()` has 11 INFERRED edges - model-reasoned connections that need verification._
- **What connects `better-sqlite3`, `react-dom` to the rest of the system?**
  _2 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `db.js` be split into smaller, more focused modules?**
  _Cohesion score 0.06162464985994398 - nodes in this community are weakly interconnected._
- **Why does `react` connect `constants.js` to `package.json`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Should `human_operator.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07474747474747474 - nodes in this community are weakly interconnected._
- **Why does `BrowserDriver` connect `BrowserDriver` to `time`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._