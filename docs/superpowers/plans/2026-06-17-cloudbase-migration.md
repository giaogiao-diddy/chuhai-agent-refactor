# CloudBase Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current Python/FastAPI backend with a WeChat CloudBase Node.js backend for “深度未来”, supporting dynamic enterprise overseas-readiness assessment, native OpenID identity, dual scoring, customer-facing reports, consultant-facing lead reports, file upload readiness, and future WeCom/SCRM unlock.

**Architecture:** Keep the existing `backend/` as a read-only V1/V2 reference while building a new CloudBase backend under `cloudfunctions/`. The mini program will move from HTTP requests to `wx.cloud.callFunction`, using CloudBase native OpenID identity instead of JWT. The first working release should ship dynamic questions, answer saving, dual scoring, template reports, and report listing before AI/PDF/WeCom enhancements.

**Tech Stack:** WeChat Mini Program, CloudBase, Node.js cloud functions, `wx-server-sdk`, CloudBase document database, Cloud Storage, existing mini program pages.

---

## Product Context

Product name:

```text
深度未来
```

Core purposes:

```text
1. Activate private-domain users.
2. Generate enterprise overseas-readiness assessment reports.
3. Identify high-value 1v1 consulting leads for consultant follow-up.
```

Important product positioning:

- This is an enterprise overseas-readiness assessment, not a short-video overseas assessment.
- The report may recommend short-video overseas acquisition only after judging the user's industry, product, market, path, risk, and execution foundation.
- Some industries are not suitable for short-video-led acquisition. For these industries, the system must show strong risk warnings and recommend alternatives such as Facebook paid traffic, independent sites, exhibitions, B2B channels, SEO, or other compliant channels.
- The product must produce two different report surfaces:
  - Customer-facing assessment report: evaluates overseas feasibility and first-step direction.
  - Consultant-facing lead report: evaluates willingness, urgency, lead quality, follow-up priority, and sales talking points.
- Consultants may see both reports. Customers may only see the customer-facing report, with full content gated by unlock.

---

## CloudBase Environment

Use this CloudBase environment ID throughout mini program initialization, cloud function deployment, and CloudBase SDK examples:

```text
cloud1-d8gh82s3a39eff92d
```

Do not rely on an implicit current environment.

---

## File Structure

Create:

- `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/shared/db.js`  
  Initializes `wx-server-sdk`, exposes `db`, `_`, `getWXContext`, and timestamp helpers.

- `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/shared/questionFlow.js`  
  Defines dynamic question metadata, branches, question types, and completion rules.

- `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/shared/scoring.js`  
  Calculates `feasibility_score`, `feasibility_tag`, `lead_score`, and `lead_priority`.

- `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/shared/reportTemplate.js`  
  Builds structured customer reports and consultant lead reports without AI.

- `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/shared/validators.js`  
  Validates answer payloads for single choice, multiple choice, text, number, file, and url.

- `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/getQuestionFlow/index.js`
- `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/createAssessment/index.js`
- `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/submitAnswer/index.js`
- `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/completeAssessment/index.js`
- `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/generateReport/index.js`
- `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/getReportList/index.js`
- `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/getReportDetail/index.js`
- `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/getConsultantLeadReport/index.js`

Modify:

- `/Users/lkh/Desktop/罗宾出海Agent/miniprogram/app.js`  
  Initialize `wx.cloud`.

- `/Users/lkh/Desktop/罗宾出海Agent/miniprogram/utils/cloudApi.js`  
  New wrapper around `wx.cloud.callFunction`.

- `/Users/lkh/Desktop/罗宾出海Agent/miniprogram/pages/index/index.js`  
  Call `createAssessment` through CloudBase.

- `/Users/lkh/Desktop/罗宾出海Agent/miniprogram/pages/assessment/assessment.js`  
  Render dynamic question flow and support multiple question types.

- `/Users/lkh/Desktop/罗宾出海Agent/miniprogram/pages/my-report/my-report.js`
- `/Users/lkh/Desktop/罗宾出海Agent/miniprogram/pages/report-partial/report-partial.js`
- `/Users/lkh/Desktop/罗宾出海Agent/miniprogram/pages/report-full/report-full.js`

Do not delete:

