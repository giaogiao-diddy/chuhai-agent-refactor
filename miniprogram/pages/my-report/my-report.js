"use strict";

const { call } = require("../../utils/cloudApi");

function normalizeReport(item) {
  const report = item.report_json || {};
  const summary = report.summary_report || {};
  const hero = report.hero || {};
  return {
    ...item,
    displayTime: item.created_at || "",
    display_score: hero.score || 0,
    tag: hero.tag || "",
    brief: summary.preliminary_judgment || hero.one_sentence_judgment || "查看本次出海测评报告详情"
  };
}

Page({
  data: {
    report: null,
    reports: [],
    loading: true,
    empty: false,
    checkingReport: false
  },

  async onLoad() {
    await this.loadMyReport();
  },

  async loadMyReport() {
    const { data, error } = await call("getReportList");

    if (error) {
      wx.showToast({ title: "加载失败", icon: "none" });
      this.setData({ loading: false, empty: true });
      return;
    }

    const reports = data && Array.isArray(data.reports) ? data.reports.map(normalizeReport) : [];
    if (!reports.length) {
      this.setData({ loading: false, empty: true });
      return;
    }

    this.setData({
      report: reports[0],
      reports: reports,
      loading: false
    });
  },

  async goToReport(e) {
    const index = Number(e.currentTarget.dataset.index) || 0;
    const report = this.data.reports[index];
    const assessmentId = report && report.assessment_id;
    if (!assessmentId || this.data.checkingReport) return;

    const app = getApp();
    app.globalData.assessmentId = assessmentId;

    if (report.is_unlocked) {
      wx.navigateTo({
        url: `/pages/report-full/report-full?assessment_id=${assessmentId}&report_id=${report._id || ""}`
      });
      return;
    }

    wx.navigateTo({
      url: `/pages/report-partial/report-partial?assessment_id=${assessmentId}&report_id=${report._id || ""}&score=${report.display_score || 0}&tag=${encodeURIComponent(report.tag || "")}`
    });
  }
});
