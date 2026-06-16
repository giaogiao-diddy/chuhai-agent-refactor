"use strict";

const { get } = require("../../utils/api");

function normalizeReport(item) {
  const s = item.summary || {};
  return {
    ...item,
    displayTime: item.completed_at || "",
    brief: s.preliminary_judgment || s.tag_explanation || "查看本次出海测评报告详情"
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
    const { data, error } = await get("/api/reports/my/list");

    if (error) {
      wx.showToast({ title: "加载失败", icon: "none" });
      this.setData({ loading: false, empty: true });
      return;
    }

    const reports = Array.isArray(data) ? data.map(normalizeReport) : [];
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
        url: `/pages/report-full/report-full?assessment_id=${assessmentId}`
      });
      return;
    }

    this.setData({ checkingReport: true });
    wx.showLoading({ title: "检查报告状态..." });

    const { data, error } = await get(`/api/reports/${assessmentId}/full`);

    wx.hideLoading();
    this.setData({ checkingReport: false });

    if (data && !error) {
      wx.navigateTo({
        url: `/pages/report-full/report-full?assessment_id=${assessmentId}`
      });
      return;
    }

    wx.navigateTo({
      url: `/pages/report-partial/report-partial?assessment_id=${assessmentId}&score=${report.display_score || report.total_score || 0}&tag=${encodeURIComponent(report.tag || "")}`
    });
  }
});
