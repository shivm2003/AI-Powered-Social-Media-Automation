"""
Image Generation Engine.
Creates high-converting branded social media graphics with Pillow.
Supports 6 distinct programmatic design layouts, platform aspect ratios
(1:1, 4:5, 9:16, 16:9), custom palettes, logos, and badges.
"""
import os
import random
import uuid
from pathlib import Path
import logging
from config import IMAGES_DIR

logger = logging.getLogger("automation.media.image")

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logger.warning("Pillow not installed. Run: pip install Pillow")

ASPECT_RATIO_DIMS = {
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
}


def hex_to_rgb(hex_code, default=(124, 92, 252)):
    if not hex_code:
        return default
    hex_code = hex_code.lstrip("#")
    if len(hex_code) == 6:
        try:
            return tuple(int(hex_code[i : i + 2], 16) for i in (0, 2, 4))
        except Exception:
            return default
    return default


def get_font(size, bold=False):
    """Load best available system fonts across Windows/Linux."""
    font_names = (
        ["arialbd.ttf", "segoeuib.ttf", "calibrib.ttf", "DejaVuSans-Bold.ttf", "arial.ttf"]
        if bold else
        ["segoeui.ttf", "arial.ttf", "calibri.ttf", "DejaVuSans.ttf"]
    )
    for fn in font_names:
        try:
            return ImageFont.truetype(fn, size)
        except Exception:
            continue
    return ImageFont.load_default()


