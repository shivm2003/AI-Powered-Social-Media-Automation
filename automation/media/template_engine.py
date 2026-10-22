"""
Template & Creative Variation Matrix Engine.
Generates thousands of unique, context-aware visual design prompts and layouts
for social media graphics and AI image generation (ChatGPT / DALL-E / Gemini).
"""
import random
import uuid

# 12+ Core Creative Design Archetypes
DESIGN_ARCHETYPES = {
    "lifestyle": {
        "name": "Authentic Indian Lifestyle Photography",
        "description": "Candid, relatable real-world moment showing an Indian middle-class family enjoying benefits",
        "keywords": [
            "candid Indian commercial lifestyle photography",
            "relatable Indian middle-class family in warm contemporary living room",
            "authentic emotion, warm smiling Indian expressions",
            "natural high-end editorial shot with warm sunlit daylight",
            "unposed realistic Indian family interaction and joy",
        ]
    },
    "minimal": {
        "name": "Minimalist Scandinavian Luxury",
        "description": "Ultra-clean aesthetic with vast negative space, refined textures and understated elegance",
        "keywords": [
            "minimalist Scandinavian editorial aesthetic",
            "vast clean negative space, museum-quality simplicity",
            "soft natural daylight casting gentle shadows",
            "organic matte textures, architectural geometry",
            "refined luxury brand composition",
        ]
    },
    "neo_brutalist": {
        "name": "Neo-Brutalist & Streetwear Pop",
        "description": "High-contrast bold geometry, saturated colors, thick outlines, and sticker-badge vibe",
        "keywords": [
            "modern neo-brutalist graphic design aesthetic",
            "high contrast color blocking with punchy saturated tones",
            "stark geometric layout, bold framing, modern streetwear vibe",
            "creative graphic design trend with dynamic badges",
            "crisp typography-inspired shapes, visual punch",
        ]
    },
    "3d_tech": {
        "name": "Sleek 3D Glassmorphism & Isometric",
        "description": "Futuristic tactile glass, glowing holographic UI components and isometric 3D models",
        "keywords": [
            "sleek 3D isometric commercial design",
            "translucent frosted glassmorphism elements with refractive materials",
            "floating holographic tech interface details, tactile metallic accents",
            "vibrant ambient colored rim lighting, Unreal Engine 5 render feel",
            "modern Octane render, crystal clear reflections",
        ]
    },
    "infographic": {
        "name": "Visual Split Comparison & Infographic",
        "description": "Clear visual comparison, before-and-after, or key benefits highlighted dynamically",
        "keywords": [
            "clean commercial infographic visual layout",
            "split comparison visual metaphor showing transformation",
            "crisp checkmarks, metric badge callouts, organized hierarchy",
            "modern high-converting marketing breakdown",
            "visual clarity, bold focal points, trustworthy layout",
        ]
    },
    "corporate": {
        "name": "Authoritative Corporate & FinTech",
        "description": "Sophisticated navy, gold, marble, and sleek architectural lines exuding trust",
        "keywords": [
            "executive corporate commercial advertising",
            "sleek modern high-rise glass architecture backdrop",
            "trustworthy, authoritative, premium institutional finish",
            "subtle gold and deep navy prestige color accents",
            "Forbes and Bloomberg editorial advertising look",
        ]
    },
    "editorial": {
        "name": "High-Fashion & Magazine Editorial",
        "description": "Striking artistic angles, Vogue/GQ studio lighting, high fashion color contrast",
        "keywords": [
            "high-fashion commercial studio editorial",
            "dramatic studio lighting, soft key light with sharp rim light",
            "art-directed visual harmony, magazine cover grade framing",
            "vivid high-end commercial grade detail",
            "bold artistic direction, sophisticated symmetry",
        ]
    },
    "vintage": {
        "name": "Retro 90s Film & Nostalgia",
        "description": "Analog film warmth, subtle grain, vintage color palettes and nostalgic warmth",
        "keywords": [
            "vintage 90s commercial aesthetic with Kodak Portra warmth",
            "subtle analog film grain, rich saturated amber and teal tones",
            "retro-modern resurgence, nostalgic warm lens flare",
            "tactile physical texture, authentic retro appeal",
        ]
    },
    "pop_art": {
        "name": "Vibrant Pop-Art & Illustrated",
        "description": "Comic book halftones, bold color bursts, energetic action lines",
        "keywords": [
            "contemporary commercial pop-art graphic illustration",
            "halftone dots, electric saturated color bursts",
            "high-energy visual punch, dynamic diagonal composition",
            "playful, viral-worthy, modern digital vector illustration",
        ]
    },
    "cinematic": {
        "name": "Cinematic Storytelling & Mood",
        "description": "Anamorphic widescreen lens feel, dramatic chiaroscuro and atmospheric depth",
        "keywords": [
            "cinematic commercial frame, anamorphic lens flare",
            "dramatic chiaroscuro lighting, deep shadows and glowing highlights",
            "shallow depth of field with creamy bokeh background",
            "atmospheric haze, Hollywood commercial movie frame",
        ]
    },
    "product_hero": {
        "name": "Studio Product Hero Podium",
        "description": "Product displayed on an elegant podium with luxury studio backdrop",
        "keywords": [
            "luxury product showcase on sculptural minimalist podium",
            "studio beauty lighting, soft diffused reflections",
            "subtle botanical shadows in background, textured stone pedestal",
            "premium retail commercial hero advertisement",
        ]
    },
    "bold_geometric": {
        "name": "Bold Typographic & Geometric Poster",
        "description": "Heavy geometric layout, swiss graphic style, visual hierarchy and color harmony",
        "keywords": [
            "Swiss graphic design international typographic style",
            "bold modular grid with striking visual balance",
            "vibrant contrasting hues, clean Bauhaus-inspired geometry",
            "award-winning brand identity advertisement",
        ]
    }
}