- `/Users/lkh/Desktop/罗宾出海Agent/backend/`  
  Keep as implementation reference until CloudBase version reaches feature parity.

---

## CloudBase Collections

Create these collections in CloudBase console before testing:

- `users`
- `assessments`
- `answers`
- `reports`
- `lead_reports`
- `ai_report_logs`
- `uploaded_files`
- `wecom_unlock_sessions`

Initial permission policy for MVP:

- All writes must go through cloud functions.
- Mini program frontend should not directly write core business collections.
- Cloud functions identify users with `cloud.getWXContext().OPENID`.
- Consultant-only lead reports must not be returned by customer report APIs.

---

## Question Flow Model

The new assessment is not a fixed 18-question list. It is:

```text
common foundation questions
  -> branch question: has overseas business or not
  -> branch: has_overseas
  -> branch: no_overseas
  -> shared closing questions
```

Supported question types:

```text
single_choice
multiple_choice
text
number
file
url
```

The branch terms should be:

```text
has_overseas
no_overseas
```

Avoid naming them `normal` and `special`.

The branch question should identify whether the enterprise already has overseas business or foreign trade experience. Recommended business names:

```text
has_overseas
no_overseas
```

The question system must support explanations for abstract questions. Each question may include:

```js
{
  description: "为什么要问这题，以及这题如何影响报告判断",
  helper_text: "给用户看的轻量解释",
  consultant_note: "仅给顾问看的判断提示"
}
```

---

## Phase 1: CloudBase Foundation

### Task 1: Initialize CloudBase In Mini Program

**Files:**

- Modify: `/Users/lkh/Desktop/罗宾出海Agent/miniprogram/app.js`

- [ ] **Step 1: Add CloudBase initialization**

Add this in `App({ onLaunch() { ... } })`, preserving existing global data:

```js
if (!wx.cloud) {
  console.error("请使用 2.2.3 或以上基础库以使用云能力");
} else {
  wx.cloud.init({
    env: "cloud1-d8gh82s3a39eff92d",
    traceUser: true
  });
}
```

- [ ] **Step 2: Verify in WeChat Developer Tools**

Run the mini program in developer tools.

Expected:

```text
No wx.cloud undefined error.
No cloud init error.
```

- [ ] **Step 3: Confirm env binding**

Confirm the mini program project is bound to this CloudBase environment:

```text
cloud1-d8gh82s3a39eff92d
```

### Task 2: Add Cloud Function Shared Database Helper

**Files:**

- Create: `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/shared/db.js`

- [ ] **Step 1: Create helper**

```js
const cloud = require("wx-server-sdk");

cloud.init({
  env: cloud.DYNAMIC_CURRENT_ENV
});

const db = cloud.database();
const _ = db.command;

function getContext() {
  return cloud.getWXContext();
}

function now() {
  return db.serverDate();
}

module.exports = {
  cloud,
  db,
  _,
  getContext,
  now
};
```

- [ ] **Step 2: Verify module loads**

Run from project root:

```bash
node -e "require('./cloudfunctions/shared/db'); console.log('ok')"
```

Expected:

```text
ok
```

---

## Phase 2: Dynamic Question Flow

### Task 3: Define Question Flow

**Files:**

- Create: `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/shared/questionFlow.js`

- [ ] **Step 1: Add minimal dynamic question set**

Create a first version with these sections:

