"use client";

import { usePathname } from "next/navigation";
import { useState, useCallback, useEffect } from "react";
import { clearAuthToken, devLogin, getWechatLoginUrl, isLoggedIn } from "@/lib/api";

type NavItem = {
  href: string;
  label: string;
  icon: "chat" | "reports" | "admin" | "knowledge" | "settings";
};

const NAV_ITEMS: NavItem[] = [
  { href: "/chat", label: "出海诊断", icon: "chat" },
  { href: "/reports", label: "我的报告", icon: "reports" },
  { href: "/admin/leads", label: "顾问后台", icon: "admin" },
  { href: "/knowledge", label: "知识库", icon: "knowledge" },
  { href: "/settings/models", label: "模型设置", icon: "settings" },
  { href: "/settings/mcp", label: "MCP 服务", icon: "settings" },
];

type Props = {
  title: string;
  modelStatus?: string | null;
  sidePanel?: React.ReactNode;
  children: React.ReactNode;
};

export default function AppShell({ title, modelStatus, sidePanel, children }: Props) {
  const pathname = usePathname();
  const [navOpen, setNavOpen] = useState(false);
  const [navCollapsed, setNavCollapsed] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [loggedIn, setLoggedIn] = useState(false);

  useEffect(() => {
    setLoggedIn(isLoggedIn());
    try {
      setNavCollapsed(localStorage.getItem("shell_nav_collapsed") === "1");
    } catch {}
  }, []);

  const toggleNavCollapsed = useCallback(() => {
    setNavCollapsed(v => {
      const next = !v;
      try { localStorage.setItem("shell_nav_collapsed", next ? "1" : "0"); } catch {}
      return next;
    });
  }, []);

  const handleLogin = useCallback(async () => {
    setAuthError(null);
    try {
      const data = await getWechatLoginUrl();
      window.location.href = data.url;
    } catch (err: unknown) {
      setAuthError(err instanceof Error ? err.message : "获取登录链接失败");
    }
  }, []);

  const handleDevLogin = useCallback(async () => {
    setAuthError(null);
    try {
      await devLogin("开发者");
      window.location.reload();
    } catch (err: unknown) {
      setAuthError(err instanceof Error ? err.message : "开发登录失败");
    }
  }, []);

  const handleLogout = useCallback(() => {
    clearAuthToken();
    window.location.reload();
  }, []);

  return (
    <div className={`shell${navCollapsed ? " nav-collapsed" : ""}`}>
      {/* Mobile overlay */}
      {navOpen && (
        <div
          onClick={() => setNavOpen(false)}
          style={{
            position: "fixed", inset: 0, background: "rgba(0,0,0,0.3)", zIndex: 99,
          }}
        />
      )}

      {/* Left Nav */}
      <nav className={`shell-nav${navOpen ? " open" : ""}`}>
        <div className="shell-nav-brand">
          <span className="shell-brand-mark" aria-hidden="true" />
          <span className="shell-brand-copy">
            <span className="shell-brand-title">深度未来</span>
            <span className="shell-brand-subtitle">Export Agent Console</span>
          </span>
          <button
            className="shell-nav-collapse"
            onClick={toggleNavCollapsed}
            aria-label={navCollapsed ? "展开导航" : "收起导航"}
            title={navCollapsed ? "展开导航" : "收起导航"}
            type="button"
          >
            {navCollapsed ? "›" : "‹"}
          </button>
        </div>
        <div className="shell-nav-items">
          {NAV_ITEMS.map(item => (
            <a
              key={item.href}
              href={item.href}
              className={`shell-nav-item${pathname === item.href || pathname?.startsWith(item.href + "/") ? " active" : ""}`}
              onClick={() => setNavOpen(false)}
              aria-label={item.label}
              title={item.label}
            >
              <span className="shell-line-icon" data-kind={item.icon} aria-hidden="true" />
              <span className="shell-nav-label">{item.label}</span>
            </a>
          ))}
        </div>
      </nav>

      {sidePanel && (
        <aside className="shell-context-rail">
          {sidePanel}
        </aside>
      )}

      {/* Main */}
      <div className={`shell-main${sidePanel ? " with-context" : ""}`}>
        {/* Top Bar */}
        <header className="shell-topbar">
          <div className="shell-topbar-left">
            <button
              className="shell-hamburger"
              onClick={() => setNavOpen(v => !v)}
              aria-label="菜单"
            >
              {navOpen ? "✕" : "☰"}
            </button>
            <span className="shell-topbar-title">{title}</span>
          </div>
          <div className="shell-topbar-right">
            {modelStatus && (
              <span className="shell-model-status">{modelStatus}</span>
            )}
            <div className="auth-bar">
              {loggedIn ? (
                <>
                  <span>已登录</span>
                  <button onClick={handleLogout}>退出</button>
                </>
              ) : (
                <>
                  <button onClick={handleLogin}>微信登录</button>
                  <button onClick={handleDevLogin} style={{ border: "1px solid var(--color-accent)", color: "var(--color-accent)" }}>开发登录</button>
                  {authError && <span style={{ color: "var(--color-danger)" }}>{authError}</span>}
                </>
              )}
            </div>
          </div>
        </header>

        {/* Content */}
        <main className="shell-content">
          {children}
        </main>
      </div>
    </div>
  );
}
