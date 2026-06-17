const QUESTIONS = [
  {
    id: "q_industry",
    section: "foundation",
    branch: "common",
    type: "text",
    title: "您所在的行业和主营产品是什么？",
    description: "请尽量写到细分品类，例如“健身器材-力量训练设备”“可降解餐具-纸杯/刀叉/餐盒”。这会直接影响行业机会和目标市场判断。",
    helper_text: "行业越具体，报告越像是在分析你的真实生意。",
    required: true,
    sort: 1,
    ai_memory_key: "industry_product",
  },
  {
    id: "q_company_type",
    section: "foundation",
    branch: "common",
    type: "single_choice",
    title: "您的企业性质更接近哪一种？",
    description: "这会影响系统判断你的供应链优势、品牌表达方式和适合的出海路径。",
    required: true,
    sort: 2,
    options: [
      { id: "factory", text: "源头工厂", feasibility_score: 4, lead_score: 3 },
      { id: "trade_factory", text: "工贸一体", feasibility_score: 4, lead_score: 3 },
      { id: "trading_company", text: "外贸公司", feasibility_score: 3, lead_score: 2 },
      { id: "brand_owner", text: "自有品牌方", feasibility_score: 4, lead_score: 3 },
      { id: "expert_ip", text: "专家IP/知识类创业者", feasibility_score: 2, lead_score: 2 },
    ],
  },
  {
    id: "q_team_scale",
    section: "foundation",
    branch: "common",
    type: "single_choice",
    title: "当前团队规模大概是多少？",
    description: "团队规模不是越大越好，但会影响执行复杂度和路径建议。",
    required: true,
    sort: 3,
    options: [
      { id: "lt20", text: "20人及以下", feasibility_score: 1, lead_score: 2 },
      { id: "20_99", text: "21-99人", feasibility_score: 2, lead_score: 3 },
      { id: "100_499", text: "100-499人", feasibility_score: 3, lead_score: 3 },
      { id: "gte500", text: "500人以上", feasibility_score: 4, lead_score: 2 },
    ],
  },
  {
    id: "q_revenue_pressure",
    section: "foundation",
    branch: "common",
    type: "multiple_choice",
    title: "目前国内经营最明显的压力是什么？",
    description: "这道题会影响顾问判断你是否有出海的真实动机。",
    required: true,
    sort: 4,
    options: [
      { id: "growth_slow", text: "国内增长乏力", feasibility_score: 1, lead_score: 4 },
      { id: "margin_down", text: "利润率下降", feasibility_score: 1, lead_score: 4 },
      { id: "need_new_market", text: "想寻找新市场", feasibility_score: 2, lead_score: 5 },
      { id: "not_clear", text: "只是想先了解一下", feasibility_score: 0, lead_score: 1 },
    ],
  },
  {
    id: "q_has_overseas",
    section: "foundation",
    branch: "common",
    type: "single_choice",
    title: "您目前是否已经有海外订单或海外客户？",
    description: "这道题用于区分已有外贸基础和完全未出海的企业，后续题目会根据您的实际阶段变化。",
    required: true,
    sort: 5,
    is_branch_question: true,
    options: [
      { id: "stable_orders", text: "已有稳定海外订单", branch_to: "has_overseas", feasibility_score: 4, lead_score: 4 },
      { id: "some_orders", text: "有零散海外询盘或订单", branch_to: "has_overseas", feasibility_score: 3, lead_score: 4 },
      { id: "team_no_order", text: "有外贸团队或渠道，但暂无订单", branch_to: "no_overseas", feasibility_score: 2, lead_score: 3 },
      { id: "none", text: "完全没有海外业务", branch_to: "no_overseas", feasibility_score: 1, lead_score: 3 },
    ],
  },
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
      { id: "social", text: "海外社媒内容获客", feasibility_score: 4, lead_score: 3 },
    ],
  },
  {
    id: "q_overseas_market",
    section: "overseas_validation",
    branch: "has_overseas",
    type: "text",
    title: "您的海外客户主要分布在哪些国家或地区？",
    description: "请填写主要国家或区域，例如“中东、印尼、美国、南美”。",
    required: true,
    sort: 11,
    ai_memory_key: "existing_market",
  },
  {
    id: "q_order_quality",
    section: "overseas_validation",
    branch: "has_overseas",
    type: "single_choice",
    title: "当前海外订单质量更接近哪一种？",
    required: true,
    sort: 12,
    options: [
      { id: "large_repeat", text: "大单且有复购", feasibility_score: 4, lead_score: 4 },
      { id: "small_repeat", text: "中小单，有偶尔复购", feasibility_score: 3, lead_score: 3 },
      { id: "one_time", text: "基本是一次性采购", feasibility_score: 2, lead_score: 2 },
      { id: "unclear", text: "订单质量还不稳定", feasibility_score: 1, lead_score: 3 },
    ],
  },
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
      { id: "unclear", text: "暂时不清楚优势", feasibility_score: 1, lead_score: 1 },
    ],
  },
  {
    id: "q_first_overseas_goal",
    section: "domestic_foundation",
    branch: "no_overseas",
    type: "single_choice",
    title: "如果启动出海，您最想先验证什么？",
    required: true,
    sort: 11,
    options: [
      { id: "market_demand", text: "海外有没有需求", feasibility_score: 2, lead_score: 4 },
      { id: "target_country", text: "先做哪个国家", feasibility_score: 2, lead_score: 4 },
      { id: "client_profile", text: "海外客户是谁", feasibility_score: 2, lead_score: 3 },
      { id: "acquisition_channel", text: "用什么渠道获客", feasibility_score: 1, lead_score: 3 },
    ],
  },
  {
    id: "q_product_advantages",
    section: "product",
    branch: "common",
    type: "multiple_choice",
    title: "您认为产品或供应链最明显的优势是什么？",
    required: true,
    sort: 50,
    options: [
      { id: "price", text: "源头工厂/价格优势", feasibility_score: 3, lead_score: 2 },
      { id: "custom", text: "可定制/交期快", feasibility_score: 3, lead_score: 2 },
      { id: "rd", text: "研发能力强", feasibility_score: 4, lead_score: 2 },
      { id: "cert", text: "认证或检测资料较齐全", feasibility_score: 4, lead_score: 3 },
      { id: "brand", text: "品牌或案例有影响力", feasibility_score: 4, lead_score: 3 },
    ],
  },
  {
    id: "q_materials",
    section: "product",
    branch: "common",
    type: "multiple_choice",
    title: "目前已经具备哪些出海资料？",
    description: "这些资料会影响海外客户信任建立和成交效率。",
    required: true,
    sort: 60,
    options: [
      { id: "catalog", text: "产品目录/Catalog", feasibility_score: 3, lead_score: 2 },
      { id: "certification", text: "检测报告或目标国家认证", feasibility_score: 4, lead_score: 3 },
      { id: "quotation", text: "英文报价单或产品说明", feasibility_score: 3, lead_score: 2 },
      { id: "logistics", text: "成熟货代/报关合作", feasibility_score: 3, lead_score: 2 },
      { id: "none", text: "暂时都没有", feasibility_score: 0, lead_score: 3 },
    ],
  },
  {
    id: "q_short_video_restriction",
    section: "pathway",
    branch: "common",
    type: "single_choice",
    title: "您的产品是否存在平台表达或广告投放限制？",
    description: "部分行业不适合以短视频作为主路径，需要做强风险提示并推荐替代渠道。",
    required: true,
    sort: 70,
    options: [
      { id: "no_limit", text: "基本没有明显限制", feasibility_score: 3, lead_score: 2, short_video_risk: "low" },
      { id: "minor_limit", text: "有一些表达限制，但可以合规展示", feasibility_score: 2, lead_score: 3, short_video_risk: "medium" },
      { id: "high_limit", text: "限制较多，短视频平台不一定适合", feasibility_score: 1, lead_score: 4, short_video_risk: "high" },
      { id: "unclear", text: "不清楚是否有限制", feasibility_score: 1, lead_score: 3, short_video_risk: "unknown" },
    ],
  },
  {
    id: "q_execution_willingness",
    section: "closing",
    branch: "common",
    type: "single_choice",
    title: "如果方向判断清楚，您更倾向于怎么投入？",
    required: true,
    sort: 80,
    options: [
      { id: "long_term", text: "愿意长期布局，只要方向正确", feasibility_score: 3, lead_score: 5 },
      { id: "see_result", text: "愿意投入，但希望阶段性看到结果", feasibility_score: 2, lead_score: 4 },
      { id: "low_cost", text: "希望先低成本试错，再逐步加大投入", feasibility_score: 2, lead_score: 4 },
      { id: "unclear", text: "暂时没有明确预算和投入计划", feasibility_score: 0, lead_score: 1 },
    ],
  },
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
      { id: "first_step", text: "不知道第一步怎么走", feasibility_score: 0, lead_score: 5 },
    ],
  },
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
    return question.branch === "common" || (branch && question.branch === branch);
  }).sort((a, b) => a.sort - b.sort);
}

function getQuestionById(questionId) {
  return QUESTIONS.find((item) => item.id === questionId) || null;
}

module.exports = {
  QUESTIONS,
  resolveBranch,
  getQuestionsForBranch,
  getQuestionById,
};
