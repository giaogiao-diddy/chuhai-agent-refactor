"use client";

import { useEffect, useRef } from "react";
import { useStreaming } from "@/hooks/useStreaming";
import { validateRenderedReport } from "@/lib/reportSafety";

export default function ChatPage() {
  const {
    state, messages, input, isStarting, isStreaming, isFinishing, isCompleted,
    report, assessmentId, usedTemplateReport, error, start, setInput, send, finish, restart,
  } = useStreaming();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { start(); }, []); // eslint-disable-line
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, report]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  };

  const showFinish = state && state.conversation_round >= 1 && !isCompleted;
  const busy = isStreaming || isFinishing || isStarting;
  const reportSafe = report && validateRenderedReport(report);

  return (
    <div style={s.page}>
      <header style={s.header}>
        <span style={s.title}>出海诊断顾问</span>
        <span style={s.round}>
          {state ? `${state.conversation_round} / 8 轮` : ""}
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
        {reportSafe && (
          <div style={s.reportCard}>
            <h3 style={s.reportTitle}>诊断报告</h3>
            {usedTemplateReport && <p style={s.templateNote}>本次报告由保守模板生成</p>}
            <p><b>总分：</b>{report.feasibility_score} / 100（{report.tag}）</p>
            <p style={{ color: "#666" }}>{report.tag_explanation}</p>
            <p>{report.preliminary_judgment}</p>
            <h4>优势</h4><ul>{report.strengths.map((t,i) => <li key={i}>{t}</li>)}</ul>
            <h4>风险</h4><ul>{report.risks.map((t,i) => <li key={i}>{t}</li>)}</ul>
            <h4>综合结论</h4><p>{report.summary_conclusion}</p>
            <h4>推荐路径</h4><p>{report.recommended_path}</p>
            <h4>风险提醒</h4><p>{report.risk_reminder}</p>
            <h4>30天行动计划</h4>
            <ol>{report.action_plan_30days.map((a,i) => <li key={i}>{a}</li>)}</ol>
            <p style={{ color: "#999" }}>{report.unlock_hint}</p>
            {assessmentId && <p style={s.assessmentId}>报告编号：{assessmentId}</p>}
            <p style={{ marginTop: 8 }}><a href="/reports" style={{ color: "#0D9488", fontSize: 14 }}>查看我的报告</a></p>
          </div>
        )}
        {report && !reportSafe && <div style={s.error}>报告内容校验失败，请联系管理员</div>}
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
  reportCard: { background: "#fff", borderRadius: 12, padding: 16, marginBottom: 12, boxShadow: "0 1px 3px rgba(0,0,0,0.08)" },
  reportTitle: { fontSize: 18, marginBottom: 8 },
  templateNote: { background: "#fff8e1", padding: "4px 10px", borderRadius: 6, fontSize: 13, color: "#795548", marginBottom: 8 },
  assessmentId: { fontSize: 11, color: "#aaa", marginTop: 8, wordBreak: "break-all" },
  inputRow: { display: "flex", padding: "8px 12px", borderTop: "1px solid #e0e0e0", background: "#fff", gap: 8 },
  input: { flex: 1, padding: "8px 12px", borderRadius: 8, border: "1px solid #ccc", fontSize: 15, outline: "none", resize: "none" as const, fontFamily: "inherit" },
  btn: { padding: "8px 20px", borderRadius: 8, border: "none", background: "#0D9488", color: "#fff", fontSize: 15, cursor: "pointer" },
  finishBtn: { padding: "8px 16px", borderRadius: 8, border: "none", background: "#e65100", color: "#fff", fontSize: 14, cursor: "pointer" },
  restartBtn: { padding: "8px 16px", borderRadius: 8, border: "1px solid #0D9488", background: "#fff", color: "#0D9488", fontSize: 14, cursor: "pointer" },
};
