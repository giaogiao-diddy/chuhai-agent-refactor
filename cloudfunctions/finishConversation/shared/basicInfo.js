const REQUIRED_STRING_FIELDS = [
  "companyName",
  "industry",
  "industryCategory",
  "mainProduct",
  "annualRevenue",
];

const REQUIRED_ARRAY_FIELDS = [
  "currentSalesRegions",
  "targetMarkets",
];

function assertObject(value, field) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${field}必须是对象`);
  }
}

function normalizeRequiredString(value, field) {
  if (typeof value !== "string") {
    throw new Error(`${field}必须是字符串`);
  }
  const trimmed = value.trim();
  if (!trimmed) {
    throw new Error(`${field}不能为空`);
  }
  if (trimmed.length > 120) {
    throw new Error(`${field}长度不能超过120个字符`);
  }
  return trimmed;
}

function normalizeStringArray(value, field) {
  if (!Array.isArray(value)) {
    throw new Error(`${field}必须是数组`);
  }
  const normalized = value
    .map((item) => {
      if (typeof item !== "string") {
        throw new Error(`${field}只能包含字符串`);
      }
      return item.trim();
    })
    .filter(Boolean);

  if (normalized.length === 0) {
    throw new Error(`${field}不能为空`);
  }
  if (normalized.length > 10) {
    throw new Error(`${field}最多填写10项`);
  }
  return normalized;
}

function validateBasicInfo(rawBasicInfo) {
  assertObject(rawBasicInfo, "basicInfo");

  const basicInfo = {};
  REQUIRED_STRING_FIELDS.forEach((field) => {
    basicInfo[field] = normalizeRequiredString(rawBasicInfo[field], field);
  });
  REQUIRED_ARRAY_FIELDS.forEach((field) => {
    basicInfo[field] = normalizeStringArray(rawBasicInfo[field], field);
  });

  if (typeof rawBasicInfo.hasForeignTradeExperience !== "boolean") {
    throw new Error("hasForeignTradeExperience必须是布尔值");
  }
  basicInfo.hasForeignTradeExperience = rawBasicInfo.hasForeignTradeExperience;

  return {
    companyName: basicInfo.companyName,
    industry: basicInfo.industry,
    industryCategory: basicInfo.industryCategory,
    mainProduct: basicInfo.mainProduct,
    currentSalesRegions: basicInfo.currentSalesRegions,
    targetMarkets: basicInfo.targetMarkets,
    annualRevenue: basicInfo.annualRevenue,
    hasForeignTradeExperience: basicInfo.hasForeignTradeExperience,
  };
}

module.exports = {
  validateBasicInfo,
};
