"use client";

import { useEffect, useState } from "react";
import { listReports, getReportDetail } from "@/lib/api";
import { validateRenderedReport } from "@/lib/reportSafety";
import type { ReportListItem, UserReport } from "@/lib/api";

export default function ReportsPage() {
  const [items, setItems] = useState<ReportListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<UserReport | null>(null);
  const [detailId, setDetailId] = useState<string | null>(null);

  useEffect(() => {
    listReports().then(setItems).catch(() => setError("加载失败")).finally(() => setLoading(false));
  }, []);

  async function viewDetail(id: string) {
    setDetailId(id); setError(null); setDetail(null);
    try {
      const d = await getReportDetail(id);
      if (validateRenderedReport(d.user_report)) { setDetail(d.user_report); }
      else { setError("报告内容校验失败，请联系管理员"); }
    } catch { setError("加载失败"); }
  }

  return (
    <div style={s.page}>
      <header style={s.header}><span style={s.title}>我的报告</span></header>
      <div style={s.body}>
        {loading && <div style={s.status}>加载中...</div>}
        {error && <div style={s.error}>{error}</div>}
        {items.map((r) => (
          <div key={r.assessment_id} style={s.card} onClick={() => viewDetail(r.assessment_id)}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <b>{r.tag || "未标签"}</b>
              <span>{r.feasibility_score != null ? `${r.feasibility_score}分` : ""}</span>
            </div>
            <div style={{ fontSize: 13, color: "#888", marginTop: 4 }}>
              {r.created_at?.slice(0, 10)} {r.used_template_report ? "· 模板" : ""}
            </div>
          </div>
        ))}
        {detail && (
          <div style={s.reportCard}>
            <h3>{detail.tag}（{detail.feasibility_score}分）</h3>
            <p style={{ color: "#666" }}>{detail.tag_explanation}</p>
            <p>{detail.preliminary_judgment}</p>
            <h4>优势</h4><ul>{detail.strengths.map((t,i) => <li key={i}>{t}</li>)}</ul>
            <h4>风险</h4><ul>{detail.risks.map((t,i) => <li key={i}>{t}</li>)}</ul>
            <h4>综合结论</h4><p>{detail.summary_conclusion}</p>
            <h4>推荐路径</h4><p>{detail.recommended_path}</p>
            <h4>30天行动计划</h4>
            <ol>{detail.action_plan_30days.map((a,i) => <li key={i}>{a}</li>)}</ol>
            <p style={{ color: "#999" }}>{detail.unlock_hint}</p>
          </div>
        )}
      </div>
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  page: { maxWidth: 700, margin: "0 auto", minHeight: "100dvh", background: "#f5f5f5" },
  header: { padding: "12px 16px", background: "#0D9488", color: "#fff" },
  title: { fontWeight: 600, fontSize: 16 },
  body: { padding: "12px 16px" },
  card: { background: "#fff", borderRadius: 10, padding: "12px 14px", marginBottom: 10, boxShadow: "0 1px 3px rgba(0,0,0,0.06)", cursor: "pointer" },
  status: { textAlign: "center", color: "#999", padding: 16 },
  error: { textAlign: "center", color: "#d32f2f", padding: 8 },
  reportCard: { background: "#fff", borderRadius: 12, padding: 16, marginTop: 12, boxShadow: "0 1px 3px rgba(0,0,0,0.08)" },
};
