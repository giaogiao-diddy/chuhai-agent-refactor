const { db, getContext, now } = require("./shared/db");
const { fail, success, fromError } = require("./shared/response");
const { CONVERSATION_STATUS, canFinishConversation, getMissingSlots } = require("./shared/agentState");
const { mapSlotsToScoringInput } = require("./shared/slotToScoreMapper");
const { calculateScores } = require("./shared/scoring");
const { retrieveIndustryKnowledge } = require("./shared/ragRetriever");
const { validateStructure, splitReports } = require("./shared/reportGuard");
const { buildTemplateReport } = require("./shared/reportTemplate");

// ── 主函数 ────────────────────────────────────────────────────

exports.main = async (event) => {
  const { OPENID } = getContext();
  if (!OPENID) return fail("UNAUTHORIZED", "未获取到用户身份");

  const assessmentId = (event && event.assessment_id) || "";
  if (!assessmentId || typeof assessmentId !== "string") {
    return fail("INVALID_PARAMS", "assessment_id 不能为空");
  }

  try {
    // ── 1. 归属校验 ──
    const assessRes = await db.collection("assessments").doc(assessmentId).get();
    const doc = Array.isArray(assessRes.data) ? assessRes.data[0] : assessRes.data;
    if (!doc) return fail("NOT_FOUND", "测评不存在");
    if (doc.openid !== OPENID) return fail("FORBIDDEN", "无权操作此测评");

    // 防止重复完成
    if (doc.status === "completed") {
      return success({
        assessment_id: assessmentId,
        openid: OPENID,
        status: "completed",
        feasibility_score: doc.feasibility_score || 0,
        feasibility_tag: doc.feasibility_tag || "",
      });
    }

    // ── 2. 查题库 ──
    const qRes = await db.collection("questions")
      .where({ is_active: true })
      .orderBy("sort_order", "asc")
      .get();
    const questions = qRes.data || [];

    // ── 3. 槽位 → 评分输入（含缺题补全） ──
    const alignedAnswers = Array.isArray(doc.aligned_answers) ? doc.aligned_answers : [];
    const scoredAnswers = mapSlotsToScoringInput({
      alignedAnswers,
      questions,
      defaultPolicy: DEFAULT_POLICY,
    });

    // ── 4. 规则评分 ──
    const scores = calculateScores(scoredAnswers);
    const scoringMeta = {
      feasibility_score: scores.feasibility_score,
      lead_score: scores.lead_score,
      feasibility_tag: scores.feasibility_tag,
      lead_priority: scores.lead_priority,
      display_score: scores.feasibility_score + 43,
    };

    // ── 5. RAG 检索 ──
    const slots = doc.conversation_slots || {};
    const industry = (slots.industry && slots.industry.value) || "";
    const targetMarkets = (slots.targetMarkets && slots.targetMarkets.value) || [];
    const ragContext = await retrieveIndustryKnowledge(industry, targetMarkets);

    // ── 6. AI 报告生成 ──
    let aiReportJson = null;
    let generationType = "ai";

    try {
      aiReportJson = await generateAIReport({
        assessment: doc,
        scoredAnswers,
        scoringMeta,
        ragContext,
        questions,
      });
    } catch (aiErr) {
      console.error("AI 报告生成失败，走模板兜底:", aiErr.message);
      generationType = "template";
    }

    // ── 7. 报告审计与拆分 ──
    let userReport;
    let consultantReport;

    if (aiReportJson && validateStructure(aiReportJson).valid) {
      const split = splitReports(aiReportJson, scoringMeta, assessmentId);
      userReport = split.userReport;
      consultantReport = split.consultantReport;
      userReport.generation_type = "ai";
    } else {
      // 模板兜底 — 也拆用户版和顾问版
      const template = buildTemplateReport({
        assessment: doc,
        answers: scoredAnswers,
        scores: scoringMeta,
      });
      userReport = {
        assessment_id: assessmentId,
        openid: OPENID,
        generation_type: "template",
        summary_report: (template.customer_report || template).summary_report || {},
        full_report: (template.customer_report || template).full_report || {},
        total_score: scoringMeta.feasibility_score,
        display_score: scoringMeta.display_score,
        tag: scoringMeta.feasibility_tag,
        is_unlocked: false,
        generated_at: new Date().toISOString(),
      };
      consultantReport = {
        assessment_id: assessmentId,
        openid: OPENID,
        lead_score: scoringMeta.lead_score,
        lead_priority: scoringMeta.lead_priority,
        feasibility_score: scoringMeta.feasibility_score,
        feasibility_tag: scoringMeta.feasibility_tag,
        sales_followup: template.consultant_report || {
          lead_temperature: "中",
          followup_focus: ["出海意愿", "行业路径"],
          opening_script: "看了您的测评结果，建议先从目标市场和产品适配度开始梳理。",
        },
        generated_at: new Date().toISOString(),
      };
      generationType = "template";
    }

    // ── 8. 分布式事务原子落库 ──
    await db.runTransaction(async (transaction) => {
      // 8a. 写入用户报告
      const reportColl = transaction.collection("reports");
      const reportRes = await reportColl.add({ data: userReport });

      // 8b. 写入顾问线索报告
      const leadColl = transaction.collection("lead_reports");
      await leadColl.add({ data: consultantReport });

      // 8c. 原子更新 assessment
      await transaction.collection("assessments").doc(assessmentId).update({
        data: {
          status: "completed",
          conversation_status: CONVERSATION_STATUS.COMPLETED,
          feasibility_score: scoringMeta.feasibility_score,
          lead_score: scoringMeta.lead_score,
          feasibility_tag: scoringMeta.feasibility_tag,
          lead_priority: scoringMeta.lead_priority,
          display_score: scoringMeta.display_score,
          report_id: reportRes._id || reportRes.id,
          generation_type: generationType,
          completedAt: now(),
          updatedAt: now(),
        },
      });
    });

    // ── 9. 返回 ──
    return success({
      assessment_id: assessmentId,
      status: "completed",
      feasibility_score: scoringMeta.feasibility_score,
      feasibility_tag: scoringMeta.feasibility_tag,
      generation_type: generationType,
    });
  } catch (err) {
    if (err && err.errCode === "DATABASE_DOCUMENT_NOT_FOUND") {
      return fail("NOT_FOUND", "测评不存在");
    }
    console.error("finishConversation 异常:", err);
    return fail("REPORT_TRANSACTION_FAILED", err.message || "报告生成异常");
  }
};

