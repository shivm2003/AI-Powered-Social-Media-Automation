"""
Manvix AI — Professional Word (.docx) BRD & FRD Generator.
Generates:
1. Manvix_AI_Full_Project_BRD.docx (Business Requirements Document)
2. Manvix_AI_Full_Project_FRD.docx (Functional Requirements Document)
Both documents are styled with executive typography, headers, callout boxes, and full technical/business tables.
"""
import os
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

BASE_DIR = Path(__file__).parent.parent.parent
DOCS_DIR = BASE_DIR / "data" / "documents"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

# Color Palette
COLOR_PRIMARY = RGBColor(15, 23, 42)      # Deep Navy / Slate 900
COLOR_SECONDARY = RGBColor(30, 58, 138)   # Royal Blue
COLOR_ACCENT = RGBColor(14, 116, 144)     # Cyan / Teal Accent
COLOR_MUTED = RGBColor(100, 116, 139)     # Slate 500
COLOR_DARK = RGBColor(30, 41, 59)         # Text Dark
HEX_HEADER_BG = "1E293B"                  # Dark Slate for Table Header
HEX_ZEBRA_BG = "F8FAFC"                   # Off-white zebra row
HEX_BORDER = "CBD5E1"                     # Slate 300 border
HEX_CALLOUT_BG = "F1F5F9"                 # Light slate background
HEX_CALLOUT_BORDER = "0284C7"             # Cyan / Sky border


def set_cell_shading(cell, color_hex):
    """Sets cell background fill."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:val="clear" w:color="auto" w:fill="{color_hex}"/>')
    tcPr.append(shd)


def set_table_borders(table, border_color=HEX_BORDER):
    """Applies clean subtle borders to a table."""
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="single" w:sz="4" w:space="0" w:color="{border_color}"/>'
        f'  <w:left w:val="single" w:sz="4" w:space="0" w:color="{border_color}"/>'
        f'  <w:bottom w:val="single" w:sz="4" w:space="0" w:color="{border_color}"/>'
        f'  <w:right w:val="single" w:sz="4" w:space="0" w:color="{border_color}"/>'
        f'  <w:insideH w:val="single" w:sz="4" w:space="0" w:color="{border_color}"/>'
        f'  <w:insideV w:val="single" w:sz="4" w:space="0" w:color="{border_color}"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)


def add_callout(doc, title, text):
    """Creates a styled callout box."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    set_cell_shading(cell, HEX_CALLOUT_BG)
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'  <w:left w:val="single" w:sz="24" w:space="0" w:color="{HEX_CALLOUT_BORDER}"/>'
        f'  <w:top w:val="none"/>'
        f'  <w:right w:val="none"/>'
        f'  <w:bottom w:val="none"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)
    cell.paragraphs[0].paragraph_format.space_before = Pt(4)
    cell.paragraphs[0].paragraph_format.space_after = Pt(2)
    p = cell.paragraphs[0]
    run_t = p.add_run(f"📌 {title}\n")
    run_t.bold = True
    run_t.font.color.rgb = COLOR_SECONDARY
    run_t.font.size = Pt(10.5)

    run_b = p.add_run(text)
    run_b.font.color.rgb = COLOR_DARK
    run_b.font.size = Pt(9.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)


def add_custom_heading(doc, text, level):
    """Adds styled headings with proper spacing."""
    p = doc.add_paragraph()
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.bold = True
    if level == 1:
        p.paragraph_format.space_before = Pt(18)
        p.paragraph_format.space_after = Pt(6)
        run.font.size = Pt(18)
        run.font.color.rgb = COLOR_PRIMARY
    elif level == 2:
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
        run.font.size = Pt(14)
        run.font.color.rgb = COLOR_SECONDARY
    elif level == 3:
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(2)
        run.font.size = Pt(11.5)
        run.font.color.rgb = COLOR_ACCENT
    return p


def format_table(table, col_widths, headers, data):
    """Formats a complete table with widths, header shading, and alternating zebra rows."""
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(table)

    # Header Row
    hdr_cells = table.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        set_cell_shading(hdr_cells[i], HEX_HEADER_BG)
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in p.runs:
            run.font.bold = True
            run.font.color.rgb = RGBColor(255, 255, 255)
            run.font.size = Pt(9.5)

    # Data Rows
    for row_idx, row_data in enumerate(data):
        row = table.rows[row_idx + 1]
        is_even = (row_idx % 2 == 0)
        bg = "FFFFFF" if is_even else HEX_ZEBRA_BG
        for col_idx, val in enumerate(row_data):
            cell = row.cells[col_idx]
            cell.text = str(val)
            set_cell_shading(cell, bg)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            for run in p.runs:
                run.font.size = Pt(9)
                run.font.color.rgb = COLOR_DARK

    # Column Widths
    for row in table.rows:
        for idx, width in enumerate(col_widths):
            row.cells[idx].width = Inches(width)


