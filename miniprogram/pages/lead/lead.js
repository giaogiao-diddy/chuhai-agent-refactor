"use strict";

const app = getApp();
const { post } = require("../../utils/api");

Page({
  data: {
    assessmentId: null,
    name: "",
    contact: "",
    company: "",
    role: "",
    submitting: false
  },

  onLoad(options) {
    const assessmentId = Number(options.assessment_id) || app.globalData.assessmentId || null;
    this.setData({ assessmentId: assessmentId });
  },

  /** 表单字段双向绑定 */
  onInput(e) {
    const field = e.currentTarget.dataset.field;
    this.setData({ [field]: e.detail.value });
  },

  /** 提交留资 */
  async submitLead() {
    const { name, contact, company, role } = this.data;

    // 前端校验
    if (!name.trim()) {
      wx.showToast({ title: "请填写姓名", icon: "none" });
      return;
    }
    if (!contact.trim()) {
      wx.showToast({ title: "请填写电话/微信", icon: "none" });
      return;
    }
    if (contact.trim().length < 2) {
      wx.showToast({ title: "联系方式至少 2 个字符", icon: "none" });
      return;
    }
    if (!company.trim()) {
      wx.showToast({ title: "请填写公司名称", icon: "none" });
      return;
    }
    if (!role.trim()) {
      wx.showToast({ title: "请填写您的身份", icon: "none" });
      return;
    }

    this.setData({ submitting: true });

    const assessmentId = this.data.assessmentId;

    const { data, error } = await post("/api/leads", {
      assessment_id: assessmentId,
      name: name.trim(),
      contact: contact.trim(),
      company: company.trim(),
      role: role.trim()
    });

    this.setData({ submitting: false });

    if (error) {
      wx.showToast({ title: "提交失败: " + error, icon: "none" });
      return;
    }

    // 跳转完整报告 — 显式传 assessment_id
    wx.redirectTo({ url: `/pages/report-full/report-full?assessment_id=${this.data.assessmentId}` });
  }
});
