"use strict";

const app = getApp();
const { call } = require("../../utils/cloudApi");

Page({
  data: {
    loading: true,
    submitting: false
  },

  onLoad() {
    this.setData({ loading: false });
  },

  async startAssessment() {
    this.setData({ submitting: true });
    wx.showLoading({ title: "准备中", mask: true });

    const { data, error } = await call("createAssessment");

    wx.hideLoading();
    this.setData({ submitting: false });

    if (error) {
      wx.showToast({ title: error, icon: "none" });
      return;
    }

    app.globalData.assessmentId = data.assessment_id;
    wx.navigateTo({ url: "/pages/assessment/assessment" });
  },

  goToMyReport() {
    wx.navigateTo({ url: "/pages/my-report/my-report" });
  }
});
