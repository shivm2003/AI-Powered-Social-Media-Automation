"""
Prompt builder for generating viral social media posts and image/video directions.
"""

def build_social_prompt(
    product_name: str,
    description: str,
    category: str,
    target_audience: str,
    key_benefits: list,
    tone: str,
    language: str,
    cta: str,
    platforms: list,
    content_type: str = "image",
    custom_instructions: str = ""
) -> str:
    benefits_str = ", ".join(key_benefits) if isinstance(key_benefits, list) else str(key_benefits)
    platforms_str = ", ".join(platforms) if isinstance(platforms, list) else str(platforms)

    is_loan = "loan" in product_name.lower() or "loan" in description.lower() or category.lower() == "finance"
    loan_rule = "\n4. Mandatory Apply Link: The caption MUST start with this exact application link at the very beginning (Line 1): '👉 Apply Now: https://loansolutions.everythingrental.in/application'" if is_loan else ""
    caption_desc = "The complete engaging caption starting with Line 1: '👉 Apply Now: https://loansolutions.everythingrental.in/application', followed by hook, value propositions, Indian Rupee benefits, line breaks, emojis, and hashtags" if is_loan else "The complete engaging caption tailored for an Indian audience with hook, value propositions, Indian Rupee benefits, line breaks, emojis, and call to action"

    prompt = f"""You are an elite creative director and social media copywriter specialized in high-converting Indian market campaigns.
Generate high-converting, viral social media content strictly adhering to Indian standards (Indian middle-class families, Indian Rupee ₹ currency, authentic domestic aspirations):

Product Name: {product_name}
Category: {category}
Product Description: {description}
Target Audience: {target_audience or 'Indian middle-class families, salaried professionals, and entrepreneurs'}
Key Benefits: {benefits_str}
Tone of Voice: {tone}
Language: {language}
Call to Action: {cta}
Target Social Media Platforms: {platforms_str}
Content Format: {content_type} (e.g. image post, reel/video, carousel)
{f"Additional Instructions: {custom_instructions}" if custom_instructions else ""}

CRITICAL INDIAN STANDARDS & RULES:
1. Currency Standard: Strictly use the Indian Rupee symbol (₹, INR, Lakhs, Crores, e.g. '₹5 Lakhs', 'EMIs starting at ₹2,999/month'). NEVER use dollar signs ($) or foreign currencies.
2. Demographics & Theme: Center around relatable Indian middle-class families, warm contemporary Indian homes, dream home ownership (Apna Ghar), family financial security, and personal aspirations.
3. Visual Direction: The visual_prompt must describe authentic, relatable Indian individuals/families in a contemporary Indian setting with Indian Rupee (₹) elements. Clean commercial advertising quality, no messy text in the artwork.{loan_rule}

Please provide your response strictly in the following JSON structure without extra markdown quotes:
{{
  "caption": "{caption_desc}",
  "short_caption": "A concise 1-2 sentence version in Indian Rupee standards suitable for Twitter or WhatsApp status",
  "hashtags": ["#ViralReels", "#ExplorePage", "#LoanSolutions", "#PersonalLoan", "#HomeLoanIndia", "#LowEMI", "#ApnaGhar", "#TrendingNow"],
  "headline": "A punchy 4-7 word headline to put directly on the image/video graphic",
  "subheadline": "A compelling 1-line subtext for the visual banner",
  "visual_prompt": "A detailed visual description for AI image generation featuring authentic Indian middle-class subjects, Indian Rupee (₹) accents, warm lighting, and clean composition",
  "video_script_slides": [
    {{"slide": 1, "text": "Hook text (0-3s)", "visual": "Description of first visual"}},
    {{"slide": 2, "text": "Problem & Solution (3-8s)", "visual": "Description of second visual"}},
    {{"slide": 3, "text": "Key Benefits (8-12s)", "visual": "Description of third visual"}},
    {{"slide": 4, "text": "Call to action (12-15s)", "visual": "Logo and CTA button"}}
  ]
}}
"""
    return prompt
