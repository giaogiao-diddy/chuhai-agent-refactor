const { db, getContext, now } = require("./shared/db");
const { fail, success, fromError } = require("./shared/response");
const {
  CONVERSATION_STATUS,
  FINISH_REASON,
  MAX_CONVERSATION_ROUNDS,
  MAX_AI_FAILURES,
  getMissingSlots,
  canFinishConversation,
  shouldForceFinish,
} = require("./shared/agentState");
const { mergeSlots } = require("./shared/conversationSlots");
const { enrichAlignedAnswersWithScores } = require("./shared/slotAlignment");
const { applyDefaultAnswers } = require("./shared/defaultAnswerPolicy");
const { TOOLS_DEFINITIONS, TOOLS_MAPPING } = require("./shared/toolRegistry");

// ── 配置 ──────────────────────────────────────────────────────
const MAX_MESSAGE_LENGTH = 500;
const MAX_RECENT_MESSAGES = 12;

const SYSTEM_PROMPT = `你是深度未来的企业出海诊断顾问。你需要通过自然对话采集企业信息，并输出严格 JSON。

规则：
1. replyText：3 句以内。先给 1 句行业痛点洞察，再自然提问。不要长篇大论。
2. extracted_slots：从用户本轮消息中抽取的结构化信息。字段只能在预定义槽位列表中选择。
3. aligned_answers：将用户信息对齐到题库选项。每次最多 2 条。
4. 不要重复问已回答过的问题。
5. 不要输出 JSON 以外的任何文字。不要用 markdown 代码块包裹。

输出格式：
{"replyText":"给用户的自然语言回复","extracted_slots":{},"aligned_answers":[]}`;

// ── 主函数 ────────────────────────────────────────────────────