// ── 保守默认补全策略 ──────────────────────────────────────────

const DEFAULT_POLICY = {
  2: { option_id: 1, reason: "企业规模未明确，按最低承载力保守估计" },
  3: { option_id: 1, reason: "年营收未明确，按最低档保守估计" },
  4: { option_id: 1, reason: "成立年限未明确，按最低年限保守估计" },
  5: { option_id: 1, reason: "测试预算未明确，按最低预算保守估计" },
  6: { option_id: 1, reason: "产品标准化程度未明确，按定制为主保守估计" },
  7: { option_id: 1, reason: "供应链交付能力未明确，按不稳定性保守估计" },
  8: { option_id: 1, reason: "跨境经验未明确，按无经验保守估计" },
  9: { option_id: 1, reason: "英文/本地化能力未明确，按暂不具备保守估计" },
  10: { option_id: 1, reason: "线上获客基础未明确，按几乎无为保守估计" },
  11: { option_id: 1, reason: "品牌资料准备未明确，按资料较少保守估计" },
  12: { option_id: 1, reason: "海外履约能力未明确，按暂未考虑保守估计" },
  13: { option_id: 1, reason: "目标市场未明确，按不明确保守估计" },
  14: { option_id: 1, reason: "合规了解未明确，按基本不了解保守估计" },
  15: { option_id: 1, reason: "团队推进未明确，按无人负责保守估计" },
  16: { option_id: 1, reason: "出海目标未明确，按仅了解机会保守估计" },
  17: { option_id: 1, reason: "交付稳定性未明确，按不稳定性保守估计" },
  18: { option_id: 1, reason: "跨境收款未明确，按未配置保守估计" },
};

// ── AI 报告生成 ────────────────────────────────────────────────

