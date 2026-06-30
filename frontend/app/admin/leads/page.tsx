"use client";

import { useRef, useState } from "react";
import { listAdminLeads, getAdminLeadDetail, updateAdminLeadFollowup } from "@/lib/api";
import { validateRenderedReport } from "@/lib/reportSafety";
import AuthBar from "@/components/AuthBar";
import type { AdminLeadListItem, AdminLeadDetail, FollowupStatus } from "@/lib/api";

const FOLLOWUP_OPTIONS: FollowupStatus[] = ["未联系", "已联系", "已预约", "已成交"];

export default function AdminLeadsPage() {
  const [items, setItems] = useState<AdminLeadListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<AdminLeadDetail | null>(null);
  const [followupStatus, setFollowupStatus] = useState<FollowupStatus>("未联系");
  const [followupNote, setFollowupNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [filterStatus, setFilterStatus] = useState<FollowupStatus | "全部">("全部");
  const latestDetailRequestRef = useRef<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    setDetail(null);
    try {
      const data = await listAdminLeads(
        filterStatus === "全部" ? undefined : { followup_status: filterStatus }
      );
      setItems(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  async function viewDetail(submissionId: string) {
    latestDetailRequestRef.current = submissionId;
    setError(null);
    setDetail(null);
    try {
      const d = await getAdminLeadDetail(submissionId);
      if (latestDetailRequestRef.current !== submissionId) return;
      if (!validateRenderedReport(d.user_report)) {
        setError("报告内容校验失败，请联系管理员"); return;
      }
      setDetail(d);
      setFollowupStatus(d.followup_status);
      setFollowupNote(d.followup_note || "");
    } catch (err: unknown) {
      if (latestDetailRequestRef.current !== submissionId) return;
      setError(err instanceof Error ? err.message : "加载失败");
    }
  }

  async function saveFollowup() {
    if (!detail || saving) return;
    setSaving(true);
    setError(null);
    try {
      const d = await updateAdminLeadFollowup(detail.submission_id, {
        followup_status: followupStatus,
        followup_note: followupNote.trim() || undefined,
      });
      setDetail(d);
      if (filterStatus !== "全部" && d.followup_status !== filterStatus) {
        setItems(prev => prev.filter(item => item.submission_id !== d.submission_id));
      } else {
        setItems(prev => prev.map(item =>
          item.submission_id === d.submission_id
            ? { ...item, followup_status: d.followup_status }
            : item
        ));
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "更新失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={s.page}>
      <AuthBar />
      <header style={s.header}><span style={s.title}>线索管理</span></header>
      <div style={s.body}>
        <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          <button style={s.btn} onClick={load} disabled={loading}>
            {loading ? "加载中..." : "加载线索"}
          </button>
          <select style={s.filterSelect} value={filterStatus}
            onChange={e => setFilterStatus(e.target.value as FollowupStatus | "全部")}>
            <option value="全部">全部</option>
            {FOLLOWUP_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        {error && <div style={s.error}>{error}</div>}
        {items.map((r) => (
          <div key={r.submission_id} style={s.card} onClick={() => viewDetail(r.submission_id)}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <b>{r.contact_name}</b>
              <span style={{ color: r.lead_priority === "P0" ? "#d32f2f" : "#666" }}>
                {r.lead_priority || ""} · {r.followup_status}
              </span>
            </div>
            <div style={{ fontSize: 13, color: "#888", marginTop: 4 }}>
              {[r.phone, r.wechat_id, r.company_name].filter(Boolean).join(" · ")}
            </div>
            <div style={{ fontSize: 12, color: "#aaa", marginTop: 2 }}>
              {r.tag}{r.feasibility_score != null ? ` · ${r.feasibility_score}分` : ""}
              {r.used_template_report ? " · 模板" : ""}
            </div>
          </div>
        ))}
        {detail && (
          <div style={s.detailCard}>
            <h3>{detail.contact_name}</h3>
            <p>{detail.phone}{detail.wechat_id ? ` · 微信: ${detail.wechat_id}` : ""}</p>
            {detail.company_name && <p>{detail.company_name}</p>}
            {detail.note && <p style={{ color: "#666" }}>{detail.note}</p>}

            {/* 顾问版报告 */}
            <div style={s.consultantSection}>
              <h4>顾问报告</h4>
              <p><b>线索分数：</b>{detail.lead_report.lead_score}</p>
              <p><b>优先级：</b>{detail.lead_report.lead_priority}</p>
              <h4>销售话术</h4><p>{detail.lead_report.sales_followup}</p>
              <h4>顾问备注</h4><p>{detail.lead_report.consultant_notes}</p>
            </div>

            {/* 用户版报告 */}
            <h4>{detail.user_report.tag}（{detail.user_report.feasibility_score}分）</h4>
            <p style={{ color: "#666" }}>{detail.user_report.tag_explanation}</p>
            <p>{detail.user_report.preliminary_judgment}</p>
            <h4>优势</h4><ul>{detail.user_report.strengths.map((t,i) => <li key={i}>{t}</li>)}</ul>
            <h4>风险</h4><ul>{detail.user_report.risks.map((t,i) => <li key={i}>{t}</li>)}</ul>
            <h4>推荐路径</h4><p>{detail.user_report.recommended_path}</p>
            <h4>30天行动计划</h4>
            <ol>{detail.user_report.action_plan_30days.map((a,i) => <li key={i}>{a}</li>)}</ol>

            {/* 跟进表单 */}
            <div style={s.followupSection}>
              <h4>跟进</h4>
              <select style={s.select} value={followupStatus}
                onChange={e => setFollowupStatus(e.target.value as FollowupStatus)} disabled={saving}>
                {FOLLOWUP_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <textarea style={s.textarea} placeholder="跟进备注（可选）" value={followupNote}
                onChange={e => setFollowupNote(e.target.value)} disabled={saving} rows={3} />
              <button style={s.saveBtn} onClick={saveFollowup} disabled={saving}>
                {saving ? "保存中..." : "保存跟进"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  page: { maxWidth: 800, margin: "0 auto", minHeight: "100dvh", background: "#f5f5f5" },
  header: { padding: "12px 16px", background: "#1a1a2e", color: "#fff" },
  title: { fontWeight: 600, fontSize: 16 },
  body: { padding: "12px 16px" },
  btn: { padding: "8px 16px", borderRadius: 8, border: "none", background: "#0D9488", color: "#fff", fontSize: 14, cursor: "pointer" },
  filterSelect: { padding: "8px 12px", borderRadius: 8, border: "1px solid #ccc", fontSize: 14, outline: "none", background: "#fff" },
  card: { background: "#fff", borderRadius: 10, padding: "12px 14px", marginBottom: 10, boxShadow: "0 1px 3px rgba(0,0,0,0.06)", cursor: "pointer" },
  error: { textAlign: "center", color: "#d32f2f", padding: 8 },
  detailCard: { background: "#fff", borderRadius: 12, padding: 16, marginTop: 12, marginBottom: 12, boxShadow: "0 1px 3px rgba(0,0,0,0.08)" },
  consultantSection: { padding: "10px 14px", marginBottom: 16, borderRadius: 8, background: "#fff8e1" },
  followupSection: { marginTop: 16, paddingTop: 16, borderTop: "1px solid #eee" },
  select: { display: "block", width: "100%", padding: "8px 12px", marginBottom: 8, borderRadius: 8, border: "1px solid #ccc", fontSize: 14, outline: "none" },
  textarea: { display: "block", width: "100%", padding: "8px 12px", marginBottom: 8, borderRadius: 8, border: "1px solid #ccc", fontSize: 14, outline: "none", resize: "vertical", boxSizing: "border-box" },
  saveBtn: { padding: "8px 20px", borderRadius: 8, border: "none", background: "#0D9488", color: "#fff", fontSize: 14, cursor: "pointer" },
};
