"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useStreaming } from "@/hooks/useStreaming";
import { getReportDetail } from "@/lib/api";
import { validateRenderedReport } from "@/lib/reportSafety";
import AuthBar from "@/components/AuthBar";
import UserReportCard from "@/components/UserReportCard";
import type { UserReport } from "@/lib/api";

export default function ChatPage() {
  const {
    state, messages, input, isStarting, isStreaming, isFinishing, isCompleted,
    report, assessmentId, usedTemplateReport, wechatQrUrl, error, missingItems, nextQuestions,
    start, setInput, send, finish, restart,
  } = useStreaming();
  const bottomRef = useRef<HTMLDivElement>(null);
  const [fullReport, setFullReport] = useState<UserReport | null>(null);

  const handleUnlocked = useCallback(async () => {
    if (!assessmentId) return;
    try {
      const d = await getReportDetail(assessmentId);
      if (d.is_unlocked && d.user_report) setFullReport(d.user_report);
    } catch { /* unlock check silently fails */ }
  }, [assessmentId]);

  const displayReport = fullReport || report;
  const reportSafe = displayReport && validateRenderedReport(displayReport);

  useEffect(() => { start(); }, []); // eslint-disable-line
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, displayReport]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  };

  const showFinish = state && state.conversation_round >= 3 && !isCompleted;
  const busy = isStreaming || isFinishing || isStarting;

  return (
    <div style={s.page}>
      <AuthBar />
      <header style={s.header}>
        <span style={s.title}>出海诊断顾问</span>
        <span style={s.round}>
          {state ? `${state.conversation_round} 轮` : ""}
          {isCompleted ? " · " : ""}
        </span>
      </header>
      <div style={s.chat}>
        {messages.map((m, i) => (
          <div key={i} style={m.role === "user" ? s.userRow : s.assistantRow}>
            <div style={m.role === "user" ? s.userBubble : s.assistantBubble}>{m.content}</div>
          </div>
        ))}
        {isStarting && <div style={s.status}>正在连接...</div>}
        {error && <div style={s.error}>{error}</div>}
        {missingItems.length > 0 && (
          <div style={s.missingBox}>
            <div style={s.missingTitle}>生成报告还缺少：</div>
            {missingItems.map((m, i) => (
              <div key={i} style={s.missingItem}>
                <span style={s.missingLabel}>{m.label}</span>
                {m.ask && <div style={s.missingAsk}>{m.ask}</div>}
              </div>
            ))}
          </div>
        )}
        {reportSafe && (
          <>
            <h3 style={s.reportTitle}>诊断报告</h3>
            <UserReportCard
              report={displayReport}
              usedTemplateReport={usedTemplateReport}
              assessmentId={assessmentId}
              showReportsLink
              onUnlocked={handleUnlocked}
              wechatQrUrl={wechatQrUrl}
            />
          </>
        )}
        {displayReport && !reportSafe && <div style={s.error}>报告内容校验失败，请联系管理员</div>}
        <div ref={bottomRef} />
      </div>
      <div style={s.inputRow}>
        {showFinish && (
          <button style={s.finishBtn} onClick={finish} disabled={busy}>
            {isFinishing ? "生成中..." : "生成报告"}
          </button>
        )}
        {isCompleted && (
          <button style={s.restartBtn} onClick={restart} disabled={busy}>重新开始</button>
        )}
        <textarea style={s.input} value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isCompleted ? "本次诊断已完成，可重新开始" : "输入你的企业信息..."}
          disabled={busy || isCompleted} rows={2} />
        <button style={s.btn} onClick={send} disabled={busy || isCompleted || !input.trim()}>
          {isStreaming ? "..." : "发送"}
        </button>
      </div>
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  page: { maxWidth: 700, margin: "0 auto", height: "100dvh", display: "flex", flexDirection: "column" },
  header: { padding: "12px 16px", background: "#0D9488", color: "#fff", display: "flex", justifyContent: "space-between" },
  title: { fontWeight: 600, fontSize: 16 },
  round: { fontSize: 13, opacity: 0.85 },
  chat: { flex: 1, overflowY: "auto", padding: "12px 16px" },
  userRow: { display: "flex", justifyContent: "flex-end", marginBottom: 10 },
  assistantRow: { display: "flex", justifyContent: "flex-start", marginBottom: 10 },
  userBubble: { maxWidth: "80%", padding: "8px 14px", borderRadius: 16, borderBottomRightRadius: 4, background: "#0D9488", color: "#fff", fontSize: 15, lineHeight: 1.5, whiteSpace: "pre-wrap" },
  assistantBubble: { maxWidth: "80%", padding: "8px 14px", borderRadius: 16, borderBottomLeftRadius: 4, background: "#fff", boxShadow: "0 1px 3px rgba(0,0,0,0.08)", fontSize: 15, lineHeight: 1.5, whiteSpace: "pre-wrap" },
  status: { textAlign: "center", color: "#999", padding: 8 },
  error: { textAlign: "center", color: "#d32f2f", padding: 8 },
  reportTitle: { fontSize: 18, marginBottom: 8 },
  inputRow: { display: "flex", padding: "8px 12px", borderTop: "1px solid #e0e0e0", background: "#fff", gap: 8 },
  input: { flex: 1, padding: "8px 12px", borderRadius: 8, border: "1px solid #ccc", fontSize: 15, outline: "none", resize: "none" as const, fontFamily: "inherit" },
  btn: { padding: "8px 20px", borderRadius: 8, border: "none", background: "#0D9488", color: "#fff", fontSize: 15, cursor: "pointer" },
  finishBtn: { padding: "8px 16px", borderRadius: 8, border: "none", background: "#e65100", color: "#fff", fontSize: 14, cursor: "pointer" },
  restartBtn: { padding: "8px 16px", borderRadius: 8, border: "1px solid #0D9488", background: "#fff", color: "#0D9488", fontSize: 14, cursor: "pointer" },
  missingBox: { background: "#fff3e0", padding: "10px 14px", borderRadius: 8, marginBottom: 10 },
  missingTitle: { fontWeight: 600, fontSize: 14, marginBottom: 6, color: "#e65100" },
  missingItem: { marginBottom: 6, fontSize: 14 },
  missingLabel: { fontWeight: 600, color: "#333" },
  missingAsk: { color: "#666", marginTop: 2 },
};
