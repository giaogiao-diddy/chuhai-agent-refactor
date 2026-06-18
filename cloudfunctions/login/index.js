const { db, getContext, now } = require("./shared/db");
const { fail, fromError, success } = require("./shared/response");

exports.main = async () => {
  const { OPENID, UNIONID } = getContext();

  if (!OPENID) {
    return fail("UNAUTHORIZED", "未获取到用户身份，请重新进入小程序");
  }

  try {
    const existing = await db.collection("users")
      .where({ openid: OPENID })
      .limit(1)
      .get();

    if (existing.data && existing.data.length > 0) {
      const user = existing.data[0];
      await db.collection("users").doc(user._id).update({
        data: {
          unionid: UNIONID || user.unionid || "",
          lastLoginAt: now(),
          updatedAt: now(),
        },
      });

      return success({
        user: {
          _id: user._id,
          openid: user.openid,
          unionid: UNIONID || user.unionid || "",
          nickName: user.nickName || "",
          avatarUrl: user.avatarUrl || "",
          role: user.role || "user",
          basicInfo: user.basicInfo || {},
        },
        isNewUser: false,
      });
    }

    const createdUser = {
      openid: OPENID,
      unionid: UNIONID || "",
      nickName: "",
      avatarUrl: "",
      phone: "",
      role: "user",
      basicInfo: {},
      createdAt: now(),
      updatedAt: now(),
      lastLoginAt: now(),
    };
    const created = await db.collection("users").add({ data: createdUser });

    return success({
      user: {
        _id: created._id,
        openid: OPENID,
        unionid: UNIONID || "",
        nickName: "",
        avatarUrl: "",
        role: "user",
        basicInfo: {},
      },
      isNewUser: true,
    });
  } catch (err) {
    console.error("login 失败:", err);
    return fromError(err, "DB_ERROR", "登录失败，请稍后重试");
  }
};
