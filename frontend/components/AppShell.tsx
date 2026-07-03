"use client";

import { usePathname } from "next/navigation";
import { useState, useCallback, useEffect } from "react";
import { clearAuthToken, getWechatLoginUrl, isLoggedIn } from "@/lib/api";

type NavItem = {
  href: string;
  label: string;
  icon: string;
};

const NAV_ITEMS: NavItem[] = [
  { href: "/chat", label: "出海诊断", icon: "💬" },
  { href: "/reports", label: "我的报告", icon: "📋" },
  { href: "/admin/leads", label: "顾问后台", icon: "📊" },
  { href: "/settings/models", label: "模型设置", icon: "⚙️" },
];

type Props = {
  title: string;
  modelStatus?: string | null;
  children: React.ReactNode;
};

export default function AppShell({ title, modelStatus, children }: Props) {
  const pathname = usePathname();
  const [navOpen, setNavOpen] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [loggedIn, setLoggedIn] = useState(false);

  useEffect(() => { setLoggedIn(isLoggedIn()); }, []);

  const handleLogin = useCallback(async () => {
    setAuthError(null);
    try {
      const data = await getWechatLoginUrl();
      window.location.href = data.url;
    } catch (err: unknown) {
      setAuthError(err instanceof Error ? err.message : "获取登录链接失败");
    }
  }, []);

  const handleLogout = useCallback(() => {
    clearAuthToken();
    window.location.reload();
  }, []);

  return (
    <div className="shell">
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
        <div className="shell-nav-brand">出海诊断工作台</div>
        <div className="shell-nav-items">
          {NAV_ITEMS.map(item => (
            <a
              key={item.href}
              href={item.href}
              className={`shell-nav-item${pathname === item.href || pathname?.startsWith(item.href + "/") ? " active" : ""}`}
              onClick={() => setNavOpen(false)}
            >
              <span className="shell-nav-icon">{item.icon}</span>
              {item.label}
            </a>
          ))}
        </div>
      </nav>

      {/* Main */}
      <div className="shell-main">
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
              <span style={{ color: "var(--color-text-muted)", fontSize: 12 }}>{modelStatus}</span>
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
