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

const SUMMARY_FIELD_LABELS = {
  current_stage: "当前阶段",
  stage: "当前阶段",
  profile: "用户画像",
  user_profile: "用户画像",
  key_gaps: "关键短板",
  gaps: "关键短板",
  core_strategy: "核心策略",
  strategy: "核心策略",
  next_step: "下一步重点"
};

function clampPercent(value) {
  const number = Number(value) || 0;
  return Math.max(0, Math.min(100, number));
}

function parsePercentText(value) {
  if (typeof value === "string") {
    const matched = value.match(/\d+(\.\d+)?/);
    if (matched) {
      return clampPercent(Number(matched[0]));
    }
  }
  return null;
}

function splitSentences(text) {
  return String(text || "")
    .replace(/\s+/g, "")
    .replace(/核心策略[:：]/g, "。核心策略：")
    .replace(/[。！？；]/g, "$&|")
    .split("|")
    .map(item => item.trim())
    .filter(Boolean);
}

function pickSentence(sentences, keywords, fallbackIndex) {
  for (let i = 0; i < sentences.length; i += 1) {
    const sentence = sentences[i];
    for (let j = 0; j < keywords.length; j += 1) {
      if (sentence.indexOf(keywords[j]) !== -1) {
        return sentence;
      }
    }
  }
  return sentences[fallbackIndex] || "";
}

function normalizeSummaryItems(report) {
  const source = report.summary_sections || report.summary_conclusion || "";

  if (source && typeof source === "object" && !Array.isArray(source)) {
    return Object.keys(source)
      .map(key => ({
        title: SUMMARY_FIELD_LABELS[key] || key,
        content: String(source[key] || "").trim()
      }))
      .filter(item => item.content);
  }

  const sentences = splitSentences(source);
  if (!sentences.length) {
    return [];
  }

  const items = [
    {
      title: "用户画像",
      content: sentences[0]
    },
    {
      title: "当前阶段",
      content: pickSentence(sentences, ["阶段", "标签", "类型"], 1)
    },
    {
      title: "关键短板",
      content: pickSentence(sentences, ["短板", "缺失", "薄弱", "不足", "模糊", "依赖"], 2)
    },
    {
      title: "核心策略",
      content: pickSentence(sentences, ["核心策略", "策略", "建议", "重点"], sentences.length - 1)
    }
  ];

  const seen = {};
  return items.filter(item => {
    const content = String(item.content || "").trim();
    if (!content || seen[content]) {
      return false;
    }
    seen[content] = true;
    item.content = content.replace(/^核心策略[:：]/, "");
    return true;
  });
}

function normalizeDimensionRows(dimensionScores) {
  if (!dimensionScores) {
    return [];
  }

  const entries = Array.isArray(dimensionScores)
    ? dimensionScores.map((item, index) => [item.key || item.name || String(index), item])
    : Object.keys(dimensionScores).map(key => [key, dimensionScores[key]]);

  return entries.map(([key, value]) => {
    const isObject = value && typeof value === "object" && !Array.isArray(value);
    const score = isObject ? Number(value.score || value.value || 0) : Number(value || 0);
    const maxScore = isObject ? Number(value.max_score || value.maxScore || 100) : 100;
    const parsedPercent = isObject ? parsePercentText(value.percentage || value.percent) : null;
    const percent = parsedPercent !== null
      ? parsedPercent
      : clampPercent(maxScore > 0 ? score / maxScore * 100 : score);
    const scoreText = maxScore && maxScore !== 100 ? `${score}/${maxScore}` : `${score}`;

    return {
      key: key,
      name: DIMENSION_LABELS[key] || (isObject && value.label) || key,
      score: score,
      maxScore: maxScore,
      scoreText: scoreText,
      percent: percent,
      percentText: `${Math.round(percent)}%`,
      comment: isObject ? (value.comment || value.level || value.description || "") : ""
    };
  });
}

Page({
  data: {
    assessmentId: null,
    report: null,
    summaryItems: [],
    dimensionRows: [],
    loading: true,
    benefitMinutes: 45
  },

  onLoad(options) {
    const assessmentId = Number(options.assessment_id) || app.globalData.assessmentId || null;
    this.setData({ assessmentId: assessmentId });
    this.loadFullReport();
  },

  async loadFullReport() {
    const assessmentId = this.data.assessmentId;

    if (!assessmentId) {
      wx.showToast({ title: "参数错误", icon: "none" });
      this.setData({ loading: false });
      return;
    }

    const { data, error } = await get(`/api/reports/${assessmentId}/full`);

    if (error) {
      wx.showToast({ title: "加载报告失败", icon: "none" });
      this.setData({ loading: false });
      return;
    }

    this.setData({
      report: data,
      summaryItems: normalizeSummaryItems(data || {}),
      dimensionRows: normalizeDimensionRows(data && data.dimension_scores),
      loading: false
    });
  },

  /** 转发 — 升级权益 */
  onShareAppMessage() {
    const assessmentId = this.data.assessmentId;
    post("/api/share-records", {
      assessment_id: assessmentId,
      share_scene: "moment"
    }).catch(err => console.error("分享记录失败:", err));

    this.setData({
      benefitMinutes: this.data.benefitMinutes + 10
    });

    return {
      title: "我的出海准备度评估报告",
      path: `/pages/index/index`
    };
  }
});
