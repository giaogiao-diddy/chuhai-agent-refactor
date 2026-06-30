import { getRenderedReportText, validateRenderedReport } from "../lib/reportSafety";
import type { PublicReportSummary, UserReport } from "../lib/api";

let passed = 0;
let failed = 0;

function assert(condition: boolean, name: string) {
  if (condition) { passed++; console.log(`  ✓ ${name}`); }
  else { failed++; console.error(`  ✗ FAIL: ${name}`); }
}

const summary: PublicReportSummary = {
  feasibility_score: 50, display_score: 50,
  tag: "基础具备型", tag_explanation: "具备出海基础",
  preliminary_judgment: "初步具备出海条件",
  strengths: ["源头工厂"], risks: ["社媒经验不足"],
  unlock_hint: "添加企业微信顾问解锁完整报告",
};

const fullClean: UserReport = {
  ...summary,
  summary_conclusion: "综合结论", positioning_assessment: "定位分析",
  content_assessment: "内容适配", conversion_assessment: "转化路径",
  dimension_scores: [{ name: "企业基础", raw_score: 15, max_score: 20, normalized_score: 75 }],
  recommended_path: "推荐路径", risk_reminder: "风险提醒",
  action_plan_30days: ["第一步", "第二步", "第三步", "第四步"],
  consultant_guide: "顾问引导",
};

console.log("报告安全扫描测试:");

// 1. summary 通过
assert(validateRenderedReport(summary), "summary 报告安全文本通过");

// 2-7: full report 每个字段独立命中 forbidden
// 每个测试构造一个只在目标字段写入 forbidden 的报告，确保字段级覆盖

const fieldTests: [string, UserReport][] = [
  ["positioning_assessment", { ...fullClean, positioning_assessment: "含sales_followup的定位" }],
  ["content_assessment", { ...fullClean, content_assessment: "含consultant_notes的内容" }],
  ["conversion_assessment", { ...fullClean, conversion_assessment: "含sales_followup的转化" }],
  ["summary_conclusion", { ...fullClean, summary_conclusion: "含sales_followup的结论" }],
  ["recommended_path", { ...fullClean, recommended_path: "含sales_followup的路径" }],
  ["risk_reminder", { ...fullClean, risk_reminder: "含sales_followup的风险" }],
  ["action_plan_30days", { ...fullClean, action_plan_30days: ["第一步", "含sales_followup的第二步", "第三步", "第四步"] }],
  ["dimension_scores.name", { ...fullClean, dimension_scores: [{ name: "lead_score维度", raw_score: 0, max_score: 20, normalized_score: 0 }] }],
  ["consultant_guide", { ...fullClean, consultant_guide: "含sales_followup的引导" }],
];
for (const [label, r] of fieldTests) {
  assert(!validateRenderedReport(r), `full report ${label} 命中 forbidden term 返回 false`);
}

// 8. clean full report 通过
assert(validateRenderedReport(fullClean), "clean full report 通过");

console.log(`\n${passed + failed} tests: ${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
