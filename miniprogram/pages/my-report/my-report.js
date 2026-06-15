"use strict";

const { get } = require("../../utils/api");

Page({
  data: {
    report: null,
    loading: true,
    empty: false
  },

  async onLoad() {
    await this.loadMyReport();
  },

  async loadMyReport() {
    const { data, error } = await get("/api/reports/my");

    if (error) {
      wx.showToast({ title: "加载失败", icon: "none" });
      this.setData({ loading: false, empty: true });
      return;
    }

    if (!data || !data.total_score) {
      this.setData({ loading: false, empty: true });
      return;
    }

    this.setData({
      report: data,
      loading: false
    });
  },

  /** 跳转部分报告页查看详情 */
  goToReport() {
    const assessmentId = this.data.report.assessment_id;
    if (!assessmentId) return;

    const app = getApp();
    app.globalData.assessmentId = assessmentId;

    wx.navigateTo({
      url: `/pages/report-partial/report-partial?score=${this.data.report.total_score || 0}&tag=${encodeURIComponent(this.data.report.tag || "")}`
    });
  }
});
