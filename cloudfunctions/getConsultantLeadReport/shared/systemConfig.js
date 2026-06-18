const DEFAULT_SYSTEM_CONFIG = {
  _id: "global_config",
  wecom_qr_url: "",
  ai_report_enabled: true,
  benefit_minutes_default: 45,
  announcement: "预计20-30分钟完成企业出海可行性测评，生成专属分析报告。",
};

const ALLOWED_SYSTEM_CONFIG_FIELDS = [
  "wecom_qr_url",
  "ai_report_enabled",
  "benefit_minutes_default",
  "announcement",
];

function normalizeSystemConfig(rawConfig) {
  const source = rawConfig && typeof rawConfig === "object" && !Array.isArray(rawConfig)
    ? rawConfig
    : {};

  return {
    _id: "global_config",
    wecom_qr_url: typeof source.wecom_qr_url === "string"
      ? source.wecom_qr_url
      : DEFAULT_SYSTEM_CONFIG.wecom_qr_url,
    ai_report_enabled: typeof source.ai_report_enabled === "boolean"
      ? source.ai_report_enabled
      : DEFAULT_SYSTEM_CONFIG.ai_report_enabled,
    benefit_minutes_default: typeof source.benefit_minutes_default === "number"
      ? source.benefit_minutes_default
      : DEFAULT_SYSTEM_CONFIG.benefit_minutes_default,
    announcement: typeof source.announcement === "string" && source.announcement.trim()
      ? source.announcement.trim()
      : DEFAULT_SYSTEM_CONFIG.announcement,
  };
}

function validateSystemConfigPatch(rawPatch) {
  if (!rawPatch || typeof rawPatch !== "object" || Array.isArray(rawPatch)) {
    throw new Error("config必须是对象");
  }

  const patch = {};
  Object.keys(rawPatch).forEach((key) => {
    if (!ALLOWED_SYSTEM_CONFIG_FIELDS.includes(key)) {
      throw new Error(`${key}不是允许更新的配置字段`);
    }
  });

  if ("wecom_qr_url" in rawPatch) {
    if (typeof rawPatch.wecom_qr_url !== "string") {
      throw new Error("wecom_qr_url必须是字符串");
    }
    patch.wecom_qr_url = rawPatch.wecom_qr_url.trim();
  }
  if ("ai_report_enabled" in rawPatch) {
    if (typeof rawPatch.ai_report_enabled !== "boolean") {
      throw new Error("ai_report_enabled必须是布尔值");
    }
    patch.ai_report_enabled = rawPatch.ai_report_enabled;
  }
  if ("benefit_minutes_default" in rawPatch) {
    if (typeof rawPatch.benefit_minutes_default !== "number" || rawPatch.benefit_minutes_default < 0) {
      throw new Error("benefit_minutes_default必须是非负数字");
    }
    patch.benefit_minutes_default = rawPatch.benefit_minutes_default;
  }
  if ("announcement" in rawPatch) {
    if (typeof rawPatch.announcement !== "string") {
      throw new Error("announcement必须是字符串");
    }
    patch.announcement = rawPatch.announcement.trim();
  }

  if (Object.keys(patch).length === 0) {
    throw new Error("没有可更新的配置字段");
  }

  return patch;
}

module.exports = {
  ALLOWED_SYSTEM_CONFIG_FIELDS,
  DEFAULT_SYSTEM_CONFIG,
  normalizeSystemConfig,
  validateSystemConfigPatch,
};
