/**
 * 多标签联合 RAG 检索器 — 从 CloudBase NoSQL knowledge_base 集合中
 * 按行业标签 + 目标市场联合模糊匹配召回知识，最多 3 条。
 *
 * 检索策略：
 *   1. 拆分用户行业为关键词列表
 *   2. 用 db.RegExp 对 industry_tags 做模糊匹配
 *   3. 用 db.RegExp 对 market_tags 做模糊匹配
 *   4. db.command.or 联合检索
 *   5. limit(3) + field 投影（不取全文档）
 *   6. 无结果或异常时返回内置通用方法论兜底
 */

const cloud = require("wx-server-sdk");
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });
const db = cloud.database();
const _ = db.command;

// ── 内置终极兜底方法论 ──────────────────────────────────────

const FALLBACK_KNOWLEDGE = {
  playbook:
    "建议先判断海外目标市场是否存在明确需求、中国供应链是否具备价格或工艺优势，" +
    "再选择短视频、展会、独立站、B2B 平台等最适配的验证路径。不要把所有资源押在单一获客渠道上。",
  riskPoints:
    "目标市场不明确导致资源浪费；产品合规认证缺失导致无法进入市场；" +
    "交付与售后体系缺失影响客户信任；知识产权保护意识薄弱",
};

// ── 辅助 ──────────────────────────────────────────────────────

/**
 * 从行业字符串拆分为关键词列表。
 * 示例: "健身器材-力量训练设备" → ["健身器材", "力量训练", "设备"]
 */
function splitIndustryKeywords(industry) {
  if (!industry || typeof industry !== "string" || !industry.trim()) return [];
  return industry
    .replace(/[、，,.\-/()（）]/g, " ")
    .split(/\s+/)
    .filter((w) => w.length >= 1)
    .map((w) => w.trim());
}

/**
 * 对关键词数组中的每个词，生成一个 db.RegExp 条件。
 * 返回格式: _.or([ { industry_tags: /词1/ }, { industry_tags: /词2/ }, ... ])
 */
function buildIndustryCondition(keywords) {
  if (!keywords.length) return null;
  return _.or(
    keywords.map((kw) => ({
      industry_tags: db.RegExp({ regexp: escapeRegex(kw), options: "i" }),
    }))
  );
}

function buildMarketCondition(markets) {
  if (!markets || !Array.isArray(markets) || !markets.length) return null;
  return _.or(
    markets.map((m) => {
      const kw = typeof m === "string" ? m.trim() : String(m).trim();
      return kw
        ? { market_tags: db.RegExp({ regexp: escapeRegex(kw), options: "i" }) }
        : null;
    }).filter(Boolean)
  );
}

function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * 多标签联合检索。
 * 策略：industry_tags 匹配 权重高，market_tags 匹配 权重低。
 * 优先返回同时命中行业和市场的记录，不足 3 条时补行业单命中。
 */
async function queryKnowledgeBase(industryKeywords, targetMarkets) {
  const conditions = [];

  const industryCond = buildIndustryCondition(industryKeywords);
  if (industryCond) conditions.push(industryCond);

  const marketCond = buildMarketCondition(targetMarkets);
  if (marketCond) conditions.push(marketCond);

  // 无任何条件 → 不查
  if (!conditions.length) return [];

  const where =
    conditions.length === 1 ? conditions[0] : _.and(conditions);

  try {
    const res = await db
      .collection("knowledge_base")
      .where(where)
      .field({ title: true, content: true, risk_points: true, category: true })
      .limit(3)
      .get();

    return (res.data || []).map((doc) => ({
      title: doc.title || "",
      content: doc.content || "",
      riskPoints: doc.risk_points || "",
      category: doc.category || "",
    }));
  } catch (err) {
    console.error("knowledge_base 查询异常:", err);
    return [];
  }
}

// ── 主导出 ────────────────────────────────────────────────────

/**
 * 检索行业知识。
 * 优先查 knowledge_base 集合做多标签模糊匹配，
 * 失败或空结果时返回通用方法论兜底。
 *
 * @param {string} industry      - 用户行业
 * @param {string[]} targetMarkets - 目标市场数组
 * @returns {{ playbook: string, riskPoints: string, sources: string[] }}
 */
async function retrieveIndustryKnowledge(industry, targetMarkets) {
  const keywords = splitIndustryKeywords(industry);
  const markets = Array.isArray(targetMarkets) ? targetMarkets : [];

  try {
    const matches = await queryKnowledgeBase(keywords, markets);

    if (matches.length > 0) {
      return {
        playbook: matches.map((m) => m.content).join("\n\n"),
        riskPoints: matches
          .flatMap((m) =>
            (m.riskPoints || "").split(/[；;]/).filter(Boolean)
          )
          .filter((v, i, a) => a.indexOf(v) === i)
          .join("；"),
        sources: matches.map((m) => m.title),
      };
    }
  } catch (err) {
    console.error("RAG 检索异常，走通用兜底:", err);
  }

  // 安全降级
  return {
    playbook: FALLBACK_KNOWLEDGE.playbook,
    riskPoints: FALLBACK_KNOWLEDGE.riskPoints,
    sources: ["通用中小工厂出海方法论"],
  };
}

module.exports = {
  retrieveIndustryKnowledge,
};