# ==============================================================================
# 1. BUILD BRD (BUSINESS REQUIREMENTS DOCUMENT)
# ==============================================================================
def generate_brd(output_path):
    print(f"Generating BRD at: {output_path}...")
    doc = Document()

    # Document Geometry
    sections = doc.sections
    for s in sections:
        s.top_margin = Inches(0.8)
        s.bottom_margin = Inches(0.8)
        s.left_margin = Inches(0.8)
        s.right_margin = Inches(0.8)

    # Title Page Block
    p_title_top = doc.add_paragraph()
    p_title_top.paragraph_format.space_before = Pt(40)
    r_sub = p_title_top.add_run("ENTERPRISE PRODUCT SPECIFICATION & STRATEGY\n")
    r_sub.font.size = Pt(11)
    r_sub.font.color.rgb = COLOR_ACCENT
    r_sub.bold = True

    r_title = p_title_top.add_run("Business Requirements Document (BRD)\n")
    r_title.font.size = Pt(26)
    r_title.font.color.rgb = COLOR_PRIMARY
    r_title.bold = True

    r_proj = p_title_top.add_run("Manvix AI: Autonomous Social Media Marketing & Audience Growth Engine\n")
    r_proj.font.size = Pt(16)
    r_proj.font.color.rgb = COLOR_SECONDARY

    p_meta = doc.add_paragraph()
    p_meta.paragraph_format.space_after = Pt(24)
    p_meta.add_run(
        "Document Version: 1.0.0 (Production Release)\n"
        "Date: October 2026\n"
        "Business Entity: Loan Solutions (Shivam Mishra Marketing Operations)\n"
        "System Target: Meta (Instagram & Facebook), LinkedIn, Telegram Bot (@shiv2003_bot)\n"
        "Classification: Confidential — Commercial Proprietary"
    )

    add_callout(
        doc,
        "Executive Business Mandate",
        "This Business Requirements Document defines the commercial objectives, operational requirements, "
        "and market success metrics for Manvix AI. It establishes how AI-driven content generation, multi-platform "
        "social publishing, human-touch friend sharing, and targeted outreach drive sustainable customer acquisition "
        "for Loan Solutions with zero reliance on paid ads."
    )

    doc.add_page_break()

    # Table of Contents Outline
    add_custom_heading(doc, "Document Table of Contents", 1)
    toc_items = [
        "1. Project Overview & Commercial Rationale",
        "2. Strategic Business Goals & ROI Architecture",
        "3. User Personas & Target Demographics",
        "4. Scope of the System (In-Scope vs Out-of-Scope)",
        "5. Core Business Requirements & User Stories",
        "6. Cultural & Localization Marketing Guidelines",
        "7. Meta Anti-Spam & Operational Safety Framework",
        "8. Business KPIs & Operational Success Metrics",
        "9. Risk Analysis, Assumptions & Mitigation Strategies",
        "10. 1-Click Rollback & Change Management Policy",
    ]
    for item in toc_items:
        p_toc = doc.add_paragraph()
        p_toc.paragraph_format.space_after = Pt(2)
        r = p_toc.add_run(f"•  {item}")
        r.font.size = Pt(10)
        r.font.color.rgb = COLOR_DARK

    doc.add_page_break()

    # Section 1: Overview
    add_custom_heading(doc, "1. Project Overview & Commercial Rationale", 1)
    p_desc = doc.add_paragraph()
    p_desc.add_run(
        "Traditional digital marketing agencies and small-to-medium enterprise financial brokers face three severe bottlenecks:\n"
        "1. High Creation Cost & Delay: Producing daily graphic creatives, video reels, and localized copy requires multiple specialists and days of turnaround.\n"
        "2. Manual Outreach Limitations: Organic relationship building and connection management across Facebook and Instagram is tedious, repetitive, and inconsistent.\n"
        "3. Account Suspension Risks: Off-the-shelf bots use aggressive automation that triggers immediate Meta anti-bot defenses, causing permanent bans.\n\n"
        "Manvix AI directly solves these problems by providing an autonomous, closed-loop marketing engine. Powered by advanced multimodal models (Gemini & ChatGPT), "
        "human-operator browser telemetry, and Telegram-driven human-in-the-loop review, Manvix AI generates localized, high-converting posts, verifies them across networks, "
        "shares them to friend networks with realistic human touch, and grows the audience through targeted lead extraction."
    )

    # Section 2: Goals & ROI
    add_custom_heading(doc, "2. Strategic Business Goals & ROI Architecture", 1)
    roi_headers = ["Strategic Objective", "Commercial Metric / Benchmark", "Business Impact"]
    roi_data = [
        ["Autonomous Creative Production", "From 45 mins down to 30 seconds per campaign", "98% reduction in creative agency labor costs."],
        ["24s Indian Video Reel Generation", "100% adherence to Indian advertising standards", "High engagement via 9:16 vertical video algorithms."],
        ["Human-Touch Post Sharing", "Distribute posts to up to 30 friends per session", "Organic reach multiplier of 5x–12x with 0 ad spend."],
        ["Targeted Follower Lead Extraction", "Capture exact follower counts & follow targets", "Direct pipeline of qualified middle-class financial leads."],
        ["Zero Platform Ban Rate", "100% account longevity via human operator emulation", "Protects brand equity and social assets permanently."],
        ["Two-Way Mobile Supervision", "Instant Telegram approvals & password ingestion", "Complete hands-off mobile management for business owners."]
    ]
    t_roi = doc.add_table(rows=len(roi_data) + 1, cols=3)
    format_table(t_roi, [2.2, 2.3, 2.4], roi_headers, roi_data)

    # Section 3: Personas
    add_custom_heading(doc, "3. User Personas & Target Demographics", 1)
    persona_headers = ["Persona Role", "Key Responsibilities & Pain Points", "Manvix AI Value Proposition"]
    persona_data = [
        [
            "Financial Broker / Business Owner\n(Shivam Mishra — Loan Solutions)",
            "Needs steady inbound loan inquiries (Home Loan, LAP, Business Loan). Lacks time to create graphics or manage daily social accounts.",
            "Receives ready-to-post creatives on Telegram; approves with 1 click; watches system auto-post and share to friends."
        ],
        [
            "Target Consumer\n(Indian Middle-Class Borrowers)",
            "Needs quick personal loans or loan against property; skeptical of hidden charges and complex bank paperwork.",
            "Sees clear, relatable marketing copy with transparent EMI tables, Rupee ₹ symbols, and direct WhatsApp links."
        ],
        [
            "System Automation Operator\n(AI System Administrator)",
            "Monitors queue health, multi-profile Chrome accounts, anti-detection pacing, and disaster recovery.",
            "Accesses live /queue dashboard, inspects database logs, and uses 1-click revert batch utility when updating."
        ]
    ]
    t_pers = doc.add_table(rows=len(persona_data) + 1, cols=3)
    format_table(t_pers, [2.0, 2.5, 2.4], persona_headers, persona_data)

    # Section 4: Scope
    add_custom_heading(doc, "4. Scope of the System (In-Scope vs Out-of-Scope)", 1)
    scope_headers = ["Functional Domain", "In-Scope Business Capabilities", "Out-of-Scope Limitations"]
    scope_data = [
        ["Content Generation", "AI Copywriting, 1:1 Feed Graphics, 24s 3-clip Video Reels with Indian voice/music.", "3D rendering, live broadcast streaming."],
        ["Social Publishing", "Facebook Personal Profile, Facebook Business Page, Instagram Feed, Reels, LinkedIn.", "Paid Facebook Ads Manager ad spend bidding."],
        ["Audience Growth", "Target user ID follower count extraction, follow requests, FB friend request acceptance.", "Scraping private personal contact phone books."],
        ["Friend Post Sharing", "Instagram Share dialog multi-select ('Send Separately'), Facebook Messenger.", "Direct mass SMS or WhatsApp Cloud broadcast API."],
        ["Platform Control", "Telegram Bot interactive flows, Next.js Web UI, Chrome Port 9222 automation.", "Standalone native iOS/Android binary builds."]
    ]
    t_scope = doc.add_table(rows=len(scope_data) + 1, cols=3)
    format_table(t_scope, [1.8, 2.8, 2.3], scope_headers, scope_data)

    # Section 5: Core Business Requirements
    add_custom_heading(doc, "5. Core Business Requirements & User Stories", 1)
    reqs_headers = ["Req ID", "Business Feature", "User Story & Acceptance Criteria"]
    reqs_data = [
        [
            "BR-01",
            "Loan Solutions Branding & Reference Watermark",
            "As a business owner, I require all generated media to prominently feature 'Loan Solutions' branding and logos so brand awareness is enforced across all channels."
        ],
        [
            "BR-02",
            "Indian Financial Market Localization",
            "As a marketing manager, the AI copy must use Rupee symbols (₹), emphasize low EMIs, zero paperwork, fast disbursal, and localized Hindi/English middle-class appeal."
        ],
        [
            "BR-03",
            "Interactive Telegram Human-in-the-Loop Review",
            "As an operator, I must receive generated graphics/videos on Telegram (@shiv2003_bot) with [Approve & Post], [Edit], and [Regenerate] buttons before anything is published."
        ],
        [
            "BR-04",
            "Auto Password Ingestion on Session Expiry",
            "As an operator, if a social account logs out in Chrome, the bot must prompt me for the password in Telegram and type it into the browser without technical intervention."
        ],
        [
            "BR-05",
            "Target User ID Follower Extraction & Follows",
            "As an outreach specialist, I want to input an Instagram user ID, automatically capture their exact follower count (e.g. 11.3k, 106k), and dispatch a follow request."
        ],
        [
            "BR-06",
            "Posted Content Gallery (Images & Videos)",
            "As a marketer, I require a visual gallery in Telegram showing all published images and video reels with pagination to review historical campaign performance."
        ],
        [
            "BR-07",
            "Human-Touch 'Share to All' Friends",
            "As a business owner, when I select 'Share to All', the system must distribute the post to my friends across Instagram and Facebook with randomized anti-spam delays."
        ],
        [
            "BR-08",
            "Multitasking Concurrency & Queue Dashboard",
            "As an operator, running outreach, generation, and sharing tasks must be queued safely without colliding on the single Chrome browser window."
        ],
        [
            "BR-09",
            "1-Click Rollback & Change Management",
            "As an administrator, I must have an instant 1-click batch tool to revert recent codebase changes back to a clean state if any operational issue arises."
        ]
    ]
    t_req = doc.add_table(rows=len(reqs_data) + 1, cols=3)
    format_table(t_req, [1.0, 2.2, 3.7], reqs_headers, reqs_data)

    # Section 6: Cultural & Compliance
    add_custom_heading(doc, "6. Cultural & Localization Marketing Guidelines", 1)
    p_cul = doc.add_paragraph()
    p_cul.add_run(
        "To resonate with Indian consumers and convert cold social media audiences into qualified loan applicants, "
        "Manvix AI strictly adheres to the following content guidelines:\n"
        "• High-Trust Emotional Hooks: Narratives focus on family milestones ('Apna Ghar Loan', 'Child Higher Education', 'Business Expansion', 'Wedding Season').\n"
        "• Mandatory Line 1 Call-to-Action: High-converting direct link ('👉 Apply Now: https://loansolutions.everythingrental.in/application') followed by phone/WhatsApp hotline ('📞 +91 8112570656').\n"
        "• Currency Transparency: All rates and EMIs are quoted with ₹ symbols; terminology avoids complex banking jargon in favor of clear benefit statements ('Zero hidden charges', 'Paisa Vasool', 'Minimum paperwork').\n"
        "• Viral Hashtag Matrix: High-volume Indian hashtags mixed with niche finance tags (#LoanSolutions #InstaGood #ReelsOfInstagram #FYP #ReelsIndia #LoanExpert #LowInterestRate)."
    )

    # Section 7: Anti-Spam Safety
    add_custom_heading(doc, "7. Meta Anti-Spam & Operational Safety Framework", 1)
    add_callout(
        doc,
        "Zero-Ban Operating Principles",
        "Meta utilizes machine-learning velocity traps to detect automated behavior. Manvix AI is designed "
        "to be indistinguishable from human browsing by implementing variable delays, random bezier mouse curvatures, "
        "natural typing latency, and strict operational ceilings."
    )
    p_safe = doc.add_paragraph()
    p_safe.add_run(
        "1. Random Inter-Action Delays: 1.2s to 2.5s between contact selections in Share dialogs; 15s to 30s between follow requests.\n"
        "2. Typing Emulation: Character intervals randomized between 20ms and 50ms with occasional pauses.\n"
        "3. Cross-Platform Cooldowns: Mandatory 4s to 7s pause when switching between Instagram Direct and Facebook Messenger.\n"
        "4. Strict Session Quotas: Maximum 25 to 30 friend shares per post; maximum 50 follow requests per day per profile.\n"
        "5. Instant Kill-Switch: Immediate task termination via Telegram [🛑 Stop Task] button generating instant flag cancellation."
    )

    # Section 8: KPIs
    add_custom_heading(doc, "8. Business KPIs & Operational Success Metrics", 1)
    kpi_headers = ["Key Performance Indicator", "Measurement Standard", "Target Goal"]
    kpi_data = [
        ["Weekly Published Posts", "Total approved graphics & video reels posted to feeds", "14 to 28 posts / week"],
        ["Friend Share Reach Expansion", "Unique friends receiving direct post shares", "150 to 300 connections / week"],
        ["Outbound Follow Pipeline", "Target leads followed with extracted follower records", "250 to 500 leads / week"],
        ["Customer Acquisition Cost (CAC)", "Total ad spend required per inbound application", "₹0.00 (Zero ad spend)"],
        ["Account Longevity Rate", "Absence of automated action blocks or suspensions", "100% operational health"],
        ["Approval Turnaround", "Time from generation to mobile Telegram approval", "< 60 seconds"]
    ]
    t_kpi = doc.add_table(rows=len(kpi_data) + 1, cols=3)
    format_table(t_kpi, [2.3, 2.7, 1.9], kpi_headers, kpi_data)

    # Section 9: Risks
    add_custom_heading(doc, "9. Risk Analysis & Mitigation Matrix", 1)
    risk_headers = ["Risk Description", "Severity", "Automated Mitigation Strategy"]
    risk_data = [
        [
            "Meta UI Selector Mutation",
            "High",
            "Multi-tiered selector fallbacks (SVG aria-label, nearest button parent, DOM role='option', XPath)."
        ],
        [
            "Chrome Blank Screen / Freeze",
            "Medium",
            "Automated DOM health watchdog (is_blank_or_unrendered) triggers rehydration and refresh."
        ],
        [
            "Account Password Logout",
            "Medium",
            "Two-way Telegram password ingestion prompt auto-fills credentials directly into the active browser."
        ],
        [
            "Concurrent Task Collision",
            "Medium",
            "TaskQueueOrchestrator manages sequential worker locks and tab isolation on port 9222."
        ],
        [
            "Operational Misconfiguration",
            "Low",
            "revert_changes.bat allows instant 1-click hard or soft rollback to previous GitHub commits."
        ]
    ]
    t_risk = doc.add_table(rows=len(risk_data) + 1, cols=3)
    format_table(t_risk, [2.2, 1.2, 3.5], risk_headers, risk_data)

    # Section 10: Rollback
    add_custom_heading(doc, "10. 1-Click Rollback & Change Management Policy", 1)
    p_rb = doc.add_paragraph()
    p_rb.add_run(
        "To ensure continuous business operations without downtime, Manvix AI enforces a strict Change Management Policy:\n"
        "• All updates must be tracked in CHANGELOG_FEATURES.md with exact commit hashes.\n"
        "• An executable 1-click utility (revert_changes.bat) must always be present in the repository root.\n"
        "• Non-technical operators can restore the entire system to a known good state in under 5 seconds by selecting "
        "Option 2 in revert_changes.bat or issuing 'git reset --hard HEAD~1'."
    )

    doc.save(str(output_path))
    print(f"✅ Successfully generated BRD: {output_path} ({os.path.getsize(output_path)} bytes)")


