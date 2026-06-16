"use strict";

const app = getApp();
const { get, post } = require("../../utils/api");

const DIMENSION_LABELS = {
  enterprise_capacity: "企业承载力",
  overseas_foundation: "出海基础",
  product_trust_asset: "信任资产",
  content_acquisition: "内容获客",
  conversion_system: "转化系统"
};

const METHOD_TAGS = {
  "定位": "定位定生死",
  "内容": "内容定江山",
  "转化": "SOP定天下"
};

const ACTION_DAY_LABELS = ["第1-7天", "第8-14天", "第15-21天", "第22-30天"];

function clampPercent(value) {
  const n = Number(value) || 0;
  return Math.max(0, Math.min(100, n));
}

function normalizeDimensionRows(dimensionScores) {
  if (!dimensionScores) return [];

  const entries = Array.isArray(dimensionScores)
    ? dimensionScores.map((item, i) => [item.key || item.name || String(i), item])
    : Object.keys(dimensionScores).map(k => [k, dimensionScores[k]]);

  return entries.map(([key, value]) => {
    const isObj = value && typeof value === "object" && !Array.isArray(value);
    const score = isObj ? Number(value.score || value.value || 0) : Number(value || 0);
    const maxScore = isObj ? Number(value.max_score || value.maxScore || 100) : 100;
    const percent = clampPercent(maxScore > 0 ? (score / maxScore) * 100 : score);
    const percentText = `${Math.round(percent)}%`;

    return {
      key,
      name: DIMENSION_LABELS[key] || (isObj && value.label) || key,
      score,
      maxScore,
      scoreText: percentText,
      percent,
      percentText,
      comment: isObj ? (value.diagnosis || value.next_action || value.comment || value.level || value.description || "") : ""
    };
  });
}

function stripLeadingMethodTag(text) {
  const raw = String(text || "").trim();
  const bracketMatch = raw.match(/^【([^】]{2,18})】\s*(.*)$/);
  if (bracketMatch) {
    return {
      methodTag: bracketMatch[1],
      content: bracketMatch[2].trim()
    };
  }

  const colonMatch = raw.match(/^(定位定生死|内容定江山|SOP\s*定天下|SOP定天下)[:：]\s*(.*)$/);
  if (colonMatch) {
    return {
      methodTag: colonMatch[1].replace(/\s+/g, ""),
      content: colonMatch[2].trim()
    };
  }

  return { methodTag: "", content: raw };
}

/**
 * V3 结构化字段 → 渲染 sections
 *
 * 后端 full_report.{positioning_assessment, content_assessment, conversion_assessment}
 * 是三个独立的结构化文本块，直接展示，不做断句/关键词匹配。
 */
function buildStructuredSections(report) {
  if (!report) return [];

  if (Array.isArray(report.diagnosis_cards) && report.diagnosis_cards.length) {
    return report.diagnosis_cards
      .map(item => {
        const parsed = stripLeadingMethodTag(item.content || "");
        const title = item.title || "诊断";
        return {
          title,
          methodTag: item.method_tag || parsed.methodTag || METHOD_TAGS[title] || "",
          content: parsed.content
        };
      })
      .filter(item => item.content);
  }

  const mapping = [
    { key: "positioning_assessment", label: "定位评估" },
    { key: "content_assessment", label: "内容矩阵评估" },
    { key: "conversion_assessment", label: "转化与合规评估" }
  ];

  const sections = mapping
    .map(m => {
      const parsed = stripLeadingMethodTag(report[m.key] || "");
      return {
        title: m.label,
        methodTag: parsed.methodTag,
        content: parsed.content
      };
    })
    .filter(s => s.content);

  // 如果三个结构化字段都缺失，回退为展示 summary_conclusion 作为单段综合结论
  if (sections.length === 0 && report.summary_conclusion) {
    sections.push({
      title: "综合结论",
      content: String(report.summary_conclusion).trim()
    });
  }

  return sections;
}

function buildStrategyItems(report) {
  const strategy = report && report.strategy_path;
  if (!strategy || typeof strategy !== "object" || Array.isArray(strategy)) {
    return [];
  }

  const labels = {
    positioning: "定位路径",
    content: "内容路径",
    conversion: "转化路径"
  };

  return ["positioning", "content", "conversion"]
    .map(key => {
      const steps = splitPathSteps(strategy[key]);
      return {
        title: labels[key],
        steps,
        content: steps.join(" → ")
      };
    })
    .filter(item => item.steps.length || item.content);
}

