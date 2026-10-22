"""
Trending Keywords & Viral Hashtag Engine for Facebook and Instagram.
Provides dynamic, fresh, and algorithm-optimized hashtags and SEO keywords
tailored to Indian audiences, maximizing viral reach for image and video posts.
"""
import random
import re
from typing import List, Dict

# ─────────────────────────────────────────────────────────────────────────────
# VIRAL HASHTAG TAXONOMY (Tailored for Indian Middle-Class & Viral Algorithms)
# ─────────────────────────────────────────────────────────────────────────────

HASHTAG_POOLS: Dict[str, Dict[str, List[str]]] = {
    "finance": {
        # High-volume algorithmic triggers (Explore / For You / Reels)
        "viral_anchors": [
            "#Viral",
            "#Trending",
            "#ExplorePage",
            "#ReelsIndia",
            "#ViralReels",
            "#FYP",
            "#TrendingNow",
            "#InstaGood",
            "#DailyTrending",
            "#ReelsOfInstagram",
        ],
        # High-intent conversion & keyword search tags
        "niche_keywords": [
            "#LoanSolutions",
            "#PersonalLoan",
            "#HomeLoanIndia",
            "#InstantLoan",
            "#LowEMI",
            "#EasyLoanApproval",
            "#QuickDisbursal",
            "#BusinessLoanIndia",
            "#ZeroPaperwork",
            "#LowInterestRate",
            "#LoanExpert",
            "#SmartBorrowing",
            "#OnlineLoanApp",
            "#InstantCashIndia",
        ],
        # Emotional & demographic community tags (India-centric)
        "community_intent": [
            "#ApnaGhar",
            "#FinancialFreedom",
            "#IndianMiddleClass",
            "#DreamHome",
            "#FamilySecurity",
            "#SapnoKaGhar",
            "#SalariedIndia",
            "#PaisaVasool",
            "#SmartFinance",
            "#IndiaRising",
        ],
        # Facebook-optimized focused topical tags
        "facebook_focused": [
            "#LoanSolutions",
            "#PersonalLoan",
            "#HomeLoan",
            "#FinancialSecurity",
            "#LowEMI",
            "#InstantApproval",
            "#ApnaGhar",
            "#India",
        ],
    },
    "general": {
        "viral_anchors": [
            "#Viral",
            "#Trending",
            "#ExplorePage",
            "#ReelsIndia",
            "#TrendingNow",
            "#MadeInIndia",
            "#FYP",
        ],
        "niche_keywords": [
            "#BusinessGrowth",
            "#Innovation",
            "#TrustedBrand",
            "#IndianEntrepreneurs",
            "#StartupIndia",
            "#VocalForLocal",
            "#SmartSolutions",
        ],
        "community_intent": [
            "#IndianMiddleClass",
            "#IndiaLife",
            "#DesiLifestyle",
            "#FamilyFirst",
            "#QualityLife",
        ],
        "facebook_focused": [
            "#MadeInIndia",
            "#BusinessGrowth",
            "#Innovation",
            "#TrustedSolutions",
            "#India",
        ],
    },
}

# High-CTR SEO keywords to rank in Meta graph search & explore feed recommendations
SEO_KEYWORDS: Dict[str, List[str]] = {
    "finance": [
        "Instant Approval in Minutes",
        "Lowest EMI in ₹",
        "Zero Hidden Fees",
        "Direct Bank Account Disbursal",
        "Minimal Paperwork 100% Digital",
        "Apna Ghar Home Loan",
        "Hassle-Free Personal Loan",
        "Flexible Repayment Tenures",
    ],
    "general": [
        "Exclusive Limited Time Offer",
        "Trusted by Thousands Across India",
        "Top-Rated Quality & Service",
        "Easy & Hassle-Free Experience",
        "100% Satisfaction Guaranteed",
    ],
}


def get_fresh_trending_hashtags(
    platform: str = "instagram",
    category: str = "finance",
    existing_tags: List[str] = None,
    max_count: int = None
) -> List[str]:
    """
    Dynamically generates a fresh, randomized, and algorithm-optimized set
    of viral hashtags for the specified platform.
    
    Guarantees diversity on each call so consecutive posts do not repeat
    identical sequences (protects against Instagram shadowbans).
    """
    cat_key = "finance" if ("loan" in category.lower() or "finance" in category.lower()) else "general"
    pool = HASHTAG_POOLS.get(cat_key, HASHTAG_POOLS["general"])
    platform_clean = platform.lower().strip()

    selected = []

    # Include existing tags if passed
    if existing_tags:
        for t in existing_tags:
            tag_clean = t if t.startswith("#") else f"#{t}"
            if tag_clean not in selected:
                selected.append(tag_clean)

    if platform_clean == "facebook":
        target_count = max_count or random.randint(6, 8)
        # Facebook favors clean, focused topical tags
        fb_pool = list(pool.get("facebook_focused", []))
        random.shuffle(fb_pool)
        for t in fb_pool:
            if t not in selected:
                selected.append(t)
            if len(selected) >= target_count:
                break
    else:
        # Instagram favors rich 12-16 tag mix: anchors + niche + community
        target_count = max_count or random.randint(12, 16)

        # 1. Mandatory brand anchor
        if cat_key == "finance" and "#LoanSolutions" not in selected:
            selected.insert(0, "#LoanSolutions")

        # 2. Pick 3-4 viral algorithmic anchors
        anchors = list(pool.get("viral_anchors", []))
        random.shuffle(anchors)
        for t in anchors[:4]:
            if t not in selected and len(selected) < target_count:
                selected.append(t)

        # 3. Pick 5-7 niche keywords
        niche = list(pool.get("niche_keywords", []))
        random.shuffle(niche)
        for t in niche[:6]:
            if t not in selected and len(selected) < target_count:
                selected.append(t)

        # 4. Pick 3-4 community intent tags
        comm = list(pool.get("community_intent", []))
        random.shuffle(comm)
        for t in comm[:4]:
            if t not in selected and len(selected) < target_count:
                selected.append(t)

    return selected[:target_count]


def enrich_caption_with_trending_hashtags(
    caption: str,
    platform: str = "instagram",
    category: str = "finance"
) -> str:
    """
    Inspects caption and ensures it has a rich, fresh set of platform-optimized
    viral hashtags. If existing hashtags are sparse (< 4), supplements with fresh trending tags.
    """
    if not caption:
        tags = get_fresh_trending_hashtags(platform=platform, category=category)
        return " ".join(tags)

    # Extract existing hashtags
    existing_tags = re.findall(r"#\w+", caption)

    # If already has plenty of hashtags (>= 8 for IG or >= 5 for FB), return as-is
    threshold = 5 if platform.lower() == "facebook" else 8
    if len(existing_tags) >= threshold:
        return caption.strip()

    # Otherwise, generate fresh trending tags to reach optimal virality
    needed_count = 7 if platform.lower() == "facebook" else 14
    fresh_tags = get_fresh_trending_hashtags(
        platform=platform,
        category=category,
        existing_tags=existing_tags,
        max_count=needed_count
    )

    # Strip existing hashtags from caption body so we can format them cleanly at the end
    body_without_tags = re.sub(r"#\w+", "", caption)
    body_without_tags = re.sub(r"\n{3,}", "\n\n", body_without_tags).strip()

    tag_block = " ".join(fresh_tags)
    return f"{body_without_tags}\n\n{tag_block}".strip()
