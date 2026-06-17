const { db, getContext } = require("./shared/db");

exports.main = async (event) => {
  const { OPENID } = getContext();
  const assessmentId = event.assessment_id;
  const result = await db.collection("reports")
    .where({ assessment_id: assessmentId, openid: OPENID })
    .limit(1)
    .get();

  if (result.data.length === 0) {
    throw new Error("报告不存在或无权访问");
  }

  return {
    ok: true,
    is_unlocked: !!result.data[0].is_unlocked,
  };
};
