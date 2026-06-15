"use strict";

/**
 * 罗宾出海分析 Agent — 小程序入口
 *
 * 全局职责：
 * 1. 检测登录态 — 首次进入调用 wx.login 换后端 token
 * 2. 将 token / user_id 存入 storage，后续请求统一携带
 * 3. 暴露 app.globalData 供页面共享状态
 */

const { login, getToken, getUserId } = require("./utils/auth");

App({
  globalData: {
    token: null,       // JWT token，登录后写入
    userId: null,      // 后端 user_id
    openid: null,      // 微信 openid（仅用于调试）
    assessmentId: null // 当前测评 ID，页面间传递
  },

  async onLaunch() {
    // 尝试从缓存恢复登录态
    const cachedToken = getToken();
    const cachedUserId = getUserId();

    if (cachedToken && cachedUserId) {
      this.globalData.token = cachedToken;
      this.globalData.userId = cachedUserId;
      console.log("[App] 从缓存恢复登录态, userId:", cachedUserId);
      return;
    }

    // 首次登录：调微信登录 → 换后端 token
    try {
      const result = await login();
      this.globalData.token = result.token;
      this.globalData.userId = result.user_id;
      this.globalData.openid = result.openid;
      console.log("[App] 登录成功, userId:", result.user_id);
    } catch (err) {
      console.error("[App] 登录失败:", err);
      // 不阻断用户进入，后续需要登录的接口会再次尝试
    }
  }
});
