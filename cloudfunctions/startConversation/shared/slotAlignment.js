function questionMap(questions) {
  const map = new Map();
  (questions || []).forEach((question) => {
    if (question && typeof question.question_id === "number") {
      map.set(Number(question.question_id), question);
    }
  });
  return map;
}

function findOption(question, optionId) {
  return (question.options || []).find((option) => Number(option.option_id) === Number(optionId));
}

function normalizeAlignedAnswer(answer) {
  if (!answer || typeof answer !== "object" || Array.isArray(answer)) {
    throw new Error("aligned_answers元素必须是对象");
  }
  const questionId = Number(answer.question_id);
  if (!Number.isFinite(questionId)) {
    throw new Error("question_id必须是数字");
  }
  const normalized = {
    question_id: questionId,
    evidence: typeof answer.evidence === "string" ? answer.evidence.trim() : "",
    confidence: typeof answer.confidence === "number" ? answer.confidence : 0,
    answer_text: typeof answer.answer_text === "string" ? answer.answer_text : "",
    aligned_by: typeof answer.aligned_by === "string" ? answer.aligned_by : "ai",
    imputed: answer.imputed === true,
  };

  if (answer.option_id !== undefined && answer.option_id !== null) {
    normalized.option_id = Number(answer.option_id);
    if (!Number.isFinite(normalized.option_id)) {
      throw new Error("option_id必须是数字");
    }
  }

  if (normalized.confidence < 0 || normalized.confidence > 1) {
    throw new Error("confidence必须在0到1之间");
  }

  return normalized;
}

function validateAlignedAnswers(alignedAnswers, questions) {
  if (!Array.isArray(alignedAnswers)) {
    throw new Error("aligned_answers必须是数组");
  }
  const questionsById = questionMap(questions);

  return alignedAnswers.map((rawAnswer) => {
    const answer = normalizeAlignedAnswer(rawAnswer);
    const question = questionsById.get(answer.question_id);
    if (!question) {
      throw new Error(`question_id不存在: ${answer.question_id}`);
    }

    if (question.type === "text") {
      return answer;
    }

    const option = findOption(question, answer.option_id);
    if (!option) {
      throw new Error(`option_id不存在: ${answer.option_id}`);
    }
    return answer;
  });
}

function enrichAlignedAnswersWithScores(alignedAnswers, questions) {
  const validAnswers = validateAlignedAnswers(alignedAnswers, questions);
  const questionsById = questionMap(questions);

  return validAnswers.map((answer) => {
    const question = questionsById.get(answer.question_id);
    if (question.type === "text") {
      return {
        ...answer,
        score_detail: {
          feasibility_score: 0,
          lead_score: 0,
        },
      };
    }

    const option = findOption(question, answer.option_id);
    return {
      ...answer,
      score_detail: {
        feasibility_score: option.feasibility_score || option.score || 0,
        lead_score: option.lead_score || option.score || 0,
      },
    };
  });
}

module.exports = {
  enrichAlignedAnswersWithScores,
  validateAlignedAnswers,
};
