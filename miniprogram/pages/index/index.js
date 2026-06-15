"use strict";

const app = getApp();
const { login } = require("../../utils/auth");
const { post } = require("../../utils/api");

Page({
  data: {
    loading: true,
    loggedIn: false,
    submitting: false
  },

  async onLoad() {
    // 检查登录态
    if (app.globalData.token) {
      this.setData({ loading: false, loggedIn: true });
    } else {
      // 尝试登录
      try {
        const result = await login();
        app.globalData.token = result.token;
        app.globalData.userId = result.user_id;
        app.globalData.openid = result.openid;
        this.setData({ loading: false, loggedIn: true });
      } catch (err) {
        console.error("[Index] 登录失败:", err);
        this.setData({ loading: false, loggedIn: false });
        wx.showToast({ title: "登录失败，请重试", icon: "none" });
      }
    }
  },

  /** 点击"开始测评" — 创建测评并跳转 */
  async startAssessment() {
    if (!app.globalData.token) {
      try {
        const result = await login();
        app.globalData.token = result.token;
        app.globalData.userId = result.user_id;
        app.globalData.openid = result.openid;
        this.setData({ loggedIn: true });
      } catch (err) {
        wx.showToast({ title: "登录失败，请重试", icon: "none" });
        return;
      }
    }

    this.setData({ submitting: true });
    wx.showLoading({ title: "准备中", mask: true });

    const { data, error } = await post("/api/assessments", {});

    wx.hideLoading();
    this.setData({ submitting: false });

    if (error) {
      wx.showToast({ title: error, icon: "none" });
      return;
    }

    app.globalData.assessmentId = data.id;
    wx.navigateTo({ url: "/pages/assessment/assessment" });
  },

  /** 跳转"我的报告" */
  goToMyReport() {
    if (!app.globalData.token) {
      wx.showToast({ title: "请先登录", icon: "none" });
      return;
    }
    wx.navigateTo({ url: "/pages/my-report/my-report" });
  }
});
