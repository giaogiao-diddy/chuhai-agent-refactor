"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { listReports, getReportDetail } from "@/lib/api";
import { validateRenderedReport } from "@/lib/reportSafety";
import AppShell from "@/components/AppShell";
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
          item.assessment_id === id ? { ...item, followup_status: d.followup_status } : item
        ));
      }
    } catch { setError("加载失败"); }
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
    <AppShell title="我的报告">
      <div style={{ maxWidth: 700, margin: "0 auto" }}>
        {loading && <div className="status-msg">加载中...</div>}
        {error && <div className="error-msg">{error}</div>}
        {!loading && !error && items.length === 0 && (
          <div className="card" style={{ textAlign: "center", padding: 32 }}>
            <div className="status-msg">暂无诊断报告</div>
            <a href="/chat" className="btn btn-primary" style={{ marginTop: 12 }}>开始诊断</a>
          </div>
        )}
        {items.map(r => (
          <div key={r.assessment_id} className="card card-sm"
            style={{ marginBottom: 8, cursor: "pointer" }}
            onClick={() => viewDetail(r.assessment_id)}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <b>{r.tag || "未标签"}</b>
              <span style={{ fontSize: 14, color: "var(--color-text-secondary)" }}>
                {r.feasibility_score != null ? `${r.feasibility_score}分` : ""}
              </span>
            </div>
            <div style={{ fontSize: 13, color: "var(--color-text-muted)", marginTop: 4 }}>
              {r.created_at?.slice(0, 10)} · 跟进：{r.followup_status || "待留资"}
              {r.used_template_report ? " · 模板" : ""}
              {r.model_name ? ` · ${r.model_name}` : ""}
            </div>
          </div>
        ))}
        {detail && (
          <>
            <div className="card card-sm" style={{ marginBottom: 12, fontSize: 13, color: "var(--color-text-secondary)" }}>
              跟进状态：{detailFollowupStatus || "待留资"}
            </div>
            <UserReportCard
              report={detail}
              assessmentId={detailAssessmentId}
              onUnlocked={() => reloadDetail(detailAssessmentId!)}
              wechatQrUrl={wechatQrUrl}
            />
          </>
        )}
      </div>
    </AppShell>
  );
}
