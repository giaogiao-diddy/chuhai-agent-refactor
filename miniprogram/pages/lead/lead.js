"use strict";

const app = getApp();
const { call } = require("../../utils/cloudApi");

Page({
  data: {
    assessmentId: null,
    loading: true,
    isUnlocked: false,
    qrCodeUrl: "",
    consultantName: "企微顾问",
    pollingInterval: 2000,
    message: "",
    enableMockUnlock: false,
    mockUnlocking: false
  },

  timer: null,

  onLoad(options) {
    const assessmentId = options.assessment_id || app.globalData.assessmentId || null;
    this.setData({ assessmentId: assessmentId });
    this.loadUnlockSession();
  },

  onUnload() {
    this.stopPolling();
  },

  onHide() {
    this.stopPolling();
  },

  /** 加载解锁会话 */
  async loadUnlockSession() {
    const { assessmentId } = this.data;
    if (!assessmentId) {
      wx.showToast({ title: "参数错误", icon: "none" });
      this.setData({ loading: false });
      return;
    }

    const { data, error } = await call("createWecomUnlockSession", {
      assessment_id: assessmentId
    });

    if (error) {
      wx.showToast({ title: "加载失败: " + error, icon: "none" });
      this.setData({ loading: false });
      return;
    }

    // 如果已经解锁，直接跳完整报告
    if (data.is_unlocked) {
      this.setData({ loading: false, isUnlocked: true, message: data.message });
      this.goToFullReport();
      return;
    }

    this.setData({
      loading: false,
      isUnlocked: false,
      qrCodeUrl: data.qr_code_url || "",
      consultantName: data.consultant_name || "企微顾问",
      pollingInterval: (data.polling_interval || 2.0) * 1000,
      message: data.message,
      enableMockUnlock: data.enable_mock_unlock || false
    });

    this.startPolling();
  },

  /** 开始轮询解锁状态 */
  startPolling() {
    this.stopPolling();
    this.timer = setInterval(() => {
      this.checkUnlockStatus();
    }, this.data.pollingInterval);
  },

  stopPolling() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  },

  /** 查询解锁状态 */
  async checkUnlockStatus() {
    const { assessmentId, isUnlocked } = this.data;
    if (isUnlocked || !assessmentId) return;

    const { data, error } = await call("getWecomUnlockStatus", {
      assessment_id: assessmentId
    });

    if (error || !data) return;

    if (data.is_unlocked) {
      this.stopPolling();
      this.setData({ isUnlocked: true, message: "添加成功！正在解锁报告..." });
      setTimeout(() => {
        this.goToFullReport();
      }, 800);
    }
  },

  /** 手动检查（按钮触发） */
  async onCheckStatus() {
    wx.showLoading({ title: "检查中" });
    await this.checkUnlockStatus();
    wx.hideLoading();

    if (!this.data.isUnlocked) {
      wx.showToast({ title: "暂未检测到添加，请确认已添加后再试", icon: "none" });
    }
  },

  /** 开发模拟解锁 */
  async onMockUnlock() {
    const { assessmentId, mockUnlocking } = this.data;
    if (mockUnlocking || !assessmentId) return;

    this.setData({ mockUnlocking: true });

    const { data, error } = await call("mockUnlock", {
      assessment_id: assessmentId
    });

    this.setData({ mockUnlocking: false });

    if (error) {
      wx.showToast({ title: "模拟解锁失败: " + error, icon: "none" });
      return;
    }

    this.stopPolling();
    this.setData({ isUnlocked: true, message: "解锁成功！正在进入完整报告..." });
    setTimeout(() => {
      this.goToFullReport();
    }, 800);
  },

  /** 跳转完整报告 */
  goToFullReport() {
    wx.redirectTo({
      url: `/pages/report-full/report-full?assessment_id=${this.data.assessmentId}`
    });
  },

  /** 返回部分报告 */
  goBack() {
    wx.navigateBack();
  }
});
