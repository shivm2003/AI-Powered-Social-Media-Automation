"use client";

import Link from "next/link";
import ThreeDCard from "@/components/3d/ThreeDCard";
import { CAMPAIGN_STATUSES } from "@/lib/constants";
import styles from "./ActivityStream3D.module.css";

export default function ActivityStream3D({ campaigns = [] }) {
  const displayCampaigns = campaigns?.slice(0, 5) || [];

  return (
    <ThreeDCard maxTilt={10}>
      <div className={styles.streamContainer}>
        <div className={styles.streamHeader}>
          <div className={styles.streamTitle}>
            <span>📋</span> Live Dispatch Stream
          </div>
          <span className={styles.streamCount}>
            {campaigns?.length || 0} Total Campaigns
          </span>
        </div>

        {displayCampaigns.length > 0 ? (
          <>
            <div className={styles.list}>
              {displayCampaigns.map((campaign) => {
                const statusConfig = CAMPAIGN_STATUSES[campaign.status] || CAMPAIGN_STATUSES.draft;
                return (
                  <div key={campaign.id} className={styles.item}>
                    <div className={styles.itemLeft}>
                      <span className={styles.statusIcon}>{statusConfig.icon}</span>
                      <div className={styles.itemDetails}>
                        <div className={styles.itemTitle}>
                          {campaign.product_name || "Untitled Campaign"}
                        </div>
                        <div className={styles.itemSub}>
                          {campaign.content_type || "Post"} • {campaign.llm_provider || "AI Model"}
                        </div>
                      </div>
                    </div>
                    <span className={`tag tag-${statusConfig.color}`}>
                      {statusConfig.label}
                    </span>
                  </div>
                );
              })}
            </div>
            <Link href="/campaigns" className={styles.viewAllLink}>
              View All Campaigns & Historical Logs →
            </Link>
          </>
        ) : (
          <div className={styles.emptyState}>
            <div className={styles.emptyIcon}>🛰️</div>
            <p className={styles.emptyText}>
              No active campaigns yet. Launch your first post using the Content Studio to populate your stream!
            </p>
          </div>
        )}
      </div>
    </ThreeDCard>
  );
}
