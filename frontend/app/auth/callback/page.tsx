"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { handleWechatCallback, setAuthToken } from "@/lib/api";

function CallbackContent() {
  const params = useSearchParams();
  const [status, setStatus] = useState<string>("处理中...");
  const handledRef = useRef(false);

  useEffect(() => {
    if (handledRef.current) return;
    handledRef.current = true;
    const code = params.get("code");
    const state = params.get("state");
    if (!code || !state) {
      setStatus("微信登录参数缺失");
      return;
    }
    handleWechatCallback(code, state).then(data => {
      setAuthToken(data.access_token);
      window.location.href = "/chat";
    }).catch(() => {
      setStatus("微信登录失败，请返回重试");
    });
  }, [params]);

  return (
    <p style={{ fontSize: 16, color: status.includes("失败") || status.includes("缺失") ? "#d32f2f" : "#666" }}>
      {status}
    </p>
  );
}

export default function AuthCallbackPage() {
  return (
    <div style={{ maxWidth: 400, margin: "80px auto", textAlign: "center" }}>
      <Suspense fallback={<p>加载中...</p>}>
        <CallbackContent />
      </Suspense>
    </div>
  );
}
