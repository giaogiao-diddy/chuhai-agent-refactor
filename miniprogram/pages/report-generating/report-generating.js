"use strict";

const app = getApp();
const { get } = require("../../utils/api");

// 轮询退避序列（秒）
const BACKOFF_SEQUENCE = [1.0, 1.5, 2.5, 4.0];
const MAX_POLL_STEPS = BACKOFF_SEQUENCE.length;

/* 按标签生成动态等待文案 */
const WAIT_MESSAGES = {
  "观察准备型": "正在分析您的行业定位与出海基础条件...",
  "轻量试探型": "正在评估您的产品匹配度与内容获客潜力...",
  "基础具备型": "正在深度分析您的转化体系与海外交付能力...",
  "优先布局型": "正在综合研判您的全球化扩张路径与风险边界..."
};
const FALLBACK_MESSAGE = "正在精细生成您的专属出海评估报告...";

Page({
  data: {
    assessmentId: null,
    score: 0,
    tag: "",
    elapsed: 0,
    maxWait: 20,
    showTimeoutHint: false,
    waitMessage: FALLBACK_MESSAGE
  },

  timer: null,
  pollStep: 0,

  onLoad(options) {
    const assessmentId = Number(options.assessment_id) || app.globalData.assessmentId || null;
    // 同步 globalData
    if (assessmentId) app.globalData.assessmentId = assessmentId;

    const tag = decodeURIComponent(options.tag || "");
    const message = WAIT_MESSAGES[tag] || FALLBACK_MESSAGE;

    this.setData({
      assessmentId: assessmentId,
      score: Number(options.score) || 0,
      tag: tag,
      waitMessage: message
    });

    this.startPolling();
  },

  onUnload() {
    this.stopPolling();
  },

  stopPolling() {
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
  },

  startPolling() {
    const id = this.data.assessmentId;
    if (!id) {
      wx.showToast({ title: "参数错误", icon: "none" });
      return;
    }
    this.pollStep = 0;
    this.doPoll();
  },

  doPoll() {
    if (this.pollStep >= MAX_POLL_STEPS) this.pollStep = MAX_POLL_STEPS - 1;
    const delay = BACKOFF_SEQUENCE[this.pollStep] * 1000;
    this.pollStep += 1;

    this.timer = setTimeout(async () => {
      const id = this.data.assessmentId;
      if (!id) {
        console.error("[Polling] assessmentId 丢失");
        return;
      }

      const elapsed = this.data.elapsed + Math.round(delay / 1000);
      this.setData({ elapsed });

      if (elapsed >= this.data.maxWait) {
        this.setData({ showTimeoutHint: true });
      }

      const { data, error } = await get(`/api/assessments/${id}/report-status`);

      if (error) {
        console.error("[Polling] 查询失败:", error);
        this.doPoll();
        return;
      }

      if (data.status === "success") {
        this.stopPolling();
        wx.redirectTo({
          url: `/pages/report-partial/report-partial?assessment_id=${id}&score=${this.data.score}&tag=${encodeURIComponent(this.data.tag)}`
        });
        return;
      }

      if (data.status === "failed") {
        this.stopPolling();
        wx.showToast({ title: "报告生成失败，请重试", icon: "none" });
        return;
      }

      // pending / generating → 继续
      this.doPoll();
    }, delay);
  }
});
