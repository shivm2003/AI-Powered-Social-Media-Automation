"use client";

import Link from "next/link";
import ThreeDCard from "@/components/3d/ThreeDCard";
import styles from "./FeatureMatrix3D.module.css";

const features = [
  {
    title: "Multi-LLM Synthesis",
    desc: "Generate viral copy with Gemini API, Claude 3.5 & ChatGPT 4o tailored to platform audiences.",
    icon: "🧠",
    status: "Active",
    linkText: "Configure Models",
    href: "/settings",
  },
  {
    title: "Branded Visual Canvas",
    desc: "Render high-converting 4K social banners, typography overlays & promotional video reels.",
    icon: "🎨",
    status: "Rendering Ready",
    linkText: "Studio Generator",
    href: "/generate",
  },
  {
    title: "Chrome Human Operator",
    desc: "Persistent browser profiles with human typing cadence and anti-detection remote debugging.",
    icon: "🌐",
    status: "Port 9222 Ready",
    linkText: "Browser Manager",
    href: "/accounts",
  },
  {
    title: "Telegram Bot Hub",
    desc: "Interactive instant mobile approvals: review, revise, or publish directly via Telegram inline keys.",
    icon: "📱",
    status: "Poller Connected",
    linkText: "Bot Settings",
    href: "/settings",
  },
];

export default function FeatureMatrix3D() {
  return (
    <div className={styles.container}>
      <div className={styles.sectionHeader}>
        <div className={styles.sectionTitle}>
          <span>⚡</span> Manvxi AI Autonomous Pipelines
        </div>
        <div className={styles.sectionTag}>Neural Core Systems</div>
      </div>

      <div className={styles.featureGrid}>
        {features.map((feat, idx) => (
          <ThreeDCard key={idx} maxTilt={12}>
            <div className={styles.featureCardInner}>
              <div className={styles.cardTop}>
                <div className={styles.featureIcon}>{feat.icon}</div>
                <div className={styles.featureStatus}>
                  <span className={styles.dot} />
                  <span>{feat.status}</span>
                </div>
              </div>

              <div className={styles.cardBody}>
                <h3 className={styles.featureHeading}>{feat.title}</h3>
                <p className={styles.featureDesc}>{feat.desc}</p>
              </div>

              <Link href={feat.href} className={styles.cardLink}>
                <span>{feat.linkText}</span>
                <span>→</span>
              </Link>
            </div>
          </ThreeDCard>
        ))}
      </div>
    </div>
  );
}
