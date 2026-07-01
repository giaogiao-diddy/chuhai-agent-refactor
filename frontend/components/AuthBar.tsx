"use client";

import { useState } from "react";
import { clearAuthToken, getWechatLoginUrl, isLoggedIn } from "@/lib/api";

export default function AuthBar() {
  const [error, setError] = useState<string | null>(null);

  async function handleLogin() {
    setError(null);
    try {
      const data = await getWechatLoginUrl();
      window.location.href = data.url;
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "获取登录链接失败");
    }
  }

  function handleLogout() {
    clearAuthToken();
    window.location.reload();
  }

  const loggedIn = typeof window !== "undefined" && isLoggedIn();

  return (
    <div style={s.bar}>
      {loggedIn ? (
        <>
          <span style={s.text}>已登录</span>
          <button style={s.btn} onClick={handleLogout}>退出登录</button>
        </>
      ) : (
        <>
          <button style={s.btn} onClick={handleLogin}>微信登录</button>
          {error && <span style={s.error}>{error}</span>}
        </>
      )}
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  bar: { display: "flex", alignItems: "center", gap: 8, padding: "6px 12px", background: "#f5f5f5", fontSize: 13 },
  text: { color: "#666" },
  btn: { padding: "4px 12px", borderRadius: 6, border: "1px solid #07C160", background: "#fff", color: "#07C160", fontSize: 13, cursor: "pointer" },
  error: { color: "#d32f2f", fontSize: 12 },
};
