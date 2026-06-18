function activeScoredQuestions(questions) {
  return (questions || []).filter((question) => {
    return question && question.is_active !== false && (question.type === "radio" || question.type === "checkbox");
  });
}

function answerKey(answer) {
  return Number(answer.question_id);
}

function applyDefaultAnswers(alignedAnswers, questions, defaultPolicy) {
  const answers = Array.isArray(alignedAnswers) ? alignedAnswers.slice() : [];
  const answeredIds = new Set(answers.map(answerKey));
  const policy = defaultPolicy || {};

  activeScoredQuestions(questions).forEach((question) => {
    if (answeredIds.has(Number(question.question_id))) {
      return;
    }

    const configuredDefault = policy[question.question_id] || policy[String(question.question_id)];
    const fallbackOption = question.options && question.options[0] ? question.options[0] : null;
    const optionId = configuredDefault && configuredDefault.option_id
      ? configuredDefault.option_id
      : fallbackOption && fallbackOption.option_id;

    if (!optionId) {
      return;
    }

    answers.push({
      question_id: Number(question.question_id),
      option_id: Number(optionId),
      evidence: configuredDefault && configuredDefault.reason
        ? configuredDefault.reason
        : "对话未明确提及，系统使用保守默认值",
      confidence: 0,
      aligned_by: "default_imputation",
      imputed: true,
    });
  });

  return answers;
}

module.exports = {
  applyDefaultAnswers,
};