async function generateAIReport({ assessment, scoredAnswers, scoringMeta, ragContext, questions }) {
  const https = require("https");
  const apiKey = process.env.LB_LLM_API_KEY || "";
  if (!apiKey) throw new Error("AI 服务未配置");

  const industry = (assessment.conversation_slots &&
    assessment.conversation_slots.industry &&
    assessment.conversation_slots.industry.value) || "未提供";

  const prompt = buildReportPrompt({
    industry,
    scores: scoringMeta,
    answers: scoredAnswers,
    rag: ragContext,
  });

  return new Promise((resolve, reject) => {
    const body = JSON.stringify({
      model: process.env.LB_LLM_MODEL || "deepseek-chat",
      messages: [
        { role: "system", content: REPORT_SYSTEM_PROMPT },
        { role: "user", content: prompt },
      ],
      temperature: 0.3,
      max_tokens: 4000,
    });

    const req = https.request({
      hostname: "api.deepseek.com",
      path: "/v1/chat/completions",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${apiKey}`,
      },
      timeout: 60000,
    }, (res) => {
      let data = "";
      res.on("data", (chunk) => { data += chunk; });
      res.on("end", () => {
        try {
          const parsed = JSON.parse(data);
          if (parsed.error) throw new Error(parsed.error.message);
          const content = (parsed.choices && parsed.choices[0] &&
            parsed.choices[0].message && parsed.choices[0].message.content) || "";
          const cleaned = content.replace(/```json\s*|\s*```/g, "").trim();
          resolve(JSON.parse(cleaned));
        } catch (e) {
          reject(new Error(`AI 响应解析失败: ${e.message}`));
        }
      });
    });
    req.on("error", reject);
    req.on("timeout", () => { req.destroy(); reject(new Error("AI 调用超时")); });
    req.write(body);
    req.end();
  });
}

function buildReportPrompt({ industry, scores, answers, rag }) {
  return `请基于以下数据生成企业出海诊断报告。

企业行业：${industry}
企业出海评分：${scores.feasibility_score}（展示分 ${scores.display_score}）
企业标签：${scores.feasibility_tag}
顾问跟进优先级：${scores.lead_priority}

行业知识参考：
- 行业打法：${rag.playbook || "无特定行业数据"}
- 风险点：${rag.riskPoints || "通用出海风险"}

答案明细：${JSON.stringify(answers.slice(0, 5))}

输出必须是严格的 JSON，不要有任何额外文字：
{
  "summary_report": {
    "total_score": ${scores.feasibility_score},
    "display_score": ${scores.display_score},
    "tag": "${scores.feasibility_tag}",
    "tag_explanation": "标签解读80字",
    "preliminary_judgment": "综合诊断120字",
    "strengths": ["优势1", "优势2"],
    "risks": ["风险1", "风险2"],
    "unlock_hint": "添加企业微信顾问解锁完整报告"
  },
  "full_report": {
    "summary_conclusion": "综合结论200字",
    "positioning_assessment": "定位分析200字",
    "content_assessment": "内容分析200字",
    "conversion_assessment": "转化分析200字",
    "dimension_scores": {},
    "recommended_path": "推荐路径",
    "risk_reminder": "风险提醒",
    "action_plan_30days": ["步骤1", "步骤2", "步骤3", "步骤4"],
    "consultant_guide": "顾问引导语"
  },
  "sales_followup": {
    "lead_temperature": "高/中/低",
    "followup_focus": ["重点1", "重点2"],
    "opening_script": "企微首联话术50字"
  }
}`;
}

const REPORT_SYSTEM_PROMPT = `你是深度未来的企业出海诊断顾问。请根据提供的企业信息、评分、行业知识库参考和对话数据生成专业报告。

关键规则：
1. 必须结合上下文给出的【行业知识库参考】真实案例和风险点进行报告润色，拒绝空洞陈述
2. 如果知识库给出了同行业的出海打法和供应链雷区，必须在报告的定位分析、风险提醒和行动建议中体现
3. 知识库中没有覆盖到的部分，基于通用出海方法论补充，不编造具体数据
4. 不承诺具体收益，不输出确定性合规结论，不使用强否定表达
5. 输出必须是严格 JSON，不要 markdown 代码块`;
