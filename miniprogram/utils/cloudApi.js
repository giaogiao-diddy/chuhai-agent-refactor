"use strict";

function call(name, data) {
  return wx.cloud.callFunction({
    name,
    data: data || {}
  }).then((res) => {
    const result = res.result || {};
    if (result.ok === false) {
      return {
        data: result,
        error: result.error || "云函数调用失败"
      };
    }
    return {
      data: result,
      error: null
    };
  }).catch((err) => {
    console.error("[CloudAPI] 调用失败:", name, err);
    return {
      data: null,
      error: err.errMsg || err.message || "云函数调用失败"
    };
  });
}

module.exports = {
  call
};
