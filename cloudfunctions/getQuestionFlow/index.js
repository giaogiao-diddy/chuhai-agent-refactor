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

  return {
    ok: true,
    branch,
    questions: getQuestionsForBranch(branch),
  };
};
