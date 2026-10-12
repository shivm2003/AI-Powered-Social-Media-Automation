// Platform configuration — defines what fields each social platform needs
export const PLATFORMS = {
  facebook: {
    name: "Facebook",
    icon: "📘",
    color: "hsl(220, 46%, 48%)",
    colorMuted: "hsla(220, 46%, 48%, 0.15)",
    fields: [
      { key: "email", label: "Email / Phone", type: "text", required: true, placeholder: "your@email.com or phone number" },
      { key: "password", label: "Password", type: "password", required: true, placeholder: "••••••••" },
      { key: "page_name", label: "Page Name", type: "text", required: false, placeholder: "Your Facebook Page (optional)" },
    ],
    contentTypes: ["text", "image", "video", "carousel"],
    maxCaption: 63206,
    aspectRatios: ["1:1", "4:5", "16:9"],
  },
  instagram: {
    name: "Instagram",
    icon: "📷",
    color: "hsl(333, 79%, 53%)",
    colorMuted: "hsla(333, 79%, 53%, 0.15)",
    fields: [
      { key: "username", label: "Username", type: "text", required: true, placeholder: "@yourusername" },
      { key: "password", label: "Password", type: "password", required: true, placeholder: "••••••••" },
      { key: "account_type", label: "Account Type", type: "select", required: true, options: ["personal", "professional"], defaultValue: "professional" },
    ],
    contentTypes: ["image", "video", "carousel"],
    maxCaption: 2200,
    aspectRatios: ["1:1", "4:5", "9:16"],
  },
  linkedin: {
    name: "LinkedIn",
    icon: "💼",
    color: "hsl(201, 100%, 35%)",
    colorMuted: "hsla(201, 100%, 35%, 0.15)",
    fields: [
      { key: "email", label: "Email", type: "text", required: true, placeholder: "your@email.com" },
      { key: "password", label: "Password", type: "password", required: true, placeholder: "••••••••" },
      { key: "profile_type", label: "Profile Type", type: "select", required: true, options: ["personal", "organization"], defaultValue: "personal" },
      { key: "org_name", label: "Organization Name", type: "text", required: false, placeholder: "Org name (if organization)", showIf: { field: "profile_type", value: "organization" } },
    ],
    contentTypes: ["text", "image", "video", "carousel"],
    maxCaption: 3000,
    aspectRatios: ["1:1", "16:9"],
  },
  whatsapp: {
    name: "WhatsApp",
    icon: "💬",
    color: "hsl(142, 70%, 40%)",
    colorMuted: "hsla(142, 70%, 40%, 0.15)",
    fields: [
      { key: "phone", label: "Phone Number", type: "text", required: true, placeholder: "+91 XXXXXXXXXX" },
    ],
    contentTypes: ["text", "image", "video"],
    maxCaption: 700,
    aspectRatios: ["1:1", "9:16"],
    loginNote: "WhatsApp requires QR code scanning. Click 'Test Login' to open WhatsApp Web and scan the QR code with your phone.",
  },
};

// LLM providers
export const LLM_PROVIDERS = {
  gemini: {
    name: "Google Gemini",
    icon: "🌟",
    color: "hsl(210, 80%, 55%)",
    colorMuted: "hsla(210, 80%, 55%, 0.15)",
    url: "https://gemini.google.com",
    capabilities: ["text", "image", "code"],
    description: "Google's most capable AI model with multimodal understanding",
  },
  chatgpt: {
    name: "OpenAI ChatGPT",
    icon: "🤖",
    color: "hsl(160, 60%, 45%)",
    colorMuted: "hsla(160, 60%, 45%, 0.15)",
    url: "https://chatgpt.com",
    capabilities: ["text", "image", "code"],
    description: "Advanced language model with DALL-E image generation",
  },
  claude: {
    name: "Anthropic Claude",
    icon: "🧠",
    color: "hsl(25, 85%, 55%)",
    colorMuted: "hsla(25, 85%, 55%, 0.15)",
    url: "https://claude.ai",
    capabilities: ["text", "code"],
    description: "Thoughtful AI assistant with strong reasoning capabilities",
  },
};

