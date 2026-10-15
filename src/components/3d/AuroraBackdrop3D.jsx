"use client";

import styles from "./AuroraBackdrop3D.module.css";

export default function AuroraBackdrop3D() {
  return (
    <div className={styles.backdropContainer} aria-hidden="true">
      <div className={styles.auroraGlow1} />
      <div className={styles.auroraGlow2} />
      <div className={styles.auroraGlow3} />
      <div className={styles.gridFloor} />
    </div>
  );
}
