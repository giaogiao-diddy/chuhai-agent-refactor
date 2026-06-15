"use strict";

const app = getApp();
const { get } = require("../../utils/api");

Page({
  data: {
    assessmentId: null,
    score: 0,
    tag: "",
    report: null,
    loading: true
  },

  async onLoad(options) {
    const assessmentId = Number(options.assessment_id) || app.globalData.assessmentId || null;

    this.setData({
      assessmentId: assessmentId,
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

  /** 跳转留资页 — 显式传 assessment_id */
  goToLead() {
    const id = this.data.assessmentId;
    wx.navigateTo({ url: `/pages/lead/lead?assessment_id=${id}` });
  }
});