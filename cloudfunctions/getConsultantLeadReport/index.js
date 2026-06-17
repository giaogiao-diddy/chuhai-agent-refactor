const { db, getContext } = require("./shared/db");

exports.main = async (event) => {
  const { OPENID } = getContext();
  const assessmentId = event.assessment_id;
  const assessmentResult = await db.collection("assessments").doc(assessmentId).get();

  if (!assessmentResult.data) {
    throw new Error("测评不存在");
  }

  if (assessmentResult.data.openid !== OPENID) {
    throw new Error("无权访问顾问报告");
  }

  const result = await db.collection("lead_reports")
    .where({ assessment_id: assessmentId })
    .limit(1)
    .get();

  if (result.data.length === 0) {
    throw new Error("顾问报告不存在");
  }

  return {
    ok: true,
    lead_report: result.data[0],
  };
};