function splitPathSteps(value) {
  if (Array.isArray(value)) {
    return value
      .map(item => {
        if (item && typeof item === "object") {
          return item.content || item.text || item.title || "";
        }
        return item;
      })
      .map(item => String(item || "").trim())
      .filter(Boolean);
  }

  const cleaned = String(value || "")
    .replace(/^(定位路径|内容路径|转化路径)[:：]\s*/, "")
    .trim();
  if (!cleaned) return [];

  const arrowParts = cleaned
    .replace(/→/g, "->")
    .split("->")
    .map(item => item.replace(/^(定位路径|内容路径|转化路径)[:：]\s*/, "").trim())
    .filter(Boolean);
  if (arrowParts.length > 1) return arrowParts;

  const punctuationParts = cleaned
    .split(/[，；。]/)
    .flatMap(item => {
      const trimmed = item.trim();
      if (trimmed.includes("、")) {
        return trimmed.split("、");
      }
      return [trimmed];
    })
    .map(item => item.trim())
    .filter(item => item.length >= 2);
  if (punctuationParts.length > 1) return punctuationParts;

  const listParts = cleaned
    .split("、")
    .map(item => item.trim())
    .filter(item => item.length >= 4);
  return listParts.length > 1 ? listParts : [cleaned];
}

function buildRiskCards(report) {
  if (!report || !Array.isArray(report.risk_cards)) {
    return [];
  }

  return report.risk_cards
    .map(item => ({
      title: item.title || "风险提醒",
      content: String(item.content || "").trim()
    }))
    .filter(item => item.content);
}

function normalizeActionPlan(actionPlan) {
  if (!Array.isArray(actionPlan)) return [];

  return actionPlan
    .map((item, index) => {
      const rawLabel = item && typeof item === "object" ? item.label || item.period || "" : "";
      const rawContent = item && typeof item === "object"
        ? item.content || item.text || item.action || ""
        : item;
      const content = String(rawContent || "")
        .replace(/^第\s*\d+\s*周\s*[:：]\s*/, "")
        .replace(/^第\s*\d+\s*[-~－—]\s*\d+\s*天\s*[:：]\s*/, "")
        .trim();
      return {
        key: `${index}-${content}`,
        label: ACTION_DAY_LABELS[index] || rawLabel || `第${index + 1}阶段`,
        content
      };
    })
    .filter(item => item.content);
}

Page({
  data: {
    assessmentId: null,
    report: null,
    structuredSections: [],
    dimensionRows: [],
    strategyItems: [],
    riskCards: [],
    actionSteps: [],
    loading: true,
    benefitMinutes: 45
  },

  onLoad(options) {
    const id = Number(options.assessment_id) || app.globalData.assessmentId || null;
    this.setData({ assessmentId: id });
    this.loadFullReport();
  },

  async loadFullReport() {
    const id = this.data.assessmentId;
    if (!id) {
      wx.showToast({ title: "参数错误", icon: "none" });
      this.setData({ loading: false });
      return;
    }

    const { data, error } = await get(`/api/reports/${id}/full`);

    if (error) {
      wx.showToast({ title: "加载报告失败", icon: "none" });
      this.setData({ loading: false });
      return;
    }

    this.setData({
      report: data,
      structuredSections: buildStructuredSections(data || {}),
      dimensionRows: normalizeDimensionRows(data && data.dimension_scores),
      strategyItems: buildStrategyItems(data || {}),
      riskCards: buildRiskCards(data || {}),
      actionSteps: normalizeActionPlan(data && data.action_plan_30days),
      loading: false
    });
  },

  onShareAppMessage() {
    const id = this.data.assessmentId;
    post("/api/share-records", {
      assessment_id: id,
      share_scene: "moment"
    }).catch(err => console.error("分享记录失败:", err));

    // 本地累加，确保文案实时更新
    const next = this.data.benefitMinutes + 10;
    this.setData({ benefitMinutes: next });

    return {
      title: "我的出海准备度评估报告",
      path: "/pages/index/index"
    };
  }
});
