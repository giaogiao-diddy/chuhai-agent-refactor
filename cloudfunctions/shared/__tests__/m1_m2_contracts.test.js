const assert = require("assert");

const { validateBasicInfo } = require("../basicInfo");
const { normalizeQuestion, splitQuestionsByBranch } = require("../questionModel");
const { fail, success } = require("../response");
const { DEFAULT_SYSTEM_CONFIG, normalizeSystemConfig } = require("../systemConfig");

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

test("response helpers always return unified contract", () => {
  assert.deepEqual(success({ id: "x" }), {
    success: true,
    data: { id: "x" },
  });
  assert.deepEqual(fail("INVALID_PARAMS", "参数错误"), {
    success: false,
    errorCode: "INVALID_PARAMS",
    errorMessage: "参数错误",
  });
});

test("validateBasicInfo trims strings and preserves array and boolean fields", () => {
  const basicInfo = validateBasicInfo({
    companyName: "  深度未来科技  ",
    industry: "企业服务",
    industryCategory: "出海咨询",
    mainProduct: "企业出海测评",
    currentSalesRegions: ["国内", "东南亚"],
    targetMarkets: ["北美"],
    annualRevenue: "1000万-5000万",
    hasForeignTradeExperience: true,
  });

  assert.equal(basicInfo.companyName, "深度未来科技");
  assert.deepEqual(basicInfo.currentSalesRegions, ["国内", "东南亚"]);
  assert.equal(basicInfo.hasForeignTradeExperience, true);
});

test("validateBasicInfo rejects missing string array and boolean fields", () => {
  assert.throws(() => {
    validateBasicInfo({
      companyName: "",
      industry: "企业服务",
      industryCategory: "出海咨询",
      mainProduct: "企业出海测评",
      currentSalesRegions: ["国内"],
      targetMarkets: ["北美"],
      annualRevenue: "1000万-5000万",
      hasForeignTradeExperience: false,
    });
  }, /companyName不能为空/);

  assert.throws(() => {
    validateBasicInfo({
      companyName: "深度未来科技",
      industry: "企业服务",
      industryCategory: "出海咨询",
      mainProduct: "企业出海测评",
      currentSalesRegions: "国内",
      targetMarkets: ["北美"],
      annualRevenue: "1000万-5000万",
      hasForeignTradeExperience: false,
    });
  }, /currentSalesRegions必须是数组/);

  assert.throws(() => {
    validateBasicInfo({
      companyName: "深度未来科技",
      industry: "企业服务",
      industryCategory: "出海咨询",
      mainProduct: "企业出海测评",
      currentSalesRegions: ["国内"],
      targetMarkets: ["北美"],
      annualRevenue: "1000万-5000万",
      hasForeignTradeExperience: "false",
    });
  }, /hasForeignTradeExperience必须是布尔值/);
});

test("normalizeQuestion enforces question schema and maps legacy option scores", () => {
  const question = normalizeQuestion({
    question_id: 1,
    title: "是否已有外贸经验？",
    description: "",
    dimension: "feasibility",
    branch: "common",
    type: "radio",
    options: [
      { option_id: 1, option_text: "有", score: 4, branch_to: "has_overseas" },
      { option_id: 2, option_text: "没有", score: 1, branch_to: "no_overseas" },
    ],
    sort_order: 10,
    is_active: true,
  });

  assert.equal(question.question_id, 1);
  assert.equal(question.type, "radio");
  assert.equal(question.options[0].score, 4);
  assert.equal(question.options[0].feasibility_score, 4);
});

test("splitQuestionsByBranch returns common and selected branch in stable order", () => {
  const grouped = splitQuestionsByBranch([
    { question_id: 2, title: "B", dimension: "lead", branch: "has_overseas", type: "text", options: [], sort_order: 20 },
    { question_id: 1, title: "A", dimension: "feasibility", branch: "common", type: "text", options: [], sort_order: 10 },
    { question_id: 3, title: "C", dimension: "lead", branch: "no_overseas", type: "text", options: [], sort_order: 30 },
  ], "has_overseas");

  assert.deepEqual(grouped.questions.map((item) => item.question_id), [1, 2]);
  assert.equal(grouped.by_branch.common.length, 1);
  assert.equal(grouped.by_branch.has_overseas.length, 1);
});

test("normalizeSystemConfig returns defaults when database config is empty", () => {
  const config = normalizeSystemConfig(null);

  assert.equal(config.ai_report_enabled, DEFAULT_SYSTEM_CONFIG.ai_report_enabled);
  assert.equal(config.benefit_minutes_default, 45);
  assert.equal(typeof config.announcement, "string");
});
