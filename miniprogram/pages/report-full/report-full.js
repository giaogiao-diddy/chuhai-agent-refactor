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

function clampPercent(value) {
  const n = Number(value) || 0;
  return Math.max(0, Math.min(100, n));
}

function parsePercentText(value) {
  if (typeof value === "string") {
    const m = value.match(/\d+(\.\d+)?/);
    if (m) return clampPercent(Number(m[0]));
  }
  return null;
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
    const parsed = isObj ? parsePercentText(value.percentage || value.percent) : null;
    const percent = parsed !== null
      ? parsed
      : clampPercent(maxScore > 0 ? (score / maxScore) * 100 : score);
    const scoreText = maxScore && maxScore !== 100 ? `${score}/${maxScore}` : `${score}`;

    return {
      key,
      name: DIMENSION_LABELS[key] || (isObj && value.label) || key,
      score,
      maxScore,
      scoreText,
      percent,
      percentText: `${Math.round(percent)}%`,
      comment: isObj ? (value.comment || value.level || value.description || "") : ""
    };
  });
}

/**
 * V3 结构化字段 → 渲染 sections
 *
 * 后端 full_report.{positioning_assessment, content_assessment, conversion_assessment}
 * 是三个独立的结构化文本块，直接展示，不做断句/关键词匹配。
 */
function buildStructuredSections(report) {
  if (!report) return [];

  const mapping = [
    { key: "positioning_assessment", label: "定位评估" },
    { key: "content_assessment", label: "内容矩阵评估" },
    { key: "conversion_assessment", label: "转化与合规评估" }
  ];

  const sections = mapping
    .map(m => ({ title: m.label, content: (report[m.key] || "").trim() }))
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

Page({
  data: {
    assessmentId: null,
    report: null,
    structuredSections: [],
    dimensionRows: [],
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
