/**
 * 报告安全守门员 — JSON 结构审计 + 字段脱敏隔离。
 *
 * 两道关卡：
 *   1. validateStructure — 检查 AI 输出是否包含必填字段、字数合规、无异构内容
 *   2. splitReports      — 将完整 JSON 拆为用户版（安全）和顾问版（隔离）
 */

// ── 违禁词表 ──────────────────────────────────────────────────

const FORBIDDEN_PATTERNS = [
  /利润\s*提升\s*\d+%/,       // 承诺具体收益
  /收益\s*翻\s*\d+\s*倍/,      // 承诺具体收益
  /一定\s*能\s*成功/,          // 绝对化保证
  /唯一\s*出路/,               // 绝对化表达
  /必然\s*增长/,               // 绝对化表达
  /不需要\s*ICP\s*证/,         // 确定性合规结论
  /不需要\s*认证/,             // 确定性合规结论
  /不需要\s*缴税/,             // 确定性法律结论
];

// ── 必填字段清单 ──────────────────────────────────────────────

const SUMMARY_REQUIRED = [
  "total_score", "display_score", "tag", "tag_explanation",
  "preliminary_judgment", "strengths", "risks", "unlock_hint",
];

const FULL_REQUIRED = [
  "summary_conclusion", "positioning_assessment",
  "content_assessment", "conversion_assessment",
  "dimension_scores", "recommended_path", "risk_reminder",
  "action_plan_30days", "consultant_guide",
];

const SALES_REQUIRED = [
  "lead_temperature", "followup_focus", "opening_script",
];

// ── 字数上限 ──────────────────────────────────────────────────

const TEXT_LIMITS = {
  summary_conclusion: 400,
  positioning_assessment: 300,
  content_assessment: 300,
  conversion_assessment: 300,
  recommended_path: 250,
  risk_reminder: 250,
  opening_script: 200,
};

// ── 辅助 ──────────────────────────────────────────────────────

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function checkForbidden(text) {
  if (typeof text !== "string") return [];
  return FORBIDDEN_PATTERNS.filter((p) => p.test(text)).map((p) => p.source);
}

function checkRequiredFields(obj, required, label) {
  const missing = [];
  if (!isPlainObject(obj)) {
    return [`${label} 不是有效对象`];
  }
  required.forEach((key) => {
    if (obj[key] === undefined || obj[key] === null) {
      missing.push(`${label}.${key} 缺失`);
    }
  });
  return missing;
}

function checkTextLimits(obj, limits) {
  const violations = [];
  Object.keys(limits).forEach((key) => {
    const value = obj[key];
    if (typeof value === "string" && value.length > limits[key]) {
      violations.push(`${key} 超出字数限制: ${value.length}/${limits[key]}`);
    }
  });
  return violations;
}

// ── 导出函数 ──────────────────────────────────────────────────

/**
 * 第一道关：验证 AI 报告结构的合法性与内容安全性。
 *
 * @param {object} rawAiJson — DeepSeek 返回的原始 JSON
 * @returns {{ valid: boolean, errors: string[] }}
 */
function validateStructure(rawAiJson) {
  const errors = [];
  if (!isPlainObject(rawAiJson)) {
    return { valid: false, errors: ["AI 输出不是有效 JSON 对象"] };
  }

  // 必填字段检查
  errors.push(...checkRequiredFields(rawAiJson.summary_report, SUMMARY_REQUIRED, "summary_report"));
  errors.push(...checkRequiredFields(rawAiJson.full_report, FULL_REQUIRED, "full_report"));
  errors.push(...checkRequiredFields(rawAiJson.sales_followup, SALES_REQUIRED, "sales_followup"));

  // 违禁内容检查
  const fullText = JSON.stringify(rawAiJson);
  const forbidden = checkForbidden(fullText);
  forbidden.forEach((p) => errors.push(`违禁内容: ${p}`));

  // 字数检查
  if (isPlainObject(rawAiJson.full_report)) {
    errors.push(...checkTextLimits(rawAiJson.full_report, TEXT_LIMITS));
  }

  return { valid: errors.length === 0, errors };
}

/**
 * 第二道关：物理剥离销售敏感字段。
 *
 * 用户版（写入 reports）包含：
 *   - summary_report / full_report / total_score / display_score / tag
 *
 * 顾问版（写入 lead_reports）包含：
 *   - assessment_id / lead_score / lead_priority
 *   - sales_followup（完整保留）
 *   - 评分明细
 *
 * @param {object} rawAiJson       — AI 原始 JSON
 * @param {object} scoringMeta     — { feasibility_score, lead_score, feasibility_tag, lead_priority }
 * @param {string} assessmentId
 * @returns {{ userReport: object, consultantReport: object }}
 */
function splitReports(rawAiJson, scoringMeta, assessmentId) {
  const meta = scoringMeta || {};

  const userReport = {
    assessment_id: assessmentId,
    generation_type: "ai",
    summary_report: rawAiJson.summary_report || {},
    full_report: rawAiJson.full_report || {},
    total_score: meta.feasibility_score || 0,
    display_score: meta.display_score || (meta.feasibility_score || 0) + 43,
    tag: meta.feasibility_tag || "",
    is_unlocked: false,
    generated_at: new Date().toISOString(),
  };

  // 确保用户版不含顾问字段
  delete userReport.summary_report.lead_score;
  delete userReport.summary_report.lead_priority;
  delete userReport.full_report.lead_score;
  delete userReport.full_report.lead_priority;

  const consultantReport = {
    assessment_id: assessmentId,
    lead_score: meta.lead_score || 0,
    lead_priority: meta.lead_priority || "",
    feasibility_score: meta.feasibility_score || 0,
    feasibility_tag: meta.feasibility_tag || "",
    sales_followup: rawAiJson.sales_followup || {},
    generated_at: new Date().toISOString(),
  };

  return { userReport, consultantReport };
}

module.exports = {
  validateStructure,
  splitReports,
};
