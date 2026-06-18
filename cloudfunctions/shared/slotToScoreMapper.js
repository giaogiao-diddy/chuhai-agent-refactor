const { enrichAlignedAnswersWithScores } = require("./slotAlignment");
const { applyDefaultAnswers } = require("./defaultAnswerPolicy");

/**
 * 将对话槽位对齐结果 + 缺题补全 → 转成 scoring.js 可直接计算的完整答案数组。
 *
 * 流程：
 *   1. 用题库分值丰富 AI 对齐的答案（score_detail）
 *   2. 遍历 17 道计分题，缺失题用保守默认值补全
 *   3. 默认补全答案同样注入 score_detail
 *   4. 保证输出中每个元素都有 question_id / option_id / score_detail
 *
 * @param {object} input
 * @param {Array}  input.alignedAnswers - slotAlignment 对齐后的答案
 * @param {Array}  input.questions      - 题库（questions 集合文档数组）
 * @param {object} [input.defaultPolicy] - 缺题补全策略，key 为 question_id
 * @returns {Array} 完整答案数组，可直接传给 scoring.calculateScores()
 */
function mapSlotsToScoringInput({ alignedAnswers, questions, defaultPolicy } = {}) {
  const safeAnswers = Array.isArray(alignedAnswers) ? alignedAnswers : [];
  const safeQuestions = Array.isArray(questions) ? questions : [];
  const policy = defaultPolicy || {};

  // 1. 用题库分值丰富已对齐答案
  const enriched = enrichAlignedAnswersWithScores(safeAnswers, safeQuestions);

  // 2. 遍历计分题，缺失的用保守默认值补全
  const complete = applyDefaultAnswers(enriched, safeQuestions, policy);

  // 3. 为默认补全答案注入 score_detail（applyDefaultAnswers 只写 option_id）
  const questionMap = new Map();
  safeQuestions.forEach((q) => {
    const id = Number(q.question_id);
    if (Number.isFinite(id)) questionMap.set(id, q);
  });

  const finalAnswers = complete.map((answer) => {
    if (answer.score_detail) return answer;

    const q = questionMap.get(Number(answer.question_id));
    const opts = Array.isArray(q && q.options) ? q.options : [];
    const opt = opts.find((o) => Number(o.option_id) === Number(answer.option_id));

    return {
      ...answer,
      score_detail: {
        feasibility_score: (opt && opt.feasibility_score) || (opt && opt.score) || 0,
        lead_score: (opt && opt.lead_score) || (opt && opt.score) || 0,
      },
    };
  });

  return finalAnswers;
}

module.exports = {
  mapSlotsToScoringInput,
};
