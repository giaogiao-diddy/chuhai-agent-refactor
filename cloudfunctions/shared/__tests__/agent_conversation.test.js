const assert = require("assert");

const {
  CONVERSATION_STATUS,
  canFinishConversation,
  getMissingSlots,
  shouldForceFinish,
} = require("../agentState");
const {
  mergeSlots,
  validateExtractedSlots,
} = require("../conversationSlots");
const {
  applyDefaultAnswers,
} = require("../defaultAnswerPolicy");
const {
  enrichAlignedAnswersWithScores,
  validateAlignedAnswers,
} = require("../slotAlignment");

function test(name, fn) {
  try {
    fn();
    console.log(`PASS ${name}`);
  } catch (error) {
    console.error(`FAIL ${name}`);
    console.error(error);
    process.exitCode = 1;
  }
}

const sampleQuestions = [
  {
    question_id: 1,
    title: "企业所属行业",
    type: "text",
    options: [],
    is_active: true,
  },
  {
    question_id: 2,
    title: "团队规模",
    type: "radio",
    options: [
      { option_id: 1, option_text: "10人以下", feasibility_score: 1, lead_score: 1 },
      { option_id: 2, option_text: "10-50人", feasibility_score: 2, lead_score: 2 },
    ],
    is_active: true,
  },
  {
    question_id: 3,
    title: "目标市场",
    type: "radio",
    options: [
      { option_id: 1, option_text: "暂不明确", feasibility_score: 1, lead_score: 1 },
      { option_id: 2, option_text: "已有明确市场", feasibility_score: 3, lead_score: 2 },
    ],
    is_active: true,
  },
];

test("agent state identifies missing required slots and finish readiness", () => {
  const slots = {
    industry: { value: "健身器材", confidence: 0.92, evidence: "我们做健身器材", confirmed: true },
    mainProduct: { value: "商用力量训练设备", confidence: 0.9, evidence: "主推商用力量训练", confirmed: true },
    hasForeignTradeExperience: { value: false, confidence: 0.85, evidence: "还没有外贸经验", confirmed: true },
    targetMarkets: { value: ["东南亚"], confidence: 0.8, evidence: "想看东南亚", confirmed: true },
    currentSalesRegions: { value: ["国内"], confidence: 0.8, evidence: "目前国内为主", confirmed: true },
    teamCapability: { value: "没有专门外贸团队", confidence: 0.82, evidence: "没有专门团队", confirmed: true },
    budgetLevel: { value: "有初步预算", confidence: 0.79, evidence: "可以投入一点预算", confirmed: true },
    currentPainPoints: { value: ["不知道怎么获客"], confidence: 0.88, evidence: "不知道怎么获客", confirmed: true },
  };

  assert.deepEqual(getMissingSlots(slots), []);
  assert.equal(canFinishConversation(slots), true);
  assert.equal(CONVERSATION_STATUS.COLLECTING, "collecting");
});

test("agent state forces finish when round or ai failure limit is reached", () => {
  assert.deepEqual(shouldForceFinish({ conversationRound: 8, aiFailureCount: 0 }), {
    forced: true,
    reason: "max_rounds_reached",
  });
  assert.deepEqual(shouldForceFinish({ conversationRound: 1, aiFailureCount: 2 }), {
    forced: true,
    reason: "ai_failure_fallback",
  });
});

test("mergeSlots keeps stronger evidence and merges arrays", () => {
  const merged = mergeSlots(
    {
      industry: { value: "健身器材", confidence: 0.92, evidence: "我们做健身器材" },
      targetMarkets: { value: ["东南亚"], confidence: 0.75, evidence: "想看东南亚" },
    },
    {
      industry: { value: "运动器材", confidence: 0.55, evidence: "可能是运动器材" },
      targetMarkets: { value: ["东南亚", "中东"], confidence: 0.82, evidence: "东南亚和中东都想看" },
    }
  );

  assert.equal(merged.industry.value, "健身器材");
  assert.deepEqual(merged.targetMarkets.value, ["东南亚", "中东"]);
});

test("validateExtractedSlots rejects malformed confidence", () => {
  assert.throws(() => {
    validateExtractedSlots({
      industry: { value: "健身器材", confidence: 2, evidence: "x" },
    });
  }, /confidence必须在0到1之间/);
});

test("validateAlignedAnswers rejects unknown question and option ids", () => {
  assert.throws(() => {
    validateAlignedAnswers([{ question_id: 99, option_id: 1, confidence: 0.9 }], sampleQuestions);
  }, /question_id不存在/);

  assert.throws(() => {
    validateAlignedAnswers([{ question_id: 2, option_id: 99, confidence: 0.9 }], sampleQuestions);
  }, /option_id不存在/);
});

test("enrichAlignedAnswersWithScores uses backend question scores", () => {
  const enriched = enrichAlignedAnswersWithScores([
    {
      question_id: 2,
      option_id: 2,
      evidence: "团队十几个人",
      confidence: 0.86,
    },
  ], sampleQuestions);

  assert.equal(enriched[0].score_detail.feasibility_score, 2);
  assert.equal(enriched[0].score_detail.lead_score, 2);
});

test("applyDefaultAnswers fills missing scored questions conservatively", () => {
  const completed = applyDefaultAnswers(
    [
      {
        question_id: 2,
        option_id: 2,
        evidence: "团队十几个人",
        confidence: 0.86,
      },
    ],
    sampleQuestions,
    {
      3: { option_id: 1, reason: "目标市场未明确，保守补全" },
    }
  );

  const imputed = completed.find((answer) => answer.question_id === 3);
  assert.equal(imputed.option_id, 1);
  assert.equal(imputed.imputed, true);
  assert.equal(imputed.confidence, 0);
});
