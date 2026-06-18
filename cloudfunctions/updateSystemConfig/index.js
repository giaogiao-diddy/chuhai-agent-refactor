const { db, _, getContext, now } = require("./shared/db");
const { isAdminOpenid } = require("./shared/auth");
const { validateSystemConfigPatch } = require("./shared/systemConfig");
const { fail, fromError, success } = require("./shared/response");

exports.main = async (event) => {
  const { OPENID } = getContext();

  if (!OPENID) {
    return fail("UNAUTHORIZED", "未获取到用户身份，请重新进入小程序");
  }
  if (!isAdminOpenid(OPENID)) {
    return fail("FORBIDDEN", "无权限更新系统配置");
  }

  try {
    const patch = validateSystemConfigPatch(event && event.config);
    const updateData = { updated_at: now() };
    Object.keys(patch).forEach((key) => {
      updateData[key] = _.set(patch[key]);
    });

    const updated = await db.collection("system_config").doc("global_config").update({
      data: updateData,
    });

    if (!updated.stats || updated.stats.updated === 0) {
      await db.collection("system_config").doc("global_config").set({
        data: {
          _id: "global_config",
          ...patch,
          updated_at: now(),
        },
      });
    }

    return success({
      updated: true,
      updatedFields: Object.keys(patch),
    });
  } catch (err) {
    console.error("updateSystemConfig 失败:", err);
    return fromError(err, "INVALID_PARAMS", "更新系统配置失败");
  }
};
