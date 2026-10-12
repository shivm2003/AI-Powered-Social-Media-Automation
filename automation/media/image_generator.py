"""
Image Generation Engine.
Creates high-converting branded social media graphics with Pillow.
Supports platform aspect ratios (1:1, 4:5, 9:16, 16:9), custom palettes, logos, and badges.
"""
import os
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


def create_gradient_canvas(width, height, color1, color2, bg_dark=(15, 17, 26)):
    """Creates a sleek, rich dark-gradient canvas with glowing radial accents."""
    base = Image.new("RGBA", (width, height), (*bg_dark, 255))
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Gradient glow top-left (color1)
    for r in range(min(width, height) // 2, 0, -15):
        alpha = int(45 * (1 - r / (min(width, height) // 2)))
        draw.ellipse(
            (-r + width // 4, -r + height // 4, r + width // 4, r + height // 4),
            fill=(*color1, alpha)
        )

    # Gradient glow bottom-right (color2)
    for r in range(min(width, height) // 2, 0, -15):
        alpha = int(35 * (1 - r / (min(width, height) // 2)))
        draw.ellipse(
            (width - width // 4 - r, height - height // 4 - r, width - width // 4 + r, height - height // 4 + r),
            fill=(*color2, alpha)
        )

    return Image.alpha_composite(base, overlay)


def generate_social_image(
    product_name: str,
    headline: str,
    subheadline: str = "",
    brand_colors: dict = None,
    aspect_ratio: str = "1:1",
    cta_text: str = "Learn More →",
    logo_path: str = None,
    category: str = "Featured Solution"
) -> Path:
    """
    Renders an eye-catching, branded social graphic.
    """
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    width, height = ASPECT_RATIO_DIMS.get(aspect_ratio, (1080, 1080))

    out_filename = f"{uuid.uuid4().hex[:12]}_{aspect_ratio.replace(':', 'x')}.png"
    out_path = IMAGES_DIR / out_filename

    if not HAS_PIL:
        # Fallback dummy file
        with open(out_path, "wb") as f:
            f.write(b"PNG-DUMMY")
        return out_path

    colors = brand_colors or {}
    primary = hex_to_rgb(colors.get("primary", "#7C5CFC"))
    secondary = hex_to_rgb(colors.get("secondary", "#3DD6D0"))

    canvas = create_gradient_canvas(width, height, primary, secondary)
    draw = ImageDraw.Draw(canvas)

    # Draw central glassmorphic card
    card_margin_x = int(width * 0.08)
    card_margin_y = int(height * 0.12)
    card_box = (
        card_margin_x,
        card_margin_y,
        width - card_margin_x,
        height - card_margin_y
    )

    card_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    card_draw = ImageDraw.Draw(card_layer)
    card_draw.rounded_rectangle(
        card_box,
        radius=int(min(width, height) * 0.04),
        fill=(255, 255, 255, 14),
        outline=(255, 255, 255, 40),
        width=2
    )
    canvas = Image.alpha_composite(canvas, card_layer)
    draw = ImageDraw.Draw(canvas)

    # Load system fonts if possible
    def get_font(size):
        for font_name in ["arialbd.ttf", "arial.ttf", "segoeui.ttf", "calibri.ttf", "DejaVuSans.ttf"]:
            try:
                return ImageFont.truetype(font_name, size)
            except Exception:
                continue
        return ImageFont.load_default()

    font_badge = get_font(int(min(width, height) * 0.024))
    font_title = get_font(int(min(width, height) * 0.055))
    font_headline = get_font(int(min(width, height) * 0.042))
    font_sub = get_font(int(min(width, height) * 0.028))
    font_cta = get_font(int(min(width, height) * 0.030))

    cur_y = card_box[1] + int(height * 0.06)
    left_x = card_box[0] + int(width * 0.06)

    # Category Pill Badge
    pill_text = f"✦  {category.upper()}  ✦"
    pill_w = int(len(pill_text) * 10)
    pill_h = int(min(width, height) * 0.04)
    draw.rounded_rectangle(
        (left_x, cur_y, left_x + pill_w, cur_y + pill_h),
        radius=pill_h // 2,
        fill=(*primary, 90),
        outline=(*secondary, 150),
        width=1
    )
    draw.text((left_x + 14, cur_y + 6), pill_text, fill=(240, 240, 255), font=font_badge)
    cur_y += pill_h + int(height * 0.04)

    # Product Name
    draw.text((left_x, cur_y), product_name, fill=(255, 255, 255), font=font_title)
    cur_y += int(min(width, height) * 0.08)

    # Punchy Headline (wrapped if needed)
    headline_text = headline or f"Unlock Next-Gen Results With {product_name}"
    draw.text((left_x, cur_y), headline_text[:65], fill=(*secondary, 255), font=font_headline)
    cur_y += int(min(width, height) * 0.07)

    # Subheadline
    sub_text = subheadline or "Supercharge productivity and elevate your brand presence."
    draw.text((left_x, cur_y), sub_text[:90], fill=(200, 205, 225), font=font_sub)
    cur_y += int(min(width, height) * 0.09)

    # Decorative divider
    draw.line((left_x, cur_y, width - left_x, cur_y), fill=(255, 255, 255, 30), width=2)
    cur_y += int(min(width, height) * 0.05)

    # Call to Action Button
    cta_w = int(width * 0.38)
    cta_h = int(min(width, height) * 0.07)
    cta_top = card_box[3] - cta_h - int(height * 0.06)

    draw.rounded_rectangle(
        (left_x, cta_top, left_x + cta_w, cta_top + cta_h),
        radius=int(cta_h // 2),
        fill=(*primary, 240),
        outline=(*secondary, 200),
        width=2
    )
    draw.text(
        (left_x + int(cta_w * 0.15), cta_top + int(cta_h * 0.22)),
        cta_text,
        fill=(255, 255, 255),
        font=font_cta
    )

    # Optional Logo insertion
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo_size = int(min(width, height) * 0.12)
            logo.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)
            canvas.paste(logo, (card_box[2] - logo.width - int(width * 0.04), card_box[1] + int(height * 0.04)), logo)
        except Exception as e:
            logger.warning(f"Failed to render logo: {e}")

    # Convert to RGB and save
    final_img = canvas.convert("RGB")
    final_img.save(out_path, quality=95)
    logger.info(f"Generated social image at {out_path}")
    return out_path
