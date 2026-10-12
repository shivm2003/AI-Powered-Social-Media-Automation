import { NextResponse } from "next/server";
import { getCampaignById, updateCampaignStatus, deleteCampaign, getProductById } from "@/lib/db";
import { runAutomationCommand } from "@/lib/automation";

export async function GET(request, { params }) {
  try {
    const campaign = getCampaignById(params.id);
    if (!campaign) {
      return NextResponse.json({ error: "Campaign not found" }, { status: 404 });
    }
    return NextResponse.json(campaign);
  } catch (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

function safeParseArray(val) {
  if (Array.isArray(val)) return val;
  if (!val) return [];
  try {
    const p = JSON.parse(val);
    return Array.isArray(p) ? p : [p];
  } catch {
    return typeof val === "string" ? [val] : [];
  }
}

export async function PUT(request, { params }) {
  try {
    const body = await request.json();
    const { action } = body; // 'approve', 'reject', 'revise'
    const campaign = getCampaignById(params.id);

    if (!campaign) {
      return NextResponse.json({ error: "Campaign not found" }, { status: 404 });
    }

    if (action === "approve") {
      updateCampaignStatus(params.id, "approved");
      const platforms = safeParseArray(campaign.platforms);
      const mediaPaths = safeParseArray(campaign.media_paths);
      const hashtags = safeParseArray(campaign.generated_hashtags);
      const caption = `${campaign.generated_caption || ""}\n\n${hashtags.join(" ")}`;

      // Trigger automatic posting via Selenium
      try {
        await runAutomationCommand({
          action: "post",
          platforms,
          media_path: mediaPaths[0] || null,
          caption,
        });
        updateCampaignStatus(params.id, "posted");
      } catch (e) {
        console.warn("Auto-posting exception:", e);
      }

      return NextResponse.json({ message: "Campaign approved and publishing dispatched" });
    } else if (action === "reject") {
      updateCampaignStatus(params.id, "rejected");
      return NextResponse.json({ message: "Campaign marked as rejected" });
    } else if (action === "revise") {
      updateCampaignStatus(params.id, "generating", { revision_notes: body.notes || "" });
      // Can trigger regeneration
      return NextResponse.json({ message: "Revision recorded" });
    }

    return NextResponse.json({ message: "Updated" });
  } catch (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function DELETE(request, { params }) {
  try {
    deleteCampaign(params.id);
    return NextResponse.json({ message: "Campaign deleted successfully" });
  } catch (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
