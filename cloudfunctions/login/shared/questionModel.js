const VALID_DIMENSIONS = new Set(["feasibility", "lead"]);
const VALID_BRANCHES = new Set(["common", "has_overseas", "no_overseas"]);
const VALID_TYPES = new Set(["radio", "checkbox", "text"]);

function ensureNumber(value, field) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    throw new Error(`${field}必须是数字`);
  }
  return value;
}

function ensureString(value, field, allowEmpty) {
  if (typeof value !== "string") {
    throw new Error(`${field}必须是字符串`);
  }
  const trimmed = value.trim();
  if (!allowEmpty && !trimmed) {
    throw new Error(`${field}不能为空`);
  }
  return trimmed;
}

function normalizeOption(option) {
  if (!option || typeof option !== "object" || Array.isArray(option)) {
    throw new Error("options元素必须是对象");
  }
  const score = ensureNumber(option.score, "options.score");
  const normalized = {
    option_id: ensureNumber(option.option_id, "options.option_id"),
    option_text: ensureString(option.option_text, "options.option_text", false),
    score,
    feasibility_score: typeof option.feasibility_score === "number" ? option.feasibility_score : score,
    lead_score: typeof option.lead_score === "number" ? option.lead_score : score,
  };

  if (typeof option.branch_to === "string" && option.branch_to.trim()) {
    if (!VALID_BRANCHES.has(option.branch_to)) {
      throw new Error("options.branch_to不合法");
    }
    normalized.branch_to = option.branch_to;
  }

  return normalized;
}

function normalizeQuestion(rawQuestion) {
  if (!rawQuestion || typeof rawQuestion !== "object" || Array.isArray(rawQuestion)) {
    throw new Error("题目必须是对象");
  }

  const question = {
    question_id: ensureNumber(rawQuestion.question_id, "question_id"),
    title: ensureString(rawQuestion.title, "title", false),
    description: ensureString(rawQuestion.description || "", "description", true),
    dimension: ensureString(rawQuestion.dimension, "dimension", false),
    branch: ensureString(rawQuestion.branch, "branch", false),
    type: ensureString(rawQuestion.type, "type", false),
    options: Array.isArray(rawQuestion.options) ? rawQuestion.options.map(normalizeOption) : [],
    sort_order: ensureNumber(rawQuestion.sort_order, "sort_order"),
    is_active: rawQuestion.is_active !== false,
  };

  if (!VALID_DIMENSIONS.has(question.dimension)) {
    throw new Error("dimension不合法");
  }
  if (!VALID_BRANCHES.has(question.branch)) {
    throw new Error("branch不合法");
  }
  if (!VALID_TYPES.has(question.type)) {
    throw new Error("type不合法");
  }
  if ((question.type === "radio" || question.type === "checkbox") && question.options.length === 0) {
    throw new Error("选项题必须配置options");
  }
  if (question.type === "text" && question.options.length !== 0) {
    throw new Error("填空题options必须为空数组");
  }

  return question;
}

function sortQuestions(questions) {
  return questions.slice().sort((a, b) => a.sort_order - b.sort_order);
}

function splitQuestionsByBranch(rawQuestions, branch) {
  const targetBranch = VALID_BRANCHES.has(branch) ? branch : null;
  const normalized = sortQuestions(rawQuestions.map(normalizeQuestion).filter((item) => item.is_active));
  const questions = normalized.filter((item) => {
    return item.branch === "common" || (targetBranch && item.branch === targetBranch);
  });

  return {
    questions,
    by_branch: {
      common: normalized.filter((item) => item.branch === "common"),
      has_overseas: normalized.filter((item) => item.branch === "has_overseas"),
      no_overseas: normalized.filter((item) => item.branch === "no_overseas"),
    },
  };
}

module.exports = {
  VALID_BRANCHES,
  VALID_DIMENSIONS,
  VALID_TYPES,
  normalizeQuestion,
  splitQuestionsByBranch,
};
