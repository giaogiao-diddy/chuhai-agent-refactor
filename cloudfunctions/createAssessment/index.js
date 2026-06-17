const { db, getContext, now } = require("./shared/db");
const { validateBasicInfo } = require("./shared/basicInfo");
const { fail, fromError, success } = require("./shared/response");

exports.main = async (event) => {
  const { OPENID } = getContext();

  if (!OPENID) {
    return fail("UNAUTHORIZED", "未获取到用户身份，请重新进入小程序");
  }

  try {
    const basicInfo = event && event.basicInfo
      ? validateBasicInfo(event.basicInfo)
      : {};
    const userResult = await db.collection("users")
      .where({ openid: OPENID })
      .limit(1)
      .get();
    const user = userResult.data && userResult.data[0] ? userResult.data[0] : null;

    const result = await db.collection("assessments").add({
      data: {
        openid: OPENID,
        user_id: user ? user._id : null,
        status: "in_progress",
        branch: null,
        basicInfo,
        answers: [],
        feasibility_score: 0,
        lead_score: 0,
        overseasScore: 0,
        consultantScore: 0,
        feasibility_tag: null,
        lead_priority: null,
        overseasTag: null,
        consultantTag: null,
        unlockedFullReport: false,
        is_unlocked: false,
        addedWechat: false,
        createdAt: now(),
        updatedAt: now(),
        completedAt: null,
      },
    });

    return success({
      assessment_id: result._id,
      assessmentId: result._id,
      status: "in_progress",
    });
  } catch (err) {
    console.error("createAssessment 失败:", err);
    return fromError(err, "INVALID_PARAMS", "创建测评失败");
  }
};