# 15+ Composition & Angle Perspectives
COMPOSITION_ANGLES = [
    "dynamic eye-level candid shot capturing natural perspective",
    "overhead bird's-eye flat-lay layout with organized aesthetic arrangement",
    "45-degree isometric heroic perspective showcasing depth and dimension",
    "dramatic low-angle heroic shot looking upward for power and confidence",
    "close-up macro focus on crisp textural details with soft background blur",
    "centered symmetrical composition with strong leading lines",
    "rule-of-thirds off-center layout creating dynamic breathing space",
    "wide environmental shot situating the subject in a beautiful modern setting",
    "Dutch tilt diagonal angle conveying speed, innovation, and excitement",
    "split-frame dual perspective highlighting contrast and transformation",
    "framing through architectural foreground elements for cinematic depth",
    "clean modular grid composition with harmonious negative margins",
    "portrait orientation with vertical visual flow and clear focal hierarchy",
    "sweeping curved flow drawing the viewer's gaze through the key elements",
    "layered depth with foreground, midground focal point, and soft ambient background",
]

# 12+ Lighting & Atmospheric Moods
LIGHTING_MOODS = [
    "golden hour natural sunlight casting warm long shadows and amber glow",
    "diffused softbox studio lighting eliminating harsh glare with soft falloff",
    "crisp high-key bright commercial lighting with pure vibrant clarity",
    "dramatic rim lighting outlining silhouettes against a moody background",
    "vibrant dual-tone colored gel lighting with cyan and magenta accents",
    "early morning soft overcast daylight for crisp, honest, clean rendering",
    "subtle cyberpunk neon accents glowing gently in a modern space",
    "dramatic chiaroscuro with high contrast between deep shadows and key light",
    "warm indoor ambient lighting with cozy, inviting, approachable atmosphere",
    "clean Scandinavian natural light filtering through sheer modern blinds",
    "sleek exhibition spotlight isolating the central subject with focused prestige",
    "sun-dappled organic lighting with botanical leaf shadows dancing gently",
]

# 10+ Color Palette Themes
COLOR_THEMES = [
    "deep midnight navy with radiant gold and crisp white accents",
    "fresh energetic electric purple, turquoise, and subtle coral highlights",
    "warm earthy terracotta, olive green, and soft ivory tones",
    "sleek monochrome graphite and slate with a single intense brand neon accent",
    "sunset gradient blending warm crimson, radiant orange, and golden amber",
    "crisp oceanic teal, cobalt blue, and frosted silver",
    "modern pastel mint, lavender, and buttercup yellow with crisp dark contrast",
    "luxurious champagne, matte black, and burnished bronze",
    "vibrant tropical citrus palette with lime, mango orange, and cobalt",
    "pure clinical white, soft cloud grey, and authoritative medical/fintech azure",
]

