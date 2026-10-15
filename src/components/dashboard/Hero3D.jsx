"use client";

import Link from "next/link";
import styles from "./Hero3D.module.css";

export default function Hero3D({ stats }) {
  return (
    <div className={styles.heroCard}>
      <div className={styles.heroContent}>
        <div className={styles.badgeRow}>
          <div className={styles.modelBadge}>
            <span>⚡</span> Manvxi AI Engine v2.0
          </div>
          <div className={styles.statusBadge}>
            <span className={styles.pulseDot} />
            <span>Autonomous Mode Online</span>
          </div>
          <div className={styles.modelBadge} style={{ borderColor: "rgba(56, 189, 248, 0.4)", color: "#38bdf8" }}>
            <span>🌐</span> Multi-LLM: Gemini • Claude • ChatGPT
          </div>
        </div>

        <div>
          <h1 className={styles.heroTitle}>
            Next-Gen Growth Powered by <span className={styles.gradientText}>Manvxi AI</span>
          </h1>
          <p className={styles.heroSubtitle}>
            Orchestrate viral multi-platform social media campaigns, automate human-cadence publishing,
            and generate high-converting visual media in dynamic 3D space.
          </p>
        </div>

        <div className={styles.actionRow}>
          <Link href="/generate" className={styles.btnPrimary3D}>
            <span>✨</span> Launch Content Studio
          </Link>
          <Link href="/products" className={styles.btnSecondary3D}>
            <span>📦</span> Manage Products ({stats?.productCount || 0})
          </Link>
          <Link href="/growth" className={styles.btnSecondary3D}>
            <span>👥</span> Outreach & Growth
          </Link>
        </div>

        <div className={styles.heroMetaGrid}>
          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>Published Posts</span>
            <span className={styles.metaValue}>🚀 {stats?.postedCount || 0} Delivered</span>
          </div>
          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>Synced Accounts</span>
            <span className={styles.metaValue}>🔗 {stats?.accountCount || 0} Connected</span>
          </div>
          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>Pending Approval</span>
            <span className={styles.metaValue}>⏳ {stats?.pendingCount || 0} In Queue</span>
          </div>
          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>Browser Sync</span>
            <span className={styles.metaValue}>⚡ 9222 Active</span>
          </div>
        </div>
      </div>
    </div>
  );
}
