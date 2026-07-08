"use client";

import { useEffect, useRef, useState } from "react";
import type { AgentTraceEvent } from "@/lib/streaming";

const STEP_LABELS: Record<string, string> = {
  extract: "正在分析对话内容",
  readiness: "判断信息完整度",
  memory_recall: "搜索相关记忆",
  dialogue: "生成追问",
  rag_search: "检索知识库",
  report_generate: "生成诊断报告",
  report_audit: "审计报告质量",
};

type Props = {
  events: AgentTraceEvent[];
  isStreaming?: boolean;
};

export default function AgentTracePanel({ events, isStreaming }: Props) {
  const [open, setOpen] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  // 有新的 trace 时自动滚动到底部
  useEffect(() => {
    if (events.length > 0 && open) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [events.length, open]);

  // 当前正在运行的步骤
  const runningSteps = new Set(
    events
      .filter(e => e.status === "started")
      .map(e => e.step)
      .filter(step =>
        !events.some(e => e.step === step && (e.status === "completed" || e.status === "failed"))
      )
  );

  const hasLiveActivity = isStreaming || runningSteps.size > 0;

  return (
    <div className="card card-sm" style={{ marginTop: 12 }}>
      {/* Header */}
      <div
        style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer" }}
        onClick={() => setOpen(v => !v)}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {hasLiveActivity && (
            <span style={{
              width: 8, height: 8, borderRadius: "50%",
              background: "var(--color-accent, #30B9E8)",
              animation: "pulse-dot 1.2s ease-in-out infinite",
            }} />
          )}
          <span style={{ fontWeight: 600, fontSize: 13 }}>
            {hasLiveActivity ? "思考中…" : "Agent 运行记录"}
          </span>
        </div>
        <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
          {events.length > 0 ? `${events.length} 步` : ""} {open ? "▲" : "▼"}
        </span>
      </div>

      {open && (
        <div style={{ marginTop: 8 }}>
          {events.length === 0 && !isStreaming && (
            <div style={{ fontSize: 12, color: "var(--color-text-muted)", padding: "8px 0", textAlign: "center" }}>
              发送消息后将在此显示 Agent 执行过程
            </div>
          )}
          {events.length === 0 && isStreaming && (
            <div style={{ fontSize: 12, color: "var(--color-text-muted)", padding: "8px 0", textAlign: "center" }}>
              准备中…
            </div>
          )}
          {events.map((ev, i) => {
            const isRunning = ev.status === "started" &&
              !events.slice(i + 1).some(e => e.step === ev.step && (e.status === "completed" || e.status === "failed"));
            return (
              <div key={i} style={{
                ...s.row,
                color: ev.status === "failed" ? "var(--color-danger)" : "var(--color-text)",
              }}>
                {/* Status icon */}
                <span style={s.icon}>
                  {ev.status === "completed" && "✓"}
                  {ev.status === "failed" && "✗"}
                  {(ev.status === "started" && isRunning) && (
                    <span className="trace-spinner" />
                  )}
                  {(ev.status === "started" && !isRunning) && "·"}
                </span>
                {/* Label */}
                <span style={{ ...s.label, opacity: ev.status === "started" ? 0.7 : 1 }}>
                  {STEP_LABELS[ev.step] || ev.step}
                </span>
                {/* Timing */}
                {ev.elapsed_ms != null && (
                  <span style={s.time}>
                    {ev.elapsed_ms < 1000 ? `${ev.elapsed_ms}ms` : `${(ev.elapsed_ms / 1000).toFixed(1)}s`}
                  </span>
                )}
                {/* Summary line */}
                {ev.summary && ev.status !== "started" && (
                  <span style={s.summary}>{ev.summary}</span>
                )}
              </div>
            );
          })}
          <div ref={bottomRef} />
        </div>
      )}

      <style jsx>{`
        @keyframes pulse-dot {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.4; transform: scale(0.7); }
        }
        .trace-spinner {
          display: inline-block;
          width: 12px;
          height: 12px;
          border: 2px solid var(--color-border, #E2DED8);
          border-top-color: var(--color-accent, #30B9E8);
          border-radius: 50%;
          animation: trace-spin 0.7s linear infinite;
        }
        @keyframes trace-spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  row: {
    display: "grid",
    gridTemplateColumns: "18px 1fr auto",
    alignItems: "start",
    gap: "3px 8px",
    padding: "5px 0",
    borderBottom: "1px solid var(--color-border-light, #EDE9E4)",
    fontSize: 12,
    lineHeight: 1.5,
  },
  icon: {
    fontSize: 11,
    width: 18,
    textAlign: "center" as const,
    flexShrink: 0,
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    marginTop: 2,
  },
  label: {
    fontWeight: 500,
    fontSize: 12,
  },
  time: {
    fontSize: 10,
    color: "var(--color-text-muted)",
    textAlign: "right" as const,
  },
  summary: {
    fontSize: 10,
    color: "var(--color-text-secondary)",
    gridColumn: "2 / -1",
    lineHeight: 1.4,
  },
};
