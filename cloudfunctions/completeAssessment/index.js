const { db, getContext, now } = require("./shared/db");
const { getQuestionsForBranch } = require("./shared/questionFlow");
const { calculateScores } = require("./shared/scoring");
const { buildTemplateReport } = require("./shared/reportTemplate");

async function upsert(collectionName, query, data) {
  const existing = await db.collection(collectionName).where(query).limit(1).get();
  if (existing.data.length > 0) {
    await db.collection(collectionName).doc(existing.data[0]._id).update({ data });
    return existing.data[0]._id;
  }
  const created = await db.collection(collectionName).add({ data: { ...data, created_at: now() } });
  return created._id;
}

exports.main = async (event) => {
  const { OPENID } = getContext();
  const assessmentId = event.assessment_id;
  const assessmentResult = await db.collection("assessments").doc(assessmentId).get();

  if (!assessmentResult.data || assessmentResult.data.openid !== OPENID) {
    throw new Error("测评不存在或无权访问");
  }

  const assessment = assessmentResult.data;
  const branch = assessment.branch;
  if (!branch) {
    throw new Error("请先完成分流题");
  }

  const requiredQuestions = getQuestionsForBranch(branch).filter((question) => question.required);
  const answersResult = await db.collection("answers").where({ assessment_id: assessmentId, openid: OPENID }).get();
  const answers = answersResult.data;
  const answeredIds = new Set(answers.map((answer) => answer.question_id));
  const missing = requiredQuestions.filter((question) => !answeredIds.has(question.id));

  if (missing.length > 0) {
    return {
      ok: false,
      error: "还有必答题未完成",
      missing_question_ids: missing.map((question) => question.id),
    };
  }

  const scores = calculateScores(answers);
  const reportBundle = buildTemplateReport({ assessment, answers, scores });

  await db.collection("assessments").doc(assessmentId).update({
    data: {
      ...scores,
      status: "completed",
      completed_at: now(),
      updated_at: now(),
    },
  });

  const reportId = await upsert("reports", { assessment_id: assessmentId, openid: OPENID }, {
    openid: OPENID,
    assessment_id: assessmentId,
    generation_type: "template",
    generation_status: "success",
    is_unlocked: false,
    report_json: reportBundle.customer_report,
    updated_at: now(),
  });

  await upsert("lead_reports", { assessment_id: assessmentId, openid: OPENID }, {
    openid: OPENID,
    assessment_id: assessmentId,
    report_json: reportBundle.consultant_report,
    updated_at: now(),
  });

  return {
    ok: true,
    assessment_id: assessmentId,
    report_id: reportId,
    ...scores,
    report: reportBundle.customer_report,
  };
};
