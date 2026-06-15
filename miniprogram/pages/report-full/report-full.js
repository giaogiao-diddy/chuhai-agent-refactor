"use strict";

const app = getApp();
const { get, post } = require("../../utils/api");

Page({
  data: {
    assessmentId: null,
    report: null,
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