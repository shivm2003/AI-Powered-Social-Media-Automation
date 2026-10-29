import { NextResponse } from "next/server";
import { getCampaignById, updateCampaignStatus, deleteCampaign, getProductById } from "@/lib/db";
import { runAutomationCommand } from "@/lib/automation";

export async function GET(request, { params }) {
  try {
    const { id } = await params;
    const campaign = await getCampaignById(id);
    if (!campaign) {
      return NextResponse.json({ error: "Campaign not found" }, { status: 404 });
    }
    return NextResponse.json(campaign);
  } catch (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

function safeParseArray(val) {
  let arr = [];
  if (Array.isArray(val)) arr = val;
  else if (!val) return [];
  else {
    try {
      const p = JSON.parse(val);
      arr = Array.isArray(p) ? p : [p];
    } catch {
      arr = typeof val === "string" ? [val] : [];
    }
  }
  const result = [];
  for (const item of arr) {
    if (typeof item === "string" && item.includes(",")) {
      result.push(...item.split(",").map((s) => s.trim()).filter(Boolean));
    } else if (item) {
      result.push(item);
    }
  }
  return result;
}

export async function PUT(request, { params }) {
  try {
    const { id } = await params;
    const body = await request.json();
    const { action } = body; // 'approve', 'reject', 'revise'
    const campaign = await getCampaignById(id);

    if (!campaign) {
      return NextResponse.json({ error: "Campaign not found" }, { status: 404 });
    }

    if (action === "approve") {
      await updateCampaignStatus(id, "approved");
      const selectedPlatforms = body.platform
        ? [body.platform]
        : (body.platforms ? safeParseArray(body.platforms) : safeParseArray(campaign.platforms));
      const targetPlatforms = selectedPlatforms.length > 0 ? selectedPlatforms : ["facebook"];
      const mediaPaths = safeParseArray(campaign.media_paths);
      const hashtags = safeParseArray(campaign.generated_hashtags);
      const caption = `${campaign.generated_caption || ""}\n\n${hashtags.join(" ")}`;

      // Trigger automatic posting via Selenium
      try {
        const result = await runAutomationCommand({
          action: "post",
          platforms: targetPlatforms,
          campaign_id: id,
          media_path: mediaPaths[0] || null,
          caption,
        });
        await updateCampaignStatus(id, "posted", {
          platforms: targetPlatforms,
          media_paths: mediaPaths,
        });
        return NextResponse.json({
          message: `Campaign approved and published to ${targetPlatforms.join(", ")}!`,
          result,
        });
      } catch (e) {
        console.warn("Auto-posting exception:", e);
        await updateCampaignStatus(id, "posted", {
          platforms: targetPlatforms,
          media_paths: mediaPaths,
        });
        return NextResponse.json({
          message: `Campaign approved. Publishing dispatched to ${targetPlatforms.join(", ")}.`,
          warning: e.message,
        });
      }
    } else if (action === "reject") {
      await updateCampaignStatus(id, "rejected");
      return NextResponse.json({ message: "Campaign marked as rejected" });
    } else if (action === "revise") {
      const notes = body.notes || "";
      const provider = body.provider || campaign.llm_provider || "gemini";
      const product = await getProductById(campaign.product_id);
      const contactNumber =
        body.contact_number ||
        body.contactNumber ||
        campaign.contact_number ||
        product?.contact_number ||
        (product?.name?.toLowerCase().includes("loan") ? "8112570656" : null);

      await updateCampaignStatus(id, "generating", {
        revision_notes: notes,
        contact_number: contactNumber,
      });
      const updatedCampaignRecord = await getCampaignById(id);
      const revCount = updatedCampaignRecord?.revision_count || 1;
      const selectedPlatforms = body.platforms
        ? safeParseArray(body.platforms)
        : safeParseArray(campaign.platforms);
      const targetPlatforms = selectedPlatforms.length > 0 ? selectedPlatforms : ["facebook", "instagram"];

      function safeParseJson(val, fallback = {}) {
        if (!val) return fallback;
        if (typeof val === "object") return val;
        try {
          return JSON.parse(val);
        } catch {
          return fallback;
        }
      }

      try {
        const flowResult = await runAutomationCommand(
          {
            action: "human_flow_generate",
            platform: provider,
            provider: provider,
            product: product
              ? {
                  id: product.id,
                  name: product.name,
                  description: product.description,
                  category: product.category,
                  target_audience: product.target_audience,
                  key_benefits: safeParseJson(product.key_benefits, []),
                  brand_colors: safeParseJson(product.brand_colors, {}),
                  logo_path: product.logo_path || null,
                  contact_number: contactNumber,
                }
              : {},
            platforms: targetPlatforms,
            content_type: campaign.content_type || "image",
            language: campaign.language || "english",
            tone: campaign.tone || "professional",
            cta: campaign.cta || "learn_more",
            custom_instructions: `REVISION #${revCount} FEEDBACK: ${notes}\nOriginal Instructions: ${campaign.custom_instructions || ""}\nPrevious Copy: ${(campaign.generated_caption || "").slice(0, 150)}`,
            aspect_ratio: campaign.aspect_ratio || "1:1",
            visual_style: campaign.visual_style || "photorealistic",
            skill_image_path: product?.logo_path || null,
            campaign_id: id,
            revision_count: revCount,
            contact_number: contactNumber,
          },
          150000
        );

        if (flowResult && flowResult.status === "success") {
          const content = flowResult.content || {};
          const caption = flowResult.caption || content.caption || `Discover ${product?.name || "Product"}!`;
          const hashtags = Array.isArray(content.hashtags) ? content.hashtags : [];
          const mediaPaths = flowResult.media_path ? [flowResult.media_path] : [];
          const telegramDispatched = !!flowResult.telegram_dispatched;

          await updateCampaignStatus(id, telegramDispatched ? "preview_sent" : "draft", {
            generated_caption: caption,
            generated_hashtags: JSON.stringify(hashtags),
            media_paths: mediaPaths,
          });

          const finalCampaign = await getCampaignById(id);
          return NextResponse.json({
            success: true,
            message: `Revision #${revCount} generated successfully! ${
              telegramDispatched ? "Updated preview dispatched to Telegram for review." : ""
            }`,
            campaign: finalCampaign,
            logs: flowResult.logs || [],
          });
        } else {
          await updateCampaignStatus(id, "draft");
          return NextResponse.json({
            warning: "Revision generation returned without explicit success",
            logs: flowResult?.logs || [],
          });
        }
      } catch (genErr) {
        console.warn("Revision flow generation exception:", genErr);
        await updateCampaignStatus(id, "draft");
        return NextResponse.json(
          {
            error: "Revision generation error: " + genErr.message,
          },
          { status: 500 }
        );
      }
    }

    return NextResponse.json({ message: "Updated" });
  } catch (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function DELETE(request, { params }) {
  try {
    const { id } = await params;
    await deleteCampaign(id);
    return NextResponse.json({ message: "Campaign deleted successfully" });
  } catch (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
