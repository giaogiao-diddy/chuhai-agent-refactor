"use strict";

function call(name, data) {
  return wx.cloud.callFunction({
    name,
    data: data || {}
  }).then((res) => {
    const result = res.result || {};
    // 新格式 { success:false, errorCode, errorMessage }
    if (result.success === false || result.ok === false) {
      return {
        data: null,
        error: result.errorMessage || result.error || "云函数调用失败"
      };
    }
    // 新格式 { success:true, data:{...} } → 解包里层 data
    // 旧格式 { ok:true, ... } → 原样返回
    return {
      data: result.data || result,
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