```js
const QUESTIONS = [
  {
    id: "q_industry",
    section: "foundation",
    branch: "common",
    type: "text",
    title: "您所在的行业和主营产品是什么？",
    description: "请尽量写到细分品类，例如“健身器材-力量训练设备”“可降解餐具-纸杯/刀叉/餐盒”。这会直接影响行业机会和目标市场判断。",
    required: true,
    sort: 1,
    ai_memory_key: "industry_product"
  },
  {
    id: "q_company_type",
    section: "foundation",
    branch: "common",
    type: "single_choice",
    title: "您的企业性质更接近哪一种？",
    required: true,
    sort: 2,
    options: [
      { id: "factory", text: "源头工厂", feasibility_score: 4, lead_score: 3 },
      { id: "trade_factory", text: "工贸一体", feasibility_score: 4, lead_score: 3 },
      { id: "trading_company", text: "外贸公司", feasibility_score: 3, lead_score: 2 },
      { id: "brand_owner", text: "自有品牌方", feasibility_score: 4, lead_score: 3 },
      { id: "expert_ip", text: "专家IP/知识类创业者", feasibility_score: 2, lead_score: 2 }
    ]
  },
  {
    id: "q_has_overseas",
    section: "foundation",
    branch: "common",
    type: "single_choice",
    title: "您目前是否已经有海外订单或海外客户？",
    description: "这道题用于区分已有外贸基础和完全未出海的企业，后续题目会根据您的实际阶段变化。",
    required: true,
    sort: 3,
    is_branch_question: true,
    options: [
      { id: "stable_orders", text: "已有稳定海外订单", branch_to: "has_overseas", feasibility_score: 4, lead_score: 4 },
      { id: "some_orders", text: "有零散海外询盘或订单", branch_to: "has_overseas", feasibility_score: 3, lead_score: 4 },
      { id: "team_no_order", text: "有外贸团队或渠道，但暂无订单", branch_to: "no_overseas", feasibility_score: 2, lead_score: 3 },
      { id: "none", text: "完全没有海外业务", branch_to: "no_overseas", feasibility_score: 1, lead_score: 3 }
    ]
  }
];

function resolveBranch(answers) {
  const branchAnswer = answers.find((item) => item.question_id === "q_has_overseas");
  if (!branchAnswer) {
    return null;
  }
  const question = QUESTIONS.find((item) => item.id === "q_has_overseas");
  const option = question.options.find((item) => item.id === branchAnswer.option_id);
  return option ? option.branch_to : null;
}

function getQuestionsForBranch(branch) {
  return QUESTIONS.filter((question) => {
    return question.branch === "common" || question.branch === branch;
  }).sort((a, b) => a.sort - b.sort);
}

module.exports = {
  QUESTIONS,
  resolveBranch,
  getQuestionsForBranch
};
```

- [ ] **Step 2: Add branch-specific questions**

Add at least two `has_overseas` questions:

```js
{
  id: "q_overseas_channels",
  section: "overseas_validation",
  branch: "has_overseas",
  type: "multiple_choice",
  title: "您的海外客户主要来自哪些渠道？",
  required: true,
  sort: 10,
  options: [
    { id: "expo", text: "海外展会", feasibility_score: 2, lead_score: 2 },
    { id: "b2b", text: "阿里国际站等B2B平台", feasibility_score: 2, lead_score: 2 },
    { id: "referral", text: "老客户介绍", feasibility_score: 3, lead_score: 2 },
    { id: "social", text: "海外社媒内容获客", feasibility_score: 4, lead_score: 3 }
  ]
}
```

Add at least two `no_overseas` questions:

```js
{
  id: "q_domestic_strength",
  section: "domestic_foundation",
  branch: "no_overseas",
  type: "multiple_choice",
  title: "您当前在国内市场的主要基础是什么？",
  required: true,
  sort: 10,
  options: [
    { id: "factory_capacity", text: "有稳定产能", feasibility_score: 3, lead_score: 2 },
    { id: "domestic_customers", text: "有稳定国内客户", feasibility_score: 3, lead_score: 2 },
    { id: "brand_content", text: "有品牌或内容基础", feasibility_score: 3, lead_score: 3 },
    { id: "unclear", text: "暂时不清楚优势", feasibility_score: 1, lead_score: 1 }
  ]
}
```

Add shared closing questions:

```js
{
  id: "q_biggest_concern",
  section: "closing",
  branch: "common",
  type: "multiple_choice",
    title: "如果启动出海，您现在最担心什么？",
  description: "这道题不会直接拉低企业出海可行性分，但会影响顾问跟进优先级和后续解读重点。",
  required: true,
  sort: 90,
  options: [
    { id: "cost", text: "投入太大，怕打水漂", feasibility_score: 0, lead_score: 4 },
    { id: "market", text: "不知道先做哪个国家", feasibility_score: 1, lead_score: 4 },
    { id: "team", text: "担心没有团队执行", feasibility_score: 0, lead_score: 3 },
    { id: "compliance", text: "担心产品合规和交易风险", feasibility_score: 0, lead_score: 3 },
    { id: "first_step", text: "不知道第一步怎么走", feasibility_score: 0, lead_score: 5 }
  ]
}
```

