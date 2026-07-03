"use client";

import { useRef, useState } from "react";
import { listAdminLeads, getAdminLeadDetail, updateAdminLeadFollowup } from "@/lib/api";
import { validateRenderedReport } from "@/lib/reportSafety";
import AppShell from "@/components/AppShell";
import type { AdminLeadListItem, AdminLeadDetail, FollowupStatus } from "@/lib/api";

const FOLLOWUP_OPTIONS: FollowupStatus[] = ["未联系", "已联系", "已预约", "已成交"];

const PRIORITY_BADGES: Record<string, string> = {
  P0: "badge-warning",
  P1: "badge-warning",
  P2: "badge-neutral",
  P3: "badge-neutral",
};

const PRIORITY_LABELS: Record<string, string> = {
  P0: "紧急", P1: "优先", P2: "正常", P3: "低优",
};

function priorityBadge(p: string | null): { cls: string; label: string } {
  const cls = PRIORITY_BADGES[p || ""] || "badge-neutral";
  const label = PRIORITY_LABELS[p || ""] || (p || "");
  return { cls, label };
}

export default function AdminLeadsPage() {
  const [items, setItems] = useState<AdminLeadListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<AdminLeadDetail | null>(null);
  const [followupStatus, setFollowupStatus] = useState<FollowupStatus>("未联系");
  const [followupNote, setFollowupNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [filterStatus, setFilterStatus] = useState<FollowupStatus | "全部">("全部");
  const [copied, setCopied] = useState(false);
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
    setCopied(false);
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

  async function copyFollowupScript() {
    if (!detail?.lead_report?.sales_followup) return;
    try {
      await navigator.clipboard.writeText(detail.lead_report.sales_followup);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* clipboard not available */ }
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
        {items.map(r => {
          const pb = priorityBadge(r.lead_priority);
          return (
            <div key={r.submission_id} className="card card-sm"
              style={{ marginBottom: 8, cursor: "pointer" }}
              onClick={() => viewDetail(r.submission_id)}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <b>{r.contact_name}</b>
                  {r.company_name && <span style={{ fontSize: 13, color: "var(--color-text-secondary)", marginLeft: 8 }}>{r.company_name}</span>}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  {r.lead_priority && (
                    <span className={`badge ${pb.cls}`} style={{ fontSize: 11 }}>{pb.label}</span>
                  )}
                  <span className="badge badge-neutral" style={{ fontSize: 11 }}>{r.followup_status}</span>
                </div>
              </div>
              <div style={{ fontSize: 13, color: "var(--color-text-muted)", marginTop: 4 }}>
                {[r.phone, r.wechat_id].filter(Boolean).join(" · ")}
              </div>
              <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 2 }}>
                {r.tag}{r.feasibility_score != null ? ` · ${r.feasibility_score}分` : ""}
                {r.used_template_report ? " · 模板" : ""}
                {" · "}{r.created_at?.slice(0, 10)}
              </div>
            </div>
          );
        })}

        {/* Detail panel */}
        {detail && (
          <div className="card" style={{ marginTop: 16 }}>
            {/* Contact profile */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
              <div>
                <h3 style={{ margin: 0 }}>{detail.contact_name}</h3>
                <p style={{ color: "var(--color-text-secondary)", margin: "4px 0" }}>
                  {detail.phone}{detail.wechat_id ? ` · 微信: ${detail.wechat_id}` : ""}
                </p>
                {detail.company_name && <p style={{ margin: "4px 0" }}>{detail.company_name}</p>}
                {detail.note && <p style={{ color: "var(--color-text-secondary)", margin: "4px 0", fontSize: 13 }}>备注：{detail.note}</p>}
              </div>
              <div style={{ textAlign: "right" }}>
                {detail.lead_priority && (
                  <span className={`badge ${priorityBadge(detail.lead_priority).cls}`} style={{ fontSize: 13, marginBottom: 4 }}>
                    {priorityBadge(detail.lead_priority).label}
                  </span>
                )}
                <div style={{ fontSize: 13, color: "var(--color-text-secondary)", marginTop: 4 }}>
                  {detail.tag} · {detail.feasibility_score}分
                  {detail.used_template_report ? " · 模板" : ""}
                </div>
              </div>
            </div>

            {/* Enterprise summary */}
            <div className="card" style={{ background: "var(--color-bg)", marginBottom: 16 }}>
              <h4 style={{ marginTop: 0 }}>企业画像摘要</h4>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4, fontSize: 13 }}>
                <div><b>标签：</b>{detail.user_report.tag}</div>
                <div><b>分数：</b>{detail.user_report.feasibility_score} / {detail.user_report.display_score}</div>
                <div><b>推荐路径：</b>{detail.user_report.recommended_path}</div>
                <div><b>跟进：</b>{detail.followup_status}{detail.followup_note ? ` — ${detail.followup_note}` : ""}</div>
              </div>
              <div style={{ marginTop: 8 }}>
                <b style={{ fontSize: 13 }}>优势：</b>
                <span style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>{detail.user_report.strengths.join("；")}</span>
              </div>
              <div style={{ marginTop: 4 }}>
                <b style={{ fontSize: 13 }}>风险：</b>
                <span style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>{detail.user_report.risks.join("；")}</span>
              </div>
            </div>

            {/* Consultant report */}
            <div className="card" style={{ background: "var(--color-warning-bg)", marginBottom: 16 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h4 style={{ margin: 0 }}>顾问报告</h4>
                <button className="btn btn-secondary btn-sm" onClick={copyFollowupScript}>
                  {copied ? "已复制" : "复制跟进话术"}
                </button>
              </div>
              <p style={{ marginTop: 8 }}><b>线索分数：</b>{detail.lead_report.lead_score}</p>
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
