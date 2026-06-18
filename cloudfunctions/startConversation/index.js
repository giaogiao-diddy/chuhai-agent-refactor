const { db, getContext, now } = require("./shared/db");
const { fail, success } = require("./shared/response");
const { CONVERSATION_STATUS } = require("./shared/agentState");

const OPENING = "你好，我是深度未来的企业出海诊断顾问。先从最关键的开始：你们主要做什么产品？目前有没有海外客户或外贸经验？";

exports.main = async (event) => {
  const { OPENID } = getContext();
  if (!OPENID) {
    return fail("UNAUTHORIZED", "未获取到用户身份");
  }

  const assessmentId = event && event.assessment_id;
  if (!assessmentId || typeof assessmentId !== "string" || !assessmentId.trim()) {
    return fail("INVALID_PARAMS", "assessment_id 不能为空");
  }

  try {
    // 校验测评归属
    const assessRes = await db.collection("assessments").doc(assessmentId).get();
    const assessment = assessRes.data;
    if (!assessment || assessment.length === 0) {
      return fail("NOT_FOUND", "测评不存在");
    }
    const doc = Array.isArray(assessment) ? assessment[0] : assessment;
    if (doc.openid !== OPENID) {
      return fail("FORBIDDEN", "无权操作此测评");
    }

    // 原子化初始化 Agent 状态
    await db.collection("assessments").doc(assessmentId).update({
      data: {
        assessment_mode: "agent_conversation",
        conversation_status: CONVERSATION_STATUS.COLLECTING,
        conversation_round: 0,
        conversation_slots: {},
        aligned_answers: [],
        ai_failure_count: 0,
        agent_version: "controlled-agent-v2-phase2",
        updatedAt: now(),
      },
    });

    return success({
      replyText: OPENING,
      conversation_status: CONVERSATION_STATUS.COLLECTING,
      conversation_round: 0,
    });
  } catch (err) {
    // doc() 找不到会抛错
    if (err && err.errCode === "DATABASE_DOCUMENT_NOT_FOUND") {
      return fail("NOT_FOUND", "测评不存在");
    }
    console.error("startConversation 失败:", err);
    return fail("INTERNAL_ERROR", err.message || "启动对话失败");
  }
};