// Content types
export const CONTENT_TYPES = {
  text: { name: "Text Post", icon: "📝", description: "Text-only social media post" },
  image: { name: "Image Post", icon: "🖼️", description: "Image with caption" },
  video: { name: "Video", icon: "🎬", description: "Short-form video content" },
  carousel: { name: "Carousel", icon: "🎠", description: "Multiple images in one post" },
};

// Tone options
export const TONES = [
  { value: "professional", label: "Professional" },
  { value: "casual", label: "Casual" },
  { value: "friendly", label: "Friendly" },
  { value: "bold", label: "Bold" },
  { value: "inspirational", label: "Inspirational" },
  { value: "humorous", label: "Humorous" },
  { value: "formal", label: "Formal" },
];

// CTA options
export const CTA_OPTIONS = [
  { value: "learn_more", label: "Learn More" },
  { value: "sign_up", label: "Sign Up" },
  { value: "buy_now", label: "Buy Now" },
  { value: "contact_us", label: "Contact Us" },
  { value: "download", label: "Download" },
  { value: "visit_website", label: "Visit Website" },
  { value: "book_now", label: "Book Now" },
  { value: "custom", label: "Custom" },
];

// Visual styles
export const VISUAL_STYLES = [
  { value: "minimal", label: "Minimal", description: "Clean, simple design" },
  { value: "bold", label: "Bold", description: "Eye-catching, vibrant" },
  { value: "gradient", label: "Gradient", description: "Smooth color gradients" },
  { value: "photorealistic", label: "Photo-realistic", description: "Natural looking" },
  { value: "illustrated", label: "Illustrated", description: "Hand-drawn or digital art" },
  { value: "corporate", label: "Corporate", description: "Business-professional" },
];

// Languages
export const LANGUAGES = [
  { value: "english", label: "English" },
  { value: "hindi", label: "Hindi" },
  { value: "both", label: "Both (Bilingual)" },
];

// Product categories
export const PRODUCT_CATEGORIES = [
  { value: "service", label: "Service" },
  { value: "software", label: "Software" },
  { value: "physical", label: "Physical Product" },
  { value: "finance", label: "Financial Service" },
  { value: "education", label: "Education" },
  { value: "healthcare", label: "Healthcare" },
  { value: "ecommerce", label: "E-Commerce" },
  { value: "other", label: "Other" },
];

// Campaign statuses
export const CAMPAIGN_STATUSES = {
  draft: { label: "Draft", color: "default", icon: "📝" },
  generating: { label: "Generating", color: "info", icon: "⏳" },
  preview_sent: { label: "Pending Approval", color: "warning", icon: "📱" },
  approved: { label: "Approved", color: "success", icon: "✅" },
  posting: { label: "Posting...", color: "info", icon: "🚀" },
  posted: { label: "Published", color: "success", icon: "🎉" },
  rejected: { label: "Rejected", color: "danger", icon: "❌" },
  revision: { label: "Revision Requested", color: "warning", icon: "✏️" },
};

// Aspect ratios with dimensions
export const ASPECT_RATIOS = {
  "1:1": { label: "1:1 Square", width: 1080, height: 1080 },
  "4:5": { label: "4:5 Portrait", width: 1080, height: 1350 },
  "9:16": { label: "9:16 Story/Reel", width: 1080, height: 1920 },
  "16:9": { label: "16:9 Landscape", width: 1920, height: 1080 },
};

// Campaign objective options
export const CAMPAIGN_OBJECTIVES = [
  { value: "awareness", label: "Brand Awareness" },
  { value: "leads", label: "Lead Generation" },
  { value: "sales", label: "Sales / Conversions" },
  { value: "engagement", label: "Engagement" },
  { value: "traffic", label: "Website Traffic" },
  { value: "followers", label: "Follower Growth" },
];