### Task 4: Implement getQuestionFlow Cloud Function

**Files:**

- Create: `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/getQuestionFlow/index.js`
- Create: `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/getQuestionFlow/package.json`

- [ ] **Step 1: Implement function**

```js
const { db, getContext } = require("../shared/db");
const { getQuestionsForBranch } = require("../shared/questionFlow");

exports.main = async (event) => {
  const { OPENID } = getContext();
  const assessmentId = event.assessment_id;
  let branch = event.branch || null;

  if (assessmentId) {
    const result = await db.collection("assessments").doc(assessmentId).get();
    if (result.data && result.data.openid === OPENID) {
      branch = result.data.branch || branch;
    }
  }

  const questions = getQuestionsForBranch(branch);
  return {
    ok: true,
    branch,
    questions
  };
};
```

- [ ] **Step 2: Add package file**

```json
{
  "name": "get-question-flow",
  "version": "1.0.0",
  "main": "index.js",
  "dependencies": {
    "wx-server-sdk": "latest"
  }
}
```

---

## Phase 3: Assessment And Answers

### Task 5: Create Assessment

**Files:**

- Create: `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/createAssessment/index.js`
- Create: `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/createAssessment/package.json`

- [ ] **Step 1: Implement createAssessment**

```js
const { db, getContext, now } = require("../shared/db");

exports.main = async () => {
  const { OPENID } = getContext();

  const created = await db.collection("assessments").add({
    data: {
      openid: OPENID,
      status: "in_progress",
      branch: null,
      feasibility_score: 0,
      lead_score: 0,
      feasibility_tag: null,
      lead_priority: null,
      is_unlocked: false,
      created_at: now(),
      completed_at: null
    }
  });

  return {
    ok: true,
    assessment_id: created._id
  };
};
```

### Task 6: Validate Answer Payloads

**Files:**

- Create: `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/shared/validators.js`

- [ ] **Step 1: Implement validation**

```js
function requireNonEmptyString(value, field) {
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new Error(`${field}不能为空`);
  }
}

function validateAnswer(question, payload) {
  if (!question) {
    throw new Error("题目不存在");
  }

  if (question.type === "single_choice") {
    requireNonEmptyString(payload.option_id, "option_id");
  }

  if (question.type === "multiple_choice") {
    if (!Array.isArray(payload.option_ids) || payload.option_ids.length === 0) {
      throw new Error("option_ids不能为空");
    }
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
  validateAnswer
};
```

### Task 7: Submit Answer

**Files:**

- Create: `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/submitAnswer/index.js`
- Create: `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/submitAnswer/package.json`

- [ ] **Step 1: Implement submitAnswer**

```js
const { db, _, getContext, now } = require("../shared/db");
const { QUESTIONS } = require("../shared/questionFlow");
const { validateAnswer } = require("../shared/validators");

function selectedOptions(question, payload) {
  if (question.type === "single_choice") {
    return question.options.filter((option) => option.id === payload.option_id);
  }
  if (question.type === "multiple_choice") {
    return question.options.filter((option) => payload.option_ids.includes(option.id));
  }
  return [];
}

function scoreDetail(question, payload) {
  const options = selectedOptions(question, payload);
  return {
    feasibility_score: options.reduce((sum, option) => sum + (option.feasibility_score || 0), 0),
    lead_score: options.reduce((sum, option) => sum + (option.lead_score || 0), 0)
  };
}

exports.main = async (event) => {
  const { OPENID } = getContext();
  const assessmentId = event.assessment_id;
  const questionId = event.question_id;
  const question = QUESTIONS.find((item) => item.id === questionId);

  validateAnswer(question, event);

  const assessment = await db.collection("assessments").doc(assessmentId).get();
  if (!assessment.data || assessment.data.openid !== OPENID) {
    throw new Error("测评不存在或无权访问");
  }

  const detail = scoreDetail(question, event);
  const answerData = {
    openid: OPENID,
    assessment_id: assessmentId,
    question_id: questionId,
    question_type: question.type,
    option_id: event.option_id || null,
    option_ids: event.option_ids || [],
    answer_text: event.answer_text || "",
    answer_number: typeof event.answer_number === "number" ? event.answer_number : null,
    file_ids: event.file_ids || [],
    score_detail: detail,
    updated_at: now()
  };

  const existing = await db.collection("answers")
    .where({ assessment_id: assessmentId, openid: OPENID, question_id: questionId })
    .limit(1)
    .get();

  if (existing.data.length > 0) {
    await db.collection("answers").doc(existing.data[0]._id).update({ data: answerData });
  } else {
    await db.collection("answers").add({ data: { ...answerData, created_at: now() } });
  }

  let branch = assessment.data.branch || null;
  if (question.is_branch_question) {
    const option = question.options.find((item) => item.id === event.option_id);
    branch = option ? option.branch_to : branch;
    await db.collection("assessments").doc(assessmentId).update({
      data: {
        branch,
        updated_at: now()
      }
    });
  }

  return {
    ok: true,
    assessment_id: assessmentId,
    question_id: questionId,
    branch,
    score_detail: detail
  };
};
```

