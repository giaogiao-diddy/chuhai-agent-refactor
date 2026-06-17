const { db, getContext, now } = require("./shared/db");
const { getQuestionById } = require("./shared/questionFlow");
const { validateAnswer } = require("./shared/validators");

function selectedOptions(question, payload) {
  if (question.type === "single_choice") {
    return question.options.filter((option) => option.id === payload.option_id);
  }
  if (question.type === "multiple_choice") {
    return question.options.filter((option) => payload.option_ids.includes(option.id));
  }
  return [];
}

function scoreDetail(question, payload) {
  const options = selectedOptions(question, payload);
  return {
    feasibility_score: options.reduce((sum, option) => sum + (option.feasibility_score || 0), 0),
    lead_score: options.reduce((sum, option) => sum + (option.lead_score || 0), 0),
  };
}

exports.main = async (event) => {
  const { OPENID } = getContext();
  const assessmentId = event.assessment_id;
  const question = getQuestionById(event.question_id);

  validateAnswer(question, event);

  const assessment = await db.collection("assessments").doc(assessmentId).get();
  if (!assessment.data || assessment.data.openid !== OPENID) {
    throw new Error("测评不存在或无权访问");
  }

  const detail = scoreDetail(question, event);
  const answerData = {
    openid: OPENID,
    assessment_id: assessmentId,
    question_id: question.id,
    question_type: question.type,
    option_id: event.option_id || null,
    option_ids: event.option_ids || [],
    answer_text: event.answer_text || "",
    answer_number: typeof event.answer_number === "number" ? event.answer_number : null,
    file_ids: event.file_ids || [],
    score_detail: detail,
    updated_at: now(),
  };

  const existing = await db.collection("answers")
    .where({ assessment_id: assessmentId, openid: OPENID, question_id: question.id })
    .limit(1)
    .get();

  if (existing.data.length > 0) {
    await db.collection("answers").doc(existing.data[0]._id).update({ data: answerData });
  } else {
    await db.collection("answers").add({ data: { ...answerData, created_at: now() } });
  }

  let branch = assessment.data.branch || null;
  if (question.is_branch_question) {
    const option = question.options.find((item) => item.id === event.option_id);
    branch = option ? option.branch_to : branch;
    await db.collection("assessments").doc(assessmentId).update({
      data: {
        branch,
        updated_at: now(),
      },
    });
  }

  return {
    ok: true,
    assessment_id: assessmentId,
    question_id: question.id,
    branch,
    score_detail: detail,
  };
};
