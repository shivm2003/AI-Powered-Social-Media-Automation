"use client";

import ThreeDCard from "@/components/3d/ThreeDCard";
import styles from "./StatsGrid3D.module.css";

export default function StatsGrid3D({ stats }) {
  const cards = [
    {
      title: "Active Products",
      value: stats?.productCount || 0,
      icon: "📦",
      colorClass: styles.iconPurple,
      subBadge: "Brand Catalogs",
    },
    {
      title: "Connected Accounts",
      value: stats?.accountCount || 0,
      icon: "🔗",
      colorClass: styles.iconCyan,
      subBadge: "Multi-Platform Synced",
    },
    {
      title: "Published Posts",
      value: stats?.postedCount || 0,
      icon: "🚀",
      colorClass: styles.iconGreen,
      subBadge: "Live Across Social",
    },
    {
      title: "Pending Approval",
      value: stats?.pendingCount || 0,
      icon: "⏳",
      colorClass: styles.iconOrange,
      subBadge: "Awaiting Telegram Review",
    },
  ];

  return (
    <div className={styles.grid}>
      {cards.map((card, idx) => (
        <ThreeDCard key={idx} maxTilt={14}>
          <div className={styles.statCardInner}>
            <div className={`${styles.iconPedestal} ${card.colorClass}`}>
              {card.icon}
            </div>
            <div className={styles.statDetails}>
              <div className={styles.statValue}>{card.value}</div>
              <div className={styles.statLabel}>{card.title}</div>
              <div className={styles.statBadge}>
                <span>●</span> {card.subBadge}
              </div>
            </div>
          </div>
        </ThreeDCard>
      ))}
    </div>
  );
}