---

## Phase 4: Dual Scoring And Template Report

### Task 8: Implement Scoring

**Files:**

- Create: `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/shared/scoring.js`

- [ ] **Step 1: Add scoring functions**

```js
function feasibilityTag(score) {
  if (score <= 20) {
    return "观察准备型";
  }
  if (score <= 35) {
    return "轻量试探型";
  }
  if (score <= 50) {
    return "基础具备型";
  }
  return "优先布局型";
}

function leadPriority(score) {
  if (score >= 45) {
    return "P0-立即跟进";
  }
  if (score >= 30) {
    return "P1-重点跟进";
  }
  if (score >= 18) {
    return "P2-培育跟进";
  }
  return "P3-低频触达";
}

function calculateScores(answers) {
  const feasibility_score = answers.reduce((sum, answer) => {
    return sum + ((answer.score_detail && answer.score_detail.feasibility_score) || 0);
  }, 0);

  const lead_score = answers.reduce((sum, answer) => {
    return sum + ((answer.score_detail && answer.score_detail.lead_score) || 0);
  }, 0);

  return {
    feasibility_score,
    lead_score,
    feasibility_tag: feasibilityTag(feasibility_score),
    lead_priority: leadPriority(lead_score)
  };
}

module.exports = {
  calculateScores,
  feasibilityTag,
  leadPriority
};
```

### Task 9: Build Template Report

**Files:**

- Create: `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/shared/reportTemplate.js`

- [ ] **Step 1: Implement structured report**

