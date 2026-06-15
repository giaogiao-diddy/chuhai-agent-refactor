"use strict";

/**
 * 后端 API 封装
 *
 * - 所有请求统一走此模块
 * - 自动注入 JWT token
 * - 统一错误处理，返回 { data, error } 结构
 */

const { getToken } = require("./auth");

// ═══════════════════════════════════════════════
// 环境切换 — 联调时改这里
// ═══════════════════════════════════════════════
const BASE_URL = "http://127.0.0.1:8000";

/**
 * 通用请求方法
 * @param {string} path    — API 路径（如 /api/questions）
 * @param {string} method  — HTTP 方法
 * @param {object} [data]  — 请求体（POST/PUT 时）
 * @returns {Promise<{data: any, error: string|null}>}
 */
function request(path, method, data) {
  return new Promise((resolve) => {
    const token = getToken();
    const header = {
      "Content-Type": "application/json"
    };

    if (token) {
      header["Authorization"] = `Bearer ${token}`;
    }

    wx.request({
      url: BASE_URL + path,
      method: method,
      header: header,
      data: data,
      timeout: 30000,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve({ data: res.data, error: null });
        } else {
          const msg = (res.data && res.data.error) || `请求失败 (${res.statusCode})`;
          resolve({ data: null, error: msg });
        }
      },
      fail(err) {
        console.error("[API] 网络错误:", err);
        resolve({ data: null, error: "网络连接失败，请检查网络" });
      }
    });
  });
}

/* ── 对外方法 ────────────────────────────────── */

/** GET 请求 */
function get(path) {
  return request(path, "GET");
}

/** POST 请求 */
function post(path, data) {
  return request(path, "POST", data);
}

module.exports = {
  BASE_URL,
  get,
  post
};
