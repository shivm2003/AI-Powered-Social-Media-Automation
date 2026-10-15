import { NextResponse } from "next/server";
import { getSetting, getCampaignById, updateCampaignStatus, getProductById } from "@/lib/db";
import { runAutomationCommand } from "@/lib/automation";

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

export async function GET() {
  try {
    const token = (await getSetting("telegram_bot_token")) || process.env.TELEGRAM_BOT_TOKEN;
    const chatId = (await getSetting("telegram_chat_id")) || process.env.TELEGRAM_CHAT_ID;

    if (!token) {
      return NextResponse.json({
        configured: false,
        message: "Telegram Bot Token is not configured yet.",
      });
    }

    // Ping Telegram API getMe
    const res = await fetch(`https://api.telegram.org/bot${token}/getMe`);
    const data = await res.json();

    if (data.ok) {
      return NextResponse.json({
        configured: true,
        connected: true,
        bot: data.result,
        chat_id: chatId || null,
      });
    } else {
      return NextResponse.json({
        configured: true,
        connected: false,
        error: data.description,
      });
    }
  } catch (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function POST(request) {
  try {
    const body = await request.json();

    // Check if this is a manual test message request from frontend settings
    if (body.action === "test_message") {
      const token = (await getSetting("telegram_bot_token")) || process.env.TELEGRAM_BOT_TOKEN;
      const chatId = body.chat_id || (await getSetting("telegram_chat_id")) || process.env.TELEGRAM_CHAT_ID;

      if (!token || !chatId) {
        return NextResponse.json({ error: "Missing Bot Token or Chat ID" }, { status: 400 });
      }

      const res = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chat_id: chatId,
          text: "🚀 <b>Manvxi AI</b>: Telegram connection verified successfully!",
          parse_mode: "HTML",
        }),
      });
      const data = await res.json();
      return NextResponse.json(data);
    }

    // ── Handle Telegram Webhook Updates ──
    const token = (await getSetting("telegram_bot_token")) || process.env.TELEGRAM_BOT_TOKEN;

    // 1. Handle Inline Button Clicks (callback_query)
    if (body.callback_query) {
      const callback = body.callback_query;
      const callbackData = callback.data || "";
      const chatId = callback.message?.chat?.id;

      // Acknowledge callback query to stop button loading spinner
      if (token && callback.id) {
        fetch(`https://api.telegram.org/bot${token}/answerCallbackQuery`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ callback_query_id: callback.id }),
        }).catch(() => {});
      }

      if (callbackData.startsWith("approve:")) {
        const campaignId = callbackData.split(":")[1];
        if (token && chatId) {
          // Send platform selection menu with Cancel button
          await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              chat_id: chatId,
              text: "🚀 <b>Campaign Approved!</b>\n\nWhich social media platform would you like to publish this post to?",
              parse_mode: "HTML",
              reply_markup: {
                inline_keyboard: [
                  [
                    { text: "📘 Facebook", callback_data: `post_to:facebook:${campaignId}` },
                    { text: "📸 Instagram", callback_data: `post_to:instagram:${campaignId}` },
                  ],
                  [
                    { text: "💼 LinkedIn", callback_data: `post_to:linkedin:${campaignId}` },
                    { text: "💬 WhatsApp", callback_data: `post_to:whatsapp:${campaignId}` },
                  ],
                  [
                    { text: "❌ Cancel", callback_data: `cancel_post:${campaignId}` },
                  ],
                ],
              },
            }),
          });
        }
      } else if (callbackData.startsWith("cancel_post:")) {
        if (token && chatId) {
          await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              chat_id: chatId,
              text: "❌ <b>Post publication was cancelled.</b> No post will be made.",
              parse_mode: "HTML",
            }),
          });
        }
      } else if (callbackData.startsWith("post_to:")) {
        const parts = callbackData.split(":");
        const platform = parts[1] || "facebook";
        const campaignId = parts[2] || "";
        const campaign = await getCampaignById(campaignId);

        if (campaign) {
          if (token && chatId) {
            await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                chat_id: chatId,
                text: `🚀 <b>Selected ${platform.toUpperCase()}</b>. Connecting to browser and verifying session...`,
                parse_mode: "HTML",
              }),
            });
          }

          const mediaPaths = safeParseArray(campaign.media_paths);
          const hashtags = safeParseArray(campaign.generated_hashtags);
          const caption = `${campaign.generated_caption || ""}\n\n${hashtags.join(" ")}`;

          runAutomationCommand({
            action: "post",
            platforms: [platform],
            campaign_id: campaignId,
            media_path: mediaPaths[0] || null,
            caption,
          }).catch(console.error);

          await updateCampaignStatus(campaignId, "posted");
        }
      } else if (callbackData.startsWith("revise:")) {
        const campaignId = callbackData.split(":")[1];
        if (token && chatId) {
          await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              chat_id: chatId,
              text: `✏️ <b>Revision Requested</b> for campaign <code>${campaignId}</code>.\n\nPlease reply to this message with your feedback/suggestions (e.g. <i>"Make caption punchier, use brighter colors, emphasize 20% discount"</i>).`,
              parse_mode: "HTML",
            }),
          });
        }
      } else if (callbackData.startsWith("reject:")) {
        const campaignId = callbackData.split(":")[1];
        await updateCampaignStatus(campaignId, "rejected");
        if (token && chatId) {
          await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              chat_id: chatId,
              text: `❌ Campaign marked as rejected/draft. No posts were published.`,
              parse_mode: "HTML",
            }),
          });
        }
      }

      // Answer callback query
      if (token && callback.id) {
        await fetch(`https://api.telegram.org/bot${token}/answerCallbackQuery`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ callback_query_id: callback.id }),
        });
      }

      return NextResponse.json({ ok: true });
    }

    // 2. Handle Text Suggestions from User (Reply for revision)
    if (body.message && body.message.text && body.message.reply_to_message) {
      const replyText = body.message.reply_to_message.text || "";
      const userSuggestion = body.message.text;
      const chatId = body.message.chat.id;

      // Extract campaign ID if mentioned
      const match = replyText.match(/campaign <code>([a-zA-Z0-9-]+)<\/code>/i) || replyText.match(/([a-zA-Z0-9-]{36})/);
      if (match) {
        const campaignId = match[1];
        const campaign = await getCampaignById(campaignId);

        if (campaign) {
          // Re-generate content incorporating suggestion
          const product = await getProductById(campaign.product_id);
          const platforms = safeParseArray(campaign.platforms);

          // Send "Regenerating..." notification
          if (token) {
            await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                chat_id: chatId,
                text: `🔄 Remaking image & copy with your suggestions: <i>"${userSuggestion}"</i>...`,
                parse_mode: "HTML",
              }),
            });
          }

          // Trigger generation with revision notes
          runAutomationCommand({
            action: "generate_text",
            provider: campaign.llm_provider,
            product: product || { name: "Product" },
            platforms,
            content_type: campaign.content_type,
            custom_instructions: `${campaign.custom_instructions || ""}. User feedback: ${userSuggestion}`,
          }).then(async (genRes) => {
            const newCaption = genRes.content?.caption || campaign.generated_caption;
            const newHashtags = genRes.content?.hashtags || [];

            // Regenerate image
            const imgRes = await runAutomationCommand({
              action: "generate_image",
              product: product || { name: "Product" },
              headline: genRes.content?.headline || "Updated Feature",
              subheadline: genRes.content?.subheadline || userSuggestion,
              aspect_ratio: campaign.aspect_ratio || "1:1",
            });

            const newMediaPath = imgRes.image_path || "";

            await updateCampaignStatus(campaignId, "preview_sent", {
              generated_caption: newCaption,
              generated_hashtags: JSON.stringify(newHashtags),
              media_paths: newMediaPath ? [newMediaPath] : [],
              revision_notes: userSuggestion,
            });

            // Re-send preview to Telegram
            runAutomationCommand({
              action: "send_telegram_preview",
              campaign_id: campaignId,
              caption: `${newCaption}\n\n${newHashtags.join(" ")}`,
              media_path: newMediaPath,
              platforms,
              revision_count: (campaign.revision_count || 0) + 1,
            });
          }).catch(console.error);
        }
      }

      return NextResponse.json({ ok: true });
    }

    return NextResponse.json({ ok: true });
  } catch (error) {
    console.error("Telegram webhook error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
