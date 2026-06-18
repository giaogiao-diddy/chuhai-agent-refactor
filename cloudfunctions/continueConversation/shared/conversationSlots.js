function assertPlainObject(value, field) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${field}必须是对象`);
  }
}

function normalizeConfidence(confidence) {
  if (confidence === undefined || confidence === null) {
    return 0;
  }
  if (typeof confidence !== "number" || Number.isNaN(confidence)) {
    throw new Error("confidence必须是数字");
  }
  if (confidence < 0 || confidence > 1) {
    throw new Error("confidence必须在0到1之间");
  }
  return confidence;
}

function normalizeEvidence(evidence) {
  if (evidence === undefined || evidence === null) {
    return "";
  }
  if (typeof evidence !== "string") {
    throw new Error("evidence必须是字符串");
  }
  return evidence.trim();
}

function normalizeSlot(slot) {
  assertPlainObject(slot, "slot");
  return {
    value: slot.value,
    confidence: normalizeConfidence(slot.confidence),
    evidence: normalizeEvidence(slot.evidence),
    source_message_id: typeof slot.source_message_id === "string" ? slot.source_message_id : "",
    confirmed: slot.confirmed === true,
  };
}

function validateExtractedSlots(extractedSlots) {
  assertPlainObject(extractedSlots, "extracted_slots");
  const normalized = {};
  Object.keys(extractedSlots).forEach((slotKey) => {
    normalized[slotKey] = normalizeSlot(extractedSlots[slotKey]);
  });
  return normalized;
}

function uniqueArray(values) {
  return Array.from(new Set(values.filter((item) => item !== null && item !== undefined && String(item).trim() !== "")));
}

function mergeSlotValue(existingSlot, incomingSlot) {
  const existing = existingSlot || null;
  const incoming = incomingSlot || null;
  if (!incoming) {
    return existing;
  }
  if (!existing) {
    return incoming;
  }

  if (Array.isArray(existing.value) || Array.isArray(incoming.value)) {
    const existingValues = Array.isArray(existing.value) ? existing.value : [existing.value];
    const incomingValues = Array.isArray(incoming.value) ? incoming.value : [incoming.value];
    return {
      ...existing,
      ...incoming,
      value: uniqueArray(existingValues.concat(incomingValues)),
      confidence: Math.max(existing.confidence || 0, incoming.confidence || 0),
      evidence: incoming.evidence || existing.evidence || "",
    };
  }

  if (incoming.confirmed || (incoming.confidence || 0) >= (existing.confidence || 0)) {
    return incoming;
  }
  return existing;
}

function mergeSlots(existingSlots, extractedSlots) {
  const existing = existingSlots ? validateExtractedSlots(existingSlots) : {};
  const incoming = extractedSlots ? validateExtractedSlots(extractedSlots) : {};
  const merged = { ...existing };

  Object.keys(incoming).forEach((slotKey) => {
    merged[slotKey] = mergeSlotValue(merged[slotKey], incoming[slotKey]);
  });

  return merged;
}

module.exports = {
  mergeSlots,
  validateExtractedSlots,
};