def wrap_text(text, max_chars=32):
    """Word wraps text into list of lines."""
    words = (text or "").split()
    lines = []
    cur = []
    cur_len = 0
    for w in words:
        if cur_len + len(w) + 1 <= max_chars:
            cur.append(w)
            cur_len += len(w) + 1
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
            cur_len = len(w)
    if cur:
        lines.append(" ".join(cur))
    return lines


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT 1: Dark Glassmorphism with Glowing Radials
# ─────────────────────────────────────────────────────────────────────────────
def render_dark_glassmorphism(width, height, primary, secondary, product_name, headline, subheadline, category, cta_text):
    canvas = Image.new("RGBA", (width, height), (15, 17, 26, 255))
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d_overlay = ImageDraw.Draw(overlay)

    # Gradient glows
    for r in range(min(width, height) // 2, 0, -15):
        alpha1 = int(50 * (1 - r / (min(width, height) // 2)))
        alpha2 = int(40 * (1 - r / (min(width, height) // 2)))
        d_overlay.ellipse((-r + width // 4, -r + height // 4, r + width // 4, r + height // 4), fill=(*primary, alpha1))
        d_overlay.ellipse((width - width // 4 - r, height - height // 4 - r, width - width // 4 + r, height - height // 4 + r), fill=(*secondary, alpha2))

    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)

    card_mx = int(width * 0.08)
    card_my = int(height * 0.12)
    card_box = (card_mx, card_my, width - card_mx, height - card_my)

    card_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    c_draw = ImageDraw.Draw(card_layer)
    c_draw.rounded_rectangle(card_box, radius=int(min(width, height) * 0.04), fill=(255, 255, 255, 15), outline=(255, 255, 255, 45), width=2)
    canvas = Image.alpha_composite(canvas, card_layer)
    draw = ImageDraw.Draw(canvas)

    left_x = card_box[0] + int(width * 0.06)
    cur_y = card_box[1] + int(height * 0.06)

    # Category Pill
    pill_text = f"•  {(category or 'FEATURED').upper()}  •"
    pill_h = int(min(width, height) * 0.042)
    pill_w = max(int(len(pill_text) * 11), 160)
    draw.rounded_rectangle((left_x, cur_y, left_x + pill_w, cur_y + pill_h), radius=pill_h // 2, fill=(*primary, 110), outline=(*secondary, 180), width=1)
    draw.text((left_x + 16, cur_y + int(pill_h * 0.18)), pill_text, fill=(240, 240, 255), font=get_font(int(min(width, height) * 0.024), bold=True))
    cur_y += pill_h + int(height * 0.04)

    # Product Name
    draw.text((left_x, cur_y), product_name, fill=(255, 255, 255), font=get_font(int(min(width, height) * 0.055), bold=True))
    cur_y += int(min(width, height) * 0.08)

    # Headline
    for l in wrap_text(headline, max_chars=32)[:2]:
        draw.text((left_x, cur_y), l, fill=(*secondary, 255), font=get_font(int(min(width, height) * 0.042), bold=True))
        cur_y += int(min(width, height) * 0.052)
    cur_y += int(min(width, height) * 0.02)

    # Subheadline
    for l in wrap_text(subheadline, max_chars=44)[:2]:
        draw.text((left_x, cur_y), l, fill=(210, 215, 235), font=get_font(int(min(width, height) * 0.028)))
        cur_y += int(min(width, height) * 0.038)

    # CTA Button
    cta_w = max(int(width * 0.40), 220)
    cta_h = int(min(width, height) * 0.072)
    cta_top = card_box[3] - cta_h - int(height * 0.055)
    draw.rounded_rectangle((left_x, cta_top, left_x + cta_w, cta_top + cta_h), radius=cta_h // 2, fill=(*primary, 240), outline=(*secondary, 220), width=2)
    draw.text((left_x + int(cta_w * 0.14), cta_top + int(cta_h * 0.22)), cta_text, fill=(255, 255, 255), font=get_font(int(min(width, height) * 0.030), bold=True))
    return canvas


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT 2: Split-Screen Modern (Color Block Contrast)
# ─────────────────────────────────────────────────────────────────────────────
def render_split_screen_modern(width, height, primary, secondary, product_name, headline, subheadline, category, cta_text):
    canvas = Image.new("RGBA", (width, height), (18, 20, 29, 255))
    draw = ImageDraw.Draw(canvas)

    # Top/Left diagonal block
    split_h = int(height * 0.46)
    draw.rectangle((0, 0, width, split_h), fill=(*primary, 255))

    # Decorative geometric circles
    draw.ellipse((width - int(width * 0.35), -int(height * 0.1), width + int(width * 0.2), int(height * 0.45)), fill=(*secondary, 40))

    # Top Brand Header
    draw.text((int(width * 0.08), int(height * 0.06)), f"★  {(category or 'SOLUTIONS').upper()}", fill=(255, 255, 255, 220), font=get_font(int(min(width, height) * 0.024), bold=True))
    draw.text((int(width * 0.08), int(height * 0.11)), product_name, fill=(255, 255, 255), font=get_font(int(min(width, height) * 0.062), bold=True))

    # Headline inside top block
    top_y = int(height * 0.21)
    for l in wrap_text(headline, max_chars=30)[:2]:
        draw.text((int(width * 0.08), top_y), l, fill=(255, 255, 255), font=get_font(int(min(width, height) * 0.040), bold=True))
        top_y += int(min(width, height) * 0.052)

    # Bottom Content Card
    bottom_y = split_h + int(height * 0.06)
    card_mx = int(width * 0.08)
    card_w = width - (card_mx * 2)

    # Feature points
    features = [
        f"✓  {subheadline[:55]}" if subheadline else "✓  Instant processing with zero hidden fees",
        "✓  100% verified, trusted & highly rated",
        "✓  Fast turnaround & 24/7 dedicated assistance",
    ]
    cur_y = bottom_y
    for feat in features:
        draw.rounded_rectangle((card_mx, cur_y, card_mx + card_w, cur_y + int(height * 0.07)), radius=10, fill=(255, 255, 255, 12), outline=(255, 255, 255, 25))
        draw.text((card_mx + 20, cur_y + int(height * 0.018)), feat, fill=(225, 230, 245), font=get_font(int(min(width, height) * 0.027)))
        cur_y += int(height * 0.085)

    # CTA Button
    cta_h = int(min(width, height) * 0.075)
    cta_w = max(int(width * 0.50), 240)
    cta_top = height - cta_h - int(height * 0.08)
    draw.rounded_rectangle((card_mx, cta_top, card_mx + cta_w, cta_top + cta_h), radius=8, fill=(*secondary, 255))
    draw.text((card_mx + int(cta_w * 0.12), cta_top + int(cta_h * 0.25)), cta_text, fill=(15, 20, 30), font=get_font(int(min(width, height) * 0.032), bold=True))
    return canvas


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT 3: Neo-Brutalist & Pop (High Contrast & Badges)
# ─────────────────────────────────────────────────────────────────────────────
def render_neo_brutalist_pop(width, height, primary, secondary, product_name, headline, subheadline, category, cta_text):
    # Vibrant light pastel background
    canvas = Image.new("RGBA", (width, height), (248, 246, 240, 255))
    draw = ImageDraw.Draw(canvas)

    # Thick brutalist border
    border_thick = 8
    draw.rectangle((0, 0, width, height), outline=(20, 20, 20), width=border_thick)

    # Category Ribbon Badge
    badge_w = int(width * 0.55)
    badge_h = int(min(width, height) * 0.055)
    bx = int(width * 0.08)
    by = int(height * 0.08)
    # Drop shadow
    draw.rectangle((bx + 6, by + 6, bx + badge_w + 6, by + badge_h + 6), fill=(20, 20, 20))
    draw.rectangle((bx, by, bx + badge_w, by + badge_h), fill=(*primary, 255), outline=(20, 20, 20), width=3)
    draw.text((bx + 18, by + 8), f"★ {(category or 'OFFICIAL').upper()}", fill=(255, 255, 255), font=get_font(int(min(width, height) * 0.026), bold=True))

    # Main brutalist card with offset shadow
    cx = int(width * 0.08)
    cy = int(height * 0.18)
    cw = width - (cx * 2)
    ch = int(height * 0.60)
    # Black shadow box
    draw.rounded_rectangle((cx + 10, cy + 10, cx + cw + 10, cy + ch + 10), radius=12, fill=(20, 20, 20))
    # Foreground yellow/white box
    draw.rounded_rectangle((cx, cy, cx + cw, cy + ch), radius=12, fill=(255, 255, 255), outline=(20, 20, 20), width=4)

    # Product Name inside card
    draw.text((cx + 30, cy + 30), product_name, fill=(20, 20, 20), font=get_font(int(min(width, height) * 0.058), bold=True))

    # Headline inside card
    hy = cy + int(min(width, height) * 0.11)
    for l in wrap_text(headline, max_chars=28)[:3]:
        draw.text((cx + 30, hy), l, fill=(*primary, 255), font=get_font(int(min(width, height) * 0.046), bold=True))
        hy += int(min(width, height) * 0.056)

    # Subheadline
    hy += 10
    for l in wrap_text(subheadline, max_chars=36)[:2]:
        draw.text((cx + 30, hy), l, fill=(80, 80, 90), font=get_font(int(min(width, height) * 0.030)))
        hy += int(min(width, height) * 0.040)

    # Neo-Brutalist CTA Button
    btn_w = int(cw * 0.65)
    btn_h = int(min(width, height) * 0.085)
    btn_x = cx + 30
    btn_y = cy + ch - btn_h - 30

    draw.rounded_rectangle((btn_x + 6, btn_y + 6, btn_x + btn_w + 6, btn_y + btn_h + 6), radius=8, fill=(20, 20, 20))
    draw.rounded_rectangle((btn_x, btn_y, btn_x + btn_w, btn_y + btn_h), radius=8, fill=(*secondary, 255), outline=(20, 20, 20), width=3)
    draw.text((btn_x + 25, btn_y + int(btn_h * 0.22)), cta_text, fill=(20, 20, 20), font=get_font(int(min(width, height) * 0.034), bold=True))

    return canvas


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT 4: Minimalist Scandinavian Light (Ultra-Clean Luxury)
# ─────────────────────────────────────────────────────────────────────────────
def render_minimalist_light(width, height, primary, secondary, product_name, headline, subheadline, category, cta_text):
    canvas = Image.new("RGBA", (width, height), (252, 252, 253, 255))
    draw = ImageDraw.Draw(canvas)

    mx = int(width * 0.10)
    my = int(height * 0.12)

    # Subtle top accent bar
    draw.rectangle((mx, my, mx + int(width * 0.12), my + 6), fill=(*primary, 255))

    # Category Subtitle
    draw.text((mx, my + 24), (category or "PREMIUM SOLUTION").upper(), fill=(140, 145, 160), font=get_font(int(min(width, height) * 0.024), bold=True))

    # Product Name
    draw.text((mx, my + int(height * 0.08)), product_name, fill=(25, 30, 45), font=get_font(int(min(width, height) * 0.062), bold=True))

    # Headline
    hy = my + int(height * 0.18)
    for l in wrap_text(headline, max_chars=32)[:3]:
        draw.text((mx, hy), l, fill=(*primary, 255), font=get_font(int(min(width, height) * 0.046), bold=True))
        hy += int(min(width, height) * 0.058)

    # Elegant divider line
    hy += 15
    draw.line((mx, hy, width - mx, hy), fill=(225, 230, 240), width=2)
    hy += 25

    # Subheadline
    for l in wrap_text(subheadline, max_chars=46)[:3]:
        draw.text((mx, hy), l, fill=(100, 110, 130), font=get_font(int(min(width, height) * 0.030)))
        hy += int(min(width, height) * 0.042)

    # Clean CTA Pill
    cta_w = int(width * 0.45)
    cta_h = int(min(width, height) * 0.075)
    cta_y = height - my - cta_h
    draw.rounded_rectangle((mx, cta_y, mx + cta_w, cta_y + cta_h), radius=cta_h // 2, fill=(25, 30, 45), outline=(*primary, 255), width=2)
    draw.text((mx + int(cta_w * 0.15), cta_y + int(cta_h * 0.22)), cta_text, fill=(255, 255, 255), font=get_font(int(min(width, height) * 0.030), bold=True))
    return canvas


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT 5: Feature Cards & Stat Spotlight
# ─────────────────────────────────────────────────────────────────────────────
def render_stat_and_feature_cards(width, height, primary, secondary, product_name, headline, subheadline, category, cta_text):
    canvas = Image.new("RGBA", (width, height), (20, 24, 38, 255))
    draw = ImageDraw.Draw(canvas)

    mx = int(width * 0.08)
    cur_y = int(height * 0.08)

    # Top Brand Pill
    pill_text = f"⚡ {(category or 'EXCLUSIVE').upper()}"
    pill_h = int(min(width, height) * 0.045)
    pill_w = max(int(len(pill_text) * 12), 170)
    draw.rounded_rectangle((mx, cur_y, mx + pill_w, cur_y + pill_h), radius=pill_h // 2, fill=(*secondary, 60), outline=(*secondary, 200), width=1)
    draw.text((mx + 18, cur_y + 8), pill_text, fill=(*secondary, 255), font=get_font(int(min(width, height) * 0.024), bold=True))
    cur_y += pill_h + int(height * 0.03)

    # Product Name & Headline
    draw.text((mx, cur_y), product_name, fill=(255, 255, 255), font=get_font(int(min(width, height) * 0.052), bold=True))
    cur_y += int(min(width, height) * 0.07)

    for l in wrap_text(headline, max_chars=32)[:2]:
        draw.text((mx, cur_y), l, fill=(240, 245, 255), font=get_font(int(min(width, height) * 0.040), bold=True))
        cur_y += int(min(width, height) * 0.050)

    cur_y += int(height * 0.02)

    # Large Highlight Metric Card
    box_w = width - (mx * 2)
    box_h = int(height * 0.18)
    draw.rounded_rectangle((mx, cur_y, mx + box_w, cur_y + box_h), radius=14, fill=(*primary, 200), outline=(255, 255, 255, 60), width=2)
    draw.text((mx + 25, cur_y + 20), "★ 100% VERIFIED & TRUSTED", fill=(*secondary, 255), font=get_font(int(min(width, height) * 0.026), bold=True))
    stat_sub = subheadline or "Fast approvals, zero hidden fees, and transparent terms."
    draw.text((mx + 25, cur_y + int(box_h * 0.45)), stat_sub[:70], fill=(255, 255, 255), font=get_font(int(min(width, height) * 0.027)))
    cur_y += box_h + int(height * 0.04)

    # Two side-by-side chips
    chip_w = (box_w - 20) // 2
    chip_h = int(height * 0.10)
    draw.rounded_rectangle((mx, cur_y, mx + chip_w, cur_y + chip_h), radius=10, fill=(255, 255, 255, 12), outline=(255, 255, 255, 30))
    draw.text((mx + 15, cur_y + 12), "✓ Fast Response", fill=(255, 255, 255), font=get_font(int(min(width, height) * 0.025), bold=True))
    draw.text((mx + 15, cur_y + 40), "Quick 24/7 service", fill=(180, 190, 210), font=get_font(int(min(width, height) * 0.022)))

    draw.rounded_rectangle((mx + chip_w + 20, cur_y, mx + box_w, cur_y + chip_h), radius=10, fill=(255, 255, 255, 12), outline=(255, 255, 255, 30))
    draw.text((mx + chip_w + 35, cur_y + 12), "✓ 0 Hidden Fees", fill=(255, 255, 255), font=get_font(int(min(width, height) * 0.025), bold=True))
    draw.text((mx + chip_w + 35, cur_y + 40), "Transparent process", fill=(180, 190, 210), font=get_font(int(min(width, height) * 0.022)))

    # CTA Button
    cta_h = int(min(width, height) * 0.075)
    cta_w = max(int(width * 0.48), 240)
    cta_top = height - cta_h - int(height * 0.07)
    draw.rounded_rectangle((mx, cta_top, mx + cta_w, cta_top + cta_h), radius=cta_h // 2, fill=(*secondary, 255))
    draw.text((mx + int(cta_w * 0.14), cta_top + int(cta_h * 0.22)), cta_text, fill=(15, 20, 30), font=get_font(int(min(width, height) * 0.030), bold=True))
    return canvas


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT 6: Editorial Magazine Banner
# ─────────────────────────────────────────────────────────────────────────────
def render_magazine_banner(width, height, primary, secondary, product_name, headline, subheadline, category, cta_text):
    canvas = Image.new("RGBA", (width, height), (12, 14, 20, 255))
    draw = ImageDraw.Draw(canvas)

    # Frame border
    draw.rectangle((20, 20, width - 20, height - 20), outline=(*primary, 150), width=3)

    mx = int(width * 0.08)
    cur_y = int(height * 0.09)

    # Top Issue Label
    draw.text((mx, cur_y), f"EDITION / {(category or 'SPOTLIGHT').upper()}", fill=(*secondary, 255), font=get_font(int(min(width, height) * 0.022), bold=True))
    cur_y += int(height * 0.05)

    # Massive Headline banner block
    draw.text((mx, cur_y), product_name.upper(), fill=(255, 255, 255), font=get_font(int(min(width, height) * 0.068), bold=True))
    cur_y += int(min(width, height) * 0.09)

    for l in wrap_text(headline, max_chars=28)[:3]:
        draw.text((mx, cur_y), l, fill=(*primary, 255), font=get_font(int(min(width, height) * 0.050), bold=True))
        cur_y += int(min(width, height) * 0.060)

    cur_y += int(height * 0.03)

    # Quote block
    quote_box = (mx, cur_y, width - mx, cur_y + int(height * 0.18))
    draw.rectangle(quote_box, fill=(255, 255, 255, 10), outline=(255, 255, 255, 30), width=1)
    qy = cur_y + 20
    for l in wrap_text(f'"{subheadline or "Empowering individuals and growing enterprises with dependable solutions."}"', max_chars=42)[:3]:
        draw.text((mx + 25, qy), l, fill=(220, 225, 240), font=get_font(int(min(width, height) * 0.028)))
        qy += int(min(width, height) * 0.038)

    # Bottom Full-width Ribbon CTA
    ribbon_h = int(min(width, height) * 0.085)
    ribbon_y = height - ribbon_h - 20
    draw.rectangle((20, ribbon_y, width - 20, height - 20), fill=(*primary, 255))
    draw.text((mx, ribbon_y + int(ribbon_h * 0.25)), f"▶  {cta_text.upper()}", fill=(255, 255, 255), font=get_font(int(min(width, height) * 0.032), bold=True))
    return canvas


# Master Layout Registry
LAYOUT_RENDERERS = [
    render_dark_glassmorphism,
    render_split_screen_modern,
    render_neo_brutalist_pop,
    render_minimalist_light,
    render_stat_and_feature_cards,
    render_magazine_banner,
]


def generate_social_image(
    product_name: str,
    headline: str,
    subheadline: str = "",
    brand_colors: dict = None,
    aspect_ratio: str = "1:1",
    cta_text: str = "Learn More →",
    logo_path: str = None,
    category: str = "Featured Solution",
    visual_style: str = "auto",
) -> Path:
    """
    Renders an eye-catching, branded social graphic using one of 6 distinct design layouts.
    Rotates layouts dynamically to ensure visual freshness across thousands of graphics.
    """
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    width, height = ASPECT_RATIO_DIMS.get(aspect_ratio, (1080, 1080))

    out_filename = f"{uuid.uuid4().hex[:12]}_{aspect_ratio.replace(':', 'x')}.png"
    out_path = IMAGES_DIR / out_filename

    if not HAS_PIL:
        with open(out_path, "wb") as f:
            f.write(b"PNG-DUMMY")
        return out_path

    colors = brand_colors or {}
    primary = hex_to_rgb(colors.get("primary", "#7C5CFC"))
    secondary = hex_to_rgb(colors.get("secondary", "#3DD6D0"))

    # Clean CTA text
    clean_cta = (cta_text or "Learn More").replace("➜", "->").replace("→", "->").replace("âžœ", "->").strip()
    if not clean_cta.endswith("->") and not clean_cta.endswith(">"):
        clean_cta = f"{clean_cta} ->"

    # Select Layout based on style or random rotation
    vs = (visual_style or "auto").lower()
    if "minimal" in vs:
        renderer = render_minimalist_light
    elif "neo" in vs or "bold" in vs:
        renderer = render_neo_brutalist_pop
    elif "split" in vs or "corp" in vs:
        renderer = render_split_screen_modern
    elif "stat" in vs or "info" in vs:
        renderer = render_stat_and_feature_cards
    elif "mag" in vs or "edit" in vs:
        renderer = render_magazine_banner
    elif "glass" in vs or "3d" in vs:
        renderer = render_dark_glassmorphism
    else:
        # Auto-diversify: choose randomly among the 6 diverse layouts!
        renderer = random.choice(LAYOUT_RENDERERS)

    canvas = renderer(
        width=width,
        height=height,
        primary=primary,
        secondary=secondary,
        product_name=product_name or "Featured Product",
        headline=headline or f"Discover {product_name}",
        subheadline=subheadline or "Dependable solutions designed for your growth.",
        category=category,
        cta_text=clean_cta,
    )

    # Optional Logo insertion
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo_size = int(min(width, height) * 0.10)
            logo.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)
            canvas.paste(logo, (width - logo.width - int(width * 0.05), int(height * 0.05)), logo)
        except Exception as e:
            logger.warning(f"Failed to render logo: {e}")

    final_img = canvas.convert("RGB")
    final_img.save(out_path, quality=95)
    logger.info(f"Generated multi-template social image at {out_path} using {renderer.__name__}")
    return out_path