exports.main = async (event) => {
  const { OPENID } = getContext();
  if (!OPENID) {
    return fail("UNAUTHORIZED", "未获取到用户身份");
  }

  // 参数校验
  const assessmentId = (event && event.assessment_id) || "";
  const clientMessageId = (event && event.client_message_id) || "";
  const message = (event && event.message) || "";

  if (!assessmentId || typeof assessmentId !== "string") {
    return fail("INVALID_PARAMS", "assessment_id 不能为空");
  }
  if (!clientMessageId || typeof clientMessageId !== "string") {
    return fail("INVALID_PARAMS", "client_message_id 不能为空");
  }
  if (!message || typeof message !== "string" || !message.trim()) {
    return fail("INVALID_PARAMS", "message 不能为空");
  }
  if (message.length > MAX_MESSAGE_LENGTH) {
    return fail("INVALID_PARAMS", `消息长度不能超过 ${MAX_MESSAGE_LENGTH} 字符`);
  }

  try {
    // ── 1. 查测评 + 校验归属 ──
    const assessRes = await db.collection("assessments").doc(assessmentId).get();
    const doc = Array.isArray(assessRes.data) ? assessRes.data[0] : assessRes.data;
    if (!doc) return fail("NOT_FOUND", "测评不存在");
    if (doc.openid !== OPENID) return fail("FORBIDDEN", "无权操作此测评");

    // ── 2. 幂等查重 ──
    const dupRes = await db.collection("answers")
      .where({ client_message_id: clientMessageId, type: "conversation_message" })
      .limit(1)
      .get();
    if (dupRes.data && dupRes.data.length > 0) {
      // 重复请求 → 返回缓存的 AI 回复
      const cached = dupRes.data[0];
      return success({
        replyText: cached.ai_reply || "已收到您的消息",
        conversation_round: doc.conversation_round || 0,
        isEnded: doc.conversation_status === CONVERSATION_STATUS.COMPLETED,
      });
    }

    // ── 3. 状态机熔断判决 ──
    const currentRound = Number(doc.conversation_round) || 0;
    const aiFailureCount = Number(doc.ai_failure_count) || 0;
    const forceCheck = shouldForceFinish({ conversationRound: currentRound, aiFailureCount });

    if (forceCheck.forced) {
      // 熔断 → 标记可结束
      await db.collection("assessments").doc(assessmentId).update({
        data: {
          conversation_status: forceCheck.reason === FINISH_REASON.AI_FAILURE_FALLBACK
            ? CONVERSATION_STATUS.FALLBACK_QUESTIONNAIRE
            : CONVERSATION_STATUS.READY_TO_FINISH,
          fallback_reason: forceCheck.reason,
          updatedAt: now(),
        },
      });
      return success({
        replyText: forceCheck.reason === FINISH_REASON.AI_FAILURE_FALLBACK
          ? "抱歉，当前服务繁忙。您可以通过标准测评继续完成评估。"
          : "我们的沟通已经比较充分了。现在为您生成诊断报告，请稍候。",
        conversation_round: currentRound,
        isEnded: true,
      });
    }

    // ── 4. 保存用户消息 ──
    await db.collection("answers").add({
      data: {
        assessment_id: assessmentId,
        openid: OPENID,
        type: "conversation_message",
        role: "user",
        client_message_id: clientMessageId,
        content: message.trim(),
        created_at: now(),
      },
    });

    // ── 5. 查历史对话（最近 12 条） ──
    const historyRes = await db.collection("answers")
      .where({ assessment_id: assessmentId, type: "conversation_message" })
      .orderBy("created_at", "asc")
      .limit(MAX_RECENT_MESSAGES)
      .get();
    const history = (historyRes.data || []).map((m) => ({
      role: m.role,
      content: m.content,
    }));

    // ── 6. 查题库 ──
    const qRes = await db.collection("questions")
      .where({ is_active: true })
      .orderBy("sort_order", "asc")
      .get();
    const questions = qRes.data || [];

    // ── 7. 调 DeepSeek ──
    const existingSlots = doc.conversation_slots || {};
    const missingSlots = getMissingSlots(existingSlots);
    const questionSummary = questions.map((q) =>
      `Q${q.question_id} ${q.title} [${q.type}]`
    ).join("; ");

    let aiResult;
    try {
      aiResult = await callDeepSeekWithTools({
        systemPrompt: SYSTEM_PROMPT,
        userMessage: message.trim(),
        history,
        existingSlots,
        missingSlots,
        questionSummary,
      });
    } catch (aiErr) {
      console.error("DeepSeek 调用失败:", aiErr);
      // 失败计数 +1
      await db.collection("assessments").doc(assessmentId).update({
        data: {
          ai_failure_count: db.command.inc(1),
          updatedAt: now(),
        },
      });
      // 如果还能继续 → 返回通用回复，不中断对话
      return success({
        replyText: "不好意思，我稍微走神了。能再说一下刚才提到的产品和市场方向吗？",
        conversation_round: currentRound + 1,
        isEnded: false,
      });
    }

    // ── 8. 清洗合并槽位 ──
    let mergedSlots = existingSlots;
    if (aiResult.extracted_slots && typeof aiResult.extracted_slots === "object") {
      try {
        mergedSlots = mergeSlots(existingSlots, aiResult.extracted_slots);
      } catch (slotErr) {
        console.error("槽位合并失败:", slotErr);
      }
    }

    // ── 9. 对齐选项并追加 ──
    let alignedAnswers = Array.isArray(doc.aligned_answers) ? doc.aligned_answers.slice() : [];
    if (Array.isArray(aiResult.aligned_answers) && aiResult.aligned_answers.length > 0) {
      try {
        const enriched = enrichAlignedAnswersWithScores(aiResult.aligned_answers, questions);
        enriched.forEach((a) => {
          const existingIdx = alignedAnswers.findIndex(
            (x) => Number(x.question_id) === Number(a.question_id)
          );
          if (existingIdx >= 0) {
            alignedAnswers[existingIdx] = a;
          } else {
            alignedAnswers.push(a);
          }
        });
      } catch (alignErr) {
        console.error("选项对齐失败:", alignErr);
      }
    }

    // ── 10. 判断是否可结束 ──
    const canFinish = canFinishConversation(mergedSlots);
    const nextRound = currentRound + 1;
    const isLastRound = nextRound >= MAX_CONVERSATION_ROUNDS;
    const nextStatus = canFinish || isLastRound
      ? CONVERSATION_STATUS.READY_TO_FINISH
      : CONVERSATION_STATUS.COLLECTING;

    // ── 11. 原子更新 assessment ──
    await db.collection("assessments").doc(assessmentId).update({
      data: {
        conversation_slots: mergedSlots,
        aligned_answers: alignedAnswers,
        conversation_round: nextRound,
        conversation_status: nextStatus,
        ai_failure_count: 0,
        updatedAt: now(),
      },
    });

    // ── 12. 保存 AI 回复 ──
    const replyText = aiResult.replyText || "明白了。根据你的情况，让我继续了解一些关键信息。";
    await db.collection("answers").add({
      data: {
        assessment_id: assessmentId,
        openid: OPENID,
        type: "conversation_message",
        role: "assistant",
        client_message_id: clientMessageId,
        ai_reply: replyText,
        content: replyText,
        created_at: now(),
      },
    });

    // ── 13. 返回 ──
    return success({
      replyText,
      conversation_round: nextRound,
      isEnded: nextStatus === CONVERSATION_STATUS.READY_TO_FINISH,
      collected_slots: Object.keys(mergedSlots).reduce((acc, k) => {
        if (mergedSlots[k] && mergedSlots[k].value !== undefined) {
          acc[k] = mergedSlots[k].value;
        }
        return acc;
      }, {}),
    });
  } catch (err) {
    console.error("continueConversation 异常:", err);
    return fail("INTERNAL_ERROR", "对话处理异常，请稍后重试");
  }
};

