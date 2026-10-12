"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  {
    section: "Main",
    items: [
      { href: "/", icon: "📊", label: "Dashboard" },
      { href: "/products", icon: "📦", label: "Products" },
      { href: "/accounts", icon: "🔗", label: "Accounts" },
      { href: "/generate", icon: "✨", label: "Generate" },
    ],
  },
  {
    section: "Management",
    items: [
      { href: "/campaigns", icon: "📋", label: "Campaigns" },
      { href: "/settings", icon: "⚙️", label: "Settings" },
    ],
  },
];

export default function Sidebar() {
  const pathname = usePathname();

  const isActive = (href) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">⚡</div>
        <span className="sidebar-title">AI Social</span>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((section) => (
          <div key={section.section}>
            <div className="nav-section-label">{section.section}</div>
            {section.items.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`nav-item ${isActive(item.href) ? "active" : ""}`}
              >
                <span className="nav-item-icon">{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            ))}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: "var(--radius-full)",
              background: "var(--accent-gradient)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "var(--font-sm)",
              fontWeight: 700,
              color: "white",
            }}
          >
            U
          </div>
          <div>
            <div style={{ fontSize: "var(--font-sm)", fontWeight: 600 }}>User</div>
            <div style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)" }}>
              Local Instance
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
