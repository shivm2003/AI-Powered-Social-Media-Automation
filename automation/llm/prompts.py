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

    prompt = f"""You are an elite creative director and social media copywriter.
Generate high-converting, viral social media content for the following product:

Product Name: {product_name}
Category: {category}
Product Description: {description}
Target Audience: {target_audience}
Key Benefits: {benefits_str}
Tone of Voice: {tone}
Language: {language}
Call to Action: {cta}
Target Social Media Platforms: {platforms_str}
Content Format: {content_type} (e.g. image post, reel/video, carousel)
{f"Additional Instructions: {custom_instructions}" if custom_instructions else ""}

Please provide your response strictly in the following JSON structure without extra markdown quotes:
{{
  "caption": "The complete engaging caption with hook, value propositions, line breaks, emojis, and call to action",
  "short_caption": "A concise 1-2 sentence version suitable for Twitter or WhatsApp status",
  "hashtags": ["#Tag1", "#Tag2", "#Tag3", "#Tag4", "#Tag5"],
  "headline": "A punchy 4-7 word headline to put directly on the image/video graphic",
  "subheadline": "A compelling 1-line subtext for the visual banner",
  "visual_prompt": "A detailed visual description for AI image generation (lighting, colors, composition, vibe, product placement)",
  "video_script_slides": [
    {{"slide": 1, "text": "Hook text (0-3s)", "visual": "Description of first visual"}},
    {{"slide": 2, "text": "Problem & Solution (3-8s)", "visual": "Description of second visual"}},
    {{"slide": 3, "text": "Key Benefits (8-12s)", "visual": "Description of third visual"}},
    {{"slide": 4, "text": "Call to action (12-15s)", "visual": "Logo and CTA button"}}
  ]
}}
"""
    return prompt
