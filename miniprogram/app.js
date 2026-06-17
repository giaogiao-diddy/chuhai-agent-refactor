"use strict";

/**
 * 罗宾出海分析 Agent — 小程序入口
 *
 * 全局职责：
 * 1. 初始化 CloudBase 云开发环境
 * 2. 使用云函数天然注入的 OPENID 识别用户
 * 3. 暴露 app.globalData 供页面共享状态
 */

const CLOUDBASE_ENV_ID = "cloud1-d8gh82s3a39eff92d";

App({
  globalData: {
    cloudReady: false,
    envId: CLOUDBASE_ENV_ID,
    assessmentId: null // 当前测评 ID，页面间传递
  },

  onLaunch() {
    if (!wx.cloud) {
      console.error("[App] 当前基础库不支持 wx.cloud，请升级微信开发者工具和基础库");
      return;
    }

    wx.cloud.init({
      env: CLOUDBASE_ENV_ID,
      traceUser: true
    });
    this.globalData.cloudReady = true;
    console.log("[App] CloudBase 初始化完成:", CLOUDBASE_ENV_ID);
  }
});
