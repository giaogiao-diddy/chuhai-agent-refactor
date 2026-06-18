const { normalizeQuestion, splitQuestionsByBranch } = require("./questionModel");

const LEGACY_TYPE_MAP = {
  radio: "single_choice",
  checkbox: "multiple_choice",
  text: "text",
};

function toLegacyQuestion(question) {
  return {
    id: String(question.question_id),
    question_id: question.question_id,
    branch: question.branch,
    type: LEGACY_TYPE_MAP[question.type] || question.type,
    title: question.title,
    description: question.description,
    required: true,
    sort: question.sort_order,
    sort_order: question.sort_order,
    options: question.options.map((option) => ({
      id: String(option.option_id),
      option_id: option.option_id,
      text: option.option_text,
      option_text: option.option_text,
      score: option.score,
      feasibility_score: option.feasibility_score,
      lead_score: option.lead_score,
      branch_to: option.branch_to,
    })),
  };
}

async function loadActiveQuestions(db) {
  const result = await db.collection("questions")
    .where({ is_active: true })
    .orderBy("sort_order", "asc")
    .get();

  return (result.data || []).map(normalizeQuestion);
}

async function getQuestionsForBranch(db, branch, options) {
  const allQuestions = await loadActiveQuestions(db);
  const grouped = splitQuestionsByBranch(allQuestions, branch);
  if (options && options.legacy) {
    return grouped.questions.map(toLegacyQuestion);
  }
  return grouped;
}

async function getQuestionById(db, questionId) {
  const numericId = typeof questionId === "number" ? questionId : Number(questionId);
  if (!Number.isFinite(numericId)) {
    return null;
  }

  const result = await db.collection("questions")
    .where({ question_id: numericId, is_active: true })
    .limit(1)
    .get();

  if (!result.data || result.data.length === 0) {
    return null;
  }
  return normalizeQuestion(result.data[0]);
}

module.exports = {
  getQuestionById,
  getQuestionsForBranch,
  loadActiveQuestions,
  toLegacyQuestion,
};