# Domain-specific Context Enhancers tailored for Indian Market & Middle-Class Aspirations
DOMAIN_CONTEXTS = {
    "finance": [
        "Authentic happy Indian middle-class family (smiling parents and cheerful child) sitting together on a comfortable sofa in their bright modern Indian apartment living room, joyfully celebrating their dream home loan approval with relief, subtle glowing 3D Indian Rupee symbol (₹) and trusted green checkmark badge in background",
        "Delighted Indian couple holding the keys to their dream new home during Griha Pravesh moment on their sunlit balcony, warm golden hour glow, financial security concept with glowing Indian Rupee (₹) growth accent",
        "Hardworking Indian small business owner / shopkeeper smiling with immense pride in his thriving, colorful retail store, holding a smartphone displaying instant business loan approval in Indian Rupees (₹ Lakhs)",
        "Affectionate Indian parents celebrating their daughter's college admission, studying with a modern laptop, happy family securing education loan with Indian Rupee (₹) emblem",
        "Confident Indian salaried professional checking digital banking loan approval notification on smartphone displaying Indian Rupee (₹) disbursement, modern Indian urban apartment backdrop",
        "Smiling Indian family posing happily beside their brand new family car in a pleasant Indian residential neighborhood, hassle-free auto loan with low Indian Rupee (₹) monthly EMI accent",
        "Respectable Indian financial advisor with warm pleasant smile explaining easy EMI loan options to an appreciative Indian middle-class couple in a modern glass office",
    ],
    "software": [
        "holographic analytics dashboard floating seamlessly above modern glass workspace with Indian Rupee (₹) growth metrics",
        "collaborative startup team celebrating milestone in sun-drenched modern Bangalore / Gurgaon tech hub loft",
        "sleek laptop displaying intelligent automated workflows with glowing connectivity nodes and Rupee financial tracking",
        "modern developer workspace with curved monitors, ambient light strips, and clean code graphics",
    ],
    "service": [
        "dedicated Indian professional specialist delivering top-tier service with warm confident smile in modern environment",
        "clock and speed visual metaphor representing instant 24/7 turnaround and hassle-free assistance for Indian clients",
        "relieved Indian middle-class customer experiencing seamless five-star service experience",
        "modern tablet displaying instant one-tap booking and glowing five-star review badge with Indian Rupee pricing",
    ],
    "ecommerce": [
        "premium unboxing experience with branded packaging, luxury tissue wrap, and glowing festive ribbon",
        "satisfied Indian customer receiving package at door of modern Indian home with bright sunny smile",
        "curated flat-lay showcase of lifestyle essentials surrounding the hero product with Indian festive accents",
        "express delivery box with wings and speed motion lines arriving at contemporary Indian porch",
    ],
    "healthcare": [
        "compassionate modern healthcare professional in clean bright modern clinic serving Indian family",
        "radiant healthy Indian individual full of energy enjoying outdoor morning sunlight in park",
        "cutting-edge medical science visualization with clean white and calm cyan hues",
        "peace of mind visual metaphor with hands cradling a glowing green health emblem for family security",
    ],
    "education": [
        "engaged Indian student mastering new skill on sleek tablet in inspiring library cafe",
        "glowing graduation cap and upward trending learning milestone charts with proud Indian parents",
        "interactive digital blackboard with futuristic holographic learning modules",
        "confident Indian professional receiving accredited certificate of achievement",
    ],
}


def get_archetype_key(visual_style: str = None) -> str:
    """Maps user-selected visualStyle string to available archetypes or picks random."""
    if not visual_style or visual_style in ["auto", "random", "diversify"]:
        return random.choice(list(DESIGN_ARCHETYPES.keys()))

    vs = visual_style.lower().strip()
    if vs in DESIGN_ARCHETYPES:
        return vs
    # Fuzzy mappings
    if "photo" in vs or "real" in vs:
        return random.choice(["lifestyle", "product_hero", "editorial"])
    if "mini" in vs:
        return "minimal"
    if "bold" in vs:
        return random.choice(["neo_brutalist", "bold_geometric"])
    if "3d" in vs or "tech" in vs:
        return "3d_tech"
    if "corp" in vs or "biz" in vs or "finance" in vs:
        return "corporate"
    if "grad" in vs:
        return random.choice(["neo_brutalist", "pop_art", "3d_tech"])
    if "illust" in vs or "art" in vs:
        return random.choice(["pop_art", "vintage"])

    return random.choice(list(DESIGN_ARCHETYPES.keys()))


