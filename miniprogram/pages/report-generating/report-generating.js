"use strict";

const app = getApp();
const { call } = require("../../utils/cloudApi");

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

  onLoad(options) {
    const assessmentId = options.assessment_id || app.globalData.assessmentId || null;
    if (assessmentId) app.globalData.assessmentId = assessmentId;

    const tag = decodeURIComponent(options.tag || "");
    this.setData({
      assessmentId,
      score: Number(options.score) || 0,
      tag,
      waitMessage: WAIT_MESSAGES[tag] || FALLBACK_MESSAGE
    });

    this.checkReportSoon();
  },

  onUnload() {
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
  },

  checkReportSoon() {
    this.timer = setTimeout(async () => {
      const id = this.data.assessmentId;
      if (!id) {
        wx.showToast({ title: "参数错误", icon: "none" });
        return;
      }

      const { data, error } = await call("getReportDetail", {
        assessment_id: id,
        full: false
      });

      if (error || !data || !data.ok) {
        this.setData({ showTimeoutHint: true });
        wx.showToast({ title: "报告暂未生成", icon: "none" });
        return;
      }

      wx.redirectTo({
        url: `/pages/report-partial/report-partial?assessment_id=${id}&score=${this.data.score}&tag=${encodeURIComponent(this.data.tag)}`
      });
    }, 1000);
  }
});