```js
function buildTemplateReport({ assessment, answers, scores }) {
  const industryAnswer = answers.find((item) => item.question_id === "q_industry");
  const industry = industryAnswer && industryAnswer.answer_text ? industryAnswer.answer_text : "当前行业";

  const customer_report = {
    hero: {
      title: `${industry}出海可行性诊断报告`,
      score: scores.feasibility_score,
      tag: scores.feasibility_tag,
      one_sentence_judgment: `基于当前答案，${industry}需要先厘清目标国家、客户画像、购买理由和第一步进入路径。`,
      core_contradiction: "当前不是单纯缺流量，而是行业机会、产品表达、客户信任和成交SOP之间还没有形成闭环。"
    },
    summary_report: {
      industry_market: `系统需要基于${industry}继续判断海外主要需求国家、增长趋势和中国供应链优势。`,
      preliminary_judgment: "建议先判断行业机会、目标市场和产品购买理由，再选择短视频、展会、独立站、B2B平台或其他路径。",
      strengths: ["已经开始系统评估出海路径", "适合通过问卷结果继续拆解行业机会"],
      risks: ["目标国家和客户画像可能还不够清晰", "交付、合规或销售承接能力仍需进一步确认"],
      recommended_path: "如果行业合规和内容表达条件允许，可优先考虑用短视频内容做低成本市场验证；若行业存在平台限制，应改用展会、Facebook投流、独立站、B2B或SEO等路径。"
    },
    full_report: {
      industry_assessment: "行业层面应判断海外是否有明确需求、需求增长在哪些国家、中国供应链是否具备价格、工艺、材质、交付或产业带优势。",
      pathway_assessment: "路径层面应比较短视频、展会、独立站、Facebook投流、B2B平台、SEO等方式的适配度，而不是默认把所有企业导向短视频。",
      positioning_assessment: "定位层面应先判断海外是否有明确需求、中国供应链是否具备优势，以及最适合切入的客户画像。",
      content_assessment: "如果选择短视频出海，内容层面应把产品目录、应用场景、工厂实力、客户案例转化为海外客户能理解的信任内容。",
      conversion_assessment: "转化层面应建立询盘筛选、报价、样品、跟进、交付和售后的最小SOP，把流量转化成可管理的留量。",
      risk_cards: [
        { title: "市场路径风险", content: "如果目标市场选择过宽，内容测试和销售跟进都会失焦。" },
        { title: "短视频适配风险", content: "如果行业受平台规则、合规表达或广告政策限制，不应强推短视频，应优先选择更稳妥的获客路径。" },
        { title: "交付兑现风险", content: "如果交期、质量、认证或跨境交易资料不稳定，前端获客越多，后端压力越大。" }
      ],
      action_plan_30days: [
        "第1-7天：明确行业、主营产品、目标客户画像和首选市场。",
        "第8-14天：判断短视频、展会、独立站、B2B平台等路径适配度，选出第一条低风险验证路径。",
        "第15-21天：整理产品目录、客户案例、工厂实力和常见问题素材。",
        "第22-30天：检查交付、认证、收款、物流和售后基础资料。"
      ]
    }
  };

  const consultant_report = {
    lead_score: scores.lead_score,
    lead_priority: scores.lead_priority,
    followup_focus: ["出海意愿强度", "第一步路径判断", "预算与执行条件", "行业路径风险"],
    opening_script: `看了您的测评，${industry}现在最需要先判断目标市场、产品购买理由和第一步路径，我建议先从海外客户画像和出海方式适配度拆起。`,
    internal_note: "该报告仅供顾问跟进使用，不直接展示给客户。"
  };

  return {
    customer_report,
    consultant_report
  };
}

module.exports = {
  buildTemplateReport
};
```

### Task 10: Complete Assessment And Generate Report

**Files:**

- Create: `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/completeAssessment/index.js`
- Create: `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/generateReport/index.js`

- [ ] **Step 1: Implement completeAssessment**

```js
const { db, getContext, now } = require("../shared/db");
const { getQuestionsForBranch } = require("../shared/questionFlow");
const { calculateScores } = require("../shared/scoring");
const { buildTemplateReport } = require("../shared/reportTemplate");

exports.main = async (event) => {
  const { OPENID } = getContext();
  const assessmentId = event.assessment_id;
  const assessmentResult = await db.collection("assessments").doc(assessmentId).get();

  if (!assessmentResult.data || assessmentResult.data.openid !== OPENID) {
    throw new Error("测评不存在或无权访问");
  }

  const assessment = assessmentResult.data;
  const branch = assessment.branch;
  if (!branch) {
    throw new Error("请先完成分流题");
  }

  const requiredQuestions = getQuestionsForBranch(branch).filter((question) => question.required);
  const answersResult = await db.collection("answers").where({ assessment_id: assessmentId, openid: OPENID }).get();
  const answers = answersResult.data;
  const answeredIds = new Set(answers.map((answer) => answer.question_id));
  const missing = requiredQuestions.filter((question) => !answeredIds.has(question.id));

  if (missing.length > 0) {
    return {
      ok: false,
      error: "还有必答题未完成",
      missing_question_ids: missing.map((question) => question.id)
    };
  }

  const scores = calculateScores(answers);
  const reportBundle = buildTemplateReport({ assessment, answers, scores });

  await db.collection("assessments").doc(assessmentId).update({
    data: {
      ...scores,
      status: "completed",
      completed_at: now(),
      updated_at: now()
    }
  });

  const existingReport = await db.collection("reports").where({ assessment_id: assessmentId, openid: OPENID }).limit(1).get();
  const customerReportData = {
    openid: OPENID,
    assessment_id: assessmentId,
    generation_type: "template",
    generation_status: "success",
    is_unlocked: false,
    report_json: reportBundle.customer_report,
    updated_at: now()
  };

  if (existingReport.data.length > 0) {
    await db.collection("reports").doc(existingReport.data[0]._id).update({ data: customerReportData });
  } else {
    await db.collection("reports").add({ data: { ...customerReportData, created_at: now() } });
  }

  const existingLeadReport = await db.collection("lead_reports").where({ assessment_id: assessmentId, openid: OPENID }).limit(1).get();
  const consultantReportData = {
    openid: OPENID,
    assessment_id: assessmentId,
    report_json: reportBundle.consultant_report,
    updated_at: now()
  };

  if (existingLeadReport.data.length > 0) {
    await db.collection("lead_reports").doc(existingLeadReport.data[0]._id).update({ data: consultantReportData });
  } else {
    await db.collection("lead_reports").add({ data: { ...consultantReportData, created_at: now() } });
  }

  return {
    ok: true,
    assessment_id: assessmentId,
    ...scores,
    report: reportBundle.customer_report
  };
};
```

