const { db, getContext, now } = require("./shared/db");
const { getQuestionById } = require("./shared/questionFlow");
const { validateAnswer } = require("./shared/validators");
const { fail, fromError, success } = require("./shared/response");

function selectedOptions(question, payload) {
  if (question.type === "single_choice" || question.type === "radio") {
    return question.options.filter((option) => String(option.option_id || option.id) === String(payload.option_id));
  }
  if (question.type === "multiple_choice" || question.type === "checkbox") {
    return question.options.filter((option) => payload.option_ids.map(String).includes(String(option.option_id || option.id)));
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
  if (!OPENID) {
    return fail("UNAUTHORIZED", "未获取到用户身份，请重新进入小程序");
  }
  if (!assessmentId) {
    return fail("INVALID_PARAMS", "assessment_id不能为空");
  }

  try {
    const question = await getQuestionById(db, event.question_id);
    validateAnswer(question, event);

    const assessment = await db.collection("assessments").doc(assessmentId).get();
    if (!assessment.data || assessment.data.openid !== OPENID) {
      return fail("FORBIDDEN", "测评不存在或无权访问");
    }

    const detail = scoreDetail(question, event);
    const answerData = {
      openid: OPENID,
      assessment_id: assessmentId,
      question_id: question.question_id,
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
      .where({ assessment_id: assessmentId, openid: OPENID, question_id: question.question_id })
      .limit(1)
      .get();

    if (existing.data.length > 0) {
      await db.collection("answers").doc(existing.data[0]._id).update({ data: answerData });
    } else {
      await db.collection("answers").add({ data: { ...answerData, created_at: now() } });
    }

    let branch = assessment.data.branch || null;
    const selected = selectedOptions(question, event)[0];
    if (selected && selected.branch_to) {
      branch = selected.branch_to;
      await db.collection("assessments").doc(assessmentId).update({
        data: {
          branch,
          updated_at: now(),
        },
      });
    }

    return {
      ok: true,
      ...success({
        assessment_id: assessmentId,
        question_id: question.question_id,
        branch,
        score_detail: detail,
      }),
      assessment_id: assessmentId,
      question_id: question.question_id,
      branch,
      score_detail: detail,
    };
  } catch (err) {
    console.error("submitAnswer 失败:", err);
    return {
      ok: false,
      ...fromError(err, "INVALID_PARAMS", "保存答案失败"),
      error: err.message || "保存答案失败",
    };
  }
};
