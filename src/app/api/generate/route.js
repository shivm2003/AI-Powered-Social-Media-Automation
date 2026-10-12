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
      llmProvider = "gemini",
      selectedPlatforms = ["facebook", "instagram"],
      contentType = "image",
      language = "english",
      tone = "professional",
      cta = "learn_more",
      aspectRatio = "1:1",
      videoDuration = 15,
      visualStyle = "minimal",
      customInstructions = "",
    } = body;

    if (!selectedProducts.length) {
      return NextResponse.json({ error: "At least one product must be selected" }, { status: 400 });
    }

    const productId = selectedProducts[0];
    const product = getProductById(productId);
    if (!product) {
      return NextResponse.json({ error: "Product not found" }, { status: 404 });
    }

    // 1. Create campaign in DB
    const campaignId = uuidv4();
    createCampaign({
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

    // 2. Generate Copy with LLM
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
          key_benefits: JSON.parse(product.key_benefits || "[]"),
          brand_colors: JSON.parse(product.brand_colors || "{}"),
        },
        platforms: selectedPlatforms,
        content_type: contentType,
        language,
        tone,
        cta,
        custom_instructions: customInstructions,
      }, 90000);
    } catch (e) {
      console.warn("LLM automation warning:", e.message);
      textResult = {
        status: "success",
        content: {
          caption: `🚀 Discover ${product.name}! ${product.description}\n\n👉 Learn more today!`,
          hashtags: [`#${product.name.replace(/\s+/g, "")}`, "#Innovation", "#Growth"],
          headline: `Discover ${product.name}`,
          subheadline: "Elevate your daily operations effortlessly.",
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
    const hashtags = contentData.hashtags || [];
    const mediaPaths = [];

    // 3. Generate Media (Image or Video)
    if (contentType === "image" || contentType === "carousel") {
      try {
        const imgResult = await runAutomationCommand({
          action: "generate_image",
          product: {
            name: product.name,
            category: product.category,
          },
          headline: contentData.headline || `Discover ${product.name}`,
          subheadline: contentData.subheadline || "",
          brand_colors: JSON.parse(product.brand_colors || "{}"),
          aspect_ratio: aspectRatio,
          cta_text: "Learn More ➜",
          logo_path: product.logo_path || null,
        }, 60000);

        if (imgResult.image_path) {
          mediaPaths.push(imgResult.image_path);
        }
      } catch (err) {
        console.warn("Image generation warning:", err.message);
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
          brand_colors: JSON.parse(product.brand_colors || "{}"),
          duration: videoDuration,
          aspect_ratio: aspectRatio,
          logo_path: product.logo_path || null,
        }, 120000);

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
    updateCampaignStatus(campaignId, finalStatus, {
      generated_caption: caption,
      generated_hashtags: JSON.stringify(hashtags),
      media_paths: mediaPaths,
    });

    const updatedCampaign = getCampaignById(campaignId);

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
