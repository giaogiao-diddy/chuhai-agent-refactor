"use strict";

/**
 * 登录 & Token 管理
 *
 * 流程：
 * 1. 调用 wx.login() 获取临时 code
 * 2. 将 code 发送到后端 /api/auth/wechat-login
 * 3. 后端返回 JWT token + user_id
 * 4. 将 token 持久化到 storage，后续请求自动携带
 *
 * 开发模式：wx.login() 失败时自动用测试 code 登录
 * 后端 mock 模式接受任意非空 code，无需真实微信环境。
 */

const { BASE_URL } = require("./config");

const STORAGE_KEY_TOKEN = "auth_token";
const STORAGE_KEY_USER_ID = "auth_user_id";

// ═══════════════════════════════════════
// 开发模式 — wx.login 失败时用测试 code
// ═══════════════════════════════════════
const DEV_CODE = "dev_test_code_001";

function isLocalDevBackend() {
  return BASE_URL.includes("127.0.0.1") || BASE_URL.includes("localhost");
}

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

/* ── 内部：用 code 换后端 token ──────────────── */

function exchangeCodeForToken(code) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: BASE_URL + "/api/auth/wechat-login",
      method: "POST",
      header: { "Content-Type": "application/json" },
      data: { code: code },
      timeout: 10000,
      success(apiRes) {
        if (apiRes.statusCode === 200 && apiRes.data) {
          const { token, user_id } = apiRes.data;
          setToken(token);
          setUserId(user_id);
          resolve(apiRes.data);
        } else {
          const msg = (apiRes.data && apiRes.data.detail) || "登录失败";
          reject(new Error(msg));
        }
      },
      fail(err) {
        reject(new Error("登录请求失败: " + err.errMsg));
      }
    });
  });
}

/* ── 登录 ────────────────────────────────────── */

/**
 * 微信登录 → 换后端 token
 * 如果 wx.login() 失败（开发工具常见问题），fallback 到测试 code
 */
function login() {
  if (isLocalDevBackend()) {
    return exchangeCodeForToken(DEV_CODE);
  }

  return new Promise((resolve) => {
    let resolved = false;

    function doLogin(code) {
      if (resolved) return;
      resolved = true;
      exchangeCodeForToken(code).then(resolve);
    }

    // 先尝试真实 wx.login
    wx.login({
      success(res) {
        if (res.code) {
          exchangeCodeForToken(res.code)
            .then((result) => { if (!resolved) { resolved = true; resolve(result); } })
            .catch(() => {
              console.warn("[Auth] wx.request 失败，使用开发模式 code");
              doLogin(DEV_CODE);
            });
        } else {
          console.warn("[Auth] wx.login 未返回 code，使用开发模式");
          doLogin(DEV_CODE);
        }
      },
      fail(err) {
        console.warn("[Auth] wx.login 失败: " + err.errMsg + "，使用开发模式");
        doLogin(DEV_CODE);
      }
    });

    // 超时保护：2 秒后 wx.login 还没回调 → 用 dev code
    setTimeout(() => {
      if (!resolved) {
        console.warn("[Auth] wx.login 超时，使用开发模式 code");
        doLogin(DEV_CODE);
      }
    }, 2000);
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
