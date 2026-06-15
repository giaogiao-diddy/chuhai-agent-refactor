"use strict";

const app = getApp();
const { get } = require("../../utils/api");

Page({
  data: {
    score: 0,
    tag: "",
    elapsed: 0,
    showTimeoutHint: false
  },

  timer: null,
  maxWait: 20,  // 20 秒后提示用户

  onLoad(options) {
    this.setData({
      score: Number(options.score) || 0,
      tag: decodeURIComponent(options.tag || "")
    });

    this.startPolling();
  },

  onUnload() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  },

  startPolling() {
    const assessmentId = app.globalData.assessmentId;

    if (!assessmentId) {
      wx.showToast({ title: "参数错误", icon: "none" });
      return;
    }

    this.timer = setInterval(async () => {
      const elapsed = this.data.elapsed + 1;
      this.setData({ elapsed });

      // 超时提示
      if (elapsed >= this.maxWait) {
        this.setData({ showTimeoutHint: true });
      }

      const { data, error } = await get(
        `/api/assessments/${assessmentId}/report-status`
      );

      if (error) {
        console.error("[Polling] 查询失败:", error);
        return;
      }

      if (data.status === "success") {
        clearInterval(this.timer);
        this.timer = null;

        wx.redirectTo({
          url: `/pages/report-partial/report-partial?assessment_id=${assessmentId}&score=${this.data.score}&tag=${encodeURIComponent(this.data.tag)}`
        });
      } else if (data.status === "failed") {
        clearInterval(this.timer);
        this.timer = null;
        wx.showToast({ title: "报告生成失败，请重试", icon: "none" });
      }
      // status === "generating" 或 "pending" 时继续轮询
    }, 1500);
  }
});
