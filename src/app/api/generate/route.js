import { NextResponse } from "next/server";
import { getProductById, createCampaign, updateCampaignStatus, getCampaignById } from "@/lib/db";
import { runAutomationCommand } from "@/lib/automation";
import { v4 as uuidv4 } from "uuid";
import path from "path";

export async function POST(request) {
  try {
    const body = await request.json();
    const {
      selectedProducts = [],
      llmProvider = "chatgpt",
      selectedPlatforms = ["facebook", "instagram"],
      contentType = "image",
      language = "english",
      tone = "professional",
      cta = "learn_more",
      aspectRatio = "1:1",
      videoDuration = 15,
      visualStyle = "photorealistic",
      customInstructions = "",
      skillImagePath = null,
      humanFlow = true,
    } = body;

    function safeParseJson(val, fallback = {}) {
      if (!val) return fallback;
      if (typeof val === "object") return val;
      try {
        return JSON.parse(val);
      } catch {
        return fallback;
      }
    }

    if (!selectedProducts.length) {
      return NextResponse.json({ error: "At least one product must be selected" }, { status: 400 });
    }

    const productId = selectedProducts[0];
    const product = await getProductById(productId);
    if (!product) {
      return NextResponse.json({ error: "Product not found" }, { status: 404 });
    }

    // 1. Create campaign in DB
    const campaignId = uuidv4();
    await createCampaign({
      id: campaignId,
      product_id: productId,
      llm_provider: llmProvider,
      content_type: contentType,
      language,
      platforms: selectedPlatforms,
      audience: product.target_audience,
      tone,
      cta,
      aspect_ratio: aspectRatio,
      video_duration: videoDuration,
      visual_style: visualStyle,
      custom_instructions: customInstructions,
      status: "generating",
    });

    const brandColorsParsed = safeParseJson(product.brand_colors, {
      primary: "#7C5CFC",
      secondary: "#3DD6D0",
      accent: "#FFB347",
    });

    // ── Human Flow Execution Pipeline ──
    if (humanFlow !== false) {
      try {
        const flowResult = await runAutomationCommand(
          {
            action: "human_flow_generate",
            platform: llmProvider,
            provider: llmProvider,
            product: {
              name: product.name,
              description: product.description,
              category: product.category,
              target_audience: product.target_audience,
              key_benefits: safeParseJson(product.key_benefits, []),
              brand_colors: brandColorsParsed,
              logo_path: product.logo_path || null,
            },
            platforms: selectedPlatforms,
            content_type: contentType,
            language,
            tone,
            cta,
            custom_instructions: customInstructions,
            aspect_ratio: aspectRatio,
            visual_style: visualStyle,
            skill_image_path: skillImagePath || product.logo_path || null,
            campaign_id: campaignId,
          },
          150000 // 2.5 minutes for realistic human-paced execution
        );

        if (flowResult && flowResult.status === "success") {
          const content = flowResult.content || {};
          const caption = content.caption || `Discover ${product.name}!`;
          const hashtags = Array.isArray(content.hashtags) ? content.hashtags : [];
          const mediaPaths = flowResult.media_path ? [flowResult.media_path] : [];
          const telegramDispatched = !!flowResult.telegram_dispatched;

          const finalStatus = telegramDispatched ? "preview_sent" : "draft";
          await updateCampaignStatus(campaignId, finalStatus, {
            generated_caption: caption,
            generated_hashtags: JSON.stringify(hashtags),
            media_paths: mediaPaths,
          });

          const updatedCampaign = await getCampaignById(campaignId);
          return NextResponse.json({
            success: true,
            campaign: updatedCampaign,
            logs: flowResult.logs || [],
            telegramDispatched,
            humanFlow: true,
            message: telegramDispatched
              ? "Human Flow executed! Content generated & dispatched to Telegram for approval."
              : "Human Flow executed! Content generated and saved as draft.",
          });
        }
      } catch (err) {
        console.warn("Human flow notice, falling back to standard generator:", err.message);
      }
    }

    // 2. Fallback / Standard Generation
    let textResult;
    try {
      textResult = await runAutomationCommand({
        action: "generate_text",
        provider: llmProvider,
        product: {
          name: product.name,
          description: product.description,
          category: product.category,
          target_audience: product.target_audience,
          key_benefits: safeParseJson(product.key_benefits, []),
          brand_colors: safeParseJson(product.brand_colors, { primary: "#7C5CFC", secondary: "#3DD6D0", accent: "#FFB347" }),
        },
        platforms: selectedPlatforms,
        content_type: contentType,
        language,
        tone,
        cta,
        custom_instructions: customInstructions,
      }, 45000);
    } catch (e) {
      console.warn("LLM automation warning:", e.message);
      textResult = {
        status: "success",
        content: {
          caption: `🚀 Discover ${product.name}!\n\n${product.description || "The smart solution built for your growth."}\n\n👉 Learn more and get started today!`,
          hashtags: [`#${product.name.replace(/\s+/g, "")}`, "#Innovation", "#Growth", "#Success"],
          headline: `Discover ${product.name}`,
          subheadline: product.description ? product.description.slice(0, 60) : "Elevate your daily operations effortlessly.",
          video_script_slides: [
            { slide: 1, text: "Need a better solution?", visual: "Problem intro" },
            { slide: 2, text: `Meet ${product.name}`, visual: "Hero reveal" },
            { slide: 3, text: "Get started today!", visual: "CTA" },
          ],
        },
      };
    }

    const contentData = textResult.content || {};
    const caption = contentData.caption || `Check out ${product.name}!`;
    const hashtags = Array.isArray(contentData.hashtags) ? contentData.hashtags : [];
    const mediaPaths = [];

    // 3. Generate Media (Image or Video)
    if (contentType === "image" || contentType === "carousel") {
      try {
        const resolvedSkillImage = skillImagePath || product.logo_path || null;
        const imgResult = await runAutomationCommand({
          action: "generate_image",
          provider: llmProvider,
          product: {
            name: product.name,
            category: product.category,
          },
          headline: contentData.headline || `Discover ${product.name}`,
          subheadline: contentData.subheadline || "",
          brand_colors: brandColorsParsed,
          aspect_ratio: aspectRatio,
          visual_style: visualStyle,
          cta_text: "Learn More ➜",
          logo_path: product.logo_path || null,
          skill_image_path: resolvedSkillImage,
          custom_instructions: customInstructions,
        }, 75000);

        if (imgResult.image_path) {
          mediaPaths.push(imgResult.image_path);
        }
      } catch (err) {
        console.warn("Image generation warning:", err.message);
        try {
          const fbResult = await runAutomationCommand({
            action: "generate_image",
            provider: "design_engine",
            product: { name: product.name, category: product.category },
            headline: contentData.headline || `Discover ${product.name}`,
            subheadline: contentData.subheadline || "",
            brand_colors: brandColorsParsed,
            aspect_ratio: aspectRatio,
            cta_text: "Learn More ➜",
            skill_image_path: skillImagePath || product.logo_path || null,
          }, 15000);
          if (fbResult.image_path) {
            mediaPaths.push(fbResult.image_path);
          }
        } catch (e2) {
          console.warn("Fallback image warning:", e2.message);
        }
      }
    } else if (contentType === "video") {
      try {
        const vidResult = await runAutomationCommand({
          action: "generate_video",
          product: {
            name: product.name,
          },
          slides: contentData.video_script_slides || [
            { slide: 1, text: product.name, visual: "Title card" },
          ],
          brand_colors: brandColorsParsed,
          duration: videoDuration,
          aspect_ratio: aspectRatio,
          logo_path: product.logo_path || null,
        }, 30000);

        if (vidResult.video_path) {
          mediaPaths.push(vidResult.video_path);
        }
      } catch (err) {
        console.warn("Video generation warning:", err.message);
      }
    }

    // 4. Send Telegram Preview
    let telegramDispatched = false;
    try {
      const tgResult = await runAutomationCommand({
        action: "send_telegram_preview",
        campaign_id: campaignId,
        caption: `${caption}\n\n${hashtags.join(" ")}`,
        media_path: mediaPaths[0] || "",
        platforms: selectedPlatforms,
        revision_count: 0,
      }, 45000);
      telegramDispatched = tgResult.status === "success";
    } catch (err) {
      console.warn("Telegram dispatch notice:", err.message);
    }

    // 5. Update Campaign in Database
    const finalStatus = telegramDispatched ? "preview_sent" : "draft";
    await updateCampaignStatus(campaignId, finalStatus, {
      generated_caption: caption,
      generated_hashtags: JSON.stringify(hashtags),
      media_paths: mediaPaths,
    });

    const updatedCampaign = await getCampaignById(campaignId);

    return NextResponse.json({
      success: true,
      campaign: updatedCampaign,
      message: telegramDispatched
        ? "Content generated and preview sent to Telegram! Review and approve on your phone."
        : "Content generated successfully and saved as draft.",
    });
  } catch (error) {
    console.error("Content generation route error:", error);
    return NextResponse.json({ error: error.message || "Failed to generate content" }, { status: 500 });
  }
}
