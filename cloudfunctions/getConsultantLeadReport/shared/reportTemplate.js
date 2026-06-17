function findAnswer(answers, questionId) {
  return answers.find((item) => item.question_id === questionId) || null;
}

function textAnswer(answers, questionId, fallback) {
  const answer = findAnswer(answers, questionId);
  return answer && answer.answer_text ? answer.answer_text : fallback;
}

function selectedOptionIds(answers, questionId) {
  const answer = findAnswer(answers, questionId);
  if (!answer) return [];
  if (answer.option_id) return [answer.option_id];
  if (Array.isArray(answer.option_ids)) return answer.option_ids;
  return [];
}

function hasShortVideoRisk(answers) {
  return selectedOptionIds(answers, "q_short_video_restriction").some((id) => {
    return id === "high_limit" || id === "unclear";
  });
}

function buildTemplateReport({ assessment, answers, scores }) {
  const industry = textAnswer(answers, "q_industry", "当前行业");
  const market = textAnswer(answers, "q_overseas_market", "待验证市场");
  const shortVideoRisk = hasShortVideoRisk(answers);
  const recommendedPath = shortVideoRisk
    ? "当前不建议把短视频作为唯一主路径，应优先比较 Facebook 投流、独立站、展会、B2B 平台、SEO 等更稳妥的获客方式。"
    : "如果行业合规和内容表达条件允许，可优先考虑用短视频内容做低成本市场验证，再结合展会、B2B 或独立站承接高意向客户。";

  const customer_report = {
    hero: {
      title: `${industry}出海可行性诊断报告`,
      score: scores.feasibility_score,
      tag: scores.feasibility_tag,
      one_sentence_judgment: `基于当前答案，${industry}需要先厘清目标国家、客户画像、购买理由和第一步进入路径。`,
      core_contradiction: "当前不是单纯缺流量，而是行业机会、产品表达、客户信任和成交SOP之间还没有形成闭环。",
    },
    summary_report: {
      industry_market: `系统已记录的市场线索为：${market}。后续应继续判断主要需求国家、增长趋势和中国供应链优势。`,
      preliminary_judgment: "建议先判断行业机会、目标市场和产品购买理由，再选择短视频、展会、独立站、B2B平台或其他路径。",
      strengths: ["已经开始系统评估出海路径", "适合通过问卷结果继续拆解行业机会"],
      risks: ["目标国家和客户画像可能还不够清晰", "交付、合规或销售承接能力仍需进一步确认"],
      recommended_path: recommendedPath,
      unlock_hint: "添加企业微信顾问后，解锁完整报告和1对1深度解读。",
    },
    full_report: {
      summary_conclusion: `这份报告不是判断${industry}能不能拍短视频，而是先判断行业、产品、国家、路径、风险和第一步动作。短视频只有在合规表达和成交承接条件允许时，才适合作为优先验证路径。`,
      industry_assessment: "行业层面应判断海外是否有明确需求、需求增长在哪些国家、中国供应链是否具备价格、工艺、材质、交付或产业带优势。",
      pathway_assessment: "路径层面应比较短视频、展会、独立站、Facebook投流、B2B平台、SEO等方式的适配度，而不是默认把所有企业导向短视频。",
      positioning_assessment: "定位层面应先判断海外是否有明确需求、中国供应链是否具备优势，以及最适合切入的客户画像。",
      content_assessment: "如果选择短视频出海，内容层面应把产品目录、应用场景、工厂实力、客户案例转化为海外客户能理解的信任内容。",
      conversion_assessment: "转化层面应建立询盘筛选、报价、样品、跟进、交付和售后的最小SOP，把流量转化成可管理的留量。",
      dimension_scores: {
        feasibility: { score: scores.feasibility_score, max_score: 80, diagnosis: "企业出海可行性综合分" },
        lead: { score: scores.lead_score, max_score: 80, diagnosis: "顾问跟进优先级综合分，仅内部使用" },
      },
      risk_cards: [
        { title: "市场路径风险", content: "如果目标市场选择过宽，内容测试和销售跟进都会失焦。" },
        { title: "短视频适配风险", content: shortVideoRisk ? "该行业或产品可能存在平台表达限制，应做强风险提示并准备替代路径。" : "当前未发现明显短视频表达限制，但仍需结合平台规则复核。" },
        { title: "交付兑现风险", content: "如果交期、质量、认证或跨境交易资料不稳定，前端获客越多，后端压力越大。" },
      ],
      action_plan_30days: [
        "第1-7天：明确行业、主营产品、目标客户画像和首选市场。",
        "第8-14天：判断短视频、展会、独立站、B2B平台等路径适配度，选出第一条低风险验证路径。",
        "第15-21天：整理产品目录、客户案例、工厂实力和常见问题素材。",
        "第22-30天：检查交付、认证、收款、物流和售后基础资料。",
      ],
      consultant_guide: "建议添加企业微信顾问，基于你的行业、目标市场和当前答案获得1对1深度解读。",
    },
  };

  const consultant_report = {
    lead_score: scores.lead_score,
    lead_priority: scores.lead_priority,
    branch: assessment.branch,
    followup_focus: ["出海意愿强度", "第一步路径判断", "预算与执行条件", "行业路径风险"],
    opening_script: `看了您的测评，${industry}现在最需要先判断目标市场、产品购买理由和第一步路径，我建议先从海外客户画像和出海方式适配度拆起。`,
    internal_note: "该报告仅供顾问跟进使用，不直接展示给客户。",
  };

  return {
    customer_report,
    consultant_report,
  };
}

module.exports = {
  buildTemplateReport,
};
