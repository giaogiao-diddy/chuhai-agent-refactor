"use strict";

const app = getApp();
const { get, post } = require("../../utils/api");

Page({
  data: {
    report: null,
    loading: true,
    benefitMinutes: 45
  },

  async onLoad() {
    await this.loadFullReport();
  },

  async loadFullReport() {
    const assessmentId = app.globalData.assessmentId;

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
    // 先记录转发到后端
    const assessmentId = app.globalData.assessmentId;
    post("/api/share-records", {
      assessment_id: assessmentId,
      share_scene: "moment"
    }).catch(err => console.error("分享记录失败:", err));

    // 本地更新权益
    this.setData({
      benefitMinutes: this.data.benefitMinutes + 10
    });

    return {
      title: "我的出海准备度评估报告",
      path: `/pages/index/index`
    };
  }
});