// ── DeepSeek API 封装 ─────────────────────────────────────────

async function callDeepSeek({ systemPrompt, userMessage, history, existingSlots, missingSlots, questionSummary }) {
  const https = require("https");
  const apiKey = process.env.LB_LLM_API_KEY || "";
  if (!apiKey) {
    throw new Error("AI 服务未配置");
  }

  const slotStatus = Object.keys(existingSlots || {}).reduce((acc, k) => {
    const s = (existingSlots || {})[k];
    if (s && s.value !== undefined) {
      acc[k] = typeof s.value === "string" ? s.value : JSON.stringify(s.value);
    }
    return acc;
  }, {});

  const messages = [
    {
      role: "system",
      content: `${systemPrompt}

当前已采集槽位：${JSON.stringify(slotStatus)}
缺失槽位：${JSON.stringify(missingSlots)}
可用题库摘要：${questionSummary}`,
    },
    ...(history || []).map((h) => ({ role: h.role, content: h.content })),
    { role: "user", content: userMessage },
  ];

  return new Promise((resolve, reject) => {
    const body = JSON.stringify({
      model: process.env.LB_LLM_MODEL || "deepseek-chat",
      messages,
      temperature: 0.3,
      max_tokens: 600,
    });

    const req = https.request({
      hostname: "api.deepseek.com",
      path: "/v1/chat/completions",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${apiKey}`,
      },
      timeout: 15000,
    }, (res) => {
      let data = "";
      res.on("data", (chunk) => { data += chunk; });
      res.on("end", () => {
        try {
          const parsed = JSON.parse(data);
          if (parsed.error) {
            reject(new Error(parsed.error.message || "AI 调用失败"));
            return;
          }
          const content = parsed.choices && parsed.choices[0] && parsed.choices[0].message
            ? parsed.choices[0].message.content
            : "";
          const cleaned = (content || "").replace(/```json\s*|\s*```/g, "").trim();
          const result = JSON.parse(cleaned);
          resolve(result);
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

// ── Function Calling 递归循环（最大深度 2） ─────────────────
// 设计：云函数 20s 生命周期足够容纳 2 次 AI 往返。
// 第一次：AI 可能返回 tool_calls → 后端执行工具 → 结果喂回
// 第二次：AI 消化真实数据，生成最终回复

async function callDeepSeekWithTools(params) {
  const { systemPrompt, userMessage, history, existingSlots, missingSlots, questionSummary } = params;

  // 第一轮：发起带工具定义的 AI 请求
  const firstMessages = [
    {
      role: "system",
      content: buildToolAwareSystemPrompt({ systemPrompt, existingSlots, missingSlots, questionSummary }),
    },
    ...(history || []).map((h) => ({ role: h.role, content: h.content })),
    { role: "user", content: userMessage },
  ];

  const firstResult = await callDeepSeekRaw({ messages: firstMessages, tools: TOOLS_DEFINITIONS });
  // 调用带工具支持的原始 API

  // 检查是否触发了工具调用
  if (firstResult._raw && firstResult._raw.tool_calls && firstResult._raw.tool_calls.length > 0) {
    const toolCalls = firstResult._raw.tool_calls;

    // 追加 AI 的工具呼叫意图
    firstMessages.push(firstResult._raw);

    // 遍历执行每个工具
    for (const call of toolCalls) {
      const functionName = call.function && call.function.name;
      const rawArgs = (call.function && call.function.arguments) || "{}";

      let parsedArgs = {};
      try {
        parsedArgs = typeof rawArgs === "string" ? JSON.parse(rawArgs) : rawArgs;
      } catch (e) {
        parsedArgs = {};
      }

      // 执行真实后端函数（内置容错）
      const executor = TOOLS_MAPPING[functionName];
      const toolResult = executor
        ? await executor(parsedArgs)
        : JSON.stringify({ error: "UNKNOWN_TOOL", message: `未知工具: ${functionName}` });

      // 追加工具结果到消息链
      firstMessages.push({
        role: "tool",
        tool_call_id: call.id,
        name: functionName,
        content: toolResult,
      });
    }

    // 第二轮：AI 消化工具数据，生成最终回复
    try {
      const secondResult = await callDeepSeekRaw({ messages: firstMessages });
      return secondResult;
    } catch (err) {
      console.error("工具第二轮 AI 调用失败，降级使用第一轮结果:", err.message);
      // 降级：工具执行了但合成失败 → 返回工具数据的简要总结
      return {
        replyText: "根据系统查询，已获取到相关市场数据。建议结合您的具体产品进一步分析。",
        extracted_slots: {},
        aligned_answers: [],
      };
    }
  }

  // 未触发工具调用 → 直接返回第一轮结果
  return firstResult;
}

/**
 * 带工具支持的底层 AI 调用。
 * 返回解析后的 JSON 对象，额外附 _raw 指向原始 message（用于 tool_calls 检测）。
 */
async function callDeepSeekRaw({ messages, tools }) {
  const https = require("https");
  const apiKey = process.env.LB_LLM_API_KEY || "";
  if (!apiKey) throw new Error("AI 服务未配置");

  const requestBody = {
    model: process.env.LB_LLM_MODEL || "deepseek-chat",
    messages,
    temperature: 0.3,
    max_tokens: tools ? 600 : 600,
  };
  if (tools) {
    requestBody.tools = tools;
    requestBody.tool_choice = "auto";
  }

  return new Promise((resolve, reject) => {
    const body = JSON.stringify(requestBody);
    const req = https.request({
      hostname: "api.deepseek.com",
      path: "/v1/chat/completions",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${apiKey}`,
      },
      timeout: 15000,
    }, (res) => {
      let data = "";
      res.on("data", (chunk) => { data += chunk; });
      res.on("end", () => {
        try {
          const parsed = JSON.parse(data);
          if (parsed.error) throw new Error(parsed.error.message);

          const message = parsed.choices[0].message;
          const content = message.content || "";

          // 如果 AI 选择了工具调用 → 不解析 JSON，直接返回 raw message
          if (message.tool_calls && message.tool_calls.length > 0) {
            resolve({ _raw: message, replyText: "", extracted_slots: {}, aligned_answers: [] });
            return;
          }

          const cleaned = content.replace(/```json\s*|\s*```/g, "").trim();
          const result = JSON.parse(cleaned);
          resolve({ ...result, _raw: message });
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

/**
 * 构建带工具感知的 System Prompt
 */
function buildToolAwareSystemPrompt({ systemPrompt, existingSlots, missingSlots, questionSummary }) {
  const slotStatus = Object.keys(existingSlots || {}).reduce((acc, k) => {
    const s = (existingSlots || {})[k];
    if (s && s.value !== undefined) {
      acc[k] = typeof s.value === "string" ? s.value : JSON.stringify(s.value);
    }
    return acc;
  }, {});

  return `${systemPrompt}

当前已采集槽位：${JSON.stringify(slotStatus)}
缺失槽位：${JSON.stringify(missingSlots)}
可用题库摘要：${questionSummary}

重要：当用户询问"XX市场前景如何""这个行业在XX国家好不好做"等需要真实商情数据的问题时，你必须调用 searchMarketData 工具获取数据，不要凭猜测回答。`;
}
