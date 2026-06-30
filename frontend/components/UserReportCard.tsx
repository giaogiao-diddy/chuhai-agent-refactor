"use client";

import { useState } from "react";
import type { PublicReportSummary, UserReport } from "@/lib/api";
import { submitLead } from "@/lib/api";

type Props = {
  report: PublicReportSummary | UserReport;
  usedTemplateReport?: boolean;
  assessmentId?: string | null;
  showReportsLink?: boolean;
  onUnlocked?: () => void;
  wechatQrUrl?: string | null;
};

function isFull(report: PublicReportSummary | UserReport): report is UserReport {
  return "summary_conclusion" in report;
}

export default function UserReportCard({ report, usedTemplateReport, assessmentId, showReportsLink, onUnlocked, wechatQrUrl }: Props) {
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
    <div style={s.card}>
      {usedTemplateReport && <p style={s.templateNote}>本次报告由保守模板生成</p>}
      <p><b>总分：</b>{report.feasibility_score} / 100（{report.tag}）</p>
      <p style={{ color: "#666" }}>{report.tag_explanation}</p>
      <p>{report.preliminary_judgment}</p>
      <h4>优势</h4><ul>{report.strengths.map((t, i) => <li key={i}>{t}</li>)}</ul>
      <h4>风险</h4><ul>{report.risks.map((t, i) => <li key={i}>{t}</li>)}</ul>

      {full && (
        <>
          <h4>定位分析</h4><p>{report.positioning_assessment}</p>
          <h4>内容/产品适配</h4><p>{report.content_assessment}</p>
          <h4>转化路径分析</h4><p>{report.conversion_assessment}</p>
          <h4>维度得分</h4>
          <ul>{report.dimension_scores.map((d, i) => <li key={i}>{d.name}: {d.normalized_score}</li>)}</ul>
          <h4>综合结论</h4><p>{report.summary_conclusion}</p>
          <h4>推荐路径</h4><p>{report.recommended_path}</p>
          <h4>风险提醒</h4><p>{report.risk_reminder}</p>
          <h4>30天行动计划</h4>
          <ol>{report.action_plan_30days.map((a, i) => <li key={i}>{a}</li>)}</ol>
        </>
      )}

      {full && wechatQrUrl && (
        <div style={{ marginTop: 16, paddingTop: 16, borderTop: "1px solid #eee", textAlign: "center" }}>
          <img src={wechatQrUrl} alt="企业微信顾问二维码" style={{ maxWidth: 200, borderRadius: 8 }} />
          <p style={{ fontSize: 13, color: "#666", marginTop: 8 }}>扫码添加企业微信顾问，获取 1v1 解读</p>
        </div>
      )}

      <p style={{ color: "#999" }}>{report.unlock_hint}</p>
      {assessmentId && <p style={s.assessmentId}>报告编号：{assessmentId}</p>}
      {showReportsLink && (
        <p style={{ marginTop: 8 }}><a href="/reports" style={{ color: "#0D9488", fontSize: 14 }}>查看我的报告</a></p>
      )}

      {assessmentId && !full && (
        <div style={s.form}>
          <h4 style={{ marginBottom: 8 }}>解锁完整报告</h4>
          {submitted ? (
            <p style={{ color: "#0D9488", fontSize: 14 }}>已提交，顾问会根据诊断结果联系你。</p>
          ) : (
            <form onSubmit={handleSubmit}>
              <input style={s.input} placeholder="姓名（必填）" value={contactName}
                onChange={e => setContactName(e.target.value)} required disabled={submitting} />
              <input style={s.input} placeholder="手机/联系方式（必填）" value={phone}
                onChange={e => setPhone(e.target.value)} required disabled={submitting} />
              <input style={s.input} placeholder="微信号（可选）" value={wechatId}
                onChange={e => setWechatId(e.target.value)} disabled={submitting} />
              <input style={s.input} placeholder="公司名称（可选）" value={companyName}
                onChange={e => setCompanyName(e.target.value)} disabled={submitting} />
              <input style={s.input} placeholder="补充说明（可选）" value={note}
                onChange={e => setNote(e.target.value)} disabled={submitting} />
              {formError && <p style={{ color: "#d32f2f", fontSize: 13, marginBottom: 8 }}>{formError}</p>}
              <button type="submit" style={s.btn} disabled={submitting || !contactName.trim() || !phone.trim()}>
                {submitting ? "提交中..." : "提交"}
              </button>
            </form>
          )}
        </div>
      )}
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  card: { background: "#fff", borderRadius: 12, padding: 16, marginBottom: 12, boxShadow: "0 1px 3px rgba(0,0,0,0.08)" },
  templateNote: { background: "#fff8e1", padding: "4px 10px", borderRadius: 6, fontSize: 13, color: "#795548", marginBottom: 8 },
  assessmentId: { fontSize: 11, color: "#aaa", marginTop: 8, wordBreak: "break-all" },
  form: { marginTop: 16, paddingTop: 16, borderTop: "1px solid #eee" },
  input: { display: "block", width: "100%", padding: "8px 12px", marginBottom: 8, borderRadius: 8, border: "1px solid #ccc", fontSize: 14, outline: "none", boxSizing: "border-box" },
  btn: { padding: "8px 20px", borderRadius: 8, border: "none", background: "#0D9488", color: "#fff", fontSize: 14, cursor: "pointer" },
};
