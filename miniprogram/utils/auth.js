"use strict";

/**
 * 登录 & Token 管理
 *
 * 流程：
 * 1. 调用 wx.login() 获取临时 code
 * 2. 将 code 发送到后端 /api/auth/wechat-login
 * 3. 后端返回 JWT token + user_id
 * 4. 将 token 持久化到 storage，后续请求自动携带
 */

const STORAGE_KEY_TOKEN = "auth_token";
const STORAGE_KEY_USER_ID = "auth_user_id";

/* ── 读写缓存 ────────────────────────────────── */

function getToken() {
  return wx.getStorageSync(STORAGE_KEY_TOKEN) || null;
}

function setToken(token) {
  wx.setStorageSync(STORAGE_KEY_TOKEN, token);
}

function getUserId() {
  const id = wx.getStorageSync(STORAGE_KEY_USER_ID);
  return id ? Number(id) : null;
}

function setUserId(id) {
  wx.setStorageSync(STORAGE_KEY_USER_ID, String(id));
}

function clearAuth() {
  wx.removeStorageSync(STORAGE_KEY_TOKEN);
  wx.removeStorageSync(STORAGE_KEY_USER_ID);
}

/* ── 登录 ────────────────────────────────────── */

/**
 * 微信登录 → 换后端 token
 * @returns {Promise<{token: string, user_id: number, openid: string, is_new: boolean}>}
 */
function login() {
  return new Promise((resolve, reject) => {
    wx.login({
      success(res) {
        if (!res.code) {
          reject(new Error("wx.login 未返回 code"));
          return;
        }

        wx.request({
          url: "http://127.0.0.1:8000/api/auth/wechat-login",
          method: "POST",
          header: { "Content-Type": "application/json" },
          data: { code: res.code },
          timeout: 15000,
          success(apiRes) {
            if (apiRes.statusCode === 200 && apiRes.data) {
              const { token, user_id } = apiRes.data;
              setToken(token);
              setUserId(user_id);
              resolve(apiRes.data);
            } else {
              const msg = (apiRes.data && apiRes.data.error) || "登录失败";
              reject(new Error(msg));
            }
          },
          fail(err) {
            reject(new Error("登录请求失败: " + err.errMsg));
          }
        });
      },
      fail(err) {
        reject(new Error("wx.login 失败: " + err.errMsg));
      }
    });
  });
}

module.exports = {
  getToken,
  setToken,
  getUserId,
  setUserId,
  clearAuth,
  login
};