---

## Phase 5: Mini Program Integration

### Task 11: Add cloudApi Wrapper

**Files:**

- Create: `/Users/lkh/Desktop/罗宾出海Agent/miniprogram/utils/cloudApi.js`

- [ ] **Step 1: Implement wrapper**

```js
"use strict";

function call(name, data) {
  return wx.cloud.callFunction({
    name,
    data: data || {}
  }).then((res) => {
    return {
      data: res.result,
      error: null
    };
  }).catch((err) => {
    console.error("[CloudAPI] 调用失败:", name, err);
    return {
      data: null,
      error: err.errMsg || err.message || "云函数调用失败"
    };
  });
}

module.exports = {
  call
};
```

### Task 12: Update Assessment Page To Dynamic Flow

**Files:**

- Modify: `/Users/lkh/Desktop/罗宾出海Agent/miniprogram/pages/assessment/assessment.js`

- [ ] **Step 1: Replace fixed question assumptions**

Replace logic that assumes `1 / 18` with state derived from returned question flow:

```js
const { call } = require("../../utils/cloudApi");

async function loadQuestionFlow(assessmentId, branch) {
  const { data, error } = await call("getQuestionFlow", {
    assessment_id: assessmentId,
    branch
  });
  if (error || !data || !data.ok) {
    throw new Error(error || "题目加载失败");
  }
  return data.questions;
}
```

- [ ] **Step 2: Submit answer through cloud function**

```js
async function submitAnswer(payload) {
  const { data, error } = await call("submitAnswer", payload);
  if (error || !data || !data.ok) {
    throw new Error(error || "答案提交失败");
  }
  return data;
}
```

- [ ] **Step 3: Reload question flow after branch question**

When `submitAnswer` returns a new `branch`, call `loadQuestionFlow(assessmentId, branch)` again and render the branch-specific questions.

---

## Phase 6: Reports

### Task 13: Get Report List

**Files:**

- Create: `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/getReportList/index.js`
- Modify: `/Users/lkh/Desktop/罗宾出海Agent/miniprogram/pages/my-report/my-report.js`

- [ ] **Step 1: Implement function**

```js
const { db, getContext } = require("../shared/db");

exports.main = async () => {
  const { OPENID } = getContext();
  const result = await db.collection("reports")
    .where({ openid: OPENID })
    .orderBy("created_at", "desc")
    .get();

  return {
    ok: true,
    reports: result.data
  };
};
```

### Task 14: Get Report Detail

**Files:**

- Create: `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/getReportDetail/index.js`
- Modify: `/Users/lkh/Desktop/罗宾出海Agent/miniprogram/pages/report-full/report-full.js`
- Modify: `/Users/lkh/Desktop/罗宾出海Agent/miniprogram/pages/report-partial/report-partial.js`

- [ ] **Step 1: Implement function**

```js
const { db, getContext } = require("../shared/db");

exports.main = async (event) => {
  const { OPENID } = getContext();
  const reportId = event.report_id;
  const result = await db.collection("reports").doc(reportId).get();

  if (!result.data || result.data.openid !== OPENID) {
    throw new Error("报告不存在或无权访问");
  }

  return {
    ok: true,
    report: result.data
  };
};
```

### Task 14.5: Get Consultant Lead Report

**Files:**

- Create: `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/getConsultantLeadReport/index.js`

- [ ] **Step 1: Implement consultant-only lead report function**

