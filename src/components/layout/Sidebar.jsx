"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import styles from "./Sidebar.module.css";

const navItems = [
  {
    section: "Main Studio",
    items: [
      { href: "/", icon: "📊", label: "Dashboard" },
      { href: "/products", icon: "📦", label: "Products & Brands" },
      { href: "/accounts", icon: "🔗", label: "Accounts & Browser" },
      { href: "/generate", icon: "✨", label: "Content Studio" },
      { href: "/growth", icon: "👥", label: "Outreach & Growth" },
    ],
  },
  {
    section: "Operations",
    items: [
      { href: "/campaigns", icon: "📋", label: "Campaigns" },
      { href: "/settings", icon: "⚙️", label: "Settings" },
    ],
  },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const isActive = (href) => {
    if (!mounted || !pathname) return false;
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <aside className={styles.sidebar}>
      <div className={styles.sidebarHeader}>
        <div className={styles.logoIconWrapper}>
          <div className={styles.logoPulse} />
          <span>⚡</span>
        </div>
        <div className={styles.brandGroup}>
          <span className={styles.sidebarTitle}>Manvxi AI</span>
          <span className={styles.brandBadge}>Autonomous 3D PRO</span>
        </div>
      </div>

      <nav className={styles.sidebarNav}>
        {navItems.map((section) => (
          <div key={section.section} className={styles.sectionGroup}>
            <div className={styles.sectionLabel}>{section.section}</div>
            {section.items.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`${styles.navItem} ${isActive(item.href) ? styles.active : ""}`}
                suppressHydrationWarning
              >
                <span className={styles.navIcon}>{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            ))}
          </div>
        ))}
      </nav>

      <div className={styles.sidebarFooter}>
        <div className={styles.userCard}>
          <div className={styles.avatar}>M</div>
          <div>
            <div className={styles.userName}>Operator</div>
            <div className={styles.userRole}>Manvxi AI Core</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
