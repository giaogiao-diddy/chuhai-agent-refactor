const assert = require("assert");

const {
  getQuestionById,
  getQuestionsForBranch,
  resolveBranch,
} = require("../questionFlow");
const { buildTemplateReport } = require("../reportTemplate");
const { calculateScores } = require("../scoring");
const { validateAnswer } = require("../validators");

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

test("question flow uses overseas branch names", () => {
  const branchQuestion = getQuestionById("q_has_overseas");
  const branchNames = branchQuestion.options.map((item) => item.branch_to).filter(Boolean);

  assert(branchNames.includes("has_overseas"));
  assert(branchNames.includes("no_overseas"));
});

test("question flow returns common and selected branch questions", () => {
  const hasOverseasQuestions = getQuestionsForBranch("has_overseas");
  const noOverseasQuestions = getQuestionsForBranch("no_overseas");

  assert(hasOverseasQuestions.some((item) => item.id === "q_overseas_channels"));
  assert(!hasOverseasQuestions.some((item) => item.id === "q_domestic_strength"));
  assert(noOverseasQuestions.some((item) => item.id === "q_domestic_strength"));
  assert(!noOverseasQuestions.some((item) => item.id === "q_overseas_channels"));
});

test("resolveBranch derives branch from branch answer", () => {
  const branch = resolveBranch([
    {
      question_id: "q_has_overseas",
      option_id: "stable_orders",
    },
  ]);

  assert.equal(branch, "has_overseas");
});

test("validators support text single and multiple choice", () => {
  validateAnswer(getQuestionById("q_industry"), { answer_text: "五金配件" });
  validateAnswer(getQuestionById("q_company_type"), { option_id: "factory" });
  validateAnswer(getQuestionById("q_revenue_pressure"), {
    option_ids: ["growth_slow", "need_new_market"],
  });

  assert.throws(() => {
    validateAnswer(getQuestionById("q_company_type"), { option_id: "wrong" });
  }, /选项不属于当前题目/);
});

test("scoring produces separate feasibility and lead scores", () => {
  const scores = calculateScores([
    {
      score_detail: {
        feasibility_score: 4,
        lead_score: 2,
      },
    },
    {
      score_detail: {
        feasibility_score: 1,
        lead_score: 5,
      },
    },
  ]);

  assert.equal(scores.feasibility_score, 5);
  assert.equal(scores.lead_score, 7);
  assert.equal(scores.feasibility_tag, "观察准备型");
  assert.equal(scores.lead_priority, "P3-低频触达");
});

test("template report separates customer and consultant reports", () => {
  const scores = {
    feasibility_score: 42,
    lead_score: 38,
    feasibility_tag: "基础具备型",
    lead_priority: "P1-重点跟进",
  };
  const report = buildTemplateReport({
    assessment: {
      branch: "has_overseas",
    },
    answers: [
      {
        question_id: "q_industry",
        answer_text: "五金配件",
      },
      {
        question_id: "q_overseas_market",
        answer_text: "中东",
      },
    ],
    scores,
  });

  assert(report.customer_report);
  assert(report.customer_report.full_report);
  assert(report.consultant_report);
  assert.equal(report.consultant_report.lead_priority, "P1-重点跟进");
  assert(!report.customer_report.consultant_report);
});