```js
const { db, getContext } = require("../shared/db");

exports.main = async (event) => {
  const { OPENID } = getContext();
  const assessmentId = event.assessment_id;

  const assessmentResult = await db.collection("assessments").doc(assessmentId).get();
  if (!assessmentResult.data) {
    throw new Error("测评不存在");
  }

  // MVP: only the report owner can read it. Before adding a real consultant backend,
  // replace this with consultant role verification.
  if (assessmentResult.data.openid !== OPENID) {
    throw new Error("无权访问顾问报告");
  }

  const result = await db.collection("lead_reports")
    .where({ assessment_id: assessmentId })
    .limit(1)
    .get();

  if (result.data.length === 0) {
    throw new Error("顾问报告不存在");
  }

  return {
    ok: true,
    lead_report: result.data[0]
  };
};
```

- [ ] **Step 2: Harden before production**

Before building the consultant/admin backend, do not expose this function in customer-facing pages. The final production version must verify consultant role before returning `lead_reports`.

---

## Phase 7: Deferred Enhancements

### Task 15: AI Report Generation

**Files:**

- Create: `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/shared/prompts.js`
- Create: `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/shared/aiClient.js`
- Modify: `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/generateReport/index.js`

Implementation notes:

- Port prompt constants from `/Users/lkh/Desktop/罗宾出海Agent/backend/app/services/prompts.py`.
- Keep score fields rule-owned.
- AI may generate `diagnosis_tag`, `report_memory`, `sales_hint`, and report wording only.
- Save raw/parsed responses to `ai_report_logs`.
- On AI error, keep template report.

### Task 16: File Upload And File Summary

**Files:**

- Modify: mini program assessment page to call `wx.cloud.uploadFile`.
- Create: `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/extractFileSummary/index.js`

Implementation notes:

- PDF/PPT/product catalog upload is optional.
- If file is uploaded, save file metadata to `uploaded_files`.
- If file is not uploaded, require product/industry text fields.
- Do not block assessment completion on file parsing failure.

### Task 17: WeCom/SCRM Unlock

**Files:**

- Create: `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/createWecomUnlockSession/index.js`
- Create: `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/getWecomUnlockStatus/index.js`
- Create: `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/wecomCallback/index.js`
- Create: `/Users/lkh/Desktop/罗宾出海Agent/cloudfunctions/mockUnlock/index.js`

Implementation notes:

- Keep report unlock state in `reports.is_unlocked`.
- For real automatic unlock, prefer SCRM webhook that returns `unlock_token`.
- Do not expose mock unlock in production.
- External callbacks should use HTTP Function or cloud function HTTP access with signature verification.

---

## Verification Checklist

Run after Phase 1-6:

- [ ] Developer tools can start mini program with `wx.cloud.init`.
- [ ] `createAssessment` creates one assessment under current OpenID.
- [ ] `getQuestionFlow` returns common questions before branch selection.
- [ ] `submitAnswer` saves text, single choice, and multiple choice answers.
- [ ] Branch answer updates `assessment.branch`.
- [ ] `getQuestionFlow` returns branch-specific questions after branch selection.
- [ ] `completeAssessment` refuses completion when required questions are missing.
- [ ] `completeAssessment` writes `feasibility_score`, `lead_score`, `feasibility_tag`, and `lead_priority`.
- [ ] `reports` collection contains a structured template report.
- [ ] My Reports page lists historical reports.
- [ ] Report detail page renders the new structured JSON without `[object Object]`.

---

## Migration Rules

- Do not delete or rewrite `/Users/lkh/Desktop/罗宾出海Agent/backend/` during the first migration pass.
- Do not reuse JWT or `/api/auth/wechat-login` in the CloudBase version.
- Do not call the old FastAPI endpoints from migrated pages.
- Do not make PDF/PPT upload mandatory in MVP.
- Do not let AI change scores, tags, branch, or unlock permission.
- Do not name the branches `normal` / `special`; use business names.

---

## Suggested Commit Sequence

1. `feat: initialize cloudbase mini program runtime`
2. `feat: add cloudbase dynamic question flow`
3. `feat: add cloudbase assessment answer functions`
4. `feat: add dual scoring and template reports`
5. `feat: migrate mini program assessment flow to cloud functions`
6. `feat: migrate report list and detail to cloud functions`
7. `feat: add ai report generation on cloudbase`
8. `feat: add file upload and wecom unlock cloud functions`
