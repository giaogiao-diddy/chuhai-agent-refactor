/**
 * 受控工具箱 — Function Calling Schema 定义与真实后端业务函数映射。
 *
 * 设计原则：
 *   1. AI 只负责判断"要不要调工具、调哪个"——它看到的是 Schema 定义
 *   2. 后端负责"执行工具、返回数据"——AI 拿不到原始接口密钥
 *   3. 每个工具独立 try-catch，单工具失败不影响其他工具执行
 *   4. 内置数据作为 MVP，后续可替换为真实海关/行业 API
 */

// ── 内置出海商情数据 ────────────────────────────────────────

const MARKET_INTELLIGENCE = {
  default: {
    growth_rate: "稳定增长中",
    demand_level: "待进一步确认",
    competitor_density: "中等",
    verdict: "当前目标市场具备出海基础机会，建议结合产品差异化策略切入。",
  },
  "东南亚": {
    growth_rate: "年均 28%-35%",
    demand_level: "强劲",
    competitor_density: "高（中国厂商集中）",
    verdict: "东南亚正处于消费升级爆发期，对高性价比的中国制造需求旺盛。建议以短视频内容建立品牌信任，避免纯价格战。",
  },
  "中东": {
    growth_rate: "年均 22%-30%",
    demand_level: "旺盛",
    competitor_density: "中",
    verdict: "中东市场客单价高、品牌忠诚度强，对高端制造和建材类产品需求大。建议建立本地化代理网络，配合短视频展示工厂实力。",
  },
  "北美": {
    growth_rate: "年均 8%-15%",
    demand_level: "稳定",
    competitor_density: "极高",
    verdict: "北美是成熟市场，竞争激烈但利润空间大。建议以差异化设计和品牌故事切入，短视频需配合独立站和亚马逊店铺承接。",
  },
  "欧洲": {
    growth_rate: "年均 6%-12%",
    demand_level: "稳定偏强",
    competitor_density: "高",
    verdict: "欧洲市场对环保认证和合规要求严格，但品牌溢价空间大。建议优先拿到CE/ROHS等认证再启动内容营销。",
  },
  "日韩": {
    growth_rate: "年均 5%-10%",
    demand_level: "精准",
    competitor_density: "高（本土品牌强势）",
    verdict: "日韩消费者对品质和设计极度敏感。建议以精细化产品定位和本地化包装切入，短视频内容需匹配当地审美风格。",
  },
  "南美": {
    growth_rate: "年均 15%-25%",
    demand_level: "增长中",
    competitor_density: "中低",
    verdict: "南美是新兴蓝海市场，对中国制造的接受度持续提升。建议先通过B2B平台建立渠道，再以短视频辅助品牌曝光。",
  },
};

// ── Schema 定义 ─────────────────────────────────────────────

const TOOLS_DEFINITIONS = [
  {
    type: "function",
    function: {
      name: "searchMarketData",
      description:
        "查询特定出海品类在目标国家或新兴市场的宏观出口规模、需求增量密度、竞争饱和程度及时间差战略机遇数据。" +
        "当用户询问'XX市场怎么样''XX国家好不好做''这个产品适合哪个国家'时，应调用此工具获取真实商情而非猜测。",
      parameters: {
        type: "object",
        properties: {
          industry: {
            type: "string",
            description: "细分行业名称，如'健身器材''五金工具''男装'等",
          },
          market: {
            type: "string",
            description: "目标海外市场，如'东南亚''中东''北美''欧洲'等",
          },
        },
        required: ["industry", "market"],
      },
    },
  },
];

// ── 真实执行映射 ────────────────────────────────────────────

async function searchMarketData(args) {
  const industry = (args && args.industry) || "未指定行业";
  const marketInput = (args && args.market) || "";

  // 模糊匹配目标市场
  const marketKey = Object.keys(MARKET_INTELLIGENCE).find(
    (key) =>
      marketInput.includes(key) ||
      key.includes(marketInput) ||
      (marketInput === "日韩" && key === "日韩")
  );

  const data = marketKey
    ? MARKET_INTELLIGENCE[marketKey]
    : MARKET_INTELLIGENCE["default"];

  return JSON.stringify({
    industry: industry,
    market: marketInput,
    growth_rate: data.growth_rate,
    demand_level: data.demand_level,
    competitor_density: data.competitor_density,
    time_gap_verdict: data.verdict,
    data_source: "内置出海商情库",
    disclaimer: "以上数据为宏观趋势参考，具体决策请结合产品特性与目标市场深度调研",
  });
}

const TOOLS_MAPPING = {
  searchMarketData: async (args) => {
    try {
      return await searchMarketData(args);
    } catch (err) {
      console.error("searchMarketData 执行异常:", err);
      return JSON.stringify({
        error: "TOOL_EXECUTION_FAILED",
        message: "商情查询暂时不可用，请稍后重试",
      });
    }
  },
};

// ── 导出 ────────────────────────────────────────────────────

module.exports = {
  TOOLS_DEFINITIONS,
  TOOLS_MAPPING,
};
