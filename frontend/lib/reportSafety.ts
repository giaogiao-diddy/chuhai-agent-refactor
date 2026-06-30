import type { PublicReportSummary, UserReport } from "./api";

export const FORBIDDEN_REPORT_TERMS = [
  "lead_score", "lead_priority", "lead_report", "raw_report",
  "sales_followup", "consultant_notes", "consultant_guide",
  "scoring_result", "audit_result", "scoring_error", "report_error",
  "销售话术", "顾问跟进", "线索优先级", "顾问备注",
];

function isFull(report: PublicReportSummary | UserReport): report is UserReport {
  return "summary_conclusion" in report;
}

export function getRenderedReportText(report: PublicReportSummary | UserReport): string {
  const parts = [
    report.tag, report.tag_explanation, report.preliminary_judgment,
    ...report.strengths, ...report.risks, report.unlock_hint,
  ];
  if (isFull(report)) {
    parts.push(
      report.positioning_assessment,
      report.content_assessment,
      report.conversion_assessment,
      report.summary_conclusion,
      report.recommended_path,
      report.risk_reminder,
      report.consultant_guide,
      ...report.action_plan_30days,
      ...report.dimension_scores.map(d => `${d.name} ${d.normalized_score}`),
    );
  }
  return parts.join("\n");
}

export function validateRenderedReport(report: PublicReportSummary | UserReport): boolean {
  const text = getRenderedReportText(report);
  return !FORBIDDEN_REPORT_TERMS.some((term) => text.includes(term));
}
