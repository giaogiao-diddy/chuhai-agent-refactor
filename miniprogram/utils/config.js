"use strict";

/**
 * 全局配置 — 所有模块从这里读 BASE_URL
 *
 * 开发者工具中的 127.0.0.1 指向电脑本机；手机预览中的 127.0.0.1 指向手机本机。
 * 因此手机预览需要使用电脑在同一 WiFi 下的局域网 IP。
 */

const DEVTOOLS_BASE_URL = "http://127.0.0.1:8000";
const DEVICE_PREVIEW_BASE_URL = "http://192.168.10.112:8000";
const PROD_BASE_URL = "";
const USE_MOCK_LOGIN = false;

function getPlatform() {
  try {
    const info = wx.getSystemInfoSync();
    return info && info.platform ? info.platform : "";
  } catch (err) {
    return "";
  }
}

function resolveBaseUrl() {
  const platform = getPlatform();

  if (PROD_BASE_URL) {
    return PROD_BASE_URL;
  }

  if (platform === "devtools") {
    return DEVTOOLS_BASE_URL;
  }

  return DEVICE_PREVIEW_BASE_URL;
}

const BASE_URL = resolveBaseUrl();

module.exports = {
  BASE_URL,
  DEVTOOLS_BASE_URL,
  DEVICE_PREVIEW_BASE_URL,
  PROD_BASE_URL,
  USE_MOCK_LOGIN
};
