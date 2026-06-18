const { db, getContext } = require("./shared/db");
const { getQuestionsForBranch } = require("./shared/questionFlow");

exports.main = async (event) => {
  const { OPENID } = getContext();
  const assessmentId = event && event.assessment_id;
  let branch = event && event.branch ? event.branch : null;

  if (assessmentId) {
    const result = await db.collection("assessments").doc(assessmentId).get();
    if (result.data && result.data.openid === OPENID) {
      branch = result.data.branch || branch;
    }
  }

  try {
    const questions = await getQuestionsForBranch(db, branch, { legacy: true });
    return {
      ok: true,
      success: true,
      data: {
        branch,
        questions,
      },
      branch,
      questions,
    };
  } catch (err) {
    console.error("getQuestionFlow 失败:", err);
    return {
      ok: false,
      success: false,
      errorCode: "DB_ERROR",
      errorMessage: "获取题流失败",
      error: "获取题流失败",
    };
  }
};
