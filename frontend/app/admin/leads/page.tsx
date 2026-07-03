"use client";

import { useRef, useState } from "react";
import { listAdminLeads, getAdminLeadDetail, updateAdminLeadFollowup } from "@/lib/api";
import { validateRenderedReport } from "@/lib/reportSafety";
import AppShell from "@/components/AppShell";
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
    <AppShell title="顾问后台">
      <div style={{ maxWidth: 900, margin: "0 auto" }}>
        {/* Toolbar */}
        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          <button className="btn btn-primary btn-sm" onClick={load} disabled={loading}>
            {loading ? "加载中..." : "加载线索"}
          </button>
          <select className="select" style={{ width: "auto" }} value={filterStatus}
            onChange={e => setFilterStatus(e.target.value as FollowupStatus | "全部")}>
            <option value="全部">全部</option>
            {FOLLOWUP_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>

        {error && <div className="error-msg">{error}</div>}

        {/* Lead list */}
        {items.map(r => (
          <div key={r.submission_id} className="card card-sm"
            style={{ marginBottom: 8, cursor: "pointer" }}
            onClick={() => viewDetail(r.submission_id)}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <b>{r.contact_name}</b>
              <span style={{ fontSize: 13, color: r.lead_priority === "P0" ? "var(--color-danger)" : "var(--color-text-secondary)" }}>
                <span className={`badge ${r.lead_priority === "P0" ? "badge-warning" : "badge-neutral"}`}>
                  {r.lead_priority || ""}
                </span>
                {" "}{r.followup_status}
              </span>
            </div>
            <div style={{ fontSize: 13, color: "var(--color-text-muted)", marginTop: 4 }}>
              {[r.phone, r.wechat_id, r.company_name].filter(Boolean).join(" · ")}
            </div>
            <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 2 }}>
              {r.tag}{r.feasibility_score != null ? ` · ${r.feasibility_score}分` : ""}
              {r.used_template_report ? " · 模板" : ""}
            </div>
          </div>
        ))}

        {/* Detail panel */}
        {detail && (
          <div className="card" style={{ marginTop: 16 }}>
            <h3 style={{ marginTop: 0 }}>{detail.contact_name}</h3>
            <p style={{ color: "var(--color-text-secondary)" }}>
              {detail.phone}{detail.wechat_id ? ` · 微信: ${detail.wechat_id}` : ""}
            </p>
            {detail.company_name && <p>{detail.company_name}</p>}
            {detail.note && <p style={{ color: "var(--color-text-secondary)" }}>{detail.note}</p>}

            {/* Consultant report */}
            <div className="card" style={{ background: "var(--color-warning-bg)", marginBottom: 16 }}>
              <h4>顾问报告</h4>
              <p><b>线索分数：</b>{detail.lead_report.lead_score}</p>
              <p><b>优先级：</b>{detail.lead_report.lead_priority}</p>
              <h4>销售话术</h4><p>{detail.lead_report.sales_followup}</p>
              <h4>顾问备注</h4><p>{detail.lead_report.consultant_notes}</p>
            </div>

            {/* User report */}
            <h4>{detail.user_report.tag}（{detail.user_report.feasibility_score}分）</h4>
            <p style={{ color: "var(--color-text-secondary)" }}>{detail.user_report.tag_explanation}</p>
            <p>{detail.user_report.preliminary_judgment}</p>
            <h4>优势</h4><ul>{detail.user_report.strengths.map((t, i) => <li key={i}>{t}</li>)}</ul>
            <h4>风险</h4><ul>{detail.user_report.risks.map((t, i) => <li key={i}>{t}</li>)}</ul>
            <h4>推荐路径</h4><p>{detail.user_report.recommended_path}</p>
            <h4>30天行动计划</h4>
            <ol>{detail.user_report.action_plan_30days.map((a, i) => <li key={i}>{a}</li>)}</ol>

            {/* Followup form */}
            <div style={{ marginTop: 20, paddingTop: 16, borderTop: "1px solid var(--color-border)" }}>
              <h4>跟进</h4>
              <select className="select" style={{ marginBottom: 8 }} value={followupStatus}
                onChange={e => setFollowupStatus(e.target.value as FollowupStatus)} disabled={saving}>
                {FOLLOWUP_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <textarea className="textarea" placeholder="跟进备注（可选）" value={followupNote}
                onChange={e => setFollowupNote(e.target.value)} disabled={saving} rows={3}
                style={{ marginBottom: 8 }}
              />
              <button className="btn btn-primary" onClick={saveFollowup} disabled={saving}>
                {saving ? "保存中..." : "保存跟进"}
              </button>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
