"use client";

import { usePathname } from "next/navigation";

const pageTitles = {
  "/": "Dashboard",
  "/products": "Products",
  "/accounts": "Accounts",
  "/generate": "Generate Content",
  "/campaigns": "Campaigns",
  "/settings": "Settings",
};

export default function Header() {
  const pathname = usePathname();

  const getTitle = () => {
    if (pageTitles[pathname]) return pageTitles[pathname];
    // Handle dynamic routes
    if (pathname.startsWith("/products/")) return "Edit Product";
    if (pathname.startsWith("/generate/")) return "Generate Content";
    if (pathname.startsWith("/campaigns/")) return "Campaign Details";
    return "Dashboard";
  };

  return (
    <header className="header">
      <div className="header-left">
        <div className="header-breadcrumb">
          <span>AI Social</span>
          <span>›</span>
          <span className="current">{getTitle()}</span>
        </div>
      </div>

      <div className="header-right">
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "var(--space-2)",
            padding: "var(--space-2) var(--space-4)",
            background: "var(--success-muted)",
            borderRadius: "var(--radius-full)",
            fontSize: "var(--font-xs)",
            fontWeight: 600,
            color: "var(--success)",
          }}
        >
          <span className="status-dot verified pulse" />
          System Online
        </div>
      </div>
    </header>
  );
}