# ==============================================================================
# 2. BUILD FRD (FUNCTIONAL REQUIREMENTS DOCUMENT)
# ==============================================================================
def generate_frd(output_path):
    print(f"Generating FRD at: {output_path}...")
    doc = Document()

    # Document Geometry
    sections = doc.sections
    for s in sections:
        s.top_margin = Inches(0.8)
        s.bottom_margin = Inches(0.8)
        s.left_margin = Inches(0.8)
        s.right_margin = Inches(0.8)

    # Title Page Block
    p_title_top = doc.add_paragraph()
    p_title_top.paragraph_format.space_before = Pt(40)
    r_sub = p_title_top.add_run("TECHNICAL SPECIFICATIONS & ARCHITECTURE MANUAL\n")
    r_sub.font.size = Pt(11)
    r_sub.font.color.rgb = COLOR_ACCENT
    r_sub.bold = True

    r_title = p_title_top.add_run("Functional Requirements Document (FRD)\n")
    r_title.font.size = Pt(26)
    r_title.font.color.rgb = COLOR_PRIMARY
    r_title.bold = True

    r_proj = p_title_top.add_run("Manvix AI: System Architecture, Data Models & Technical Modules\n")
    r_proj.font.size = Pt(16)
    r_proj.font.color.rgb = COLOR_SECONDARY

    p_meta = doc.add_paragraph()
    p_meta.paragraph_format.space_after = Pt(24)
    p_meta.add_run(
        "Document Version: 1.0.0 (Technical Release)\n"
        "Target Platforms: Next.js 14, Python 3.10+, Selenium WebDriver, Telegram Bot API, FFmpeg\n"
        "Database Architecture: Dual-Engine (PostgreSQL with SQLite Fallback)\n"
        "Chrome Debugging Port: 127.0.0.1:9222 (Shared Headful Browser Profile)\n"
        "Classification: Highly Technical — Developer & DevOps Reference"
    )

    add_callout(
        doc,
        "System Architectural Scope",
        "This Functional Requirements Document details the exact software architecture, component modules, "
        "browser DOM interaction algorithms, REST API schemas, database schemas, and state machines powering "
        "Manvix AI. It provides an exhaustive engineering reference ensuring every feature is fully documented."
    )

    doc.add_page_break()

    # Table of Contents
    add_custom_heading(doc, "Document Table of Contents", 1)
    toc_items = [
        "1. High-Level Technical Architecture & Component Map",
        "2. Module FR-01: Generative AI Media & 24s Video Engine",
        "3. Module FR-02: Chrome Shared Driver & DOM Resilience Subsystem",
        "4. Module FR-03: Multi-Platform Social Auto-Publishing Engine",
        "5. Module FR-04: Telegram Interactive Human-in-the-Loop Daemon",
        "6. Module FR-05: Social Growth & Instagram Target Follower Extractor",
        "7. Module FR-06: Posted Content Gallery & Human-Touch 'Share to All'",
        "8. Module FR-07: Multitasking Queue Orchestrator & Concurrency",
        "9. Module FR-08: Next.js Frontend Dashboard & REST API Endpoints",
        "10. Module FR-09: Complete Database Schema & Data Dictionary",
        "11. Module FR-10: Human Operator Anti-Detection Engine",
        "12. Module FR-11: 1-Click Rollback & Git Versioning Utility",
        "13. Requirements Traceability Matrix (RTM)",
    ]
    for item in toc_items:
        p_toc = doc.add_paragraph()
        p_toc.paragraph_format.space_after = Pt(2)
        r = p_toc.add_run(f"•  {item}")
        r.font.size = Pt(10)
        r.font.color.rgb = COLOR_DARK

    doc.add_page_break()

    # Section 1: Architecture
    add_custom_heading(doc, "1. High-Level Technical Architecture & Component Map", 1)
    p_arch = doc.add_paragraph()
    p_arch.add_run(
        "Manvix AI is structured as a decoupled, asynchronous three-tier platform:\n\n"
        "1. Presentation & API Layer (Next.js 14):\n"
        "   • Provides web dashboards (/campaigns, /generate, /growth, /accounts, /products).\n"
        "   • Hosts Next.js API route handlers (/api/generate, /api/campaigns, /api/growth, etc.).\n\n"
        "2. Core Automation Engine (Python 3.10+):\n"
        "   • Browser Controller: Selenium remote client attached to Chrome port 9222 with session re-use.\n"
        "   • Generative Engines: Gemini 1.5 Pro & Flash, OpenAI ChatGPT, Pillow graphics composer, FFmpeg video pipeline.\n"
        "   • Telegram Daemon: Long-polling bot poller with singleton process supervisor.\n"
        "   • TaskQueueOrchestrator: Priority worker queue with lock management and live telemetry.\n\n"
        "3. Data Persistence Layer:\n"
        "   • Primary: PostgreSQL (production high-concurrency database).\n"
        "   • Fallback / Local: SQLite (data/database.sqlite) with automatic schema initialization and failover."
    )

    # Section 2: FR-01 Media Engine
    add_custom_heading(doc, "2. Module FR-01: Generative AI Media & 24s Video Engine", 1)
    p_m1 = doc.add_paragraph()
    p_m1.add_run(
        "Files: automation/media/gemini_video_engine.py, automation/media/image_generator.py, automation/media/template_engine.py\n\n"
        "Technical Capabilities:\n"
        "• 24-Second Video Pipeline: Generates a 3-act sequential script: Hook Scene (0-8s) -> Value Offer (8-16s) -> Strong Call-to-Action (16-24s).\n"
        "• Aspect Ratio Conformity: Renders vertical 9:16 (1080x1920) for Instagram Reels and 1:1 (1080x1080) for feed posts.\n"
        "• Watermark & Brand Ingestion: Automatically composites 'Loan Solutions.png' in the top-left or top-right quadrant with clean alpha transparency.\n"
        "• FFmpeg Stitching Engine: Concatenates generated clips with crossfade transitions, overlays background audio, and burns animated subtitles with Rupee ₹ formatting."
    )

    # Section 3: FR-02 Chrome Driver
    add_custom_heading(doc, "3. Module FR-02: Chrome Shared Driver & DOM Resilience Subsystem", 1)
    p_m2 = doc.add_paragraph()
    p_m2.add_run(
        "File: automation/browser/driver.py\n\n"
        "Technical Specifications:\n"
        "• Remote Debugging Port 9222: Connects to an existing active Google Chrome process, preserving session cookies and login states.\n"
        "• Multi-Window Handle Management: Maintains a persistent mapping (platform_tabs) of window handles for Facebook, Instagram, ChatGPT, and Gemini.\n"
        "• Self-Healing Watchdog: 'is_blank_or_unrendered()' checks for zero interactive elements, missing React roots, or 'Aw, Snap' crash pages.\n"
        "• Auto-Rehydration: 'ensure_healthy_page()' fires synthetic window focus and visibilitychange DOM events, executing a clean refresh if blank white screen is detected."
    )

    # Section 4: FR-03 Social Publishing
    add_custom_heading(doc, "4. Module FR-03: Multi-Platform Social Auto-Publishing Engine", 1)
    p_m3 = doc.add_paragraph()
    p_m3.add_run(
        "Files: automation/social/facebook.py, automation/social/instagram.py, automation/social/linkedin.py\n\n"
        "Publishing Mechanics:\n"
        "• Facebook: Focuses feed composer on personal profile or Page, injects media into file upload input, types localized copy with keystroke jitter, and clicks 'Post'.\n"
        "• Instagram: Directs to instagram.com/create/style/, uploads image or reel MP4, selects 1:1 or 9:16 framing, injects caption with Line 1 CTA, and clicks 'Share'.\n"
        "• LinkedIn: Navigates to feed, opens modal composer, uploads media, and submits business post."
    )

    # Section 5: FR-04 Telegram Bot
    add_custom_heading(doc, "5. Module FR-04: Telegram Interactive Human-in-the-Loop Daemon", 1)
    p_m4 = doc.add_paragraph()
    p_m4.add_run(
        "Files: automation/telegram/poller.py, automation/telegram/bot.py\n\n"
        "Daemon Specifications:\n"
        "• Process Singleton Supervisor: 'ensure_single_poller_instance()' terminates duplicate poller PIDs on startup to avoid Telegram 409 conflict errors.\n"
        "• Interactive Review Cards: Renders photo/video previews with inline buttons: [Approve & Post], [Edit Caption], [Regenerate], [Reject].\n"
        "• Checkbox Platform Selection: Live toggling of target networks ([Facebook ✅], [Instagram ✅], [LinkedIn ⬜], [Select All]).\n"
        "• Password Ingestion: On detection of logged-out social accounts in Chrome, prompts user via Telegram message, ingests password, and pastes into browser textbox.\n"
        "• Telegram File Ingestion: Uploading photos or documents in Telegram automatically mirrors them to 'Loan Solutions.png' and updates product logos."
    )

    # Section 6: FR-05 Growth & Instagram Follows
    add_custom_heading(doc, "6. Module FR-05: Social Growth & Instagram Target Follower Extractor", 1)
    p_m5 = doc.add_paragraph()
    p_m5.add_run(
        "Files: automation/social/growth_orchestrator.py, automation/social/instagram_follow.py\n\n"
        "Feature Specifications:\n"
        "• Target User ID Follower Count Extractor: Navigates to instagram.com/<username>/, extracts total followers from header text or og:description meta tag (e.g. 11.3k, 106k).\n"
        "• Profile Privacy Detection: Distinguishes between Public and Private accounts; handles follow button variations ('Follow', 'Follow Back', 'Requested').\n"
        "• Lead Persistence: Saves username, follower count, status, and timestamp to 'instagram_leads_tracker.json' and SQLite table.\n"
        "• Facebook Friend Request Acceptor: Scans facebook.com/friends/requests/, automatically confirms pending requests, and likes recent posts.\n"
        "• Instagram Account Pruner: Scans following list and unfollows inactive or non-reciprocal accounts."
    )

    # Section 7: FR-06 Post Gallery & Share to All
    add_custom_heading(doc, "7. Module FR-06: Posted Content Gallery & Human-Touch 'Share to All'", 1)
    p_m6 = doc.add_paragraph()
    p_m6.add_run(
        "Files: automation/social/post_sharer.py, automation/telegram/bot.py, automation/telegram/poller.py\n\n"
        "Functional Specifications:\n"
        "• Unified Media Resolver: 'get_all_published_posts()' aggregates published campaigns and validates local disk media (39 verified posts).\n"
        "• Telegram Interactive Gallery: Renders photo/video with caption preview, share count, and pagination buttons ([Prev], [Next], [Share to All]).\n"
        "• Instagram Native Share Modal Controller:\n"
        "  - Navigates to target post or clicks latest profile thumbnail.\n"
        "  - Triggers native Share SVG ('Share Post' / 'Share').\n"
        "  - Identifies candidate contacts via 'div[role=\"option\"]' in topmost dialog.\n"
        "  - Sequentially selects friends with human pauses (1.2s – 2.5s) displaying tagged pills in 'To:' field.\n"
        "  - Dispatches post via native 'Send Separately' button.\n"
        "• Facebook Messenger Post Sharer: Selects recipients via facebook.com/messages/new, types message with keystroke jitter, and sends.\n"
        "• Database Tracking: Records all friend dispatches in 'post_shares_log' with real-time telemetry counters."
    )

    # Section 8: FR-07 Queue Orchestrator
    add_custom_heading(doc, "8. Module FR-07: Multitasking Queue Orchestrator & Concurrency", 1)
    p_m7 = doc.add_paragraph()
    p_m7.add_run(
        "File: automation/core/task_orchestrator.py\n\n"
        "Architecture & State Machine:\n"
        "• Concurrency Limit: Enforces strict sequential access to the shared Chrome port 9222 instance.\n"
        "• States: QUEUED -> RUNNING -> COMPLETED / FAILED / CANCELLED.\n"
        "• Collisions & Preemption: Safely queues outreach, content generation, and post sharing without browser crashes.\n"
        "• Telegram Queue Dashboard: /queue command renders active job, queued tasks, and [🛑 Stop Task] cancellation buttons."
    )

    # Section 9: FR-08 Next.js & REST APIs
    add_custom_heading(doc, "9. Module FR-08: Next.js Frontend Dashboard & REST API Endpoints", 1)
    api_headers = ["Endpoint URL", "Method", "Request Payload / Parameters", "Functional Description"]
    api_data = [
        ["/api/generate", "POST", "{ product_id, llm_provider, format }", "Triggers AI copy & media generation pipeline."],
        ["/api/campaigns", "GET", "?status=published&platform=all", "Returns list of all active marketing campaigns."],
        ["/api/campaigns/[id]", "PATCH", "{ status, approval_state }", "Approves, rejects, or modifies a campaign."],
        ["/api/growth", "POST", "{ platform, location, count, mode }", "Launches audience outreach or follower campaign."],
        ["/api/accounts", "GET / POST", "{ google_email, profile_dir }", "Manages registered Google Chrome accounts."],
        ["/api/telegram", "POST", "{ chat_id, message, action }", "Receives webhooks and dispatches bot notifications."],
        ["/api/browser", "GET", "?check=health", "Returns port 9222 browser status and tab state."]
    ]
    t_api = doc.add_table(rows=len(api_data) + 1, cols=4)
    format_table(t_api, [1.5, 0.8, 2.4, 2.3], api_headers, api_data)

    # Section 10: FR-09 Database Schemas
    add_custom_heading(doc, "10. Module FR-09: Complete Database Schema & Data Dictionary", 1)
    db_headers = ["Table Name", "Primary Columns & Types", "Purpose & Storage Engine"]
    db_data = [
        ["products", "id (UUID), name (TEXT), category, description, logo_path", "Product registry (Loan Solutions, etc.). PG & SQLite."],
        ["campaigns", "id (UUID), product_id, prompt, caption, media_paths, status", "Generated marketing campaigns & approval status."],
        ["post_shares_log", "id (INT PK), campaign_id, platform, recipient_name, status, created_at", "Audit log of all friend post shares across IG & FB."],
        ["chrome_accounts", "id (UUID), name, email, profile_dir, fb_page, ig_user", "Multi-profile Google Chrome account mapping."],
        ["outreach_logs", "id (UUID), platform, target_user, status, notes, timestamp", "Record of follow requests and friend requests dispatched."],
        ["social_groups", "id (UUID), platform, group_name, member_count, created_at", "Log of created social friend marketing groups."]
    ]
    t_db = doc.add_table(rows=len(db_data) + 1, cols=3)
    format_table(t_db, [1.5, 3.2, 2.3], db_headers, db_data)

    # Section 11: FR-10 Anti-Detection
    add_custom_heading(doc, "11. Module FR-10: Human Operator Anti-Detection Engine", 1)
    p_m10 = doc.add_paragraph()
    p_m10.add_run(
        "File: automation/browser/human_operator.py\n\n"
        "Technical Emulation Algorithms:\n"
        "• Bezier Curve Mouse Movement: Generates non-linear cursor paths with acceleration and deceleration mimicking human hand-eye coordination.\n"
        "• Keystroke Jitter: Emulates natural keyboarding with variable inter-key delays (20ms – 60ms) and random micro-pauses.\n"
        "• Natural Scroll Dynamics: Uses smooth incremental wheel movements and viewport pauses to simulate content reading.\n"
        "• DOM Element Centering: Calls scrollIntoView({block: 'center'}) before any element click to match human focus."
    )

    # Section 12: FR-11 Rollback
    add_custom_heading(doc, "12. Module FR-11: 1-Click Rollback & Git Versioning Utility", 1)
    p_m11 = doc.add_paragraph()
    p_m11.add_run(
        "Files: revert_changes.bat, CHANGELOG_FEATURES.md\n\n"
        "Rollback Implementation:\n"
        "• 1-Click Interactive Menu: Options for Soft Reset ('git reset --soft HEAD~1'), Hard Reset ('git reset --hard HEAD~1'), and selective feature rollback.\n"
        "• Clean Commit Parity: All features are packaged in atomic git commits pushed to origin/main (Commit d3923d2).\n"
        "• Audit Logging: Complete record of modified files and SHA hashes documented in CHANGELOG_FEATURES.md."
    )

    # Section 13: RTM Traceability Matrix
    add_custom_heading(doc, "13. Requirements Traceability Matrix (RTM)", 1)
    rtm_headers = ["BRD Requirement", "FRD Technical Module", "Source Code Implementation", "Verification Method"]
    rtm_data = [
        ["BR-01: Brand Watermark", "FR-01: Media Engine", "template_engine.py / gemini_video_engine.py", "Visual inspection of generated PNG & MP4."],
        ["BR-02: Indian Market Copy", "FR-01: Media Engine", "caption_helper.py / image_generator.py", "Caption contains ₹, line 1 CTA, Indian tags."],
        ["BR-03: Telegram Review", "FR-04: Telegram Daemon", "bot.py / poller.py", "Inline callback approve: and reject: handling."],
        ["BR-04: Password Ingestion", "FR-04: Telegram Daemon", "poller.py (handle_text_message)", "Password typed into Chrome login input."],
        ["BR-05: Target User Follows", "FR-05: Growth Engine", "instagram_follow.py", "Extracted 11.3k on @badshah_bhai__9186."],
        ["BR-06: Post Gallery", "FR-06: Post Sharer", "bot.py (send_posted_content_gallery)", "Telegram /posts renders media cards & pages."],
        ["BR-07: Human Share to All", "FR-06: Post Sharer", "post_sharer.py", "Selected 5 friends, dispatched 'Send Separately'."],
        ["BR-08: Multitasking Queue", "FR-07: Task Orchestrator", "task_orchestrator.py", "/queue dashboard lists jobs without collisions."],
        ["BR-09: 1-Click Rollback", "FR-11: Rollback Utility", "revert_changes.bat", "Interactive batch menu executes reset --hard."]
    ]
    t_rtm = doc.add_table(rows=len(rtm_data) + 1, cols=4)
    format_table(t_rtm, [1.8, 1.6, 2.0, 1.6], rtm_headers, rtm_data)

    doc.save(str(output_path))
    print(f"✅ Successfully generated FRD: {output_path} ({os.path.getsize(output_path)} bytes)")


if __name__ == "__main__":
    brd_path = DOCS_DIR / "Manvix_AI_Full_Project_BRD.docx"
    frd_path = DOCS_DIR / "Manvix_AI_Full_Project_FRD.docx"
    generate_brd(brd_path)
    generate_frd(frd_path)
