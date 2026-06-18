const { db } = require("./shared/db");
const { normalizeSystemConfig } = require("./shared/systemConfig");
const { success } = require("./shared/response");

exports.main = async () => {
  try {
    const result = await db.collection("system_config").doc("global_config").get();
    return success({
      config: normalizeSystemConfig(result.data),
    });
  } catch (err) {
    console.warn("getSystemConfig 使用默认配置兜底:", err && err.message ? err.message : err);
    return success({
      config: normalizeSystemConfig(null),
    });
  }
};
