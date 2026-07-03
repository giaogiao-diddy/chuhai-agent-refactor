"use client";

import { useState } from "react";
import type { PublicReportSummary, UserReport } from "@/lib/api";
import { submitLead } from "@/lib/api";

type Props = {
  report: PublicReportSummary | UserReport;
  usedTemplateReport?: boolean;
  assessmentId?: string | null;
  modelName?: string | null;
  showReportsLink?: boolean;
  onUnlocked?: () => void;
  wechatQrUrl?: string | null;
};

const DIM_NAMES: Record<string, string> = {
  enterprise_base: "企业基本盘",
  overseas_validation: "海外验证度",
  product_supply_chain: "产品与供应链竞争力",
  path_clarity: "出海路径清晰度",
  content_fitness: "短视频获客适配度",
  conversion_readiness: "销转承接能力",
  action_readiness: "企业出海行动力",
};

function dimLabel(name: string): string {
  // strip _feasibility / _lead suffix
  const base = name.replace(/_(feasibility|lead)$/, "");
  return DIM_NAMES[base] || "未知维度";
}

function isFull(report: PublicReportSummary | UserReport): report is UserReport {
  return "summary_conclusion" in report;
}

export default function UserReportCard({ report, usedTemplateReport, assessmentId, modelName, showReportsLink, onUnlocked, wechatQrUrl }: Props) {
  const [contactName, setContactName] = useState("");
  const [phone, setPhone] = useState("");
  const [wechatId, setWechatId] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const full = isFull(report);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!assessmentId || submitting || submitted) return;
    setSubmitting(true);
    setFormError(null);
    try {
      await submitLead(assessmentId, {
        contact_name: contactName.trim(),
        phone: phone.trim(),
        wechat_id: wechatId.trim() || undefined,
        company_name: companyName.trim() || undefined,
        note: note.trim() || undefined,
      });
      setSubmitted(true);
      if (onUnlocked) onUnlocked();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "提交失败，请稍后重试");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      {/* Score Hero */}
      <div style={s.hero}>
        <div style={s.heroScore}>
          <span style={s.heroNumber}>{report.display_score}</span>
          <span style={s.heroOutOf}>/100</span>
        </div>
        <div style={s.heroTag}>
          <span style={s.heroTagText}>{report.tag}</span>
          {usedTemplateReport && <span className="badge badge-warning" style={{ fontSize: 11, marginLeft: 8 }}>模板报告</span>}
          {modelName && <span style={{ fontSize: 11, color: "var(--color-text-muted)", marginLeft: 8 }}>{modelName}</span>}
        </div>
      </div>

      {!full && (
        <div className="card" style={{ marginBottom: 12 }}>
          <p style={{ color: "var(--color-text-secondary)" }}>{report.tag_explanation}</p>
          <p>{report.preliminary_judgment}</p>
          <h4>优势</h4><ul>{report.strengths.map((t, i) => <li key={i}>{t}</li>)}</ul>
          <h4>风险</h4><ul>{report.risks.map((t, i) => <li key={i}>{t}</li>)}</ul>
          <p style={{ color: "var(--color-text-muted)", fontSize: 13 }}>{report.unlock_hint}</p>
        </div>
      )}

      {full && (
        <>
          {/* Summary conclusion */}
          <div className="card" style={{ marginBottom: 12 }}>
            <h4 style={{ marginTop: 0 }}>综合结论</h4>
            <p>{report.summary_conclusion}</p>
          </div>

          {/* Strengths & Risks */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
            <div className="card">
              <h4 style={{ marginTop: 0, color: "var(--color-success)" }}>核心优势</h4>
              <ul style={{ paddingLeft: 18 }}>{report.strengths.map((t, i) => <li key={i} style={{ marginBottom: 4 }}>{t}</li>)}</ul>
            </div>
            <div className="card">
              <h4 style={{ marginTop: 0, color: "var(--color-danger)" }}>主要风险</h4>
              <ul style={{ paddingLeft: 18 }}>{report.risks.map((t, i) => <li key={i} style={{ marginBottom: 4 }}>{t}</li>)}</ul>
            </div>
          </div>

          {/* Dimension scores */}
          <div className="card" style={{ marginBottom: 12 }}>
            <h4 style={{ marginTop: 0 }}>维度得分</h4>
            {report.dimension_scores
              .filter(d => d.name.endsWith("_feasibility"))
              .map((d, i) => (
                <div key={i} style={s.dimRow}>
                  <span style={s.dimLabel}>{dimLabel(d.name)}</span>
                  <div style={s.dimBar}>
                    <div style={{ ...s.dimFill, width: `${d.normalized_score}%` }} />
                  </div>
                  <span style={s.dimScore}>{d.raw_score}/{d.max_score}</span>
                </div>
              ))}
          </div>

          {/* Positioning + Content + Conversion */}
          <div className="card" style={{ marginBottom: 12 }}>
            <h4 style={{ marginTop: 0 }}>定位分析</h4><p>{report.positioning_assessment}</p>
            <h4>内容/产品适配</h4><p>{report.content_assessment}</p>
            <h4>转化路径分析</h4><p>{report.conversion_assessment}</p>
          </div>

          {/* Recommended path */}
          <div className="card" style={{ marginBottom: 12 }}>
            <h4 style={{ marginTop: 0 }}>推荐路径</h4>
            <p>{report.recommended_path}</p>
            <h4 style={{ marginTop: 12 }}>风险提醒</h4>
            <p style={{ color: "var(--color-warning)" }}>{report.risk_reminder}</p>
          </div>

          {/* 30-day action plan checklist */}
          <div className="card" style={{ marginBottom: 12 }}>
            <h4 style={{ marginTop: 0 }}>30 天行动计划</h4>
            {report.action_plan_30days.map((a, i) => (
              <div key={i} style={s.checkItem}>
                <span style={s.checkbox}>☐</span>
                <span>{a}</span>
              </div>
            ))}
          </div>
        </>
      )}

      {/* WeChat QR */}
      {full && wechatQrUrl && (
        <div className="card" style={{ marginBottom: 12, textAlign: "center" }}>
          <img src={wechatQrUrl} alt="企业微信顾问二维码" style={{ maxWidth: 200, borderRadius: 8 }} />
          <p style={{ fontSize: 13, color: "var(--color-text-secondary)", marginTop: 8 }}>扫码添加企业微信顾问，获取 1v1 解读</p>
        </div>
      )}

      {/* Report meta */}
      {assessmentId && <p style={{ fontSize: 11, color: "var(--color-text-muted)", marginBottom: 12 }}>报告编号：{assessmentId}</p>}
      {showReportsLink && (
        <p style={{ marginBottom: 12 }}><a href="/reports" style={{ color: "var(--color-primary)", fontSize: 14 }}>查看我的报告</a></p>
      )}

      {/* Unlock form */}
      {assessmentId && !full && (
        <div className="card" style={{ marginBottom: 12 }}>
          <h4 style={{ marginTop: 0 }}>解锁完整报告与顾问解读</h4>
          <p style={{ fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 12 }}>
            提交联系方式后，可查看完整诊断报告，顾问会根据诊断结果联系你。
          </p>
          {submitted ? (
            <p style={{ color: "var(--color-primary)", fontSize: 14 }}>已提交，顾问会根据诊断结果联系你。</p>
          ) : (
            <form onSubmit={handleSubmit}>
              <input className="input" style={{ marginBottom: 8 }} placeholder="姓名（必填）" value={contactName}
                onChange={e => setContactName(e.target.value)} required disabled={submitting} />
              <input className="input" style={{ marginBottom: 8 }} placeholder="手机/联系方式（必填）" value={phone}
                onChange={e => setPhone(e.target.value)} required disabled={submitting} />
              <input className="input" style={{ marginBottom: 8 }} placeholder="微信号（可选）" value={wechatId}
                onChange={e => setWechatId(e.target.value)} disabled={submitting} />
              <input className="input" style={{ marginBottom: 8 }} placeholder="公司名称（可选）" value={companyName}
                onChange={e => setCompanyName(e.target.value)} disabled={submitting} />
              <input className="input" style={{ marginBottom: 8 }} placeholder="补充说明（可选）" value={note}
                onChange={e => setNote(e.target.value)} disabled={submitting} />
              {formError && <p style={{ color: "var(--color-danger)", fontSize: 13, marginBottom: 8 }}>{formError}</p>}
              <button type="submit" className="btn btn-primary" disabled={submitting || !contactName.trim() || !phone.trim()}>
                {submitting ? "提交中..." : "提交并解锁完整报告"}
              </button>
            </form>
          )}
        </div>
      )}
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  hero: {
    background: "linear-gradient(135deg, #0D9488 0%, #0F766E 100%)",
    color: "#fff", borderRadius: "var(--radius-lg)", padding: "24px 28px",
    marginBottom: 16, display: "flex", alignItems: "center", gap: 24,
  },
  heroScore: { display: "flex", alignItems: "baseline", gap: 2 },
  heroNumber: { fontSize: 48, fontWeight: 700, lineHeight: 1 },
  heroOutOf: { fontSize: 18, opacity: 0.7 },
  heroTag: { display: "flex", flexDirection: "column", gap: 4 },
  heroTagText: { fontSize: 20, fontWeight: 600 },
  dimRow: { display: "flex", alignItems: "center", gap: 10, marginBottom: 6 },
  dimLabel: { fontSize: 13, minWidth: 130, color: "var(--color-text-secondary)" },
  dimBar: { flex: 1, height: 8, background: "var(--color-border)", borderRadius: 4, overflow: "hidden" },
  dimFill: { height: "100%", background: "var(--color-primary)", borderRadius: 4, transition: "width 0.3s" },
  dimScore: { fontSize: 12, minWidth: 50, textAlign: "right", color: "var(--color-text-secondary)" },
  checkItem: { display: "flex", alignItems: "flex-start", gap: 10, padding: "6px 0", borderBottom: "1px solid var(--color-border)", fontSize: 14 },
  checkbox: { fontSize: 18, color: "var(--color-primary)", flexShrink: 0, marginTop: -1 },
};
