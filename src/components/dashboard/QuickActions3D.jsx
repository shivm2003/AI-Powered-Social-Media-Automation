"use client";

import Link from "next/link";
import ThreeDCard from "@/components/3d/ThreeDCard";
import styles from "./QuickActions3D.module.css";

const actions = [
  { href: "/generate", icon: "✨", label: "Launch Content Studio", desc: "Generate with Gemini/ChatGPT" },
  { href: "/products", icon: "📦", label: "Manage Products & Brands", desc: "Catalog & USP management" },
  { href: "/accounts", icon: "🔗", label: "Social Accounts & Browser", desc: "Chrome profile & platforms" },
  { href: "/growth", icon: "👥", label: "Outreach & Growth Engine", desc: "Audience engagement automation" },
  { href: "/campaigns", icon: "📋", label: "Review All Campaigns", desc: "History, metrics & status" },
  { href: "/settings", icon: "⚙️", label: "Configure AI & Telegram", desc: "API keys & bot tokens" },
];

export default function QuickActions3D() {
  return (
    <ThreeDCard maxTilt={10}>
      <div className={styles.actionDeck}>
        <div className={styles.deckHeader}>
          <div className={styles.deckTitle}>
            <span>⚡</span> Quick Launch Deck
          </div>
          <span className={styles.deckBadge}>Instant Access</span>
        </div>

        <div className={styles.buttonList}>
          {actions.map((act, i) => (
            <Link key={i} href={act.href} className={styles.actionBtn}>
              <div className={styles.btnLeft}>
                <span className={styles.btnIcon}>{act.icon}</span>
                <div>
                  <div>{act.label}</div>
                </div>
              </div>
              <span className={styles.arrow}>→</span>
            </Link>
          ))}
        </div>
      </div>
    </ThreeDCard>
  );
}
