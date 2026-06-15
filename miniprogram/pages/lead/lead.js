"use strict";

const app = getApp();
const { post } = require("../../utils/api");

Page({
  data: {
    name: "",
    contact: "",
    company: "",
    role: "",
    submitting: false
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
    if (!company.trim()) {
      wx.showToast({ title: "请填写公司名称", icon: "none" });
      return;
    }
    if (!role.trim()) {
      wx.showToast({ title: "请填写您的身份", icon: "none" });
      return;
    }

    this.setData({ submitting: true });

    const assessmentId = app.globalData.assessmentId;

    const { data, error } = await post("/api/leads", {
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

    // 跳转完整报告
    wx.redirectTo({ url: "/pages/report-full/report-full" });
  }
});