def build_diverse_visual_prompt(
    product_name: str,
    description: str = "",
    category: str = "service",
    visual_style: str = "auto",
    aspect_ratio: str = "1:1",
    brand_colors: dict = None,
    platforms: list = None,
    custom_instructions: str = "",
    skill_image_path: str = None,
) -> dict:
    """
    Builds a rich, highly diverse visual prompt for ChatGPT / DALL-E / Gemini.
    Strictly tailored to Indian standards (Indian middle-class families, Indian Rupee ₹ currency,
    authentic domestic aspirations, and clean commercial advertising quality).
    """
    platforms = platforms or ["facebook", "instagram"]
    archetype_key = get_archetype_key(visual_style)
    archetype = DESIGN_ARCHETYPES.get(archetype_key, DESIGN_ARCHETYPES["lifestyle"])

    # Pick randomized attributes
    selected_angle = random.choice(COMPOSITION_ANGLES)
    selected_lighting = random.choice(LIGHTING_MOODS)
    selected_color_theme = random.choice(COLOR_THEMES)

    # Pick domain context
    cat_lower = (category or "service").lower()
    matched_domain = None
    for k in DOMAIN_CONTEXTS:
        if k in cat_lower or (k == "finance" and ("loan" in product_name.lower() or "loan" in description.lower())):
            matched_domain = k
            break
    if not matched_domain:
        matched_domain = "finance" if "loan" in product_name.lower() or "bank" in product_name.lower() else "service"

    domain_scene = random.choice(DOMAIN_CONTEXTS.get(matched_domain, DOMAIN_CONTEXTS["service"]))

    # Aspect ratio description
    ar_desc = {
        "1:1": "1:1 square Instagram/Facebook feed format",
        "4:5": "4:5 vertical portrait social post format",
        "9:16": "9:16 full-screen vertical Story/Reel format",
        "16:9": "16:9 landscape social banner format",
    }.get(aspect_ratio, "1:1 square aspect ratio")

    # Brand color hints
    color_hint = ""
    if brand_colors and any(brand_colors.values()):
        color_hint = f"Incorporate brand accents ({brand_colors.get('primary', '#7C5CFC')}, {brand_colors.get('secondary', '#3DD6D0')}) naturally into the scene."
    else:
        color_hint = f"Color harmony: {selected_color_theme}."

    # Assemble unique image prompt with strict visual purity & Indian standards
    unique_seed = uuid.uuid4().hex[:6]
    image_prompt = (
        f"Generate a masterclass commercial advertising graphic for '{product_name}' [Style Variant #{unique_seed}].\n"
        f"• Target Demographic & Cultural Context: Authentic Indian middle-class family and individuals. Warm, relatable, respectful, and contemporary Indian home or business setting with natural smiling expressions.\n"
        f"• Currency Standard: Indian Rupee (₹). Any currency symbols, digital banking screens, approval badges, or visual coin accents MUST show the Indian Rupee symbol '₹' (NEVER use US Dollar '$' or foreign currency). All financial scales in Indian standards (₹, Lakhs).\n"
        f"• Core Subject & Scene: {domain_scene}.\n"
        f"• Product Context: {description[:130] if description else product_name}.\n"
        f"• Design Archetype: {archetype['name']} — {', '.join(archetype['keywords'][:3])}.\n"
        f"• Camera & Framing: {selected_angle}.\n"
        f"• Lighting & Atmosphere: {selected_lighting}.\n"
        f"• Color Palette: {color_hint}\n"
        f"• Format: {ar_desc}, commercial 8k resolution, ultra-clean commercial advertising quality, no watermark.\n"
        f"• TEXT RULE: Absolutely NO hashtags (#...), NO paragraphs, NO descriptions, and NO tiny text painted on the image canvas. Keep the graphic 100% clean, uncluttered visual artwork."
    )

    if custom_instructions and custom_instructions.strip():
        image_prompt += f"\n• Special User Instructions: {custom_instructions.strip()}."

    if skill_image_path:
        image_prompt += f"\n• Attached Reference Branding: The official brand image for '{product_name}' is uploaded into this conversation. Harmonize the visual concept, color palette, and styling with this branding."

    is_loan = "loan" in product_name.lower() or "loan" in description.lower() or category.lower() == "finance"
    apply_cta_rule = "\nMandatory Call-to-Action Link: You MUST start the post caption at the very beginning (Line 1) with this exact application link: 👉 Apply Now: https://loansolutions.everythingrental.in/application" if is_loan else ""

    # Assemble complete unified prompt with strict visual vs. text copy separation for Indian audience
    unified_prompt = (
        f"--- TASK 1: CLEAN VISUAL ARTWORK (IMAGE GENERATION) ---\n"
        f"{image_prompt}\n"
        f"CRITICAL: Do NOT draw or paint hashtags (#...) or long descriptive text inside the image. The image must be clean visual art.\n\n"
        f"--- TASK 2: SOCIAL MEDIA POST (IN CHAT TEXT BELOW THE IMAGE ONLY) ---\n"
        f"In your text reply beneath the image, write the social media post tailored for an Indian middle-class audience:\n"
        f"Headline: A compelling, emotional hook for {product_name} celebrating family dreams, financial security, and easy approvals\n"
        f"Caption: An engaging 2-3 paragraph marketing copy highlighting trust, transparent process, low monthly EMIs in Indian Rupees (₹), quick disbursal, and a clear call-to-action.{apply_cta_rule}\n"
        f"Hashtags: Fresh, high-volume viral hashtags and SEO keywords tailored for {', '.join(platforms)} to maximize reach on Instagram and Facebook (e.g. #ExplorePage #ViralReels #LoanSolutions #PersonalLoan #LowEMI #ApnaGhar #FinancialFreedom - written ONLY here in text, NEVER painted inside the image)."
    )

    return {
        "archetype": archetype_key,
        "archetype_name": archetype["name"],
        "image_prompt": image_prompt,
        "unified_prompt": unified_prompt,
        "lighting": selected_lighting,
        "composition": selected_angle,
        "seed": unique_seed,
    }
