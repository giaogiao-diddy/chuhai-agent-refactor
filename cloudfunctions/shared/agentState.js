const CONVERSATION_STATUS = {
  COLLECTING: "collecting",
  READY_TO_FINISH: "ready_to_finish",
  COMPLETED: "completed",
  VETOED: "vetoed",
  FALLBACK_QUESTIONNAIRE: "fallback_questionnaire",
  FAILED: "failed",
};

const FINISH_REASON = {
  ENOUGH_INFORMATION: "enough_information",
  USER_REQUESTED_FINISH: "user_requested_finish",
  MAX_ROUNDS_REACHED: "max_rounds_reached",
  HARD_VETO: "hard_veto",
  AI_FAILURE_FALLBACK: "ai_failure_fallback",
};

const REQUIRED_SLOTS = [
  "industry",
  "mainProduct",
  "hasForeignTradeExperience",
  "targetMarkets",
  "currentSalesRegions",
  "teamCapability",
  "budgetLevel",
  "currentPainPoints",
];

const MAX_CONVERSATION_ROUNDS = 8;
const MAX_AI_FAILURES = 2;

function slotHasValue(slot) {
  if (!slot || typeof slot !== "object") {
    return false;
  }
  const value = slot.value;
  if (Array.isArray(value)) {
    return value.length > 0;
  }
  if (typeof value === "string") {
    return value.trim().length > 0;
  }
  return value !== null && value !== undefined;
}

function getMissingSlots(slots) {
  const currentSlots = slots || {};
  return REQUIRED_SLOTS.filter((slotKey) => !slotHasValue(currentSlots[slotKey]));
}

function canFinishConversation(slots) {
  return getMissingSlots(slots).length === 0;
}

function shouldForceFinish(input) {
  const conversationRound = Number(input && input.conversationRound) || 0;
  const aiFailureCount = Number(input && input.aiFailureCount) || 0;

  if (conversationRound >= MAX_CONVERSATION_ROUNDS) {
    return {
      forced: true,
      reason: FINISH_REASON.MAX_ROUNDS_REACHED,
    };
  }
  if (aiFailureCount >= MAX_AI_FAILURES) {
    return {
      forced: true,
      reason: FINISH_REASON.AI_FAILURE_FALLBACK,
    };
  }
  return {
    forced: false,
    reason: "",
  };
}

module.exports = {
  CONVERSATION_STATUS,
  FINISH_REASON,
  MAX_AI_FAILURES,
  MAX_CONVERSATION_ROUNDS,
  REQUIRED_SLOTS,
  canFinishConversation,
  getMissingSlots,
  shouldForceFinish,
};
