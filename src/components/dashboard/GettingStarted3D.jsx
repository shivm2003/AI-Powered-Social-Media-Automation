"use client";

import Link from "next/link";
import styles from "./GettingStarted3D.module.css";

const steps = [
  {
    num: "1",
    title: "Add your first product",
    desc: "Define your brand identity, target demographic, unique selling proposition & logo.",
    href: "/products",
  },
  {
    num: "2",
    title: "Connect social media accounts",
    desc: "Link Facebook, Instagram, LinkedIn, or WhatsApp Web with persistent Chrome profiles.",
    href: "/accounts",
  },
  {
    num: "3",
    title: "Configure Telegram bot for instant approvals",
    desc: "Set your bot token & chat ID to review generated media and publish with a single tap.",
    href: "/settings",
  },
  {
    num: "4",
    title: "Generate and launch viral campaigns",
    desc: "Synthesize high-converting copy and branded graphics with Gemini 2.5, Claude & ChatGPT.",
    href: "/generate",
  },
];

export default function GettingStarted3D() {
  return (
    <div className={styles.guideCard}>
      <div className={styles.guideHeader}>
        <div style={{ fontSize: "1.5rem" }}>🚀</div>
        <div className={styles.guideTitle}>Quick Start Sequence</div>
      </div>

      <div className={styles.stepList}>
        {steps.map((s) => (
          <Link key={s.num} href={s.href} style={{ textDecoration: "none" }}>
            <div className={styles.stepItem}>
              <div className={styles.stepNumber}>{s.num}</div>
              <div>
                <div className={styles.stepTitle}>{s.title}</div>
                <div className={styles.stepDesc}>{s.desc}</div>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
