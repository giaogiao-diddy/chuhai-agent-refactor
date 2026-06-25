import type { UserReport } from "./api";

export const FORBIDDEN_REPORT_TERMS = [
  "lead_score", "lead_priority", "lead_report", "raw_report",
  "sales_followup", "consultant_notes", "consultant_guide",
  "scoring_result", "audit_result", "scoring_error", "report_error",
  "销售话术", "顾问跟进", "线索优先级", "顾问备注",
];

export function getRenderedReportText(report: UserReport): string {
  return [
    report.tag, report.tag_explanation, report.preliminary_judgment,
    ...report.strengths, ...report.risks,
    report.summary_conclusion, report.recommended_path,
    report.risk_reminder, ...report.action_plan_30days, report.unlock_hint,
  ].join("\n");
}

export function validateRenderedReport(report: UserReport): boolean {
  const text = getRenderedReportText(report);
  return !FORBIDDEN_REPORT_TERMS.some((term) => text.includes(term));
}
