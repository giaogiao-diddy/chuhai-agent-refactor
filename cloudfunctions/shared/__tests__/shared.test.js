const assert = require("assert");

const {
  getQuestionById,
  getQuestionsForBranch,
} = require("../questionFlow");
const { normalizeQuestion } = require("../questionModel");
const { buildTemplateReport } = require("../reportTemplate");
const { calculateScores } = require("../scoring");
const { validateAnswer } = require("../validators");

async function test(name, fn) {
  try {
    await fn();
    console.log(`PASS ${name}`);
  } catch (error) {
    console.error(`FAIL ${name}`);
    console.error(error);
    process.exitCode = 1;
  }
}

const MOCK_QUESTIONS = [
  {
    question_id: 1,
    title: "是否已有海外订单？",
    description: "",
    dimension: "feasibility",
    branch: "common",
    type: "radio",
    options: [
      { option_id: 1, option_text: "有", score: 4, branch_to: "has_overseas" },
      { option_id: 2, option_text: "没有", score: 1, branch_to: "no_overseas" },
    ],
    sort_order: 1,
    is_active: true,
  },
  {
    question_id: 2,
    title: "已有出海渠道",
    description: "",
    dimension: "lead",
    branch: "has_overseas",
    type: "checkbox",
    options: [{ option_id: 1, option_text: "展会", score: 2 }],
    sort_order: 2,
    is_active: true,
  },
  {
    question_id: 3,
    title: "准备先验证什么",
    description: "",
    dimension: "lead",
    branch: "no_overseas",
    type: "text",
    options: [],
    sort_order: 3,
    is_active: true,
  },
];

function createMockDb(data) {
  return {
    collection() {
      return {
        where(query) {
          const matched = data.filter((item) => {
            return Object.keys(query).every((key) => item[key] === query[key]);
          });
          return {
            orderBy() {
              return {
                async get() {
                  return { data: matched.slice().sort((a, b) => a.sort_order - b.sort_order) };
                },
              };
            },
            limit() {
              return {
                async get() {
                  return { data: matched.slice(0, 1) };
                },
              };
            },
          };
        },
      };
    },
  };
}

test("question flow loads active questions from database and filters branch", async () => {
  const db = createMockDb(MOCK_QUESTIONS);
  const hasOverseasQuestions = await getQuestionsForBranch(db, "has_overseas");
  const noOverseasQuestions = await getQuestionsForBranch(db, "no_overseas");

  assert(hasOverseasQuestions.questions.some((item) => item.question_id === 2));
  assert(!hasOverseasQuestions.questions.some((item) => item.question_id === 3));
  assert(noOverseasQuestions.questions.some((item) => item.question_id === 3));
  assert(!noOverseasQuestions.questions.some((item) => item.question_id === 2));
});

test("question flow gets question by numeric id", async () => {
  const db = createMockDb(MOCK_QUESTIONS);
  const question = await getQuestionById(db, 1);

  assert.equal(question.question_id, 1);
  assert.equal(question.options[0].branch_to, "has_overseas");
});

test("validators support text single and multiple choice", () => {
  validateAnswer(normalizeQuestion({
    question_id: 10,
    title: "行业",
    description: "",
    dimension: "feasibility",
    branch: "common",
    type: "text",
    options: [],
    sort_order: 1,
  }), { answer_text: "五金配件" });
  validateAnswer(normalizeQuestion(MOCK_QUESTIONS[0]), { option_id: 1 });
  validateAnswer(normalizeQuestion(MOCK_QUESTIONS[1]), { option_ids: [1] });

  assert.throws(() => {
    validateAnswer(normalizeQuestion(MOCK_QUESTIONS[0]), { option_id: 999 });
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
