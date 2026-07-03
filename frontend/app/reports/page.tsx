"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { listReports, getReportDetail } from "@/lib/api";
import { validateRenderedReport } from "@/lib/reportSafety";
import AuthBar from "@/components/AuthBar";
import UserReportCard from "@/components/UserReportCard";
import type { PublicReportSummary, ReportListItem, UserReport } from "@/lib/api";

export default function ReportsPage() {
  const [items, setItems] = useState<ReportListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<PublicReportSummary | UserReport | null>(null);
  const [detailAssessmentId, setDetailAssessmentId] = useState<string | null>(null);
  const [detailFollowupStatus, setDetailFollowupStatus] = useState<string | null>(null);
  const [wechatQrUrl, setWechatQrUrl] = useState<string | null>(null);
  const latestDetailRequestRef = useRef<string | null>(null);

  useEffect(() => {
    listReports().then(setItems).catch(() => setError("加载失败")).finally(() => setLoading(false));
  }, []);

  const reloadDetail = useCallback(async (id: string) => {
    try {
      const d = await getReportDetail(id);
      const display = d.is_unlocked && d.user_report ? d.user_report : d.report_summary;
      if (validateRenderedReport(display)) {
        setDetail(display);
        setDetailFollowupStatus(d.followup_status);
        setWechatQrUrl(d.wechat_qr_url);
        setItems(prev => prev.map(item =>
          item.assessment_id === id
            ? { ...item, followup_status: d.followup_status }
            : item
        ));
      }
    } catch {
      setError("加载失败");
    }
  }, []);

  async function viewDetail(id: string) {
    latestDetailRequestRef.current = id;
    setError(null);
    setDetail(null);
    setDetailAssessmentId(id);
    try {
      const d = await getReportDetail(id);
      if (latestDetailRequestRef.current !== id) return;
      const display = d.is_unlocked && d.user_report ? d.user_report : d.report_summary;
      if (validateRenderedReport(display)) {
        setDetail(display);
        setDetailFollowupStatus(d.followup_status);
        setWechatQrUrl(d.wechat_qr_url);
      } else {
        setError("报告内容校验失败，请联系管理员");
      }
    } catch {
      if (latestDetailRequestRef.current !== id) return;
      setError("加载失败");
    }
  }

  return (
    <div style={s.page}>
      <AuthBar />
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
              {r.created_at?.slice(0, 10)} · 跟进：{r.followup_status || "待留资"}
              {r.used_template_report ? " · 模板" : ""}
              {r.model_name ? ` · ${r.model_name}` : ""}
            </div>
          </div>
        ))}
        {detail && (
          <>
            <div style={s.followupRow}>
              跟进状态：{detailFollowupStatus || "待留资"}
            </div>
            <UserReportCard
            report={detail}
            assessmentId={detailAssessmentId}
            onUnlocked={() => reloadDetail(detailAssessmentId!)}
            wechatQrUrl={wechatQrUrl}
          />
          </>)
        }
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
  followupRow: { background: "#fff", borderRadius: 10, padding: "8px 14px", marginBottom: 10, fontSize: 13, color: "#666", boxShadow: "0 1px 3px rgba(0,0,0,0.06)" },
};
