"use client";

import { useState } from "react";
import type { AgentTraceEvent } from "@/lib/streaming";

const STEP_LABELS: Record<string, string> = {
  extract: "信息抽取",
  readiness: "完整度判断",
  memory_recall: "记忆召回",
  dialogue: "追问生成",
  rag_search: "知识检索",
  report_generate: "报告生成",
  report_audit: "报告审计",
};

type Props = {
  events: AgentTraceEvent[];
};

export default function AgentTracePanel({ events }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className="card card-sm" style={{ marginTop: 12 }}>
      <div
        style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer" }}
        onClick={() => setOpen(v => !v)}
      >
        <span style={{ fontWeight: 600, fontSize: 13 }}>Agent Trace</span>
        <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
          {events.length > 0 ? `${events.length} 步` : ""} {open ? "▲" : "▼"}
        </span>
      </div>

      {open && (
        <div style={{ marginTop: 8 }}>
          {events.length === 0 && (
            <div style={{ fontSize: 12, color: "var(--color-text-muted)", padding: "8px 0", textAlign: "center" }}>
              本轮还没有运行记录
            </div>
          )}
          {events.map((ev, i) => (
            <div key={i} style={s.row}>
              <span className={`badge ${badge(ev.status)}`} style={{ fontSize: 11, minWidth: 36, textAlign: "center" }}>
                {ev.status === "started" ? "开始" : ev.status === "completed" ? "完成" : "失败"}
              </span>
              <span style={{ fontSize: 12, fontWeight: 500, flex: 1 }}>
                {STEP_LABELS[ev.step] || ev.step}
              </span>
              {ev.elapsed_ms != null && (
                <span style={{ fontSize: 11, color: "var(--color-text-muted)", minWidth: 50, textAlign: "right" }}>
                  {ev.elapsed_ms < 1000 ? `${ev.elapsed_ms}ms` : `${(ev.elapsed_ms / 1000).toFixed(1)}s`}
                </span>
              )}
              {ev.summary && (
                <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginTop: 2, gridColumn: "2" }}>
                  {ev.summary}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function badge(status: string): string {
  if (status === "completed") return "badge-success";
  if (status === "failed") return "badge-warning";
  return "badge-neutral";
}

const s: Record<string, React.CSSProperties> = {
  row: {
    display: "grid", gridTemplateColumns: "40px 1fr auto",
    alignItems: "center", gap: "4px 8px",
    padding: "4px 0", borderBottom: "1px solid var(--color-border)",
    fontSize: 12,
  },
};
