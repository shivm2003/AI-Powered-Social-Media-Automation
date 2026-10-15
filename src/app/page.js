"use client";

import { useState, useEffect } from "react";
import AuroraBackdrop3D from "@/components/3d/AuroraBackdrop3D";
import ThreeDScene from "@/components/3d/ThreeDScene";
import Hero3D from "@/components/dashboard/Hero3D";
import StatsGrid3D from "@/components/dashboard/StatsGrid3D";
import FeatureMatrix3D from "@/components/dashboard/FeatureMatrix3D";
import QuickActions3D from "@/components/dashboard/QuickActions3D";
import ActivityStream3D from "@/components/dashboard/ActivityStream3D";
import GettingStarted3D from "@/components/dashboard/GettingStarted3D";
import styles from "./page.module.css";

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  async function fetchStats() {
    try {
      const res = await fetch("/api/stats");
      const data = await res.json();
      setStats(data);
    } catch (error) {
      console.error("Failed to fetch stats:", error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className={styles.loadingContainer}>
        <div className={styles.spinner3D} />
        <div className={styles.loadingText}>
          <span>⚡</span> Initializing Manvxi AI 3D Command Matrix...
        </div>
      </div>
    );
  }

  return (
    <div className={styles.pageContainer}>
      {/* 3D Ambient Lighting Backdrop */}
      <AuroraBackdrop3D />

      {/* WebGL 3D Interactive Hero Canvas */}
      <ThreeDScene />

      {/* Futuristic 3D Command Banner */}
      <Hero3D stats={stats} />

      {/* 3D Perspective Tilt Metric Cards */}
      <StatsGrid3D stats={stats} />

      {/* 3D Neural Automation Pipeline Grid */}
      <FeatureMatrix3D />

      {/* Command Deck & Activity Stream Grid */}
      <div className={styles.twoColumnGrid}>
        <QuickActions3D />
        <ActivityStream3D campaigns={stats?.recentCampaigns} />
      </div>

      {/* Step-by-Step Guide for New Workspaces */}
      {stats?.productCount === 0 && <GettingStarted3D />}
    </div>
  );
}
