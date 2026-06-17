"use strict";

const app = getApp();
const { call } = require("../../utils/cloudApi");

Page({
  data: {
    assessmentId: null,
    reportId: null,
    score: 0,
    tag: "",
    report: null,
    loading: true
  },

  async onLoad(options) {
    const assessmentId = options.assessment_id || app.globalData.assessmentId || null;

    this.setData({
      assessmentId: assessmentId,
      reportId: options.report_id || null,
      score: Number(options.score) || 0,
      tag: decodeURIComponent(options.tag || "")
    });

    await this.loadSummary();
  },

  async loadSummary() {
    const assessmentId = this.data.assessmentId;

    if (!assessmentId) {
      wx.showToast({ title: "参数错误", icon: "none" });
      this.setData({ loading: false });
      return;
    }

    const { data, error } = await call("getReportDetail", {
      assessment_id: assessmentId,
      report_id: this.data.reportId || undefined,
      full: false
    });

    if (error) {
      wx.showToast({ title: "加载报告失败", icon: "none" });
      this.setData({ loading: false });
      return;
    }

    const report = data.report || data;
    const hero = report.hero || {};
    const summary = report.summary_report || {};

    this.setData({
      report: {
        ...summary,
        display_score: hero.score || this.data.score,
        total_score: hero.score || this.data.score,
        tag: hero.tag || this.data.tag,
        tag_explanation: hero.one_sentence_judgment || summary.industry_market || "",
        preliminary_judgment: summary.preliminary_judgment || hero.core_contradiction || ""
      },
      loading: false
    });
  },

  /** 跳转留资页 — 显式传 assessment_id */
  goToLead() {
    const id = this.data.assessmentId;
    wx.navigateTo({ url: `/pages/lead/lead?assessment_id=${id}` });
  }
});
