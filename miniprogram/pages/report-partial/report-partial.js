"use strict";

const app = getApp();
const { get } = require("../../utils/api");

Page({
  data: {
    score: 0,
    tag: "",
    report: null,
    loading: true
  },

  async onLoad(options) {
    this.setData({
      score: Number(options.score) || 0,
      tag: decodeURIComponent(options.tag || "")
    });

    await this.loadSummary();
  },

  async loadSummary() {
    const assessmentId = app.globalData.assessmentId;

    const { data, error } = await get(`/api/reports/${assessmentId}/summary`);

    if (error) {
      wx.showToast({ title: "加载报告失败", icon: "none" });
      this.setData({ loading: false });
      return;
    }

    this.setData({
      report: data,
      loading: false
    });
  },

  /** 跳转留资页 */
  goToLead() {
    wx.navigateTo({ url: "/pages/lead/lead" });
  }
});
