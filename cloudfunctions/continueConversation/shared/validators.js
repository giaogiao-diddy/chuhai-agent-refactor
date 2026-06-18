function requireNonEmptyString(value, field) {
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new Error(`${field}不能为空`);
  }
}

function optionExists(question, optionId) {
  return Array.isArray(question.options) && question.options.some((option) => {
    return String(option.id || option.option_id) === String(optionId);
  });
}

function validateAnswer(question, payload) {
  if (!question) {
    throw new Error("题目不存在");
  }

  if (question.type === "single_choice" || question.type === "radio") {
    if (payload.option_id === undefined || payload.option_id === null || String(payload.option_id).trim() === "") {
      throw new Error("option_id不能为空");
    }
    if (!optionExists(question, payload.option_id)) {
      throw new Error("选项不属于当前题目");
    }
  }

  if (question.type === "multiple_choice" || question.type === "checkbox") {
    if (!Array.isArray(payload.option_ids) || payload.option_ids.length === 0) {
      throw new Error("option_ids不能为空");
    }
    payload.option_ids.forEach((optionId) => {
      if (!optionExists(question, optionId)) {
        throw new Error("选项不属于当前题目");
      }
    });
  }

  if (question.type === "text") {
    requireNonEmptyString(payload.answer_text, "answer_text");
  }

  if (question.type === "number") {
    if (typeof payload.answer_number !== "number" || Number.isNaN(payload.answer_number)) {
      throw new Error("answer_number必须是数字");
    }
  }

  if (question.type === "file") {
    if (!Array.isArray(payload.file_ids) || payload.file_ids.length === 0) {
      throw new Error("file_ids不能为空");
    }
  }

  if (question.type === "url") {
    requireNonEmptyString(payload.answer_text, "answer_text");
  }
}

module.exports = {
  validateAnswer,
};
